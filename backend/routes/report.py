# Report CRM Routes
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import io
import pandas as pd

from .deps import get_db, get_admin_user, get_jakarta_now, User

router = APIRouter(tags=["Report CRM"])

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
    
    # Helper function to normalize customer ID for consistent NDP/RDP comparison
    def normalize_customer_id(customer_id: str) -> str:
        if not customer_id:
            return ""
        return customer_id.strip().lower()
    
    # Rebuild customer_first_date with normalized IDs
    customer_first_date = {}
    for record in sorted(all_time_records, key=lambda x: x['record_date']):
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        key = (cid_normalized, pid)
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    yearly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        new_id = 0
        rdp = 0
        total_form = len(month_records)
        nominal = 0
        
        # Track unique NDP/RDP customers per month
        month_ndp_customers = set()
        month_rdp_customers = set()
        
        for record in month_records:
            cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record['product_id'])
            first_date = customer_first_date.get(key)
            
            if first_date and first_date.startswith(month_str) and first_date == record['record_date']:
                # NDP - count unique customers
                if cid_normalized not in month_ndp_customers:
                    month_ndp_customers.add(cid_normalized)
                    new_id += 1
            elif first_date and first_date < record['record_date']:
                # RDP - count unique customers per month (NEW LOGIC)
                if cid_normalized not in month_rdp_customers:
                    month_rdp_customers.add(cid_normalized)
                    rdp += 1
            nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        yearly_data.append({
            'month': m,
            'new_id': new_id,
            'rdp': rdp,
            'total_form': total_form,
            'nominal': nominal
        })
    
    monthly_data = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        daily_groups = {}
        for record in month_records:
            date = record['record_date']
            if date not in daily_groups:
                daily_groups[date] = []
            daily_groups[date].append(record)
        
        for date, records in sorted(daily_groups.items()):
            new_id = 0
            rdp = 0
            nominal = 0
            
            for record in records:
                key = (record['customer_id'], record['product_id'])
                first_date = customer_first_date.get(key)
                if first_date == date:
                    new_id += 1
                else:
                    rdp += 1
                nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
            
            monthly_data.append({
                'month': m,
                'date': date,
                'new_id': new_id,
                'rdp': rdp,
                'total_form': len(records),
                'nominal': nominal
            })
    
    CRM_EFFICIENCY_TARGET = 278000000
    monthly_by_staff = []
    for m in range(1, 13):
        month_str = f"{year}-{str(m).zfill(2)}"
        month_records = [r for r in all_records if r['record_date'].startswith(month_str)]
        
        staff_month_data = {}
        for record in month_records:
            sid = record['staff_id']
            sname = record['staff_name']
            
            if sid not in staff_month_data:
                staff_month_data[sid] = {
                    'staff_id': sid,
                    'staff_name': sname,
                    'new_id': 0,
                    'rdp': 0,
                    'total_form': 0,
                    'nominal': 0
                }
            
            key = (record['customer_id'], record['product_id'])
            first_date = customer_first_date.get(key)
            if first_date and first_date.startswith(month_str) and first_date == record['record_date']:
                staff_month_data[sid]['new_id'] += 1
            elif first_date and first_date < record['record_date']:
                staff_month_data[sid]['rdp'] += 1
            
            staff_month_data[sid]['total_form'] += 1
            staff_month_data[sid]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        staff_list = []
        for sid, data in staff_month_data.items():
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
    
    selected_month_str = f"{year}-{str(month).zfill(2)}"
    selected_month_records = [r for r in all_records if r['record_date'].startswith(selected_month_str)]
    
    staff_daily_data = {}
    for record in selected_month_records:
        sid = record['staff_id']
        sname = record['staff_name']
        pid = record['product_id']
        pname = record['product_name']
        date = record['record_date']
        
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
        
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        is_ndp = first_date == date
        
        nom = record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        if is_ndp:
            staff_daily_data[sid]['products'][pid]['daily'][date]['new_id'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['new_id'] += 1
            staff_daily_data[sid]['totals']['new_id'] += 1
        else:
            staff_daily_data[sid]['products'][pid]['daily'][date]['rdp'] += 1
            staff_daily_data[sid]['products'][pid]['totals']['rdp'] += 1
            staff_daily_data[sid]['totals']['rdp'] += 1
        
        staff_daily_data[sid]['products'][pid]['daily'][date]['total_form'] += 1
        staff_daily_data[sid]['products'][pid]['daily'][date]['nominal'] += nom
        staff_daily_data[sid]['products'][pid]['totals']['total_form'] += 1
        staff_daily_data[sid]['products'][pid]['totals']['nominal'] += nom
        staff_daily_data[sid]['totals']['total_form'] += 1
        staff_daily_data[sid]['totals']['nominal'] += nom
    
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
    
    daily_groups = {}
    for record in selected_month_records:
        date = record['record_date']
        if date not in daily_groups:
            daily_groups[date] = []
        daily_groups[date].append(record)
    
    daily_data = []
    for date, records in sorted(daily_groups.items()):
        new_id = 0
        rdp = 0
        nominal = 0
        
        for record in records:
            key = (record['customer_id'], record['product_id'])
            first_date = customer_first_date.get(key)
            if first_date == date:
                new_id += 1
            else:
                rdp += 1
            nominal += record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        daily_data.append({
            'date': date,
            'new_id': new_id,
            'rdp': rdp,
            'total_form': len(records),
            'nominal': nominal
        })
    
    staff_groups = {}
    for record in all_records:
        sid = record['staff_id']
        if sid not in staff_groups:
            staff_groups[sid] = {
                'staff_id': sid,
                'staff_name': record['staff_name'],
                'new_id': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
        
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        if first_date == record['record_date']:
            staff_groups[sid]['new_id'] += 1
        else:
            staff_groups[sid]['rdp'] += 1
        staff_groups[sid]['total_form'] += 1
        staff_groups[sid]['nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    staff_performance = sorted(staff_groups.values(), key=lambda x: x['nominal'], reverse=True)
    
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
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    year: int = None,
    user: User = Depends(get_admin_user)
):
    """Export Report CRM data to Excel"""
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
