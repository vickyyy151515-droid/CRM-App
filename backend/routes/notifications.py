# Notification and User Preferences Routes

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Notifications & Preferences"])

# ==================== NOTIFICATION ENDPOINTS ====================

@router.get("/notifications")
async def get_notifications(unread_only: bool = False, limit: int = 50, user: User = Depends(get_current_user)):
    """Get notifications for current user"""
    db = get_db()
    query = {'user_id': user.id}
    if unread_only:
        query['read'] = False
    
    notifications = await db.notifications.find(query, {'_id': 0}).sort('created_at', -1).limit(limit).to_list(limit)
    unread_count = await db.notifications.count_documents({'user_id': user.id, 'read': False})
    
    return {'notifications': notifications, 'unread_count': unread_count}

@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    """Mark a notification as read"""
    db = get_db()
    result = await db.notifications.update_one(
        {'id': notification_id, 'user_id': user.id},
        {'$set': {'read': True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification marked as read'}

@router.patch("/notifications/read-all")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    """Mark all notifications as read for current user"""
    db = get_db()
    result = await db.notifications.update_many(
        {'user_id': user.id, 'read': False},
        {'$set': {'read': True}}
    )
    return {'message': f'{result.modified_count} notifications marked as read'}

@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: User = Depends(get_current_user)):
    """Delete a notification"""
    db = get_db()
    result = await db.notifications.delete_one({'id': notification_id, 'user_id': user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification deleted'}

@router.delete("/notifications")
async def delete_all_notifications(user: User = Depends(get_current_user)):
    """Delete all notifications for current user"""
    db = get_db()
    result = await db.notifications.delete_many({'user_id': user.id})
    return {'message': f'{result.deleted_count} notifications deleted', 'deleted_count': result.deleted_count}

# ==================== ADMIN DATABASE VALIDATION NOTIFICATIONS ====================

@router.get("/notifications/admin/invalid-database")
async def get_admin_invalid_database_notifications(user: User = Depends(get_admin_user)):
    """Get invalid database notifications for admin (DB Bonanza & Member WD)"""
    db = get_db()
    
    # Get unread/unresolved notifications from admin_notifications collection
    notifications = await db.admin_notifications.find(
        {'is_resolved': False},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    # Get summary counts
    bonanza_count = await db.admin_notifications.count_documents({
        'type': 'bonanza_invalid', 
        'is_resolved': False
    })
    memberwd_count = await db.admin_notifications.count_documents({
        'type': 'memberwd_invalid', 
        'is_resolved': False
    })
    
    # Get total invalid records in each category
    bonanza_invalid_total = await db.bonanza_records.count_documents({'validation_status': 'invalid'})
    memberwd_invalid_total = await db.memberwd_records.count_documents({'validation_status': 'invalid'})
    
    return {
        'notifications': notifications,
        'summary': {
            'bonanza_notifications': bonanza_count,
            'memberwd_notifications': memberwd_count,
            'bonanza_invalid_records': bonanza_invalid_total,
            'memberwd_invalid_records': memberwd_invalid_total,
            'total_unresolved': bonanza_count + memberwd_count
        }
    }

@router.patch("/notifications/admin/invalid-database/{notification_id}/read")
async def mark_admin_notification_read(notification_id: str, user: User = Depends(get_admin_user)):
    """Mark an admin notification as read"""
    db = get_db()
    result = await db.admin_notifications.update_one(
        {'id': notification_id},
        {'$set': {'is_read': True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification marked as read'}

@router.delete("/notifications/admin/invalid-database/{notification_id}")
async def delete_admin_notification(notification_id: str, user: User = Depends(get_admin_user)):
    """Delete an admin notification"""
    db = get_db()
    result = await db.admin_notifications.delete_one({'id': notification_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification deleted'}

# Helper function to create notification (can be imported by other modules)
async def create_notification(user_id: str, type: str, title: str, message: str, data: dict = None):
    """Create a notification for a user and send it via WebSocket"""
    db = get_db()
    notification = {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'type': type,
        'title': title,
        'message': message,
        'data': data or {},
        'read': False,
        'created_at': get_jakarta_now().isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Send real-time notification via WebSocket
    try:
        from .websocket import send_realtime_notification
        await send_realtime_notification(user_id, notification)
    except Exception as e:
        print(f"Failed to send real-time notification: {e}")
    
    return notification

# ==================== USER PREFERENCES ENDPOINTS ====================

class WidgetLayoutUpdate(BaseModel):
    widget_order: List[str]

@router.get("/user/preferences/widget-layout")
async def get_widget_layout(user: User = Depends(get_current_user)):
    """Get user's saved widget layout order"""
    db = get_db()
    prefs = await db.user_preferences.find_one({'user_id': user.id, 'type': 'widget_layout'}, {'_id': 0})
    if prefs:
        return {'widget_order': prefs.get('widget_order', [])}
    return {'widget_order': []}

@router.put("/user/preferences/widget-layout")
async def save_widget_layout(layout: WidgetLayoutUpdate, user: User = Depends(get_current_user)):
    """Save user's widget layout order"""
    db = get_db()
    await db.user_preferences.update_one(
        {'user_id': user.id, 'type': 'widget_layout'},
        {'$set': {
            'user_id': user.id,
            'type': 'widget_layout',
            'widget_order': layout.widget_order,
            'updated_at': get_jakarta_now().isoformat()
        }},
        upsert=True
    )
    return {'message': 'Layout saved successfully', 'widget_order': layout.widget_order}

# ==================== SIDEBAR CONFIGURATION ENDPOINTS ====================

class SidebarFolder(BaseModel):
    id: str
    name: str
    items: list
    isOpen: bool = True

class SidebarConfig(BaseModel):
    items: list
    folders: list

@router.get("/user/preferences/sidebar-config")
async def get_sidebar_config(user: User = Depends(get_current_user)):
    """Get user's saved sidebar configuration"""
    db = get_db()
    prefs = await db.user_preferences.find_one(
        {'user_id': user.id, 'type': 'sidebar_config'}, 
        {'_id': 0}
    )
    if prefs:
        return {'config': prefs.get('config', None)}
    return {'config': None}

@router.put("/user/preferences/sidebar-config")
async def save_sidebar_config(config: dict, user: User = Depends(get_current_user)):
    """Save user's sidebar configuration"""
    db = get_db()
    await db.user_preferences.update_one(
        {'user_id': user.id, 'type': 'sidebar_config'},
        {'$set': {
            'user_id': user.id,
            'type': 'sidebar_config',
            'config': config,
            'updated_at': get_jakarta_now().isoformat()
        }},
        upsert=True
    )
    return {'message': 'Sidebar config saved successfully'}

@router.delete("/user/preferences/sidebar-config")
async def reset_sidebar_config(user: User = Depends(get_current_user)):
    """Reset sidebar configuration to default"""
    db = get_db()
    await db.user_preferences.delete_one(
        {'user_id': user.id, 'type': 'sidebar_config'}
    )
    return {'message': 'Sidebar config reset to default'}
