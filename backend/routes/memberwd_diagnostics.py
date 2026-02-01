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
    - Find orphaned records
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
    }, {'_id': 0, 'id': 1, 'batch_id': 1, 'replaced_invalid_ids': 1}).to_list(10000)
    
    replacements_with_batch = sum(1 for r in replacement_records if r.get('batch_id'))
    replacements_without_batch = len(replacement_records) - replacements_with_batch
    
    # 4. Count archived records
    archived_count = await db.memberwd_records.count_documents({'status': 'invalid_archived'})
    
    # 5. Check batches
    batches = await db.memberwd_batches.find({}, {'_id': 0, 'id': 1, 'initial_count': 1, 'current_count': 1}).to_list(1000)
    existing_batch_ids = set(b['id'] for b in batches)
    
    total_initial = sum(b.get('initial_count', 0) for b in batches)
    total_current = sum(b.get('current_count', 0) for b in batches)
    
    # 6. Count records per batch to verify
    batch_record_counts = []
    for batch in batches[:20]:  # Limit to first 20
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch['id'],
            'status': 'assigned'
        })
        batch_record_counts.append({
            'batch_id': batch['id'][:8],
            'stored_initial': batch.get('initial_count', 0),
            'stored_current': batch.get('current_count', 0),
            'actual_assigned': actual_count
        })
    
    # 7. Find records with invalid batch_id (batch doesn't exist)
    records_with_batch = await db.memberwd_records.find({
        'status': 'assigned',
        'batch_id': {'$exists': True, '$nin': [None, '']}
    }, {'_id': 0, 'id': 1, 'batch_id': 1}).to_list(100000)
    
    orphaned_records = sum(1 for r in records_with_batch if r.get('batch_id') not in existing_batch_ids)
    
    # 8. DETAILED: Get sample of orphaned records to understand the issue
    orphaned_details = []
    for r in records_with_batch:
        if r.get('batch_id') not in existing_batch_ids:
            # Get full record details
            full_record = await db.memberwd_records.find_one(
                {'id': r['id']},
                {'_id': 0, 'id': 1, 'batch_id': 1, 'auto_replaced': 1, 'replaced_invalid_ids': 1, 
                 'assigned_to': 1, 'database_id': 1, 'assigned_at': 1, 'database_name': 1}
            )
            if full_record and len(orphaned_details) < 5:  # Limit to 5 samples
                detail = {
                    'record_id': full_record['id'][:8],
                    'orphan_batch_id': full_record.get('batch_id', '')[:8] if full_record.get('batch_id') else 'None',
                    'is_replacement': full_record.get('auto_replaced', False),
                    'database_name': full_record.get('database_name', 'Unknown'),
                    'assigned_at': full_record.get('assigned_at', '')[:19] if full_record.get('assigned_at') else 'None'
                }
                
                # If replacement, check the archived record
                if full_record.get('replaced_invalid_ids'):
                    archived = await db.memberwd_records.find_one(
                        {'id': {'$in': full_record['replaced_invalid_ids']}},
                        {'_id': 0, 'id': 1, 'batch_id': 1, 'assigned_at': 1, 'assigned_to': 1, 'database_id': 1}
                    )
                    if archived:
                        detail['archived_record_id'] = archived['id'][:8]
                        detail['archived_batch_id'] = archived.get('batch_id', '')[:8] if archived.get('batch_id') else 'None'
                        detail['archived_assigned_at'] = archived.get('assigned_at', '')[:19] if archived.get('assigned_at') else 'None'
                        
                        # Check if archived batch exists
                        if archived.get('batch_id'):
                            detail['archived_batch_exists'] = archived['batch_id'] in existing_batch_ids
                
                orphaned_details.append(detail)
    
    return {
        'summary': {
            'total_assigned_records': total_assigned,
            'records_without_batch_id': records_no_batch,
            'replacement_records_total': len(replacement_records),
            'replacements_with_batch': replacements_with_batch,
            'replacements_without_batch': replacements_without_batch,
            'archived_records': archived_count,
            'orphaned_records': orphaned_records,
            'total_batches': len(batches),
            'sum_of_initial_counts': total_initial,
            'sum_of_current_counts': total_current
        },
        'orphaned_samples': orphaned_details,
        'batch_verification': batch_record_counts,
        'expected_total': total_initial,
        'actual_total': total_assigned,
        'difference': total_initial - total_assigned
    }


@router.post("/memberwd/admin/repair-batches")
async def repair_memberwd_batches(user: User = Depends(get_admin_user)):
    """
    Repair Member WD batch issues:
    1. Find orphaned records (batch_id points to non-existent batch) and reassign them
    2. Find replacement records without batch_id and assign them to correct batch
    3. Update batch counts to match actual record counts
    """
    db = get_db()
    
    repairs = {
        'orphaned_fixed': 0,
        'replacements_fixed': 0,
        'batch_counts_updated': 0,
        'errors': []
    }
    
    # Get all existing batch IDs
    batches = await db.memberwd_batches.find({}, {'_id': 0, 'id': 1}).to_list(10000)
    existing_batch_ids = set(b['id'] for b in batches)
    
    # 1. Fix ORPHANED records (have batch_id but batch doesn't exist)
    orphaned_records = await db.memberwd_records.find({
        'status': 'assigned',
        'batch_id': {'$exists': True, '$nin': [None, '']},
    }, {'_id': 0}).to_list(100000)
    
    for record in orphaned_records:
        if record.get('batch_id') not in existing_batch_ids:
            # This record points to a deleted batch - need to find correct batch
            
            # If it's a replacement record, find the batch from archived invalid records
            if record.get('auto_replaced') and record.get('replaced_invalid_ids'):
                invalid_ids = record['replaced_invalid_ids']
                # Find archived record to get its original assignment info
                archived = await db.memberwd_records.find_one(
                    {'id': {'$in': invalid_ids}},
                    {'_id': 0, 'assigned_at': 1, 'assigned_to': 1, 'database_id': 1, 'batch_id': 1}
                )
                
                if archived:
                    # Try to find batch by the archived record's batch_id first
                    if archived.get('batch_id') and archived['batch_id'] in existing_batch_ids:
                        await db.memberwd_records.update_one(
                            {'id': record['id']},
                            {'$set': {'batch_id': archived['batch_id']}}
                        )
                        repairs['orphaned_fixed'] += 1
                        continue
                    
                    # Otherwise find batch by matching timestamp
                    matching_batch = await db.memberwd_batches.find_one({
                        'staff_id': archived.get('assigned_to'),
                        'database_id': archived.get('database_id'),
                        'created_at': archived.get('assigned_at')
                    }, {'_id': 0, 'id': 1})
                    
                    if matching_batch:
                        await db.memberwd_records.update_one(
                            {'id': record['id']},
                            {'$set': {'batch_id': matching_batch['id']}}
                        )
                        repairs['orphaned_fixed'] += 1
                    else:
                        repairs['errors'].append(f"Could not find batch for orphaned replacement {record['id'][:8]}")
            else:
                # Non-replacement orphaned record - try to find batch by timestamp
                matching_batch = await db.memberwd_batches.find_one({
                    'staff_id': record.get('assigned_to'),
                    'database_id': record.get('database_id'),
                    'created_at': record.get('assigned_at')
                }, {'_id': 0, 'id': 1})
                
                if matching_batch:
                    await db.memberwd_records.update_one(
                        {'id': record['id']},
                        {'$set': {'batch_id': matching_batch['id']}}
                    )
                    repairs['orphaned_fixed'] += 1
                else:
                    repairs['errors'].append(f"Could not find batch for orphaned record {record['id'][:8]}")
    
    # 2. Fix replacement records without batch_id
    replacement_records = await db.memberwd_records.find({
        'status': 'assigned',
        'auto_replaced': True,
        '$or': [
            {'batch_id': {'$exists': False}},
            {'batch_id': None},
            {'batch_id': ''}
        ]
    }, {'_id': 0}).to_list(10000)
    
    for record in replacement_records:
        invalid_ids = record.get('replaced_invalid_ids', [])
        if not invalid_ids:
            repairs['errors'].append(f"Record {record['id'][:8]} has no replaced_invalid_ids")
            continue
        
        # Find the invalid record to get its batch_id
        invalid_record = await db.memberwd_records.find_one(
            {'id': {'$in': invalid_ids}},
            {'_id': 0, 'batch_id': 1}
        )
        
        if invalid_record and invalid_record.get('batch_id'):
            if invalid_record['batch_id'] in existing_batch_ids:
                await db.memberwd_records.update_one(
                    {'id': record['id']},
                    {'$set': {'batch_id': invalid_record['batch_id']}}
                )
                repairs['replacements_fixed'] += 1
            else:
                repairs['errors'].append(f"Invalid record's batch {invalid_record['batch_id'][:8]} doesn't exist")
        else:
            repairs['errors'].append(f"Could not find batch for replacement {record['id'][:8]}")
    
    # 3. Update batch counts to match actual records
    all_batches = await db.memberwd_batches.find({}, {'_id': 0}).to_list(1000)
    
    for batch in all_batches:
        actual_count = await db.memberwd_records.count_documents({
            'batch_id': batch['id'],
            'status': 'assigned'
        })
        
        if actual_count != batch.get('current_count', 0):
            await db.memberwd_batches.update_one(
                {'id': batch['id']},
                {'$set': {'current_count': actual_count}}
            )
            repairs['batch_counts_updated'] += 1
    
    return {
        'success': True,
        'message': f"Fixed {repairs['orphaned_fixed']} orphaned records, {repairs['replacements_fixed']} replacements, updated {repairs['batch_counts_updated']} batch counts",
        'details': repairs
    }
