# Member WD CRM Routes

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import uuid
import random
import pandas as pd
import io
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Member WD CRM"])

class MemberWDAssignment(BaseModel):
    record_ids: List[str]
    staff_id: str

class RandomMemberWDAssignment(BaseModel):
    database_id: str
    staff_id: str
    quantity: int
    username_field: str = "Username"

class RecordValidation(BaseModel):
    record_ids: List[str]
    is_valid: bool
    reason: Optional[str] = None

@router.post("/memberwd/upload")
async def upload_memberwd_database(
    file: UploadFile = File(...),
    name: str = Form(...),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Upload a new Member WD database (Admin only)"""
    db = get_db()
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
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

@router.get("/memberwd/databases")
async def get_memberwd_databases(product_id: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all Member WD databases (Admin only)"""
    db = get_db()
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
        if 'product_id' not in database:
            database['product_id'] = ''
            database['product_name'] = 'Unknown'
    
    return databases

@router.get("/memberwd/databases/{database_id}/records")
async def get_memberwd_records(database_id: str, status: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all records from a Member WD database (Admin only)"""
    db = get_db()
    query = {'database_id': database_id}
    if status:
        query['status'] = status
    
    records = await db.memberwd_records.find(query, {'_id': 0}).sort('row_number', 1).to_list(100000)
    return records

@router.post("/memberwd/assign")
async def assign_memberwd_records(assignment: MemberWDAssignment, user: User = Depends(get_admin_user)):
    """Assign Member WD records to a staff member (Admin only)"""
    db = get_db()
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

@router.post("/memberwd/assign-random")
async def assign_random_memberwd_records(assignment: RandomMemberWDAssignment, user: User = Depends(get_admin_user)):
    """Randomly assign Member WD records to a staff member, skipping reserved members (Admin only)"""
    db = get_db()
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    reserved_members = await db.reserved_members.find({}, {'_id': 0, 'customer_name': 1}).to_list(100000)
    reserved_names = set(str(m['customer_name']).lower().strip() for m in reserved_members if m.get('customer_name'))
    
    available_records = await db.memberwd_records.find(
        {'database_id': assignment.database_id, 'status': 'available'},
        {'_id': 0}
    ).to_list(100000)
    
    eligible_records = []
    skipped_count = 0
    for record in available_records:
        username = record.get('row_data', {}).get(assignment.username_field, '')
        # Convert to string in case the value is a number
        username_str = str(username).lower().strip() if username else ''
        if username_str and username_str in reserved_names:
            skipped_count += 1
            continue
        eligible_records.append(record)
    
    if len(eligible_records) == 0:
        raise HTTPException(status_code=400, detail="No eligible records available")
    
    if assignment.quantity > len(eligible_records):
        raise HTTPException(status_code=400, detail=f"Only {len(eligible_records)} eligible records available")
    
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
        'remaining_eligible': len(eligible_records) - assignment.quantity
    }

@router.delete("/memberwd/databases/{database_id}")
async def delete_memberwd_database(database_id: str, user: User = Depends(get_admin_user)):
    """Delete a Member WD database and all its records (Admin only)"""
    db = get_db()
    await db.memberwd_records.delete_many({'database_id': database_id})
    await db.memberwd_databases.delete_one({'id': database_id})
    return {'message': 'Database deleted successfully'}

@router.get("/memberwd/staff/records")
async def get_staff_memberwd_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get Member WD records assigned to the current staff"""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    query = {'assigned_to': user.id, 'status': 'assigned'}
    if product_id:
        query['product_id'] = product_id
    
    records = await db.memberwd_records.find(query, {'_id': 0}).sort('assigned_at', -1).to_list(10000)
    
    for record in records:
        if 'product_id' not in record:
            record['product_id'] = ''
            record['product_name'] = 'Unknown'
    
    return records

@router.get("/memberwd/staff")
async def get_memberwd_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
