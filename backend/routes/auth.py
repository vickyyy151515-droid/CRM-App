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

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

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
    
    try:
        user = await db.users.find_one({'email': credentials.email})
    except Exception as e:
        # Database connection error
        raise HTTPException(
            status_code=503, 
            detail="Service temporarily unavailable. Please try again in a moment."
        )
    
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update login timestamp and set user as online
    now = get_jakarta_now()
    try:
        await db.users.update_one(
            {'id': user['id']},
            {'$set': {
                'last_login': now.isoformat(),
                'last_activity': now.isoformat(),
                'is_online': True
            }}
        )
    except Exception as e:
        # Log but don't fail login if we can't update timestamp
        print(f"Warning: Could not update login timestamp: {e}")
    
    token = create_token(user['id'], user['email'], user['role'])
    return {
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'blocked_pages': user.get('blocked_pages', [])
        }
    }

@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info including blocked_pages - READ ONLY, no activity update"""
    db = get_db()
    
    # DO NOT update last_activity here - only heartbeat should update activity
    # This prevents issues where viewing the page updates all users
    
    user_data = await db.users.find_one({'id': user.id}, {'_id': 0, 'password_hash': 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        'id': user_data['id'],
        'email': user_data['email'],
        'name': user_data['name'],
        'role': user_data['role'],
        'blocked_pages': user_data.get('blocked_pages', []),
        'created_at': user_data.get('created_at')
    }

@router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, user: User = Depends(get_current_user)):
    """Change current user's password"""
    db = get_db()
    
    # Get current user with password hash
    current_user = await db.users.find_one({'id': user.id})
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(request.current_password, current_user['password_hash']):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    
    # Update password
    new_hash = hash_password(request.new_password)
    await db.users.update_one(
        {'id': user.id},
        {'$set': {'password_hash': new_hash}}
    )
    
    return {'message': 'Password changed successfully'}

@router.put("/auth/profile")
async def update_profile(request: UpdateProfileRequest, user: User = Depends(get_current_user)):
    """Update current user's profile (name, email)"""
    db = get_db()
    
    update_data = {}
    
    if request.name:
        update_data['name'] = request.name
    
    if request.email:
        # Check if email is already taken by another user
        existing = await db.users.find_one({'email': request.email, 'id': {'$ne': user.id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data['email'] = request.email
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    await db.users.update_one({'id': user.id}, {'$set': update_data})
    
    # Return updated user
    updated_user = await db.users.find_one({'id': user.id}, {'_id': 0, 'password_hash': 0})
    return {
        'message': 'Profile updated successfully',
        'user': {
            'id': updated_user['id'],
            'email': updated_user['email'],
            'name': updated_user['name'],
            'role': updated_user['role']
        }
    }

@router.post("/auth/logout")
async def logout(user: User = Depends(get_current_user)):
    """Logout and update user status"""
    db = get_db()
    now = get_jakarta_now()
    await db.users.update_one(
        {'id': user.id},
        {'$set': {
            'last_logout': now.isoformat(),
        }}
    )
    return {'message': 'Logged out successfully'}

class BeaconLogout(BaseModel):
    token: str

@router.post("/auth/logout-beacon")
async def logout_beacon(request: Request):
    """
    Logout endpoint for browser beacon (when tab/browser closes).
    Uses raw token since we can't use normal auth flow for beacon requests.
    """
    db = get_db()
    now = get_jakarta_now()
    
    try:
        # Parse the beacon body
        body = await request.json()
        token = body.get('token')
        
        if not token:
            return {'status': 'no_token'}
        
        # Decode the token to get user ID
        import jwt
        import os
        payload = jwt.decode(token, os.environ.get('JWT_SECRET', 'secret'), algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        if user_id:
            await db.users.update_one(
                {'id': user_id},
                {'$set': {
                    'last_logout': now.isoformat(),
                }}
            )
            return {'status': 'logged_out', 'user_id': user_id}
    except Exception as e:
        # Silently fail - beacon requests shouldn't cause errors
        return {'status': 'error', 'message': str(e)}

@router.post("/auth/heartbeat")
async def heartbeat(user: User = Depends(get_current_user)):
    """Update user's last activity timestamp - ONLY updates the authenticated user"""
    db = get_db()
    now = get_jakarta_now()
    
    # CRITICAL: Validate user ID exists and is not empty
    if not user.id or not isinstance(user.id, str) or len(user.id) < 10:
        raise HTTPException(status_code=400, detail=f"Invalid user ID: {user.id}")
    
    # Double-check: Verify this user exists with this exact ID
    existing_user = await db.users.find_one({'id': user.id}, {'_id': 0, 'id': 1, 'email': 1})
    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User not found: {user.id}")
    
    # Update ONLY this specific user's activity using their unique ID
    result = await db.users.update_one(
        {'id': user.id},  # Filter by exact user ID string
        {'$set': {
            'last_activity': now.isoformat(),
            'is_online': True
        }}
    )
    
    # Verify exactly 1 document was matched
    if result.matched_count != 1:
        print(f"CRITICAL BUG: Heartbeat matched {result.matched_count} docs for user_id={user.id}, email={user.email}")
        raise HTTPException(status_code=500, detail=f"Activity update error: matched {result.matched_count} users")
    
    return {
        'status': 'ok', 
        'timestamp': now.isoformat(), 
        'user_id': user.id,
        'user_email': user.email
    }

@router.get("/auth/session-status")
async def get_session_status(user: User = Depends(get_current_user)):
    """Check session status and return time until auto-logout (staff only)"""
    db = get_db()
    from datetime import datetime
    import pytz
    
    JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
    now = datetime.now(JAKARTA_TZ)
    
    # Auto-logout after 1 hour (60 minutes) of inactivity - STAFF ONLY
    AUTO_LOGOUT_MINUTES = 60
    
    user_doc = await db.users.find_one({'id': user.id})
    if not user_doc:
        return {'valid': False, 'reason': 'User not found'}
    
    # Admin/Master Admin don't have auto-logout
    if user.role in ['admin', 'master_admin']:
        return {'valid': True, 'auto_logout_enabled': False, 'role': user.role}
    
    last_activity_str = user_doc.get('last_activity')
    if not last_activity_str:
        return {'valid': True, 'minutes_remaining': AUTO_LOGOUT_MINUTES, 'auto_logout_enabled': True}
    
    try:
        last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
        if last_activity.tzinfo is None:
            last_activity = JAKARTA_TZ.localize(last_activity)
        
        minutes_since_activity = (now - last_activity).total_seconds() / 60
        minutes_remaining = max(0, AUTO_LOGOUT_MINUTES - minutes_since_activity)
        
        if minutes_since_activity >= AUTO_LOGOUT_MINUTES:
            # Session expired due to inactivity - update user status
            await db.users.update_one(
                {'id': user.id},
                {
                    '$set': {
                        'is_online': False,
                        'last_logout': now.isoformat(),
                        'logout_reason': 'auto_logout_inactivity'
                    }
                }
            )
            return {
                'valid': False,
                'reason': 'Session expired due to inactivity',
                'minutes_inactive': int(minutes_since_activity),
                'auto_logout_enabled': True
            }
        
        return {
            'valid': True,
            'minutes_remaining': int(minutes_remaining),
            'minutes_inactive': int(minutes_since_activity),
            'auto_logout_enabled': True
        }
    except Exception as e:
        return {'valid': True, 'minutes_remaining': AUTO_LOGOUT_MINUTES, 'error': str(e), 'auto_logout_enabled': True}

# ==================== USER ACTIVITY MONITORING (REBUILT) ====================
# 
# IMPORTANT: Activity tracking works as follows:
# 1. Frontend sends heartbeat on user interaction (click, scroll, keypress)
# 2. Heartbeat updates ONLY the authenticated user's last_activity timestamp
# 3. This endpoint is READ-ONLY - it calculates status from timestamps, never writes
#
# Status thresholds:
# - Online: activity within 5 minutes
# - Idle: no activity for 5-30 minutes  
# - Offline: no activity for 30+ minutes
#
# Staff auto-logout: 60 minutes of inactivity

@router.get("/users/activity")
async def get_user_activity(admin: User = Depends(get_admin_user)):
    """
    Get all users' activity status (Admin only).
    This is READ-ONLY - status is calculated from timestamps, no updates happen here.
    """
    db = get_db()
    from datetime import datetime
    import pytz
    
    JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
    now = datetime.now(JAKARTA_TZ)
    
    # Thresholds (in minutes)
    ONLINE_THRESHOLD = 5      # Active within 5 minutes = online
    IDLE_THRESHOLD = 30       # 5-30 minutes = idle
    # > 30 minutes = offline
    STAFF_AUTO_LOGOUT = 60    # Staff auto-logout after 60 minutes
    
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    activity_list = []
    online_count = 0
    idle_count = 0
    offline_count = 0
    
    for user in users:
        last_activity_str = user.get('last_activity')
        last_logout_str = user.get('last_logout')
        user_role = user.get('role', 'staff')
        
        status = 'offline'
        minutes_since_activity = None
        
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                if last_activity.tzinfo is None:
                    last_activity = JAKARTA_TZ.localize(last_activity)
                
                minutes_since_activity = (now - last_activity).total_seconds() / 60
                
                # Check if user explicitly logged out after their last activity
                explicitly_logged_out = False
                if last_logout_str:
                    try:
                        last_logout = datetime.fromisoformat(last_logout_str.replace('Z', '+00:00'))
                        if last_logout.tzinfo is None:
                            last_logout = JAKARTA_TZ.localize(last_logout)
                        if last_logout > last_activity:
                            explicitly_logged_out = True
                    except:
                        pass
                
                # For staff, consider them offline if past auto-logout threshold
                staff_session_expired = (user_role == 'staff' and minutes_since_activity >= STAFF_AUTO_LOGOUT)
                
                # Determine status (READ-ONLY calculation)
                if explicitly_logged_out or staff_session_expired:
                    status = 'offline'
                elif minutes_since_activity < ONLINE_THRESHOLD:
                    status = 'online'
                elif minutes_since_activity < IDLE_THRESHOLD:
                    status = 'idle'
                else:
                    status = 'offline'
                    
            except Exception as e:
                status = 'offline'
        
        # Count by status
        if status == 'online':
            online_count += 1
        elif status == 'idle':
            idle_count += 1
        else:
            offline_count += 1
        
        activity_list.append({
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user_role,
            'status': status,
            'minutes_since_activity': int(minutes_since_activity) if minutes_since_activity is not None else None,
            'last_activity': last_activity_str,
            'last_login': user.get('last_login'),
            'last_logout': last_logout_str
        })
    
    # Sort: online first, then idle, then offline, then by name
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
            'online_minutes': ONLINE_THRESHOLD,
            'idle_minutes': IDLE_THRESHOLD,
            'staff_auto_logout_minutes': STAFF_AUTO_LOGOUT
        },
        'server_time': now.isoformat()
    }

@router.post("/auth/reset-activity")
async def reset_activity(admin: User = Depends(get_admin_user)):
    """Reset all users' activity timestamps (Admin accessible) - Use to fix corrupted data"""
    db = get_db()
    
    result = await db.users.update_many(
        {},
        {
            '$unset': {
                'last_activity': '',
                'last_logout': '',
                'logout_reason': ''
            }
        }
    )
    
    return {
        'status': 'ok',
        'message': f'Reset activity for {result.modified_count} users. All will show offline until they interact.',
        'modified_count': result.modified_count
    }

# ==================== EMERGENCY PASSWORD RESET ====================

class EmergencyPasswordReset(BaseModel):
    email: str
    new_password: str
    secret_key: str

@router.post("/auth/emergency-reset-password")
async def emergency_reset_password(data: EmergencyPasswordReset):
    """
    Emergency password reset - requires secret key for security.
    Use this only when locked out of your account.
    """
    db = get_db()
    
    # Secret key must match JWT_SECRET for security
    import os
    expected_secret = os.environ.get('JWT_SECRET', '')[:16]  # First 16 chars of JWT secret
    
    if not data.secret_key or data.secret_key != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    # Find user
    user = await db.users.find_one({'email': data.email})
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {data.email}")
    
    # Validate new password
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Update password
    new_hash = hash_password(data.new_password)
    await db.users.update_one(
        {'email': data.email},
        {'$set': {'password_hash': new_hash}}
    )
    
    return {
        'status': 'ok',
        'message': f'Password reset successful for {data.email}',
        'user_role': user.get('role')
    }

# ==================== USER MANAGEMENT ENDPOINTS ====================

@router.get("/users")
async def get_all_users(admin: User = Depends(get_admin_user)):
    """Get all users (Admin only)"""
    db = get_db()
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return users

# PAGE ACCESS ROUTES - Using query parameter to avoid path conflicts
@router.get("/page-access")
async def get_page_access(user_id: str, admin: User = Depends(get_admin_user)):
    """Get blocked pages for a user (alternative endpoint)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'blocked_pages': 1, 'role': 1, 'email': 1})
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")
    
    return {'blocked_pages': user.get('blocked_pages', []), 'user_id': user_id}

@router.put("/page-access")
async def update_page_access(
    user_id: str,
    access_data: PageAccessUpdate, 
    master_admin: User = Depends(get_master_admin_user)
):
    """Update blocked pages for an admin user (alternative endpoint)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found with id: {user_id}")
    
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

# Legacy routes kept for backwards compatibility
@router.get("/users/{user_id}/page-access")
async def get_user_page_access(user_id: str, admin: User = Depends(get_admin_user)):
    """Get blocked pages for a user"""
    db = get_db()
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'blocked_pages': 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {'blocked_pages': user.get('blocked_pages', [])}

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

@router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    """Get all staff users"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
