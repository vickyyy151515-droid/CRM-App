# Core Database and Records Management Routes
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import uuid
import os
import pandas as pd

from .deps import get_db, get_current_user, get_admin_user, get_jakarta_now, User
from .notifications import create_notification

router = APIRouter(tags=["Records Management"])

# File upload directory
ROOT_DIR = Path(__file__).parent.parent
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

# ==================== PYDANTIC MODELS ====================

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
    whatsapp_status: Optional[str] = None

class RespondStatusUpdate(BaseModel):
    respond_status: Optional[str] = None

class ReservedMember(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_name: str
    phone_number: Optional[str] = None
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
    phone_number: Optional[str] = None
    product_id: str
    staff_id: Optional[str] = None

class BulkReservedMemberCreate(BaseModel):
    customer_names: List[str]  # List of customer names (one per line)
    product_id: str
    staff_id: str

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

class BatchTitleUpdate(BaseModel):
    title: str

# ==================== HELPER FUNCTIONS ====================

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

# ==================== DATABASE ENDPOINTS ====================

@router.post("/databases", response_model=Database)
async def upload_database(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    db = get_db()
    
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

@router.get("/databases/with-stats")
async def get_databases_with_stats(search: Optional[str] = None, product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get all databases with real-time record status counts"""
    db = get_db()
    query = {}
    if search:
        query['$or'] = [
            {'filename': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    if product_id:
        query['product_id'] = product_id
    
    databases = await db.databases.find(query, {'_id': 0}).sort('uploaded_at', -1).to_list(1000)
    
    # Get all database IDs for aggregation
    db_ids = [d['id'] for d in databases]
    
    # Use aggregation to get counts for all databases in one query (fixes N+1 problem)
    counts_pipeline = [
        {'$match': {'database_id': {'$in': db_ids}}},
        {'$group': {
            '_id': {'database_id': '$database_id', 'status': '$status'},
            'count': {'$sum': 1}
        }}
    ]
    counts_result = await db.customer_records.aggregate(counts_pipeline).to_list(10000)
    
    # Build lookup dictionary
    counts_lookup = {}
    for item in counts_result:
        db_id = item['_id']['database_id']
        status = item['_id']['status']
        if db_id not in counts_lookup:
            counts_lookup[db_id] = {'available': 0, 'requested': 0, 'assigned': 0}
        counts_lookup[db_id][status] = item['count']
    
    result = []
    for db_item in databases:
        if isinstance(db_item['uploaded_at'], str):
            db_item['uploaded_at'] = datetime.fromisoformat(db_item['uploaded_at'])
        
        # Get record counts from lookup
        counts = counts_lookup.get(db_item['id'], {'available': 0, 'requested': 0, 'assigned': 0})
        available_count = counts.get('available', 0)
        requested_count = counts.get('requested', 0)
        assigned_count = counts.get('assigned', 0)
        total_count = available_count + requested_count + assigned_count
        
        result.append({
            'id': db_item['id'],
            'filename': db_item['filename'],
            'file_type': db_item['file_type'],
            'file_size': db_item['file_size'],
            'description': db_item.get('description'),
            'product_id': db_item.get('product_id'),
            'product_name': db_item.get('product_name', 'Unknown'),
            'uploaded_by': db_item['uploaded_by'],
            'uploaded_by_name': db_item['uploaded_by_name'],
            'uploaded_at': db_item['uploaded_at'].isoformat() if hasattr(db_item['uploaded_at'], 'isoformat') else db_item['uploaded_at'],
            'total_records': total_count,
            'available_count': available_count,
            'requested_count': requested_count,
            'assigned_count': assigned_count
        })
    
    return result

@router.get("/databases", response_model=List[Database])
async def get_databases(search: Optional[str] = None, product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    db = get_db()
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

@router.get("/databases/{database_id}", response_model=Database)
async def get_database(database_id: str, user: User = Depends(get_current_user)):
    db = get_db()
    database = await db.databases.find_one({'id': database_id}, {'_id': 0})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if isinstance(database['uploaded_at'], str):
        database['uploaded_at'] = datetime.fromisoformat(database['uploaded_at'])
    
    return Database(**database)

@router.delete("/databases/{database_id}")
async def delete_database(database_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
    database = await db.databases.find_one({'id': database_id})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if os.path.exists(database['file_path']):
        os.remove(database['file_path'])
    
    await db.databases.delete_one({'id': database_id})
    await db.customer_records.delete_many({'database_id': database_id})
    await db.download_requests.delete_many({'database_id': database_id})
    
    return {'message': 'Database deleted successfully'}

@router.get("/databases/{database_id}/records", response_model=List[CustomerRecord])
async def get_database_records(database_id: str, status: Optional[str] = None, user: User = Depends(get_current_user)):
    db = get_db()
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

# ==================== DOWNLOAD REQUEST ENDPOINTS ====================

@router.post("/download-requests", response_model=DownloadRequest)
async def create_download_request(request_data: DownloadRequestCreate, user: User = Depends(get_current_user)):
    db = get_db()
    
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can request records")
    
    database = await db.databases.find_one({'id': request_data.database_id})
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")
    
    if request_data.record_count <= 0:
        raise HTTPException(status_code=400, detail="Record count must be greater than 0")
    
    # Get all reserved member names for this product (case-insensitive)
    product_id = database.get('product_id')
    reserved_members = await db.reserved_members.find(
        {'product_id': product_id, 'status': {'$in': ['pending', 'approved']}},
        {'_id': 0, 'customer_name': 1}
    ).to_list(10000)
    
    # Create a set of reserved names (normalized to uppercase for case-insensitive comparison)
    reserved_names = set()
    for member in reserved_members:
        name = member.get('customer_name', '').strip().upper()
        if name:
            reserved_names.add(name)
    
    # Get all available records from the database (get more than needed to account for duplicates)
    # Fetch up to 3x the requested amount to have enough replacements
    fetch_limit = min(request_data.record_count * 3, 10000)
    all_available_records = await db.customer_records.find(
        {'database_id': request_data.database_id, 'status': 'available'},
        {'_id': 0}
    ).sort('row_number', 1).to_list(fetch_limit)
    
    if len(all_available_records) == 0:
        raise HTTPException(status_code=400, detail="No available records in this database")
    
    # Filter out records that have usernames matching Reserved Members' customer_name
    valid_records = []
    skipped_records = []
    
    for record in all_available_records:
        row_data = record.get('row_data', {})
        username = None
        
        # Check for username field (case-insensitive keys)
        for key in row_data:
            key_lower = key.lower()
            if key_lower in ['username', 'user_name', 'user', 'id', 'userid', 'user_id']:
                username = row_data[key]
                break
        
        # Normalize username for comparison against reserved customer_name
        if username:
            normalized_username = str(username).strip().upper()
            
            if normalized_username in reserved_names:
                # This record's username matches a reserved customer_name, skip it
                skipped_records.append({
                    'record_id': record['id'],
                    'username': username,
                    'reason': 'Reserved by another staff'
                })
                continue
        
        valid_records.append(record)
        
        # Stop once we have enough valid records
        if len(valid_records) >= request_data.record_count:
            break
    
    # Check if we have enough valid records
    if len(valid_records) < request_data.record_count:
        available_count = len(valid_records)
        reserved_count = len(skipped_records)
        raise HTTPException(
            status_code=400, 
            detail=f"Only {available_count} non-reserved records available ({reserved_count} records skipped due to Reserved Member duplicates). You requested {request_data.record_count}."
        )
    
    # Use only the requested number of valid records
    selected_records = valid_records[:request_data.record_count]
    record_ids = [record['id'] for record in selected_records]
    
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
    # Store info about skipped records for transparency
    doc['skipped_reserved_count'] = len(skipped_records)
    
    await db.download_requests.insert_one(doc)
    
    for record_id in record_ids:
        await db.customer_records.update_one(
            {'id': record_id},
            {'$set': {'status': 'requested'}}
        )
    
    return request

@router.get("/download-requests", response_model=List[DownloadRequest])
async def get_download_requests(user: User = Depends(get_current_user)):
    db = get_db()
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

@router.patch("/download-requests/{request_id}/approve")
async def approve_request(request_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
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
    
    await create_notification(
        user_id=request['requested_by'],
        type='request_approved',
        title='Request Approved',
        message=f'Your request for {request["record_count"]} records from {request["database_name"]} has been approved',
        data={'request_id': request_id, 'record_count': request['record_count'], 'database_name': request['database_name']}
    )
    
    return {'message': 'Request approved and records assigned'}

@router.patch("/download-requests/{request_id}/reject")
async def reject_request(request_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
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
    
    await create_notification(
        user_id=request['requested_by'],
        type='request_rejected',
        title='Request Rejected',
        message=f'Your request for {request["record_count"]} records from {request["database_name"]} has been rejected',
        data={'request_id': request_id, 'database_name': request['database_name']}
    )
    
    return {'message': 'Request rejected'}

# ==================== MY RECORDS ENDPOINTS ====================

@router.get("/my-request-batches")
async def get_my_request_batches(user: User = Depends(get_current_user)):
    """Get all approved request batches for the current staff member"""
    db = get_db()
    
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can view request batches")
    
    requests = await db.download_requests.find(
        {'requested_by': user.id, 'status': 'approved'},
        {'_id': 0}
    ).sort('reviewed_at', -1).to_list(1000)
    
    batches = []
    for req in requests:
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
    
    legacy_titles = {}
    legacy_title_docs = await db.batch_titles.find({'user_id': user.id}, {'_id': 0}).to_list(100)
    for doc in legacy_title_docs:
        legacy_titles[doc['batch_id']] = doc.get('title')
    
    legacy_records_all = await db.customer_records.find(
        {
            'assigned_to': user.id,
            'status': 'assigned',
            '$or': [{'request_id': {'$exists': False}}, {'request_id': None}]
        },
        {'_id': 0, 'database_id': 1, 'database_name': 1, 'product_name': 1, 'whatsapp_status': 1, 'respond_status': 1}
    ).to_list(10000)
    
    if legacy_records_all:
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

@router.patch("/my-request-batches/{batch_id}/title")
async def update_batch_title(batch_id: str, title_update: BatchTitleUpdate, user: User = Depends(get_current_user)):
    """Update the custom title for a batch"""
    db = get_db()
    
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can update batch titles")
    
    if batch_id.startswith('legacy_'):
        database_id = batch_id.replace('legacy_', '')
        await db.batch_titles.update_one(
            {'batch_id': batch_id, 'user_id': user.id},
            {'$set': {'title': title_update.title, 'database_id': database_id}},
            upsert=True
        )
    else:
        request = await db.download_requests.find_one({'id': batch_id, 'requested_by': user.id})
        if not request:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        await db.download_requests.update_one(
            {'id': batch_id},
            {'$set': {'custom_title': title_update.title}}
        )
    
    return {'message': 'Title updated successfully'}

@router.get("/my-assigned-records-by-batch")
async def get_my_assigned_records_by_batch(request_id: str, user: User = Depends(get_current_user)):
    """Get assigned records for a specific request batch"""
    db = get_db()
    
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can view assigned records")
    
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

@router.get("/download/{request_id}")
async def download_database(request_id: str, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="File download is no longer supported. Use assigned records instead.")

@router.get("/my-assigned-records", response_model=List[CustomerRecord])
async def get_my_assigned_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    db = get_db()
    
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

# ==================== STATUS UPDATE ENDPOINTS ====================

@router.patch("/customer-records/{record_id}/whatsapp-status")
async def update_whatsapp_status(record_id: str, status_update: WhatsAppStatusUpdate, user: User = Depends(get_current_user)):
    db = get_db()
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

@router.patch("/customer-records/{record_id}/respond-status")
async def update_respond_status(record_id: str, status_update: RespondStatusUpdate, user: User = Depends(get_current_user)):
    db = get_db()
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

# ==================== RESERVED MEMBERS ENDPOINTS ====================

@router.post("/reserved-members", response_model=ReservedMember)
async def create_reserved_member(member_data: ReservedMemberCreate, user: User = Depends(get_current_user)):
    db = get_db()
    
    product = await db.products.find_one({'id': member_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
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


@router.post("/reserved-members/bulk")
async def bulk_create_reserved_members(bulk_data: BulkReservedMemberCreate, user: User = Depends(get_admin_user)):
    """
    Bulk add reserved members (Admin only).
    Creates multiple reservations for the same product and staff.
    Skips duplicates and returns summary of results.
    """
    db = get_db()
    
    # Validate product
    product = await db.products.find_one({'id': bulk_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Validate staff
    staff = await db.users.find_one({'id': bulk_data.staff_id})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Clean and deduplicate customer names
    customer_names = []
    for name in bulk_data.customer_names:
        cleaned = name.strip()
        if cleaned and cleaned not in customer_names:
            customer_names.append(cleaned)
    
    if not customer_names:
        raise HTTPException(status_code=400, detail="No valid customer names provided")
    
    # Process each customer name
    added = []
    skipped = []
    
    for customer_name in customer_names:
        # Check for existing reservation (case-insensitive)
        existing = await db.reserved_members.find_one({
            'customer_name': {'$regex': f'^{customer_name}$', '$options': 'i'},
            'product_id': bulk_data.product_id,
            'status': {'$in': ['pending', 'approved']}
        })
        
        if existing:
            owner = await db.users.find_one({'id': existing['staff_id']})
            owner_name = owner['name'] if owner else 'Unknown'
            skipped.append({
                'customer_name': customer_name,
                'reason': f"Already reserved by {owner_name}"
            })
            continue
        
        # Create the reservation
        member = ReservedMember(
            customer_name=customer_name,
            product_id=bulk_data.product_id,
            product_name=product['name'],
            staff_id=bulk_data.staff_id,
            staff_name=staff['name'],
            status='approved',
            created_by=user.id,
            created_by_name=user.name,
            approved_at=get_jakarta_now(),
            approved_by=user.id,
            approved_by_name=user.name
        )
        
        doc = member.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['approved_at'] = doc['approved_at'].isoformat()
        
        await db.reserved_members.insert_one(doc)
        added.append(customer_name)
    
    return {
        'success': True,
        'total_processed': len(customer_names),
        'added_count': len(added),
        'skipped_count': len(skipped),
        'added': added,
        'skipped': skipped,
        'product_name': product['name'],
        'staff_name': staff['name']
    }


@router.get("/reserved-members", response_model=List[ReservedMember])
async def get_reserved_members(status: Optional[str] = None, product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    db = get_db()
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
        if 'product_id' not in member:
            member['product_id'] = ''
            member['product_name'] = 'Unknown'
    
    return members

@router.patch("/reserved-members/{member_id}/approve")
async def approve_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
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
    
    await create_notification(
        user_id=member['staff_id'],
        type='reserved_approved',
        title='Reservation Approved',
        message=f'Your reservation for "{member["customer_name"]}" in {member.get("product_name", "Unknown")} has been approved',
        data={'member_id': member_id, 'customer_name': member['customer_name']}
    )
    
    return {'message': 'Reserved member approved'}

@router.patch("/reserved-members/{member_id}/reject")
async def reject_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    if member['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Member already processed")
    
    await create_notification(
        user_id=member['staff_id'],
        type='reserved_rejected',
        title='Reservation Rejected',
        message=f'Your reservation for "{member["customer_name"]}" in {member.get("product_name", "Unknown")} has been rejected',
        data={'customer_name': member['customer_name']}
    )
    
    await db.reserved_members.delete_one({'id': member_id})
    
    return {'message': 'Reserved member request rejected'}

@router.delete("/reserved-members/{member_id}")
async def delete_reserved_member(member_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
    member = await db.reserved_members.find_one({'id': member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Reserved member not found")
    
    await db.reserved_members.delete_one({'id': member_id})
    
    return {'message': 'Reserved member deleted'}

@router.patch("/reserved-members/{member_id}/move")
async def move_reserved_member(member_id: str, new_staff_id: str, user: User = Depends(get_admin_user)):
    db = get_db()
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

# ==================== DOWNLOAD HISTORY ====================

@router.get("/download-history", response_model=List[DownloadHistory])
async def get_download_history(user: User = Depends(get_current_user)):
    db = get_db()
    query = {}
    if user.role == 'staff':
        query['downloaded_by'] = user.id
    
    history = await db.download_history.find(query, {'_id': 0}).sort('downloaded_at', -1).to_list(1000)
    
    for item in history:
        if isinstance(item['downloaded_at'], str):
            item['downloaded_at'] = datetime.fromisoformat(item['downloaded_at'])
    
    return history
