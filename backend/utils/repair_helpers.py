"""
Data Repair and Health Check Helper Functions
Common validation and repair operations for all record modules
"""

from typing import Dict, Any, List, Optional
from utils.helpers import get_jakarta_now
from utils.db_operations import get_collection_names, count_records_by_status

# Common username fields used across all modules for customer ID lookup
USERNAME_FIELDS = [
    'Username', 'username', 'USER', 'user', 'ID', 'id',
    'Nama Lengkap', 'nama_lengkap', 'Name', 'name',
    'CUSTOMER', 'customer', 'Customer', 'NAMA'
]


async def check_database_health(
    db,
    database_id: str,
    database_name: str,
    module: str = 'records'
) -> Dict[str, Any]:
    """
    Check health of a single database.
    
    Args:
        db: Database connection
        database_id: Database ID
        database_name: Database name
        module: Module type ('records', 'bonanza', 'memberwd')
        
    Returns:
        Health report dict
    """
    collections = get_collection_names(module)
    records_collection = collections['records']
    
    # Count records by status
    counts = await count_records_by_status(db, database_id, records_collection)
    
    # Check for issues
    missing_db_name = await db[records_collection].count_documents({
        'database_id': database_id, 
        '$or': [{'database_name': {'$exists': False}}, {'database_name': None}]
    })
    
    orphaned_assignments = await db[records_collection].count_documents({
        'database_id': database_id, 
        'status': 'assigned', 
        'assigned_to': None
    })
    
    # Count invalid status (old bug)
    invalid_status_count = await db[records_collection].count_documents({
        'database_id': database_id, 
        'status': 'invalid'
    })
    
    # Count other invalid status values
    valid_statuses = ['available', 'assigned', 'invalid_archived', 'invalid']
    other_invalid_status = await db[records_collection].count_documents({
        'database_id': database_id, 
        'status': {'$nin': valid_statuses}
    })
    
    total_issues = missing_db_name + orphaned_assignments + invalid_status_count + other_invalid_status
    
    return {
        'database_id': database_id,
        'database_name': database_name,
        'total_records': counts['total'],
        'available': counts['available'],
        'assigned': counts['assigned'],
        'archived': counts['archived'],
        'invalid_status_records': invalid_status_count,
        'sum_matches': counts['total'] == (counts['available'] + counts['assigned'] + counts['archived'] + invalid_status_count),
        'issues': {
            'missing_db_name': missing_db_name,
            'orphaned_assignments': orphaned_assignments,
            'invalid_status': invalid_status_count,
            'other_invalid_status': other_invalid_status
        },
        'has_issues': total_issues > 0,
        'total_issues': total_issues
    }


async def repair_database_records(
    db,
    database_id: str,
    database_name: str,
    product_name: str,
    module: str = 'records'
) -> Dict[str, int]:
    """
    Repair records in a single database.
    
    Args:
        db: Database connection
        database_id: Database ID
        database_name: Database name
        product_name: Product name for the database
        module: Module type
        
    Returns:
        Dict with repair counts
    """
    collections = get_collection_names(module)
    records_collection = collections['records']
    
    repairs = {
        'fixed_missing_db_info': 0,
        'fixed_invalid_status_restored': 0,
        'fixed_invalid_status_cleared': 0,
        'fixed_orphaned_assignments': 0
    }
    
    # Fix records with missing database_name
    result = await db[records_collection].update_many(
        {'database_id': database_id, 'database_name': {'$exists': False}},
        {'$set': {'database_name': database_name, 'product_name': product_name}}
    )
    repairs['fixed_missing_db_info'] += result.modified_count
    
    # Fix records with None database_name
    result = await db[records_collection].update_many(
        {'database_id': database_id, 'database_name': None},
        {'$set': {'database_name': database_name, 'product_name': product_name}}
    )
    repairs['fixed_missing_db_info'] += result.modified_count
    
    # Fix records with status='invalid' that have assignment info
    # Restore them to 'assigned' with is_reservation_conflict flag
    invalid_with_assignment = await db[records_collection].find({
        'database_id': database_id,
        'status': 'invalid',
        'assigned_to': {'$exists': True, '$ne': None}
    }, {'_id': 0, 'id': 1}).to_list(10000)
    
    for record in invalid_with_assignment:
        await db[records_collection].update_one(
            {'id': record['id']},
            {'$set': {
                'status': 'assigned',
                'is_reservation_conflict': True
            }}
        )
        repairs['fixed_invalid_status_restored'] += 1
    
    # Fix remaining 'invalid' status records without proper assignment
    result = await db[records_collection].update_many(
        {
            'database_id': database_id,
            'status': 'invalid',
            '$or': [
                {'assigned_to': {'$exists': False}},
                {'assigned_to': None}
            ]
        },
        {'$set': {'status': 'available'}}
    )
    repairs['fixed_invalid_status_cleared'] += result.modified_count
    
    # Fix other invalid status values
    valid_statuses = ['available', 'assigned', 'invalid_archived', 'invalid']
    result = await db[records_collection].update_many(
        {'database_id': database_id, 'status': {'$nin': valid_statuses}},
        {'$set': {'status': 'available'}}
    )
    repairs['fixed_invalid_status_cleared'] += result.modified_count
    
    # Fix orphaned assignments (status=assigned but no assigned_to)
    result = await db[records_collection].update_many(
        {'database_id': database_id, 'status': 'assigned', 'assigned_to': None},
        {'$set': {
            'status': 'available',
            'assigned_to': None,
            'assigned_to_name': None,
            'assigned_at': None
        }}
    )
    repairs['fixed_orphaned_assignments'] += result.modified_count
    
    return repairs


async def run_full_health_check(
    db,
    module: str = 'records'
) -> Dict[str, Any]:
    """
    Run full health check on all databases in a module.
    
    Args:
        db: Database connection
        module: Module type
        
    Returns:
        Full health report
    """
    collections = get_collection_names(module)
    
    health_report = {
        'databases': [],
        'total_issues': 0,
        'issues': []
    }
    
    databases = await db[collections['databases']].find({}, {'_id': 0}).to_list(1000)
    
    for database in databases:
        db_health = await check_database_health(
            db, 
            database['id'], 
            database['name'],
            module
        )
        
        health_report['databases'].append(db_health)
        health_report['total_issues'] += db_health['total_issues']
        
        if db_health['has_issues']:
            for issue_type, count in db_health['issues'].items():
                if count > 0:
                    health_report['issues'].append(
                        f"{database['name']}: {count} {issue_type.replace('_', ' ')}"
                    )
    
    health_report['is_healthy'] = health_report['total_issues'] == 0
    
    return health_report


async def run_full_repair(
    db,
    module: str = 'records'
) -> Dict[str, Any]:
    """
    Run full repair on all databases in a module.
    
    Args:
        db: Database connection
        module: Module type
        
    Returns:
        Full repair report
    """
    collections = get_collection_names(module)
    now = get_jakarta_now()
    
    repair_log = {
        'timestamp': now.isoformat(),
        'fixed_missing_db_info': 0,
        'fixed_invalid_status_restored': 0,
        'fixed_invalid_status_cleared': 0,
        'fixed_orphaned_assignments': 0,
        'databases_checked': [],
        'errors': []
    }
    
    databases = await db[collections['databases']].find({}, {'_id': 0}).to_list(1000)
    
    for database in databases:
        try:
            repairs = await repair_database_records(
                db,
                database['id'],
                database['name'],
                database.get('product_name', 'Unknown'),
                module
            )
            
            # Accumulate totals
            for key in repairs:
                if key in repair_log:
                    repair_log[key] += repairs[key]
            
            # Get updated counts
            counts = await count_records_by_status(db, database['id'], collections['records'])
            
            repair_log['databases_checked'].append({
                'database_id': database['id'],
                'database_name': database['name'],
                'total_records': counts['total'],
                'available': counts['available'],
                'assigned': counts['assigned'],
                'archived': counts['archived'],
                'is_consistent': counts['total'] == (counts['available'] + counts['assigned'] + counts['archived'])
            })
            
        except Exception as e:
            repair_log['errors'].append(f"{database['name']}: {str(e)}")
    
    total_fixed = (
        repair_log['fixed_missing_db_info'] + 
        repair_log['fixed_invalid_status_restored'] + 
        repair_log['fixed_invalid_status_cleared'] +
        repair_log['fixed_orphaned_assignments']
    )
    
    return {
        'success': True,
        'message': f'Data repair completed. Fixed {total_fixed} issues.',
        'repair_log': repair_log
    }


async def sync_batch_counts(db) -> Dict[str, Any]:
    """
    Synchronize batch counts with actual record counts (MemberWD specific).
    
    Args:
        db: Database connection
        
    Returns:
        Sync report
    """
    sync_report = {
        'fixed_batch_counts': 0,
        'batches_synchronized': []
    }
    
    batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(10000)
    
    for batch in batches:
        batch_id = batch.get('id')
        stored_count = batch.get('current_count', 0)
        
        # Count actual assigned records in this batch
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch_id,
            'status': 'assigned'
        })
        
        if stored_count != actual_count:
            await db.memberwd_batches.update_one(
                {'id': batch_id},
                {'$set': {'current_count': actual_count}}
            )
            sync_report['fixed_batch_counts'] += 1
            sync_report['batches_synchronized'].append({
                'batch_id': batch_id[:8] + '...',
                'staff_name': batch.get('staff_name', 'Unknown'),
                'stored_count': stored_count,
                'actual_count': actual_count,
                'difference': actual_count - stored_count
            })
    
    # Delete empty batches
    deleted = await db.memberwd_batches.delete_many({'current_count': {'$lte': 0}})
    if deleted.deleted_count > 0:
        sync_report['empty_batches_deleted'] = deleted.deleted_count
    
    return sync_report
