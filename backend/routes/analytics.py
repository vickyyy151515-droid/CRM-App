# Analytics and Export Routes

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import io
from .deps import User, get_db, get_admin_user
from utils.helpers import get_jakarta_now, normalize_customer_id

router = APIRouter(tags=["Analytics & Export"])

def get_date_range(period: str, custom_start: str = None, custom_end: str = None):
    """Get start and end dates for a period"""
    now = get_jakarta_now()
    if period == 'custom' and custom_start and custom_end:
        start = datetime.fromisoformat(custom_start + 'T00:00:00').replace(tzinfo=now.tzinfo)
        end = datetime.fromisoformat(custom_end + 'T23:59:59').replace(tzinfo=now.tzinfo)
        return start.isoformat(), end.isoformat()
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
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    staff_id: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get comprehensive staff performance analytics"""
    db = get_db()
    start_date, end_date = get_date_range(period, custom_start, custom_end)
    
    record_query = {'status': 'assigned'}
    if staff_id:
        record_query['assigned_to'] = staff_id
    if product_id:
        record_query['product_id'] = product_id
    
    # Use aggregation for better performance instead of loading all records
    pipeline = [
        {'$match': record_query},
        {'$group': {
            '_id': '$assigned_to',
            'total': {'$sum': 1},
            'wa_ada': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'ada']}, 1, 0]}},
            'wa_tidak': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'tidak']}, 1, 0]}},
            'wa_ceklis1': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'ceklis1']}, 1, 0]}},
            'resp_ya': {'$sum': {'$cond': [{'$eq': ['$respond_status', 'ya']}, 1, 0]}},
            'resp_tidak': {'$sum': {'$cond': [{'$eq': ['$respond_status', 'tidak']}, 1, 0]}},
            'in_period': {'$sum': {'$cond': [{'$gte': ['$assigned_at', start_date]}, 1, 0]}}
        }}
    ]
    aggregated_stats = await db.customer_records.aggregate(pipeline).to_list(1000)
    stats_lookup = {s['_id']: s for s in aggregated_stats}
    
    staff_list = await db.users.find({'role': 'staff'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    
    staff_metrics = []
    for staff in staff_list:
        stats = stats_lookup.get(staff['id'], {})
        
        total = stats.get('total', 0)
        total_period = stats.get('in_period', 0)
        
        wa_ada = stats.get('wa_ada', 0)
        wa_tidak = stats.get('wa_tidak', 0)
        wa_ceklis1 = stats.get('wa_ceklis1', 0)
        wa_checked = wa_ada + wa_tidak + wa_ceklis1
        
        resp_ya = stats.get('resp_ya', 0)
        resp_tidak = stats.get('resp_tidak', 0)
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
    
    # Get daily chart data using aggregation
    daily_pipeline = [
        {'$match': {**record_query, 'assigned_at': {'$gte': start_date}}},
        {'$addFields': {'date_str': {'$substr': ['$assigned_at', 0, 10]}}},
        {'$group': {
            '_id': '$date_str',
            'assigned': {'$sum': 1},
            'wa_checked': {'$sum': {'$cond': [{'$ne': ['$whatsapp_status', None]}, 1, 0]}},
            'responded': {'$sum': {'$cond': [{'$eq': ['$respond_status', 'ya']}, 1, 0]}}
        }},
        {'$sort': {'_id': 1}}
    ]
    daily_results = await db.customer_records.aggregate(daily_pipeline).to_list(1000)
    daily_chart = [{'date': d['_id'], 'assigned': d['assigned'], 'wa_checked': d['wa_checked'], 'responded': d['responded']} for d in daily_results]
    
    # Get overall summary using aggregation
    summary_pipeline = [
        {'$match': record_query},
        {'$group': {
            '_id': None,
            'total': {'$sum': 1},
            'wa_ada': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'ada']}, 1, 0]}},
            'wa_tidak': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'tidak']}, 1, 0]}},
            'wa_ceklis1': {'$sum': {'$cond': [{'$eq': ['$whatsapp_status', 'ceklis1']}, 1, 0]}},
            'resp_ya': {'$sum': {'$cond': [{'$eq': ['$respond_status', 'ya']}, 1, 0]}},
            'resp_tidak': {'$sum': {'$cond': [{'$eq': ['$respond_status', 'tidak']}, 1, 0]}},
            'in_period': {'$sum': {'$cond': [{'$gte': ['$assigned_at', start_date]}, 1, 0]}}
        }}
    ]
    summary_result = await db.customer_records.aggregate(summary_pipeline).to_list(1)
    summary = summary_result[0] if summary_result else {'total': 0, 'wa_ada': 0, 'wa_tidak': 0, 'wa_ceklis1': 0, 'resp_ya': 0, 'resp_tidak': 0, 'in_period': 0}
    
    total_all = summary.get('total', 0)
    wa_all_ada = summary.get('wa_ada', 0)
    wa_all_tidak = summary.get('wa_tidak', 0)
    wa_all_ceklis1 = summary.get('wa_ceklis1', 0)
    wa_all_checked = wa_all_ada + wa_all_tidak + wa_all_ceklis1
    resp_all_ya = summary.get('resp_ya', 0)
    resp_all_tidak = summary.get('resp_tidak', 0)
    records_in_period_count = summary.get('in_period', 0)
    
    return {
        'period': period, 'start_date': start_date, 'end_date': end_date,
        'summary': {
            'total_records': total_all, 'records_in_period': records_in_period_count,
            'whatsapp_ada': wa_all_ada, 'whatsapp_tidak': wa_all_tidak, 'whatsapp_ceklis1': wa_all_ceklis1,
            'whatsapp_checked': wa_all_checked,
            'whatsapp_rate': round((wa_all_ada / wa_all_checked * 100) if wa_all_checked > 0 else 0, 1),
            'respond_ya': resp_all_ya, 'respond_tidak': resp_all_tidak,
            'respond_rate': round((resp_all_ya / (resp_all_ya + resp_all_tidak) * 100) if (resp_all_ya + resp_all_tidak) > 0 else 0, 1)
        },
        'staff_metrics': staff_metrics, 'daily_chart': daily_chart
    }

@router.get("/analytics/business")
async def get_business_analytics(period: str = 'month', product_id: Optional[str] = None, staff_id: Optional[str] = None, user: User = Depends(get_admin_user)):
custom_start: Optional[str] = None,
custom_end: Optional[str] = None,
    """Get business analytics including OMSET trends"""
    db = get_db()
    start_date, end_date = get_date_range(period, custom_start, custom_end)
    
    # FIXED: Use 'record_date' field instead of 'date'
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id
    if staff_id:
        omset_query['staff_id'] = staff_id
    
    def is_tambahan_record(record):
        """Check if record has 'tambahan' in keterangan field"""
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Fetch records for unique customer calculation (only approved)
    from utils.db_operations import add_approved_filter
    records = await db.omset_records.find(add_approved_filter(omset_query), {'_id': 0}).to_list(100000)
    
    # Build customer_first_date for NDP detection
    # IMPORTANT: Exclude records with "tambahan" from first_date calculation
    # When filtering by staff_id, still need global first_date to determine NDP/RDP correctly
    # But for the omset totals, we only show the selected staff's records
    # Build STAFF-SPECIFIC customer first deposit map using MongoDB aggregation
    from utils.db_operations import build_staff_first_date_map
    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)
    
    # Calculate daily stats with unique (staff, customer, product) tuples
    daily_stats = {}
    for record in records:
        date = record.get('record_date')
        if not date:
            continue
        
        if date not in daily_stats:
            daily_stats[date] = {
                'total': 0,
                'count': 0,
                'ndp_tuples': set(),
                'rdp_tuples': set()
            }
        
        daily_stats[date]['total'] += record.get('depo_total', 0) or 0
        daily_stats[date]['count'] += 1
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        product_id_rec = record['product_id']
        key = (staff_id_rec, cid_normalized, product_id_rec)
        first_date = staff_customer_first_date.get(key)
        
        ndp_tuple = (staff_id_rec, cid_normalized, product_id_rec)
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            daily_stats[date]['rdp_tuples'].add(ndp_tuple)
        elif first_date == date:
            daily_stats[date]['ndp_tuples'].add(ndp_tuple)
        else:
            daily_stats[date]['rdp_tuples'].add(ndp_tuple)
    
    # Build omset_chart
    omset_chart = []
    total_ndp = 0
    total_rdp = 0
    ndp_omset = 0
    rdp_omset = 0
    
    for date, stats in sorted(daily_stats.items()):
        ndp_count = len(stats['ndp_tuples'])
        rdp_count = len(stats['rdp_tuples'])
        total_ndp += ndp_count
        total_rdp += rdp_count
        omset_chart.append({
            'date': date,
            'total': stats['total'],
            'count': stats['count'],
            'ndp': ndp_count,
            'rdp': rdp_count
        })
    
    # Calculate NDP/RDP OMSET separately
    for record in records:
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        product_id_rec = record['product_id']
        key = (staff_id_rec, cid_normalized, product_id_rec)
        first_date = staff_customer_first_date.get(key)
        date = record.get('record_date')
        
        # "tambahan" records are always RDP
        if is_tambahan_record(record):
            rdp_omset += record.get('depo_total', 0) or 0
        elif first_date == date:
            ndp_omset += record.get('depo_total', 0) or 0
        else:
            rdp_omset += record.get('depo_total', 0) or 0
    
    # Product OMSET aggregation
    product_pipeline = [
        {'$match': omset_query},
        {'$group': {
            '_id': '$product_id',
            'total_omset': {'$sum': '$depo_total'},
            'record_count': {'$sum': 1}
        }}
    ]
    product_results = await db.omset_records.aggregate(product_pipeline).to_list(1000)
    product_lookup = {p['_id']: p for p in product_results}
    
    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    product_omset = []
    for product in products:
        stats = product_lookup.get(product['id'], {'total_omset': 0, 'record_count': 0})
        total = stats.get('total_omset', 0)
        count = stats.get('record_count', 0)
        product_omset.append({
            'product_id': product['id'], 'product_name': product['name'],
            'total_omset': total, 'record_count': count,
            'avg_omset': round(total / count, 2) if count > 0 else 0
        })
    
    product_omset.sort(key=lambda x: x['total_omset'], reverse=True)
    
    # Database utilization using aggregation
    db_counts_pipeline = [
        {'$group': {
            '_id': {'database_id': '$database_id', 'status': '$status'},
            'count': {'$sum': 1}
        }}
    ]
    db_counts = await db.customer_records.aggregate(db_counts_pipeline).to_list(10000)
    db_counts_lookup = {}
    for item in db_counts:
        db_id = item['_id']['database_id']
        status = item['_id']['status']
        if db_id not in db_counts_lookup:
            db_counts_lookup[db_id] = {'total': 0, 'assigned': 0}
        db_counts_lookup[db_id]['total'] += item['count']
        if status == 'assigned':
            db_counts_lookup[db_id]['assigned'] = item['count']
    
    databases = await db.databases.find({}, {'_id': 0}).to_list(1000)
    db_utilization = []
    for database in databases:
        counts = db_counts_lookup.get(database['id'], {'total': 0, 'assigned': 0})
        total_records = counts['total']
        assigned = counts['assigned']
        available = total_records - assigned
        db_utilization.append({
            'database_id': database['id'], 'database_name': database.get('filename', 'Unknown'),
            'product_name': database.get('product_name', 'Unknown'),
            'total_records': total_records, 'assigned': assigned, 'available': available,
            'utilization_rate': round((assigned / total_records * 100) if total_records > 0 else 0, 1)
        })
    
    db_utilization.sort(key=lambda x: x['utilization_rate'], reverse=True)
    
    # Calculate total OMSET from daily chart
    total_omset = sum(d['total'] for d in omset_chart)
    total_records_count = sum(d['count'] for d in omset_chart)
    
    return {
        'period': period, 'start_date': start_date, 'end_date': end_date,
        'summary': {
            'total_omset': total_omset, 'total_records': total_records_count,
            'avg_omset_per_record': round(total_omset / total_records_count, 2) if total_records_count > 0 else 0,
            'ndp_count': total_ndp, 'rdp_count': total_rdp, 'ndp_omset': ndp_omset, 'rdp_omset': rdp_omset,
            'ndp_percentage': round((total_ndp / (total_ndp + total_rdp) * 100) if (total_ndp + total_rdp) > 0 else 0, 1)
        },
        'omset_chart': omset_chart, 'product_omset': product_omset, 'database_utilization': db_utilization
    }

@router.get("/analytics/staff-ndp-rdp-daily")
async def get_staff_ndp_rdp_daily(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get daily NDP/RDP breakdown per staff for chart visualization"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id

    from utils.db_operations import add_approved_filter, build_staff_first_date_map
    records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0}
    ).to_list(100000)

    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)

    # Group by (date, staff_id) → {ndp, rdp}
    daily_staff = {}
    staff_names = {}
    for record in records:
        date = record.get('record_date')
        sid = record.get('staff_id')
        if not date or not sid:
            continue

        sname = record.get('staff_name', 'Unknown')
        staff_names[sid] = sname

        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        pid = record['product_id']
        key = (sid, cid_normalized, pid)
        first_date = staff_customer_first_date.get(key)

        keterangan = record.get('keterangan', '') or ''
        is_tambahan = 'tambahan' in keterangan.lower()

        ds_key = (date, sid)
        if ds_key not in daily_staff:
            daily_staff[ds_key] = {'ndp_set': set(), 'rdp_set': set()}

        tup = (sid, cid_normalized, pid)
        if is_tambahan:
            daily_staff[ds_key]['rdp_set'].add(tup)
        elif first_date == date:
            daily_staff[ds_key]['ndp_set'].add(tup)
        else:
            daily_staff[ds_key]['rdp_set'].add(tup)

    # Collect all dates and active staff
    all_dates = sorted({k[0] for k in daily_staff})
    active_staff = sorted(staff_names.keys(), key=lambda s: staff_names[s])

    # Build chart data: one row per date, columns for each staff's NDP/RDP
    chart_data = []
    for date in all_dates:
        row = {'date': date}
        for sid in active_staff:
            ds_key = (date, sid)
            entry = daily_staff.get(ds_key, {'ndp_set': set(), 'rdp_set': set()})
            row[f'ndp_{sid}'] = len(entry['ndp_set'])
            row[f'rdp_{sid}'] = len(entry['rdp_set'])
        chart_data.append(row)

    staff_list = [{'id': sid, 'name': staff_names[sid]} for sid in active_staff]

    return {
        'chart_data': chart_data,
        'staff': staff_list,
        'period': period
    }


@router.get("/analytics/staff-conversion-funnel")
async def get_staff_conversion_funnel(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get conversion funnel data per staff: Assigned → WA Checked → Responded → Deposited"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    rec_query = {'status': 'assigned'}
    if product_id:
        rec_query['product_id'] = product_id

    records = await db.customer_records.find(rec_query, {'_id': 0}).to_list(100000)

    # Group by staff
    staff_map = {}
    for r in records:
        sid = r.get('assigned_to')
        if not sid:
            continue
        if sid not in staff_map:
            staff_map[sid] = {'name': r.get('assigned_to_name', 'Unknown'), 'assigned': 0, 'wa_checked': 0, 'responded': 0, 'customers': set()}
        staff_map[sid]['assigned'] += 1
        if r.get('whatsapp_status') == 'ada':
            staff_map[sid]['wa_checked'] += 1
        if r.get('respond_status') == 'ya':
            staff_map[sid]['responded'] += 1
            cid = r.get('row_data', {}).get('customer_id') or r.get('row_data', {}).get('username') or r.get('id')
            pid = r.get('product_id', '')
            if cid:
                staff_map[sid]['customers'].add((str(cid).strip().lower(), pid))

    # Count deposited customers per staff from omset
    from utils.db_operations import add_approved_filter
    omset_query = {}
    if product_id:
        omset_query['product_id'] = product_id
    omset_records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0, 'staff_id': 1, 'customer_id_normalized': 1, 'customer_id': 1, 'product_id': 1}
    ).to_list(100000)

    staff_deposited = {}
    for o in omset_records:
        sid = o.get('staff_id')
        cid = o.get('customer_id_normalized') or str(o.get('customer_id', '')).strip().lower()
        pid = o.get('product_id', '')
        if sid not in staff_deposited:
            staff_deposited[sid] = set()
        staff_deposited[sid].add((cid, pid))

    result = []
    for sid, data in staff_map.items():
        deposited_set = staff_deposited.get(sid, set())
        deposited_count = len(data['customers'] & deposited_set) if data['customers'] else 0
        result.append({
            'staff_id': sid,
            'staff_name': data['name'],
            'assigned': data['assigned'],
            'wa_checked': data['wa_checked'],
            'responded': data['responded'],
            'deposited': deposited_count
        })

    result.sort(key=lambda x: x['assigned'], reverse=True)
    return {'funnel_data': result}


@router.get("/analytics/revenue-heatmap")
async def get_revenue_heatmap(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get revenue heatmap: staff × day-of-week with deposit counts and amounts"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id

    records = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'staff_id': 1, 'staff_name': 1, 'record_date': 1, 'depo_total': 1, 'nominal': 1}
    ).to_list(100000)

    DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    staff_names = {}
    heatmap = {}

    for r in records:
        sid = r.get('staff_id')
        staff_names[sid] = r.get('staff_name', 'Unknown')
        date_str = r.get('record_date', '')
        try:
            from datetime import date as dt_date
            d = dt_date.fromisoformat(date_str)
            dow = d.weekday()  # 0=Mon, 6=Sun
        except Exception:
            continue

        key = (sid, dow)
        amount = r.get('depo_total') or r.get('nominal') or 0
        if key not in heatmap:
            heatmap[key] = {'count': 0, 'amount': 0}
        heatmap[key]['count'] += 1
        heatmap[key]['amount'] += amount

    staff_list = sorted(staff_names.keys(), key=lambda s: staff_names[s])
    grid = []
    max_count = 0
    max_amount = 0
    for sid in staff_list:
        row = {'staff_id': sid, 'staff_name': staff_names[sid], 'days': []}
        for dow in range(7):
            cell = heatmap.get((sid, dow), {'count': 0, 'amount': 0})
            if cell['count'] > max_count:
                max_count = cell['count']
            if cell['amount'] > max_amount:
                max_amount = cell['amount']
            row['days'].append({'day': DAY_NAMES[dow], 'count': cell['count'], 'amount': cell['amount']})
        grid.append(row)

    return {'grid': grid, 'max_count': max_count, 'max_amount': max_amount, 'day_names': DAY_NAMES}


@router.get("/analytics/deposit-lifecycle")
async def get_deposit_lifecycle(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get average time from 'responded ya' to first deposit, per staff and product"""
    db = get_db()

    from utils.db_operations import add_approved_filter

    # Get all responded records with timestamps
    rec_query = {'status': 'assigned', 'respond_status': 'ya', 'respond_status_updated_at': {'$ne': None}}
    if product_id:
        rec_query['product_id'] = product_id
    responded = await db.customer_records.find(rec_query, {'_id': 0}).to_list(100000)

    # Get all omset records
    omset_query = {}
    if product_id:
        omset_query['product_id'] = product_id
    omset_recs = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'staff_id': 1, 'staff_name': 1, 'customer_id_normalized': 1, 'customer_id': 1, 'product_id': 1, 'record_date': 1}
    ).to_list(100000)

    # Build earliest deposit date per (staff, customer, product)
    from datetime import datetime
    deposit_dates = {}
    for o in omset_recs:
        sid = o.get('staff_id')
        cid = o.get('customer_id_normalized') or str(o.get('customer_id', '')).strip().lower()
        pid = o.get('product_id', '')
        rd = o.get('record_date', '')
        key = (sid, cid, pid)
        if key not in deposit_dates or rd < deposit_dates[key]:
            deposit_dates[key] = rd

    # Calculate lifecycle per staff
    staff_lifecycle = {}
    for r in responded:
        sid = r.get('assigned_to')
        sname = r.get('assigned_to_name', 'Unknown')
        pid = r.get('product_id', '')
        respond_at = r.get('respond_status_updated_at', '')

        cid_raw = r.get('row_data', {}).get('customer_id') or r.get('row_data', {}).get('username') or ''
        cid = str(cid_raw).strip().lower()
        if not cid or not respond_at:
            continue

        deposit_date = deposit_dates.get((sid, cid, pid))

        if sid not in staff_lifecycle:
            staff_lifecycle[sid] = {'name': sname, 'converted': [], 'pending': 0, 'total_responded': 0}

        staff_lifecycle[sid]['total_responded'] += 1

        if deposit_date:
            try:
                resp_dt = datetime.fromisoformat(respond_at.replace('Z', '+00:00'))
                dep_dt = datetime.fromisoformat(deposit_date + 'T00:00:00+07:00')
                days_diff = max(0, (dep_dt - resp_dt).days)
                staff_lifecycle[sid]['converted'].append(days_diff)
            except Exception:
                staff_lifecycle[sid]['converted'].append(0)
        else:
            staff_lifecycle[sid]['pending'] += 1

    result = []
    for sid, data in staff_lifecycle.items():
        avg_days = round(sum(data['converted']) / len(data['converted']), 1) if data['converted'] else None
        min_days = min(data['converted']) if data['converted'] else None
        max_days = max(data['converted']) if data['converted'] else None
        result.append({
            'staff_id': sid,
            'staff_name': data['name'],
            'total_responded': data['total_responded'],
            'converted_count': len(data['converted']),
            'pending_count': data['pending'],
            'avg_days': avg_days,
            'min_days': min_days,
            'max_days': max_days,
            'conversion_rate': round(len(data['converted']) / data['total_responded'] * 100, 1) if data['total_responded'] > 0 else 0
        })

    result.sort(key=lambda x: x['avg_days'] if x['avg_days'] is not None else 999)
    return {'lifecycle_data': result}


# ==================== NEW ANALYTICS CHARTS (Operational & Strategic) ====================

@router.get("/analytics/response-time-by-staff")
async def get_response_time_by_staff(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Average time from assignment to first WA check and first response, per staff"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    rec_query = {
        'status': 'assigned',
        'assigned_at': {'$ne': None}
    }
    if product_id:
        rec_query['product_id'] = product_id

    records = await db.customer_records.find(rec_query, {'_id': 0}).to_list(100000)

    staff_times = {}
    for r in records:
        sid = r.get('assigned_to')
        sname = r.get('assigned_to_name', 'Unknown')
        assigned_at = r.get('assigned_at', '')
        if not sid or not assigned_at:
            continue

        if sid not in staff_times:
            staff_times[sid] = {
                'name': sname,
                'wa_times': [],
                'respond_times': [],
                'total_assigned': 0
            }
        staff_times[sid]['total_assigned'] += 1

        try:
            assigned_dt = datetime.fromisoformat(assigned_at.replace('Z', '+00:00'))
        except Exception:
            continue

        # Time to WA check
        wa_updated = r.get('whatsapp_status_updated_at')
        if wa_updated:
            try:
                wa_dt = datetime.fromisoformat(wa_updated.replace('Z', '+00:00'))
                diff_hours = max(0, (wa_dt - assigned_dt).total_seconds() / 3600)
                if diff_hours < 720:  # cap at 30 days
                    staff_times[sid]['wa_times'].append(diff_hours)
            except Exception:
                pass

        # Time to response
        resp_updated = r.get('respond_status_updated_at')
        if resp_updated:
            try:
                resp_dt = datetime.fromisoformat(resp_updated.replace('Z', '+00:00'))
                diff_hours = max(0, (resp_dt - assigned_dt).total_seconds() / 3600)
                if diff_hours < 720:
                    staff_times[sid]['respond_times'].append(diff_hours)
            except Exception:
                pass

    result = []
    for sid, data in staff_times.items():
        avg_wa = round(sum(data['wa_times']) / len(data['wa_times']), 1) if data['wa_times'] else None
        avg_resp = round(sum(data['respond_times']) / len(data['respond_times']), 1) if data['respond_times'] else None
        result.append({
            'staff_id': sid,
            'staff_name': data['name'],
            'total_assigned': data['total_assigned'],
            'avg_wa_hours': avg_wa,
            'avg_respond_hours': avg_resp,
            'wa_checked_count': len(data['wa_times']),
            'responded_count': len(data['respond_times']),
            'fastest_wa': round(min(data['wa_times']), 1) if data['wa_times'] else None,
            'slowest_wa': round(max(data['wa_times']), 1) if data['wa_times'] else None,
        })

    result.sort(key=lambda x: x['avg_wa_hours'] if x['avg_wa_hours'] is not None else 999)
    return {'response_time_data': result}


@router.get("/analytics/followup-effectiveness")
async def get_followup_effectiveness(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Track follow-ups sent vs. successful deposits per staff"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    rec_query = {'status': 'assigned'}
    if product_id:
        rec_query['product_id'] = product_id

    records = await db.customer_records.find(rec_query, {'_id': 0}).to_list(100000)

    from utils.db_operations import add_approved_filter
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id
    omset_recs = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'staff_id': 1, 'customer_id_normalized': 1, 'customer_id': 1, 'product_id': 1}
    ).to_list(100000)

    # Build deposited set per staff
    staff_deposited = {}
    for o in omset_recs:
        sid = o.get('staff_id')
        cid = o.get('customer_id_normalized') or str(o.get('customer_id', '')).strip().lower()
        pid = o.get('product_id', '')
        if sid not in staff_deposited:
            staff_deposited[sid] = set()
        staff_deposited[sid].add((cid, pid))

    staff_map = {}
    for r in records:
        sid = r.get('assigned_to')
        sname = r.get('assigned_to_name', 'Unknown')
        if not sid:
            continue
        if sid not in staff_map:
            staff_map[sid] = {
                'name': sname, 'wa_checked': 0, 'wa_ada': 0,
                'responded': 0, 'followup_customers': set(), 'total': 0
            }
        staff_map[sid]['total'] += 1

        wa = r.get('whatsapp_status')
        if wa in ['ada', 'tidak', 'ceklis1']:
            staff_map[sid]['wa_checked'] += 1
        if wa == 'ada':
            staff_map[sid]['wa_ada'] += 1

        if r.get('respond_status') == 'ya':
            staff_map[sid]['responded'] += 1
            cid = r.get('row_data', {}).get('customer_id') or r.get('row_data', {}).get('username') or ''
            pid = r.get('product_id', '')
            if cid:
                staff_map[sid]['followup_customers'].add((str(cid).strip().lower(), pid))

    result = []
    for sid, data in staff_map.items():
        deposited_set = staff_deposited.get(sid, set())
        converted = len(data['followup_customers'] & deposited_set) if data['followup_customers'] else 0
        result.append({
            'staff_id': sid,
            'staff_name': data['name'],
            'total_assigned': data['total'],
            'wa_checked': data['wa_checked'],
            'wa_ada': data['wa_ada'],
            'responded': data['responded'],
            'deposited': converted,
            'effectiveness': round(converted / data['responded'] * 100, 1) if data['responded'] > 0 else 0
        })

    result.sort(key=lambda x: x['effectiveness'], reverse=True)
    return {'effectiveness_data': result}


@router.get("/analytics/product-performance")
async def get_product_performance(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """NDP/RDP counts and amounts per product"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter, build_staff_first_date_map
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0}
    ).to_list(100000)

    staff_customer_first_date = await build_staff_first_date_map(db)

    products = await db.products.find({}, {'_id': 0}).to_list(1000)
    product_names = {p['id']: p['name'] for p in products}

    product_stats = {}
    for record in records:
        pid = record.get('product_id', '')
        pname = product_names.get(pid, pid)
        sid = record.get('staff_id')
        cid = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        date = record.get('record_date', '')
        amount = record.get('depo_total', 0) or 0

        key = (sid, cid, pid)
        first_date = staff_customer_first_date.get(key)
        keterangan = record.get('keterangan', '') or ''
        is_tambahan = 'tambahan' in keterangan.lower()

        if pid not in product_stats:
            product_stats[pid] = {'name': pname, 'ndp': 0, 'rdp': 0, 'ndp_amount': 0, 'rdp_amount': 0, 'total_records': 0}

        product_stats[pid]['total_records'] += 1
        if is_tambahan:
            product_stats[pid]['rdp'] += 1
            product_stats[pid]['rdp_amount'] += amount
        elif first_date == date:
            product_stats[pid]['ndp'] += 1
            product_stats[pid]['ndp_amount'] += amount
        else:
            product_stats[pid]['rdp'] += 1
            product_stats[pid]['rdp_amount'] += amount

    result = []
    for pid, stats in product_stats.items():
        total = stats['ndp'] + stats['rdp']
        result.append({
            'product_id': pid,
            'product_name': stats['name'],
            'ndp_count': stats['ndp'],
            'rdp_count': stats['rdp'],
            'total_count': total,
            'ndp_amount': stats['ndp_amount'],
            'rdp_amount': stats['rdp_amount'],
            'total_amount': stats['ndp_amount'] + stats['rdp_amount'],
            'ndp_percentage': round(stats['ndp'] / total * 100, 1) if total > 0 else 0
        })

    result.sort(key=lambda x: x['total_amount'], reverse=True)
    return {'product_data': result}


@router.get("/analytics/customer-value-comparison")
async def get_customer_value_comparison(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Compare New vs Returning customer total deposit amounts (LTV)"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter, build_staff_first_date_map
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id

    records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0}
    ).to_list(100000)

    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)

    # Aggregate by staff: NDP vs RDP amounts
    staff_value = {}
    daily_value = {}
    for record in records:
        sid = record.get('staff_id')
        sname = record.get('staff_name', 'Unknown')
        cid = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        pid = record.get('product_id', '')
        date = record.get('record_date', '')
        amount = record.get('depo_total', 0) or 0

        key = (sid, cid, pid)
        first_date = staff_customer_first_date.get(key)
        keterangan = record.get('keterangan', '') or ''
        is_tambahan = 'tambahan' in keterangan.lower()

        is_ndp = not is_tambahan and first_date == date

        if sid not in staff_value:
            staff_value[sid] = {'name': sname, 'ndp_amount': 0, 'rdp_amount': 0, 'ndp_count': 0, 'rdp_count': 0}

        if is_ndp:
            staff_value[sid]['ndp_amount'] += amount
            staff_value[sid]['ndp_count'] += 1
        else:
            staff_value[sid]['rdp_amount'] += amount
            staff_value[sid]['rdp_count'] += 1

        # Daily breakdown
        if date not in daily_value:
            daily_value[date] = {'ndp_amount': 0, 'rdp_amount': 0}
        if is_ndp:
            daily_value[date]['ndp_amount'] += amount
        else:
            daily_value[date]['rdp_amount'] += amount

    staff_result = []
    for sid, data in staff_value.items():
        total = data['ndp_amount'] + data['rdp_amount']
        staff_result.append({
            'staff_id': sid,
            'staff_name': data['name'],
            'ndp_amount': data['ndp_amount'],
            'rdp_amount': data['rdp_amount'],
            'total_amount': total,
            'ndp_count': data['ndp_count'],
            'rdp_count': data['rdp_count'],
            'avg_ndp': round(data['ndp_amount'] / data['ndp_count']) if data['ndp_count'] > 0 else 0,
            'avg_rdp': round(data['rdp_amount'] / data['rdp_count']) if data['rdp_count'] > 0 else 0
        })
    staff_result.sort(key=lambda x: x['total_amount'], reverse=True)

    daily_chart = [{'date': d, 'ndp_amount': v['ndp_amount'], 'rdp_amount': v['rdp_amount']} for d, v in sorted(daily_value.items())]

    total_ndp = sum(s['ndp_amount'] for s in staff_result)
    total_rdp = sum(s['rdp_amount'] for s in staff_result)

    return {
        'staff_data': staff_result,
        'daily_chart': daily_chart,
        'summary': {
            'total_ndp_amount': total_ndp,
            'total_rdp_amount': total_rdp,
            'total_amount': total_ndp + total_rdp,
            'ndp_share': round(total_ndp / (total_ndp + total_rdp) * 100, 1) if (total_ndp + total_rdp) > 0 else 0
        }
    }


@router.get("/analytics/deposit-trends")
async def get_deposit_trends(
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    granularity: str = 'daily',
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Deposit volume trends over time with daily/weekly/monthly granularity"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter
    omset_query = {'record_date': {'$gte': start_date[:10]}}
    if product_id:
        omset_query['product_id'] = product_id

    records = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'record_date': 1, 'depo_total': 1, 'nominal': 1, 'staff_id': 1, 'customer_id': 1}
    ).to_list(100000)

    from datetime import date as dt_date

    bucket_data = {}
    for r in records:
        date_str = r.get('record_date', '')
        amount = r.get('depo_total') or r.get('nominal') or 0
        if not date_str:
            continue

        try:
            d = dt_date.fromisoformat(date_str)
        except Exception:
            continue

        if granularity == 'weekly':
            # ISO week start (Monday)
            start_of_week = d - timedelta(days=d.weekday())
            bucket_key = start_of_week.isoformat()
        elif granularity == 'monthly':
            bucket_key = f"{d.year}-{d.month:02d}"
        else:
            bucket_key = date_str

        if bucket_key not in bucket_data:
            bucket_data[bucket_key] = {'amount': 0, 'count': 0, 'customers': set()}
        bucket_data[bucket_key]['amount'] += amount
        bucket_data[bucket_key]['count'] += 1
        cid = str(r.get('customer_id', '')).strip().lower()
        if cid:
            bucket_data[bucket_key]['customers'].add(cid)

    chart_data = []
    for key in sorted(bucket_data.keys()):
        data = bucket_data[key]
        chart_data.append({
            'date': key,
            'amount': data['amount'],
            'count': data['count'],
            'unique_customers': len(data['customers']),
            'avg_deposit': round(data['amount'] / data['count']) if data['count'] > 0 else 0
        })

    total_amount = sum(d['amount'] for d in chart_data)
    total_count = sum(d['count'] for d in chart_data)
    peak = max(chart_data, key=lambda x: x['amount']) if chart_data else None

    return {
        'chart_data': chart_data,
        'granularity': granularity,
        'summary': {
            'total_amount': total_amount,
            'total_deposits': total_count,
            'avg_per_period': round(total_amount / len(chart_data)) if chart_data else 0,
            'peak_period': peak['date'] if peak else None,
            'peak_amount': peak['amount'] if peak else 0
        }
    }


# ==================== DRILL-DOWN DETAIL ENDPOINTS ====================

@router.get("/analytics/drill-down/response-time")
async def drill_down_response_time(
    staff_id: str,
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Drill-down: individual records with WA/response timestamps for a staff"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    rec_query = {'status': 'assigned', 'assigned_to': staff_id, 'assigned_at': {'$ne': None}}
    if product_id:
        rec_query['product_id'] = product_id

    records = await db.customer_records.find(
        rec_query,
        {'_id': 0, 'id': 1, 'assigned_at': 1, 'whatsapp_status': 1, 'whatsapp_status_updated_at': 1,
         'respond_status': 1, 'respond_status_updated_at': 1, 'product_name': 1,
         'row_data': 1, 'database_name': 1}
    ).sort('assigned_at', -1).to_list(100)

    result = []
    for r in records:
        assigned_at = r.get('assigned_at', '')
        wa_updated = r.get('whatsapp_status_updated_at')
        resp_updated = r.get('respond_status_updated_at')
        wa_hours = None
        resp_hours = None

        try:
            a_dt = datetime.fromisoformat(assigned_at.replace('Z', '+00:00'))
            if wa_updated:
                wa_dt = datetime.fromisoformat(wa_updated.replace('Z', '+00:00'))
                wa_hours = round(max(0, (wa_dt - a_dt).total_seconds() / 3600), 1)
            if resp_updated:
                r_dt = datetime.fromisoformat(resp_updated.replace('Z', '+00:00'))
                resp_hours = round(max(0, (r_dt - a_dt).total_seconds() / 3600), 1)
        except Exception:
            pass

        cid = r.get('row_data', {}).get('customer_id') or r.get('row_data', {}).get('username') or '-'
        result.append({
            'record_id': r.get('id', ''),
            'customer_id': str(cid),
            'product': r.get('product_name', ''),
            'database': r.get('database_name', ''),
            'assigned_at': assigned_at,
            'wa_status': r.get('whatsapp_status') or '-',
            'wa_hours': wa_hours,
            'respond_status': r.get('respond_status') or '-',
            'respond_hours': resp_hours,
        })

    return {'records': result, 'total': len(result)}


@router.get("/analytics/drill-down/followup-detail")
async def drill_down_followup_detail(
    staff_id: str,
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Drill-down: responded customers with deposit status for a staff"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    rec_query = {'status': 'assigned', 'assigned_to': staff_id, 'respond_status': 'ya'}
    if product_id:
        rec_query['product_id'] = product_id

    records = await db.customer_records.find(rec_query, {'_id': 0}).to_list(100)

    # Get deposits for this staff
    from utils.db_operations import add_approved_filter
    omset_query = {'staff_id': staff_id}
    if product_id:
        omset_query['product_id'] = product_id
    deposits = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'customer_id_normalized': 1, 'customer_id': 1, 'product_id': 1, 'depo_total': 1, 'record_date': 1}
    ).to_list(100000)

    deposit_map = {}
    for d in deposits:
        cid = d.get('customer_id_normalized') or str(d.get('customer_id', '')).strip().lower()
        pid = d.get('product_id', '')
        key = (cid, pid)
        if key not in deposit_map:
            deposit_map[key] = {'total': 0, 'count': 0, 'last_date': ''}
        deposit_map[key]['total'] += d.get('depo_total', 0) or 0
        deposit_map[key]['count'] += 1
        rd = d.get('record_date', '')
        if rd > deposit_map[key]['last_date']:
            deposit_map[key]['last_date'] = rd

    result = []
    for r in records:
        cid_raw = r.get('row_data', {}).get('customer_id') or r.get('row_data', {}).get('username') or ''
        cid = str(cid_raw).strip().lower()
        pid = r.get('product_id', '')
        dep_info = deposit_map.get((cid, pid))

        result.append({
            'customer_id': str(cid_raw) or '-',
            'product': r.get('product_name', ''),
            'respond_at': r.get('respond_status_updated_at', ''),
            'wa_status': r.get('whatsapp_status') or '-',
            'deposited': dep_info is not None,
            'deposit_total': dep_info['total'] if dep_info else 0,
            'deposit_count': dep_info['count'] if dep_info else 0,
            'last_deposit': dep_info['last_date'] if dep_info else None,
        })

    result.sort(key=lambda x: (not x['deposited'], -(x['deposit_total'])))
    converted = sum(1 for r in result if r['deposited'])
    return {'records': result, 'total': len(result), 'converted': converted, 'pending': len(result) - converted}


@router.get("/analytics/drill-down/product-staff")
async def drill_down_product_staff(
    product_id: str,
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Drill-down: staff-level NDP/RDP breakdown for a specific product"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter, build_staff_first_date_map
    omset_query = {'record_date': {'$gte': start_date[:10]}, 'product_id': product_id}
    records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0}
    ).to_list(100000)

    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)

    staff_data = {}
    for record in records:
        sid = record.get('staff_id')
        sname = record.get('staff_name', 'Unknown')
        cid = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        date = record.get('record_date', '')
        amount = record.get('depo_total', 0) or 0
        key = (sid, cid, product_id)
        first_date = staff_customer_first_date.get(key)
        keterangan = record.get('keterangan', '') or ''
        is_tambahan = 'tambahan' in keterangan.lower()
        is_ndp = not is_tambahan and first_date == date

        if sid not in staff_data:
            staff_data[sid] = {'name': sname, 'ndp': 0, 'rdp': 0, 'ndp_amt': 0, 'rdp_amt': 0}
        if is_ndp:
            staff_data[sid]['ndp'] += 1
            staff_data[sid]['ndp_amt'] += amount
        else:
            staff_data[sid]['rdp'] += 1
            staff_data[sid]['rdp_amt'] += amount

    result = []
    for sid, d in staff_data.items():
        result.append({
            'staff_id': sid, 'staff_name': d['name'],
            'ndp_count': d['ndp'], 'rdp_count': d['rdp'],
            'ndp_amount': d['ndp_amt'], 'rdp_amount': d['rdp_amt'],
            'total_amount': d['ndp_amt'] + d['rdp_amt'],
            'total_count': d['ndp'] + d['rdp']
        })
    result.sort(key=lambda x: x['total_amount'], reverse=True)
    return {'staff_breakdown': result, 'total_staff': len(result)}


@router.get("/analytics/drill-down/staff-customers")
async def drill_down_staff_customers(
    staff_id: str,
    period: str = 'month',
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Drill-down: top customers by deposit value for a staff (NDP vs RDP)"""
    db = get_db()
    start_date, _ = get_date_range(period, custom_start, custom_end)

    from utils.db_operations import add_approved_filter, build_staff_first_date_map
    omset_query = {'record_date': {'$gte': start_date[:10]}, 'staff_id': staff_id}
    if product_id:
        omset_query['product_id'] = product_id

    records = await db.omset_records.find(
        add_approved_filter(omset_query), {'_id': 0}
    ).to_list(100000)

    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)

    customer_map = {}
    for record in records:
        cid = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        cname = record.get('customer_name') or record.get('customer_id', '')
        pid = record.get('product_id', '')
        date = record.get('record_date', '')
        amount = record.get('depo_total', 0) or 0
        key = (staff_id, cid, pid)
        first_date = staff_customer_first_date.get(key)
        keterangan = record.get('keterangan', '') or ''
        is_tambahan = 'tambahan' in keterangan.lower()
        is_ndp = not is_tambahan and first_date == date

        ckey = (cid, pid)
        if ckey not in customer_map:
            customer_map[ckey] = {
                'customer_id': str(record.get('customer_id', '')),
                'customer_name': str(cname),
                'product': record.get('product_name', ''),
                'type': 'NDP' if is_ndp else 'RDP',
                'total_amount': 0, 'deposit_count': 0, 'first_deposit': date, 'last_deposit': date
            }
        customer_map[ckey]['total_amount'] += amount
        customer_map[ckey]['deposit_count'] += 1
        if date < customer_map[ckey]['first_deposit']:
            customer_map[ckey]['first_deposit'] = date
        if date > customer_map[ckey]['last_deposit']:
            customer_map[ckey]['last_deposit'] = date

    result = sorted(customer_map.values(), key=lambda x: x['total_amount'], reverse=True)[:50]
    return {'customers': result, 'total': len(result)}


@router.get("/analytics/drill-down/date-deposits")
async def drill_down_date_deposits(
    date: str,
    granularity: str = 'daily',
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Drill-down: individual deposits for a specific date/period"""
    db = get_db()

    from utils.db_operations import add_approved_filter
    from datetime import date as dt_date

    # Determine date range based on granularity
    if granularity == 'weekly':
        try:
            start_d = dt_date.fromisoformat(date)
            end_d = start_d + timedelta(days=6)
            omset_query = {'record_date': {'$gte': start_d.isoformat(), '$lte': end_d.isoformat()}}
        except Exception:
            omset_query = {'record_date': date}
    elif granularity == 'monthly':
        omset_query = {'record_date': {'$regex': f'^{date}'}}
    else:
        omset_query = {'record_date': date}

    if product_id:
        omset_query['product_id'] = product_id

    records = await db.omset_records.find(
        add_approved_filter(omset_query),
        {'_id': 0, 'staff_id': 1, 'staff_name': 1, 'customer_id': 1, 'customer_name': 1,
         'product_name': 1, 'depo_total': 1, 'nominal': 1, 'record_date': 1, 'keterangan': 1,
         'customer_type': 1}
    ).sort('depo_total', -1).to_list(200)

    result = []
    for r in records:
        result.append({
            'staff_name': r.get('staff_name', 'Unknown'),
            'customer_id': str(r.get('customer_id', '')),
            'customer_name': r.get('customer_name', ''),
            'product': r.get('product_name', ''),
            'amount': r.get('depo_total') or r.get('nominal') or 0,
            'date': r.get('record_date', ''),
            'type': r.get('customer_type', ''),
            'note': r.get('keterangan', ''),
        })

    total_amount = sum(r['amount'] for r in result)
    return {'deposits': result, 'total_count': len(result), 'total_amount': total_amount}


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
custom_start: Optional[str] = None,
custom_end: Optional[str] = None,
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
