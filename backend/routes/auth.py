# Authentication and User Management Routes

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .deps import (
    User, UserCreate, UserLogin, get_db, get_current_user, get_admin_user, get_master_admin_user,
    hash_password, verify_password, create_token, get_jakarta_now, can_manage_user, ROLE_HIERARCHY
)

router = APIRouter(tags=["Authentication"])

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

class PageAccessUpdate(BaseModel):
    blocked_pages: List[str] = []

# ==================== AUTH ENDPOINTS ====================

@router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, admin: User = Depends(get_admin_user)):
    """Register a new user (Admin only)"""
    db = get_db()
    existing = await db.users.find_one({'email': user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    
    doc = user.model_dump()
    doc['password_hash'] = password_hash
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user

@router.post("/auth/login")
async def login(credentials: UserLogin):
    """Login and get JWT token"""
    db = get_db()
    user = await db.users.find_one({'email': credentials.email})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update login timestamp and set user as online
    now = get_jakarta_now()
    await db.users.update_one(
        {'id': user['id']},
        {'$set': {
            'last_login': now.isoformat(),
            'last_activity': now.isoformat(),
            'is_online': True
        }}
    )
    
    token = create_token(user['id'], user['email'], user['role'])
    return {
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role']
        }
    }

@router.get("/auth/me", response_model=User)
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info"""
    return user

@router.post("/auth/logout")
async def logout(user: User = Depends(get_current_user)):
    """Logout and update user status"""
    db = get_db()
    now = get_jakarta_now()
    await db.users.update_one(
        {'id': user.id},
        {'$set': {
            'last_logout': now.isoformat(),
            'is_online': False
        }}
    )
    return {'message': 'Logged out successfully'}

@router.post("/auth/heartbeat")
async def heartbeat(user: User = Depends(get_current_user)):
    """Update user's last activity timestamp (call this periodically from frontend)"""
    db = get_db()
    now = get_jakarta_now()
    await db.users.update_one(
        {'id': user.id},
        {'$set': {
            'last_activity': now.isoformat(),
            'is_online': True
        }}
    )
    return {'status': 'ok', 'timestamp': now.isoformat()}

# ==================== USER ACTIVITY MONITORING ====================

@router.get("/users/activity")
async def get_user_activity(admin: User = Depends(get_admin_user)):
    """Get all users' activity status (Admin only)"""
    db = get_db()
    from datetime import datetime, timedelta
    import pytz
    
    JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
    now = datetime.now(JAKARTA_TZ)
    
    # Consider user idle if no activity for 5 minutes
    IDLE_THRESHOLD_MINUTES = 5
    # Consider user offline if no activity for 30 minutes
    OFFLINE_THRESHOLD_MINUTES = 30
    
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    activity_list = []
    online_count = 0
    idle_count = 0
    offline_count = 0
    
    for user in users:
        last_activity_str = user.get('last_activity')
        last_login_str = user.get('last_login')
        last_logout_str = user.get('last_logout')
        is_online = user.get('is_online', False)
        
        status = 'offline'
        idle_minutes = None
        
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                if last_activity.tzinfo is None:
                    last_activity = JAKARTA_TZ.localize(last_activity)
                
                minutes_since_activity = (now - last_activity).total_seconds() / 60
                
                if minutes_since_activity < IDLE_THRESHOLD_MINUTES and is_online:
                    status = 'online'
                    online_count += 1
                elif minutes_since_activity < OFFLINE_THRESHOLD_MINUTES and is_online:
                    status = 'idle'
                    idle_minutes = int(minutes_since_activity)
                    idle_count += 1
                else:
                    status = 'offline'
                    offline_count += 1
                    # Auto-update is_online to false if user has been inactive too long
                    if is_online:
                        await db.users.update_one({'id': user['id']}, {'$set': {'is_online': False}})
            except:
                status = 'offline'
                offline_count += 1
        else:
            offline_count += 1
        
        activity_list.append({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role'],
            'status': status,
            'idle_minutes': idle_minutes,
            'last_login': last_login_str,
            'last_activity': last_activity_str,
            'last_logout': last_logout_str
        })
    
    # Sort: online first, then idle, then offline
    status_order = {'online': 0, 'idle': 1, 'offline': 2}
    activity_list.sort(key=lambda x: (status_order.get(x['status'], 3), x['name']))
    
    return {
        'users': activity_list,
        'summary': {
            'total': len(users),
            'online': online_count,
            'idle': idle_count,
            'offline': offline_count
        },
        'thresholds': {
            'idle_minutes': IDLE_THRESHOLD_MINUTES,
            'offline_minutes': OFFLINE_THRESHOLD_MINUTES
        }
    }

# ==================== USER MANAGEMENT ENDPOINTS ====================

@router.get("/users")
async def get_all_users(admin: User = Depends(get_admin_user)):
    """Get all users (Admin only)"""
    db = get_db()
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return users

@router.get("/users/{user_id}")
async def get_user(user_id: str, admin: User = Depends(get_admin_user)):
    """Get a specific user (Admin only)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'password_hash': 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}")
async def update_user(user_id: str, user_data: UserUpdate, admin: User = Depends(get_admin_user)):
    """Update a user (Admin only - with role hierarchy enforcement)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Role hierarchy check - admins can only edit staff, master_admin can edit anyone
    target_role = user.get('role', 'staff')
    if not can_manage_user(admin.role, target_role):
        raise HTTPException(
            status_code=403, 
            detail=f"You don't have permission to edit {target_role} users"
        )
    
    # Prevent role escalation - can't promote someone to a role higher or equal to yours
    if user_data.role and user_data.role != target_role:
        new_role_level = ROLE_HIERARCHY.get(user_data.role, 0)
        admin_role_level = ROLE_HIERARCHY.get(admin.role, 0)
        if new_role_level >= admin_role_level:
            raise HTTPException(
                status_code=403,
                detail=f"You cannot promote users to {user_data.role} role"
            )
    
    update_data = {}
    if user_data.name:
        update_data['name'] = user_data.name
    if user_data.email:
        existing = await db.users.find_one({'email': user_data.email, 'id': {'$ne': user_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data['email'] = user_data.email
    if user_data.password:
        update_data['password_hash'] = hash_password(user_data.password)
    if user_data.role:
        update_data['role'] = user_data.role
    
    if update_data:
        await db.users.update_one({'id': user_id}, {'$set': update_data})
    
    updated_user = await db.users.find_one({'id': user_id}, {'_id': 0, 'password_hash': 0})
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(get_admin_user)):
    """Delete a user (Admin only - with role hierarchy enforcement)"""
    db = get_db()
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Role hierarchy check
    target_role = user.get('role', 'staff')
    if not can_manage_user(admin.role, target_role):
        raise HTTPException(
            status_code=403, 
            detail=f"You don't have permission to delete {target_role} users"
        )
    
    await db.users.delete_one({'id': user_id})
    return {'message': 'User deleted successfully'}

# ==================== PAGE ACCESS CONTROL (Master Admin Only) ====================

@router.put("/users/{user_id}/page-access")
async def update_user_page_access(
    user_id: str, 
    access_data: PageAccessUpdate, 
    master_admin: User = Depends(get_master_admin_user)
):
    """Update blocked pages for an admin user (Master Admin only)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Can only set page access for admin users
    if user.get('role') != 'admin':
        raise HTTPException(
            status_code=400, 
            detail="Page access control is only available for admin users"
        )
    
    await db.users.update_one(
        {'id': user_id},
        {'$set': {'blocked_pages': access_data.blocked_pages}}
    )
    
    return {'message': 'Page access updated successfully', 'blocked_pages': access_data.blocked_pages}

@router.get("/users/{user_id}/page-access")
async def get_user_page_access(user_id: str, admin: User = Depends(get_admin_user)):
    """Get blocked pages for a user"""
    db = get_db()
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'blocked_pages': 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {'blocked_pages': user.get('blocked_pages', [])}

@router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    """Get all staff users"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
