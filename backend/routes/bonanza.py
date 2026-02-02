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
    """Archive invalid records and optionally assign new records to staff"""
    db = get_db()
    
    now = get_jakarta_now()
    
    # Find invalid records
    invalid_records = await db.bonanza_records.find({
        'assigned_to': staff_id,
        'validation_status': 'invalid'
    }).to_list(10000)
    
    if len(invalid_records) == 0:
        raise HTTPException(status_code=404, detail="No invalid records found for this staff")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    record_ids = [r['id'] for r in invalid_records]
    
    # Get unique database IDs from invalid records for auto-assignment
    database_ids = list(set(r.get('database_id') for r in invalid_records if r.get('database_id')))
    
    # Archive invalid records (move to 'invalid_archived' status)
    await db.bonanza_records.update_many(
        {'id': {'$in': record_ids}},
        {'$set': {
            'status': 'invalid_archived',
            'archived_at': now.isoformat(),
            'archived_by': user.id,
            'archived_by_name': user.name
        }}
    )
    
    # Mark related notifications as resolved
    await db.admin_notifications.update_many(
        {'type': 'bonanza_invalid', 'staff_id': staff_id, 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    # Auto-assign new records if requested
    new_assigned_count = 0
    skipped_reserved = 0
    if data.auto_assign_quantity > 0 and database_ids:
        # Find available records from the same databases
        available_records = await db.bonanza_records.find({
            'database_id': {'$in': database_ids},
            'status': 'available'
        }, {'_id': 0}).to_list(data.auto_assign_quantity * 3)  # Get extra in case some are reserved
        
        # Get reserved members - check both customer_id and customer_name for comprehensive matching
        reserved_members = await db.reserved_members.find(
            {'status': 'approved'},  # Only approved reservations
            {'_id': 0, 'customer_id': 1, 'customer_name': 1}
        ).to_list(100000)
        
        # Build set of reserved identifiers (uppercase for case-insensitive matching)
        reserved_ids = set()
        for m in reserved_members:
            if m.get('customer_id'):
                reserved_ids.add(str(m['customer_id']).strip().upper())
            if m.get('customer_name'):
                reserved_ids.add(str(m['customer_name']).strip().upper())
        
        eligible_records = []
        for record in available_records:
            row_data = record.get('row_data', {})
            
            # Check Username field (case-insensitive)
            is_reserved = False
            for key in ['Username', 'username', 'USER', 'user', 'ID', 'id']:
                if key in row_data:
                    value = str(row_data[key]).strip().upper()
                    if value in reserved_ids:
                        is_reserved = True
                        skipped_reserved += 1
                        break
            
            # Also check Nama Lengkap / Name field
            if not is_reserved:
                for key in ['Nama Lengkap', 'nama_lengkap', 'Name', 'name', 'NAMA']:
                    if key in row_data:
                        value = str(row_data[key]).strip().upper()
                        if value in reserved_ids:
                            is_reserved = True
                            skipped_reserved += 1
                            break
            
            if not is_reserved:
                eligible_records.append(record)
                if len(eligible_records) >= data.auto_assign_quantity:
                    break
        
        if eligible_records:
            selected_ids = [r['id'] for r in eligible_records]
            await db.bonanza_records.update_many(
                {'id': {'$in': selected_ids}},
                {'$set': {
                    'status': 'assigned',
                    'assigned_to': staff['id'],
                    'assigned_to_name': staff['name'],
                    'assigned_at': now.isoformat(),
                    'assigned_by': user.id,
                    'assigned_by_name': user.name,
                    'auto_replaced': True,
                    'replaced_invalid_ids': record_ids
                }}
            )
            new_assigned_count = len(selected_ids)
    
    # Build message with reserved member info
    message = f'{len(record_ids)} record diarsipkan.'
    if data.auto_assign_quantity > 0:
        message += f' {new_assigned_count} record baru ditugaskan ke {staff["name"]}.'
        if skipped_reserved > 0:
            message += f' ({skipped_reserved} record reserved member dilewati)'
        if new_assigned_count < data.auto_assign_quantity:
            shortage = data.auto_assign_quantity - new_assigned_count
            message += f' Kekurangan {shortage} record karena tidak tersedia.'
    
    return {
        'success': True,
        'archived_count': len(record_ids),
        'new_assigned_count': new_assigned_count,
        'skipped_reserved': skipped_reserved,
        'message': message
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
