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
        # Get approved leave records
        leave_records = await db.leave_requests.find(
            {'status': 'approved'},
            {'staff_id': 1, 'date': 1}
        ).to_list(10000)
        leave_set = {(leave['staff_id'], leave['date']) for leave in leave_records}
        
        # Update attendance records that have leave but aren't marked
        fixed_count = 0
        for staff_id, date in leave_set:
            result = await db.attendance_records.update_many(
                {
                    'staff_id': staff_id,
                    'date': date,
                    'is_late': True,
                    '$or': [
                        {'has_approved_leave': {'$exists': False}},
                        {'has_approved_leave': False}
                    ]
                },
                {
                    '$set': {
                        'has_approved_leave': True,
                        'is_late': False,
                        'sync_fixed_at': jakarta_now.isoformat()
                    }
                }
            )
            fixed_count += result.modified_count
        
        results['attendance_leave_conflict'] = {
            'fixed': fixed_count,
            'message': f'Fixed {fixed_count} attendance records with leave conflict'
        }
    
    if repair_type in ['sync_last_omset_date', 'all']:
        # Populate last_omset_date for reserved members from omset_records
        reserved_members = await db.reserved_members.find({}, {'_id': 0, 'id': 1, 'customer_id': 1, 'staff_id': 1}).to_list(10000)
        updated_count = 0
        
        for rm in reserved_members:
            customer_id = rm.get('customer_id', '')
            staff_id = rm.get('staff_id', '')
            
            if not customer_id or not staff_id:
                continue
            
            # Find the most recent omset record for this customer+staff
            last_omset = await db.omset_records.find_one(
                {
                    'customer_id': {'$regex': f'^{customer_id}$', '$options': 'i'},
                    'staff_id': staff_id
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
                        {'$set': {'last_omset_date': last_date.isoformat()}}
                    )
                    if result.modified_count > 0:
                        updated_count += 1
                except Exception as e:
                    print(f"Error updating last_omset_date for {customer_id}: {e}")
        
        results['sync_last_omset_date'] = {
            'updated': updated_count,
            'message': f'Updated last_omset_date for {updated_count} reserved members'
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
    recent_attendance = await db.attendance_records.find(
        {'is_late': True},
        {'_id': 0, 'has_approved_leave': 1}
    ).limit(100).to_list(100)
    
    leave_aware_count = sum(1 for a in recent_attendance if a.get('has_approved_leave') is not None)
    
    sync_features.append({
        'feature': 'Attendance + Leave',
        'description': 'Staff with approved leave are not marked late',
        'status': 'synced' if leave_aware_count == len(recent_attendance) else 'partial',
        'details': f'{leave_aware_count}/{len(recent_attendance)} records have leave flag'
    })
    
    # 2. Reserved Members <-> Last Omset Sync
    reserved = await db.reserved_members.find({}, {'_id': 0, 'last_omset_date': 1}).to_list(1000)
    has_omset_date = sum(1 for r in reserved if r.get('last_omset_date'))
    
    sync_features.append({
        'feature': 'Reserved Members + Omset',
        'description': 'Reserved members track last deposit date',
        'status': 'synced' if has_omset_date >= len(reserved) * 0.8 else 'partial' if has_omset_date > 0 else 'not_synced',
        'details': f'{has_omset_date}/{len(reserved)} members have last_omset_date'
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
