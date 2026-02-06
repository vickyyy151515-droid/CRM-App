# Leaderboard and Targets Routes
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .deps import get_db, get_current_user, get_admin_user, User
from utils.helpers import normalize_customer_id, get_jakarta_now

router = APIRouter(tags=["Leaderboard"])

# ==================== PYDANTIC MODELS ====================

class TargetsUpdate(BaseModel):
    monthly_omset: float  # Monthly OMSET target in Rupiah
    daily_ndp: int  # Daily NDP target
    daily_rdp: int  # Daily RDP target

# ==================== DEFAULT TARGETS ====================

DEFAULT_TARGETS = {
    'monthly_omset': 100000000,  # Rp 100M default
    'daily_ndp': 10,  # 10 NDP per day
    'daily_rdp': 15   # 15 RDP per day
}

# ==================== HELPER FUNCTIONS ====================

async def get_targets():
    """Get current targets from database or return defaults"""
    db = get_db()
    config = await db.settings.find_one({'key': 'staff_targets'}, {'_id': 0})
    if config:
        return config['value']
    return DEFAULT_TARGETS

# ==================== LEADERBOARD ENDPOINTS ====================

@router.get("/leaderboard")
async def get_leaderboard(
    period: str = "month",  # "month" or "all"
    user: User = Depends(get_current_user)
):
    """Get staff leaderboard with rankings by OMSET, NDP, RDP"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    current_year = jakarta_now.year
    current_month = jakarta_now.month
    today = jakarta_now.strftime('%Y-%m-%d')
    
    # Build query based on period
    if period == "month":
        month_str = f"{current_year}-{str(current_month).zfill(2)}"
        query = {'record_date': {'$regex': f'^{month_str}'}}
    else:  # all time
        query = {}
    
    def is_tambahan_record(record):
        """Check if record has 'tambahan' in keterangan field"""
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Fetch records for calculating unique customers
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    today_records = await db.omset_records.find({'record_date': today}, {'_id': 0}).to_list(10000)
    
    # Build customer_first_date for NDP detection (need all records for this)
    # IMPORTANT: Exclude records with "tambahan" from first_date calculation
    all_records = await db.omset_records.find({}, {'_id': 0, 'customer_id': 1, 'customer_id_normalized': 1, 'product_id': 1, 'record_date': 1, 'keterangan': 1, 'staff_id': 1}).to_list(100000)
    
    # STAFF-SPECIFIC customer_first_date (SINGLE SOURCE OF TRUTH for NDP/RDP)
    # Key: (staff_id, customer_id_normalized, product_id) -> first_date
    staff_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        staff_id_rec = record['staff_id']
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (staff_id_rec, cid_normalized, record['product_id'])
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Get all staff users
    staff_users = await db.users.find({'role': 'staff'}, {'_id': 0}).to_list(100)
    staff_map = {s['id']: s for s in staff_users}
    
    # Calculate stats for each staff - track (customer, product) pairs for consistency
    staff_stats = {}
    for staff in staff_users:
        staff_stats[staff['id']] = {
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'total_omset': 0,
            'total_ndp': 0,
            'total_rdp': 0,
            'today_ndp': 0,
            'today_rdp': 0,
            'days_worked': set(),
            'daily_ndp_pairs': {},  # {date: set((customer_id, product_id))}
            'daily_rdp_pairs': {}   # {date: set((customer_id, product_id))}
        }
    
    # Process records
    for record in records:
        staff_id = record['staff_id']
        date = record['record_date']
        
        # Initialize staff if not exists (for deleted staff)
        if staff_id not in staff_stats:
            staff_stats[staff_id] = {
                'staff_id': staff_id,
                'staff_name': record.get('staff_name', 'Unknown'),
                'total_omset': 0,
                'total_ndp': 0,
                'total_rdp': 0,
                'today_ndp': 0,
                'today_rdp': 0,
                'days_worked': set(),
                'daily_ndp_pairs': {},
                'daily_rdp_pairs': {}
            }
        
        staff_stats[staff_id]['total_omset'] += record.get('depo_total', 0) or 0
        staff_stats[staff_id]['days_worked'].add(date)
        
        # Initialize daily tracking sets
        if date not in staff_stats[staff_id]['daily_ndp_pairs']:
            staff_stats[staff_id]['daily_ndp_pairs'][date] = set()
            staff_stats[staff_id]['daily_rdp_pairs'][date] = set()
        
        # Check NDP/RDP - use STAFF-SPECIFIC first_date
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        product_id_rec = record['product_id']
        staff_key = (staff_id, cid_normalized, product_id_rec)
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        # Track by (customer, product) pair — each product counted independently
        customer_product_pair = (cid_normalized, product_id_rec)
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            if customer_product_pair not in staff_stats[staff_id]['daily_rdp_pairs'][date]:
                staff_stats[staff_id]['daily_rdp_pairs'][date].add(customer_product_pair)
                staff_stats[staff_id]['total_rdp'] += 1
        elif staff_first_date == date:
            if customer_product_pair not in staff_stats[staff_id]['daily_ndp_pairs'][date]:
                staff_stats[staff_id]['daily_ndp_pairs'][date].add(customer_product_pair)
                staff_stats[staff_id]['total_ndp'] += 1
        else:
            if customer_product_pair not in staff_stats[staff_id]['daily_rdp_pairs'][date]:
                staff_stats[staff_id]['daily_rdp_pairs'][date].add(customer_product_pair)
                staff_stats[staff_id]['total_rdp'] += 1
    
    # Calculate today's stats separately
    today_ndp_pairs = {}  # {staff_id: set((customer_id, product_id))}
    today_rdp_pairs = {}  # {staff_id: set((customer_id, product_id))}
    
    for record in today_records:
        staff_id = record['staff_id']
        
        if staff_id not in today_ndp_pairs:
            today_ndp_pairs[staff_id] = set()
            today_rdp_pairs[staff_id] = set()
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        product_id_rec = record['product_id']
        # Use STAFF-SPECIFIC first_date for today's stats too
        staff_key = (staff_id, cid_normalized, product_id_rec)
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        customer_product_pair = (cid_normalized, product_id_rec)
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            if customer_product_pair not in today_rdp_pairs[staff_id]:
                today_rdp_pairs[staff_id].add(customer_product_pair)
                if staff_id in staff_stats:
                    staff_stats[staff_id]['today_rdp'] += 1
        elif staff_first_date == today:
            if customer_product_pair not in today_ndp_pairs[staff_id]:
                today_ndp_pairs[staff_id].add(customer_product_pair)
                if staff_id in staff_stats:
                    staff_stats[staff_id]['today_ndp'] += 1
        else:
            if customer_product_pair not in today_rdp_pairs[staff_id]:
                today_rdp_pairs[staff_id].add(customer_product_pair)
                if staff_id in staff_stats:
                    staff_stats[staff_id]['today_rdp'] += 1
    
    # Convert to list and calculate averages
    leaderboard = []
    for staff_id, stats in staff_stats.items():
        days_count = len(stats['days_worked'])
        leaderboard.append({
            'staff_id': stats['staff_id'],
            'staff_name': stats['staff_name'],
            'total_omset': stats['total_omset'],
            'total_ndp': stats['total_ndp'],
            'total_rdp': stats['total_rdp'],
            'today_ndp': stats['today_ndp'],
            'today_rdp': stats['today_rdp'],
            'days_worked': days_count,
            'avg_daily_omset': stats['total_omset'] / days_count if days_count > 0 else 0,
            'avg_daily_ndp': stats['total_ndp'] / days_count if days_count > 0 else 0,
            'avg_daily_rdp': stats['total_rdp'] / days_count if days_count > 0 else 0
        })
    
    # Sort by OMSET for default ranking
    leaderboard_by_omset = sorted(leaderboard, key=lambda x: x['total_omset'], reverse=True)
    leaderboard_by_ndp = sorted(leaderboard, key=lambda x: x['total_ndp'], reverse=True)
    leaderboard_by_rdp = sorted(leaderboard, key=lambda x: x['total_rdp'], reverse=True)
    
    # Add ranks
    for i, item in enumerate(leaderboard_by_omset):
        item['omset_rank'] = i + 1
    for i, item in enumerate(leaderboard_by_ndp):
        for lb in leaderboard_by_omset:
            if lb['staff_id'] == item['staff_id']:
                lb['ndp_rank'] = i + 1
                break
    for i, item in enumerate(leaderboard_by_rdp):
        for lb in leaderboard_by_omset:
            if lb['staff_id'] == item['staff_id']:
                lb['rdp_rank'] = i + 1
                break
    
    # Get targets
    targets = await get_targets()
    
    return {
        'period': period,
        'year': current_year,
        'month': current_month,
        'today': today,
        'leaderboard': leaderboard_by_omset,
        'targets': targets
    }

@router.get("/leaderboard/targets")
async def get_leaderboard_targets(user: User = Depends(get_current_user)):
    """Get current targets"""
    targets = await get_targets()
    return targets

@router.put("/leaderboard/targets")
async def update_leaderboard_targets(
    targets: TargetsUpdate,
    user: User = Depends(get_admin_user)
):
    """Update targets (Admin only)"""
    db = get_db()
    
    targets_doc = {
        'key': 'staff_targets',
        'value': {
            'monthly_omset': targets.monthly_omset,
            'daily_ndp': targets.daily_ndp,
            'daily_rdp': targets.daily_rdp
        },
        'updated_at': get_jakarta_now().isoformat(),
        'updated_by': user.id,
        'updated_by_name': user.name
    }
    
    await db.settings.update_one(
        {'key': 'staff_targets'},
        {'$set': targets_doc},
        upsert=True
    )
    
    return {'message': 'Targets updated successfully', 'targets': targets_doc['value']}

@router.post("/leaderboard/targets/reset")
async def reset_leaderboard_targets(user: User = Depends(get_admin_user)):
    """Reset targets to defaults (Admin only)"""
    db = get_db()
    await db.settings.delete_one({'key': 'staff_targets'})
    return {'message': 'Targets reset to defaults', 'targets': DEFAULT_TARGETS}

# ==================== STAFF TARGET PROGRESS ====================

REQUIRED_SUCCESS_DAYS = 18  # Must reach target on at least 18 days per month

@router.get("/staff/target-progress")
async def get_staff_target_progress(user: User = Depends(get_current_user)):
    """
    Get staff's own target progress for the banner display.
    Calculates:
    - Today's NDP/RDP vs target
    - Days reached target this month
    - Current streak
    - Previous months failure status (for warning levels)
    """
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    current_year = jakarta_now.year
    current_month = jakarta_now.month
    today = jakarta_now.strftime('%Y-%m-%d')
    current_day = jakarta_now.day
    days_in_month = 31 if current_month in [1,3,5,7,8,10,12] else 30 if current_month in [4,6,9,11] else 29 if current_year % 4 == 0 else 28
    days_remaining = days_in_month - current_day
    
    # Get targets
    targets = await get_targets()
    daily_ndp_target = targets.get('daily_ndp', 10)
    daily_rdp_target = targets.get('daily_rdp', 15)
    
    staff_id = user.id
    
    def is_tambahan_record(record):
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get all records for this staff
    all_records = await db.omset_records.find(
        {'staff_id': staff_id},
        {'_id': 0, 'customer_id': 1, 'customer_id_normalized': 1, 'product_id': 1, 'record_date': 1, 'keterangan': 1}
    ).to_list(100000)
    
    # Build staff-specific customer_first_date
    staff_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Calculate daily NDP/RDP for current month
    month_str = f"{current_year}-{str(current_month).zfill(2)}"
    month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
    
    # Track unique customers per day
    daily_ndp = {}  # {date: set(customer_ids)}
    daily_rdp = {}  # {date: set(customer_ids)}
    
    for record in month_records:
        date = record['record_date']
        if date not in daily_ndp:
            daily_ndp[date] = set()
            daily_rdp[date] = set()
        
        if is_tambahan_record(record):
            continue
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        first_date = staff_customer_first_date.get(key)
        
        if first_date:
            unique_key = f"{cid_normalized}_{record['product_id']}"
            if first_date == date:
                daily_ndp[date].add(unique_key)
            else:
                daily_rdp[date].add(unique_key)
    
    # Calculate today's progress
    today_ndp_count = len(daily_ndp.get(today, set()))
    today_rdp_count = len(daily_rdp.get(today, set()))
    today_target_reached = today_ndp_count >= daily_ndp_target or today_rdp_count >= daily_rdp_target
    today_reached_via = 'ndp' if today_ndp_count >= daily_ndp_target else ('rdp' if today_rdp_count >= daily_rdp_target else None)
    
    # Calculate days reached target this month
    success_days = 0
    success_dates = []
    all_dates_in_month = sorted(set(daily_ndp.keys()) | set(daily_rdp.keys()))
    
    for date in all_dates_in_month:
        ndp_count = len(daily_ndp.get(date, set()))
        rdp_count = len(daily_rdp.get(date, set()))
        if ndp_count >= daily_ndp_target or rdp_count >= daily_rdp_target:
            success_days += 1
            success_dates.append(date)
    
    # Calculate current streak (consecutive days reaching target, ending today or yesterday)
    streak = 0
    check_date = today
    while True:
        ndp_count = len(daily_ndp.get(check_date, set()))
        rdp_count = len(daily_rdp.get(check_date, set()))
        if ndp_count >= daily_ndp_target or rdp_count >= daily_rdp_target:
            streak += 1
            # Go to previous day
            prev_date = datetime.strptime(check_date, '%Y-%m-%d')
            prev_date = prev_date.replace(day=prev_date.day - 1) if prev_date.day > 1 else None
            if prev_date:
                check_date = prev_date.strftime('%Y-%m-%d')
            else:
                break
        else:
            break
    
    # Get previous months' success history
    # Check last 2 months for warning levels
    # IMPORTANT: Reset at January - don't look at previous year's data
    prev_month_1 = current_month - 1 if current_month > 1 else 12
    prev_year_1 = current_year if current_month > 1 else current_year - 1
    prev_month_2 = prev_month_1 - 1 if prev_month_1 > 1 else 12
    prev_year_2 = prev_year_1 if prev_month_1 > 1 else prev_year_1 - 1
    
    # Reset warning counters in January - don't look back to previous year
    # This gives staff a fresh start each year
    skip_prev_month_1 = current_month == 1  # January - skip December of last year
    skip_prev_month_2 = current_month <= 2  # January/February - skip months from last year
    
    async def get_month_success(year, month):
        """Calculate success days for a specific month"""
        month_str = f"{year}-{str(month).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        daily_ndp_m = {}
        daily_rdp_m = {}
        
        for record in month_records:
            date = record['record_date']
            if date not in daily_ndp_m:
                daily_ndp_m[date] = set()
                daily_rdp_m[date] = set()
            
            if is_tambahan_record(record):
                continue
            
            cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record['product_id'])
            first_date = staff_customer_first_date.get(key)
            
            if first_date:
                unique_key = f"{cid_normalized}_{record['product_id']}"
                if first_date == date:
                    daily_ndp_m[date].add(unique_key)
                else:
                    daily_rdp_m[date].add(unique_key)
        
        success = 0
        for date in set(daily_ndp_m.keys()) | set(daily_rdp_m.keys()):
            if len(daily_ndp_m.get(date, set())) >= daily_ndp_target or len(daily_rdp_m.get(date, set())) >= daily_rdp_target:
                success += 1
        return success
    
    prev_month_1_success = await get_month_success(prev_year_1, prev_month_1) if not skip_prev_month_1 else REQUIRED_SUCCESS_DAYS  # Treat as passed if skipped
    prev_month_2_success = await get_month_success(prev_year_2, prev_month_2) if not skip_prev_month_2 else REQUIRED_SUCCESS_DAYS  # Treat as passed if skipped
    
    prev_month_1_failed = prev_month_1_success < REQUIRED_SUCCESS_DAYS and not skip_prev_month_1
    prev_month_2_failed = prev_month_2_success < REQUIRED_SUCCESS_DAYS and not skip_prev_month_2
    
    # Determine warning level
    # 0 = No warning (on track or met target)
    # 1 = Soft warning (10 days before month end, not on track)
    # 2 = Hard warning (failed last month)
    # 3 = Very serious warning (failed 2 consecutive months)
    
    warning_level = 0
    warning_message = None
    
    if prev_month_1_failed and prev_month_2_failed:
        warning_level = 3
        warning_message = f"⚠️ SERIOUS: You've missed the {REQUIRED_SUCCESS_DAYS}-day target for 2 consecutive months. Immediate improvement required!"
    elif prev_month_1_failed:
        warning_level = 2
        warning_message = f"⚠️ WARNING: You missed the {REQUIRED_SUCCESS_DAYS}-day target last month ({prev_month_1_success} days). Don't let it happen again!"
    elif days_remaining <= 10 and success_days < REQUIRED_SUCCESS_DAYS:
        days_needed = REQUIRED_SUCCESS_DAYS - success_days
        if days_needed > days_remaining:
            warning_level = 1
            warning_message = f"⚠️ You need {days_needed} more successful days but only {days_remaining} days left in the month!"
        elif days_needed > 0:
            warning_level = 1
            warning_message = f"📢 {days_remaining} days left! Need {days_needed} more successful day(s) to reach {REQUIRED_SUCCESS_DAYS}-day target."
    
    # Calculate projection
    if current_day > 0:
        avg_success_rate = success_days / current_day
        projected_success = int(avg_success_rate * days_in_month)
    else:
        projected_success = 0
    
    # Determine status symbol
    # 🏆 = Met/exceeding monthly target
    # ✓ = On track
    # ⚠️ = Soft warning / 1st month failure
    # 🚨 = 2nd consecutive month failure
    
    if warning_level == 3:
        status_symbol = '🚨'
        status_text = '2nd Consecutive Miss'
    elif warning_level == 2:
        status_symbol = '⚠️'
        status_text = 'Previous Month Missed'
    elif success_days >= REQUIRED_SUCCESS_DAYS:
        status_symbol = '🏆'
        status_text = 'Monthly Target Achieved!'
    elif projected_success >= REQUIRED_SUCCESS_DAYS:
        status_symbol = '✓'
        status_text = 'On Track'
    else:
        status_symbol = '📊'
        status_text = 'In Progress'
    
    return {
        'staff_id': staff_id,
        'staff_name': user.name,
        'today': today,
        'current_month': current_month,
        'current_year': current_year,
        'days_remaining': days_remaining,
        
        # Targets
        'daily_ndp_target': daily_ndp_target,
        'daily_rdp_target': daily_rdp_target,
        'required_success_days': REQUIRED_SUCCESS_DAYS,
        
        # Today's progress
        'today_ndp': today_ndp_count,
        'today_rdp': today_rdp_count,
        'today_target_reached': today_target_reached,
        'today_reached_via': today_reached_via,
        
        # Monthly progress
        'success_days': success_days,
        'projected_success': projected_success,
        'streak': streak,
        
        # Warning system
        'warning_level': warning_level,
        'warning_message': warning_message,
        'prev_month_1_success': prev_month_1_success,
        'prev_month_2_success': prev_month_2_success,
        'prev_month_1_failed': prev_month_1_failed,
        'prev_month_2_failed': prev_month_2_failed,
        
        # Status
        'status_symbol': status_symbol,
        'status_text': status_text
    }

@router.get("/admin/staff-target-progress")
async def get_all_staff_target_progress(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user: User = Depends(get_admin_user)
):
    """
    Get target progress for ALL staff members (Admin only).
    Used for the admin dashboard tracking view.
    """
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    current_year = year or jakarta_now.year
    current_month = month or jakarta_now.month
    today = jakarta_now.strftime('%Y-%m-%d')
    current_day = jakarta_now.day
    days_in_month = 31 if current_month in [1,3,5,7,8,10,12] else 30 if current_month in [4,6,9,11] else 29 if current_year % 4 == 0 else 28
    days_remaining = days_in_month - current_day
    
    # Get targets
    targets = await get_targets()
    daily_ndp_target = targets.get('daily_ndp', 10)
    daily_rdp_target = targets.get('daily_rdp', 15)
    
    # Get all staff
    all_staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'id': 1, 'name': 1}).to_list(1000)
    
    def is_tambahan_record(record):
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get all OMSET records
    all_records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    # Build global customer first date
    global_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id = record.get('staff_id', '')
        key = (staff_id, cid_normalized, record['product_id'])
        if key not in global_customer_first_date:
            global_customer_first_date[key] = record['record_date']
    
    staff_progress_list = []
    total_success_staff = 0
    total_warning_staff = 0
    total_critical_staff = 0
    
    # Calculate for previous months (for warning detection)
    prev_month_1 = current_month - 1 if current_month > 1 else 12
    prev_year_1 = current_year if current_month > 1 else current_year - 1
    prev_month_2 = prev_month_1 - 1 if prev_month_1 > 1 else 12
    prev_year_2 = prev_year_1 if prev_month_1 > 1 else prev_year_1 - 1
    
    # Reset warning counters in January - don't look back to previous year
    # This gives staff a fresh start each year
    skip_prev_month_1 = current_month == 1  # January - skip December of last year
    skip_prev_month_2 = current_month <= 2  # January/February - skip months from last year
    
    for staff in all_staff:
        staff_id = staff['id']
        staff_name = staff['name']
        
        # Filter records for this staff
        staff_records = [r for r in all_records if r.get('staff_id') == staff_id]
        
        # Current month records
        month_str = f"{current_year}-{str(current_month).zfill(2)}"
        month_records = [r for r in staff_records if r['record_date'].startswith(month_str)]
        
        # Calculate daily NDP/RDP
        daily_ndp = {}
        daily_rdp = {}
        
        for record in month_records:
            date = record['record_date']
            if date not in daily_ndp:
                daily_ndp[date] = set()
                daily_rdp[date] = set()
            
            if is_tambahan_record(record):
                continue
            
            cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
            key = (staff_id, cid_normalized, record['product_id'])
            first_date = global_customer_first_date.get(key)
            
            if first_date:
                unique_key = f"{cid_normalized}_{record['product_id']}"
                if first_date == date:
                    daily_ndp[date].add(unique_key)
                else:
                    daily_rdp[date].add(unique_key)
        
        # Calculate today's progress
        today_ndp_count = len(daily_ndp.get(today, set()))
        today_rdp_count = len(daily_rdp.get(today, set()))
        today_target_reached = today_ndp_count >= daily_ndp_target or today_rdp_count >= daily_rdp_target
        
        # Calculate success days this month
        success_days = 0
        for date in set(daily_ndp.keys()) | set(daily_rdp.keys()):
            if len(daily_ndp.get(date, set())) >= daily_ndp_target or len(daily_rdp.get(date, set())) >= daily_rdp_target:
                success_days += 1
        
        # Calculate previous months success
        def get_month_success_for_staff(year, month):
            month_str = f"{year}-{str(month).zfill(2)}"
            month_records = [r for r in staff_records if r['record_date'].startswith(month_str)]
            
            daily_ndp_m = {}
            daily_rdp_m = {}
            
            for record in month_records:
                date = record['record_date']
                if date not in daily_ndp_m:
                    daily_ndp_m[date] = set()
                    daily_rdp_m[date] = set()
                
                if is_tambahan_record(record):
                    continue
                
                cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
                key = (staff_id, cid_normalized, record['product_id'])
                first_date = global_customer_first_date.get(key)
                
                if first_date:
                    unique_key = f"{cid_normalized}_{record['product_id']}"
                    if first_date == date:
                        daily_ndp_m[date].add(unique_key)
                    else:
                        daily_rdp_m[date].add(unique_key)
            
            success = 0
            for date in set(daily_ndp_m.keys()) | set(daily_rdp_m.keys()):
                if len(daily_ndp_m.get(date, set())) >= daily_ndp_target or len(daily_rdp_m.get(date, set())) >= daily_rdp_target:
                    success += 1
            return success
        
        prev_month_1_success = get_month_success_for_staff(prev_year_1, prev_month_1) if not skip_prev_month_1 else REQUIRED_SUCCESS_DAYS
        prev_month_2_success = get_month_success_for_staff(prev_year_2, prev_month_2) if not skip_prev_month_2 else REQUIRED_SUCCESS_DAYS
        
        prev_month_1_failed = prev_month_1_success < REQUIRED_SUCCESS_DAYS and not skip_prev_month_1
        prev_month_2_failed = prev_month_2_success < REQUIRED_SUCCESS_DAYS and not skip_prev_month_2
        
        # Determine warning level
        warning_level = 0
        if prev_month_1_failed and prev_month_2_failed:
            warning_level = 3
            total_critical_staff += 1
        elif prev_month_1_failed:
            warning_level = 2
            total_warning_staff += 1
        elif days_remaining <= 10 and success_days < REQUIRED_SUCCESS_DAYS:
            days_needed = REQUIRED_SUCCESS_DAYS - success_days
            if days_needed > days_remaining:
                warning_level = 1
            elif days_needed > 0:
                warning_level = 1
        
        # Projection
        if current_day > 0:
            projected_success = int((success_days / current_day) * days_in_month)
        else:
            projected_success = 0
        
        # Status
        if warning_level == 3:
            status_symbol = '🚨'
        elif warning_level == 2:
            status_symbol = '⚠️'
        elif success_days >= REQUIRED_SUCCESS_DAYS:
            status_symbol = '🏆'
            total_success_staff += 1
        elif projected_success >= REQUIRED_SUCCESS_DAYS:
            status_symbol = '✓'
        else:
            status_symbol = '📊'
        
        staff_progress_list.append({
            'staff_id': staff_id,
            'staff_name': staff_name,
            'today_ndp': today_ndp_count,
            'today_rdp': today_rdp_count,
            'today_target_reached': today_target_reached,
            'success_days': success_days,
            'projected_success': projected_success,
            'warning_level': warning_level,
            'prev_month_1_success': prev_month_1_success,
            'prev_month_2_success': prev_month_2_success,
            'status_symbol': status_symbol
        })
    
    # Sort by warning level (critical first), then by success days
    staff_progress_list.sort(key=lambda x: (-x['warning_level'], -x['success_days']))
    
    return {
        'year': current_year,
        'month': current_month,
        'today': today,
        'days_remaining': days_remaining,
        'required_success_days': REQUIRED_SUCCESS_DAYS,
        'daily_ndp_target': daily_ndp_target,
        'daily_rdp_target': daily_rdp_target,
        'summary': {
            'total_staff': len(all_staff),
            'success_staff': total_success_staff,
            'warning_staff': total_warning_staff,
            'critical_staff': total_critical_staff
        },
        'staff_progress': staff_progress_list
    }
