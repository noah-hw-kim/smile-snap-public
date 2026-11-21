import uuid
from fastapi import HTTPException
from database import user_collection, diary_collection, diary_entry_helper, photo_collection, user_helper, photo_helper
from datetime import datetime, timezone
from firebase_admin import auth
# from routers.websockets import manager
import asyncio
import logging
from config import settings, s3_client

logger = logging.getLogger(__name__)

# === User Services ===
async def create_user_services(user_data: dict) -> dict:
    """
    Creates a user in Firebase Auth and a profile in MongoDB.
    """
    try:
        new_firebase_user = await asyncio.to_thread(
            auth.create_user,
            email=user_data["email"],
            password=user_data["password"],
            display_name=user_data.get("displayName")
        )
        
        user_profile = {
            "userId": new_firebase_user.uid,
            "email": user_data["email"],
            "displayName": user_data.get("displayName"),
            "role": "user",  # Default role
            "createdAt": datetime.now(timezone.utc)
        }
        
        await user_collection.insert_one(user_profile)

        return user_helper(user_profile)

    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {user_data['email']} already exists."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during user creation: {e}"
        )
    
async def update_user_service(userId: str, user_data: dict) -> dict:
    """Updates a user in MongoDB and broadcasts the change."""
    update_result = await user_collection.update_one({"userId": userId}, {"$set": user_data})
    
    if update_result.modified_count == 1:
        updated_user = await user_collection.find_one({"userId": userId})
        final_user = user_helper(updated_user)
        
        # Broadcast the update to admins and the specific user
        # await manager.broadcast_to_admins({"type": "user_updated", "data": final_user})
        # await manager.send_to_user({"type": "user_updated", "data": final_user}, userId)
        
        return final_user
        
    # If no changes were made, fetch and return the current user
    existing_user = await user_collection.find_one({"userId": userId})
    return user_helper(existing_user)

async def delete_user_service(userId: str) -> bool:
    """
    Delete user and all their data from S3, MongoDB, and Firebase Auth
    """
    try:
        logger.info(f"Starting deletion for user {userId}")
        
        try:
            await asyncio.to_thread(auth.delete_user, userId)
            logger.info(f"Successfully deleted user {userId} from Firebase Auth")
        except Exception as e:
            # If Firebase fails, ABORT entirely. Do not touch the DB.
            logger.error(f"Failed to delete Firebase identity for {userId}. Aborting deletion: {e}")
            return False
        
        photos_cursor = photo_collection.find({"userId": userId})
        photos = await photos_cursor.to_list(None)
        
        if photos:
            objects_to_delete = [
                {'Key': photo["filePath"]} 
                for photo in photos if photo.get("filePath")
            ]
            
            if objects_to_delete:
                try:
                    # Execute all deletions in ONE network call
                    await asyncio.to_thread(
                        s3_client.delete_objects,
                        Bucket=settings.S3_BUCKET_NAME,
                        Delete={'Objects': objects_to_delete}
                    )
                    logger.info(f"Batch deleted {len(objects_to_delete)} photos from S3")
                except Exception as e:
                    logger.error(f"Failed batch S3 deletion for {userId}: {e}")
                    # We log the error but CONTINUE to Step 3. 
                    # Orphaned photos cost pennies; an orphaned DB record causes application bugs.
            
        photos_deleted = await photo_collection.delete_many({"userId": userId})
        entries_deleted = await diary_collection.delete_many({"userId": userId})
        user_deleted = await user_collection.delete_one({"userId": userId})
        
        return user_deleted.deleted_count == 1
        
    except Exception as e:
        logger.error(f"Critical error in delete_user_service for {userId}: {str(e)}")
        return False
    
async def get_user_by_id(user_id: str):
    """
    Directly fetches a user from the database by their ID.
    """
    user = await user_collection.find_one({"userId": user_id})
    if user:
        return user
    return None

# === Photo Services ===
async def get_photo_by_id(photo_id: str, user_id: str) -> dict:
    """Retrieves a single photo document or raises 404."""
    photo_doc = await photo_collection.find_one({"photoId": photo_id, "userId": user_id})
    if not photo_doc:
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")
    return photo_doc

async def save_photo_metadata_service(userId: str, file_path: str) -> dict:
    photo_doc = {
        "photoId": str(uuid.uuid4()),
        "userId": userId,
        "filePath": file_path,
        "createdAt": datetime.now(timezone.utc)
    }
    await photo_collection.insert_one(photo_doc)

    # final_photo = photo_helper(photo_doc)
    
    # Broadcast the new photo to the user and admins
    # await manager.send_to_user({"type": "photo_created", "data": final_photo}, userId)
    # await manager.broadcast_to_admins({"type": "photo_created", "data": final_photo})

    return photo_helper(photo_doc)

async def delete_photo_service(userId: str, photoId: str) -> bool:
    """Deletes a photo from S3 and MongoDB, then broadcasts the change."""
    # print("start delete the photo")
    
    photo_doc = await get_photo_by_id(photoId, userId)
    # print("photo_doc found in mongodb")

    file_path_to_delete = photo_doc["filePath"]

    objects_to_delete = [
        {'Key': photo_doc["filePath"]} 
    ]
    
    if objects_to_delete:
        try:
            # Execute all deletions in ONE network call
            await asyncio.to_thread(
                s3_client.delete_objects,
                Bucket=settings.S3_BUCKET_NAME,
                Delete={'Objects': objects_to_delete}
            )
            logger.info(f"Batch deleted {len(objects_to_delete)} photos from S3")
        except Exception as e:
            logger.error(f"Failed batch S3 deletion for {userId}: {e}")
            # We log the error but CONTINUE to Step 3. 
            # Orphaned photos cost pennies; an orphaned DB record causes application bugs.
    
    # Then, delete the document from MongoDB
    delete_result = await photo_collection.delete_one({"photoId": photoId})
    
    if delete_result.deleted_count == 1:
        # await manager.send_to_user({"type": "photo_deleted", "photoId": photoId}, userId)
        # await manager.broadcast_to_admins({"type": "photo_deleted", "photoId": photoId, "userId": userId})
        return True
    return False

# === Diary Entry Services ===
async def create_diary_entry_service(userId: str, entry_data: dict) -> dict:
    try:
        # Validate required fields
        if not userId:
            raise HTTPException(status_code=400, detail="User ID is required")
        if not entry_data.get("content"):
            raise HTTPException(status_code=400, detail="Entry content is required")
        
        # Prepare the data
        entry_data["userId"] = userId
        entry_data["entryId"] = str(uuid.uuid4())
        entry_data["createdAt"] = datetime.now(timezone.utc)

        # Insert into database
        new_entry = await diary_collection.insert_one(entry_data)
        created_entry = await diary_collection.find_one({"_id": new_entry.inserted_id})
        
        if not created_entry:
            raise HTTPException(status_code=500, detail="Failed to create diary entry")
        
        final_entry = diary_entry_helper(created_entry)

        # message = {
        #     "type": "entry_created",
        #     "data": final_entry
        # }

        # # Broadcast to all connected admins
        # await manager.broadcast_to_admins(message)
        
        # # Send an update ONLY to the user who created the entry
        # await manager.send_to_user(message, userId)

        return final_entry
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"Unexpected error creating diary entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create diary entry")

async def update_diary_entry_service(entryId: str, userId: str, entry_data: dict) -> dict:
    """Updates a diary entry and broadcasts the change."""
    update_result = await diary_collection.update_one(
        {"entryId": entryId, "userId": userId}, 
        {"$set": entry_data}
    )
    if update_result.modified_count == 1:
        updated_entry = await diary_collection.find_one({"entryId": entryId})
        final_entry = diary_entry_helper(updated_entry)
        
        # Broadcast the update
        # await manager.broadcast_to_admins({"type": "entry_updated", "data": final_entry})
        # await manager.send_to_user({"type": "entry_updated", "data": final_entry}, userId)
        
        return final_entry
    raise HTTPException(status_code=404, detail=f"Entry {entryId} not found")


async def delete_diary_entry_service(entryId: str, userId: str) -> bool:
    """Deletes a diary entry and broadcasts the change."""
    delete_result = await diary_collection.delete_one({"entryId": entryId, "userId": userId})
    if delete_result.deleted_count == 1:
        # Broadcast the deletion
        # await manager.broadcast_to_admins({"type": "entry_deleted", "entryId": entryId, "userId": userId})
        # await manager.send_to_user({"type": "entry_deleted", "entryId": entryId}, userId)
        return True
    return False

