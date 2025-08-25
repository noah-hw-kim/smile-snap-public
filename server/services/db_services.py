import uuid
from fastapi import HTTPException
from database import user_collection, diary_collection, diary_entry_helper, photo_collection, user_helper, photo_helper
from datetime import datetime, timezone
from firebase_admin import auth
# from routers.websockets import manager
from google.cloud import storage
from config import bucket
import asyncio
import logging

logger = logging.getLogger(__name__)

# === User Services ===
async def create_user_services(user_data: dict) -> dict:
    """
    Creates a user in Firebase Auth and a profile in MongoDB.
    """
    try:
        new_firebase_user = auth.create_user(
            email=user_data["email"],
            password=user_data["password"],
            display_name=user_data.get("displayName")
        )
        
        user_profile = {
            "userId": new_firebase_user.uid,
            "email": user_data["email"],
            "displayName": user_data.get("displayName"),
            "role": user_data.get("role", "user"),
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
    Delete user and all their data from GCS, MongoDB, and Firebase Auth
    """
    try:
        logger.info(f"Starting deletion for user {userId}")
        
        # Step 1: Get all user's photos and delete from GCS
        photos_cursor = photo_collection.find({"userId": userId})
        photos = await photos_cursor.to_list(None)
        
        if photos:            
            for photo in photos:
                try:
                    if photo.get("filePath"):
                        blob = bucket.blob(photo["filePath"])
                        if blob.exists():
                            blob.delete()
                            logger.info(f"Deleted {photo['filePath']} from GCS")
                except Exception as e:
                    logger.error(f"Failed to delete photo {photo.get('photoId')} from GCS: {e}")
                    # Continue with other photos
        
        # Step 2: Delete all user data from MongoDB
        photos_deleted = await photo_collection.delete_many({"userId": userId})
        entries_deleted = await diary_collection.delete_many({"userId": userId})
        user_deleted = await user_collection.delete_one({"userId": userId})
        
        # Step 3: Delete from Firebase Auth
        await asyncio.to_thread(auth.delete_user, userId)
        
        # Step 4: Broadcast to admins
        # await manager.broadcast_to_admins({
        #     "type": "user_deleted",
        #     "userId": userId,
        #     "photos_deleted": photos_deleted.deleted_count,
        #     "entries_deleted": entries_deleted.deleted_count
        # })
        
        # logger.info(f"Successfully deleted user {userId}: {photos_deleted.deleted_count} photos, {entries_deleted.deleted_count} entries")
        return user_deleted.deleted_count == 1
        
    except Exception as e:
        logger.error(f"Error deleting user {userId}: {str(e)}")
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
    """Deletes a photo from GCS and MongoDB, then broadcasts the change."""
    # print("start delete the photo")
    
    photo_doc = await get_photo_by_id(photoId, userId)
    # print("photo_doc found in mongodb")

    file_path_to_delete = photo_doc["filePath"]

    # TODO: Add logic here to delete the file from GCS using photo_doc["filePath"]
    try:
        blob = bucket.blob(file_path_to_delete)
        await asyncio.to_thread(blob.delete) # Use to_thread for sync call
        print(f"Successfully deleted {file_path_to_delete} from GCS.")
    except Exception as e:
        print(f"Could not delete from GCS: {e}") # Log error but continue
    
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

