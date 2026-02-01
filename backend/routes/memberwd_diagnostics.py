# Diagnostic endpoint for Member WD batch issues

from fastapi import APIRouter, Depends, HTTPException
from .deps import User, get_db, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Member WD Diagnostics"])


@router.get("/memberwd/admin/diagnose-batches")
async def diagnose_memberwd_batches(user: User = Depends(get_admin_user)):
    """
    Diagnose Member WD batch issues:
    - Find records without batch_id
    - Find replacement records with wrong/missing batch_id
    - Find orphaned records (batch doesn't exist)
    - Verify batch record counts match actual records
    """
    db = get_db()
    
    # 1. Count all assigned records
    total_assigned = await db.memberwd_records.count_documents({'status': 'assigned'})
    
    # 2. Count records without batch_id
    records_no_batch = await db.memberwd_records.count_documents({
        'status': 'assigned',
        '$or': [
            {'batch_id': {'$exists': False}},
            {'batch_id': None},
            {'batch_id': ''}
        ]
    })
    
    # 3. Count replacement records
    replacement_records = await db.memberwd_records.find({
        'status': 'assigned',
        'auto_replaced': True
    }, {'_id': 0, 'id': 1, 'batch_id': 1, 'replaced_invalid_ids': 1, 'database_name': 1}).to_list(10000)
    
    replacements_with_batch = sum(1 for r in replacement_records if r.get('batch_id'))
    replacements_without_batch = len(replacement_records) - replacements_with_batch
    
    # 4. Count archived records
    archived_count = await db.memberwd_records.count_documents({'status': 'invalid_archived'})
    
    # 5. Check batches
    batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(1000)
    existing_batch_ids = set(b['id'] for b in batches)
    
    total_initial = sum(b.get('initial_count', 0) for b in batches)
    total_current = sum(b.get('current_count', 0) for b in batches)
    
    # 6. Count records per batch to verify - group by staff and database
    batch_record_counts = []
    batches_by_staff = {}
    
    for batch in batches:
        staff_name = batch.get('staff_name', 'Unknown')
        if staff_name not in batches_by_staff:
            batches_by_staff[staff_name] = []
        
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch['id'],
            'status': 'assigned'
        })
        
        batches_by_staff[staff_name].append({
            'batch_id': batch['id'][:8],
            'database_name': batch.get('database_name', 'Unknown'),
            'created_at': batch.get('created_at', '')[:16] if batch.get('created_at') else '',
            'stored_initial': batch.get('initial_count', 0),
            'stored_current': batch.get('current_count', 0),
            'actual_assigned': actual_count,
            'mismatch': actual_count != batch.get('current_count', 0)
        })
    
    # 7. Find records with invalid batch_id (batch doesn't exist)
    records_with_batch = await db.memberwd_records.find({
        'status': 'assigned',
        'batch_id': {'$exists': True, '$nin': [None, '']}
    }, {'_id': 0, 'id': 1, 'batch_id': 1, 'auto_replaced': 1, 'replaced_invalid_ids': 1, 
        'assigned_to': 1, 'database_id': 1, 'assigned_at': 1, 'database_name': 1}).to_list(100000)
    
    orphaned_records = [r for r in records_with_batch if r.get('batch_id') not in existing_batch_ids]
    orphaned_count = len(orphaned_records)
    
    # 8. DETAILED: Get sample of orphaned records with full tracing
    orphaned_details = []
    for r in orphaned_records[:10]:  # Limit to 10 samples
        detail = {
            'record_id': r['id'][:8],
            'orphan_batch_id': r.get('batch_id', '')[:8] if r.get('batch_id') else 'None',
            'is_replacement': r.get('auto_replaced', False),
            'database_name': r.get('database_name', 'Unknown'),
            'assigned_at': r.get('assigned_at', '')[:19] if r.get('assigned_at') else 'None'
        }
        
        # If replacement, trace back to archived record
        if r.get('replaced_invalid_ids'):
            archived = await db.memberwd_records.find_one(
                {'id': {'$in': r['replaced_invalid_ids']}},
                {'_id': 0, 'id': 1, 'batch_id': 1, 'assigned_at': 1, 'assigned_to': 1, 
                 'database_id': 1, 'database_name': 1}
            )
            if archived:
                detail['archived_record_id'] = archived['id'][:8]
                detail['archived_batch_id'] = archived.get('batch_id', '')[:8] if archived.get('batch_id') else 'None'
                detail['archived_assigned_at'] = archived.get('assigned_at', '')[:19] if archived.get('assigned_at') else 'None'
                detail['archived_database'] = archived.get('database_name', 'Unknown')
                
                # Check if archived batch exists
                if archived.get('batch_id'):
                    detail['archived_batch_exists'] = archived['batch_id'] in existing_batch_ids
                    
                    # If archived batch exists, show its details
                    if detail['archived_batch_exists']:
                        archived_batch = await db.memberwd_batches.find_one(
                            {'id': archived['batch_id']},
                            {'_id': 0, 'database_name': 1, 'staff_name': 1, 'current_count': 1}
                        )
                        if archived_batch:
                            detail['correct_batch_info'] = {
                                'database': archived_batch.get('database_name'),
                                'staff': archived_batch.get('staff_name'),
                                'current_count': archived_batch.get('current_count')
                            }
        
        orphaned_details.append(detail)
    
    # 9. Summary by staff
    staff_summary = {}
    for staff_name, staff_batches in batches_by_staff.items():
        total_stored = sum(b['stored_current'] for b in staff_batches)
        total_actual = sum(b['actual_assigned'] for b in staff_batches)
        staff_summary[staff_name] = {
            'batch_count': len(staff_batches),
            'stored_total': total_stored,
            'actual_total': total_actual,
            'difference': total_stored - total_actual,
            'batches': staff_batches
        }
    
    return {
        'summary': {
            'total_assigned_records': total_assigned,
            'records_without_batch_id': records_no_batch,
            'replacement_records_total': len(replacement_records),
            'replacements_with_batch': replacements_with_batch,
            'replacements_without_batch': replacements_without_batch,
            'archived_records': archived_count,
            'orphaned_records': orphaned_count,
            'total_batches': len(batches),
            'sum_of_initial_counts': total_initial,
            'sum_of_current_counts': total_current
        },
        'orphaned_samples': orphaned_details,
        'staff_batch_summary': staff_summary,
        'expected_total': total_current,
        'actual_total': total_assigned,
        'difference': total_current - total_assigned,
        'health_status': 'HEALTHY' if orphaned_count == 0 and records_no_batch == 0 else 'NEEDS_REPAIR'
    }


@router.post("/memberwd/admin/repair-batches")
async def repair_memberwd_batches(user: User = Depends(get_admin_user)):
    """
    Repair Member WD batch issues - PRECISE VERSION
    
    Key principle: 1 invalid = 1 replacement, replacement MUST go to the SAME batch as invalid.
    
    Strategy:
    1. For orphaned replacement records: Find the archived/invalid record it replaced,
       then find the EXACT batch that archived record belongs to by matching 
       staff_id + database_name + assigned_at timestamp.
    2. Ensure correct product matching (database_name = product source)
    3. Update batch counts to reflect actual records
    """
    db = get_db()
    
    repairs = {
        'orphaned_fixed': 0,
        'replacements_fixed': 0,
        'batch_counts_updated': 0,
        'errors': [],
        'fix_details': []  # Track what was fixed for verification
    }
    
    # Get all existing batches with full details
    batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(10000)
    existing_batch_ids = set(b['id'] for b in batches)
    
    # Build PRECISE lookup: staff_id + database_name + created_at (exact second)
    # This is the unique key for each batch
    batch_lookup_exact = {}  # key: "staff_id|database_name|assigned_at" -> batch_id
    batch_lookup_by_date = {}  # key: "staff_id|database_name|YYYY-MM-DD" -> list of batches
    
    for b in batches:
        staff_id = b.get('staff_id', '')
        db_name = b.get('database_name', '')
        created_at = b.get('created_at', '')
        
        # Exact match key (full timestamp)
        exact_key = f"{staff_id}|{db_name}|{created_at}"
        batch_lookup_exact[exact_key] = b['id']
        
        # Date-only match for fallback (same day batches)
        date_only = created_at[:10] if created_at else ''  # YYYY-MM-DD
        date_key = f"{staff_id}|{db_name}|{date_only}"
        if date_key not in batch_lookup_by_date:
            batch_lookup_by_date[date_key] = []
        batch_lookup_by_date[date_key].append(b)
    
    # STEP 1: Find ALL orphaned records (batch_id points to deleted batch)
    all_assigned = await db.memberwd_records.find({
        'status': 'assigned',
        'batch_id': {'$exists': True, '$nin': [None, '']},
    }, {'_id': 0}).to_list(100000)
    
    orphaned_records = [r for r in all_assigned if r.get('batch_id') not in existing_batch_ids]
    
    for record in orphaned_records:
        fixed = False
        target_batch_id = None
        fix_method = ''
        
        # This is a replacement record - find the original invalid it replaced
        if record.get('auto_replaced') and record.get('replaced_invalid_ids'):
            invalid_ids = record['replaced_invalid_ids']
            
            # Find the archived/invalid record to get its ORIGINAL assignment info
            archived = await db.memberwd_records.find_one(
                {'id': {'$in': invalid_ids}},
                {'_id': 0, 'assigned_at': 1, 'assigned_to': 1, 'database_id': 1, 'database_name': 1, 'batch_id': 1}
            )
            
            if archived:
                staff_id = archived.get('assigned_to', '')
                db_name = archived.get('database_name', '')
                assigned_at = archived.get('assigned_at', '')
                
                # Method 1: Check if archived record's batch_id still exists
                if archived.get('batch_id') and archived['batch_id'] in existing_batch_ids:
                    target_batch_id = archived['batch_id']
                    fix_method = 'archived_batch_exists'
                
                # Method 2: Find batch by EXACT timestamp match
                if not target_batch_id and assigned_at:
                    exact_key = f"{staff_id}|{db_name}|{assigned_at}"
                    if exact_key in batch_lookup_exact:
                        target_batch_id = batch_lookup_exact[exact_key]
                        fix_method = 'exact_timestamp_match'
                
                # Method 3: Find batch created on the SAME DAY for same staff+database
                # Pick the one with the closest timestamp
                if not target_batch_id and assigned_at:
                    date_only = assigned_at[:10]  # YYYY-MM-DD
                    date_key = f"{staff_id}|{db_name}|{date_only}"
                    
                    if date_key in batch_lookup_by_date:
                        # Find the batch with the closest created_at to the record's assigned_at
                        candidates = batch_lookup_by_date[date_key]
                        best_match = None
                        best_diff = float('inf')
                        
                        for candidate in candidates:
                            candidate_time = candidate.get('created_at', '')
                            if candidate_time and assigned_at:
                                # Compare timestamps (simple string comparison works for ISO format)
                                # We want the batch created AT or BEFORE the record was assigned
                                if candidate_time <= assigned_at:
                                    # Pick the one closest to the assignment time
                                    diff = len(assigned_at) - len(candidate_time)  # Simple heuristic
                                    if best_match is None or candidate_time > best_match.get('created_at', ''):
                                        best_match = candidate
                        
                        if best_match:
                            target_batch_id = best_match['id']
                            fix_method = 'same_day_closest_match'
                
                # Method 4: Last resort - find ANY batch with same staff+database
                # This should rarely happen if data is consistent
                if not target_batch_id:
                    for b in batches:
                        if b.get('staff_id') == staff_id and b.get('database_name') == db_name:
                            target_batch_id = b['id']
                            fix_method = 'same_staff_database_fallback'
                            break
        
        # For non-replacement orphans (shouldn't happen often), use the record's own info
        if not target_batch_id and not record.get('auto_replaced'):
            staff_id = record.get('assigned_to', '')
            db_name = record.get('database_name', '')
            assigned_at = record.get('assigned_at', '')
            
            # Try exact match first
            if assigned_at:
                exact_key = f"{staff_id}|{db_name}|{assigned_at}"
                if exact_key in batch_lookup_exact:
                    target_batch_id = batch_lookup_exact[exact_key]
                    fix_method = 'non_replacement_exact_match'
            
            # Then same-day match
            if not target_batch_id and assigned_at:
                date_only = assigned_at[:10]
                date_key = f"{staff_id}|{db_name}|{date_only}"
                if date_key in batch_lookup_by_date:
                    target_batch_id = batch_lookup_by_date[date_key][0]['id']
                    fix_method = 'non_replacement_same_day'
        
        # Apply the fix
        if target_batch_id:
            await db.memberwd_records.update_one(
                {'id': record['id']},
                {'$set': {'batch_id': target_batch_id}}
            )
            repairs['orphaned_fixed'] += 1
            repairs['fix_details'].append({
                'record_id': record['id'][:8],
                'target_batch': target_batch_id[:8],
                'method': fix_method,
                'database': record.get('database_name', 'Unknown')
            })
        else:
            repairs['errors'].append(
                f"Could not find batch for record {record['id'][:8]}, "
                f"db: {record.get('database_name', 'Unknown')}, "
                f"is_replacement: {record.get('auto_replaced', False)}"
            )
    
    # STEP 2: Fix replacement records WITHOUT batch_id
    replacement_no_batch = await db.memberwd_records.find({
        'status': 'assigned',
        'auto_replaced': True,
        '$or': [
            {'batch_id': {'$exists': False}},
            {'batch_id': None},
            {'batch_id': ''}
        ]
    }, {'_id': 0}).to_list(10000)
    
    for record in replacement_no_batch:
        invalid_ids = record.get('replaced_invalid_ids', [])
        if not invalid_ids:
            repairs['errors'].append(f"Replacement {record['id'][:8]} has no replaced_invalid_ids")
            continue
        
        # Find the archived/invalid record
        invalid_record = await db.memberwd_records.find_one(
            {'id': {'$in': invalid_ids}},
            {'_id': 0, 'batch_id': 1, 'database_name': 1, 'assigned_to': 1, 'assigned_at': 1}
        )
        
        if not invalid_record:
            repairs['errors'].append(f"Could not find archived record for replacement {record['id'][:8]}")
            continue
        
        target_batch_id = None
        fix_method = ''
        
        # Method 1: Use invalid record's batch_id if it exists
        if invalid_record.get('batch_id') and invalid_record['batch_id'] in existing_batch_ids:
            target_batch_id = invalid_record['batch_id']
            fix_method = 'invalid_batch_exists'
        
        # Method 2: Find by timestamp
        if not target_batch_id:
            staff_id = invalid_record.get('assigned_to', '')
            db_name = invalid_record.get('database_name', '')
            assigned_at = invalid_record.get('assigned_at', '')
            
            if assigned_at:
                exact_key = f"{staff_id}|{db_name}|{assigned_at}"
                if exact_key in batch_lookup_exact:
                    target_batch_id = batch_lookup_exact[exact_key]
                    fix_method = 'invalid_timestamp_match'
            
            # Same-day fallback
            if not target_batch_id and assigned_at:
                date_only = assigned_at[:10]
                date_key = f"{staff_id}|{db_name}|{date_only}"
                if date_key in batch_lookup_by_date:
                    # Find closest batch
                    for candidate in batch_lookup_by_date[date_key]:
                        if candidate.get('created_at', '') <= assigned_at:
                            target_batch_id = candidate['id']
                            fix_method = 'invalid_same_day_match'
                            break
        
        if target_batch_id:
            await db.memberwd_records.update_one(
                {'id': record['id']},
                {'$set': {'batch_id': target_batch_id}}
            )
            repairs['replacements_fixed'] += 1
            repairs['fix_details'].append({
                'record_id': record['id'][:8],
                'target_batch': target_batch_id[:8],
                'method': fix_method,
                'database': record.get('database_name', 'Unknown'),
                'type': 'no_batch_replacement'
            })
        else:
            repairs['errors'].append(f"Could not find batch for replacement {record['id'][:8]}")
    
    # STEP 3: Update batch counts to match ACTUAL records
    all_batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(1000)
    
    count_updates = []
    for batch in all_batches:
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch['id'],
            'status': 'assigned'
        })
        
        stored_count = batch.get('current_count', 0)
        if actual_count != stored_count:
            await db.memberwd_batches.update_one(
                {'id': batch['id']},
                {'$set': {'current_count': actual_count}}
            )
            repairs['batch_counts_updated'] += 1
            count_updates.append({
                'batch_id': batch['id'][:8],
                'database': batch.get('database_name', 'Unknown'),
                'old_count': stored_count,
                'new_count': actual_count
            })
    
    return {
        'success': True,
        'message': f"Fixed {repairs['orphaned_fixed']} orphaned records, {repairs['replacements_fixed']} replacements, updated {repairs['batch_counts_updated']} batch counts",
        'details': repairs,
        'count_updates': count_updates[:20]  # Limit output
    }
