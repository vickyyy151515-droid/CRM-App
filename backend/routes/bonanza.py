# DB Bonanza Routes

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import uuid
import random
import pandas as pd
import io
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["DB Bonanza"])

class BonanzaAssignment(BaseModel):
    record_ids: List[str]
    staff_id: str

class RandomBonanzaAssignment(BaseModel):
    database_id: str
    staff_id: str
    quantity: int
    username_field: str = "Username"

class RecordValidation(BaseModel):
    record_ids: List[str]
    is_valid: bool
    reason: Optional[str] = None


class BonanzaSettings(BaseModel):
    auto_replace_invalid: bool = False
    max_replacements_per_batch: int = 10


class RecallRecordsRequest(BaseModel):
    record_ids: List[str]


# Default settings
DEFAULT_BONANZA_SETTINGS = {
    'id': 'bonanza_settings',
    'auto_replace_invalid': False,
    'max_replacements_per_batch': 10
}


@router.get("/bonanza/admin/settings")
async def get_bonanza_settings(user: User = Depends(get_admin_user)):
    """Get DB Bonanza settings"""
    db = get_db()
    settings = await db.app_settings.find_one({'id': 'bonanza_settings'}, {'_id': 0})
    if not settings:
        await db.app_settings.insert_one(DEFAULT_BONANZA_SETTINGS.copy())
        settings = DEFAULT_BONANZA_SETTINGS.copy()
    return settings


@router.put("/bonanza/admin/settings")
async def update_bonanza_settings(data: BonanzaSettings, user: User = Depends(get_admin_user)):
    """Update DB Bonanza settings"""
    db = get_db()
    now = get_jakarta_now()
    
    await db.app_settings.update_one(
        {'id': 'bonanza_settings'},
        {'$set': {
            'auto_replace_invalid': data.auto_replace_invalid,
            'max_replacements_per_batch': data.max_replacements_per_batch,
            'updated_at': now.isoformat(),
            'updated_by': user.name
        }},
        upsert=True
    )
    
    return {
        'success': True,
        'message': 'Settings updated successfully',
        'settings': {
            'auto_replace_invalid': data.auto_replace_invalid,
            'max_replacements_per_batch': data.max_replacements_per_batch
        }
    }


@router.post("/bonanza/admin/sanitize-records/{database_id}")
async def sanitize_bonanza_records(database_id: str, user: User = Depends(get_admin_user)):
    """Sanitize all records in a database to fix data issues"""
    db = get_db()
    
    # Get all records for this database
    records = await db.bonanza_records.find({'database_id': database_id}, {'_id': 0}).to_list(100000)
    
    if not records:
        raise HTTPException(status_code=404, detail="No records found for this database")
    
    fixed_count = 0
    for record in records:
        row_data = record.get('row_data', {})
        sanitized = {}
        needs_fix = False
        
        for key, value in row_data.items():
            # Check if value needs sanitization
            if value is None or (isinstance(value, float) and (value != value)):  # NaN check
                sanitized[str(key)] = ''
                needs_fix = True
            elif isinstance(value, (int, float)):
                sanitized[str(key)] = str(value) if not float(value).is_integer() else str(int(value))
                if str(key) != key:
                    needs_fix = True
            else:
                try:
                    sanitized[str(key)] = str(value) if value is not None else ''
                except Exception:
                    sanitized[str(key)] = ''
                    needs_fix = True
        
        if needs_fix or row_data != sanitized:
            await db.bonanza_records.update_one(
                {'id': record['id']},
                {'$set': {'row_data': sanitized}}
            )
            fixed_count += 1
    
    return {
        'success': True,
        'total_records': len(records),
        'fixed_count': fixed_count,
        'message': f'Sanitized {fixed_count} records out of {len(records)} total'
    }


@router.post("/bonanza/upload")
async def upload_bonanza_database(
    file: UploadFile = File(...),
    name: str = Form(...),
    product_id: str = Form(...),
    user: User = Depends(get_admin_user)
):
    """Upload a new Bonanza database (Admin only)"""
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
    
    await db.bonanza_databases.insert_one(database_doc)
    
    records = []
    for idx, row in df.iterrows():
        # Sanitize row data to handle NaN, NaT, and other special values
        row_data = {}
        for col, value in row.items():
            if pd.isna(value):
                row_data[str(col)] = ''
            elif isinstance(value, (int, float)):
                if pd.isna(value) or value != value:  # Check for NaN
                    row_data[str(col)] = ''
                else:
                    row_data[str(col)] = str(value) if not float(value).is_integer() else str(int(value))
            else:
                # Convert to string and handle any encoding issues
                try:
                    row_data[str(col)] = str(value) if value is not None else ''
                except Exception:
                    row_data[str(col)] = ''
        
        record = {
            'id': str(uuid.uuid4()),
            'database_id': database_id,
            'database_name': name,
            'product_id': product_id,
            'product_name': product['name'],
            'row_number': idx + 1,
            'row_data': row_data,
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

@router.get("/bonanza/databases")
async def get_bonanza_databases(product_id: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all Bonanza databases (Admin only)"""
    db = get_db()
    query = {}
    if product_id:
        query['product_id'] = product_id
    
    databases = await db.bonanza_databases.find(query, {'_id': 0}).sort('uploaded_at', -1).to_list(1000)
    
    # Get reserved members for excluded count
    reserved_members = await db.reserved_members.find({'status': 'approved'}, {'_id': 0, 'customer_id': 1, 'customer_name': 1}).to_list(100000)
    reserved_ids = set()
    for m in reserved_members:
        if m.get('customer_id'):
            reserved_ids.add(str(m['customer_id']).strip().upper())
        if m.get('customer_name'):
            reserved_ids.add(str(m['customer_name']).strip().upper())
    
    for database in databases:
        total = await db.bonanza_records.count_documents({'database_id': database['id']})
        assigned = await db.bonanza_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        archived = await db.bonanza_records.count_documents({'database_id': database['id'], 'status': 'invalid_archived'})
        
        # Count excluded (reserved members in available records)
        available_records = await db.bonanza_records.find(
            {'database_id': database['id'], 'status': 'available'},
            {'_id': 0, 'row_data': 1}
        ).to_list(100000)
        
        excluded_count = 0
        for record in available_records:
            row_data = record.get('row_data', {})
            for key in ['Username', 'username', 'USER', 'user', 'ID', 'id', 'Nama Lengkap', 'nama_lengkap', 'Name', 'name']:
                if key in row_data and row_data[key]:
                    if str(row_data[key]).strip().upper() in reserved_ids:
                        excluded_count += 1
                        break
        
        database['total_records'] = total
        database['assigned_count'] = assigned
        database['archived_count'] = archived
        database['excluded_count'] = excluded_count
        database['available_count'] = total - assigned - archived - excluded_count
        if 'product_id' not in database:
            database['product_id'] = ''
            database['product_name'] = 'Unknown'
    
    return databases

@router.get("/bonanza/databases/{database_id}/records")
async def get_bonanza_records(database_id: str, status: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get all records from a Bonanza database (Admin only)"""
    db = get_db()
    query = {'database_id': database_id}
    if status:
        query['status'] = status
    
    records = await db.bonanza_records.find(query, {'_id': 0}).sort('row_number', 1).to_list(100000)
    return records

@router.post("/bonanza/assign")
async def assign_bonanza_records(assignment: BonanzaAssignment, user: User = Depends(get_admin_user)):
    """Assign Bonanza records to a staff member (Admin only)"""
    db = get_db()
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
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

@router.post("/bonanza/assign-random")
async def assign_random_bonanza_records(assignment: RandomBonanzaAssignment, user: User = Depends(get_admin_user)):
    """Randomly assign Bonanza records to a staff member, skipping reserved members (Admin only)"""
    db = get_db()
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get reserved members and normalize to UPPERCASE for case-insensitive comparison
    reserved_members = await db.reserved_members.find({}, {'_id': 0, 'customer_id': 1}).to_list(100000)
    reserved_ids = set(str(m['customer_id']).strip().upper() for m in reserved_members if m.get('customer_id'))
    
    available_records = await db.bonanza_records.find(
        {'database_id': assignment.database_id, 'status': 'available'},
        {'_id': 0}
    ).to_list(100000)
    
    eligible_records = []
    skipped_count = 0
    for record in available_records:
        username = record.get('row_data', {}).get(assignment.username_field, '')
        # Normalize to UPPERCASE for case-insensitive comparison
        username_str = str(username).strip().upper() if username else ''
        if username_str and username_str in reserved_ids:
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
        'remaining_eligible': len(eligible_records) - assignment.quantity
    }

@router.delete("/bonanza/databases/{database_id}")
async def delete_bonanza_database(database_id: str, user: User = Depends(get_admin_user)):
    """Delete a Bonanza database and all its records (Admin only)"""
    db = get_db()
    await db.bonanza_records.delete_many({'database_id': database_id})
    await db.bonanza_databases.delete_one({'id': database_id})
    return {'message': 'Database deleted successfully'}

@router.get("/bonanza/staff/records")
async def get_staff_bonanza_records(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get Bonanza records assigned to the current staff"""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    query = {'assigned_to': user.id, 'status': 'assigned'}
    if product_id:
        query['product_id'] = product_id
    
    records = await db.bonanza_records.find(query, {'_id': 0}).sort('assigned_at', -1).to_list(10000)
    
    for record in records:
        if 'product_id' not in record:
            record['product_id'] = ''
            record['product_name'] = 'Unknown'
    
    return records


@router.post("/bonanza/staff/validate")
async def validate_bonanza_records(data: RecordValidation, user: User = Depends(get_current_user)):
    """Staff marks records as valid or invalid. Auto-replaces if enabled in settings."""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    now = get_jakarta_now()
    
    # Only allow validating records assigned to this staff
    records = await db.bonanza_records.find({
        'id': {'$in': data.record_ids},
        'assigned_to': user.id
    }, {'_id': 0}).to_list(1000)
    
    if len(records) == 0:
        raise HTTPException(status_code=404, detail="No records found or not assigned to you")
    
    validation_status = 'validated' if data.is_valid else 'invalid'
    
    # Update records
    await db.bonanza_records.update_many(
        {'id': {'$in': data.record_ids}, 'assigned_to': user.id},
        {'$set': {
            'validation_status': validation_status,
            'validated_at': now.isoformat(),
            'validation_reason': data.reason if not data.is_valid else None
        }}
    )
    
    # Response data
    response = {
        'success': True,
        'message': f'{len(records)} records marked as {"valid" if data.is_valid else "invalid"}',
        'validation_status': validation_status,
        'auto_replaced': 0,
        'replacement_failed': 0,
        'replacement_message': None
    }
    
    # If marked as invalid, check for auto-replace setting
    if not data.is_valid:
        # Get settings
        settings = await db.app_settings.find_one({'id': 'bonanza_settings'}, {'_id': 0})
        if not settings:
            settings = DEFAULT_BONANZA_SETTINGS.copy()
        
        auto_replace = settings.get('auto_replace_invalid', False)
        max_per_batch = settings.get('max_replacements_per_batch', 10)
        
        if auto_replace:
            # Group invalid records by database_id
            invalid_by_db = {}
            for record in records:
                database_id = record.get('database_id')
                if database_id:
                    if database_id not in invalid_by_db:
                        invalid_by_db[database_id] = {
                            'database_id': database_id,
                            'database_name': record.get('database_name', 'Unknown'),
                            'product_id': record.get('product_id', ''),
                            'records': []
                        }
                    invalid_by_db[database_id]['records'].append(record)
            
            total_replaced = 0
            total_failed = 0
            replacement_details = []
            
            # Get reserved members
            reserved_members = await db.reserved_members.find({'status': 'approved'}, {'_id': 0, 'customer_id': 1, 'customer_name': 1}).to_list(100000)
            reserved_ids = set()
            for m in reserved_members:
                if m.get('customer_id'):
                    reserved_ids.add(str(m['customer_id']).strip().upper())
                if m.get('customer_name'):
                    reserved_ids.add(str(m['customer_name']).strip().upper())
            
            for database_id, group in invalid_by_db.items():
                invalid_records = group['records']
                invalid_ids = [r['id'] for r in invalid_records]
                
                # Check how many replacements already done for this staff from this database
                existing_replacements = await db.bonanza_records.count_documents({
                    'database_id': database_id,
                    'assigned_to': user.id,
                    'auto_replaced': True,
                    'status': 'assigned'
                })
                
                # Calculate how many more replacements allowed
                remaining_quota = max(0, max_per_batch - existing_replacements)
                needed = len(invalid_records)
                can_replace = min(needed, remaining_quota)
                
                if can_replace == 0:
                    total_failed += needed
                    replacement_details.append({
                        'database': group['database_name'],
                        'needed': needed,
                        'replaced': 0,
                        'reason': f'Replacement limit reached ({max_per_batch} per database)'
                    })
                    continue
                
                # Get available records from SAME database
                available = await db.bonanza_records.find({
                    'database_id': database_id,
                    'status': 'available'
                }, {'_id': 0}).to_list(can_replace * 3)
                
                # Filter out reserved
                eligible = []
                for rec in available:
                    row_data = rec.get('row_data', {})
                    is_reserved = False
                    for key in ['Username', 'username', 'USER', 'user', 'ID', 'id', 'Nama Lengkap', 'nama_lengkap', 'Name', 'name']:
                        if key in row_data and row_data[key]:
                            if str(row_data[key]).strip().upper() in reserved_ids:
                                is_reserved = True
                                break
                    if not is_reserved:
                        eligible.append(rec)
                        if len(eligible) >= can_replace:
                            break
                
                if len(eligible) == 0:
                    total_failed += can_replace
                    replacement_details.append({
                        'database': group['database_name'],
                        'needed': needed,
                        'replaced': 0,
                        'reason': 'No available records in database'
                    })
                    continue
                
                # Assign eligible records as replacements
                to_assign = eligible[:can_replace]
                assigned_ids = [r['id'] for r in to_assign]
                
                await db.bonanza_records.update_many(
                    {'id': {'$in': assigned_ids}},
                    {'$set': {
                        'status': 'assigned',
                        'assigned_to': user.id,
                        'assigned_to_name': user.name,
                        'assigned_at': now.isoformat(),
                        'auto_replaced': True,
                        'replaced_invalid_ids': invalid_ids[:len(assigned_ids)]
                    }}
                )
                
                # Archive the invalid records
                await db.bonanza_records.update_many(
                    {'id': {'$in': invalid_ids[:len(assigned_ids)]}},
                    {'$set': {
                        'status': 'invalid_archived',
                        'archived_at': now.isoformat(),
                        'auto_archived': True
                    }}
                )
                
                total_replaced += len(assigned_ids)
                
                if len(assigned_ids) < can_replace:
                    total_failed += (can_replace - len(assigned_ids))
                if needed > can_replace:
                    total_failed += (needed - can_replace)
                
                replacement_details.append({
                    'database': group['database_name'],
                    'needed': needed,
                    'replaced': len(assigned_ids),
                    'reason': None if len(assigned_ids) >= needed else 'Limit or availability'
                })
            
            response['auto_replaced'] = total_replaced
            response['replacement_failed'] = total_failed
            
            if total_replaced > 0:
                response['replacement_message'] = f'{total_replaced} record(s) auto-replaced'
            if total_failed > 0:
                if response['replacement_message']:
                    response['replacement_message'] += f', {total_failed} could not be replaced'
                else:
                    response['replacement_message'] = f'{total_failed} record(s) could not be replaced'
            
            response['replacement_details'] = replacement_details
        
        # Create admin notification for invalid records
        total_invalid = await db.bonanza_records.count_documents({
            'assigned_to': user.id,
            'validation_status': 'invalid',
            'status': 'assigned'
        })
        
        if total_invalid > 0:
            notification = {
                'id': str(uuid.uuid4()),
                'type': 'bonanza_invalid',
                'staff_id': user.id,
                'staff_name': user.name,
                'record_count': len(data.record_ids),
                'total_invalid': total_invalid,
                'reason': data.reason,
                'record_ids': data.record_ids,
                'created_at': now.isoformat(),
                'is_read': False,
                'is_resolved': False,
                'auto_replaced': response.get('auto_replaced', 0)
            }
            await db.admin_notifications.insert_one(notification)
    
    return response


@router.get("/bonanza/admin/invalid-records")
async def get_invalid_bonanza_records(user: User = Depends(get_admin_user)):
    """Get all invalid bonanza records with staff info (Admin only)"""
    db = get_db()
    
    # Group invalid records by staff (only show records still ASSIGNED)
    pipeline = [
        {'$match': {'validation_status': 'invalid', 'status': 'assigned'}},
        {'$group': {
            '_id': '$assigned_to',
            'staff_name': {'$first': '$assigned_to_name'},
            'count': {'$sum': 1},
            'records': {'$push': {
                'id': '$id',
                'row_data': '$row_data',
                'database_name': '$database_name',
                'validation_reason': '$validation_reason',
                'validated_at': '$validated_at'
            }}
        }},
        {'$sort': {'count': -1}}
    ]
    
    results = await db.bonanza_records.aggregate(pipeline).to_list(100)
    
    return {
        'total_invalid': sum(r['count'] for r in results),
        'by_staff': results
    }


@router.post("/bonanza/admin/dismiss-invalid-alerts")
async def dismiss_invalid_alerts(user: User = Depends(get_admin_user)):
    """
    Clear invalid status from records that are no longer assigned.
    For cleanup when records were recalled but still show as invalid.
    """
    db = get_db()
    now = get_jakarta_now()
    
    result = await db.bonanza_records.update_many(
        {
            'validation_status': 'invalid',
            'status': {'$ne': 'assigned'}
        },
        {
            '$unset': {
                'validation_status': '',
                'validated_at': '',
                'validation_reason': ''
            },
            '$set': {
                'invalid_dismissed_at': now.isoformat(),
                'invalid_dismissed_by': user.name
            }
        }
    )
    
    await db.admin_notifications.update_many(
        {'type': 'bonanza_invalid', 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    return {
        'success': True,
        'cleared_count': result.modified_count,
        'message': f'{result.modified_count} orphaned invalid alerts cleared'
    }


@router.post("/bonanza/admin/recall-records")
async def recall_assigned_records(data: RecallRecordsRequest, user: User = Depends(get_admin_user)):
    """
    Recall assigned records from staff - return them to available pool.
    """
    db = get_db()
    now = get_jakarta_now()
    
    if not data.record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")
    
    records_to_recall = await db.bonanza_records.find({
        'id': {'$in': data.record_ids},
        'status': 'assigned'
    }, {'_id': 0}).to_list(10000)
    
    if not records_to_recall:
        raise HTTPException(status_code=404, detail="No assigned records found with the provided IDs")
    
    result = await db.bonanza_records.update_many(
        {'id': {'$in': data.record_ids}, 'status': 'assigned'},
        {
            '$set': {
                'status': 'available',
                'recalled_at': now.isoformat(),
                'recalled_by': user.id,
                'recalled_by_name': user.name
            },
            '$unset': {
                'assigned_to': '',
                'assigned_to_name': '',
                'assigned_at': '',
                'assigned_by': '',
                'assigned_by_name': '',
                'validation_status': '',
                'validated_at': '',
                'validation_reason': '',
                'auto_replaced': '',
                'replaced_invalid_ids': ''
            }
        }
    )
    
    return {
        'success': True,
        'recalled_count': result.modified_count,
        'message': f'{result.modified_count} records recalled and returned to available pool'
    }


class ProcessInvalidRequest(BaseModel):
    auto_assign_quantity: int = 0  # How many new records to assign (0 = no auto-assign)


@router.post("/bonanza/admin/process-invalid/{staff_id}")
async def process_invalid_and_replace(staff_id: str, data: ProcessInvalidRequest, user: User = Depends(get_admin_user)):
    """
    Archive invalid records and assign replacement records to staff.
    
    KEY LOGIC:
    - For each database with invalid records, archive those invalid records
    - Then assign the SAME number of new records from the SAME database
    - This ensures assigned count stays the same (e.g., 50 assigned -> 50 assigned)
    - Available count decreases by the number of new records assigned
    """
    db = get_db()
    
    now = get_jakarta_now()
    
    # Find invalid records for this staff
    invalid_records = await db.bonanza_records.find({
        'assigned_to': staff_id,
        'validation_status': 'invalid',
        'status': 'assigned'  # Only get records that are still assigned (not already archived)
    }, {'_id': 0}).to_list(10000)
    
    if len(invalid_records) == 0:
        raise HTTPException(status_code=404, detail="No invalid records found for this staff")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get reserved members for filtering
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1}
    ).to_list(100000)
    
    reserved_ids = set()
    for m in reserved_members:
        if m.get('customer_id'):
            reserved_ids.add(str(m['customer_id']).strip().upper())
        if m.get('customer_name'):
            reserved_ids.add(str(m['customer_name']).strip().upper())
    
    def is_reserved(record):
        """Check if a record matches a reserved member"""
        row_data = record.get('row_data', {})
        for key in ['Username', 'username', 'USER', 'user', 'ID', 'id', 'Nama Lengkap', 'nama_lengkap', 'Name', 'name', 'NAMA']:
            if key in row_data and row_data[key]:
                if str(row_data[key]).strip().upper() in reserved_ids:
                    return True
        return False
    
    # Group invalid records by database_id
    invalid_by_database = {}
    for record in invalid_records:
        db_id = record.get('database_id')
        if db_id:
            if db_id not in invalid_by_database:
                invalid_by_database[db_id] = {
                    'database_id': db_id,
                    'database_name': record.get('database_name', 'Unknown'),
                    'records': []
                }
            invalid_by_database[db_id]['records'].append(record)
    
    total_archived = 0
    total_assigned = 0
    total_skipped_reserved = 0
    assignment_details = []
    
    # Process each database separately
    for db_id, group in invalid_by_database.items():
        invalid_in_db = group['records']
        invalid_ids = [r['id'] for r in invalid_in_db]
        needed_replacements = len(invalid_in_db)  # Need same number as invalid
        
        # Step 1: Archive the invalid records
        await db.bonanza_records.update_many(
            {'id': {'$in': invalid_ids}},
            {'$set': {
                'status': 'invalid_archived',
                'archived_at': now.isoformat(),
                'archived_by': user.id,
                'archived_by_name': user.name
            }}
        )
        total_archived += len(invalid_ids)
        
        # Step 2: Find and assign replacement records from the SAME database
        if data.auto_assign_quantity > 0:
            # Get available records from this specific database
            available_records = await db.bonanza_records.find({
                'database_id': db_id,
                'status': 'available'
            }, {'_id': 0}).to_list(needed_replacements * 3)
            
            # Filter out reserved members
            eligible_records = []
            skipped = 0
            for record in available_records:
                if is_reserved(record):
                    skipped += 1
                else:
                    eligible_records.append(record)
                    if len(eligible_records) >= needed_replacements:
                        break
            
            total_skipped_reserved += skipped
            
            # Assign eligible records (up to the number of invalid records)
            to_assign = eligible_records[:needed_replacements]
            if to_assign:
                assigned_ids = [r['id'] for r in to_assign]
                await db.bonanza_records.update_many(
                    {'id': {'$in': assigned_ids}},
                    {'$set': {
                        'status': 'assigned',
                        'assigned_to': staff['id'],
                        'assigned_to_name': staff['name'],
                        'assigned_at': now.isoformat(),
                        'assigned_by': user.id,
                        'assigned_by_name': user.name,
                        'auto_replaced': True,
                        'replaced_invalid_ids': invalid_ids
                    }}
                )
                total_assigned += len(assigned_ids)
            
            assignment_details.append({
                'database': group['database_name'],
                'invalid_archived': len(invalid_ids),
                'replacements_assigned': len(to_assign),
                'shortage': needed_replacements - len(to_assign) if len(to_assign) < needed_replacements else 0
            })
    
    # Mark related notifications as resolved
    await db.admin_notifications.update_many(
        {'type': 'bonanza_invalid', 'staff_id': staff_id, 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    # Build message
    message = f'{total_archived} record tidak valid diarsipkan.'
    if data.auto_assign_quantity > 0:
        message += f' {total_assigned} record baru ditugaskan ke {staff["name"]}.'
        if total_skipped_reserved > 0:
            message += f' ({total_skipped_reserved} reserved member dilewati)'
        if total_assigned < total_archived:
            shortage = total_archived - total_assigned
            message += f' Kekurangan {shortage} record karena tidak tersedia.'
    
    return {
        'success': True,
        'archived_count': total_archived,
        'new_assigned_count': total_assigned,
        'skipped_reserved': total_skipped_reserved,
        'message': message,
        'details': assignment_details
    }


# Legacy endpoint - redirect to new one
@router.post("/bonanza/admin/reassign-invalid/{staff_id}")
async def reassign_invalid_to_available(staff_id: str, user: User = Depends(get_admin_user)):
    """Legacy endpoint - now archives instead of returning to pool"""
    return await process_invalid_and_replace(staff_id, ProcessInvalidRequest(auto_assign_quantity=0), user)


@router.get("/bonanza/admin/archived-invalid")
async def get_archived_invalid_records(user: User = Depends(get_admin_user)):
    """Get all archived invalid records (Invalid Database section)"""
    db = get_db()
    
    records = await db.bonanza_records.find(
        {'status': 'invalid_archived'},
        {'_id': 0}
    ).sort('archived_at', -1).to_list(1000)
    
    # Group by database
    by_database = {}
    for record in records:
        db_name = record.get('database_name', 'Unknown')
        if db_name not in by_database:
            by_database[db_name] = {
                'database_name': db_name,
                'database_id': record.get('database_id'),
                'product_name': record.get('product_name', 'Unknown'),
                'count': 0,
                'records': []
            }
        by_database[db_name]['count'] += 1
        by_database[db_name]['records'].append(record)
    
    return {
        'total': len(records),
        'by_database': list(by_database.values())
    }


@router.post("/bonanza/admin/archived-invalid/{record_id}/restore")
async def restore_archived_record(record_id: str, user: User = Depends(get_admin_user)):
    """Restore an archived invalid record back to available pool"""
    db = get_db()
    
    now = get_jakarta_now()
    
    result = await db.bonanza_records.update_one(
        {'id': record_id, 'status': 'invalid_archived'},
        {'$set': {
            'status': 'available',
            'assigned_to': None,
            'assigned_to_name': None,
            'assigned_at': None,
            'validation_status': None,
            'validated_at': None,
            'validation_reason': None,
            'archived_at': None,
            'archived_by': None,
            'archived_by_name': None,
            'restored_at': now.isoformat(),
            'restored_by': user.name
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Record not found or not archived")
    
    return {'success': True, 'message': 'Record restored to available pool'}


@router.delete("/bonanza/admin/archived-invalid/{record_id}")
async def delete_archived_record(record_id: str, user: User = Depends(get_admin_user)):
    """Permanently delete an archived invalid record"""
    db = get_db()
    
    result = await db.bonanza_records.delete_one({'id': record_id, 'status': 'invalid_archived'})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found or not archived")
    
    return {'success': True, 'message': 'Record permanently deleted'}

@router.get("/bonanza/staff")
async def get_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff


@router.post("/bonanza/admin/repair-data")
async def repair_bonanza_data(user: User = Depends(get_admin_user)):
    """
    Repair and synchronize bonanza record data.
    This fixes inconsistencies caused by pre-update code:
    1. Fixes records with missing database_id or database_name
    2. Resets corrupted status values
    3. Clears orphaned assignments
    4. Reports detailed statistics
    """
    db = get_db()
    now = get_jakarta_now()
    
    repair_log = {
        'timestamp': now.isoformat(),
        'fixed_missing_db_info': 0,
        'fixed_invalid_status': 0,
        'fixed_orphaned_assignments': 0,
        'databases_checked': [],
        'errors': []
    }
    
    # Get all databases
    databases = await db.bonanza_databases.find({}, {'_id': 0}).to_list(1000)
    db_map = {d['id']: d for d in databases}
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        product_name = database.get('product_name', 'Unknown')
        
        # Get all records for this database
        records = await db.bonanza_records.find({'database_id': db_id}, {'_id': 0}).to_list(100000)
        
        # Count actual statuses
        status_counts = {
            'available': 0,
            'assigned': 0,
            'invalid_archived': 0,
            'unknown': 0
        }
        
        for record in records:
            status = record.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts['unknown'] += 1
        
        # Fix records with missing database_name
        result = await db.bonanza_records.update_many(
            {'database_id': db_id, 'database_name': {'$exists': False}},
            {'$set': {'database_name': db_name, 'product_name': product_name}}
        )
        if result.modified_count > 0:
            repair_log['fixed_missing_db_info'] += result.modified_count
        
        # Fix records with None database_name
        result = await db.bonanza_records.update_many(
            {'database_id': db_id, 'database_name': None},
            {'$set': {'database_name': db_name, 'product_name': product_name}}
        )
        if result.modified_count > 0:
            repair_log['fixed_missing_db_info'] += result.modified_count
        
        # Fix invalid status values (not one of the valid statuses)
        valid_statuses = ['available', 'assigned', 'invalid_archived']
        result = await db.bonanza_records.update_many(
            {'database_id': db_id, 'status': {'$nin': valid_statuses}},
            {'$set': {'status': 'available'}}
        )
        if result.modified_count > 0:
            repair_log['fixed_invalid_status'] += result.modified_count
        
        # Fix orphaned assignments (assigned but no assigned_to)
        result = await db.bonanza_records.update_many(
            {'database_id': db_id, 'status': 'assigned', 'assigned_to': None},
            {'$set': {
                'status': 'available',
                'assigned_to': None,
                'assigned_to_name': None,
                'assigned_at': None
            }}
        )
        if result.modified_count > 0:
            repair_log['fixed_orphaned_assignments'] += result.modified_count
        
        # Recalculate counts after fixes
        available = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db.bonanza_records.count_documents({'database_id': db_id})
        
        repair_log['databases_checked'].append({
            'database_id': db_id,
            'database_name': db_name,
            'total_records': total,
            'available': available,
            'assigned': assigned,
            'archived': archived,
            'sum_check': available + assigned + archived,
            'is_consistent': total == (available + assigned + archived)
        })
    
    # Check for records with no database_id at all
    orphan_records = await db.bonanza_records.count_documents({'database_id': {'$exists': False}})
    if orphan_records > 0:
        repair_log['errors'].append(f'{orphan_records} records have no database_id - manual intervention needed')
    
    orphan_records_null = await db.bonanza_records.count_documents({'database_id': None})
    if orphan_records_null > 0:
        repair_log['errors'].append(f'{orphan_records_null} records have null database_id - manual intervention needed')
    
    total_fixed = (
        repair_log['fixed_missing_db_info'] + 
        repair_log['fixed_invalid_status'] + 
        repair_log['fixed_orphaned_assignments']
    )
    
    return {
        'success': True,
        'message': f'Data repair completed. Fixed {total_fixed} issues.',
        'repair_log': repair_log
    }


@router.post("/bonanza/admin/repair-product-mismatch")
async def repair_product_mismatch(user: User = Depends(get_admin_user)):
    """
    Find and fix records where product_id doesn't match the database's product_id.
    This fixes issues caused when re-assigning invalid records to the wrong database.
    
    For example: A record with product_id='PUCUK33' in database 'Bonanza Liga Jan' (which has product_id='LIGA2000')
    will be moved to the correct 'Bonanza Pucuk Jan' database.
    """
    db = get_db()
    now = get_jakarta_now()
    
    repair_log = {
        'timestamp': now.isoformat(),
        'total_mismatched': 0,
        'total_fixed': 0,
        'total_no_target_db': 0,
        'by_database': [],
        'moves': [],
        'errors': []
    }
    
    # Get all databases and create maps
    databases = await db.bonanza_databases.find({}, {'_id': 0}).to_list(1000)
    db_by_id = {d['id']: d for d in databases}
    db_by_product = {}
    
    for database in databases:
        product_id = database.get('product_id')
        if product_id:
            if product_id not in db_by_product:
                db_by_product[product_id] = []
            db_by_product[product_id].append(database)
    
    # For each database, find records with wrong product_id
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        db_product_id = database.get('product_id')
        
        if not db_product_id:
            repair_log['errors'].append(f"Database '{db_name}' has no product_id set")
            continue
        
        # Find records in this database with DIFFERENT product_id
        mismatched_records = await db.bonanza_records.find({
            'database_id': db_id,
            'product_id': {'$exists': True, '$ne': db_product_id}
        }, {'_id': 0}).to_list(100000)
        
        db_stats = {
            'database_id': db_id,
            'database_name': db_name,
            'expected_product': db_product_id,
            'mismatched_count': len(mismatched_records),
            'fixed_count': 0,
            'no_target_count': 0
        }
        
        if mismatched_records:
            # Group by their actual product_id
            by_product = {}
            for record in mismatched_records:
                rec_product = record.get('product_id', 'UNKNOWN')
                if rec_product not in by_product:
                    by_product[rec_product] = []
                by_product[rec_product].append(record)
            
            for rec_product, records in by_product.items():
                # Find the correct database for this product
                target_databases = db_by_product.get(rec_product, [])
                
                if not target_databases:
                    repair_log['errors'].append(
                        f"No database found for product '{rec_product}' - {len(records)} records cannot be moved"
                    )
                    db_stats['no_target_count'] += len(records)
                    repair_log['total_no_target_db'] += len(records)
                    continue
                
                # Use the first database with this product
                target_db = target_databases[0]
                target_db_id = target_db['id']
                target_db_name = target_db['name']
                
                # Move records to the correct database
                record_ids = [r['id'] for r in records]
                
                result = await db.bonanza_records.update_many(
                    {'id': {'$in': record_ids}},
                    {'$set': {
                        'database_id': target_db_id,
                        'database_name': target_db_name,
                        'product_name': target_db.get('product_name', rec_product),
                        'moved_at': now.isoformat(),
                        'moved_from': db_id,
                        'moved_reason': 'product_mismatch_repair'
                    }}
                )
                
                db_stats['fixed_count'] += result.modified_count
                repair_log['total_fixed'] += result.modified_count
                
                repair_log['moves'].append({
                    'from_database': db_name,
                    'to_database': target_db_name,
                    'product_id': rec_product,
                    'count': result.modified_count
                })
        
        repair_log['by_database'].append(db_stats)
        repair_log['total_mismatched'] += db_stats['mismatched_count']
    
    # Now recount all databases to show updated stats
    updated_stats = []
    for database in databases:
        db_id = database['id']
        available = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db.bonanza_records.count_documents({'database_id': db_id})
        
        updated_stats.append({
            'database_name': database['name'],
            'product_id': database.get('product_id'),
            'total': total,
            'available': available,
            'assigned': assigned,
            'archived': archived
        })
    
    repair_log['updated_database_stats'] = updated_stats
    
    return {
        'success': True,
        'message': f'Product mismatch repair completed. Fixed {repair_log["total_fixed"]} records.',
        'repair_log': repair_log
    }


@router.get("/bonanza/admin/data-health")
async def get_bonanza_data_health(user: User = Depends(get_admin_user)):
    """
    Check the health of bonanza data without making changes.
    Returns detailed statistics about data consistency.
    """
    db = get_db()
    
    health_report = {
        'databases': [],
        'total_issues': 0,
        'issues': []
    }
    
    # Get all databases
    databases = await db.bonanza_databases.find({}, {'_id': 0}).to_list(1000)
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        
        # Count records by status
        available = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db.bonanza_records.count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db.bonanza_records.count_documents({'database_id': db_id})
        
        # Check for issues
        missing_db_name = await db.bonanza_records.count_documents({
            'database_id': db_id, 
            '$or': [{'database_name': {'$exists': False}}, {'database_name': None}]
        })
        
        orphaned_assignments = await db.bonanza_records.count_documents({
            'database_id': db_id, 
            'status': 'assigned', 
            'assigned_to': None
        })
        
        invalid_status = await db.bonanza_records.count_documents({
            'database_id': db_id, 
            'status': {'$nin': ['available', 'assigned', 'invalid_archived']}
        })
        
        db_issues = missing_db_name + orphaned_assignments + invalid_status
        
        health_report['databases'].append({
            'database_id': db_id,
            'database_name': db_name,
            'total_records': total,
            'available': available,
            'assigned': assigned,
            'archived': archived,
            'sum_matches': total == (available + assigned + archived),
            'issues': {
                'missing_db_name': missing_db_name,
                'orphaned_assignments': orphaned_assignments,
                'invalid_status': invalid_status
            },
            'has_issues': db_issues > 0
        })
        
        health_report['total_issues'] += db_issues
        
        if db_issues > 0:
            if missing_db_name > 0:
                health_report['issues'].append(f'{db_name}: {missing_db_name} records missing database_name')
            if orphaned_assignments > 0:
                health_report['issues'].append(f'{db_name}: {orphaned_assignments} orphaned assignments')
            if invalid_status > 0:
                health_report['issues'].append(f'{db_name}: {invalid_status} invalid status values')
    
    # Check for completely orphaned records
    orphan_no_db = await db.bonanza_records.count_documents({'database_id': {'$exists': False}})
    orphan_null_db = await db.bonanza_records.count_documents({'database_id': None})
    
    if orphan_no_db > 0:
        health_report['issues'].append(f'{orphan_no_db} records have no database_id field')
        health_report['total_issues'] += orphan_no_db
    if orphan_null_db > 0:
        health_report['issues'].append(f'{orphan_null_db} records have null database_id')
        health_report['total_issues'] += orphan_null_db
    
    health_report['is_healthy'] = health_report['total_issues'] == 0
    
    return health_report


@router.get("/bonanza/admin/diagnose-invalid/{staff_id}")
async def diagnose_invalid_records(staff_id: str, user: User = Depends(get_admin_user)):
    """
    Diagnose why invalid record replacement might be failing.
    Returns detailed information about the invalid records and available records.
    """
    db = get_db()
    
    # Get invalid records for this staff
    invalid_records = await db.bonanza_records.find({
        'assigned_to': staff_id,
        'validation_status': 'invalid',
        'status': 'assigned'
    }, {'_id': 0}).to_list(10000)
    
    # Get reserved members
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1}
    ).to_list(100000)
    
    reserved_ids = set()
    for m in reserved_members:
        if m.get('customer_id'):
            reserved_ids.add(str(m['customer_id']).strip().upper())
        if m.get('customer_name'):
            reserved_ids.add(str(m['customer_name']).strip().upper())
    
    diagnosis = {
        'total_invalid_records': len(invalid_records),
        'reserved_members_count': len(reserved_members),
        'invalid_records_by_database': {},
        'issues': []
    }
    
    # Group invalid records by database
    for record in invalid_records:
        db_id = record.get('database_id')
        db_name = record.get('database_name', 'Unknown')
        
        if not db_id:
            diagnosis['issues'].append(f"Invalid record {record.get('id', 'unknown')[:8]} has no database_id")
            continue
        
        if db_id not in diagnosis['invalid_records_by_database']:
            # Get database info
            database = await db.bonanza_databases.find_one({'id': db_id}, {'_id': 0})
            
            # Count available records in this database
            available_count = await db.bonanza_records.count_documents({
                'database_id': db_id,
                'status': 'available'
            })
            
            # Get sample available records
            available_sample = await db.bonanza_records.find({
                'database_id': db_id,
                'status': 'available'
            }, {'_id': 0, 'id': 1, 'row_data': 1}).to_list(10)
            
            # Check how many are reserved
            reserved_count = 0
            for rec in available_sample:
                row_data = rec.get('row_data', {})
                for key in ['Username', 'username', 'USER', 'user', 'ID', 'id', 'Nama Lengkap', 'nama_lengkap', 'Name', 'name', 'NAMA']:
                    if key in row_data and row_data[key]:
                        if str(row_data[key]).strip().upper() in reserved_ids:
                            reserved_count += 1
                            break
            
            diagnosis['invalid_records_by_database'][db_id] = {
                'database_name': database.get('name') if database else db_name,
                'database_exists': database is not None,
                'invalid_count': 0,
                'available_in_database': available_count,
                'sample_reserved_ratio': f'{reserved_count}/{len(available_sample)}',
                'sample_records': [
                    {
                        'id': r.get('id', '')[:8],
                        'username': r.get('row_data', {}).get('Username') or r.get('row_data', {}).get('username', 'N/A')
                    }
                    for r in available_sample[:5]
                ]
            }
        
        diagnosis['invalid_records_by_database'][db_id]['invalid_count'] += 1
    
    # Check if database_id in invalid records matches any existing database
    for db_id, info in diagnosis['invalid_records_by_database'].items():
        if not info['database_exists']:
            diagnosis['issues'].append(f"Database {db_id} does not exist - invalid records are orphaned")
        elif info['available_in_database'] == 0:
            diagnosis['issues'].append(f"Database {info['database_name']} has 0 available records")
    
    return diagnosis
