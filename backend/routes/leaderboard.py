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
    
    # Get all records for the period
    records = await db.omset_records.find(query, {'_id': 0}).to_list(500000)
    
    # Get all records for NDP/RDP calculation (need full history for first deposit detection)
    all_records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    # Build customer first deposit date map
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        key = (record['customer_id'], record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Get all staff users
    staff_users = await db.users.find({'role': 'staff'}, {'_id': 0}).to_list(100)
    staff_map = {s['id']: s for s in staff_users}
    
    # Calculate stats per staff
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
            'days_worked': set()
        }
    
    # Process records
    for record in records:
        staff_id = record['staff_id']
        if staff_id not in staff_stats:
            # Staff might have been deleted, create entry
            staff_stats[staff_id] = {
                'staff_id': staff_id,
                'staff_name': record.get('staff_name', 'Unknown'),
                'total_omset': 0,
                'total_ndp': 0,
                'total_rdp': 0,
                'today_ndp': 0,
                'today_rdp': 0,
                'days_worked': set()
            }
        
        # Add OMSET
        staff_stats[staff_id]['total_omset'] += record.get('depo_total', 0) or 0
        staff_stats[staff_id]['days_worked'].add(record['record_date'])
        
        # Check if NDP or RDP
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        is_ndp = first_date == record['record_date']
        
        if is_ndp:
            staff_stats[staff_id]['total_ndp'] += 1
            if record['record_date'] == today:
                staff_stats[staff_id]['today_ndp'] += 1
        else:
            staff_stats[staff_id]['total_rdp'] += 1
            if record['record_date'] == today:
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
