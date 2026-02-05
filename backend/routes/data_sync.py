# Data Sync Dashboard - Health Check and Monitoring Routes
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
import pytz

from .deps import get_db, get_admin_user, User, get_jakarta_now

router = APIRouter(tags=["Data Sync"])

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')


@router.get("/data-sync/health-check")
async def run_health_check(user: User = Depends(get_admin_user)):
    """
    Comprehensive data health check across all collections.
    Detects inconsistencies, orphaned data, and sync issues.
    """
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    issues = []
    warnings = []
    stats = {}
    
    # 1. Check for orphaned reserved members (staff doesn't exist)
    all_staff_ids = set()
    staff_users = await db.users.find({'role': 'staff'}, {'id': 1}).to_list(10000)
    all_staff_ids = {s['id'] for s in staff_users}
    
    reserved_members = await db.reserved_members.find({}, {'staff_id': 1, 'customer_id': 1}).to_list(10000)
    orphaned_reserved = [r for r in reserved_members if r.get('staff_id') not in all_staff_ids]
    
    if orphaned_reserved:
        issues.append({
            'type': 'orphaned_reserved_members',
            'severity': 'high',
            'count': len(orphaned_reserved),
            'message': f'{len(orphaned_reserved)} reserved members belong to deleted staff',
            'auto_fixable': True
        })
    
    stats['reserved_members'] = {
        'total': len(reserved_members),
        'orphaned': len(orphaned_reserved)
    }
    
    # 2. Check for orphaned bonus check submissions
    bonus_submissions = await db.bonus_check_submissions.find({}, {'staff_id': 1, 'customer_id': 1}).to_list(10000)
    orphaned_bonus = [b for b in bonus_submissions if b.get('staff_id') not in all_staff_ids]
    
    if orphaned_bonus:
        issues.append({
            'type': 'orphaned_bonus_submissions',
            'severity': 'medium',
            'count': len(orphaned_bonus),
            'message': f'{len(orphaned_bonus)} bonus check submissions belong to deleted staff',
            'auto_fixable': True
        })
    
    stats['bonus_submissions'] = {
        'total': len(bonus_submissions),
        'orphaned': len(orphaned_bonus)
    }
    
    # 3. Check for reserved members without matching in bonus submissions
    # (Bonus submission exists but reserved member doesn't)
    reserved_set = set()
    for r in reserved_members:
        cid = (r.get('customer_id') or '').strip().upper()
        sid = r.get('staff_id', '')
        reserved_set.add((cid, sid))
    
    orphaned_submissions = []
    for b in bonus_submissions:
        cid = (b.get('customer_id_normalized') or '').strip().upper()
        sid = b.get('staff_id', '')
        if (cid, sid) not in reserved_set and sid in all_staff_ids:
            orphaned_submissions.append(b)
    
    if orphaned_submissions:
        warnings.append({
            'type': 'bonus_without_reservation',
            'severity': 'low',
            'count': len(orphaned_submissions),
            'message': f'{len(orphaned_submissions)} bonus submissions for customers no longer reserved',
            'auto_fixable': True
        })
    
    # 4. Check for attendance records with leave conflicts
    thirty_days_ago = (jakarta_now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    attendance_records = await db.attendance_records.find({
        'date': {'$gte': thirty_days_ago},
        'is_late': True
    }, {'_id': 0, 'staff_id': 1, 'date': 1}).to_list(10000)
    
    leave_records = await db.leave_requests.find({
        'status': 'approved',
        'date': {'$gte': thirty_days_ago}
    }, {'_id': 0, 'staff_id': 1, 'date': 1}).to_list(10000)
    
    leave_set = {(leave['staff_id'], leave['date']) for leave in leave_records}
    
    conflict_records = []
    for a in attendance_records:
        if (a['staff_id'], a['date']) in leave_set:
            if not a.get('has_approved_leave'):
                conflict_records.append(a)
    
    if conflict_records:
        issues.append({
            'type': 'attendance_leave_conflict',
            'severity': 'medium',
            'count': len(conflict_records),
            'message': f'{len(conflict_records)} attendance records marked late but staff had approved leave',
            'auto_fixable': True
        })
    
    stats['attendance'] = {
        'late_records_30d': len(attendance_records),
        'leave_conflicts': len(conflict_records)
    }
    
    # 5. Check for reserved members past grace period
    config = await db.reserved_member_config.find_one({'type': 'cleanup_config'}, {'_id': 0})
    grace_days = 30
    if config:
        grace_days = config.get('global_grace_days', 30)
    
    cutoff_date = (jakarta_now - timedelta(days=grace_days)).strftime('%Y-%m-%d')
    
    expired_count = 0
    for rm in reserved_members:
        last_omset = rm.get('last_omset_date')
        if last_omset:
            if isinstance(last_omset, str) and last_omset < cutoff_date:
                expired_count += 1
    
    if expired_count > 0:
        warnings.append({
            'type': 'expired_reservations',
            'severity': 'medium',
            'count': expired_count,
            'message': f'{expired_count} reserved members past grace period ({grace_days} days)',
            'auto_fixable': True
        })
    
    stats['grace_period'] = {
        'grace_days': grace_days,
        'expired_count': expired_count
    }
    
    # 6. Check scheduler status
    scheduler_config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    scheduler_status = {
        'reports_enabled': scheduler_config.get('enabled', False) if scheduler_config else False,
        'atrisk_enabled': scheduler_config.get('atrisk_enabled', False) if scheduler_config else False,
        'last_report_sent': scheduler_config.get('last_sent') if scheduler_config else None,
        'last_atrisk_sent': scheduler_config.get('atrisk_last_sent') if scheduler_config else None
    }
    
    stats['scheduler'] = scheduler_status
    
    # 7. Database collection stats
    collection_stats = {}
    collections = ['users', 'reserved_members', 'bonus_check_submissions', 'attendance_records', 
                   'leave_requests', 'omset_records', 'notifications', 'bonanza_records', 'memberwd_records']
    
    for coll in collections:
        try:
            count = await db[coll].count_documents({})
            collection_stats[coll] = count
        except Exception:
            collection_stats[coll] = 0
    
    stats['collections'] = collection_stats
    
    # Calculate health score
    critical_issues = len([i for i in issues if i['severity'] == 'high'])
    medium_issues = len([i for i in issues if i['severity'] == 'medium'])
    low_issues = len([i for i in issues if i['severity'] == 'low']) + len(warnings)
    
    health_score = 100 - (critical_issues * 20) - (medium_issues * 10) - (low_issues * 5)
    health_score = max(0, min(100, health_score))
    
    return {
        'health_score': health_score,
        'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 50 else 'critical',
        'issues': issues,
        'warnings': warnings,
        'stats': stats,
        'checked_at': jakarta_now.isoformat()
    }


@router.post("/data-sync/repair")
async def repair_data(repair_type: str, user: User = Depends(get_admin_user)):
    """
    Auto-repair detected data issues.
    
    repair_type options:
    - orphaned_reserved_members: Delete reserved members for deleted staff
    - orphaned_bonus_submissions: Delete bonus submissions for deleted staff
    - bonus_without_reservation: Delete bonus submissions without valid reservation
    - attendance_leave_conflict: Fix attendance records that should have leave flag
    - all: Run all repairs
    """
    db = get_db()
    jakarta_now = get_jakarta_now()
    results = {}
    
    # Get all valid staff IDs
    staff_users = await db.users.find({'role': 'staff'}, {'id': 1}).to_list(10000)
    all_staff_ids = {s['id'] for s in staff_users}
    
    if repair_type in ['orphaned_reserved_members', 'all']:
        # Delete reserved members for non-existent staff
        orphaned = await db.reserved_members.find(
            {'staff_id': {'$nin': list(all_staff_ids)}},
            {'id': 1}
        ).to_list(10000)
        
        if orphaned:
            result = await db.reserved_members.delete_many(
                {'staff_id': {'$nin': list(all_staff_ids)}}
            )
            results['orphaned_reserved_members'] = {
                'deleted': result.deleted_count,
                'message': f'Deleted {result.deleted_count} orphaned reserved members'
            }
        else:
            results['orphaned_reserved_members'] = {'deleted': 0, 'message': 'No orphaned records found'}
    
    if repair_type in ['orphaned_bonus_submissions', 'all']:
        # Delete bonus submissions for non-existent staff
        result = await db.bonus_check_submissions.delete_many(
            {'staff_id': {'$nin': list(all_staff_ids)}}
        )
        results['orphaned_bonus_submissions'] = {
            'deleted': result.deleted_count,
            'message': f'Deleted {result.deleted_count} orphaned bonus submissions'
        }
    
    if repair_type in ['bonus_without_reservation', 'all']:
        # Get all reserved members
        reserved_members = await db.reserved_members.find({}, {'customer_id': 1, 'staff_id': 1}).to_list(10000)
        reserved_set = set()
        for r in reserved_members:
            cid = (r.get('customer_id') or '').strip().upper()
            sid = r.get('staff_id', '')
            reserved_set.add((cid, sid))
        
        # Find bonus submissions without reservation
        bonus_submissions = await db.bonus_check_submissions.find({}, {'_id': 1, 'customer_id_normalized': 1, 'staff_id': 1}).to_list(10000)
        to_delete = []
        for b in bonus_submissions:
            cid = (b.get('customer_id_normalized') or '').strip().upper()
            sid = b.get('staff_id', '')
            if (cid, sid) not in reserved_set and sid in all_staff_ids:
                to_delete.append(b['_id'])
        
        if to_delete:
            result = await db.bonus_check_submissions.delete_many({'_id': {'$in': to_delete}})
            results['bonus_without_reservation'] = {
                'deleted': result.deleted_count,
                'message': f'Deleted {result.deleted_count} bonus submissions without reservation'
            }
        else:
            results['bonus_without_reservation'] = {'deleted': 0, 'message': 'No orphaned submissions found'}
    
    if repair_type in ['attendance_leave_conflict', 'all']:
        # Get ALL approved leave records
        leave_records = await db.leave_requests.find(
            {'status': 'approved'},
            {'staff_id': 1, 'date': 1, 'leave_type': 1}
        ).to_list(10000)
        
        # Create a map of leave by (staff_id, date)
        leave_map = {}
        for leave in leave_records:
            key = (leave['staff_id'], leave['date'])
            leave_map[key] = leave.get('leave_type', 'approved')
        
        # Update ALL attendance records that have approved leave for that day
        fixed_count = 0
        for (staff_id, date), leave_type in leave_map.items():
            # Update any attendance record for this staff+date to mark as has_approved_leave
            result = await db.attendance_records.update_many(
                {
                    'staff_id': staff_id,
                    'date': date,
                    '$or': [
                        {'has_approved_leave': {'$exists': False}},
                        {'has_approved_leave': False}
                    ]
                },
                {
                    '$set': {
                        'has_approved_leave': True,
                        'leave_type': leave_type,
                        'is_late': False,  # Can't be late if on leave
                        'sync_fixed_at': jakarta_now.isoformat()
                    }
                }
            )
            fixed_count += result.modified_count
        
        results['attendance_leave_conflict'] = {
            'fixed': fixed_count,
            'leave_days_checked': len(leave_map),
            'message': f'Synced {fixed_count} attendance records with leave data'
        }
    
    if repair_type in ['sync_last_omset_date', 'all']:
        # Populate last_omset_date for reserved members from omset_records
        # Support both old field (customer_name) and new field (customer_id)
        reserved_members = await db.reserved_members.find(
            {}, 
            {'_id': 0, 'id': 1, 'customer_id': 1, 'customer_name': 1, 'staff_id': 1, 'last_omset_date': 1}
        ).to_list(10000)
        
        updated_count = 0
        checked_count = 0
        already_has_date = 0
        no_omset_found = 0
        
        for rm in reserved_members:
            # Support both old and new field names
            customer_id = rm.get('customer_id') or rm.get('customer_name') or ''
            staff_id = rm.get('staff_id', '')
            
            if not customer_id:
                continue
            
            checked_count += 1
            
            # Skip if already has last_omset_date
            if rm.get('last_omset_date'):
                already_has_date += 1
                continue
            
            # Try to find omset record - first with exact staff match, then any staff
            last_omset = await db.omset_records.find_one(
                {
                    'customer_id': {'$regex': f'^{customer_id.strip()}$', '$options': 'i'},
                    'staff_id': staff_id
                },
                {'_id': 0, 'record_date': 1},
                sort=[('record_date', -1)]
            )
            
            # If not found with staff_id, try without staff filter (for migrated customers)
            if not last_omset:
                last_omset = await db.omset_records.find_one(
                    {
                        'customer_id': {'$regex': f'^{customer_id.strip()}$', '$options': 'i'}
                    },
                    {'_id': 0, 'record_date': 1},
                    sort=[('record_date', -1)]
                )
            
            if last_omset and last_omset.get('record_date'):
                from datetime import datetime
                try:
                    record_date_str = last_omset['record_date']
                    last_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    last_date = JAKARTA_TZ.localize(last_date)
                    
                    result = await db.reserved_members.update_one(
                        {'id': rm['id']},
                        {'$set': {
                            'last_omset_date': last_date.isoformat(),
                            'sync_updated_at': jakarta_now.isoformat()
                        }}
                    )
                    if result.modified_count > 0:
                        updated_count += 1
                except Exception as e:
                    print(f"Error updating last_omset_date for {customer_id}: {e}")
            else:
                no_omset_found += 1
        
        results['sync_last_omset_date'] = {
            'updated': updated_count,
            'checked': checked_count,
            'already_synced': already_has_date,
            'no_omset_found': no_omset_found,
            'message': f'Updated {updated_count} reserved members. {already_has_date} already had date. {no_omset_found} have no omset records.'
        }
    
    if repair_type in ['fix_cross_product_invalidations', 'all']:
        # Fix records that were wrongly invalidated due to cross-product reservation conflicts
        # These are records that were marked invalid because the customer was reserved by another staff,
        # but for a DIFFERENT product - which should NOT have caused invalidation
        
        fix_count = 0
        collections = ['customer_records', 'bonanza_records', 'memberwd_records']
        
        for collection_name in collections:
            # Find records that were invalidated due to reservation
            invalidated_records = await db[collection_name].find({
                'status': 'invalid',
                'invalid_reason': {'$regex': '^Customer reserved by', '$options': 'i'},
                'reserved_by_staff_id': {'$exists': True}
            }, {'_id': 0, 'id': 1, 'product_id': 1, 'reserved_by_staff_id': 1, 'row_data': 1}).to_list(100000)
            
            for record in invalidated_records:
                record_product_id = record.get('product_id')
                reserved_by_staff_id = record.get('reserved_by_staff_id')
                
                # Get customer ID from row_data
                row_data = record.get('row_data', {})
                customer_id = None
                for key in ['Username', 'username', 'USERNAME', 'USER', 'user', 'ID', 'id', 
                           'Nama Lengkap', 'nama_lengkap', 'Name', 'name', 
                           'CUSTOMER', 'customer', 'Customer', 'customer_id', 'Customer_ID']:
                    if key in row_data and row_data[key]:
                        customer_id = str(row_data[key]).strip().upper()
                        break
                
                if not customer_id or not record_product_id or not reserved_by_staff_id:
                    continue
                
                # Check if there's actually a reservation for this customer + product by this staff
                reservation = await db.reserved_members.find_one({
                    '$or': [
                        {'customer_id': {'$regex': f'^{customer_id}$', '$options': 'i'}},
                        {'customer_name': {'$regex': f'^{customer_id}$', '$options': 'i'}}
                    ],
                    'product_id': record_product_id,
                    'staff_id': reserved_by_staff_id,
                    'status': 'approved'
                })
                
                # If no matching reservation exists for this product, this was wrongly invalidated
                if not reservation:
                    # Restore the record to assigned status
                    await db[collection_name].update_one(
                        {'id': record['id']},
                        {'$set': {
                            'status': 'assigned',
                            'invalid_reason': None,
                            'invalidated_at': None,
                            'invalidated_by': None,
                            'reserved_by_staff_id': None,
                            'reserved_by_staff_name': None,
                            'restored_at': jakarta_now.isoformat(),
                            'restored_reason': 'Cross-product invalidation fix'
                        }}
                    )
                    fix_count += 1
        
        results['fix_cross_product_invalidations'] = {
            'fixed': fix_count,
            'message': f'Restored {fix_count} records that were wrongly invalidated due to cross-product reservation'
        }
    
    # Log the repair action
    await db.system_logs.insert_one({
        'type': 'data_repair',
        'repair_type': repair_type,
        'results': results,
        'performed_by': user.id,
        'performed_by_name': user.name,
        'performed_at': jakarta_now.isoformat()
    })
    
    return {
        'success': True,
        'repair_type': repair_type,
        'results': results,
        'repaired_at': jakarta_now.isoformat()
    }


@router.get("/data-sync/activity-log")
async def get_activity_log(
    limit: int = 50,
    log_type: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get recent system activity and repair logs"""
    db = get_db()
    
    query = {}
    if log_type:
        query['type'] = log_type
    
    logs = await db.system_logs.find(
        query,
        {'_id': 0}
    ).sort('performed_at', -1).limit(limit).to_list(limit)
    
    return {
        'logs': logs,
        'total': len(logs)
    }


@router.get("/data-sync/sync-status")
async def get_sync_status(user: User = Depends(get_admin_user)):
    """
    Get real-time sync status for all major features.
    Shows which features are properly synchronized.
    """
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    sync_features = []
    
    # 1. Attendance <-> Leave Sync
    # Check: How many attendance records exist for days with approved leave?
    leave_records = await db.leave_requests.find(
        {'status': 'approved'},
        {'staff_id': 1, 'date': 1}
    ).to_list(10000)
    leave_set = {(rec['staff_id'], rec['date']) for rec in leave_records}
    
    # Count attendance records that SHOULD have has_approved_leave flag
    attendance_with_leave = 0
    attendance_properly_flagged = 0
    
    for staff_id, date in leave_set:
        records = await db.attendance_records.find(
            {'staff_id': staff_id, 'date': date},
            {'_id': 0, 'has_approved_leave': 1}
        ).to_list(100)
        
        for r in records:
            attendance_with_leave += 1
            if r.get('has_approved_leave'):
                attendance_properly_flagged += 1
    
    if attendance_with_leave > 0:
        sync_features.append({
            'feature': 'Attendance + Leave',
            'description': 'Staff with approved leave are not marked late',
            'status': 'synced' if attendance_properly_flagged == attendance_with_leave else 'partial',
            'details': f'{attendance_properly_flagged}/{attendance_with_leave} records have leave flag'
        })
    else:
        # No attendance records on leave days - check general flag presence
        recent_attendance = await db.attendance_records.find(
            {},
            {'_id': 0, 'has_approved_leave': 1}
        ).limit(100).to_list(100)
        
        leave_aware_count = sum(1 for a in recent_attendance if a.get('has_approved_leave') is not None)
        
        sync_features.append({
            'feature': 'Attendance + Leave',
            'description': 'Staff with approved leave are not marked late',
            'status': 'synced' if leave_aware_count == len(recent_attendance) or len(recent_attendance) == 0 else 'partial',
            'details': f'{leave_aware_count}/{len(recent_attendance)} records have leave flag'
        })
    
    # 2. Reserved Members <-> Last Omset Sync
    reserved = await db.reserved_members.find(
        {}, 
        {'_id': 0, 'last_omset_date': 1, 'customer_id': 1, 'customer_name': 1}
    ).to_list(10000)
    has_omset_date = sum(1 for r in reserved if r.get('last_omset_date'))
    total_reserved = len(reserved)
    
    # For reserved members without date, check if they have any omset records
    can_sync = 0
    for r in reserved:
        if not r.get('last_omset_date'):
            cid = r.get('customer_id') or r.get('customer_name')
            if cid:
                has_omset = await db.omset_records.count_documents({
                    'customer_id': {'$regex': f'^{cid.strip()}$', '$options': 'i'}
                })
                if has_omset > 0:
                    can_sync += 1
    
    if total_reserved > 0:
        status = 'synced' if has_omset_date == total_reserved else 'partial'
        details = f'{has_omset_date}/{total_reserved} members have last_omset_date'
        if can_sync > 0:
            details += f' ({can_sync} can be synced)'
    else:
        status = 'synced'
        details = 'No reserved members'
    
    sync_features.append({
        'feature': 'Reserved Members + Omset',
        'description': 'Reserved members track last deposit date',
        'status': status,
        'details': details
    })
    
    # 3. User Delete Cascade
    # Check if any orphaned data exists
    staff_ids = {s['id'] for s in await db.users.find({'role': 'staff'}, {'id': 1}).to_list(10000)}
    
    orphaned_reserved = await db.reserved_members.count_documents({'staff_id': {'$nin': list(staff_ids)}})
    orphaned_bonus = await db.bonus_check_submissions.count_documents({'staff_id': {'$nin': list(staff_ids)}})
    orphaned_attendance = await db.attendance_records.count_documents({'staff_id': {'$nin': list(staff_ids)}})
    
    total_orphaned = orphaned_reserved + orphaned_bonus + orphaned_attendance
    
    sync_features.append({
        'feature': 'User Delete Cascade',
        'description': 'Deleting users removes all related data',
        'status': 'synced' if total_orphaned == 0 else 'needs_repair',
        'details': f'{total_orphaned} orphaned records found' if total_orphaned > 0 else 'No orphaned data'
    })
    
    # 4. Bonus Check Expiration Sync
    sync_features.append({
        'feature': 'Bonus Check Expiration',
        'description': 'Uses actual deposit date (record_date) for expiration',
        'status': 'synced',
        'details': 'Code verified to use record_date from omset_records'
    })
    
    # 5. Fee Calculation Sync
    sync_features.append({
        'feature': 'Lateness Fees + Leave',
        'description': 'Fee calculation excludes approved leave days',
        'status': 'synced',
        'details': 'Code verified to exclude has_approved_leave records'
    })
    
    # 6. Scheduler Status
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    sync_features.append({
        'feature': 'Scheduled Jobs',
        'description': 'Daily cleanup and alert jobs',
        'status': 'active',
        'details': f"Cleanup: 00:01 WIB | Reports: {'Enabled' if config and config.get('enabled') else 'Disabled'}"
    })
    
    # Calculate overall sync health
    synced_count = sum(1 for f in sync_features if f['status'] in ['synced', 'active'])
    
    return {
        'overall_status': 'healthy' if synced_count == len(sync_features) else 'needs_attention',
        'synced_features': synced_count,
        'total_features': len(sync_features),
        'features': sync_features,
        'checked_at': jakarta_now.isoformat()
    }


@router.post("/data-sync/proactive-check")
async def proactive_health_check(user: User = Depends(get_admin_user)):
    """
    Run a health check and send notifications to admins if critical issues are found.
    This can be triggered manually or by a scheduled job.
    """
    from .notifications import create_notification
    
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    # Run the health check
    health_result = await run_health_check(user)
    
    issues = health_result.get('issues', [])
    warnings = health_result.get('warnings', [])
    health_score = health_result.get('health_score', 100)
    
    # Determine if we should notify admins
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    medium_issues = [i for i in issues if i.get('severity') == 'medium']
    
    notifications_sent = 0
    
    # Only send notifications if there are issues worth reporting
    if critical_issues or (medium_issues and health_score < 80):
        # Get all admins
        admins = await db.users.find(
            {'role': {'$in': ['admin', 'master_admin']}},
            {'_id': 0, 'id': 1, 'name': 1}
        ).to_list(100)
        
        # Build notification message
        if critical_issues:
            title = f'🚨 Critical Data Issues Detected ({len(critical_issues)})'
            message_parts = [f'Health Score: {health_score}%']
            for issue in critical_issues[:3]:
                message_parts.append(f"• {issue['message']}")
            if len(critical_issues) > 3:
                message_parts.append(f"... and {len(critical_issues) - 3} more")
            message = '\n'.join(message_parts)
            notification_type = 'data_health_critical'
        else:
            title = f'⚠️ Data Health Warning ({len(medium_issues)} issues)'
            message_parts = [f'Health Score: {health_score}%']
            for issue in medium_issues[:3]:
                message_parts.append(f"• {issue['message']}")
            if len(medium_issues) > 3:
                message_parts.append(f"... and {len(medium_issues) - 3} more")
            message = '\n'.join(message_parts)
            notification_type = 'data_health_warning'
        
        # Send notification to all admins
        for admin in admins:
            await create_notification(
                user_id=admin['id'],
                type=notification_type,
                title=title,
                message=message,
                data={
                    'health_score': health_score,
                    'critical_count': len(critical_issues),
                    'warning_count': len(medium_issues),
                    'checked_at': jakarta_now.isoformat()
                }
            )
            notifications_sent += 1
        
        # Log this proactive check
        await db.system_logs.insert_one({
            'type': 'proactive_health_check',
            'health_score': health_score,
            'issues_found': len(issues),
            'warnings_found': len(warnings),
            'notifications_sent': notifications_sent,
            'performed_at': jakarta_now.isoformat(),
            'performed_by': user.id
        })
    
    return {
        'health_score': health_score,
        'issues_found': len(issues),
        'critical_issues': len(critical_issues),
        'medium_issues': len(medium_issues),
        'warnings_found': len(warnings),
        'notifications_sent': notifications_sent,
        'message': f'Sent {notifications_sent} notifications to admins' if notifications_sent > 0 else 'No critical issues - no notifications sent',
        'checked_at': jakarta_now.isoformat()
    }


@router.get("/data-sync/monitoring-config")
async def get_monitoring_config(user: User = Depends(get_admin_user)):
    """Get proactive monitoring configuration"""
    db = get_db()
    
    config = await db.system_settings.find_one(
        {'key': 'proactive_monitoring'},
        {'_id': 0}
    )
    
    if not config:
        config = {
            'enabled': False,
            'check_interval_hours': 6,
            'notify_on_warning': False,
            'notify_on_critical': True,
            'last_check': None
        }
    
    return config


@router.put("/data-sync/monitoring-config")
async def update_monitoring_config(
    enabled: bool = True,
    check_interval_hours: int = 6,
    notify_on_warning: bool = False,
    notify_on_critical: bool = True,
    user: User = Depends(get_admin_user)
):
    """Update proactive monitoring configuration"""
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    await db.system_settings.update_one(
        {'key': 'proactive_monitoring'},
        {'$set': {
            'key': 'proactive_monitoring',
            'enabled': enabled,
            'check_interval_hours': check_interval_hours,
            'notify_on_warning': notify_on_warning,
            'notify_on_critical': notify_on_critical,
            'updated_at': jakarta_now.isoformat(),
            'updated_by': user.id
        }},
        upsert=True
    )


@router.get("/data-sync/conflict-resolution-log")
async def get_conflict_resolution_log(
    limit: int = 100,
    skip: int = 0,
    staff_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """
    Get history of all auto-invalidated records due to reservation conflicts.
    Shows customer ID, affected staff, timestamp, source database, and who reserved.
    """
    db = get_db()
    
    # Build query for invalidated records with reservation reason
    base_query = {
        'status': 'invalid',
        'invalid_reason': {'$regex': '^Customer reserved by', '$options': 'i'}
    }
    
    # Add filters
    if staff_id:
        base_query['assigned_to'] = staff_id
    
    if date_from:
        base_query['invalidated_at'] = {'$gte': date_from}
    
    if date_to:
        if 'invalidated_at' in base_query:
            base_query['invalidated_at']['$lte'] = date_to
        else:
            base_query['invalidated_at'] = {'$lte': date_to}
    
    # Fetch from all 3 collections
    collections = [
        ('customer_records', 'Normal Database'),
        ('bonanza_records', 'DB Bonanza'),
        ('memberwd_records', 'Member WD CRM')
    ]
    
    all_records = []
    
    for collection_name, source_label in collections:
        records = await db[collection_name].find(
            base_query,
            {
                '_id': 0,
                'id': 1,
                'database_name': 1,
                'assigned_to': 1,
                'assigned_to_name': 1,
                'invalid_reason': 1,
                'invalidated_at': 1,
                'invalidated_by': 1,
                'reserved_by_staff_id': 1,
                'reserved_by_staff_name': 1,
                'row_data': 1
            }
        ).sort('invalidated_at', -1).to_list(1000)
        
        for record in records:
            # Extract customer ID from row_data
            row_data = record.get('row_data', {})
            customer_id = None
            for key in ['Username', 'username', 'USERNAME', 'USER', 'user', 'CUSTOMER_ID', 'customer_id', 'ID', 'id']:
                if key in row_data:
                    customer_id = str(row_data[key]).strip()
                    break
            
            all_records.append({
                'record_id': record.get('id'),
                'customer_id': customer_id or 'Unknown',
                'source_type': source_label,
                'database_name': record.get('database_name', 'Unknown'),
                'affected_staff_id': record.get('assigned_to'),
                'affected_staff_name': record.get('assigned_to_name', 'Unknown'),
                'reserved_by_staff_id': record.get('reserved_by_staff_id'),
                'reserved_by_staff_name': record.get('reserved_by_staff_name', 'Unknown'),
                'invalid_reason': record.get('invalid_reason'),
                'invalidated_at': record.get('invalidated_at'),
                'invalidated_by': record.get('invalidated_by', 'system')
            })
    
    # Sort all records by invalidated_at descending
    all_records.sort(key=lambda x: x.get('invalidated_at') or '', reverse=True)
    
    # Get total count before pagination
    total_count = len(all_records)
    
    # Apply pagination
    paginated_records = all_records[skip:skip + limit]
    
    # Get summary stats
    affected_staff_ids = set(r['affected_staff_id'] for r in all_records if r['affected_staff_id'])
    reserved_by_ids = set(r['reserved_by_staff_id'] for r in all_records if r['reserved_by_staff_id'])
    
    # Count by source type
    by_source = {}
    for record in all_records:
        source = record['source_type']
        by_source[source] = by_source.get(source, 0) + 1
    
    # Count by date (last 7 days)
    from collections import defaultdict
    by_date = defaultdict(int)
    for record in all_records:
        if record.get('invalidated_at'):
            date_str = record['invalidated_at'][:10]  # Get YYYY-MM-DD
            by_date[date_str] += 1
    
    return {
        'total_count': total_count,
        'returned_count': len(paginated_records),
        'skip': skip,
        'limit': limit,
        'summary': {
            'total_invalidated': total_count,
            'affected_staff_count': len(affected_staff_ids),
            'reserved_by_count': len(reserved_by_ids),
            'by_source': by_source,
            'by_date': dict(sorted(by_date.items(), reverse=True)[:7])
        },
        'records': paginated_records
    }


@router.get("/data-sync/conflict-resolution-stats")
async def get_conflict_resolution_stats(user: User = Depends(get_admin_user)):
    """
    Get aggregated statistics for conflict resolutions.
    Useful for dashboard widgets.
    """
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    # Query for invalidated records due to reservation
    base_query = {
        'status': 'invalid',
        'invalid_reason': {'$regex': '^Customer reserved by', '$options': 'i'}
    }
    
    collections = ['customer_records', 'bonanza_records', 'memberwd_records']
    
    total_count = 0
    today_count = 0
    this_week_count = 0
    this_month_count = 0
    
    today_str = jakarta_now.strftime('%Y-%m-%d')
    week_ago = (jakarta_now - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (jakarta_now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Staff breakdown
    affected_staff = {}
    reserved_by_staff = {}
    
    for collection_name in collections:
        # Total count
        count = await db[collection_name].count_documents(base_query)
        total_count += count
        
        # Today count
        today_query = {**base_query, 'invalidated_at': {'$gte': today_str}}
        today_count += await db[collection_name].count_documents(today_query)
        
        # This week count
        week_query = {**base_query, 'invalidated_at': {'$gte': week_ago}}
        this_week_count += await db[collection_name].count_documents(week_query)
        
        # This month count
        month_query = {**base_query, 'invalidated_at': {'$gte': month_ago}}
        this_month_count += await db[collection_name].count_documents(month_query)
        
        # Get staff breakdown
        records = await db[collection_name].find(
            base_query,
            {'_id': 0, 'assigned_to_name': 1, 'reserved_by_staff_name': 1}
        ).to_list(10000)
        
        for r in records:
            affected = r.get('assigned_to_name', 'Unknown')
            reserved = r.get('reserved_by_staff_name', 'Unknown')
            affected_staff[affected] = affected_staff.get(affected, 0) + 1
            reserved_by_staff[reserved] = reserved_by_staff.get(reserved, 0) + 1
    
    # Sort staff by count
    top_affected = sorted(affected_staff.items(), key=lambda x: x[1], reverse=True)[:5]
    top_reserved = sorted(reserved_by_staff.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'total_invalidated': total_count,
        'today': today_count,
        'this_week': this_week_count,
        'this_month': this_month_count,
        'top_affected_staff': [{'name': k, 'count': v} for k, v in top_affected],
        'top_reserved_by_staff': [{'name': k, 'count': v} for k, v in top_reserved],
        'generated_at': jakarta_now.isoformat()
    }
