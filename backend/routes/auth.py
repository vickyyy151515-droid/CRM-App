# Authentication and User Management Routes

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from .deps import (
    User, UserCreate, UserLogin, get_db, get_current_user, get_admin_user,
    hash_password, verify_password, create_token, get_jakarta_now
)

router = APIRouter(tags=["Authentication"])

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

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
    """Update a user (Admin only)"""
    db = get_db()
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    """Delete a user (Admin only)"""
    db = get_db()
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.delete_one({'id': user_id})
    return {'message': 'User deleted successfully'}

@router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    """Get all staff users"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
