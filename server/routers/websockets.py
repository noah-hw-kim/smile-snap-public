from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from typing import List, Dict
import json
from dependencies import get_current_user, get_current_admin_user, verify_firebase_token
from services.db_services import get_user_by_id

class ConnectionManager:
    def __init__(self):
        # Store all connections with user IDs for easier management
        self.user_connections: Dict[str, WebSocket] = {}
        self.admin_connections: Dict[str, WebSocket] = {}  # Changed to Dict for tracking
    
    async def connect(self, websocket: WebSocket, user_id: str, is_admin: bool):
        await websocket.accept()
        if is_admin:
            self.admin_connections[user_id] = websocket
            print(f"🔴 Admin {user_id} connected. Total admins: {len(self.admin_connections)}")
        else:
            self.user_connections[user_id] = websocket
            print(f"🔴 User {user_id} connected. Total users: {len(self.user_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: str, is_admin: bool):
        try:
            if is_admin:
                if user_id in self.admin_connections:
                    del self.admin_connections[user_id]
                    print(f"🔴 Admin {user_id} disconnected. Remaining admins: {len(self.admin_connections)}")
            else:
                if user_id in self.user_connections:
                    del self.user_connections[user_id]
                    print(f"🔴 User {user_id} disconnected. Remaining users: {len(self.user_connections)}")
        except Exception as e:
            print(f"🔴 Error disconnecting {user_id}: {e}")
    
    async def broadcast_to_admins(self, message: dict):
        print(f"🔴 Broadcasting to {len(self.admin_connections)} admins: {message}")
        dead_connections = []
        
        for admin_id, connection in self.admin_connections.items():
            try:
                await connection.send_text(json.dumps(message))
                print(f"🔴 ✅ Sent to admin {admin_id}")
            except Exception as e:
                print(f"🔴 ❌ Failed to send to admin {admin_id}: {e}")
                dead_connections.append(admin_id)
        
        # Clean up dead connections
        for admin_id in dead_connections:
            del self.admin_connections[admin_id]
    
    async def send_to_user(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_text(json.dumps(message))
                print(f"🔴 ✅ Sent to user {user_id}")
            except Exception as e:
                print(f"🔴 ❌ Failed to send to user {user_id}: {e}")
                del self.user_connections[user_id]
        else:
            print(f"🔴 User {user_id} not connected")

# Create one manager for the whole application
manager = ConnectionManager()

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/updates/{userId}")
async def user_websocket(
    websocket: WebSocket,
    userId: str,
    token: str = Query(None)
):
    if not token:
        await websocket.close(code=1008, reason="No token provided")
        return
    
    try:
        user_data_from_token = verify_firebase_token(token)
        
        if user_data_from_token["userId"] != userId:
            await websocket.close(code=1008, reason="Unauthorized access")
            return
        
        user_from_db = await get_user_by_id(userId)
        if not user_from_db:
            await websocket.close(code=1008, reason="User not found in DB")
            return
            
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as e:
        print(f"🔴 Auth error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    is_admin = user_from_db.get("role") == "admin"
    await manager.connect(websocket, userId, is_admin)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            print(f"🔴 Received from {userId}: {data}")
    except WebSocketDisconnect:
        print(f"🔴 WebSocket disconnect for {userId}")
        manager.disconnect(websocket, userId, is_admin)
    except Exception as e:
        print(f"🔴 WebSocket error for {userId}: {e}")
        manager.disconnect(websocket, userId, is_admin)

@router.websocket("/ws/admin/dashboard")
async def admin_dashboard_websocket(websocket: WebSocket, admin_user: dict = Depends(get_current_admin_user)):
    admin_id = admin_user["userId"]
    await manager.connect(websocket, admin_id, is_admin=True)
    try:
        while True:
            await websocket.receive_text() # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket, admin_id, is_admin=True)