# Leaderboard and Targets Routes
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .deps import get_db, get_current_user, get_admin_user, get_jakarta_now, User

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

def normalize_customer_id(customer_id: str) -> str:
    """Normalize customer ID for consistent comparison"""
    if not customer_id:
        return ""
    return customer_id.strip().lower()

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
    
    # Global customer_first_date (for overall totals)
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # STAFF-SPECIFIC customer_first_date (for staff-level NDP/RDP)
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
    
    # Calculate stats for each staff - with unique RDP customers per day
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
            'daily_ndp_customers': {},  # {date: set(customer_ids)}
            'daily_rdp_customers': {}   # {date: set(customer_ids)}
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
                'daily_ndp_customers': {},
                'daily_rdp_customers': {}
            }
        
        staff_stats[staff_id]['total_omset'] += record.get('depo_total', 0) or 0
        staff_stats[staff_id]['days_worked'].add(date)
        
        # Initialize daily tracking sets
        if date not in staff_stats[staff_id]['daily_ndp_customers']:
            staff_stats[staff_id]['daily_ndp_customers'][date] = set()
            staff_stats[staff_id]['daily_rdp_customers'][date] = set()
        
        # Check NDP/RDP - use STAFF-SPECIFIC first_date
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_key = (staff_id, cid_normalized, record['product_id'])
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            # RDP - count unique per day
            if cid_normalized not in staff_stats[staff_id]['daily_rdp_customers'][date]:
                staff_stats[staff_id]['daily_rdp_customers'][date].add(cid_normalized)
                staff_stats[staff_id]['total_rdp'] += 1
        elif staff_first_date == date:
            # NDP - count unique per day
            if cid_normalized not in staff_stats[staff_id]['daily_ndp_customers'][date]:
                staff_stats[staff_id]['daily_ndp_customers'][date].add(cid_normalized)
                staff_stats[staff_id]['total_ndp'] += 1
        else:
            # RDP - count unique per day
            if cid_normalized not in staff_stats[staff_id]['daily_rdp_customers'][date]:
                staff_stats[staff_id]['daily_rdp_customers'][date].add(cid_normalized)
                staff_stats[staff_id]['total_rdp'] += 1
    
    # Calculate today's stats separately
    today_ndp_customers = {}  # {staff_id: set(customer_ids)}
    today_rdp_customers = {}  # {staff_id: set(customer_ids)}
    
    for record in today_records:
        staff_id = record['staff_id']
        
        if staff_id not in today_ndp_customers:
            today_ndp_customers[staff_id] = set()
            today_rdp_customers[staff_id] = set()
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        # Use STAFF-SPECIFIC first_date for today's stats too
        staff_key = (staff_id, cid_normalized, record['product_id'])
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            if cid_normalized not in today_rdp_customers[staff_id]:
                today_rdp_customers[staff_id].add(cid_normalized)
                if staff_id in staff_stats:
                    staff_stats[staff_id]['today_rdp'] += 1
        elif staff_first_date == today:
            if cid_normalized not in today_ndp_customers[staff_id]:
                today_ndp_customers[staff_id].add(cid_normalized)
                if staff_id in staff_stats:
                    staff_stats[staff_id]['today_ndp'] += 1
        else:
            if cid_normalized not in today_rdp_customers[staff_id]:
                today_rdp_customers[staff_id].add(cid_normalized)
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
