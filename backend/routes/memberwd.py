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


class MemberWDSettings(BaseModel):
    auto_replace_invalid: bool = False  # Toggle auto vs manual replacement
    max_replacements_per_batch: int = 10  # Maximum replacements per batch card


# Default settings
DEFAULT_MEMBERWD_SETTINGS = {
    'id': 'memberwd_settings',
    'auto_replace_invalid': False,
    'max_replacements_per_batch': 10
}


@router.get("/memberwd/admin/settings")
async def get_memberwd_settings(user: User = Depends(get_admin_user)):
    """Get Member WD settings"""
    db = get_db()
    settings = await db.app_settings.find_one({'id': 'memberwd_settings'}, {'_id': 0})
    if not settings:
        # Create default settings
        await db.app_settings.insert_one(DEFAULT_MEMBERWD_SETTINGS.copy())
        settings = DEFAULT_MEMBERWD_SETTINGS.copy()
    return settings


@router.put("/memberwd/admin/settings")
async def update_memberwd_settings(data: MemberWDSettings, user: User = Depends(get_admin_user)):
    """Update Member WD settings"""
    db = get_db()
    now = get_jakarta_now()
    
    await db.app_settings.update_one(
        {'id': 'memberwd_settings'},
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


@router.post("/memberwd/admin/migrate-batches")
async def migrate_existing_records_to_batches(user: User = Depends(get_admin_user)):
    """
    Migration endpoint: Auto-create batch cards for existing assigned records that don't have batch_id.
    
    Logic:
    1. Group REGULAR records by staff_id + database_id + EXACT assigned_at timestamp
    2. Create batches for each group
    3. For REPLACEMENT records (auto_replaced=True): Find the correct batch by looking up 
       the assigned_at of the invalid records they replaced
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
    
    # STEP 1: Group REGULAR records by staff_id + database_id + EXACT assigned_at timestamp
    groups = {}
    for record in regular_records:
        staff_id = record.get('assigned_to')
        database_id = record.get('database_id')
        assigned_at = record.get('assigned_at', '')
        
        if not staff_id or not database_id:
            continue
        
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
                'assigned_by': record.get('assigned_by_name', 'System Migration'),
                'assignment_key': assignment_key
            }
        
        groups[key]['records'].append(record)
    
    # STEP 2: Create batches for regular records and build timestamp->batch_id mapping
    batches_created = 0
    records_updated = 0
    timestamp_to_batch = {}  # Maps (staff_id, database_id, assigned_at) -> batch_id
    
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
        
        # Store mapping for replacement record lookup
        timestamp_to_batch[key] = batch_id
        
        # Update all records in this group with the batch_id
        record_ids = [r['id'] for r in group['records']]
        result = await db.memberwd_records.update_many(
            {'id': {'$in': record_ids}},
            {'$set': {'batch_id': batch_id}}
        )
        records_updated += result.modified_count
    
    # STEP 3: Handle replacement records - find correct batch from invalid records they replaced
    replacement_count = 0
    replacement_failed = 0
    
    for record in replacement_records:
        invalid_ids = record.get('replaced_invalid_ids', [])
        if not invalid_ids:
            replacement_failed += 1
            continue
        
        # Find one of the invalid records to get its original assigned_at
        # This tells us which batch the replacement should belong to
        invalid_record = await db.memberwd_records.find_one(
            {'id': {'$in': invalid_ids}},
            {'_id': 0, 'assigned_at': 1, 'assigned_to': 1, 'database_id': 1}
        )
        
        if not invalid_record:
            replacement_failed += 1
            continue
        
        # Build the key to find the correct batch
        staff_id = invalid_record.get('assigned_to')
        database_id = invalid_record.get('database_id')
        assigned_at = invalid_record.get('assigned_at', '')
        
        lookup_key = f"{staff_id}|{database_id}|{assigned_at}"
        
        if lookup_key in timestamp_to_batch:
            # Found the batch! Assign replacement record to it
            target_batch_id = timestamp_to_batch[lookup_key]
            await db.memberwd_records.update_one(
                {'id': record['id']},
                {'$set': {'batch_id': target_batch_id}}
            )
            replacement_count += 1
        else:
            # Batch not found - might be in a non-migrated batch
            # Try to find existing batch by matching timestamp
            existing_batch = await db.memberwd_batches.find_one(
                {
                    'staff_id': staff_id,
                    'database_id': database_id,
                    'created_at': assigned_at
                },
                {'_id': 0, 'id': 1}
            )
            if existing_batch:
                await db.memberwd_records.update_one(
                    {'id': record['id']},
                    {'$set': {'batch_id': existing_batch['id']}}
                )
                replacement_count += 1
            else:
                replacement_failed += 1
    
    return {
        'success': True,
        'message': f'Migration completed: {batches_created} batches created, {records_updated} regular records, {replacement_count} replacement records linked',
        'batches_created': batches_created,
        'records_updated': records_updated,
        'replacement_records_linked': replacement_count,
        'replacement_records_failed': replacement_failed,
        'total_records': records_updated + replacement_count,
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
    
    # Get all approved reserved members for excluded count calculation
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1, 'product_id': 1}
    ).to_list(100000)
    
    # Build set of reserved customer identifiers per product
    reserved_by_product = {}
    for rm in reserved_members:
        prod_id = rm.get('product_id', '')
        if prod_id not in reserved_by_product:
            reserved_by_product[prod_id] = set()
        if rm.get('customer_id'):
            reserved_by_product[prod_id].add(rm['customer_id'].strip().upper())
        if rm.get('customer_name'):
            reserved_by_product[prod_id].add(rm['customer_name'].strip().upper())
    
    for database in databases:
        total = await db.memberwd_records.count_documents({'database_id': database['id']})
        assigned = await db.memberwd_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        archived = await db.memberwd_records.count_documents({'database_id': database['id'], 'status': 'invalid_archived'})
        
        # Calculate excluded count
        excluded_count = 0
        product_id_for_db = database.get('product_id', '')
        available_raw = total - assigned - archived  # Don't count archived as available
        
        if product_id_for_db and product_id_for_db in reserved_by_product and available_raw > 0:
            # Get available records to check against reserved members
            available_records = await db.memberwd_records.find(
                {'database_id': database['id'], 'status': 'available'},
                {'_id': 0, 'row_data': 1}
            ).to_list(100000)
            
            reserved_set = reserved_by_product[product_id_for_db]
            for record in available_records:
                row_data = record.get('row_data', {})
                customer_id = None
                for key in ['customer_id', 'Customer_ID', 'CUSTOMER_ID', 'ID', 'id', 'Username', 'USERNAME', 'username']:
                    if key in row_data and row_data[key]:
                        customer_id = str(row_data[key]).strip().upper()
                        break
                
                if customer_id and customer_id in reserved_set:
                    excluded_count += 1
        
        database['total_records'] = total
        database['assigned_count'] = assigned
        database['archived_count'] = archived
        database['excluded_count'] = excluded_count
        database['available_count'] = available_raw - excluded_count
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
        
        # Count by validation status (check both 'valid' and 'validated' for compatibility)
        validated = sum(1 for r in batch_records if r.get('validation_status') in ['valid', 'validated'])
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
    """Staff marks records as valid or invalid. Auto-replaces if enabled in settings."""
    db = get_db()
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="Only staff can access this endpoint")
    
    now = get_jakarta_now()
    
    # Only allow validating records assigned to this staff
    records = await db.memberwd_records.find({
        'id': {'$in': data.record_ids},
        'assigned_to': user.id
    }, {'_id': 0}).to_list(1000)
    
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
        settings = await db.app_settings.find_one({'id': 'memberwd_settings'}, {'_id': 0})
        if not settings:
            settings = DEFAULT_MEMBERWD_SETTINGS.copy()
        
        auto_replace = settings.get('auto_replace_invalid', False)
        max_per_batch = settings.get('max_replacements_per_batch', 10)
        
        if auto_replace:
            # Group invalid records by batch_id and database_id
            invalid_by_batch = {}
            for record in records:
                batch_id = record.get('batch_id')
                database_id = record.get('database_id')
                if batch_id and database_id:
                    key = f"{batch_id}|{database_id}"
                    if key not in invalid_by_batch:
                        invalid_by_batch[key] = {
                            'batch_id': batch_id,
                            'database_id': database_id,
                            'database_name': record.get('database_name', 'Unknown'),
                            'product_id': record.get('product_id', ''),
                            'records': []
                        }
                    invalid_by_batch[key]['records'].append(record)
            
            total_replaced = 0
            total_failed = 0
            replacement_details = []
            
            for key, group in invalid_by_batch.items():
                batch_id = group['batch_id']
                database_id = group['database_id']
                invalid_records = group['records']
                invalid_ids = [r['id'] for r in invalid_records]
                
                # Check how many replacements already done for this batch
                existing_replacements = await db.memberwd_records.count_documents({
                    'batch_id': batch_id,
                    'auto_replaced': True,
                    'status': 'assigned'
                })
                
                # Calculate how many more replacements allowed
                remaining_quota = max(0, max_per_batch - existing_replacements)
                needed = len(invalid_records)
                can_replace = min(needed, remaining_quota)
                
                if can_replace == 0:
                    # Limit reached, notify staff
                    total_failed += needed
                    replacement_details.append({
                        'batch': batch_id[:8],
                        'database': group['database_name'],
                        'needed': needed,
                        'replaced': 0,
                        'reason': f'Replacement limit reached ({max_per_batch} per batch)'
                    })
                    continue
                
                # Get available records from the SAME database
                available = await db.memberwd_records.find({
                    'database_id': database_id,
                    'status': 'available'
                }, {'_id': 0}).to_list(can_replace)
                
                if len(available) == 0:
                    # No records available
                    total_failed += can_replace
                    replacement_details.append({
                        'batch': batch_id[:8],
                        'database': group['database_name'],
                        'needed': needed,
                        'replaced': 0,
                        'reason': 'No available records in database'
                    })
                    continue
                
                # Assign available records as replacements
                to_assign = available[:can_replace]
                assigned_ids = [r['id'] for r in to_assign]
                
                await db.memberwd_records.update_many(
                    {'id': {'$in': assigned_ids}},
                    {'$set': {
                        'status': 'assigned',
                        'assigned_to': user.id,
                        'assigned_to_name': user.name,
                        'assigned_at': now.isoformat(),
                        'batch_id': batch_id,
                        'auto_replaced': True,
                        'replaced_invalid_ids': invalid_ids[:len(assigned_ids)]
                    }}
                )
                
                # Archive the invalid records
                await db.memberwd_records.update_many(
                    {'id': {'$in': invalid_ids[:len(assigned_ids)]}},
                    {'$set': {
                        'status': 'invalid_archived',
                        'archived_at': now.isoformat(),
                        'auto_archived': True
                    }}
                )
                
                # Update batch counts
                await db.memberwd_batches.update_one(
                    {'id': batch_id},
                    {'$inc': {
                        'replaced_count': len(assigned_ids),
                        'archived_count': len(assigned_ids)
                    }}
                )
                
                total_replaced += len(assigned_ids)
                
                # If couldn't replace all
                if len(assigned_ids) < can_replace:
                    total_failed += (can_replace - len(assigned_ids))
                
                if needed > can_replace:
                    total_failed += (needed - can_replace)
                
                replacement_details.append({
                    'batch': batch_id[:8],
                    'database': group['database_name'],
                    'needed': needed,
                    'replaced': len(assigned_ids),
                    'reason': None if len(assigned_ids) >= needed else (
                        'Limit reached' if remaining_quota < needed else 'Not enough available'
                    )
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
        
        # Always create admin notification for invalid records
        total_invalid = await db.memberwd_records.count_documents({
            'assigned_to': user.id,
            'validation_status': 'invalid',
            'status': 'assigned'
        })
        
        if total_invalid > 0:  # Only notify if there are still unresolved invalid records
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
                'is_resolved': False,
                'auto_replaced': response.get('auto_replaced', 0)
            }
            await db.admin_notifications.insert_one(notification)
    
    return response


@router.get("/memberwd/admin/invalid-records")
async def get_invalid_memberwd_records(user: User = Depends(get_admin_user)):
    """Get all invalid memberwd records with staff info (Admin only)"""
    db = get_db()
    
    # Group invalid records by staff (only show ASSIGNED records, not recalled/available ones)
    pipeline = [
        {'$match': {
            'validation_status': 'invalid', 
            'status': 'assigned'  # Only show records still assigned to staff
        }},
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


@router.post("/memberwd/admin/dismiss-invalid-alerts")
async def dismiss_invalid_alerts(user: User = Depends(get_admin_user)):
    """
    Clear invalid status from records that are no longer assigned.
    This is for cleanup when records were recalled but still show as invalid.
    """
    db = get_db()
    now = get_jakarta_now()
    
    # Find records that have validation_status='invalid' but are not assigned
    # These are orphaned invalid alerts that should be cleared
    result = await db.memberwd_records.update_many(
        {
            'validation_status': 'invalid',
            'status': {'$ne': 'assigned'}  # Not assigned (available, recalled, etc.)
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
    
    # Also resolve any related notifications
    await db.admin_notifications.update_many(
        {'type': 'memberwd_invalid', 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    return {
        'success': True,
        'cleared_count': result.modified_count,
        'message': f'{result.modified_count} orphaned invalid alerts cleared'
    }


class ProcessInvalidRequest(BaseModel):
    auto_assign_quantity: int = 0  # How many new records to assign (0 = no auto-assign)


@router.post("/memberwd/admin/process-invalid/{staff_id}")
async def process_invalid_memberwd_and_replace(staff_id: str, data: ProcessInvalidRequest, user: User = Depends(get_admin_user)):
    """
    Archive invalid records and optionally assign new records to staff.
    
    CRITICAL: Each replacement MUST go to the SAME batch as the invalid record it replaces.
    1 invalid = 1 replacement, in the SAME batch.
    Also ensures replacements come from the SAME product/database.
    """
    db = get_db()
    
    now = get_jakarta_now()
    
    # Find invalid records WITH their batch info
    invalid_records = await db.memberwd_records.find({
        'assigned_to': staff_id,
        'validation_status': 'invalid',
        'status': 'assigned'  # Only get records that are still assigned (not already archived or recalled)
    }, {'_id': 0}).to_list(10000)
    
    if len(invalid_records) == 0:
        raise HTTPException(status_code=404, detail="No invalid records found for this staff")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    record_ids = [r['id'] for r in invalid_records]
    
    # Group invalid records by batch_id AND database_id
    # This is critical: replacements must go to the SAME batch and be from SAME product
    invalid_by_batch = {}  # batch_id -> list of invalid records
    for r in invalid_records:
        batch_id = r.get('batch_id')
        database_id = r.get('database_id')
        key = f"{batch_id}|{database_id}"
        if key not in invalid_by_batch:
            invalid_by_batch[key] = {
                'batch_id': batch_id,
                'database_id': database_id,
                'database_name': r.get('database_name', 'Unknown'),
                'records': []
            }
        invalid_by_batch[key]['records'].append(r)
    
    # Archive invalid records (move to 'invalid_archived' status)
    # Keep their batch_id so we can trace them later!
    await db.memberwd_records.update_many(
        {'id': {'$in': record_ids}},
        {'$set': {
            'status': 'invalid_archived',
            'archived_at': now.isoformat(),
            'archived_by': user.id,
            'archived_by_name': user.name
        }}
    )
    
    # Update batch counts (decrease by archived count)
    for group in invalid_by_batch.values():
        batch_id = group['batch_id']
        if batch_id:
            archived_count = len(group['records'])
            await db.memberwd_batches.update_one(
                {'id': batch_id},
                {'$inc': {'current_count': -archived_count, 'archived_count': archived_count}}
            )
    
    # Mark related notifications as resolved
    await db.admin_notifications.update_many(
        {'type': 'memberwd_invalid', 'staff_id': staff_id, 'is_resolved': False},
        {'$set': {'is_resolved': True, 'resolved_at': now.isoformat(), 'resolved_by': user.name}}
    )
    
    # Auto-assign new records if requested
    new_assigned_count = 0
    skipped_reserved = 0
    assignment_details = []
    
    if data.auto_assign_quantity > 0:
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
            """Check if a record is reserved"""
            row_data = record.get('row_data', {})
            for key in ['Username', 'username', 'USER', 'user', 'ID', 'id']:
                if key in row_data and row_data[key]:
                    if str(row_data[key]).strip().upper() in reserved_ids:
                        return True
            for key in ['Nama Lengkap', 'nama_lengkap', 'Name', 'name', 'NAMA']:
                if key in row_data and row_data[key]:
                    if str(row_data[key]).strip().upper() in reserved_ids:
                        return True
            return False
        
        # Process each batch group separately
        # Key: Each invalid record gets replaced by one record from the SAME database, 
        # assigned to the SAME batch
        # Replace ALL invalid records (not limited by auto_assign_quantity)
        
        for key, group in invalid_by_batch.items():
            batch_id = group['batch_id']
            database_id = group['database_id']
            invalid_in_group = group['records']
            invalid_ids_in_group = [r['id'] for r in invalid_in_group]
            
            # Need to replace ALL invalid records in this batch
            needed_for_batch = len(invalid_in_group)
            
            if not database_id:
                continue  # Can't replace without knowing the database
            
            # Get available records from the SAME database only
            available_records = await db.memberwd_records.find({
                'database_id': database_id,
                'status': 'available'
            }, {'_id': 0}).to_list(needed_for_batch * 3)
            
            # Filter out reserved
            eligible_records = []
            for record in available_records:
                if is_reserved(record):
                    skipped_reserved += 1
                else:
                    eligible_records.append(record)
                    if len(eligible_records) >= needed_for_batch:
                        break
            
            # Assign eligible records to THIS batch
            if eligible_records:
                selected_ids = [r['id'] for r in eligible_records]
                
                await db.memberwd_records.update_many(
                    {'id': {'$in': selected_ids}},
                    {'$set': {
                        'status': 'assigned',
                        'assigned_to': staff['id'],
                        'assigned_to_name': staff['name'],
                        'assigned_at': now.isoformat(),
                        'assigned_by': user.id,
                        'assigned_by_name': user.name,
                        'batch_id': batch_id,  # SAME batch as invalid!
                        'auto_replaced': True,
                        'replaced_invalid_ids': invalid_ids_in_group  # Link to specific invalids
                    }}
                )
                
                # Update batch count (increase by new assignments)
                if batch_id:
                    await db.memberwd_batches.update_one(
                        {'id': batch_id},
                        {'$inc': {'current_count': len(selected_ids), 'replaced_count': len(selected_ids)}}
                    )
                
                new_assigned_count += len(selected_ids)
                
                assignment_details.append({
                    'batch': batch_id[:8] if batch_id else 'no-batch',
                    'database': group['database_name'],
                    'invalid_count': len(invalid_in_group),
                    'replaced_count': len(selected_ids),
                    'shortage': needed_for_batch - len(selected_ids) if len(selected_ids) < needed_for_batch else 0
                })
    
    # Build message
    total_invalid = len(record_ids)
    message = f'{total_invalid} record diarsipkan.'
    if data.auto_assign_quantity > 0:
        message += f' {new_assigned_count} record baru ditugaskan ke {staff["name"]}.'
        if skipped_reserved > 0:
            message += f' ({skipped_reserved} record reserved member dilewati)'
        if new_assigned_count < total_invalid:
            shortage = total_invalid - new_assigned_count
            message += f' Kekurangan {shortage} record karena tidak tersedia.'
    
    return {
        'success': True,
        'archived_count': len(record_ids),
        'new_assigned_count': new_assigned_count,
        'skipped_reserved': skipped_reserved,
        'message': message,
        'assignment_details': assignment_details  # Show which batch got how many replacements
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


class RecallRecordsRequest(BaseModel):
    record_ids: List[str]


@router.post("/memberwd/admin/recall-records")
async def recall_assigned_records(data: RecallRecordsRequest, user: User = Depends(get_admin_user)):
    """
    Recall assigned records from staff - return them to available pool.
    This removes records from staff's Member WD CRM list.
    """
    db = get_db()
    now = get_jakarta_now()
    
    if not data.record_ids:
        raise HTTPException(status_code=400, detail="No record IDs provided")
    
    # Find the records to recall
    records_to_recall = await db.memberwd_records.find({
        'id': {'$in': data.record_ids},
        'status': 'assigned'
    }, {'_id': 0}).to_list(10000)
    
    if not records_to_recall:
        raise HTTPException(status_code=404, detail="No assigned records found with the provided IDs")
    
    # Group by batch_id to update batch counts
    batch_counts = {}
    for record in records_to_recall:
        batch_id = record.get('batch_id')
        if batch_id:
            batch_counts[batch_id] = batch_counts.get(batch_id, 0) + 1
    
    # Update records: set status back to 'available' and clear assignment fields
    result = await db.memberwd_records.update_many(
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
                'batch_id': '',
                'validation_status': '',
                'validated_at': '',
                'validation_reason': '',
                'auto_replaced': '',
                'replaced_invalid_ids': ''
            }
        }
    )
    
    # Update batch counts
    for batch_id, count in batch_counts.items():
        await db.memberwd_batches.update_one(
            {'id': batch_id},
            {'$inc': {'current_count': -count, 'recalled_count': count}}
        )
    
    # Delete empty batches (current_count <= 0)
    await db.memberwd_batches.delete_many({'current_count': {'$lte': 0}})
    
    return {
        'success': True,
        'recalled_count': result.modified_count,
        'message': f'{result.modified_count} records recalled and returned to available pool'
    }


@router.get("/memberwd/staff")
async def get_memberwd_staff_list(user: User = Depends(get_admin_user)):
    """Get list of staff members for assignment"""
    db = get_db()
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    return staff


@router.post("/memberwd/admin/repair-data")
async def repair_memberwd_data(user: User = Depends(get_admin_user)):
    """
    Repair and synchronize memberwd record data.
    This fixes inconsistencies caused by pre-update code.
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
    databases = await db.memberwd_databases.find({}, {'_id': 0}).to_list(1000)
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        product_name = database.get('product_name', 'Unknown')
        
        # Fix records with missing database_name
        result = await db.memberwd_records.update_many(
            {'database_id': db_id, 'database_name': {'$exists': False}},
            {'$set': {'database_name': db_name, 'product_name': product_name}}
        )
        if result.modified_count > 0:
            repair_log['fixed_missing_db_info'] += result.modified_count
        
        # Fix records with None database_name
        result = await db.memberwd_records.update_many(
            {'database_id': db_id, 'database_name': None},
            {'$set': {'database_name': db_name, 'product_name': product_name}}
        )
        if result.modified_count > 0:
            repair_log['fixed_missing_db_info'] += result.modified_count
        
        # Fix invalid status values
        valid_statuses = ['available', 'assigned', 'invalid_archived']
        result = await db.memberwd_records.update_many(
            {'database_id': db_id, 'status': {'$nin': valid_statuses}},
            {'$set': {'status': 'available'}}
        )
        if result.modified_count > 0:
            repair_log['fixed_invalid_status'] += result.modified_count
        
        # Fix orphaned assignments
        result = await db.memberwd_records.update_many(
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
        
        # Recalculate counts
        available = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db.memberwd_records.count_documents({'database_id': db_id})
        
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


@router.get("/memberwd/admin/data-health")
async def get_memberwd_data_health(user: User = Depends(get_admin_user)):
    """Check the health of memberwd data without making changes."""
    db = get_db()
    
    health_report = {
        'databases': [],
        'total_issues': 0,
        'issues': []
    }
    
    databases = await db.memberwd_databases.find({}, {'_id': 0}).to_list(1000)
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        
        available = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db.memberwd_records.count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db.memberwd_records.count_documents({'database_id': db_id})
        
        missing_db_name = await db.memberwd_records.count_documents({
            'database_id': db_id, 
            '$or': [{'database_name': {'$exists': False}}, {'database_name': None}]
        })
        
        orphaned_assignments = await db.memberwd_records.count_documents({
            'database_id': db_id, 
            'status': 'assigned', 
            'assigned_to': None
        })
        
        invalid_status = await db.memberwd_records.count_documents({
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
    
    health_report['is_healthy'] = health_report['total_issues'] == 0
    
    return health_report
