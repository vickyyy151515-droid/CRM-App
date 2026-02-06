# Report CRM Routes
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from typing import Optional
import io
import pandas as pd
import jwt
import os

from .deps import get_db, get_admin_user, get_current_user, User
from utils.helpers import get_jakarta_now, normalize_customer_id

router = APIRouter(tags=["Report CRM"])

JWT_SECRET = os.environ.get("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = "HS256"

# ==================== REPORT CRM ENDPOINTS ====================

@router.get("/report-crm/data")
async def get_report_crm_data(
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    year: int = None,
    month: int = None,
    user: User = Depends(get_admin_user)
):
    """Get comprehensive report data for Report CRM page"""
    db = get_db()
    
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    base_query = {}
    if product_id:
        base_query['product_id'] = product_id
    if staff_id:
        base_query['staff_id'] = staff_id
    
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    year_query = {**base_query, 'record_date': {'$gte': year_start, '$lte': year_end}}
    
    all_records = await db.omset_records.find(year_query, {'_id': 0}).to_list(100000)
    
    all_time_query = {}
    if product_id:
        all_time_query['product_id'] = product_id
    all_time_records = await db.omset_records.find(all_time_query, {'_id': 0}).to_list(500000)
    
    # ==================== HELPER FUNCTIONS ====================
    
    def get_normalized_cid(record):
        """Get normalized customer ID from record - handles both stored and computed"""
        stored = record.get('customer_id_normalized')
        if stored and str(stored).strip():  # Must be non-empty string
            return str(stored).strip().lower()
        return normalize_customer_id(record.get('customer_id', ''))
    
    def is_tambahan_record(record):
        """Check if record has 'tambahan' in keterangan field"""
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # ==================== BUILD CUSTOMER FIRST DATE LOOKUP ====================
    # Key: (customer_id_normalized, product_id) -> first deposit date
    # IMPORTANT: Exclude "tambahan" records from first_date calculation
    
    customer_first_date = {}
    for record in sorted(all_time_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = get_normalized_cid(record)
        pid = record['product_id']
        key = (cid_normalized, pid)
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # ==================== UNIFIED NDP/RDP DETERMINATION ====================
    # NDP = Customer's FIRST deposit for THIS PRODUCT matches record_date (AND not tambahan)
    # RDP = Not first deposit for this product OR is tambahan
    
    def is_ndp_record(record):
        """Determine if record counts as NDP"""
        if is_tambahan_record(record):
            return False
        cid_normalized = get_normalized_cid(record)
        key = (cid_normalized, record['product_id'])
        first_date = customer_first_date.get(key)
        return first_date == record['record_date']
    
    # ==================== PRE-COMPUTE NDP/RDP FOR EACH RECORD ====================
    # This ensures ALL sections use EXACTLY the same determination
    # Also compute unique tracking to count each (customer, product, date) only ONCE
    
    # Tracking: (product_id, date, customer_id_normalized) -> is_ndp (True/False)
    # This ensures if same customer deposits to same product on same date multiple times,
    # they are only counted ONCE (and consistently as either NDP or RDP)
    
    unique_deposits = {}  # key: (pid, date, cid_normalized) -> {'is_ndp': bool, 'records': [record, ...]}
    
    for record in all_records:
        cid_normalized = get_normalized_cid(record)
        pid = record['product_id']
        date = record['record_date']
        key = (pid, date, cid_normalized)
        
        if key not in unique_deposits:
            unique_deposits[key] = {
                'is_ndp': is_ndp_record(record),
                'records': []
            }
        unique_deposits[key]['records'].append(record)
    
    # ==================== BUILD ALL REPORT SECTIONS ====================
    # ALL sections will use the same unique_deposits lookup for consistency
    
    # --- YEARLY DATA ---
    yearly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        
        new_id = 0
        rdp = 0
        total_form = 0
        nominal = 0
        
        for (pid, date, cid), deposit_info in unique_deposits.items():
            if not date.startswith(month_str):
                continue
            
            if deposit_info['is_ndp']:
                new_id += 1
            else:
                rdp += 1
            
            # Sum nominal from all records in this unique deposit
            for record in deposit_info['records']:
                total_form += 1
                nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        yearly_data.append({
            'month': m,
            'new_id': new_id,
            'rdp': rdp,
            'total_form': total_form,
            'nominal': nominal
        })
    
    # --- MONTHLY DATA (daily breakdown for all months) ---
    monthly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        
        # Group by date within this month
        date_data = {}
        for (pid, date, cid), deposit_info in unique_deposits.items():
            if not date.startswith(month_str):
                continue
            
            if date not in date_data:
                date_data[date] = {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            
            if deposit_info['is_ndp']:
                date_data[date]['new_id'] += 1
            else:
                date_data[date]['rdp'] += 1
            
            for record in deposit_info['records']:
                date_data[date]['total_form'] += 1
                date_data[date]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        for date, data in sorted(date_data.items()):
            monthly_data.append({
                'month': m,
                'date': date,
                'new_id': data['new_id'],
                'rdp': data['rdp'],
                'total_form': data['total_form'],
                'nominal': data['nominal']
            })
    
    # --- MONTHLY BY STAFF ---
    CRM_EFFICIENCY_TARGET = 278000000
    monthly_by_staff = []
    
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        
        staff_data = {}
        
        for (pid, date, cid), deposit_info in unique_deposits.items():
            if not date.startswith(month_str):
                continue
            
            # For staff attribution, use the FIRST record's staff_id
            # (in case of duplicates, attribute to whoever entered it first)
            first_record = deposit_info['records'][0]
            sid = first_record['staff_id']
            sname = first_record['staff_name']
            
            if sid not in staff_data:
                staff_data[sid] = {
                    'staff_id': sid,
                    'staff_name': sname,
                    'new_id': 0,
                    'rdp': 0,
                    'total_form': 0,
                    'nominal': 0
                }
            
            if deposit_info['is_ndp']:
                staff_data[sid]['new_id'] += 1
            else:
                staff_data[sid]['rdp'] += 1
            
            for record in deposit_info['records']:
                staff_data[sid]['total_form'] += 1
                staff_data[sid]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        staff_list = []
        for sid, data in staff_data.items():
            efficiency = (data['nominal'] / CRM_EFFICIENCY_TARGET) * 100 if CRM_EFFICIENCY_TARGET > 0 else 0
            staff_list.append({
                **data,
                'crm_efficiency': round(efficiency, 2)
            })
        
        staff_list.sort(key=lambda x: x['nominal'], reverse=True)
        
        month_totals = {
            'new_id': sum(s['new_id'] for s in staff_list),
            'rdp': sum(s['rdp'] for s in staff_list),
            'total_form': sum(s['total_form'] for s in staff_list),
            'nominal': sum(s['nominal'] for s in staff_list)
        }
        month_totals['crm_efficiency'] = round((month_totals['nominal'] / CRM_EFFICIENCY_TARGET) * 100, 2) if CRM_EFFICIENCY_TARGET > 0 else 0
        
        monthly_by_staff.append({
            'month': m,
            'staff': staff_list,
            'totals': month_totals
        })
    
    # --- DAILY BY STAFF (for selected month) ---
    selected_month_str = f"{year}-{str(month).zfill(2)}"
    
    # Build nested structure: staff -> products -> daily
    staff_daily_data = {}
    
    for (pid, date, cid), deposit_info in unique_deposits.items():
        if not date.startswith(selected_month_str):
            continue
        
        first_record = deposit_info['records'][0]
        sid = first_record['staff_id']
        sname = first_record['staff_name']
        pname = first_record['product_name']
        
        if sid not in staff_daily_data:
            staff_daily_data[sid] = {
                'staff_id': sid,
                'staff_name': sname,
                'products': {},
                'totals': {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            }
        
        if pid not in staff_daily_data[sid]['products']:
            staff_daily_data[sid]['products'][pid] = {
                'product_id': pid,
                'product_name': pname,
                'daily': {},
                'totals': {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            }
        
        if date not in staff_daily_data[sid]['products'][pid]['daily']:
            staff_daily_data[sid]['products'][pid]['daily'][date] = {
                'date': date,
                'new_id': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
        
        # Update counts
        if deposit_info['is_ndp']:
            staff_daily_data[sid]['totals']['new_id'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['new_id'] += 1
            staff_daily_data[sid]['products'][pid]['daily'][date]['new_id'] += 1
        else:
            staff_daily_data[sid]['totals']['rdp'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['rdp'] += 1
            staff_daily_data[sid]['products'][pid]['daily'][date]['rdp'] += 1
        
        # Sum nominal from all records
        for record in deposit_info['records']:
            nom = record.get('depo_total', 0) or record.get('nominal', 0) or 0
            staff_daily_data[sid]['totals']['total_form'] += 1
            staff_daily_data[sid]['totals']['nominal'] += nom
            staff_daily_data[sid]['products'][pid]['totals']['total_form'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['nominal'] += nom
            staff_daily_data[sid]['products'][pid]['daily'][date]['total_form'] += 1
            staff_daily_data[sid]['products'][pid]['daily'][date]['nominal'] += nom
    
    # Convert to list format
    daily_by_staff = []
    for sid, staff_data in staff_daily_data.items():
        products_list = []
        for pid, product_data in staff_data['products'].items():
            daily_list = sorted(product_data['daily'].values(), key=lambda x: x['date'])
            products_list.append({
                'product_id': product_data['product_id'],
                'product_name': product_data['product_name'],
                'daily': daily_list,
                'totals': product_data['totals']
            })
        products_list.sort(key=lambda x: x['totals']['nominal'], reverse=True)
        
        daily_by_staff.append({
            'staff_id': staff_data['staff_id'],
            'staff_name': staff_data['staff_name'],
            'products': products_list,
            'totals': staff_data['totals']
        })
    
    daily_by_staff.sort(key=lambda x: x['totals']['nominal'], reverse=True)
    
    # --- DAILY DATA (simple date list for selected month) ---
    daily_data = []
    date_totals = {}
    
    for (pid, date, cid), deposit_info in unique_deposits.items():
        if not date.startswith(selected_month_str):
            continue
        
        if date not in date_totals:
            date_totals[date] = {'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
        
        if deposit_info['is_ndp']:
            date_totals[date]['new_id'] += 1
        else:
            date_totals[date]['rdp'] += 1
        
        for record in deposit_info['records']:
            date_totals[date]['total_form'] += 1
            date_totals[date]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    for date, data in sorted(date_totals.items()):
        daily_data.append({
            'date': date,
            'new_id': data['new_id'],
            'rdp': data['rdp'],
            'total_form': data['total_form'],
            'nominal': data['nominal']
        })
    
    # --- STAFF PERFORMANCE (yearly totals per staff) ---
    staff_perf_data = {}
    
    for (pid, date, cid), deposit_info in unique_deposits.items():
        first_record = deposit_info['records'][0]
        sid = first_record['staff_id']
        sname = first_record['staff_name']
        
        if sid not in staff_perf_data:
            staff_perf_data[sid] = {
                'staff_id': sid,
                'staff_name': sname,
                'new_id': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
        
        if deposit_info['is_ndp']:
            staff_perf_data[sid]['new_id'] += 1
        else:
            staff_perf_data[sid]['rdp'] += 1
        
        for record in deposit_info['records']:
            staff_perf_data[sid]['total_form'] += 1
            staff_perf_data[sid]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    staff_performance = sorted(staff_perf_data.values(), key=lambda x: x['nominal'], reverse=True)
    
    # --- DEPOSIT TIERS ---
    customer_deposit_counts = {}
    for record in all_records:
        cid = record['customer_id']
        if cid not in customer_deposit_counts:
            customer_deposit_counts[cid] = 0
        customer_deposit_counts[cid] += 1
    
    deposit_tiers = {'2x': 0, '3x': 0, '4x_plus': 0}
    for cid, count in customer_deposit_counts.items():
        if count == 2:
            deposit_tiers['2x'] += 1
        elif count == 3:
            deposit_tiers['3x'] += 1
        elif count >= 4:
            deposit_tiers['4x_plus'] += 1
    
    return {
        'yearly': yearly_data,
        'monthly': monthly_data,
        'monthly_by_staff': monthly_by_staff,
        'daily': daily_data,
        'daily_by_staff': daily_by_staff,
        'staff_performance': staff_performance,
        'deposit_tiers': deposit_tiers,
        'crm_efficiency_target': 278000000
    }

@router.get("/report-crm/export")
async def export_report_crm(
    request: Request,
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    year: int = None,
    token: Optional[str] = None
):
    """Export Report CRM data to Excel"""
    db = get_db()
    
    # Support token in query params for download links
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user_data:
                raise HTTPException(status_code=401, detail="User not found")
            user = User(**user_data)
            if user.role not in ['admin', 'master_admin']:
                raise HTTPException(status_code=403, detail="Admin access required")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        # Fall back to header-based auth
        from fastapi.security import HTTPBearer
        security = HTTPBearer()
        credentials = await security(request)
        user = await get_admin_user(await get_current_user(credentials))
    
    if year is None:
        year = get_jakarta_now().year
    
    report_data = await get_report_crm_data(product_id, staff_id, year, 1, user)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        yearly_df = pd.DataFrame(report_data['yearly'])
        yearly_df['month_name'] = yearly_df['month'].apply(lambda x: ['JAN', 'FEB', 'MAR', 'APR', 'MEI', 'JUN', 'JUL', 'AUG', 'SEPT', 'OCT', 'NOV', 'DEC'][x-1])
        yearly_df = yearly_df[['month_name', 'new_id', 'rdp', 'total_form', 'nominal']]
        yearly_df.columns = ['BULAN', 'NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'NOMINAL']
        
        totals = yearly_df[['NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'NOMINAL']].sum()
        totals_row = pd.DataFrame([['TOTAL', totals['NEW ID (NDP)'], totals['ID RDP'], totals['TOTAL FORM'], totals['NOMINAL']]], 
                                   columns=yearly_df.columns)
        yearly_df = pd.concat([yearly_df, totals_row], ignore_index=True)
        yearly_df.to_excel(writer, sheet_name='YEARLY', index=False)
        
        if report_data['monthly']:
            monthly_df = pd.DataFrame(report_data['monthly'])
            monthly_df = monthly_df[['date', 'new_id', 'rdp', 'total_form', 'nominal']]
            monthly_df.columns = ['TANGGAL', 'NEW ID', 'ID RDP', 'TOTAL FORM', 'NOMINAL']
            monthly_df.to_excel(writer, sheet_name='MONTHLY', index=False)
        
        if report_data['staff_performance']:
            staff_df = pd.DataFrame(report_data['staff_performance'])
            staff_df = staff_df[['staff_name', 'new_id', 'rdp', 'total_form', 'nominal']]
            staff_df.columns = ['STAFF', 'NEW ID (NDP)', 'ID RDP', 'TOTAL FORM', 'TOTAL OMSET']
            staff_df.to_excel(writer, sheet_name='STAFF PERFORMANCE', index=False)
        
        tiers_df = pd.DataFrame([
            {'Tier': '2x Deposit', 'Count': report_data['deposit_tiers']['2x']},
            {'Tier': '3x Deposit', 'Count': report_data['deposit_tiers']['3x']},
            {'Tier': '>4x Deposit', 'Count': report_data['deposit_tiers']['4x_plus']}
        ])
        tiers_df.to_excel(writer, sheet_name='DEPOSIT TIERS', index=False)
    
    output.seek(0)
    
    temp_path = f"/tmp/report_crm_{year}.xlsx"
    with open(temp_path, 'wb') as f:
        f.write(output.getvalue())
    
    return FileResponse(
        path=temp_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=f"Report_CRM_{year}.xlsx"
    )
