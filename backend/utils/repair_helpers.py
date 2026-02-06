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


async def check_batch_health(db) -> Dict[str, Any]:
    """
    Check health of memberwd batch counts vs actual record counts.
    
    Returns:
        Dict with batch health details
    """
    batch_report = {
        'batches': [],
        'batch_mismatches': 0
    }
    
    all_batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(10000)
    
    for batch in all_batches:
        batch_id = batch.get('id')
        stored_count = batch.get('current_count', 0)
        
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch_id,
            'status': 'assigned'
        })
        
        has_mismatch = stored_count != actual_count
        if has_mismatch:
            batch_report['batch_mismatches'] += 1
        
        batch_report['batches'].append({
            'batch_id': batch_id[:8] + '...',
            'staff_name': batch.get('staff_name', 'Unknown'),
            'product_name': batch.get('product_name', 'Unknown'),
            'stored_count': stored_count,
            'actual_count': actual_count,
            'has_mismatch': has_mismatch,
            'difference': actual_count - stored_count
        })
    
    return batch_report


async def diagnose_product_mismatch(db, module: str = 'records') -> Dict[str, Any]:
    """
    Preview what product mismatch repair would fix WITHOUT making changes.
    Works for bonanza and memberwd modules.
    
    Args:
        db: Database connection
        module: Module type ('bonanza' or 'memberwd')
        
    Returns:
        Diagnosis report
    """
    collections = get_collection_names(module)
    
    diagnosis = {
        'total_mismatched': 0,
        'by_database': [],
        'would_move': [],
        'cannot_fix': []
    }
    
    databases = await db[collections['databases']].find({}, {'_id': 0}).to_list(1000)
    db_by_product = {}
    
    for database in databases:
        product_id = database.get('product_id')
        if product_id:
            if product_id not in db_by_product:
                db_by_product[product_id] = []
            db_by_product[product_id].append(database)
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        db_product_id = database.get('product_id')
        
        if not db_product_id:
            diagnosis['cannot_fix'].append({
                'database': db_name,
                'reason': 'Database has no product_id set'
            })
            continue
        
        mismatched_records = await db[collections['records']].find({
            'database_id': db_id,
            'product_id': {'$exists': True, '$ne': db_product_id}
        }, {'_id': 0, 'id': 1, 'product_id': 1, 'status': 1, 'assigned_to_name': 1}).to_list(100000)
        
        if mismatched_records:
            by_product = {}
            for record in mismatched_records:
                rec_product = record.get('product_id', 'UNKNOWN')
                if rec_product not in by_product:
                    by_product[rec_product] = {'count': 0, 'assigned': 0, 'available': 0}
                by_product[rec_product]['count'] += 1
                if record.get('status') == 'assigned':
                    by_product[rec_product]['assigned'] += 1
                else:
                    by_product[rec_product]['available'] += 1
            
            for rec_product, stats in by_product.items():
                target_databases = db_by_product.get(rec_product, [])
                if target_databases:
                    diagnosis['would_move'].append({
                        'from_database': db_name,
                        'to_database': target_databases[0]['name'],
                        'product_id': rec_product,
                        'count': stats['count'],
                        'assigned_count': stats['assigned'],
                        'available_count': stats['available']
                    })
                else:
                    diagnosis['cannot_fix'].append({
                        'database': db_name,
                        'product_id': rec_product,
                        'count': stats['count'],
                        'reason': f'No database exists for product {rec_product}'
                    })
            
            diagnosis['by_database'].append({
                'database_name': db_name,
                'expected_product': db_product_id,
                'mismatched_count': len(mismatched_records),
                'breakdown': by_product
            })
            
            diagnosis['total_mismatched'] += len(mismatched_records)
    
    # Current stats
    current_stats = []
    for database in databases:
        db_id = database['id']
        available = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        
        current_stats.append({
            'database_name': database['name'],
            'product_id': database.get('product_id'),
            'available': available,
            'assigned': assigned,
            'archived': archived,
            'total': available + assigned + archived
        })
    
    diagnosis['current_stats'] = current_stats
    return diagnosis


async def repair_product_mismatch(db, module: str = 'records') -> Dict[str, Any]:
    """
    Find and fix records where product_id doesn't match the database's product_id.
    Works for bonanza and memberwd modules.
    
    Args:
        db: Database connection
        module: Module type ('bonanza' or 'memberwd')
        
    Returns:
        Repair result
    """
    collections = get_collection_names(module)
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
    
    databases = await db[collections['databases']].find({}, {'_id': 0}).to_list(1000)
    db_by_product = {}
    
    for database in databases:
        product_id = database.get('product_id')
        if product_id:
            if product_id not in db_by_product:
                db_by_product[product_id] = []
            db_by_product[product_id].append(database)
    
    for database in databases:
        db_id = database['id']
        db_name = database['name']
        db_product_id = database.get('product_id')
        
        if not db_product_id:
            repair_log['errors'].append(f"Database '{db_name}' has no product_id set")
            continue
        
        mismatched_records = await db[collections['records']].find({
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
            by_product = {}
            for record in mismatched_records:
                rec_product = record.get('product_id', 'UNKNOWN')
                if rec_product not in by_product:
                    by_product[rec_product] = []
                by_product[rec_product].append(record)
            
            for rec_product, records in by_product.items():
                target_databases = db_by_product.get(rec_product, [])
                
                if not target_databases:
                    repair_log['errors'].append(
                        f"No database found for product '{rec_product}' - {len(records)} records cannot be moved"
                    )
                    db_stats['no_target_count'] += len(records)
                    repair_log['total_no_target_db'] += len(records)
                    continue
                
                target_db = target_databases[0]
                record_ids = [r['id'] for r in records]
                
                result = await db[collections['records']].update_many(
                    {'id': {'$in': record_ids}},
                    {'$set': {
                        'database_id': target_db['id'],
                        'database_name': target_db['name'],
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
                    'to_database': target_db['name'],
                    'product_id': rec_product,
                    'count': result.modified_count
                })
        
        repair_log['by_database'].append(db_stats)
        repair_log['total_mismatched'] += db_stats['mismatched_count']
    
    # Recount all databases for updated stats
    updated_stats = []
    for database in databases:
        db_id = database['id']
        available = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'available'})
        assigned = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'assigned'})
        archived = await db[collections['records']].count_documents({'database_id': db_id, 'status': 'invalid_archived'})
        total = await db[collections['records']].count_documents({'database_id': db_id})
        
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


async def _build_reserved_map(db) -> Dict[str, Dict]:
    """Build a map of normalized customer IDs to their reservation info."""
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1, 'staff_id': 1, 'staff_name': 1}
    ).to_list(100000)
    
    reserved_map = {}
    for m in reserved_members:
        cid = m.get('customer_id') or m.get('customer_name')
        if cid:
            normalized = str(cid).strip().upper()
            reserved_map[normalized] = {
                'staff_id': m.get('staff_id'),
                'staff_name': m.get('staff_name', 'Unknown')
            }
    return reserved_map


def _find_customer_id_in_row(row_data: Dict) -> Optional[str]:
    """Extract customer ID from row_data by checking common username fields."""
    for key in USERNAME_FIELDS:
        if key in row_data and row_data[key]:
            return str(row_data[key]).strip()
    return None


async def diagnose_reserved_conflicts(db, module: str = 'records') -> Dict[str, Any]:
    """
    Find records assigned to staff A but reserved by staff B.
    Works for bonanza and memberwd modules.
    
    Args:
        db: Database connection
        module: Module type ('bonanza' or 'memberwd')
        
    Returns:
        Conflict diagnosis report
    """
    collections = get_collection_names(module)
    reserved_map = await _build_reserved_map(db)
    
    assigned_records = await db[collections['records']].find(
        {'status': 'assigned'},
        {'_id': 0, 'id': 1, 'row_data': 1, 'assigned_to': 1, 'assigned_to_name': 1, 'database_name': 1}
    ).to_list(100000)
    
    conflicts = []
    for record in assigned_records:
        row_data = record.get('row_data', {})
        assigned_to = record.get('assigned_to')
        
        customer_id = _find_customer_id_in_row(row_data)
        if customer_id and customer_id.upper() in reserved_map:
            reserved_info = reserved_map[customer_id.upper()]
            if reserved_info['staff_id'] != assigned_to:
                conflicts.append({
                    'record_id': record['id'],
                    'customer_id': customer_id,
                    'database_name': record.get('database_name', 'Unknown'),
                    'assigned_to': record.get('assigned_to_name', 'Unknown'),
                    'assigned_to_id': assigned_to,
                    'reserved_by': reserved_info['staff_name'],
                    'reserved_by_id': reserved_info['staff_id']
                })
    
    return {
        'total_conflicts': len(conflicts),
        'conflicts': conflicts,
        'message': f'Found {len(conflicts)} records assigned to wrong staff (should be assigned to who reserved them)'
    }


async def fix_reserved_conflicts(db, module: str = 'records') -> Dict[str, Any]:
    """
    Fix records assigned to staff A but reserved by staff B by reassigning.
    Works for bonanza and memberwd modules.
    
    Args:
        db: Database connection
        module: Module type ('bonanza' or 'memberwd')
        
    Returns:
        Fix result
    """
    collections = get_collection_names(module)
    now = get_jakarta_now()
    reserved_map = await _build_reserved_map(db)
    
    assigned_records = await db[collections['records']].find(
        {'status': 'assigned'},
        {'_id': 0, 'id': 1, 'row_data': 1, 'assigned_to': 1, 'assigned_to_name': 1, 'batch_id': 1}
    ).to_list(100000)
    
    fixed = []
    for record in assigned_records:
        row_data = record.get('row_data', {})
        assigned_to = record.get('assigned_to')
        
        customer_id = _find_customer_id_in_row(row_data)
        if customer_id and customer_id.upper() in reserved_map:
            reserved_info = reserved_map[customer_id.upper()]
            if reserved_info['staff_id'] != assigned_to:
                await db[collections['records']].update_one(
                    {'id': record['id']},
                    {'$set': {
                        'assigned_to': reserved_info['staff_id'],
                        'assigned_to_name': reserved_info['staff_name'],
                        'reassigned_at': now.isoformat(),
                        'reassigned_reason': 'reserved_conflict_fix',
                        'previous_assigned_to': assigned_to,
                        'previous_assigned_to_name': record.get('assigned_to_name')
                    }}
                )
                fixed.append({
                    'record_id': record['id'],
                    'customer_id': customer_id,
                    'from_staff': record.get('assigned_to_name'),
                    'to_staff': reserved_info['staff_name']
                })
    
    return {
        'success': True,
        'total_fixed': len(fixed),
        'fixed_records': fixed,
        'message': f'Reassigned {len(fixed)} records to their correct staff (who reserved them)'
    }
