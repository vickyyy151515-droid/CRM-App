# WebSocket routes for real-time notifications
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List
import json
import asyncio
from datetime import datetime
import jwt
import os

router = APIRouter(tags=["WebSocket"])

JWT_SECRET = os.environ.get('JWT_SECRET', 'crm-jwt-secret-key-2024')

# Connection manager to handle multiple WebSocket connections
class ConnectionManager:
    def __init__(self):
        # Store connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"WebSocket connected for user {user_id}. Total connections: {len(self.active_connections[user_id])}")
        
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"WebSocket disconnected for user {user_id}")
        
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections for a specific user"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message to user {user_id}: {e}")
                    
    async def broadcast_to_admins(self, message: dict):
        """Broadcast message to all admin connections"""
        # We'll need to track admin vs staff connections
        # For now, we send to all connections
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to user {user_id}: {e}")
                    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting: {e}")

# Global connection manager instance
manager = ConnectionManager()

def verify_ws_token(token: str) -> dict:
    """Verify JWT token from WebSocket connection"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint for real-time notifications"""
    
    # Verify token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
        
    user_data = verify_ws_token(token)
    if not user_data:
        await websocket.close(code=4002, reason="Invalid or expired token")
        return
    
    user_id = user_data.get('user_id')
    if not user_id:
        await websocket.close(code=4003, reason="Invalid token payload")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection success message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (heartbeat/ping)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                
                # Handle ping/pong for keepalive
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    # Handle other messages if needed
                    try:
                        message = json.loads(data)
                        if message.get("type") == "ping":
                            await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                    except json.JSONDecodeError:
                        pass
                        
            except asyncio.TimeoutError:
                # Send heartbeat to check if connection is still alive
                try:
                    await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
                except:
                    break
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

# Helper function to send notification via WebSocket (to be used by other routes)
async def send_realtime_notification(user_id: str, notification: dict):
    """Send a real-time notification to a specific user"""
    await manager.send_personal_message({
        "type": "notification",
        "data": notification
    }, user_id)

async def broadcast_notification(notification: dict):
    """Broadcast a notification to all connected users"""
    await manager.broadcast({
        "type": "notification",
        "data": notification
    })
