from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, status, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
import io

# ==================== CONFIGURATION ====================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')

# Database connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# App initialization
app = FastAPI(title="CRM Pro API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Auth configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
security = HTTPBearer()

# File upload directory
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

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

class Database(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str
    file_size: int
    description: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    file_path: str
    preview_data: Optional[dict] = None
    total_records: int = 0

class CustomerRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    product_id: str
    product_name: str
    row_number: int
    row_data: dict
    status: str = "available"
    whatsapp_status: Optional[str] = None
    whatsapp_status_updated_at: Optional[datetime] = None
    respond_status: Optional[str] = None
    respond_status_updated_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    request_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class WhatsAppStatusUpdate(BaseModel):
    whatsapp_status: str

class RespondStatusUpdate(BaseModel):
    respond_status: str

class ReservedMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str
    product_id: str
    product_name: str
    staff_id: str
    staff_name: str
    status: str = "approved"
    created_by: str
    created_by_name: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None

class ReservedMemberCreate(BaseModel):
    customer_name: str
    product_id: str
    staff_id: Optional[str] = None

# OMSET CRM Models
class OmsetRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str
    staff_id: str
    staff_name: str
    record_date: str  # YYYY-MM-DD format
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    depo_total: float
    keterangan: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    updated_at: Optional[datetime] = None

class OmsetRecordCreate(BaseModel):
    product_id: str
    record_date: str
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    keterangan: Optional[str] = None

class OmsetRecordUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    nominal: Optional[float] = None
    depo_kelipatan: Optional[float] = None
    keterangan: Optional[str] = None

# DB Bonanza Models
class BonanzaDatabase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    filename: str
    file_type: str
    total_records: int = 0
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class BonanzaRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    row_number: int
    row_data: dict
    status: str = "available"  # available, assigned
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    assigned_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class BonanzaAssignment(BaseModel):
    record_ids: List[str]
    staff_id: str

class DatabaseCreate(BaseModel):
    description: Optional[str] = None
    product_id: str

class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    record_ids: List[str]
    record_count: int
    requested_by: str
    requested_by_name: str
    status: str = "pending"
    requested_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_by_name: Optional[str] = None

class DownloadRequestCreate(BaseModel):
    database_id: str
    record_count: int

class DownloadHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    database_id: str
    database_name: str
    downloaded_by: str
    downloaded_by_name: str
    downloaded_at: datetime = Field(default_factory=lambda: get_jakarta_now())

# Notification Model
class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Target user
    type: str  # request_approved, request_rejected, records_assigned, new_reserved_request
    title: str
    message: str
    data: Optional[dict] = None  # Additional data like request_id, record_count, etc.
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

# Bulk Operation Models
class BulkRequestAction(BaseModel):
    request_ids: List[str]
    action: str  # approve or reject

class BulkStatusUpdate(BaseModel):
    record_ids: List[str]
    whatsapp_status: Optional[str] = None
    respond_status: Optional[str] = None

class BulkDeleteRecords(BaseModel):
    record_ids: List[str]

class DatabaseProductUpdate(BaseModel):
    product_id: str

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

@api_router.get("/server-time")
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

def parse_file_preview(file_path: str, file_type: str) -> dict:
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path, nrows=10)
        else:
            df = pd.read_excel(file_path, nrows=10)
        
        return {
            'columns': df.columns.tolist(),
            'rows': df.head(5).values.tolist(),
            'total_rows': len(df)
        }
    except Exception as e:
        return {'error': str(e)}

def parse_file_to_records(file_path: str, file_type: str) -> tuple:
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        records = []
        for idx, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    row_dict[str(col)] = None
                else:
                    row_dict[str(col)] = str(val)
            records.append(row_dict)
        
        preview = {
            'columns': df.columns.tolist(),
            'rows': df.head(5).values.tolist(),
            'total_rows': len(df)
        }
        
        return records, preview
    except Exception as e:
        return [], {'error': str(e)}

@api_router.post("/auth/register", response_model=User)
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

@api_router.post("/auth/login")
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

@api_router.get("/auth/me", response_model=User)
async def get_me(user: User = Depends(get_current_user)):
    return user

# User Management Endpoints (Admin only)
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

@api_router.get("/users")
async def get_all_users(user: User = Depends(get_admin_user)):
    """Get all users (admin only)"""
    users = await db.users.find({}, {'_id': 0, 'password': 0}).sort('created_at', -1).to_list(1000)
    
    # Get activity stats for each user
    for u in users:
        # Count assigned records
        assigned_count = await db.customer_records.count_documents({'assigned_to': u['id']})
        u['assigned_records'] = assigned_count
        
        # Count OMSET records
        omset_count = await db.omset_records.count_documents({'staff_id': u['id']})
        u['omset_records'] = omset_count
        
        # Get last activity (last OMSET record creation)
        last_omset = await db.omset_records.find_one(
            {'staff_id': u['id']},
            {'_id': 0, 'created_at': 1},
            sort=[('created_at', -1)]
        )
        u['last_activity'] = last_omset['created_at'] if last_omset else None
    
    return users

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user_data: UserUpdate, user: User = Depends(get_admin_user)):
    """Update a user (admin only)"""
    existing = await db.users.find_one({'id': user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from modifying themselves in certain ways
    if user_id == user.id and user_data.role and user_data.role != 'admin':
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    update_data = {}
    
    if user_data.name:
        update_data['name'] = user_data.name
    
    if user_data.email:
        # Check if email is already taken by another user
        email_exists = await db.users.find_one({'email': user_data.email, 'id': {'$ne': user_id}})
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_data['email'] = user_data.email
    
    if user_data.password:
        update_data['password_hash'] = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    if user_data.role:
        update_data['role'] = user_data.role
    
    if update_data:
        await db.users.update_one({'id': user_id}, {'$set': update_data})
    
    updated_user = await db.users.find_one({'id': user_id}, {'_id': 0, 'password': 0})
    return updated_user

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: User = Depends(get_admin_user)):
    """Delete a user (admin only)"""
    existing = await db.users.find_one({'id': user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user has assigned records
    assigned_count = await db.customer_records.count_documents({'assigned_to': user_id})
    omset_count = await db.omset_records.count_documents({'staff_id': user_id})
    
    if assigned_count > 0 or omset_count > 0:
        # Instead of deleting, we could mark as inactive, but for now return error
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete user with existing data ({assigned_count} assigned records, {omset_count} OMSET records). Consider deactivating instead."
        )
    
    await db.users.delete_one({'id': user_id})
    return {"message": "User deleted successfully"}

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, user: User = Depends(get_admin_user)):
    existing = await db.products.find_one({'name': product_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    product = Product(name=product_data.name)
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.products.insert_one(doc)
    return product

@api_router.get("/products", response_model=List[Product])
async def get_products(user: User = Depends(get_current_user)):
    products = await db.products.find({}, {'_id': 0}).sort('name', 1).to_list(1000)
    
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return products

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: User = Depends(get_admin_user)):
    product = await db.products.find_one({'id': product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    databases_count = await db.databases.count_documents({'product_id': product_id})
    if databases_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete product with {databases_count} associated databases")
    
    await db.products.delete_one({'id': product_id})
    return {'message': 'Product deleted successfully'}

@api_router.post("/databases", response_model=Database)
async def upload_database(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are allowed")
    
    if not product_id:
        raise HTTPException(status_code=400, detail="Product ID is required")
    
    product = await db.products.find_one({'id': product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    file_type = 'csv' if file.filename.endswith('.csv') else 'xlsx'
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    
    records_data, preview_data = parse_file_to_records(str(file_path), file_type)
    
    database = Database(
        filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        description=description,
        product_id=product_id,
        product_name=product['name'],
        uploaded_by=user.id,
        uploaded_by_name=user.name,
        file_path=str(file_path),
        preview_data=preview_data,
        total_records=len(records_data)
    )
    
    doc = database.model_dump()
    doc['uploaded_at'] = doc['uploaded_at'].isoformat()
    
    await db.databases.insert_one(doc)
    
    customer_records = []
    for idx, row_data in enumerate(records_data, start=1):
        record = CustomerRecord(
            database_id=database.id,
            database_name=database.filename,
            product_id=product_id,
            product_name=product['name'],
            row_number=idx,
            row_data=row_data
        )
        rec_doc = record.model_dump()
        rec_doc['created_at'] = rec_doc['created_at'].isoformat()
        customer_records.append(rec_doc)
    
    if customer_records:
        await db.customer_records.insert_many(customer_records)
    
    return database

@api_router.get("/databases", response_model=List[Database])
async def get_databases(search: Optional[str] = None, product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    query = {}
    if search:
        query['$or'] = [
            {'filename': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    if product_id:
        query['product_id'] = product_id
    
    databases = await db.databases.find(query, {'_id': 0}).sort('uploaded_at', -1).to_list(1000)
    
    for db_item in databases:
        if isinstance(db_item['uploaded_at'], str):
            db_item['uploaded_at'] = datetime.fromisoformat(db_item['uploaded_at'])
    
    return databases

@api_router.get("/databases/{database_id}", response_model=Database)
async def get_database(database_id: str, user: User = Depends(get_current_user)):
    database = await db.databases.find_one({'id': database_id}, {'_id': 0})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if isinstance(database['uploaded_at'], str):
        database['uploaded_at'] = datetime.fromisoformat(database['uploaded_at'])
    
    return Database(**database)

@api_router.delete("/databases/{database_id}")
async def delete_database(database_id: str, user: User = Depends(get_admin_user)):
    database = await db.databases.find_one({'id': database_id})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if os.path.exists(database['file_path']):
        os.remove(database['file_path'])
    
    await db.databases.delete_one({'id': database_id})
    await db.customer_records.delete_many({'database_id': database_id})
    await db.download_requests.delete_many({'database_id': database_id})
    
    return {'message': 'Database deleted successfully'}

@api_router.get("/databases/{database_id}/records", response_model=List[CustomerRecord])
async def get_database_records(database_id: str, status: Optional[str] = None, user: User = Depends(get_current_user)):
    database = await db.databases.find_one({'id': database_id})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    query = {'database_id': database_id}
    if status:
        query['status'] = status
    
    records = await db.customer_records.find(query, {'_id': 0}).sort('row_number', 1).to_list(10000)
    
    for record in records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        if record.get('assigned_at') and isinstance(record['assigned_at'], str):
            record['assigned_at'] = datetime.fromisoformat(record['assigned_at'])
    
    return records

@api_router.post("/download-requests", response_model=DownloadRequest)
async def create_download_request(request_data: DownloadRequestCreate, user: User = Depends(get_current_user)):
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can request records")
    
    database = await db.databases.find_one({'id': request_data.database_id})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if request_data.record_count <= 0:
        raise HTTPException(status_code=400, detail="Record count must be greater than 0")
    
    available_records = await db.customer_records.find(
        {'database_id': request_data.database_id, 'status': 'available'},
        {'_id': 0}
    ).sort('row_number', 1).to_list(request_data.record_count)
    
    if len(available_records) == 0:
        raise HTTPException(status_code=400, detail="No available records in this database")
    
    if len(available_records) < request_data.record_count:
        raise HTTPException(
            status_code=400, 
            detail=f"Only {len(available_records)} records available, but you requested {request_data.record_count}"
        )
    
    record_ids = [record['id'] for record in available_records]
    
    request = DownloadRequest(
        database_id=request_data.database_id,
        database_name=database['filename'],
        record_ids=record_ids,
        record_count=len(record_ids),
        requested_by=user.id,
        requested_by_name=user.name
    )
    
    doc = request.model_dump()
    doc['requested_at'] = doc['requested_at'].isoformat()
    
    await db.download_requests.insert_one(doc)
    
    for record_id in record_ids:
        await db.customer_records.update_one(
            {'id': record_id},
            {'$set': {'status': 'requested'}}
        )
    
    return request

@api_router.get("/download-requests", response_model=List[DownloadRequest])
async def get_download_requests(user: User = Depends(get_current_user)):
    query = {}
    if user.role == 'staff':
        query['requested_by'] = user.id
    
    requests = await db.download_requests.find(query, {'_id': 0}).sort('requested_at', -1).to_list(1000)
    
    for req in requests:
        if isinstance(req['requested_at'], str):
            req['requested_at'] = datetime.fromisoformat(req['requested_at'])
        if req.get('reviewed_at') and isinstance(req['reviewed_at'], str):
            req['reviewed_at'] = datetime.fromisoformat(req['reviewed_at'])
    
    return requests

@api_router.patch("/download-requests/{request_id}/approve")
async def approve_request(request_id: str, user: User = Depends(get_admin_user)):
    request = await db.download_requests.find_one({'id': request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")
    
    await db.download_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'approved',
            'reviewed_at': get_jakarta_now().isoformat(),
            'reviewed_by': user.id,
            'reviewed_by_name': user.name
        }}
    )
    
    for record_id in request['record_ids']:
        await db.customer_records.update_one(
            {'id': record_id},
            {'$set': {
                'status': 'assigned',
                'assigned_to': request['requested_by'],
                'assigned_to_name': request['requested_by_name'],
                'assigned_at': get_jakarta_now().isoformat(),
                'request_id': request_id
            }}
        )
    
    # Create notification for staff
    await create_notification(
        user_id=request['requested_by'],
        type='request_approved',
        title='Request Approved',
        message=f'Your request for {request["record_count"]} records from {request["database_name"]} has been approved',
        data={'request_id': request_id, 'record_count': request['record_count'], 'database_name': request['database_name']}
    )
    
    return {'message': 'Request approved and records assigned'}

@api_router.patch("/download-requests/{request_id}/reject")
async def reject_request(request_id: str, user: User = Depends(get_admin_user)):
    request = await db.download_requests.find_one({'id': request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")
    
    await db.download_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': 'rejected',
            'reviewed_at': get_jakarta_now().isoformat(),
            'reviewed_by': user.id,
            'reviewed_by_name': user.name
        }}
    )
    
    for record_id in request['record_ids']:
        await db.customer_records.update_one(
            {'id': record_id},
            {'$set': {'status': 'available'}}
        )
    
    # Create notification for staff
    await create_notification(
        user_id=request['requested_by'],
        type='request_rejected',
        title='Request Rejected',
        message=f'Your request for {request["record_count"]} records from {request["database_name"]} has been rejected',
        data={'request_id': request_id, 'database_name': request['database_name']}
    )
    
    return {'message': 'Request rejected'}

@api_router.get("/my-request-batches")
async def get_my_request_batches(user: User = Depends(get_current_user)):
    """Get all approved request batches for the current staff member"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can view request batches")
    
    # Get all approved requests for this user
    requests = await db.download_requests.find(
        {'requested_by': user.id, 'status': 'approved'},
        {'_id': 0}
    ).sort('reviewed_at', -1).to_list(1000)
    
    # Get record counts and stats for each request
    batches = []
    for req in requests:
        # Get records in this batch
        batch_records = await db.customer_records.find({
            'request_id': req['id'],
            'assigned_to': user.id
        }, {'_id': 0, 'whatsapp_status': 1, 'respond_status': 1}).to_list(10000)
        
        record_count = len(batch_records)
        ada_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'ada')
        ceklis1_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'ceklis1')
        tidak_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'tidak')
        respond_ya_count = sum(1 for r in batch_records if r.get('respond_status') == 'ya')
        respond_tidak_count = sum(1 for r in batch_records if r.get('respond_status') == 'tidak')
        
        # Get database info
        database = await db.databases.find_one({'id': req['database_id']}, {'_id': 0})
        
        batches.append({
            'id': req['id'],
            'database_id': req['database_id'],
            'database_name': database.get('name', 'Unknown') if database else 'Unknown',
            'product_name': database.get('product_name', 'Unknown') if database else 'Unknown',
            'custom_title': req.get('custom_title'),
            'quantity': req.get('quantity', 0),
            'record_count': record_count,
            'ada_count': ada_count,
            'ceklis1_count': ceklis1_count,
            'tidak_count': tidak_count,
            'respond_ya_count': respond_ya_count,
            'respond_tidak_count': respond_tidak_count,
            'requested_at': req.get('requested_at'),
            'approved_at': req.get('reviewed_at')
        })
    
    # Get legacy batch titles
    legacy_titles = {}
    legacy_title_docs = await db.batch_titles.find({'user_id': user.id}, {'_id': 0}).to_list(100)
    for doc in legacy_title_docs:
        legacy_titles[doc['batch_id']] = doc.get('title')
    
    # Check for legacy records (assigned before batch tracking)
    legacy_records_all = await db.customer_records.find(
        {
            'assigned_to': user.id,
            'status': 'assigned',
            '$or': [{'request_id': {'$exists': False}}, {'request_id': None}]
        },
        {'_id': 0, 'database_id': 1, 'database_name': 1, 'product_name': 1, 'whatsapp_status': 1, 'respond_status': 1}
    ).to_list(10000)
    
    if legacy_records_all:
        # Group by database
        legacy_by_db = {}
        for rec in legacy_records_all:
            db_id = rec['database_id']
            if db_id not in legacy_by_db:
                legacy_by_db[db_id] = {
                    'database_name': rec.get('database_name', 'Unknown'),
                    'product_name': rec.get('product_name', 'Unknown'),
                    'count': 0,
                    'ada_count': 0,
                    'ceklis1_count': 0,
                    'tidak_count': 0,
                    'respond_ya_count': 0,
                    'respond_tidak_count': 0
                }
            legacy_by_db[db_id]['count'] += 1
            if rec.get('whatsapp_status') == 'ada':
                legacy_by_db[db_id]['ada_count'] += 1
            elif rec.get('whatsapp_status') == 'ceklis1':
                legacy_by_db[db_id]['ceklis1_count'] += 1
            elif rec.get('whatsapp_status') == 'tidak':
                legacy_by_db[db_id]['tidak_count'] += 1
            if rec.get('respond_status') == 'ya':
                legacy_by_db[db_id]['respond_ya_count'] += 1
            elif rec.get('respond_status') == 'tidak':
                legacy_by_db[db_id]['respond_tidak_count'] += 1
        
        # Add legacy batches
        for db_id, info in legacy_by_db.items():
            batch_id = f'legacy_{db_id}'
            batches.append({
                'id': batch_id,
                'database_id': db_id,
                'database_name': info['database_name'],
                'product_name': info['product_name'],
                'custom_title': legacy_titles.get(batch_id),
                'quantity': info['count'],
                'record_count': info['count'],
                'ada_count': info['ada_count'],
                'ceklis1_count': info['ceklis1_count'],
                'tidak_count': info['tidak_count'],
                'respond_ya_count': info['respond_ya_count'],
                'respond_tidak_count': info['respond_tidak_count'],
                'requested_at': None,
                'approved_at': None,
                'is_legacy': True
            })
    
    return batches

class BatchTitleUpdate(BaseModel):
    title: str

@api_router.patch("/my-request-batches/{batch_id}/title")
async def update_batch_title(batch_id: str, title_update: BatchTitleUpdate, user: User = Depends(get_current_user)):
    """Update the custom title for a batch"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can update batch titles")
    
    # Handle legacy batches - store in a separate collection
    if batch_id.startswith('legacy_'):
        database_id = batch_id.replace('legacy_', '')
        await db.batch_titles.update_one(
            {'batch_id': batch_id, 'user_id': user.id},
            {'$set': {'title': title_update.title, 'database_id': database_id}},
            upsert=True
        )
    else:
        # Verify this request belongs to the user
        request = await db.download_requests.find_one({'id': batch_id, 'requested_by': user.id})
        if not request:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        await db.download_requests.update_one(
            {'id': batch_id},
            {'$set': {'custom_title': title_update.title}}
        )
    
    return {'message': 'Title updated successfully'}

@api_router.get("/my-assigned-records-by-batch")
async def get_my_assigned_records_by_batch(request_id: str, user: User = Depends(get_current_user)):
    """Get assigned records for a specific request batch"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can view assigned records")
    
    # Handle legacy batches
    if request_id.startswith('legacy_'):
        database_id = request_id.replace('legacy_', '')
        records = await db.customer_records.find(
            {
                'assigned_to': user.id,
                'database_id': database_id,
                'status': 'assigned',
                '$or': [{'request_id': {'$exists': False}}, {'request_id': None}]
            },
            {'_id': 0}
        ).sort('assigned_at', -1).to_list(10000)
    else:
        # Verify this request belongs to the user
        request = await db.download_requests.find_one({'id': request_id, 'requested_by': user.id})
        if not request:
            raise HTTPException(status_code=404, detail="Request batch not found")
        
        records = await db.customer_records.find(
            {'request_id': request_id, 'assigned_to': user.id},
            {'_id': 0}
        ).sort('assigned_at', -1).to_list(10000)
    
    for record in records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        if record.get('assigned_at') and isinstance(record['assigned_at'], str):
            record['assigned_at'] = datetime.fromisoformat(record['assigned_at'])
    
    return records

@api_router.get("/download/{request_id}")
async def download_database(request_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="File download is no longer supported. Use assigned records instead.")

@api_router.get("/my-assigned-records", response_model=List[CustomerRecord])
async def get_my_assigned_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can view assigned records")
    
    query = {
        'assigned_to': user.id,
        'status': 'assigned'
    }
    if product_id:
        query['product_id'] = product_id
    
    records = await db.customer_records.find(query, {'_id': 0}).sort('assigned_at', -1).to_list(10000)
    
    for record in records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        if record.get('assigned_at') and isinstance(record['assigned_at'], str):
            record['assigned_at'] = datetime.fromisoformat(record['assigned_at'])
    
    return records

@api_router.patch("/customer-records/{record_id}/whatsapp-status")
async def update_whatsapp_status(record_id: str, status_update: WhatsAppStatusUpdate, user: User = Depends(get_current_user)):
    record = await db.customer_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if user.role == 'staff' and record.get('assigned_to') != user.id:
        raise HTTPException(status_code=403, detail="You can only update records assigned to you")
    
    if status_update.whatsapp_status not in ['ada', 'ceklis1', 'tidak', None]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'ada', 'ceklis1', or 'tidak'")
    
    await db.customer_records.update_one(
        {'id': record_id},
        {'$set': {
            'whatsapp_status': status_update.whatsapp_status,
            'whatsapp_status_updated_at': get_jakarta_now().isoformat()
        }}
    )
    
    return {'message': 'WhatsApp status updated successfully'}

@api_router.patch("/customer-records/{record_id}/respond-status")
async def update_respond_status(record_id: str, status_update: RespondStatusUpdate, user: User = Depends(get_current_user)):
    record = await db.customer_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if user.role == 'staff' and record.get('assigned_to') != user.id:
        raise HTTPException(status_code=403, detail="You can only update records assigned to you")
    
    if status_update.respond_status not in ['ya', 'tidak', None]:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'ya' or 'tidak'")
    
    await db.customer_records.update_one(
        {'id': record_id},
        {'$set': {
            'respond_status': status_update.respond_status,
            'respond_status_updated_at': get_jakarta_now().isoformat()
        }}
    )
    
    return {'message': 'Respond status updated successfully'}

@api_router.post("/reserved-members", response_model=ReservedMember)
async def create_reserved_member(member_data: ReservedMemberCreate, user: User = Depends(get_current_user)):
    # Validate product
    product = await db.products.find_one({'id': member_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check for duplicate customer name within same product (case-insensitive)
    existing = await db.reserved_members.find_one({
        'customer_name': {'$regex': f'^{member_data.customer_name}$', '$options': 'i'},
        'product_id': member_data.product_id,
        'status': {'$in': ['pending', 'approved']}
    })
    
    if existing:
        owner = await db.users.find_one({'id': existing['staff_id']})
        owner_name = owner['name'] if owner else 'Unknown'
        raise HTTPException(
            status_code=409, 
            detail=f"Customer '{member_data.customer_name}' is already reserved by {owner_name} in {product['name']}"
        )
    
    if user.role == 'admin':
        if not member_data.staff_id:
            raise HTTPException(status_code=400, detail="Staff ID is required for admin")
        
        staff = await db.users.find_one({'id': member_data.staff_id})
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")
        
        member = ReservedMember(
            customer_name=member_data.customer_name,
            product_id=member_data.product_id,
            product_name=product['name'],
            staff_id=member_data.staff_id,
            staff_name=staff['name'],
            status='approved',
            created_by=user.id,
            created_by_name=user.name,
            approved_at=get_jakarta_now(),
            approved_by=user.id,
            approved_by_name=user.name
        )
    else:
        member = ReservedMember(
            customer_name=member_data.customer_name,
            product_id=member_data.product_id,
            product_name=product['name'],
            staff_id=user.id,
            staff_name=user.name,
            status='pending',
            created_by=user.id,
            created_by_name=user.name
        )
        
        # Notify all admins about new pending request
        admins = await db.users.find({'role': 'admin'}, {'_id': 0, 'id': 1}).to_list(100)
        for admin in admins:
            await create_notification(
                user_id=admin['id'],
                type='new_reserved_request',
                title='New Reservation Request',
                message=f'{user.name} requested to reserve "{member_data.customer_name}" in {product["name"]}',
                data={'customer_name': member_data.customer_name, 'staff_name': user.name, 'product_name': product['name']}
            )
    
    doc = member.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('approved_at'):
        doc['approved_at'] = doc['approved_at'].isoformat()
    
    await db.reserved_members.insert_one(doc)
    return member

@api_router.get("/reserved-members", response_model=List[ReservedMember])
async def get_reserved_members(status: Optional[str] = None, product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    query = {}
    if status:
        query['status'] = status
    if product_id:
        query['product_id'] = product_id
    
    members = await db.reserved_members.find(query, {'_id': 0}).sort('created_at', -1).to_list(10000)
    
    for member in members:
        if isinstance(member.get('created_at'), str):
            member['created_at'] = datetime.fromisoformat(member['created_at'])
        if member.get('approved_at') and isinstance(member['approved_at'], str):
            member['approved_at'] = datetime.fromisoformat(member['approved_at'])
        # Handle legacy data without product fields
        if 'product_id' not in member:
            member['product_id'] = ''
            member['product_name'] = 'Unknown'
    
    return members

@api_router.patch("/reserved-members/{member_id}/approve")
async def approve_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    if member['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Member already processed")
    
    await db.reserved_members.update_one(
        {'id': member_id},
        {'$set': {
            'status': 'approved',
            'approved_at': get_jakarta_now().isoformat(),
            'approved_by': user.id,
            'approved_by_name': user.name
        }}
    )
    
    # Create notification for staff
    await create_notification(
        user_id=member['staff_id'],
        type='reserved_approved',
        title='Reservation Approved',
        message=f'Your reservation for "{member["customer_name"]}" in {member.get("product_name", "Unknown")} has been approved',
        data={'member_id': member_id, 'customer_name': member['customer_name']}
    )
    
    return {'message': 'Reserved member approved'}

@api_router.patch("/reserved-members/{member_id}/reject")
async def reject_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    if member['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Member already processed")
    
    # Create notification for staff before deleting
    await create_notification(
        user_id=member['staff_id'],
        type='reserved_rejected',
        title='Reservation Rejected',
        message=f'Your reservation for "{member["customer_name"]}" in {member.get("product_name", "Unknown")} has been rejected',
        data={'customer_name': member['customer_name']}
    )
    
    await db.reserved_members.delete_one({'id': member_id})
    
    return {'message': 'Reserved member request rejected'}

@api_router.delete("/reserved-members/{member_id}")
async def delete_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    await db.reserved_members.delete_one({'id': member_id})
    
    return {'message': 'Reserved member deleted'}

@api_router.patch("/reserved-members/{member_id}/move")
async def move_reserved_member(member_id: str, new_staff_id: str, user: User = Depends(get_admin_user)):
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    staff = await db.users.find_one({'id': new_staff_id})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    await db.reserved_members.update_one(
        {'id': member_id},
        {'$set': {
            'staff_id': new_staff_id,
            'staff_name': staff['name']
        }}
    )
    
    return {'message': f"Reserved member moved to {staff['name']}"}

@api_router.get("/staff-users")
async def get_staff_users(user: User = Depends(get_current_user)):
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff

@api_router.get("/download-history", response_model=List[DownloadHistory])
async def get_download_history(user: User = Depends(get_current_user)):
    query = {}
    if user.role == 'staff':
        query['downloaded_by'] = user.id
    
    history = await db.download_history.find(query, {'_id': 0}).sort('downloaded_at', -1).to_list(1000)
    
    for item in history:
        if isinstance(item['downloaded_at'], str):
            item['downloaded_at'] = datetime.fromisoformat(item['downloaded_at'])
    
    return history

# ============== OMSET CRM API ==============

@api_router.post("/omset", response_model=OmsetRecord)
async def create_omset_record(record_data: OmsetRecordCreate, user: User = Depends(get_current_user)):
    # Validate product
    product = await db.products.find_one({'id': record_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate depo_total
    depo_total = record_data.nominal * record_data.depo_kelipatan
    
    record = OmsetRecord(
        product_id=record_data.product_id,
        product_name=product['name'],
        staff_id=user.id,
        staff_name=user.name,
        record_date=record_data.record_date,
        customer_name=record_data.customer_name,
        customer_id=record_data.customer_id,
        nominal=record_data.nominal,
        depo_kelipatan=record_data.depo_kelipatan,
        depo_total=depo_total,
        keterangan=record_data.keterangan
    )
    
    doc = record.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.omset_records.insert_one(doc)
    return record

@api_router.get("/omset")
async def get_omset_records(
    product_id: Optional[str] = None,
    record_date: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    query = {}
    
    # Staff can only see their own records, admin sees all
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if record_date:
        query['record_date'] = record_date
    elif start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).sort([('record_date', -1), ('created_at', -1)]).to_list(10000)
    
    for record in records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        if record.get('updated_at') and isinstance(record['updated_at'], str):
            record['updated_at'] = datetime.fromisoformat(record['updated_at'])
    
    return records

@api_router.put("/omset/{record_id}")
async def update_omset_record(record_id: str, update_data: OmsetRecordUpdate, user: User = Depends(get_current_user)):
    record = await db.omset_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Staff can only update their own records
    if user.role == 'staff' and record['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only update your own records")
    
    update_fields = {}
    if update_data.customer_name is not None:
        update_fields['customer_name'] = update_data.customer_name
    if update_data.customer_id is not None:
        update_fields['customer_id'] = update_data.customer_id
    if update_data.nominal is not None:
        update_fields['nominal'] = update_data.nominal
    if update_data.depo_kelipatan is not None:
        update_fields['depo_kelipatan'] = update_data.depo_kelipatan
    if update_data.keterangan is not None:
        update_fields['keterangan'] = update_data.keterangan
    
    # Recalculate depo_total if nominal or kelipatan changed
    nominal = update_data.nominal if update_data.nominal is not None else record['nominal']
    kelipatan = update_data.depo_kelipatan if update_data.depo_kelipatan is not None else record['depo_kelipatan']
    update_fields['depo_total'] = nominal * kelipatan
    update_fields['updated_at'] = get_jakarta_now().isoformat()
    
    await db.omset_records.update_one({'id': record_id}, {'$set': update_fields})
    
    return {'message': 'Record updated successfully'}

@api_router.delete("/omset/{record_id}")
async def delete_omset_record(record_id: str, user: User = Depends(get_current_user)):
    record = await db.omset_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Staff can only delete their own records
    if user.role == 'staff' and record['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own records")
    
    await db.omset_records.delete_one({'id': record_id})
    
    return {'message': 'Record deleted successfully'}

@api_router.get("/omset/summary")
async def get_omset_summary(
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    query = {}
    
    # Staff can only see their own summary, admin sees all
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Get ALL records for NDP/RDP calculation (need full history)
    all_query = {}
    if user.role == 'staff':
        all_query['staff_id'] = user.id
    elif staff_id:
        all_query['staff_id'] = staff_id
    if product_id:
        all_query['product_id'] = product_id
    
    all_records_for_ndp = await db.omset_records.find(all_query, {'_id': 0}).to_list(100000)
    
    # Calculate customer first appearance dates (per product)
    customer_first_date = {}  # (customer_id, product_id) -> first date
    for record in sorted(all_records_for_ndp, key=lambda x: x['record_date']):
        key = (record['customer_id'], record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Calculate summaries
    daily_summary = {}
    staff_summary = {}
    product_summary = {}
    total_nominal = 0
    total_depo = 0
    total_records = len(records)
    total_ndp = 0
    total_rdp = 0
    
    for record in records:
        date = record['record_date']
        staff_name = record['staff_name']
        staff_id_rec = record['staff_id']
        product_name = record['product_name']
        product_id_rec = record['product_id']
        nominal = record.get('nominal', 0) or 0
        depo_total = record.get('depo_total', 0) or 0
        
        # Determine NDP/RDP
        key = (record['customer_id'], product_id_rec)
        first_date = customer_first_date.get(key)
        is_ndp = first_date == date
        
        total_nominal += nominal
        total_depo += depo_total
        
        # Daily summary
        if date not in daily_summary:
            daily_summary[date] = {
                'date': date, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_customers': set(),
                'rdp_count': 0,
                'ndp_total': 0,
                'rdp_total': 0
            }
        daily_summary[date]['total_nominal'] += nominal
        daily_summary[date]['total_depo'] += depo_total
        daily_summary[date]['count'] += 1
        
        if is_ndp:
            daily_summary[date]['ndp_customers'].add(record['customer_id'])
            daily_summary[date]['ndp_total'] += depo_total
        else:
            daily_summary[date]['rdp_count'] += 1
            daily_summary[date]['rdp_total'] += depo_total
        
        # Staff summary
        if staff_id_rec not in staff_summary:
            staff_summary[staff_id_rec] = {
                'staff_id': staff_id_rec, 
                'staff_name': staff_name, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_count': 0,
                'rdp_count': 0
            }
        staff_summary[staff_id_rec]['total_nominal'] += nominal
        staff_summary[staff_id_rec]['total_depo'] += depo_total
        staff_summary[staff_id_rec]['count'] += 1
        if is_ndp:
            staff_summary[staff_id_rec]['ndp_count'] += 1
        else:
            staff_summary[staff_id_rec]['rdp_count'] += 1
        
        # Product summary
        if product_id_rec not in product_summary:
            product_summary[product_id_rec] = {
                'product_id': product_id_rec, 
                'product_name': product_name, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_count': 0,
                'rdp_count': 0
            }
        product_summary[product_id_rec]['total_nominal'] += nominal
        product_summary[product_id_rec]['total_depo'] += depo_total
        product_summary[product_id_rec]['count'] += 1
        if is_ndp:
            product_summary[product_id_rec]['ndp_count'] += 1
        else:
            product_summary[product_id_rec]['rdp_count'] += 1
    
    # Convert daily summary sets to counts
    daily_list = []
    for date, data in daily_summary.items():
        daily_list.append({
            'date': data['date'],
            'total_nominal': data['total_nominal'],
            'total_depo': data['total_depo'],
            'count': data['count'],
            'ndp_count': len(data['ndp_customers']),
            'rdp_count': data['rdp_count'],
            'ndp_total': data['ndp_total'],
            'rdp_total': data['rdp_total']
        })
        total_ndp += len(data['ndp_customers'])
        total_rdp += data['rdp_count']
    
    return {
        'total': {
            'total_nominal': total_nominal,
            'total_depo': total_depo,
            'total_records': total_records,
            'total_ndp': total_ndp,
            'total_rdp': total_rdp
        },
        'daily': sorted(daily_list, key=lambda x: x['date'], reverse=True),
        'by_staff': sorted(staff_summary.values(), key=lambda x: x['total_depo'], reverse=True),
        'by_product': sorted(product_summary.values(), key=lambda x: x['total_depo'], reverse=True)
    }

@api_router.get("/omset/dates")
async def get_omset_dates(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get list of dates that have omset records"""
    query = {}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    if product_id:
        query['product_id'] = product_id
    
    records = await db.omset_records.find(query, {'_id': 0, 'record_date': 1}).to_list(100000)
    
    dates = sorted(set(r['record_date'] for r in records), reverse=True)
    return dates

@api_router.get("/omset/export")
async def export_omset_records(
    request: Request,
    product_id: Optional[str] = None,
    record_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    staff_id: Optional[str] = None,
    format: str = "csv",
    token: Optional[str] = None
):
    """Export OMSET records to CSV format"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Support token from query param for window.open() downloads
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user_data:
                raise HTTPException(status_code=401, detail="User not found")
            user = User(**user_data)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        user = await get_current_user(request)
    
    query = {}
    
    # Staff can only export their own records
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if record_date:
        query['record_date'] = record_date
    elif start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).sort([('record_date', -1), ('created_at', -1)]).to_list(100000)
    
    # Calculate NDP/RDP for each record
    all_query = {'product_id': product_id} if product_id else {}
    if user.role == 'staff':
        all_query['staff_id'] = user.id
    
    all_records = await db.omset_records.find(all_query, {'_id': 0}).to_list(100000)
    
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        key = (record['customer_id'], record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Product', 'Staff', 'Customer ID', 'Nominal', 'Kelipatan', 'Depo Total', 'Type', 'Keterangan'])
    
    # Data rows
    for record in records:
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        record_type = 'NDP' if first_date == record['record_date'] else 'RDP'
        
        writer.writerow([
            record['record_date'],
            record['product_name'],
            record['staff_name'],
            record['customer_id'],
            record.get('nominal', 0),
            record.get('depo_kelipatan', 1),
            record.get('depo_total', 0),
            record_type,
            record.get('keterangan', '')
        ])
    
    output.seek(0)
    
    # Generate filename
    date_part = record_date if record_date else f"{start_date or 'all'}_to_{end_date or 'now'}"
    filename = f"omset_export_{date_part}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/octet-stream",
            "Cache-Control": "no-cache"
        }
    )

@api_router.get("/omset/export-summary")
async def export_omset_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    token: Optional[str] = None
):
    """Export OMSET summary to CSV (Admin only)"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Support token from query param for window.open() downloads
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user_data:
                raise HTTPException(status_code=401, detail="User not found")
            user = User(**user_data)
            if user.role != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        user = await get_admin_user(request)
    
    query = {}
    
    if product_id:
        query['product_id'] = product_id
    
    if start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Calculate NDP/RDP
    all_records = await db.omset_records.find({} if not product_id else {'product_id': product_id}, {'_id': 0}).to_list(100000)
    
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        key = (record['customer_id'], record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Aggregate by date
    daily_summary = {}
    for record in records:
        date = record['record_date']
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        is_ndp = first_date == date
        
        if date not in daily_summary:
            daily_summary[date] = {
                'date': date,
                'total_depo': 0,
                'ndp_customers': set(),
                'rdp_count': 0,
                'total_form': 0
            }
        
        daily_summary[date]['total_depo'] += record.get('depo_total', 0)
        daily_summary[date]['total_form'] += record.get('depo_kelipatan', 1)
        
        if is_ndp:
            daily_summary[date]['ndp_customers'].add(record['customer_id'])
        else:
            daily_summary[date]['rdp_count'] += 1
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Total Form', 'NDP', 'RDP', 'Total OMSET'])
    
    # Data rows
    for date in sorted(daily_summary.keys(), reverse=True):
        data = daily_summary[date]
        writer.writerow([
            date,
            data['total_form'],
            len(data['ndp_customers']),
            data['rdp_count'],
            data['total_depo']
        ])
    
    output.seek(0)
    
    date_part = f"{start_date or 'all'}_to_{end_date or 'now'}"
    filename = f"omset_summary_{date_part}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/octet-stream",
            "Cache-Control": "no-cache"
        }
    )

@api_router.get("/omset/ndp-rdp")
async def get_omset_ndp_rdp(
    product_id: str,
    record_date: str,
    user: User = Depends(get_current_user)
):
    """Calculate NDP and RDP for a specific date and product"""
    query = {'product_id': product_id}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    # Get all records for this product
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Group records by date and customer_id
    customer_first_date = {}  # customer_id -> first date they appeared
    
    for record in sorted(all_records, key=lambda x: x['record_date']):
        cid = record['customer_id']
        if cid not in customer_first_date:
            customer_first_date[cid] = record['record_date']
    
    # Get records for the specific date
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    # Calculate NDP and RDP
    ndp_customers = set()  # Unique customers that are NDP
    rdp_count = 0
    ndp_total = 0
    rdp_total = 0
    
    for record in date_records:
        cid = record['customer_id']
        first_date = customer_first_date.get(cid)
        
        if first_date == record_date:
            # This customer first appeared on this date = NDP
            ndp_customers.add(cid)
            ndp_total += record.get('depo_total', 0)
        else:
            # Customer appeared before = RDP
            rdp_count += 1
            rdp_total += record.get('depo_total', 0)
    
    return {
        'date': record_date,
        'product_id': product_id,
        'ndp_count': len(ndp_customers),  # Unique new customers
        'ndp_total': ndp_total,
        'rdp_count': rdp_count,  # Total redepo records
        'rdp_total': rdp_total,
        'total_records': len(date_records)
    }

@api_router.get("/omset/record-types")
async def get_omset_record_types(
    product_id: str,
    record_date: str,
    user: User = Depends(get_current_user)
):
    """Get all records with NDP/RDP classification for a specific date"""
    query = {'product_id': product_id}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    # Get all records for this product to determine first appearance
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Find first date each customer appeared
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        cid = record['customer_id']
        if cid not in customer_first_date:
            customer_first_date[cid] = record['record_date']
    
    # Get records for the specific date and add type
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    for record in date_records:
        cid = record['customer_id']
        first_date = customer_first_date.get(cid)
        record['record_type'] = 'NDP' if first_date == record_date else 'RDP'
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
    
    return date_records

# ==================== REPORT CRM ENDPOINTS ====================

@api_router.get("/report-crm/data")
async def get_report_crm_data(
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    year: int = None,
    month: int = None,
    user: User = Depends(get_admin_user)
):
    """Get comprehensive report data for Report CRM page"""
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    # Build base query
    base_query = {}
    if product_id:
        base_query['product_id'] = product_id
    if staff_id:
        base_query['staff_id'] = staff_id
    
    # Get all OMSET records for the year
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    year_query = {**base_query, 'record_date': {'$gte': year_start, '$lte': year_end}}
    
    all_records = await db.omset_records.find(year_query, {'_id': 0}).to_list(100000)
    
    # Get ALL records (all time) for NDP/RDP calculation
    all_time_query = {}
    if product_id:
        all_time_query['product_id'] = product_id
    all_time_records = await db.omset_records.find(all_time_query, {'_id': 0}).to_list(500000)
    
    # Calculate customer first appearance dates
    customer_first_date = {}
    for record in sorted(all_time_records, key=lambda x: x['record_date']):
        cid = record['customer_id']
        pid = record['product_id']
        key = (cid, pid)
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Process yearly data (by month)
    yearly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        new_id = 0
        rdp = 0
        total_form = len(month_records)
        nominal = 0
        
        for record in month_records:
            key = (record['customer_id'], record['product_id'])
            first_date = customer_first_date.get(key)
            if first_date and first_date.startswith(month_str) and first_date == record['record_date']:
                new_id += 1
            elif first_date and first_date < record['record_date']:
                rdp += 1
            nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        yearly_data.append({
            'month': m,
            'new_id': new_id,
            'rdp': rdp,
            'total_form': total_form,
            'nominal': nominal
        })
    
    # Process monthly data (by day) for all months
    monthly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        # Group by date
        daily_groups = {}
        for record in month_records:
            date = record['record_date']
            if date not in daily_groups:
                daily_groups[date] = []
            daily_groups[date].append(record)
        
        for date, records in sorted(daily_groups.items()):
            new_id = 0
            rdp = 0
            nominal = 0
            
            for record in records:
                key = (record['customer_id'], record['product_id'])
                first_date = customer_first_date.get(key)
                if first_date == date:
                    new_id += 1
                else:
                    rdp += 1
                nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
            
            monthly_data.append({
                'month': m,
                'date': date,
                'new_id': new_id,
                'rdp': rdp,
                'total_form': len(records),
                'nominal': nominal
            })
    
    # Process daily data for selected month - grouped by staff and product
    selected_month_str = f"{year}-{str(month).zfill(2)}"
    selected_month_records = [r for r in all_records if r['record_date'].startswith(selected_month_str)]
    
    # Group by staff -> product -> date
    staff_daily_data = {}
    for record in selected_month_records:
        sid = record['staff_id']
        sname = record['staff_name']
        pid = record['product_id']
        pname = record['product_name']
        date = record['record_date']
        
        if sid not in staff_daily_data:
            staff_daily_data[sid] = {
                'staff_id': sid,
                'staff_name': sname,
                'products': {},
                'totals': {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            }
        
        if pid not in staff_daily_data[sid]['products']:
            staff_daily_data[sid]['products'][pid] = {
                'product_id': pid,
                'product_name': pname,
                'daily': {},
                'totals': {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            }
        
        if date not in staff_daily_data[sid]['products'][pid]['daily']:
            staff_daily_data[sid]['products'][pid]['daily'][date] = {
                'date': date,
                'new_id': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
        
        # Determine NDP/RDP
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        is_ndp = first_date == date
        
        nom = record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        # Update daily entry
        if is_ndp:
            staff_daily_data[sid]['products'][pid]['daily'][date]['new_id'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['new_id'] += 1
            staff_daily_data[sid]['totals']['new_id'] += 1
        else:
            staff_daily_data[sid]['products'][pid]['daily'][date]['rdp'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['rdp'] += 1
            staff_daily_data[sid]['totals']['rdp'] += 1
        
        staff_daily_data[sid]['products'][pid]['daily'][date]['total_form'] += 1
        staff_daily_data[sid]['products'][pid]['daily'][date]['nominal'] += nom
        staff_daily_data[sid]['products'][pid]['totals']['total_form'] += 1
        staff_daily_data[sid]['products'][pid]['totals']['nominal'] += nom
        staff_daily_data[sid]['totals']['total_form'] += 1
        staff_daily_data[sid]['totals']['nominal'] += nom
    
    # Convert to list format for frontend
    daily_by_staff = []
    for sid, staff_data in staff_daily_data.items():
        products_list = []
        for pid, product_data in staff_data['products'].items():
            daily_list = sorted(product_data['daily'].values(), key=lambda x: x['date'])
            products_list.append({
                'product_id': product_data['product_id'],
                'product_name': product_data['product_name'],
                'daily': daily_list,
                'totals': product_data['totals']
            })
        products_list.sort(key=lambda x: x['totals']['nominal'], reverse=True)
        
        daily_by_staff.append({
            'staff_id': staff_data['staff_id'],
            'staff_name': staff_data['staff_name'],
            'products': products_list,
            'totals': staff_data['totals']
        })
    
    daily_by_staff.sort(key=lambda x: x['totals']['nominal'], reverse=True)
    
    # Also keep flat daily data for backward compatibility
    daily_groups = {}
    for record in selected_month_records:
        date = record['record_date']
        if date not in daily_groups:
            daily_groups[date] = []
        daily_groups[date].append(record)
    
    daily_data = []
    for date, records in sorted(daily_groups.items()):
        new_id = 0
        rdp = 0
        nominal = 0
        
        for record in records:
            key = (record['customer_id'], record['product_id'])
            first_date = customer_first_date.get(key)
            if first_date == date:
                new_id += 1
            else:
                rdp += 1
            nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        daily_data.append({
            'date': date,
            'new_id': new_id,
            'rdp': rdp,
            'total_form': len(records),
            'nominal': nominal
        })
    
    # Process staff performance for the year
    staff_groups = {}
    for record in all_records:
        sid = record['staff_id']
        if sid not in staff_groups:
            staff_groups[sid] = {
                'staff_id': sid,
                'staff_name': record['staff_name'],
                'new_id': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
        
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        if first_date == record['record_date']:
            staff_groups[sid]['new_id'] += 1
        else:
            staff_groups[sid]['rdp'] += 1
        staff_groups[sid]['total_form'] += 1
        staff_groups[sid]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    staff_performance = sorted(staff_groups.values(), key=lambda x: x['nominal'], reverse=True)
    
    # Calculate deposit frequency tiers (2x, 3x, >4x)
    customer_deposit_counts = {}
    for record in all_records:
        cid = record['customer_id']
        if cid not in customer_deposit_counts:
            customer_deposit_counts[cid] = 0
        customer_deposit_counts[cid] += 1
    
    deposit_tiers = {'2x': 0, '3x': 0, '4x_plus': 0}
    for cid, count in customer_deposit_counts.items():
        if count == 2:
            deposit_tiers['2x'] += 1
        elif count == 3:
            deposit_tiers['3x'] += 1
        elif count >= 4:
            deposit_tiers['4x_plus'] += 1
    
    return {
        'yearly': yearly_data,
        'monthly': monthly_data,
        'daily': daily_data,
        'daily_by_staff': daily_by_staff,
        'staff_performance': staff_performance,
        'deposit_tiers': deposit_tiers
    }

@api_router.get("/report-crm/export")
async def export_report_crm(
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    year: int = None,
    user: User = Depends(get_admin_user)
):
    """Export Report CRM data to Excel"""
    from fastapi.responses import StreamingResponse
    import tempfile
    
    if year is None:
        year = get_jakarta_now().year
    
    # Get report data
    report_data = await get_report_crm_data(product_id, staff_id, year, 1, user)
    
    # Create Excel workbook with multiple sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Yearly Summary Sheet
        yearly_df = pd.DataFrame(report_data['yearly'])
        yearly_df['month_name'] = yearly_df['month'].apply(lambda x: ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC'][x-1])
        yearly_df = yearly_df[['month_name', 'new_id', 'rdp', 'total_form', 'nominal']]
        yearly_df.columns = ['BULAN', 'NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'NOMINAL']
        
        # Add totals row
        totals = yearly_df[['NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'NOMINAL']].sum()
        totals_row = pd.DataFrame([['TOTAL', totals['NEW ID (NDP)'], totals['ID RDP'], totals['TOTAL FORM'], totals['NOMINAL']]], 
                                   columns=yearly_df.columns)
        yearly_df = pd.concat([yearly_df, totals_row], ignore_index=True)
        yearly_df.to_excel(writer, sheet_name='YEARLY', index=False)
        
        # Monthly Detail Sheet
        if report_data['monthly']:
            monthly_df = pd.DataFrame(report_data['monthly'])
            monthly_df = monthly_df[['date', 'new_id', 'rdp', 'total_form', 'nominal']]
            monthly_df.columns = ['TANGGAL', 'NEW ID', 'ID RDP', 'TOTAL FORM', 'NOMINAL']
            monthly_df.to_excel(writer, sheet_name='MONTHLY', index=False)
        
        # Staff Performance Sheet
        if report_data['staff_performance']:
            staff_df = pd.DataFrame(report_data['staff_performance'])
            staff_df = staff_df[['staff_name', 'new_id', 'rdp', 'total_form', 'nominal']]
            staff_df.columns = ['STAFF', 'NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'TOTAL OMSET']
            staff_df.to_excel(writer, sheet_name='STAFF PERFORMANCE', index=False)
        
        # Deposit Tiers Sheet
        tiers_df = pd.DataFrame([
            {'Tier': '2x Deposit', 'Count': report_data['deposit_tiers']['2x']},
            {'Tier': '3x Deposit', 'Count': report_data['deposit_tiers']['3x']},
            {'Tier': '>4x Deposit', 'Count': report_data['deposit_tiers']['4x_plus']}
        ])
        tiers_df.to_excel(writer, sheet_name='DEPOSIT TIERS', index=False)
    
    output.seek(0)
    
    # Create temp file for download
    temp_path = f"/tmp/report_crm_{year}.xlsx"
    with open(temp_path, 'wb') as f:
        f.write(output.getvalue())
    
    return FileResponse(
        path=temp_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=f"Report_CRM_{year}.xlsx"
    )

# ==================== DB BONANZA ENDPOINTS ====================

@api_router.post("/bonanza/upload")
async def upload_bonanza_database(
    file: UploadFile = File(...),
    name: str = Form(...),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Upload a new Bonanza database (Admin only)"""
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    # Validate product
    product = await db.products.find_one({'id': product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    contents = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Create database record
    database_id = str(uuid.uuid4())
    database_doc = {
        'id': database_id,
        'name': name,
        'filename': file.filename,
        'file_type': 'csv' if file.filename.endswith('.csv') else 'excel',
        'total_records': len(df),
        'product_id': product_id,
        'product_name': product['name'],
        'uploaded_by': user.id,
        'uploaded_by_name': user.name,
        'uploaded_at': get_jakarta_now().isoformat()
    }
    
    await db.bonanza_databases.insert_one(database_doc)
    
    # Create records
    records = []
    for idx, row in df.iterrows():
        record = {
            'id': str(uuid.uuid4()),
            'database_id': database_id,
            'database_name': name,
            'product_id': product_id,
            'product_name': product['name'],
            'row_number': idx + 1,
            'row_data': row.to_dict(),
            'status': 'available',
            'assigned_to': None,
            'assigned_to_name': None,
            'assigned_at': None,
            'assigned_by': None,
            'assigned_by_name': None,
            'created_at': get_jakarta_now().isoformat()
        }
        records.append(record)
    
    if records:
        await db.bonanza_records.insert_many(records)
    
    return {
        'id': database_id,
        'name': name,
        'product_id': product_id,
        'product_name': product['name'],
        'total_records': len(df),
        'columns': list(df.columns)
    }

@api_router.get("/bonanza/databases")
async def get_bonanza_databases(product_id: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all Bonanza databases (Admin only)"""
    query = {}
    if product_id:
        query['product_id'] = product_id
    
    databases = await db.bonanza_databases.find(query, {'_id': 0}).sort('uploaded_at', -1).to_list(1000)
    
    for database in databases:
        # Get counts
        total = await db.bonanza_records.count_documents({'database_id': database['id']})
        assigned = await db.bonanza_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        database['total_records'] = total
        database['assigned_count'] = assigned
        database['available_count'] = total - assigned
        # Handle legacy data without product fields
        if 'product_id' not in database:
            database['product_id'] = ''
            database['product_name'] = 'Unknown'
    
    return databases

@api_router.get("/bonanza/databases/{database_id}/records")
async def get_bonanza_records(
    database_id: str,
    status: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get all records from a Bonanza database (Admin only)"""
    query = {'database_id': database_id}
    if status:
        query['status'] = status
    
    records = await db.bonanza_records.find(query, {'_id': 0}).sort('row_number', 1).to_list(100000)
    return records

@api_router.post("/bonanza/assign")
async def assign_bonanza_records(assignment: BonanzaAssignment, user: User = Depends(get_admin_user)):
    """Assign Bonanza records to a staff member (Admin only)"""
    # Get staff info
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Update records
    result = await db.bonanza_records.update_many(
        {'id': {'$in': assignment.record_ids}, 'status': 'available'},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': get_jakarta_now().isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name
        }}
    )
    
    return {'message': f'{result.modified_count} records assigned to {staff["name"]}'}

class RandomBonanzaAssignment(BaseModel):
    database_id: str
    staff_id: str
    quantity: int
    username_field: str = "Username"  # The field name in row_data that contains the username

@api_router.post("/bonanza/assign-random")
async def assign_random_bonanza_records(assignment: RandomBonanzaAssignment, user: User = Depends(get_admin_user)):
    """Randomly assign Bonanza records to a staff member, skipping reserved members (Admin only)"""
    import random
    
    # Get staff info
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get all reserved member customer names (case-insensitive comparison)
    reserved_members = await db.reserved_members.find({}, {'_id': 0, 'customer_name': 1}).to_list(100000)
    reserved_names = set(m['customer_name'].lower().strip() for m in reserved_members if m.get('customer_name'))
    
    # Get available records from this database
    available_records = await db.bonanza_records.find(
        {'database_id': assignment.database_id, 'status': 'available'},
        {'_id': 0}
    ).to_list(100000)
    
    # Filter out records whose username is in reserved members
    eligible_records = []
    skipped_count = 0
    for record in available_records:
        username = record.get('row_data', {}).get(assignment.username_field, '')
        if username and username.lower().strip() in reserved_names:
            skipped_count += 1
            continue
        eligible_records.append(record)
    
    if len(eligible_records) == 0:
        raise HTTPException(status_code=400, detail="No eligible records available (all either assigned or in reserved members)")
    
    if assignment.quantity > len(eligible_records):
        raise HTTPException(
            status_code=400, 
            detail=f"Only {len(eligible_records)} eligible records available (requested {assignment.quantity}, {skipped_count} skipped due to reserved members)"
        )
    
    # Randomly select records
    random.shuffle(eligible_records)
    selected_records = eligible_records[:assignment.quantity]
    selected_ids = [r['id'] for r in selected_records]
    
    # Update records
    result = await db.bonanza_records.update_many(
        {'id': {'$in': selected_ids}},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': get_jakarta_now().isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name
        }}
    )
    
    return {
        'message': f'{result.modified_count} records assigned to {staff["name"]}',
        'assigned_count': result.modified_count,
        'total_reserved_in_db': skipped_count,
        'remaining_eligible': len(eligible_records) - assignment.quantity,
        'total_available': len(available_records),
        'total_eligible': len(eligible_records)
    }

@api_router.delete("/bonanza/databases/{database_id}")
async def delete_bonanza_database(database_id: str, user: User = Depends(get_admin_user)):
    """Delete a Bonanza database and all its records (Admin only)"""
    await db.bonanza_records.delete_many({'database_id': database_id})
    await db.bonanza_databases.delete_one({'id': database_id})
    return {'message': 'Database deleted successfully'}

@api_router.get("/bonanza/staff/records")
async def get_staff_bonanza_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get Bonanza records assigned to the current staff"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    query = {'assigned_to': user.id, 'status': 'assigned'}
    if product_id:
        query['product_id'] = product_id
    
    records = await db.bonanza_records.find(query, {'_id': 0}).sort('assigned_at', -1).to_list(10000)
    
    # Handle legacy data without product fields
    for record in records:
        if 'product_id' not in record:
            record['product_id'] = ''
            record['product_name'] = 'Unknown'
    
    return records

@api_router.get("/bonanza/staff")
async def get_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff

# ==================== MEMBER WD CRM ENDPOINTS ====================

@api_router.post("/memberwd/upload")
async def upload_memberwd_database(
    file: UploadFile = File(...),
    name: str = Form(...),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Upload a new Member WD database (Admin only)"""
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    # Validate product
    product = await db.products.find_one({'id': product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    contents = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    database_id = str(uuid.uuid4())
    database_doc = {
        'id': database_id,
        'name': name,
        'filename': file.filename,
        'file_type': 'csv' if file.filename.endswith('.csv') else 'excel',
        'total_records': len(df),
        'product_id': product_id,
        'product_name': product['name'],
        'uploaded_by': user.id,
        'uploaded_by_name': user.name,
        'uploaded_at': get_jakarta_now().isoformat()
    }
    
    await db.memberwd_databases.insert_one(database_doc)
    
    records = []
    for idx, row in df.iterrows():
        record = {
            'id': str(uuid.uuid4()),
            'database_id': database_id,
            'database_name': name,
            'product_id': product_id,
            'product_name': product['name'],
            'row_number': idx + 1,
            'row_data': row.to_dict(),
            'status': 'available',
            'assigned_to': None,
            'assigned_to_name': None,
            'assigned_at': None,
            'assigned_by': None,
            'assigned_by_name': None,
            'created_at': get_jakarta_now().isoformat()
        }
        records.append(record)
    
    if records:
        await db.memberwd_records.insert_many(records)
    
    return {
        'id': database_id,
        'name': name,
        'product_id': product_id,
        'product_name': product['name'],
        'total_records': len(df),
        'columns': list(df.columns)
    }

@api_router.get("/memberwd/databases")
async def get_memberwd_databases(product_id: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all Member WD databases (Admin only)"""
    query = {}
    if product_id:
        query['product_id'] = product_id
    
    databases = await db.memberwd_databases.find(query, {'_id': 0}).sort('uploaded_at', -1).to_list(1000)
    
    for database in databases:
        total = await db.memberwd_records.count_documents({'database_id': database['id']})
        assigned = await db.memberwd_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        database['total_records'] = total
        database['assigned_count'] = assigned
        database['available_count'] = total - assigned
        # Handle legacy data without product fields
        if 'product_id' not in database:
            database['product_id'] = ''
            database['product_name'] = 'Unknown'
    
    return databases

@api_router.get("/memberwd/databases/{database_id}/records")
async def get_memberwd_records(
    database_id: str,
    status: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get all records from a Member WD database (Admin only)"""
    query = {'database_id': database_id}
    if status:
        query['status'] = status
    
    records = await db.memberwd_records.find(query, {'_id': 0}).sort('row_number', 1).to_list(100000)
    return records

@api_router.post("/memberwd/assign")
async def assign_memberwd_records(assignment: BonanzaAssignment, user: User = Depends(get_admin_user)):
    """Assign Member WD records to a staff member (Admin only)"""
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    result = await db.memberwd_records.update_many(
        {'id': {'$in': assignment.record_ids}, 'status': 'available'},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': get_jakarta_now().isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name
        }}
    )
    
    return {'message': f'{result.modified_count} records assigned to {staff["name"]}'}

@api_router.post("/memberwd/assign-random")
async def assign_random_memberwd_records(assignment: RandomBonanzaAssignment, user: User = Depends(get_admin_user)):
    """Randomly assign Member WD records to a staff member, skipping reserved members (Admin only)"""
    import random
    
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    reserved_members = await db.reserved_members.find({}, {'_id': 0, 'customer_name': 1}).to_list(100000)
    reserved_names = set(m['customer_name'].lower().strip() for m in reserved_members if m.get('customer_name'))
    
    available_records = await db.memberwd_records.find(
        {'database_id': assignment.database_id, 'status': 'available'},
        {'_id': 0}
    ).to_list(100000)
    
    eligible_records = []
    skipped_count = 0
    for record in available_records:
        username = record.get('row_data', {}).get(assignment.username_field, '')
        if username and username.lower().strip() in reserved_names:
            skipped_count += 1
            continue
        eligible_records.append(record)
    
    if len(eligible_records) == 0:
        raise HTTPException(status_code=400, detail="No eligible records available (all either assigned or in reserved members)")
    
    if assignment.quantity > len(eligible_records):
        raise HTTPException(
            status_code=400, 
            detail=f"Only {len(eligible_records)} eligible records available (requested {assignment.quantity}, {skipped_count} skipped due to reserved members)"
        )
    
    random.shuffle(eligible_records)
    selected_records = eligible_records[:assignment.quantity]
    selected_ids = [r['id'] for r in selected_records]
    
    result = await db.memberwd_records.update_many(
        {'id': {'$in': selected_ids}},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': get_jakarta_now().isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name
        }}
    )
    
    return {
        'message': f'{result.modified_count} records assigned to {staff["name"]}',
        'assigned_count': result.modified_count,
        'total_reserved_in_db': skipped_count,
        'remaining_eligible': len(eligible_records) - assignment.quantity,
        'total_available': len(available_records),
        'total_eligible': len(eligible_records)
    }

@api_router.delete("/memberwd/databases/{database_id}")
async def delete_memberwd_database(database_id: str, user: User = Depends(get_admin_user)):
    """Delete a Member WD database and all its records (Admin only)"""
    await db.memberwd_records.delete_many({'database_id': database_id})
    await db.memberwd_databases.delete_one({'id': database_id})
    return {'message': 'Database deleted successfully'}

@api_router.get("/memberwd/staff/records")
async def get_staff_memberwd_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get Member WD records assigned to the current staff"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    query = {'assigned_to': user.id, 'status': 'assigned'}
    if product_id:
        query['product_id'] = product_id
    
    records = await db.memberwd_records.find(query, {'_id': 0}).sort('assigned_at', -1).to_list(10000)
    
    # Handle legacy data without product fields
    for record in records:
        if 'product_id' not in record:
            record['product_id'] = ''
            record['product_name'] = 'Unknown'
    
    return records

@api_router.get("/memberwd/staff")
async def get_memberwd_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff

# ==================== EDIT PRODUCT ENDPOINTS ====================

@api_router.patch("/bonanza/databases/{database_id}/product")
async def update_bonanza_database_product(database_id: str, update: DatabaseProductUpdate, user: User = Depends(get_admin_user)):
    """Update the product of a Bonanza database (Admin only)"""
    # Validate product
    product = await db.products.find_one({'id': update.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update database
    result = await db.bonanza_databases.update_one(
        {'id': database_id},
        {'$set': {'product_id': update.product_id, 'product_name': product['name']}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Database not found")
    
    # Update all records in this database
    await db.bonanza_records.update_many(
        {'database_id': database_id},
        {'$set': {'product_id': update.product_id, 'product_name': product['name']}}
    )
    
    return {'message': f'Database product updated to {product["name"]}'}

@api_router.patch("/memberwd/databases/{database_id}/product")
async def update_memberwd_database_product(database_id: str, update: DatabaseProductUpdate, user: User = Depends(get_admin_user)):
    """Update the product of a Member WD database (Admin only)"""
    # Validate product
    product = await db.products.find_one({'id': update.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update database
    result = await db.memberwd_databases.update_one(
        {'id': database_id},
        {'$set': {'product_id': update.product_id, 'product_name': product['name']}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Database not found")
    
    # Update all records in this database
    await db.memberwd_records.update_many(
        {'database_id': database_id},
        {'$set': {'product_id': update.product_id, 'product_name': product['name']}}
    )
    
    return {'message': f'Database product updated to {product["name"]}'}

# ==================== BULK OPERATIONS ENDPOINTS ====================

@api_router.post("/bulk/requests")
async def bulk_request_action(bulk: BulkRequestAction, user: User = Depends(get_admin_user)):
    """Bulk approve or reject download requests (Admin only)"""
    if bulk.action not in ['approve', 'reject']:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    processed = 0
    errors = []
    notifications = []
    
    for request_id in bulk.request_ids:
        request = await db.download_requests.find_one({'id': request_id, 'status': 'pending'})
        if not request:
            errors.append(f"Request {request_id} not found or not pending")
            continue
        
        if bulk.action == 'approve':
            # Get random available records
            database = await db.databases.find_one({'id': request['database_id']})
            if not database:
                errors.append(f"Database not found for request {request_id}")
                continue
            
            available_records = await db.customer_records.find({
                'database_id': request['database_id'],
                'status': 'available'
            }, {'_id': 0}).to_list(request['record_count'])
            
            if len(available_records) < request['record_count']:
                errors.append(f"Not enough records for request {request_id}")
                continue
            
            import random
            random.shuffle(available_records)
            selected = available_records[:request['record_count']]
            selected_ids = [r['id'] for r in selected]
            
            # Update records
            await db.customer_records.update_many(
                {'id': {'$in': selected_ids}},
                {'$set': {
                    'status': 'assigned',
                    'assigned_to': request['requested_by'],
                    'assigned_to_name': request['requested_by_name'],
                    'assigned_at': get_jakarta_now().isoformat(),
                    'request_id': request_id
                }}
            )
            
            # Update request
            await db.download_requests.update_one(
                {'id': request_id},
                {'$set': {
                    'status': 'approved',
                    'reviewed_at': get_jakarta_now().isoformat(),
                    'reviewed_by': user.id,
                    'reviewed_by_name': user.name,
                    'record_ids': selected_ids
                }}
            )
            
            # Create notification
            notifications.append({
                'id': str(uuid.uuid4()),
                'user_id': request['requested_by'],
                'type': 'request_approved',
                'title': 'Request Approved',
                'message': f'Your request for {request["record_count"]} records from {request["database_name"]} has been approved',
                'data': {'request_id': request_id, 'record_count': request['record_count']},
                'read': False,
                'created_at': get_jakarta_now().isoformat()
            })
        else:
            # Reject
            await db.download_requests.update_one(
                {'id': request_id},
                {'$set': {
                    'status': 'rejected',
                    'reviewed_at': get_jakarta_now().isoformat(),
                    'reviewed_by': user.id,
                    'reviewed_by_name': user.name
                }}
            )
            
            notifications.append({
                'id': str(uuid.uuid4()),
                'user_id': request['requested_by'],
                'type': 'request_rejected',
                'title': 'Request Rejected',
                'message': f'Your request for {request["record_count"]} records from {request["database_name"]} has been rejected',
                'data': {'request_id': request_id},
                'read': False,
                'created_at': get_jakarta_now().isoformat()
            })
        
        processed += 1
    
    # Insert notifications
    if notifications:
        await db.notifications.insert_many(notifications)
    
    return {
        'message': f'{processed} requests {bulk.action}d successfully',
        'processed': processed,
        'errors': errors
    }

@api_router.post("/bulk/status-update")
async def bulk_status_update(bulk: BulkStatusUpdate, user: User = Depends(get_current_user)):
    """Bulk update WhatsApp/Respond status for multiple records"""
    update_fields = {}
    if bulk.whatsapp_status:
        if bulk.whatsapp_status not in ['ada', 'tidak', 'ceklis1']:
            raise HTTPException(status_code=400, detail="Invalid whatsapp_status")
        update_fields['whatsapp_status'] = bulk.whatsapp_status
    if bulk.respond_status:
        if bulk.respond_status not in ['ya', 'tidak']:
            raise HTTPException(status_code=400, detail="Invalid respond_status")
        update_fields['respond_status'] = bulk.respond_status
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No status fields to update")
    
    update_fields['updated_at'] = get_jakarta_now().isoformat()
    
    # Build query based on user role
    query = {'id': {'$in': bulk.record_ids}}
    if user.role == 'staff':
        query['assigned_to'] = user.id
    
    result = await db.customer_records.update_many(query, {'$set': update_fields})
    
    return {
        'message': f'{result.modified_count} records updated',
        'modified_count': result.modified_count
    }

@api_router.delete("/bulk/bonanza-records")
async def bulk_delete_bonanza_records(bulk: BulkDeleteRecords, user: User = Depends(get_admin_user)):
    """Bulk delete Bonanza records (Admin only)"""
    result = await db.bonanza_records.delete_many({'id': {'$in': bulk.record_ids}})
    return {'message': f'{result.deleted_count} records deleted', 'deleted_count': result.deleted_count}

@api_router.delete("/bulk/memberwd-records")
async def bulk_delete_memberwd_records(bulk: BulkDeleteRecords, user: User = Depends(get_admin_user)):
    """Bulk delete Member WD records (Admin only)"""
    result = await db.memberwd_records.delete_many({'id': {'$in': bulk.record_ids}})
    return {'message': f'{result.deleted_count} records deleted', 'deleted_count': result.deleted_count}

# ==================== NOTIFICATION ENDPOINTS ====================

@api_router.get("/notifications")
async def get_notifications(unread_only: bool = False, limit: int = 50, user: User = Depends(get_current_user)):
    """Get notifications for current user"""
    query = {'user_id': user.id}
    if unread_only:
        query['read'] = False
    
    notifications = await db.notifications.find(query, {'_id': 0}).sort('created_at', -1).limit(limit).to_list(limit)
    unread_count = await db.notifications.count_documents({'user_id': user.id, 'read': False})
    
    return {
        'notifications': notifications,
        'unread_count': unread_count
    }

@api_router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {'id': notification_id, 'user_id': user.id},
        {'$set': {'read': True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification marked as read'}

@api_router.patch("/notifications/read-all")
async def mark_all_notifications_read(user: User = Depends(get_current_user)):
    """Mark all notifications as read for current user"""
    result = await db.notifications.update_many(
        {'user_id': user.id, 'read': False},
        {'$set': {'read': True}}
    )
    return {'message': f'{result.modified_count} notifications marked as read'}

@api_router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, user: User = Depends(get_current_user)):
    """Delete a notification"""
    result = await db.notifications.delete_one({'id': notification_id, 'user_id': user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {'message': 'Notification deleted'}

# Helper function to create notification
async def create_notification(user_id: str, type: str, title: str, message: str, data: dict = None):
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
    return notification

# ==================== USER PREFERENCES ENDPOINTS ====================

class WidgetLayoutUpdate(BaseModel):
    widget_order: List[str]

@api_router.get("/user/preferences/widget-layout")
async def get_widget_layout(user: User = Depends(get_current_user)):
    """Get user's saved widget layout order"""
    prefs = await db.user_preferences.find_one({'user_id': user.id, 'type': 'widget_layout'}, {'_id': 0})
    if prefs:
        return {'widget_order': prefs.get('widget_order', [])}
    return {'widget_order': []}

@api_router.put("/user/preferences/widget-layout")
async def save_widget_layout(layout: WidgetLayoutUpdate, user: User = Depends(get_current_user)):
    """Save user's widget layout order"""
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

# ==================== ADVANCED ANALYTICS ENDPOINTS ====================

def get_date_range(period: str):
    """Get start and end dates for a period"""
    now = get_jakarta_now()
    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'yesterday':
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        now = start + timedelta(days=1)
    elif period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'quarter':
        start = now - timedelta(days=90)
    elif period == 'year':
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=30)  # default to month
    return start.isoformat(), now.isoformat()

@api_router.get("/analytics/staff-performance")
async def get_staff_performance_analytics(
    period: str = 'month',
    staff_id: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get comprehensive staff performance analytics"""
    start_date, end_date = get_date_range(period)
    
    # Build query for customer records
    record_query = {'status': 'assigned'}
    if staff_id:
        record_query['assigned_to'] = staff_id
    if product_id:
        record_query['product_id'] = product_id
    
    # Get all assigned records
    records = await db.customer_records.find(record_query, {'_id': 0}).to_list(100000)
    
    # Filter by date range for time-based analytics
    records_in_period = [r for r in records if r.get('assigned_at', '') >= start_date]
    
    # Get all staff
    staff_list = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    # Calculate per-staff metrics
    staff_metrics = []
    for staff in staff_list:
        staff_records = [r for r in records if r.get('assigned_to') == staff['id']]
        staff_records_period = [r for r in records_in_period if r.get('assigned_to') == staff['id']]
        
        total = len(staff_records)
        total_period = len(staff_records_period)
        
        # WhatsApp status counts
        wa_ada = len([r for r in staff_records if r.get('whatsapp_status') == 'ada'])
        wa_tidak = len([r for r in staff_records if r.get('whatsapp_status') == 'tidak'])
        wa_ceklis1 = len([r for r in staff_records if r.get('whatsapp_status') == 'ceklis1'])
        wa_checked = wa_ada + wa_tidak + wa_ceklis1
        
        # Response status counts
        resp_ya = len([r for r in staff_records if r.get('respond_status') == 'ya'])
        resp_tidak = len([r for r in staff_records if r.get('respond_status') == 'tidak'])
        resp_checked = resp_ya + resp_tidak
        
        staff_metrics.append({
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'total_assigned': total,
            'assigned_in_period': total_period,
            'whatsapp_ada': wa_ada,
            'whatsapp_tidak': wa_tidak,
            'whatsapp_ceklis1': wa_ceklis1,
            'whatsapp_checked': wa_checked,
            'whatsapp_rate': round((wa_ada / wa_checked * 100) if wa_checked > 0 else 0, 1),
            'respond_ya': resp_ya,
            'respond_tidak': resp_tidak,
            'respond_checked': resp_checked,
            'respond_rate': round((resp_ya / resp_checked * 100) if resp_checked > 0 else 0, 1),
            'completion_rate': round((wa_checked / total * 100) if total > 0 else 0, 1)
        })
    
    # Sort by total assigned descending
    staff_metrics.sort(key=lambda x: x['total_assigned'], reverse=True)
    
    # Calculate daily breakdown for chart
    daily_data = {}
    for record in records_in_period:
        date = record.get('assigned_at', '')[:10]
        if date not in daily_data:
            daily_data[date] = {'date': date, 'assigned': 0, 'wa_checked': 0, 'responded': 0}
        daily_data[date]['assigned'] += 1
        if record.get('whatsapp_status'):
            daily_data[date]['wa_checked'] += 1
        if record.get('respond_status') == 'ya':
            daily_data[date]['responded'] += 1
    
    daily_chart = sorted(daily_data.values(), key=lambda x: x['date'])
    
    # Overall summary
    total_all = len(records)
    wa_all_ada = len([r for r in records if r.get('whatsapp_status') == 'ada'])
    wa_all_tidak = len([r for r in records if r.get('whatsapp_status') == 'tidak'])
    wa_all_ceklis1 = len([r for r in records if r.get('whatsapp_status') == 'ceklis1'])
    wa_all_checked = wa_all_ada + wa_all_tidak + wa_all_ceklis1
    resp_all_ya = len([r for r in records if r.get('respond_status') == 'ya'])
    resp_all_tidak = len([r for r in records if r.get('respond_status') == 'tidak'])
    
    return {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'total_records': total_all,
            'records_in_period': len(records_in_period),
            'whatsapp_ada': wa_all_ada,
            'whatsapp_tidak': wa_all_tidak,
            'whatsapp_ceklis1': wa_all_ceklis1,
            'whatsapp_checked': wa_all_checked,
            'whatsapp_rate': round((wa_all_ada / wa_all_checked * 100) if wa_all_checked > 0 else 0, 1),
            'respond_ya': resp_all_ya,
            'respond_tidak': resp_all_tidak,
            'respond_rate': round((resp_all_ya / (resp_all_ya + resp_all_tidak) * 100) if (resp_all_ya + resp_all_tidak) > 0 else 0, 1)
        },
        'staff_metrics': staff_metrics,
        'daily_chart': daily_chart
    }

@api_router.get("/analytics/business")
async def get_business_analytics(
    period: str = 'month',
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get business analytics including OMSET trends"""
    start_date, end_date = get_date_range(period)
    
    # Get OMSET records
    omset_query = {}
    if product_id:
        omset_query['product_id'] = product_id
    
    omset_records = await db.omset_records.find(omset_query, {'_id': 0}).to_list(100000)
    
    # Filter by date range
    omset_in_period = [r for r in omset_records if r.get('date', '') >= start_date[:10]]
    
    # Calculate OMSET by day
    daily_omset = {}
    for record in omset_in_period:
        date = record.get('date', '')
        if date not in daily_omset:
            daily_omset[date] = {'date': date, 'total': 0, 'count': 0, 'ndp': 0, 'rdp': 0}
        daily_omset[date]['total'] += record.get('depo_total', 0)
        daily_omset[date]['count'] += 1
        if record.get('customer_type') == 'NDP':
            daily_omset[date]['ndp'] += 1
        else:
            daily_omset[date]['rdp'] += 1
    
    omset_chart = sorted(daily_omset.values(), key=lambda x: x['date'])
    
    # Calculate OMSET by product
    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    product_omset = []
    for product in products:
        prod_records = [r for r in omset_in_period if r.get('product_id') == product['id']]
        total = sum(r.get('depo_total', 0) for r in prod_records)
        count = len(prod_records)
        product_omset.append({
            'product_id': product['id'],
            'product_name': product['name'],
            'total_omset': total,
            'record_count': count,
            'avg_omset': round(total / count, 2) if count > 0 else 0
        })
    
    product_omset.sort(key=lambda x: x['total_omset'], reverse=True)
    
    # NDP vs RDP analysis
    total_ndp = len([r for r in omset_in_period if r.get('customer_type') == 'NDP'])
    total_rdp = len([r for r in omset_in_period if r.get('customer_type') == 'RDP'])
    ndp_omset = sum(r.get('depo_total', 0) for r in omset_in_period if r.get('customer_type') == 'NDP')
    rdp_omset = sum(r.get('depo_total', 0) for r in omset_in_period if r.get('customer_type') == 'RDP')
    
    # Database utilization
    databases = await db.databases.find({}, {'_id': 0}).to_list(1000)
    db_utilization = []
    for database in databases:
        total_records = await db.customer_records.count_documents({'database_id': database['id']})
        assigned = await db.customer_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        available = total_records - assigned
        db_utilization.append({
            'database_id': database['id'],
            'database_name': database.get('filename', 'Unknown'),
            'product_name': database.get('product_name', 'Unknown'),
            'total_records': total_records,
            'assigned': assigned,
            'available': available,
            'utilization_rate': round((assigned / total_records * 100) if total_records > 0 else 0, 1)
        })
    
    db_utilization.sort(key=lambda x: x['utilization_rate'], reverse=True)
    
    # Overall summary
    total_omset = sum(r.get('depo_total', 0) for r in omset_in_period)
    
    return {
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'summary': {
            'total_omset': total_omset,
            'total_records': len(omset_in_period),
            'avg_omset_per_record': round(total_omset / len(omset_in_period), 2) if omset_in_period else 0,
            'ndp_count': total_ndp,
            'rdp_count': total_rdp,
            'ndp_omset': ndp_omset,
            'rdp_omset': rdp_omset,
            'ndp_percentage': round((total_ndp / (total_ndp + total_rdp) * 100) if (total_ndp + total_rdp) > 0 else 0, 1)
        },
        'omset_chart': omset_chart,
        'product_omset': product_omset,
        'database_utilization': db_utilization
    }

# ==================== EXPORT ENDPOINTS ====================

@api_router.get("/export/customer-records")
async def export_customer_records(
    format: str = 'xlsx',
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export customer records with filters"""
    query = {}
    if product_id:
        query['product_id'] = product_id
    if status:
        query['status'] = status
    if staff_id:
        query['assigned_to'] = staff_id
    
    records = await db.customer_records.find(query, {'_id': 0}).to_list(100000)
    
    # Filter by date range
    if start_date:
        records = [r for r in records if r.get('assigned_at', r.get('created_at', '')) >= start_date]
    if end_date:
        records = [r for r in records if r.get('assigned_at', r.get('created_at', '')) <= end_date]
    
    # Flatten records for export
    export_data = []
    for record in records:
        row = {
            'ID': record.get('id', ''),
            'Database': record.get('database_name', ''),
            'Product': record.get('product_name', ''),
            'Status': record.get('status', ''),
            'Assigned To': record.get('assigned_to_name', ''),
            'Assigned At': record.get('assigned_at', ''),
            'WhatsApp Status': record.get('whatsapp_status', ''),
            'Respond Status': record.get('respond_status', ''),
        }
        # Add row_data fields
        if record.get('row_data'):
            for key, value in record['row_data'].items():
                row[key] = value
        export_data.append(row)
    
    df = pd.DataFrame(export_data)
    
    # Generate file
    filename = f"customer_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        # Save to temp file
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

@api_router.get("/export/omset")
async def export_omset_data(
    format: str = 'xlsx',
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    customer_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export OMSET data with filters"""
    query = {}
    if product_id:
        query['product_id'] = product_id
    if staff_id:
        query['staff_id'] = staff_id
    if customer_type:
        query['customer_type'] = customer_type
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    if start_date:
        records = [r for r in records if r.get('date', '') >= start_date]
    if end_date:
        records = [r for r in records if r.get('date', '') <= end_date]
    
    export_data = []
    for record in records:
        export_data.append({
            'Date': record.get('date', ''),
            'Customer Name': record.get('customer_name', ''),
            'Customer ID': record.get('customer_id', ''),
            'Product': record.get('product_name', ''),
            'Staff': record.get('staff_name', ''),
            'Nominal': record.get('nominal', 0),
            'Kelipatan': record.get('kelipatan', 1),
            'Depo Total': record.get('depo_total', 0),
            'Customer Type': record.get('customer_type', ''),
            'Keterangan': record.get('keterangan', ''),
            'Created At': record.get('created_at', '')
        })
    
    df = pd.DataFrame(export_data)
    
    filename = f"omset_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

@api_router.get("/export/staff-report")
async def export_staff_performance_report(
    format: str = 'xlsx',
    period: str = 'month',
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export staff performance report"""
    # Get staff performance data
    analytics = await get_staff_performance_analytics(period=period, user=user)
    
    export_data = []
    for staff in analytics['staff_metrics']:
        export_data.append({
            'Staff Name': staff['staff_name'],
            'Total Assigned': staff['total_assigned'],
            'Assigned in Period': staff['assigned_in_period'],
            'WhatsApp Ada': staff['whatsapp_ada'],
            'WhatsApp Tidak': staff['whatsapp_tidak'],
            'WhatsApp Ceklis1': staff['whatsapp_ceklis1'],
            'WhatsApp Checked': staff['whatsapp_checked'],
            'WhatsApp Rate (%)': staff['whatsapp_rate'],
            'Respond Ya': staff['respond_ya'],
            'Respond Tidak': staff['respond_tidak'],
            'Respond Rate (%)': staff['respond_rate'],
            'Completion Rate (%)': staff['completion_rate']
        })
    
    df = pd.DataFrame(export_data)
    
    filename = f"staff_performance_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

@api_router.get("/export/reserved-members")
async def export_reserved_members(
    format: str = 'xlsx',
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export reserved members with filters"""
    query = {}
    if product_id:
        query['product_id'] = product_id
    if staff_id:
        query['staff_id'] = staff_id
    if status:
        query['status'] = status
    
    records = await db.reserved_members.find(query, {'_id': 0}).to_list(100000)
    
    export_data = []
    for record in records:
        export_data.append({
            'Customer Name': record.get('customer_name', ''),
            'Product': record.get('product_name', ''),
            'Staff': record.get('staff_name', ''),
            'Status': record.get('status', ''),
            'Created By': record.get('created_by_name', ''),
            'Created At': record.get('created_at', ''),
            'Approved By': record.get('approved_by_name', ''),
            'Approved At': record.get('approved_at', '')
        })
    
    df = pd.DataFrame(export_data)
    
    filename = f"reserved_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

@api_router.get("/export/bonanza-records")
async def export_bonanza_records(
    format: str = 'xlsx',
    database_id: Optional[str] = None,
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export DB Bonanza records with filters"""
    query = {}
    if database_id:
        query['database_id'] = database_id
    if product_id:
        query['product_id'] = product_id
    if staff_id:
        query['assigned_to'] = staff_id
    if status:
        query['status'] = status
    
    records = await db.bonanza_records.find(query, {'_id': 0}).to_list(100000)
    
    export_data = []
    for record in records:
        row = {
            'Database': record.get('database_name', ''),
            'Product': record.get('product_name', ''),
            'Status': record.get('status', ''),
            'Assigned To': record.get('assigned_to_name', ''),
            'Assigned At': record.get('assigned_at', '')
        }
        if record.get('row_data'):
            for key, value in record['row_data'].items():
                row[key] = value
        export_data.append(row)
    
    df = pd.DataFrame(export_data)
    
    filename = f"bonanza_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

@api_router.get("/export/memberwd-records")
async def export_memberwd_records(
    format: str = 'xlsx',
    database_id: Optional[str] = None,
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    status: Optional[str] = None,
    token: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Export Member WD records with filters"""
    query = {}
    if database_id:
        query['database_id'] = database_id
    if product_id:
        query['product_id'] = product_id
    if staff_id:
        query['assigned_to'] = staff_id
    if status:
        query['status'] = status
    
    records = await db.memberwd_records.find(query, {'_id': 0}).to_list(100000)
    
    export_data = []
    for record in records:
        row = {
            'Database': record.get('database_name', ''),
            'Product': record.get('product_name', ''),
            'Status': record.get('status', ''),
            'Assigned To': record.get('assigned_to_name', ''),
            'Assigned At': record.get('assigned_at', '')
        }
        if record.get('row_data'):
            for key, value in record['row_data'].items():
                row[key] = value
        export_data.append(row)
    
    df = pd.DataFrame(export_data)
    
    filename = f"memberwd_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(
            path=temp_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"{filename}.xlsx"
        )

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()