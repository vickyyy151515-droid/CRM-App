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
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
import io

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
security = HTTPBearer()

UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    downloaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
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
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
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
                'assigned_at': datetime.now(timezone.utc).isoformat(),
                'request_id': request_id
            }}
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
            'reviewed_at': datetime.now(timezone.utc).isoformat(),
            'reviewed_by': user.id,
            'reviewed_by_name': user.name
        }}
    )
    
    for record_id in request['record_ids']:
        await db.customer_records.update_one(
            {'id': record_id},
            {'$set': {'status': 'available'}}
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
        }, {'_id': 0, 'whatsapp_status': 1}).to_list(10000)
        
        record_count = len(batch_records)
        ada_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'ada')
        ceklis1_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'ceklis1')
        tidak_count = sum(1 for r in batch_records if r.get('whatsapp_status') == 'tidak')
        
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
        {'_id': 0, 'database_id': 1, 'database_name': 1, 'product_name': 1, 'whatsapp_status': 1}
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
                    'tidak_count': 0
                }
            legacy_by_db[db_id]['count'] += 1
            if rec.get('whatsapp_status') == 'ada':
                legacy_by_db[db_id]['ada_count'] += 1
            elif rec.get('whatsapp_status') == 'ceklis1':
                legacy_by_db[db_id]['ceklis1_count'] += 1
            elif rec.get('whatsapp_status') == 'tidak':
                legacy_by_db[db_id]['tidak_count'] += 1
        
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
            'whatsapp_status_updated_at': datetime.now(timezone.utc).isoformat()
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
            'respond_status_updated_at': datetime.now(timezone.utc).isoformat()
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
            approved_at=datetime.now(timezone.utc),
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
            'approved_at': datetime.now(timezone.utc).isoformat(),
            'approved_by': user.id,
            'approved_by_name': user.name
        }}
    )
    
    return {'message': 'Reserved member approved'}

@api_router.patch("/reserved-members/{member_id}/reject")
async def reject_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    if member['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Member already processed")
    
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
    update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()
    
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