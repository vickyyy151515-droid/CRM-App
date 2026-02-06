# Bonus Calculation Routes
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import io
import pandas as pd

from .deps import get_db, get_admin_user, User
from utils.helpers import normalize_customer_id, get_jakarta_now

router = APIRouter(tags=["Bonus Calculation"])

# ==================== DEFAULT CONFIGURATION ====================

DEFAULT_BONUS_CONFIG = {
    'main_tiers': [
        {'threshold': 280000000, 'bonus': 100},
        {'threshold': 210000000, 'bonus': 75},
        {'threshold': 140000000, 'bonus': 50},
        {'threshold': 100000000, 'bonus': 30},
        {'threshold': 70000000, 'bonus': 20},
    ],
    'ndp_tiers': [
        {'min': 11, 'max': None, 'bonus': 5.0, 'label': '>10'},
        {'min': 8, 'max': 10, 'bonus': 2.5, 'label': '8-10'},
    ],
    'rdp_tiers': [
        {'min': 16, 'max': None, 'bonus': 5.0, 'label': '>15'},
        {'min': 12, 'max': 15, 'bonus': 2.5, 'label': '12-15'},
    ]
}

# ==================== PYDANTIC MODELS ====================

class MainBonusTier(BaseModel):
    threshold: int
    bonus: float

class DailyBonusTier(BaseModel):
    min: int
    max: Optional[int] = None
    bonus: float
    label: str

class BonusConfigUpdate(BaseModel):
    main_tiers: List[dict]
    ndp_tiers: List[dict]
    rdp_tiers: List[dict]

# ==================== HELPER FUNCTIONS ====================

async def get_bonus_config():
    """Get bonus configuration from database or return defaults"""
    db = get_db()
    config = await db.settings.find_one({'key': 'bonus_config'}, {'_id': 0})
    if config:
        return config['value']
    return DEFAULT_BONUS_CONFIG

def calculate_main_bonus_with_config(total_nominal: float, main_tiers: list) -> float:
    """Calculate main bonus based on monthly total nominal"""
    sorted_tiers = sorted(main_tiers, key=lambda x: x['threshold'], reverse=True)
    for tier in sorted_tiers:
        if total_nominal >= tier['threshold']:
            return tier['bonus']
    return 0

def calculate_daily_ndp_bonus_with_config(ndp_count: int, ndp_tiers: list) -> float:
    """Calculate daily NDP bonus"""
    for tier in ndp_tiers:
        min_val = tier['min']
        max_val = tier.get('max')
        if max_val is None:
            if ndp_count >= min_val:
                return tier['bonus']
        else:
            if min_val <= ndp_count <= max_val:
                return tier['bonus']
    return 0

def calculate_daily_rdp_bonus_with_config(rdp_count: int, rdp_tiers: list) -> float:
    """Calculate daily RDP bonus"""
    for tier in rdp_tiers:
        min_val = tier['min']
        max_val = tier.get('max')
        if max_val is None:
            if rdp_count >= min_val:
                return tier['bonus']
        else:
            if min_val <= rdp_count <= max_val:
                return tier['bonus']
    return 0

# ==================== BONUS ENDPOINTS ====================

@router.get("/bonus-calculation/config")
async def get_bonus_calculation_config(user: User = Depends(get_admin_user)):
    """Get current bonus configuration"""
    config = await get_bonus_config()
    return config

@router.put("/bonus-calculation/config")
async def update_bonus_calculation_config(
    config: BonusConfigUpdate,
    user: User = Depends(get_admin_user)
):
    """Update bonus configuration"""
    db = get_db()
    config_doc = {
        'key': 'bonus_config',
        'value': {
            'main_tiers': config.main_tiers,
            'ndp_tiers': config.ndp_tiers,
            'rdp_tiers': config.rdp_tiers
        },
        'updated_at': get_jakarta_now().isoformat(),
        'updated_by': user.id,
        'updated_by_name': user.name
    }
    
    await db.settings.update_one(
        {'key': 'bonus_config'},
        {'$set': config_doc},
        upsert=True
    )
    
    return {'message': 'Bonus configuration updated successfully', 'config': config_doc['value']}

@router.post("/bonus-calculation/config/reset")
async def reset_bonus_calculation_config(user: User = Depends(get_admin_user)):
    """Reset bonus configuration to defaults"""
    db = get_db()
    await db.settings.delete_one({'key': 'bonus_config'})
    return {'message': 'Bonus configuration reset to defaults', 'config': DEFAULT_BONUS_CONFIG}

@router.get("/bonus-calculation/data")
async def get_bonus_calculation_data(
    year: int = None,
    month: int = None,
    staff_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Calculate bonus for all staff for a specific month"""
    db = get_db()
    
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    month_str = f"{year}-{str(month).zfill(2)}"
    
    query = {'record_date': {'$regex': f'^{month_str}'}}
    if staff_id:
        query['staff_id'] = staff_id
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    all_time_records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    def is_tambahan_record(record):
        """Check if record has 'tambahan' in keterangan field"""
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Build STAFF-SPECIFIC customer first deposit map (SINGLE SOURCE OF TRUTH)
    # Key: (staff_id, customer_id_normalized, product_id) -> first_date
    # IMPORTANT: Exclude records with "tambahan" from first_date calculation
    staff_customer_first_date = {}
    for record in sorted(all_time_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        staff_id_rec = record['staff_id']
        key = (staff_id_rec, cid_normalized, pid)
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    staff_data = {}
    for record in records:
        sid = record['staff_id']
        sname = record['staff_name']
        date = record['record_date']
        
        if sid not in staff_data:
            staff_data[sid] = {
                'staff_id': sid,
                'staff_name': sname,
                'total_nominal': 0,
                'daily_stats': {},
                'daily_rdp_pairs': {},  # Track unique (customer, product) per day
                'daily_ndp_pairs': {},  # Track unique (customer, product) per day
            }
        
        nominal = record.get('depo_total', 0) or record.get('nominal', 0) or 0
        staff_data[sid]['total_nominal'] += nominal
        
        if date not in staff_data[sid]['daily_stats']:
            staff_data[sid]['daily_stats'][date] = {'ndp': 0, 'rdp': 0}
            staff_data[sid]['daily_rdp_pairs'][date] = set()
            staff_data[sid]['daily_ndp_pairs'][date] = set()
        
        # Use normalized customer_id for comparison
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        staff_key = (sid, cid_normalized, pid)
        first_date = staff_customer_first_date.get(staff_key)
        
        # Track by (customer, product) pair — each product counted independently
        customer_product_pair = (cid_normalized, pid)
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            if customer_product_pair not in staff_data[sid]['daily_rdp_pairs'][date]:
                staff_data[sid]['daily_rdp_pairs'][date].add(customer_product_pair)
                staff_data[sid]['daily_stats'][date]['rdp'] += 1
        elif first_date == date:
            if customer_product_pair not in staff_data[sid]['daily_ndp_pairs'][date]:
                staff_data[sid]['daily_ndp_pairs'][date].add(customer_product_pair)
                staff_data[sid]['daily_stats'][date]['ndp'] += 1
        else:
            if customer_product_pair not in staff_data[sid]['daily_rdp_pairs'][date]:
                staff_data[sid]['daily_rdp_pairs'][date].add(customer_product_pair)
                staff_data[sid]['daily_stats'][date]['rdp'] += 1
    
    bonus_config = await get_bonus_config()
    main_tiers = bonus_config['main_tiers']
    ndp_tiers = bonus_config['ndp_tiers']
    rdp_tiers = bonus_config['rdp_tiers']
    
    result = []
    for sid, data in staff_data.items():
        main_bonus = calculate_main_bonus_with_config(data['total_nominal'], main_tiers)
        
        ndp_bonus_total = 0
        rdp_bonus_total = 0
        ndp_bonus_days = {}
        rdp_bonus_days = {}
        
        for tier in ndp_tiers:
            ndp_bonus_days[tier['label']] = 0
        for tier in rdp_tiers:
            rdp_bonus_days[tier['label']] = 0
        
        daily_breakdown = []
        
        for date, stats in sorted(data['daily_stats'].items()):
            ndp = stats['ndp']
            rdp = stats['rdp']
            
            ndp_daily_bonus = calculate_daily_ndp_bonus_with_config(ndp, ndp_tiers)
            rdp_daily_bonus = calculate_daily_rdp_bonus_with_config(rdp, rdp_tiers)
            
            ndp_bonus_total += ndp_daily_bonus
            rdp_bonus_total += rdp_daily_bonus
            
            for tier in ndp_tiers:
                min_val = tier['min']
                max_val = tier.get('max')
                if max_val is None:
                    if ndp >= min_val:
                        ndp_bonus_days[tier['label']] += 1
                        break
                else:
                    if min_val <= ndp <= max_val:
                        ndp_bonus_days[tier['label']] += 1
                        break
            
            for tier in rdp_tiers:
                min_val = tier['min']
                max_val = tier.get('max')
                if max_val is None:
                    if rdp >= min_val:
                        rdp_bonus_days[tier['label']] += 1
                        break
                else:
                    if min_val <= rdp <= max_val:
                        rdp_bonus_days[tier['label']] += 1
                        break
            
            daily_breakdown.append({
                'date': date,
                'ndp': ndp,
                'rdp': rdp,
                'ndp_bonus': ndp_daily_bonus,
                'rdp_bonus': rdp_daily_bonus
            })
        
        total_bonus = main_bonus + ndp_bonus_total + rdp_bonus_total
        
        result.append({
            'staff_id': sid,
            'staff_name': data['staff_name'],
            'total_nominal': data['total_nominal'],
            'main_bonus': main_bonus,
            'ndp_bonus_total': ndp_bonus_total,
            'rdp_bonus_total': rdp_bonus_total,
            'total_bonus': total_bonus,
            'ndp_bonus_days': ndp_bonus_days,
            'rdp_bonus_days': rdp_bonus_days,
            'daily_breakdown': daily_breakdown,
            'days_worked': len(data['daily_stats'])
        })
    
    result.sort(key=lambda x: x['total_bonus'], reverse=True)
    
    grand_total = {
        'total_nominal': sum(s['total_nominal'] for s in result),
        'main_bonus': sum(s['main_bonus'] for s in result),
        'ndp_bonus_total': sum(s['ndp_bonus_total'] for s in result),
        'rdp_bonus_total': sum(s['rdp_bonus_total'] for s in result),
        'total_bonus': sum(s['total_bonus'] for s in result)
    }
    
    return {
        'year': year,
        'month': month,
        'staff_bonuses': result,
        'grand_total': grand_total,
        'bonus_config': bonus_config
    }

@router.get("/bonus-calculation/export")
async def export_bonus_calculation(
    year: int = None,
    month: int = None,
    user: User = Depends(get_admin_user)
):
    """Export bonus calculation to Excel"""
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    bonus_data = await get_bonus_calculation_data(year, month, None, user)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_data = []
        for staff in bonus_data['staff_bonuses']:
            summary_data.append({
                'Staff': staff['staff_name'],
                'Total Nominal (Rp)': staff['total_nominal'],
                'Main Bonus ($)': staff['main_bonus'],
                'NDP Bonus ($)': staff['ndp_bonus_total'],
                'RDP Bonus ($)': staff['rdp_bonus_total'],
                'Total Bonus ($)': staff['total_bonus'],
                'Days Worked': staff['days_worked']
            })
        
        summary_data.append({
            'Staff': 'GRAND TOTAL',
            'Total Nominal (Rp)': bonus_data['grand_total']['total_nominal'],
            'Main Bonus ($)': bonus_data['grand_total']['main_bonus'],
            'NDP Bonus ($)': bonus_data['grand_total']['ndp_bonus_total'],
            'RDP Bonus ($)': bonus_data['grand_total']['rdp_bonus_total'],
            'Total Bonus ($)': bonus_data['grand_total']['total_bonus'],
            'Days Worked': '-'
        })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Bonus Summary', index=False)
        
        for staff in bonus_data['staff_bonuses']:
            if staff['daily_breakdown']:
                daily_df = pd.DataFrame(staff['daily_breakdown'])
                daily_df.columns = ['Date', 'NDP', 'RDP', 'NDP Bonus ($)', 'RDP Bonus ($)']
                sheet_name = staff['staff_name'][:31]
                daily_df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    filename = f"Bonus_Calculation_{month_names[month-1]}_{year}.xlsx"
    
    temp_path = f"/tmp/{filename}"
    with open(temp_path, 'wb') as f:
        f.write(output.getvalue())
    
    return FileResponse(
        path=temp_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=filename
    )

# ==================== STAFF BONUS ENDPOINT (Self-view only) ====================

from .auth import get_current_user as get_any_user

@router.get("/bonus-calculation/my-bonus")
async def get_my_bonus_data(
    year: int = None,
    month: int = None,
    user: User = Depends(get_any_user)
):
    """Get bonus data for the currently logged-in staff member (staff can only see their own bonus)"""
    db = get_db()
    
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    month_str = f"{year}-{str(month).zfill(2)}"
    
    # Only fetch records for this specific staff member
    query = {
        'record_date': {'$regex': f'^{month_str}'},
        'staff_id': user.id
    }
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Need all-time records to determine NDP vs RDP
    all_time_records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    def is_tambahan_record(record):
        """Check if record has 'tambahan' in keterangan field"""
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Build STAFF-SPECIFIC customer first deposit map (SINGLE SOURCE OF TRUTH)
    # Since this endpoint is for a single staff, we use (staff_id, customer_id, product_id)
    staff_customer_first_date = {}
    for record in sorted(all_time_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        staff_id_rec = record['staff_id']
        key = (staff_id_rec, cid_normalized, pid)
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Calculate staff's bonus data
    total_nominal = 0
    daily_stats = {}
    daily_rdp_pairs = {}
    daily_ndp_pairs = {}
    
    for record in records:
        date = record['record_date']
        sid = record['staff_id']
        
        nominal = record.get('depo_total', 0) or record.get('nominal', 0) or 0
        total_nominal += nominal
        
        if date not in daily_stats:
            daily_stats[date] = {'ndp': 0, 'rdp': 0}
            daily_rdp_pairs[date] = set()
            daily_ndp_pairs[date] = set()
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        staff_key = (sid, cid_normalized, pid)
        first_date = staff_customer_first_date.get(staff_key)
        
        # Track by (customer, product) pair
        customer_product_pair = (cid_normalized, pid)
        
        if is_tambahan_record(record):
            if customer_product_pair not in daily_rdp_pairs[date]:
                daily_rdp_pairs[date].add(customer_product_pair)
                daily_stats[date]['rdp'] += 1
        elif first_date == date:
            if customer_product_pair not in daily_ndp_pairs[date]:
                daily_ndp_pairs[date].add(customer_product_pair)
                daily_stats[date]['ndp'] += 1
        else:
            if customer_product_pair not in daily_rdp_pairs[date]:
                daily_rdp_pairs[date].add(customer_product_pair)
                daily_stats[date]['rdp'] += 1
    
    bonus_config = await get_bonus_config()
    main_tiers = bonus_config['main_tiers']
    ndp_tiers = bonus_config['ndp_tiers']
    rdp_tiers = bonus_config['rdp_tiers']
    
    main_bonus = calculate_main_bonus_with_config(total_nominal, main_tiers)
    
    ndp_bonus_total = 0
    rdp_bonus_total = 0
    ndp_bonus_days = {}
    rdp_bonus_days = {}
    
    for tier in ndp_tiers:
        ndp_bonus_days[tier['label']] = 0
    for tier in rdp_tiers:
        rdp_bonus_days[tier['label']] = 0
    
    daily_breakdown = []
    
    for date, stats in sorted(daily_stats.items()):
        ndp = stats['ndp']
        rdp = stats['rdp']
        
        ndp_daily_bonus = calculate_daily_ndp_bonus_with_config(ndp, ndp_tiers)
        rdp_daily_bonus = calculate_daily_rdp_bonus_with_config(rdp, rdp_tiers)
        
        ndp_bonus_total += ndp_daily_bonus
        rdp_bonus_total += rdp_daily_bonus
        
        for tier in ndp_tiers:
            min_val = tier['min']
            max_val = tier.get('max')
            if max_val is None:
                if ndp >= min_val:
                    ndp_bonus_days[tier['label']] += 1
                    break
            else:
                if min_val <= ndp <= max_val:
                    ndp_bonus_days[tier['label']] += 1
                    break
        
        for tier in rdp_tiers:
            min_val = tier['min']
            max_val = tier.get('max')
            if max_val is None:
                if rdp >= min_val:
                    rdp_bonus_days[tier['label']] += 1
                    break
            else:
                if min_val <= rdp <= max_val:
                    rdp_bonus_days[tier['label']] += 1
                    break
        
        daily_breakdown.append({
            'date': date,
            'ndp': ndp,
            'rdp': rdp,
            'ndp_bonus': ndp_daily_bonus,
            'rdp_bonus': rdp_daily_bonus
        })
    
    total_bonus = main_bonus + ndp_bonus_total + rdp_bonus_total
    
    return {
        'year': year,
        'month': month,
        'staff_id': user.id,
        'staff_name': user.name,
        'total_nominal': total_nominal,
        'main_bonus': main_bonus,
        'ndp_bonus_total': ndp_bonus_total,
        'rdp_bonus_total': rdp_bonus_total,
        'total_bonus': total_bonus,
        'ndp_bonus_days': ndp_bonus_days,
        'rdp_bonus_days': rdp_bonus_days,
        'daily_breakdown': daily_breakdown,
        'days_worked': len(daily_stats),
        'bonus_config': bonus_config  # Include config so staff can see how bonus is calculated
    }
