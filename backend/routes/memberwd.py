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
    batch_id: Optional[str] = None  # Optional: assign to existing batch

class RandomMemberWDAssignment(BaseModel):
    database_id: str
    staff_id: str
    quantity: int
    username_field: str = "Username"
    batch_id: Optional[str] = None  # Optional: assign to existing batch

class RecordValidation(BaseModel):
    record_ids: List[str]
    is_valid: bool
    reason: Optional[str] = None


@router.post("/memberwd/admin/migrate-batches")
async def migrate_existing_records_to_batches(user: User = Depends(get_admin_user)):
    """
    Migration endpoint: Auto-create batch cards for existing assigned records that don't have batch_id.
    
    Logic:
    1. For REPLACEMENT records (auto_replaced=True): Find the batch from their replaced invalid records
    2. For REGULAR records: Group by staff_id + database_id + EXACT assigned_at timestamp
    
    Records assigned in the same operation have the exact same timestamp.
    """
    db = get_db()
    now = get_jakarta_now()
    
    # Find all assigned records without batch_id
    records_without_batch = await db.memberwd_records.find({
        'status': 'assigned',
        '$or': [
            {'batch_id': {'$exists': False}},
            {'batch_id': None},
            {'batch_id': ''}
        ]
    }, {'_id': 0}).to_list(100000)
    
    if not records_without_batch:
        return {
            'success': True,
            'message': 'No records need migration - all assigned records already have batches',
            'batches_created': 0,
            'records_updated': 0
        }
    
    # Separate replacement records from regular records
    replacement_records = []
    regular_records = []
    
    for record in records_without_batch:
        if record.get('auto_replaced') and record.get('replaced_invalid_ids'):
            replacement_records.append(record)
        else:
            regular_records.append(record)
    
    # Handle replacement records: find their correct batch from archived invalid records
    replacement_updates = []
    for record in replacement_records:
        invalid_ids = record.get('replaced_invalid_ids', [])
        if invalid_ids:
            # Find the batch_id from one of the archived invalid records
            archived = await db.memberwd_records.find_one(
                {'id': {'$in': invalid_ids}, 'batch_id': {'$exists': True, '$nin': [None, '']}},
                {'_id': 0, 'batch_id': 1}
            )
            if archived and archived.get('batch_id'):
                replacement_updates.append({
                    'record_id': record['id'],
                    'batch_id': archived['batch_id']
                })
    
    # Apply batch_id updates for replacement records
    replacement_count = 0
    for update in replacement_updates:
        result = await db.memberwd_records.update_one(
            {'id': update['record_id']},
            {'$set': {'batch_id': update['batch_id']}}
        )
        if result.modified_count > 0:
            replacement_count += 1
    
    # Group REGULAR records by staff_id + database_id + EXACT assigned_at timestamp
    groups = {}
    for record in regular_records:
        staff_id = record.get('assigned_to')
        database_id = record.get('database_id')
        assigned_at = record.get('assigned_at', '')
        
        if not staff_id or not database_id:
            continue
        
        # Use the FULL assigned_at timestamp as the grouping key
        assignment_key = assigned_at if assigned_at else 'unknown'
        
        key = f"{staff_id}|{database_id}|{assignment_key}"
        if key not in groups:
            groups[key] = {
                'staff_id': staff_id,
                'staff_name': record.get('assigned_to_name', 'Unknown'),
                'database_id': database_id,
                'database_name': record.get('database_name', 'Unknown'),
                'product_id': record.get('product_id', ''),
                'product_name': record.get('product_name', 'Unknown'),
                'records': [],
                'earliest_assigned': assigned_at,
                'assigned_by': record.get('assigned_by_name', 'System Migration')
            }
        
        groups[key]['records'].append(record)
        
        # Track earliest assignment time for this group
        if assigned_at and (not groups[key]['earliest_assigned'] or assigned_at < groups[key]['earliest_assigned']):
            groups[key]['earliest_assigned'] = assigned_at
    
    # Create batches and update records
    batches_created = 0
    records_updated = 0
    
    for key, group in groups.items():
        batch_id = str(uuid.uuid4())
        
        # Create batch document
        await db.memberwd_batches.insert_one({
            'id': batch_id,
            'staff_id': group['staff_id'],
            'staff_name': group['staff_name'],
            'database_id': group['database_id'],
            'database_name': group['database_name'],
            'product_id': group['product_id'],
            'product_name': group['product_name'],
            'created_at': group['earliest_assigned'] or now.isoformat(),
            'created_by': group['assigned_by'],
            'initial_count': len(group['records']),
            'current_count': len(group['records']),
            'migrated': True,
            'migrated_at': now.isoformat(),
            'migrated_by': user.name
        })
        batches_created += 1
        
        # Update all records in this group with the batch_id
        record_ids = [r['id'] for r in group['records']]
        result = await db.memberwd_records.update_many(
            {'id': {'$in': record_ids}},
            {'$set': {'batch_id': batch_id}}
        )
        records_updated += result.modified_count
    
    return {
        'success': True,
        'message': f'Migration completed: {batches_created} batches created, {records_updated} regular records updated, {replacement_count} replacement records linked to existing batches',
        'batches_created': batches_created,
        'records_updated': records_updated,
        'replacement_records_linked': replacement_count,
        'groups': [
            {
                'staff_name': g['staff_name'],
                'database_name': g['database_name'],
                'assigned_at': g['earliest_assigned'],
                'record_count': len(g['records'])
            }
            for g in groups.values()
        ]
    }


@router.get("/memberwd/admin/check-migration-status")
async def check_migration_status(user: User = Depends(get_admin_user)):
    """Check how many records still need batch migration"""
    db = get_db()
    
    # Count records without batch_id
    records_without_batch = await db.memberwd_records.count_documents({
        'status': 'assigned',
        '$or': [
            {'batch_id': {'$exists': False}},
            {'batch_id': None},
            {'batch_id': ''}
        ]
    })
    
    # Count records with batch_id
    records_with_batch = await db.memberwd_records.count_documents({
        'status': 'assigned',
        'batch_id': {'$exists': True, '$nin': [None, '']}
    })
    
    # Count total batches
    total_batches = await db.memberwd_batches.count_documents({})
    
    # Count migrated batches (created by migration, may need re-migration)
    migrated_batches = await db.memberwd_batches.count_documents({'migrated': True})
    
    return {
        'records_needing_migration': records_without_batch,
        'records_with_batches': records_with_batch,
        'total_batches': total_batches,
        'migrated_batches': migrated_batches,
        'migration_needed': records_without_batch > 0
    }


@router.post("/memberwd/admin/reset-migrated-batches")
async def reset_migrated_batches(user: User = Depends(get_admin_user)):
    """
    Reset batches created by the migration (migrated=True).
    This will:
    1. Remove batch_id from ALL records that belong to migrated batches
    2. Delete all migrated batches
    3. After this, run /admin/migrate-batches again to create proper batches
    """
    db = get_db()
    
    # Find all migrated batches
    migrated_batches = await db.memberwd_batches.find(
        {'migrated': True},
        {'_id': 0, 'id': 1}
    ).to_list(10000)
    
    if not migrated_batches:
        return {
            'success': True,
            'message': 'No migrated batches found to reset',
            'batches_deleted': 0,
            'records_reset': 0
        }
    
    batch_ids = [b['id'] for b in migrated_batches]
    
    # Remove batch_id from ALL records belonging to these batches
    # (including replacement records - they'll be re-linked during migration)
    result = await db.memberwd_records.update_many(
        {'batch_id': {'$in': batch_ids}},
        {'$unset': {'batch_id': ''}}
    )
    records_reset = result.modified_count
    
    # Delete the migrated batches
    delete_result = await db.memberwd_batches.delete_many({'migrated': True})
    batches_deleted = delete_result.deleted_count
    
    return {
        'success': True,
        'message': f'Reset {batches_deleted} migrated batches, {records_reset} records now need re-migration',
        'batches_deleted': batches_deleted,
        'records_reset': records_reset
    }


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
    
    now = get_jakarta_now()
    
    # Create or use existing batch
    batch_id = assignment.batch_id
    if not batch_id:
        # Create new batch
        batch_id = str(uuid.uuid4())
        
        # Get database info from first record
        first_record = await db.memberwd_records.find_one({'id': assignment.record_ids[0]}, {'_id': 0})
        database_name = first_record.get('database_name', 'Unknown') if first_record else 'Unknown'
        product_name = first_record.get('product_name', 'Unknown') if first_record else 'Unknown'
        
        await db.memberwd_batches.insert_one({
            'id': batch_id,
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'database_name': database_name,
            'product_name': product_name,
            'created_at': now.isoformat(),
            'created_by': user.name,
            'initial_count': len(assignment.record_ids),
            'current_count': len(assignment.record_ids)
        })
    else:
        # Update existing batch count
        await db.memberwd_batches.update_one(
            {'id': batch_id},
            {'$inc': {'current_count': len(assignment.record_ids)}}
        )
    
    result = await db.memberwd_records.update_many(
        {'id': {'$in': assignment.record_ids}, 'status': 'available'},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': now.isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name,
            'batch_id': batch_id
        }}
    )
    
    return {
        'message': f'{result.modified_count} records assigned to {staff["name"]}',
        'batch_id': batch_id
    }

@router.post("/memberwd/assign-random")
async def assign_random_memberwd_records(assignment: RandomMemberWDAssignment, user: User = Depends(get_admin_user)):
    """Randomly assign Member WD records to a staff member, skipping reserved members (Admin only)"""
    db = get_db()
    staff = await db.users.find_one({'id': assignment.staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    now = get_jakarta_now()
    
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
    
    # Get database info
    db_info = await db.memberwd_databases.find_one({'id': assignment.database_id}, {'_id': 0})
    database_name = db_info.get('name', 'Unknown') if db_info else 'Unknown'
    product_name = db_info.get('product_name', 'Unknown') if db_info else 'Unknown'
    
    # Create or use existing batch
    batch_id = assignment.batch_id
    if not batch_id:
        # Create new batch
        batch_id = str(uuid.uuid4())
        await db.memberwd_batches.insert_one({
            'id': batch_id,
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'database_id': assignment.database_id,
            'database_name': database_name,
            'product_name': product_name,
            'created_at': now.isoformat(),
            'created_by': user.name,
            'initial_count': len(selected_ids),
            'current_count': len(selected_ids)
        })
    else:
        # Update existing batch count
        await db.memberwd_batches.update_one(
            {'id': batch_id},
            {'$inc': {'current_count': len(selected_ids)}}
        )
    
    result = await db.memberwd_records.update_many(
        {'id': {'$in': selected_ids}},
        {'$set': {
            'status': 'assigned',
            'assigned_to': staff['id'],
            'assigned_to_name': staff['name'],
            'assigned_at': now.isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name,
            'batch_id': batch_id
        }}
    )
    
    return {
        'message': f'{result.modified_count} records assigned to {staff["name"]}',
        'assigned_count': result.modified_count,
        'total_reserved_in_db': skipped_count,
        'remaining_eligible': len(eligible_records) - assignment.quantity,
        'batch_id': batch_id
    }

@router.delete("/memberwd/databases/{database_id}")
async def delete_memberwd_database(database_id: str, user: User = Depends(get_admin_user)):
    """Delete a Member WD database and all its records (Admin only)"""
    db = get_db()
    await db.memberwd_records.delete_many({'database_id': database_id})
    await db.memberwd_databases.delete_one({'id': database_id})
    return {'message': 'Database deleted successfully'}


@router.get("/memberwd/staff/batches")
async def get_staff_memberwd_batches(user: User = Depends(get_current_user)):
    """Get Member WD batches assigned to the current staff"""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    # Get batches for this staff
    batches = await db.memberwd_batches.find(
        {'staff_id': user.id},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    # Get records for each batch with counts
    for batch in batches:
        batch_records = await db.memberwd_records.find(
            {'batch_id': batch['id'], 'assigned_to': user.id, 'status': 'assigned'},
            {'_id': 0}
        ).to_list(10000)
        
        batch['records'] = batch_records
        batch['active_count'] = len(batch_records)
        
        # Count by validation status
        validated = sum(1 for r in batch_records if r.get('validation_status') == 'valid')
        invalid = sum(1 for r in batch_records if r.get('validation_status') == 'invalid')
        unvalidated = len(batch_records) - validated - invalid
        
        batch['validated_count'] = validated
        batch['invalid_count'] = invalid
        batch['unvalidated_count'] = unvalidated
    
    return batches


class BatchRenameRequest(BaseModel):
    custom_name: str


@router.patch("/memberwd/staff/batches/{batch_id}/rename")
async def rename_memberwd_batch(batch_id: str, data: BatchRenameRequest, user: User = Depends(get_current_user)):
    """Allow staff to rename their batch card title"""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    # Verify the batch belongs to this staff
    batch = await db.memberwd_batches.find_one({'id': batch_id, 'staff_id': user.id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found or not assigned to you")
    
    # Update the custom name
    await db.memberwd_batches.update_one(
        {'id': batch_id},
        {'$set': {'custom_name': data.custom_name.strip()}}
    )
    
    return {'success': True, 'message': 'Batch renamed successfully', 'custom_name': data.custom_name.strip()}


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


@router.post("/memberwd/staff/validate")
async def validate_memberwd_records(data: RecordValidation, user: User = Depends(get_current_user)):
    """Staff marks records as valid or invalid"""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    now = get_jakarta_now()
    
    # Only allow validating records assigned to this staff
    records = await db.memberwd_records.find({
        'id': {'$in': data.record_ids},
        'assigned_to': user.id
    }).to_list(1000)
    
    if len(records) == 0:
        raise HTTPException(status_code=404, detail="No records found or not assigned to you")
    
    validation_status = 'validated' if data.is_valid else 'invalid'
    
    # Update records
    await db.memberwd_records.update_many(
        {'id': {'$in': data.record_ids}, 'assigned_to': user.id},
        {'$set': {
            'validation_status': validation_status,
            'validated_at': now.isoformat(),
            'validation_reason': data.reason if not data.is_valid else None
        }}
    )
    
    # If marked as invalid, create notification for admin
    if not data.is_valid:
        # Count total invalid records for this staff
        total_invalid = await db.memberwd_records.count_documents({
            'assigned_to': user.id,
            'validation_status': 'invalid'
        })
        
        # Create or update admin notification
        notification = {
            'id': str(uuid.uuid4()),
            'type': 'memberwd_invalid',
            'staff_id': user.id,
            'staff_name': user.name,
            'record_count': len(data.record_ids),
            'total_invalid': total_invalid,
            'reason': data.reason,
            'record_ids': data.record_ids,
            'created_at': now.isoformat(),
            'is_read': False,
            'is_resolved': False
        }
        await db.admin_notifications.insert_one(notification)
    
    return {
        'success': True,
        'message': f'{len(records)} records marked as {"valid" if data.is_valid else "invalid"}',
        'validation_status': validation_status
    }


@router.get("/memberwd/admin/invalid-records")
async def get_invalid_memberwd_records(user: User = Depends(get_admin_user)):
    """Get all invalid memberwd records with staff info (Admin only)"""
    db = get_db()
    
    # Group invalid records by staff (exclude archived records)
    pipeline = [
        {'$match': {'validation_status': 'invalid', 'status': {'$ne': 'invalid_archived'}}},
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
    
    results = await db.memberwd_records.aggregate(pipeline).to_list(100)
    
    return {
        'total_invalid': sum(r['count'] for r in results),
        'by_staff': results
    }


class ProcessInvalidRequest(BaseModel):
    auto_assign_quantity: int = 0  # How many new records to assign (0 = no auto-assign)


@router.post("/memberwd/admin/process-invalid/{staff_id}")
async def process_invalid_memberwd_and_replace(staff_id: str, data: ProcessInvalidRequest, user: User = Depends(get_admin_user)):
    """Archive invalid records and optionally assign new records to staff (to the same batch)"""
    db = get_db()
    
    now = get_jakarta_now()
    
    # Find invalid records
    invalid_records = await db.memberwd_records.find({
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
    
    # Get unique database IDs and batch IDs from invalid records for auto-assignment
    database_ids = list(set(r.get('database_id') for r in invalid_records if r.get('database_id')))
    batch_ids = list(set(r.get('batch_id') for r in invalid_records if r.get('batch_id')))
    
    # Archive invalid records (move to 'invalid_archived' status)
    await db.memberwd_records.update_many(
        {'id': {'$in': record_ids}},
        {'$set': {
            'status': 'invalid_archived',
            'archived_at': now.isoformat(),
            'archived_by': user.id,
            'archived_by_name': user.name
        }}
    )
    
    # Update batch counts
    for batch_id in batch_ids:
        if batch_id:
            archived_in_batch = sum(1 for r in invalid_records if r.get('batch_id') == batch_id)
            await db.memberwd_batches.update_one(
                {'id': batch_id},
                {'$inc': {'current_count': -archived_in_batch, 'archived_count': archived_in_batch}}
            )
    
    # Mark related notifications as resolved
    await db.admin_notifications.update_many(
        {'type': 'memberwd_invalid', 'staff_id': staff_id, 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    # Auto-assign new records if requested
    new_assigned_count = 0
    skipped_reserved = 0
    if data.auto_assign_quantity > 0 and database_ids:
        # Find available records from the same databases
        available_records = await db.memberwd_records.find({
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
            
            # Use the first batch_id from invalid records for replacement records
            target_batch_id = batch_ids[0] if batch_ids else None
            
            update_data = {
                'status': 'assigned',
                'assigned_to': staff['id'],
                'assigned_to_name': staff['name'],
                'assigned_at': now.isoformat(),
                'assigned_by': user.id,
                'assigned_by_name': user.name,
                'auto_replaced': True,
                'replaced_invalid_ids': record_ids
            }
            
            if target_batch_id:
                update_data['batch_id'] = target_batch_id
            
            await db.memberwd_records.update_many(
                {'id': {'$in': selected_ids}},
                {'$set': update_data}
            )
            
            # Update batch count with new assignments
            if target_batch_id:
                await db.memberwd_batches.update_one(
                    {'id': target_batch_id},
                    {'$inc': {'current_count': len(selected_ids), 'replaced_count': len(selected_ids)}}
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
@router.post("/memberwd/admin/reassign-invalid/{staff_id}")
async def reassign_invalid_memberwd_to_available(staff_id: str, user: User = Depends(get_admin_user)):
    """Legacy endpoint - now archives instead of returning to pool"""
    return await process_invalid_memberwd_and_replace(staff_id, ProcessInvalidRequest(auto_assign_quantity=0), user)


@router.get("/memberwd/admin/archived-invalid")
async def get_archived_invalid_memberwd_records(user: User = Depends(get_admin_user)):
    """Get all archived invalid records (Invalid Database section)"""
    db = get_db()
    
    records = await db.memberwd_records.find(
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


@router.post("/memberwd/admin/archived-invalid/{record_id}/restore")
async def restore_archived_memberwd_record(record_id: str, user: User = Depends(get_admin_user)):
    """Restore an archived invalid record back to available pool"""
    db = get_db()
    
    now = get_jakarta_now()
    
    result = await db.memberwd_records.update_one(
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


@router.delete("/memberwd/admin/archived-invalid/{record_id}")
async def delete_archived_memberwd_record(record_id: str, user: User = Depends(get_admin_user)):
    """Permanently delete an archived invalid record"""
    db = get_db()
    
    result = await db.memberwd_records.delete_one({'id': record_id, 'status': 'invalid_archived'})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found or not archived")
    
    return {'success': True, 'message': 'Record permanently deleted'}

@router.get("/memberwd/staff")
async def get_memberwd_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff
