from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
import jwt
from datetime import timedelta

from models.schemas import User, UserCreate, UserLogin, UserUpdate
from utils.database import db
from utils.timezone import get_jakarta_now
from utils.auth import hash_password, verify_password, JWT_SECRET, JWT_ALGORITHM, security

router = APIRouter()

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': get_jakarta_now() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({'id': payload['user_id']}, {'_id': 0, 'password_hash': 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: User = Depends(get_current_user)):
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Server time endpoint
@router.get("/server-time")
async def get_server_time():
    """Get current server time in Jakarta timezone"""
    jakarta_now = get_jakarta_now()
    return {
        'timezone': 'Asia/Jakarta (UTC+7)',
        'datetime': jakarta_now.isoformat(),
        'date': jakarta_now.strftime('%Y-%m-%d'),
        'time': jakarta_now.strftime('%H:%M:%S'),
        'formatted': jakarta_now.strftime('%A, %d %B %Y %H:%M:%S WIB')
    }

# Auth endpoints
@router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate, admin: User = Depends(get_admin_user)):
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
    user = await db.users.find_one({'email': credentials.email})
    if not user or not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
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
    return user

# User Management Endpoints (Admin only)
@router.get("/users")
async def get_all_users(user: User = Depends(get_admin_user)):
    """Get all users (admin only)"""
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    # Add statistics for each user
    for u in users:
        assigned_count = await db.customer_records.count_documents({'assigned_to': u['id']})
        u['assigned_records'] = assigned_count
        
        omset_count = await db.omset_records.count_documents({'staff_id': u['id']})
        u['omset_records'] = omset_count
        
        # Get last activity
        last_omset = await db.omset_records.find_one(
            {'staff_id': u['id']},
            {'_id': 0, 'created_at': 1},
            sort=[('created_at', -1)]
        )
        u['last_activity'] = last_omset['created_at'] if last_omset else None
    
    return users

@router.put("/users/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate, admin: User = Depends(get_admin_user)):
    """Update a user (admin only)"""
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_fields = {}
    if update_data.name is not None:
        update_fields['name'] = update_data.name
    if update_data.email is not None:
        # Check if email is already taken by another user
        existing = await db.users.find_one({'email': update_data.email, 'id': {'$ne': user_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already taken")
        update_fields['email'] = update_data.email
    if update_data.role is not None:
        update_fields['role'] = update_data.role
    if update_data.password is not None:
        update_fields['password_hash'] = hash_password(update_data.password)
    
    if update_fields:
        await db.users.update_one({'id': user_id}, {'$set': update_fields})
    
    updated_user = await db.users.find_one({'id': user_id}, {'_id': 0, 'password_hash': 0})
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(get_admin_user)):
    """Delete a user (admin only)"""
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user has any assigned records or omset
    assigned_count = await db.customer_records.count_documents({'assigned_to': user_id})
    omset_count = await db.omset_records.count_documents({'staff_id': user_id})
    
    if assigned_count > 0 or omset_count > 0:
        # Don't allow deletion if user has data
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with existing data ({assigned_count} assigned records, {omset_count} OMSET records). Consider deactivating instead."
        )
    
    await db.users.delete_one({'id': user_id})
    return {'message': 'User deleted successfully'}

# Staff users endpoint
@router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
