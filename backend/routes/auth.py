# Authentication and User Management Routes

from fastapi import APIRouter, Depends, HTTPException, status, Request
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
    except Exception:
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


# ==================== USER ACTIVITY TRACKING ====================
#
# CRITICAL INDEPENDENCE RULE:
# - Each user's activity is tracked INDEPENDENTLY
# - Admin actions NEVER affect staff status
# - Heartbeat only updates the authenticated user's own timestamp
# - Activity page is READ-ONLY (no writes)

@router.post("/auth/heartbeat")
async def heartbeat(user: User = Depends(get_current_user)):
    """
    Update the authenticated user's last_activity timestamp.
    
    CRITICAL: This ONLY updates the user who sent the request.
    - Uses JWT token to identify the user
    - Updates ONLY that specific user's last_activity
    - Cannot affect any other user's status
    """
    db = get_db()
    now = get_jakarta_now()
    
    # Update ONLY this user's activity - filter by their unique ID
    await db.users.update_one(
        {'id': user.id},
        {'$set': {
            'last_activity': now.isoformat()
        }}
    )
    
    return {
        'status': 'ok',
        'user_id': user.id,
        'timestamp': now.isoformat()
    }


@router.get("/users/activity")
async def get_user_activity(admin: User = Depends(get_admin_user)):
    """
    Get all users' activity status (Admin/Master Admin only).
    
    CRITICAL: This is READ-ONLY.
    - Only READS timestamps from database
    - CALCULATES status based on timestamps
    - NEVER writes to database
    - Admin viewing this page does NOT affect anyone's status
    """
    db = get_db()
    
    # Import datetime utilities
    from datetime import datetime
    import pytz
    JAKARTA_TZ = pytz.timezone('Asia/Jakarta')
    now = datetime.now(JAKARTA_TZ)
    
    # Status thresholds (in minutes)
    ONLINE_THRESHOLD = 5      # Active within 5 minutes = Online
    IDLE_THRESHOLD = 30       # 5-30 minutes = Idle
    OFFLINE_THRESHOLD = 60    # 60+ minutes = Offline
    
    # Fetch all users (excluding password)
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    activity_list = []
    online_count = 0
    idle_count = 0
    offline_count = 0
    
    for user_doc in users:
        last_activity_str = user_doc.get('last_activity')
        last_logout_str = user_doc.get('last_logout')
        user_role = user_doc.get('role', 'staff')
        
        # Default status is offline
        user_status = 'offline'
        minutes_since_activity = None
        
        # Calculate status based on timestamps
        if last_activity_str:
            try:
                # Parse last_activity timestamp
                last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                if last_activity.tzinfo is None:
                    last_activity = JAKARTA_TZ.localize(last_activity)
                
                minutes_since_activity = (now - last_activity).total_seconds() / 60
                
                # Check if user logged out AFTER their last activity
                logged_out_after_activity = False
                if last_logout_str:
                    try:
                        last_logout = datetime.fromisoformat(last_logout_str.replace('Z', '+00:00'))
                        if last_logout.tzinfo is None:
                            last_logout = JAKARTA_TZ.localize(last_logout)
                        
                        # If logout is after activity, user is offline
                        if last_logout > last_activity:
                            logged_out_after_activity = True
                    except Exception:
                        pass
                
                # Determine status
                if logged_out_after_activity:
                    user_status = 'offline'
                elif minutes_since_activity < ONLINE_THRESHOLD:
                    user_status = 'online'
                elif minutes_since_activity < IDLE_THRESHOLD:
                    user_status = 'idle'
                else:
                    user_status = 'offline'
                    
            except Exception:
                user_status = 'offline'
        
        # Count by status
        if user_status == 'online':
            online_count += 1
        elif user_status == 'idle':
            idle_count += 1
        else:
            offline_count += 1
        
        activity_list.append({
            'id': user_doc.get('id'),
            'name': user_doc.get('name'),
            'email': user_doc.get('email'),
            'role': user_role,
            'status': user_status,
            'minutes_since_activity': int(minutes_since_activity) if minutes_since_activity is not None else None,
            'last_activity': last_activity_str,
            'last_logout': last_logout_str
        })
    
    # Sort: online first, then idle, then offline
    status_order = {'online': 0, 'idle': 1, 'offline': 2}
    activity_list.sort(key=lambda x: (status_order.get(x['status'], 3), x.get('name', '')))
    
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
            'offline_minutes': OFFLINE_THRESHOLD
        },
        'server_time': now.isoformat()
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
    """Delete a user (Admin only - with role hierarchy enforcement)
    
    SYNC: When a user is deleted, all their related data is also cleaned up:
    - Reserved members
    - Bonus check submissions
    - Notifications
    - Attendance records
    - Leave requests
    - Izin records
    """
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
    
    # SYNC: Clean up all related data for this user
    cleanup_results = {}
    
    # Delete reserved members owned by this user
    result = await db.reserved_members.delete_many({'staff_id': user_id})
    cleanup_results['reserved_members'] = result.deleted_count
    
    # Delete bonus check submissions by this user
    result = await db.bonus_check_submissions.delete_many({'staff_id': user_id})
    cleanup_results['bonus_check_submissions'] = result.deleted_count
    
    # Delete notifications for this user
    result = await db.notifications.delete_many({'user_id': user_id})
    cleanup_results['notifications'] = result.deleted_count
    
    # Delete attendance records for this user
    result = await db.attendance_records.delete_many({'staff_id': user_id})
    cleanup_results['attendance_records'] = result.deleted_count
    
    # Delete leave requests by this user
    result = await db.leave_requests.delete_many({'staff_id': user_id})
    cleanup_results['leave_requests'] = result.deleted_count
    
    # Delete izin records by this user
    result = await db.izin_records.delete_many({'staff_id': user_id})
    cleanup_results['izin_records'] = result.deleted_count
    
    # Delete follow-up assignments
    result = await db.customer_records.update_many(
        {'assigned_to': user_id},
        {'$set': {'assigned_to': None, 'assigned_to_name': None, 'status': 'available'}}
    )
    cleanup_results['followup_unassigned'] = result.modified_count
    
    # Finally delete the user
    await db.users.delete_one({'id': user_id})
    
    return {
        'message': 'User deleted successfully',
        'cleanup_results': cleanup_results
    }

@router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    """Get all staff users"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff

# ==================== DATA CLEANUP ENDPOINTS ====================

@router.get("/admin/orphaned-records")
async def get_orphaned_records(admin: User = Depends(get_admin_user)):
    """Get records from users that no longer exist (orphaned data)"""
    db = get_db()
    
    # Get all existing user IDs
    existing_users = await db.users.find({}, {'id': 1, 'name': 1}).to_list(10000)
    existing_user_ids = {u['id'] for u in existing_users}
    existing_user_names = {u['id']: u['name'] for u in existing_users}
    
    # Find unique staff in omset_records
    omset_pipeline = [
        {"$group": {
            "_id": {"staff_id": "$staff_id", "staff_name": "$staff_name"},
            "record_count": {"$sum": 1},
            "total_nominal": {"$sum": "$nominal"}
        }},
        {"$sort": {"record_count": -1}}
    ]
    omset_staff = await db.omset_records.aggregate(omset_pipeline).to_list(1000)
    
    # Find orphaned (staff_id not in existing users)
    orphaned = []
    active = []
    
    for doc in omset_staff:
        staff_id = doc['_id'].get('staff_id')
        staff_name = doc['_id'].get('staff_name', 'Unknown')
        
        entry = {
            'staff_id': staff_id,
            'staff_name': staff_name,
            'record_count': doc['record_count'],
            'total_nominal': doc['total_nominal'],
            'is_orphaned': staff_id not in existing_user_ids
        }
        
        if staff_id not in existing_user_ids:
            orphaned.append(entry)
        else:
            entry['current_user_name'] = existing_user_names.get(staff_id, staff_name)
            active.append(entry)
    
    return {
        'orphaned_staff': orphaned,
        'active_staff': active,
        'total_orphaned_records': sum(o['record_count'] for o in orphaned)
    }

@router.delete("/admin/staff-records/{staff_id}")
async def delete_staff_records(staff_id: str, admin: User = Depends(get_admin_user)):
    """Delete ALL records for a specific staff (use with caution!)"""
    db = get_db()
    
    # Count records first
    omset_count = await db.omset_records.count_documents({'staff_id': staff_id})
    bonanza_count = await db.bonanza_records.count_documents({'staff_id': staff_id})
    memberwd_count = await db.memberwd_records.count_documents({'staff_id': staff_id})
    
    if omset_count == 0 and bonanza_count == 0 and memberwd_count == 0:
        raise HTTPException(status_code=404, detail="No records found for this staff")
    
    # Delete from all relevant collections
    omset_result = await db.omset_records.delete_many({'staff_id': staff_id})
    bonanza_result = await db.bonanza_records.delete_many({'staff_id': staff_id})
    memberwd_result = await db.memberwd_records.delete_many({'staff_id': staff_id})
    
    # Also clean up any attendance records
    attendance_result = await db.attendance_records.delete_many({'staff_id': staff_id})
    totp_result = await db.attendance_totp.delete_many({'staff_id': staff_id})
    
    return {
        'success': True,
        'deleted': {
            'omset_records': omset_result.deleted_count,
            'bonanza_records': bonanza_result.deleted_count,
            'memberwd_records': memberwd_result.deleted_count,
            'attendance_records': attendance_result.deleted_count,
            'totp_setup': totp_result.deleted_count
        },
        'message': f'Deleted all records for staff_id: {staff_id}'
    }

@router.get("/admin/staff-record-summary")
async def get_staff_record_summary(admin: User = Depends(get_admin_user)):
    """Get summary of all staff records for cleanup review"""
    db = get_db()
    
    # Get all users
    all_users = await db.users.find({}, {'_id': 0, 'id': 1, 'name': 1, 'email': 1, 'role': 1}).to_list(10000)
    user_map = {u['id']: u for u in all_users}
    
    # Aggregate omset records by staff
    pipeline = [
        {"$group": {
            "_id": {"staff_id": "$staff_id", "staff_name": "$staff_name"},
            "omset_count": {"$sum": 1},
            "total_nominal": {"$sum": "$nominal"},
            "first_record": {"$min": "$record_date"},
            "last_record": {"$max": "$record_date"}
        }},
        {"$sort": {"omset_count": -1}}
    ]
    
    omset_data = await db.omset_records.aggregate(pipeline).to_list(1000)
    
    result = []
    for doc in omset_data:
        staff_id = doc['_id'].get('staff_id')
        staff_name = doc['_id'].get('staff_name', 'Unknown')
        user = user_map.get(staff_id)
        
        result.append({
            'staff_id': staff_id,
            'staff_name': staff_name,
            'omset_count': doc['omset_count'],
            'total_nominal': doc['total_nominal'],
            'first_record': doc['first_record'],
            'last_record': doc['last_record'],
            'user_exists': user is not None,
            'user_email': user.get('email') if user else None,
            'user_role': user.get('role') if user else None
        })
    
    return {'staff_records': result}
