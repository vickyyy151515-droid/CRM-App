# Shared dependencies and utilities for all route modules

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
import os
import uuid
import jwt
import bcrypt

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')

# Database connection - will be initialized from server.py
db = None

def set_database(database):
    """Set the database instance from server.py"""
    global db
    db = database

def get_db():
    """Get the database instance"""
    return db

# Auth configuration - JWT_SECRET must be set in environment
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")
JWT_ALGORITHM = 'HS256'
security = HTTPBearer()

# ==================== PYDANTIC MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class ProductCreate(BaseModel):
    name: str

# ==================== AUTH DEPENDENCIES ====================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Validate JWT token and return current user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user_data:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_data)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Ensure current user is an admin or master_admin"""
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def get_master_admin_user(user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a master_admin"""
    if user.role != 'master_admin':
        raise HTTPException(status_code=403, detail="Master Admin access required")
    return user

async def get_staff_user(user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a staff member"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Staff access required")
    return user

# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    'master_admin': 3,  # Highest - can manage everyone
    'admin': 2,         # Can manage staff only
    'staff': 1          # Lowest - can only manage self
}

def can_manage_user(manager_role: str, target_role: str) -> bool:
    """Check if manager_role can manage target_role based on hierarchy"""
    return ROLE_HIERARCHY.get(manager_role, 0) > ROLE_HIERARCHY.get(target_role, 0)

# ==================== PASSWORD UTILITIES ====================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
