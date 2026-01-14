# Analytics and Export Routes

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import io
from .deps import User, get_db, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Analytics & Export"])

def get_date_range(period: str):
    """Get start and end dates for a period"""
    now = get_jakarta_now()
    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'yesterday':
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        now = start + timedelta(days=1)
    elif period == 'week':
        start = now - timedelta(days=7)
    elif period == 'month':
        start = now - timedelta(days=30)
    elif period == 'quarter':
        start = now - timedelta(days=90)
    elif period == 'year':
        start = now - timedelta(days=365)
    else:
        start = now - timedelta(days=30)
    return start.isoformat(), now.isoformat()

@router.get("/analytics/staff-performance")
async def get_staff_performance_analytics(
    period: str = 'month',
    staff_id: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get comprehensive staff performance analytics"""
    db = get_db()
    start_date, end_date = get_date_range(period)
    
    record_query = {'status': 'assigned'}
    if staff_id:
        record_query['assigned_to'] = staff_id
    if product_id:
        record_query['product_id'] = product_id
    
    records = await db.customer_records.find(record_query, {'_id': 0}).to_list(100000)
    records_in_period = [r for r in records if r.get('assigned_at', '') >= start_date]
    staff_list = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    staff_metrics = []
    for staff in staff_list:
        staff_records = [r for r in records if r.get('assigned_to') == staff['id']]
        staff_records_period = [r for r in records_in_period if r.get('assigned_to') == staff['id']]
        
        total = len(staff_records)
        total_period = len(staff_records_period)
        
        wa_ada = len([r for r in staff_records if r.get('whatsapp_status') == 'ada'])
        wa_tidak = len([r for r in staff_records if r.get('whatsapp_status') == 'tidak'])
        wa_ceklis1 = len([r for r in staff_records if r.get('whatsapp_status') == 'ceklis1'])
        wa_checked = wa_ada + wa_tidak + wa_ceklis1
        
        resp_ya = len([r for r in staff_records if r.get('respond_status') == 'ya'])
        resp_tidak = len([r for r in staff_records if r.get('respond_status') == 'tidak'])
        resp_checked = resp_ya + resp_tidak
        
        staff_metrics.append({
            'staff_id': staff['id'], 'staff_name': staff['name'],
            'total_assigned': total, 'assigned_in_period': total_period,
            'whatsapp_ada': wa_ada, 'whatsapp_tidak': wa_tidak, 'whatsapp_ceklis1': wa_ceklis1,
            'whatsapp_checked': wa_checked,
            'whatsapp_rate': round((wa_ada / wa_checked * 100) if wa_checked > 0 else 0, 1),
            'respond_ya': resp_ya, 'respond_tidak': resp_tidak, 'respond_checked': resp_checked,
            'respond_rate': round((resp_ya / resp_checked * 100) if resp_checked > 0 else 0, 1),
            'completion_rate': round((wa_checked / total * 100) if total > 0 else 0, 1)
        })
    
    staff_metrics.sort(key=lambda x: x['total_assigned'], reverse=True)
    
    daily_data = {}
    for record in records_in_period:
        date = record.get('assigned_at', '')[:10]
        if date not in daily_data:
            daily_data[date] = {'date': date, 'assigned': 0, 'wa_checked': 0, 'responded': 0}
        daily_data[date]['assigned'] += 1
        if record.get('whatsapp_status'):
            daily_data[date]['wa_checked'] += 1
        if record.get('respond_status') == 'ya':
            daily_data[date]['responded'] += 1
    
    daily_chart = sorted(daily_data.values(), key=lambda x: x['date'])
    
    total_all = len(records)
    wa_all_ada = len([r for r in records if r.get('whatsapp_status') == 'ada'])
    wa_all_tidak = len([r for r in records if r.get('whatsapp_status') == 'tidak'])
    wa_all_ceklis1 = len([r for r in records if r.get('whatsapp_status') == 'ceklis1'])
    wa_all_checked = wa_all_ada + wa_all_tidak + wa_all_ceklis1
    resp_all_ya = len([r for r in records if r.get('respond_status') == 'ya'])
    resp_all_tidak = len([r for r in records if r.get('respond_status') == 'tidak'])
    
    return {
        'period': period, 'start_date': start_date, 'end_date': end_date,
        'summary': {
            'total_records': total_all, 'records_in_period': len(records_in_period),
            'whatsapp_ada': wa_all_ada, 'whatsapp_tidak': wa_all_tidak, 'whatsapp_ceklis1': wa_all_ceklis1,
            'whatsapp_checked': wa_all_checked,
            'whatsapp_rate': round((wa_all_ada / wa_all_checked * 100) if wa_all_checked > 0 else 0, 1),
            'respond_ya': resp_all_ya, 'respond_tidak': resp_all_tidak,
            'respond_rate': round((resp_all_ya / (resp_all_ya + resp_all_tidak) * 100) if (resp_all_ya + resp_all_tidak) > 0 else 0, 1)
        },
        'staff_metrics': staff_metrics, 'daily_chart': daily_chart
    }

@router.get("/analytics/business")
async def get_business_analytics(period: str = 'month', product_id: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Get business analytics including OMSET trends"""
    db = get_db()
    start_date, end_date = get_date_range(period)
    
    omset_query = {}
    if product_id:
        omset_query['product_id'] = product_id
    
    omset_records = await db.omset_records.find(omset_query, {'_id': 0}).to_list(100000)
    omset_in_period = [r for r in omset_records if r.get('date', '') >= start_date[:10]]
    
    daily_omset = {}
    for record in omset_in_period:
        date = record.get('date', '')
        if date not in daily_omset:
            daily_omset[date] = {'date': date, 'total': 0, 'count': 0, 'ndp': 0, 'rdp': 0}
        daily_omset[date]['total'] += record.get('depo_total', 0)
        daily_omset[date]['count'] += 1
        if record.get('customer_type') == 'NDP':
            daily_omset[date]['ndp'] += 1
        else:
            daily_omset[date]['rdp'] += 1
    
    omset_chart = sorted(daily_omset.values(), key=lambda x: x['date'])
    
    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    product_omset = []
    for product in products:
        prod_records = [r for r in omset_in_period if r.get('product_id') == product['id']]
        total = sum(r.get('depo_total', 0) for r in prod_records)
        count = len(prod_records)
        product_omset.append({
            'product_id': product['id'], 'product_name': product['name'],
            'total_omset': total, 'record_count': count,
            'avg_omset': round(total / count, 2) if count > 0 else 0
        })
    
    product_omset.sort(key=lambda x: x['total_omset'], reverse=True)
    
    total_ndp = len([r for r in omset_in_period if r.get('customer_type') == 'NDP'])
    total_rdp = len([r for r in omset_in_period if r.get('customer_type') == 'RDP'])
    ndp_omset = sum(r.get('depo_total', 0) for r in omset_in_period if r.get('customer_type') == 'NDP')
    rdp_omset = sum(r.get('depo_total', 0) for r in omset_in_period if r.get('customer_type') == 'RDP')
    
    databases = await db.databases.find({}, {'_id': 0}).to_list(1000)
    db_utilization = []
    for database in databases:
        total_records = await db.customer_records.count_documents({'database_id': database['id']})
        assigned = await db.customer_records.count_documents({'database_id': database['id'], 'status': 'assigned'})
        available = total_records - assigned
        db_utilization.append({
            'database_id': database['id'], 'database_name': database.get('filename', 'Unknown'),
            'product_name': database.get('product_name', 'Unknown'),
            'total_records': total_records, 'assigned': assigned, 'available': available,
            'utilization_rate': round((assigned / total_records * 100) if total_records > 0 else 0, 1)
        })
    
    db_utilization.sort(key=lambda x: x['utilization_rate'], reverse=True)
    total_omset = sum(r.get('depo_total', 0) for r in omset_in_period)
    
    return {
        'period': period, 'start_date': start_date, 'end_date': end_date,
        'summary': {
            'total_omset': total_omset, 'total_records': len(omset_in_period),
            'avg_omset_per_record': round(total_omset / len(omset_in_period), 2) if omset_in_period else 0,
            'ndp_count': total_ndp, 'rdp_count': total_rdp, 'ndp_omset': ndp_omset, 'rdp_omset': rdp_omset,
            'ndp_percentage': round((total_ndp / (total_ndp + total_rdp) * 100) if (total_ndp + total_rdp) > 0 else 0, 1)
        },
        'omset_chart': omset_chart, 'product_omset': product_omset, 'database_utilization': db_utilization
    }

# ==================== EXPORT ENDPOINTS ====================

@router.get("/export/customer-records")
async def export_customer_records(
    format: str = 'xlsx', product_id: Optional[str] = None, status: Optional[str] = None,
    staff_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None,
    token: Optional[str] = None, user: User = Depends(get_admin_user)
):
    """Export customer records with filters"""
    db = get_db()
    query = {}
    if product_id: query['product_id'] = product_id
    if status: query['status'] = status
    if staff_id: query['assigned_to'] = staff_id
    
    records = await db.customer_records.find(query, {'_id': 0}).to_list(100000)
    
    if start_date:
        records = [r for r in records if r.get('assigned_at', r.get('created_at', '')) >= start_date]
    if end_date:
        records = [r for r in records if r.get('assigned_at', r.get('created_at', '')) <= end_date]
    
    export_data = []
    for record in records:
        row = {
            'ID': record.get('id', ''), 'Database': record.get('database_name', ''),
            'Product': record.get('product_name', ''), 'Status': record.get('status', ''),
            'Assigned To': record.get('assigned_to_name', ''), 'Assigned At': record.get('assigned_at', ''),
            'WhatsApp Status': record.get('whatsapp_status', ''), 'Respond Status': record.get('respond_status', ''),
        }
        if record.get('row_data'):
            for key, value in record['row_data'].items():
                row[key] = value
        export_data.append(row)
    
    df = pd.DataFrame(export_data)
    filename = f"customer_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{filename}.xlsx")

@router.get("/export/omset")
async def export_omset_data(
    format: str = 'xlsx', product_id: Optional[str] = None, staff_id: Optional[str] = None,
    customer_type: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None,
    token: Optional[str] = None, user: User = Depends(get_admin_user)
):
    """Export OMSET data with filters"""
    db = get_db()
    query = {}
    if product_id: query['product_id'] = product_id
    if staff_id: query['staff_id'] = staff_id
    if customer_type: query['customer_type'] = customer_type
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    if start_date:
        records = [r for r in records if r.get('date', '') >= start_date]
    if end_date:
        records = [r for r in records if r.get('date', '') <= end_date]
    
    export_data = [{
        'Date': r.get('date', ''), 'Customer Name': r.get('customer_name', ''),
        'Customer ID': r.get('customer_id', ''), 'Product': r.get('product_name', ''),
        'Staff': r.get('staff_name', ''), 'Nominal': r.get('nominal', 0),
        'Kelipatan': r.get('kelipatan', 1), 'Depo Total': r.get('depo_total', 0),
        'Customer Type': r.get('customer_type', ''), 'Keterangan': r.get('keterangan', ''),
        'Created At': r.get('created_at', '')
    } for r in records]
    
    df = pd.DataFrame(export_data)
    filename = f"omset_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{filename}.xlsx")

@router.get("/export/staff-report")
async def export_staff_performance_report(format: str = 'xlsx', period: str = 'month', token: Optional[str] = None, user: User = Depends(get_admin_user)):
    """Export staff performance report"""
    analytics = await get_staff_performance_analytics(period=period, user=user)
    
    export_data = [{
        'Staff Name': s['staff_name'], 'Total Assigned': s['total_assigned'],
        'Assigned in Period': s['assigned_in_period'], 'WhatsApp Ada': s['whatsapp_ada'],
        'WhatsApp Tidak': s['whatsapp_tidak'], 'WhatsApp Ceklis1': s['whatsapp_ceklis1'],
        'WhatsApp Checked': s['whatsapp_checked'], 'WhatsApp Rate (%)': s['whatsapp_rate'],
        'Respond Ya': s['respond_ya'], 'Respond Tidak': s['respond_tidak'],
        'Respond Rate (%)': s['respond_rate'], 'Completion Rate (%)': s['completion_rate']
    } for s in analytics['staff_metrics']]
    
    df = pd.DataFrame(export_data)
    filename = f"staff_performance_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{filename}.xlsx")

@router.get("/export/leave-requests")
async def export_leave_requests(
    format: str = 'xlsx', staff_id: Optional[str] = None, status: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    token: Optional[str] = None, user: User = Depends(get_admin_user)
):
    """Export leave request records"""
    db = get_db()
    query = {}
    if staff_id: query['staff_id'] = staff_id
    if status: query['status'] = status
    
    records = await db.leave_requests.find(query, {'_id': 0}).sort('created_at', -1).to_list(100000)
    
    if start_date:
        records = [r for r in records if r.get('date', '') >= start_date]
    if end_date:
        records = [r for r in records if r.get('date', '') <= end_date]
    
    export_data = [{
        'Date': r.get('date', ''),
        'Staff Name': r.get('staff_name', ''),
        'Leave Type': 'Off Day' if r.get('leave_type') == 'off_day' else 'Sakit',
        'Start Time': r.get('start_time', '-'),
        'End Time': r.get('end_time', '-'),
        'Hours Deducted': r.get('hours_deducted', 0),
        'Reason': r.get('reason', ''),
        'Status': r.get('status', '').title(),
        'Reviewed By': r.get('reviewed_by_name', ''),
        'Reviewed At': r.get('reviewed_at', ''),
        'Admin Note': r.get('admin_note', ''),
        'Created At': r.get('created_at', '')
    } for r in records]
    
    df = pd.DataFrame(export_data)
    filename = f"leave_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{filename}.xlsx")

@router.get("/export/izin-records")
async def export_izin_records(
    format: str = 'xlsx', staff_id: Optional[str] = None,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    token: Optional[str] = None, user: User = Depends(get_admin_user)
):
    """Export izin (break) records"""
    db = get_db()
    query = {}
    if staff_id: query['staff_id'] = staff_id
    
    records = await db.izin_records.find(query, {'_id': 0}).sort('created_at', -1).to_list(100000)
    
    if start_date:
        records = [r for r in records if r.get('date', '') >= start_date]
    if end_date:
        records = [r for r in records if r.get('date', '') <= end_date]
    
    export_data = [{
        'Date': r.get('date', ''),
        'Staff Name': r.get('staff_name', ''),
        'Start Time': r.get('start_time', ''),
        'End Time': r.get('end_time', '-') if r.get('end_time') else 'Ongoing',
        'Duration (minutes)': round(r.get('duration_minutes', 0), 2) if r.get('duration_minutes') else '-',
        'Created At': r.get('created_at', '')
    } for r in records]
    
    df = pd.DataFrame(export_data)
    filename = f"izin_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format == 'csv':
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        temp_path = f"/tmp/{filename}.csv"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='text/csv', filename=f"{filename}.csv")
    else:
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        temp_path = f"/tmp/{filename}.xlsx"
        with open(temp_path, 'wb') as f:
            f.write(output.getvalue())
        return FileResponse(path=temp_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=f"{filename}.xlsx")
