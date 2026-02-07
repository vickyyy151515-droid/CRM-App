"""
Database Operations Helper Functions
Common CRUD and validation operations for all record modules (Normal DB, Bonanza, MemberWD)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import uuid

from utils.helpers import get_jakarta_now, normalize_customer_id


# Reusable approval filter: only include approved records (or records without approval_status field)
APPROVED_FILTER = {'$or': [{'approval_status': 'approved'}, {'approval_status': {'$exists': False}}]}


def add_approved_filter(query: dict) -> dict:
    """Add approval_status filter to only include approved records in calculations.
    Safely handles queries that already have $or or $and conditions."""
    approval_condition = {'$or': [{'approval_status': 'approved'}, {'approval_status': {'$exists': False}}]}
    
    if '$and' in query:
        query['$and'].append(approval_condition)
    elif '$or' in query:
        existing_or = query.pop('$or')
        query['$and'] = [{'$or': existing_or}, approval_condition]
    else:
        query['$or'] = approval_condition['$or']
    return query



async def build_staff_first_date_map(db, product_id: str = None) -> Dict[Tuple[str, str, str], str]:
    """
    Build a map of (staff_id, customer_id_normalized, product_id) -> first_date
    using MongoDB aggregation instead of loading all records into memory.
    
    This is the SINGLE SOURCE OF TRUTH for NDP/RDP across all views.
    Excludes "tambahan" records from first_date calculation.
    
    IMPORTANT: The customer_id normalization must match normalize_customer_id() from helpers.py:
    - lowercase, strip whitespace, remove special chars except alphanumeric/hyphens/underscores
    
    Args:
        db: Database connection
        product_id: Optional product filter
    
    Returns:
        Dict mapping (staff_id, customer_id, product_id) to first record date
    """
    from utils.helpers import normalize_customer_id
    
    match_stage = {
        '$match': {
            '$and': [
                {'$or': [
                    {'keterangan': {'$exists': False}},
                    {'keterangan': None},
                    {'keterangan': ''},
                    {'keterangan': {'$not': {'$regex': 'tambahan', '$options': 'i'}}}
                ]},
                # Only count approved records in NDP/RDP calculations
                {'$or': [
                    {'approval_status': 'approved'},
                    {'approval_status': {'$exists': False}}
                ]}
            ]
        }
    }
    
    if product_id:
        match_stage['$match']['$and'].append({'product_id': product_id})
    
    # Use customer_id_normalized if available, otherwise fall back to customer_id
    pipeline = [
        match_stage,
        {
            '$group': {
                '_id': {
                    's': '$staff_id',
                    'c': {'$ifNull': ['$customer_id_normalized', '$customer_id']},
                    'p': '$product_id'
                },
                'first_date': {'$min': '$record_date'}
            }
        }
    ]
    
    results = await db.omset_records.aggregate(pipeline).to_list(None)
    
    # Normalize customer IDs using the SAME function used in all endpoints
    first_date_map = {}
    for r in results:
        staff_id = r['_id']['s']
        raw_cid = r['_id']['c']
        prod_id = r['_id']['p']
        
        if not staff_id or not raw_cid or not prod_id:
            continue
        
        normalized_cid = normalize_customer_id(raw_cid)
        if not normalized_cid:
            continue
        
        key = (staff_id, normalized_cid, prod_id)
        # Keep the earliest first_date if there are collisions after normalization
        if key not in first_date_map or r['first_date'] < first_date_map[key]:
            first_date_map[key] = r['first_date']
    
    return first_date_map


async def recalculate_customer_type(db, staff_id: str, customer_id: str, product_id: str):
    """
    Recalculate and update the stored customer_type (NDP/RDP) for all records
    matching a specific (staff_id, customer_id, product_id) combo.
    
    Call this after delete, approve, decline, or restore operations to keep
    the stored customer_type in sync with the dynamic NDP/RDP calculation.
    """
    from utils.helpers import normalize_customer_id
    
    normalized_cid = normalize_customer_id(customer_id)
    
    # Find all approved records for this (staff, customer, product) combo
    query = {
        'staff_id': staff_id,
        'product_id': product_id,
        '$and': [
            {'$or': [
                {'customer_id_normalized': normalized_cid},
                {'customer_id': {'$regex': f'^{customer_id.strip()}$', '$options': 'i'}}
            ]},
            {'$or': [
                {'approval_status': 'approved'},
                {'approval_status': {'$exists': False}}
            ]}
        ]
    }
    records = await db.omset_records.find(
        query,
        {'_id': 0, 'id': 1, 'record_date': 1, 'keterangan': 1, 'customer_id': 1, 'customer_id_normalized': 1}
    ).sort('record_date', 1).to_list(10000)
    
    if not records:
        return
    
    # Find first_date (earliest non-tambahan record)
    first_date = None
    for r in records:
        keterangan = r.get('keterangan', '') or ''
        if 'tambahan' not in keterangan.lower():
            first_date = r['record_date']
            break
    
    # Update each record's customer_type
    for r in records:
        keterangan = r.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            new_type = 'RDP'
        elif first_date and r['record_date'] == first_date:
            new_type = 'NDP'
        else:
            new_type = 'RDP'
        
        await db.omset_records.update_one(
            {'id': r['id']},
            {'$set': {'customer_type': new_type}}
        )



# Collection name mapping
COLLECTION_MAP = {
    'records': {
        'databases': 'databases',
        'records': 'customer_records'
    },
    'bonanza': {
        'databases': 'bonanza_databases',
        'records': 'bonanza_records'
    },
    'memberwd': {
        'databases': 'memberwd_databases',
        'records': 'memberwd_records',
        'batches': 'memberwd_batches'
    }
}


def get_collection_names(module: str) -> Dict[str, str]:
    """Get collection names for a module."""
    return COLLECTION_MAP.get(module, COLLECTION_MAP['records'])


async def count_records_by_status(
    db,
    database_id: str,
    collection_name: str
) -> Dict[str, int]:
    """
    Count records by status for a database.
    
    Returns:
        Dict with counts: {total, available, assigned, archived}
    """
    total = await db[collection_name].count_documents({'database_id': database_id})
    available = await db[collection_name].count_documents({'database_id': database_id, 'status': 'available'})
    assigned = await db[collection_name].count_documents({'database_id': database_id, 'status': 'assigned'})
    archived = await db[collection_name].count_documents({'database_id': database_id, 'status': 'invalid_archived'})
    invalid = await db[collection_name].count_documents({'database_id': database_id, 'status': 'invalid'})
    
    return {
        'total': total,
        'available': available,
        'assigned': assigned,
        'archived': archived,
        'invalid': invalid
    }


async def get_database_with_stats(
    db,
    database_id: str,
    module: str = 'records'
) -> Optional[Dict[str, Any]]:
    """
    Get database with calculated statistics.
    
    Args:
        db: Database connection
        database_id: Database ID
        module: Module type ('records', 'bonanza', 'memberwd')
        
    Returns:
        Database dict with stats or None
    """
    collections = get_collection_names(module)
    
    database = await db[collections['databases']].find_one(
        {'id': database_id}, 
        {'_id': 0}
    )
    
    if not database:
        return None
    
    stats = await count_records_by_status(db, database_id, collections['records'])
    database.update(stats)
    
    return database


async def delete_database_with_records(
    db,
    database_id: str,
    module: str = 'records'
) -> Dict[str, int]:
    """
    Delete a database and all its associated records.
    
    Args:
        db: Database connection
        database_id: Database ID to delete
        module: Module type
        
    Returns:
        Dict with deletion counts
    """
    collections = get_collection_names(module)
    
    # Delete records first
    records_result = await db[collections['records']].delete_many({'database_id': database_id})
    
    # Delete database
    db_result = await db[collections['databases']].delete_one({'id': database_id})
    
    # For memberwd, also delete batches
    batches_deleted = 0
    if module == 'memberwd' and 'batches' in collections:
        batches_result = await db[collections['batches']].delete_many({'database_id': database_id})
        batches_deleted = batches_result.deleted_count
    
    return {
        'database_deleted': db_result.deleted_count,
        'records_deleted': records_result.deleted_count,
        'batches_deleted': batches_deleted
    }


async def assign_records_to_staff(
    db,
    record_ids: List[str],
    staff_id: str,
    staff_name: str,
    collection_name: str,
    batch_id: Optional[str] = None,
    extra_fields: Optional[Dict] = None
) -> int:
    """
    Assign records to a staff member.
    
    Args:
        db: Database connection
        record_ids: List of record IDs to assign
        staff_id: Staff user ID
        staff_name: Staff name
        collection_name: Records collection name
        batch_id: Optional batch ID (for memberwd)
        extra_fields: Additional fields to set
        
    Returns:
        Number of records updated
    """
    if not record_ids:
        return 0
    
    now = get_jakarta_now()
    
    update_data = {
        'status': 'assigned',
        'assigned_to': staff_id,
        'assigned_to_name': staff_name,
        'assigned_at': now.isoformat()
    }
    
    if batch_id:
        update_data['batch_id'] = batch_id
    
    if extra_fields:
        update_data.update(extra_fields)
    
    result = await db[collection_name].update_many(
        {'id': {'$in': record_ids}},
        {'$set': update_data}
    )
    
    return result.modified_count


async def recall_records_from_staff(
    db,
    record_ids: List[str],
    collection_name: str
) -> int:
    """
    Recall assigned records back to available status.
    
    Args:
        db: Database connection
        record_ids: List of record IDs to recall
        collection_name: Records collection name
        
    Returns:
        Number of records updated
    """
    if not record_ids:
        return 0
    
    result = await db[collection_name].update_many(
        {'id': {'$in': record_ids}},
        {
            '$set': {
                'status': 'available',
                'assigned_to': None,
                'assigned_to_name': None,
                'assigned_at': None,
                'batch_id': None,
                'validation_status': None,
                'validated_at': None,
                'is_reservation_conflict': None
            }
        }
    )
    
    return result.modified_count


async def archive_records(
    db,
    record_ids: List[str],
    collection_name: str,
    archived_by: str,
    archive_reason: str = 'Archived by admin'
) -> int:
    """
    Archive records (mark as invalid_archived).
    
    Args:
        db: Database connection
        record_ids: List of record IDs to archive
        collection_name: Records collection name
        archived_by: User who archived
        archive_reason: Reason for archiving
        
    Returns:
        Number of records archived
    """
    if not record_ids:
        return 0
    
    now = get_jakarta_now()
    
    result = await db[collection_name].update_many(
        {'id': {'$in': record_ids}},
        {
            '$set': {
                'status': 'invalid_archived',
                'archived_at': now.isoformat(),
                'archived_by': archived_by,
                'archive_reason': archive_reason
            }
        }
    )
    
    return result.modified_count


async def get_available_records(
    db,
    database_id: str,
    collection_name: str,
    limit: Optional[int] = None,
    excluded_customer_ids: Optional[set] = None
) -> List[Dict]:
    """
    Get available records from a database, optionally excluding certain customers.
    
    Args:
        db: Database connection
        database_id: Database ID
        collection_name: Records collection name
        limit: Maximum number of records to return
        excluded_customer_ids: Set of normalized customer IDs to exclude
        
    Returns:
        List of available records
    """
    query = {
        'database_id': database_id,
        'status': 'available'
    }
    
    cursor = db[collection_name].find(query, {'_id': 0})
    
    if limit:
        cursor = cursor.limit(limit * 2 if excluded_customer_ids else limit)
    
    records = await cursor.to_list(None)
    
    # Filter out excluded customers if needed
    if excluded_customer_ids:
        filtered_records = []
        for record in records:
            customer_id = normalize_customer_id(
                record.get('customer_id') or 
                record.get('customer_id_normalized') or
                ''
            )
            if customer_id and customer_id.upper() not in excluded_customer_ids:
                filtered_records.append(record)
                if limit and len(filtered_records) >= limit:
                    break
        return filtered_records
    
    return records[:limit] if limit else records


async def validate_record(
    db,
    record_id: str,
    collection_name: str,
    is_valid: bool,
    validated_by: str,
    validation_note: Optional[str] = None
) -> bool:
    """
    Mark a record as valid or invalid.
    
    Args:
        db: Database connection
        record_id: Record ID
        collection_name: Records collection name
        is_valid: Whether record is valid
        validated_by: User who validated
        validation_note: Optional validation note
        
    Returns:
        True if update successful
    """
    now = get_jakarta_now()
    
    update_data = {
        'validation_status': 'valid' if is_valid else 'invalid',
        'validated_at': now.isoformat(),
        'validated_by': validated_by
    }
    
    if validation_note:
        update_data['validation_note'] = validation_note
    
    result = await db[collection_name].update_one(
        {'id': record_id},
        {'$set': update_data}
    )
    
    return result.modified_count > 0


async def get_staff_assigned_records(
    db,
    staff_id: str,
    collection_name: str,
    product_id: Optional[str] = None,
    include_conflicts: bool = False
) -> List[Dict]:
    """
    Get records assigned to a staff member.
    
    Args:
        db: Database connection
        staff_id: Staff user ID
        collection_name: Records collection name
        product_id: Optional product ID filter
        include_conflicts: Whether to include reservation conflict records
        
    Returns:
        List of assigned records
    """
    query = {
        'assigned_to': staff_id,
        'status': 'assigned'
    }
    
    if product_id:
        query['product_id'] = product_id
    
    if not include_conflicts:
        query['$or'] = [
            {'is_reservation_conflict': {'$exists': False}},
            {'is_reservation_conflict': False},
            {'is_reservation_conflict': None}
        ]
    
    records = await db[collection_name].find(query, {'_id': 0}).to_list(10000)
    return records


async def create_notification(
    db,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = 'info'
) -> str:
    """
    Create a notification for a user.
    
    Args:
        db: Database connection
        user_id: User ID to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, warning, error, success)
        
    Returns:
        Notification ID
    """
    now = get_jakarta_now()
    notification_id = str(uuid.uuid4())
    
    await db.notifications.insert_one({
        'id': notification_id,
        'user_id': user_id,
        'title': title,
        'message': message,
        'type': notification_type,
        'read': False,
        'created_at': now.isoformat()
    })
    
    return notification_id
