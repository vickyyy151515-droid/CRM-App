# Customer Retention Tracking Routes
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .deps import get_db, get_current_user, get_admin_user, User
from utils.helpers import get_jakarta_now, normalize_customer_id

router = APIRouter(tags=["Retention"])

# ==================== RETENTION TRACKING ENDPOINTS ====================

@router.get("/retention/overview")
async def get_retention_overview(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get overall customer retention metrics"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Build query
    query = {'record_date': {'$gte': start_date, '$lte': end_date}}
    if product_id:
        query['product_id'] = product_id
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    # Get all OMSET records in date range
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    if not records:
        return {
            'date_range': {'start': start_date, 'end': end_date},
            'total_customers': 0,
            'ndp_customers': 0,
            'rdp_customers': 0,
            'retention_rate': 0,
            'total_deposits': 0,
            'total_omset': 0,
            'avg_deposits_per_customer': 0,
            'avg_omset_per_customer': 0,
            'top_loyal_customers': []
        }
    
    # Helper function to normalize customer ID
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get first deposit dates efficiently using MongoDB aggregation
    # Retention uses (customer_id, product_id) key — business-level customer acquisition
    pipeline = [
        {'$match': {'$and': [
            {'$or': [
                {'keterangan': {'$exists': False}},
                {'keterangan': None},
                {'keterangan': ''},
                {'keterangan': {'$not': {'$regex': 'tambahan', '$options': 'i'}}}
            ]}
        ]}},
        {'$group': {
            '_id': {
                'c': {'$ifNull': ['$customer_id_normalized', '$customer_id']},
                'p': '$product_id'
            },
            'first_date': {'$min': '$record_date'}
        }}
    ]
    agg_results = await db.omset_records.aggregate(pipeline).to_list(None)
    customer_first_date = {
        ((r['_id']['c'] or '').strip().upper(), r['_id']['p']): r['first_date']
        for r in agg_results if r['_id']['c'] and r['_id']['p']
    }
    
    # Analyze customers in date range - USE NORMALIZED CUSTOMER ID
    customer_stats = defaultdict(lambda: {
        'customer_id': '',
        'customer_id_display': '',  # Original for display
        'customer_name': '',
        'product_id': '',
        'product_name': '',
        'total_deposits': 0,
        'total_omset': 0,
        'first_deposit': None,
        'last_deposit': None,
        'is_ndp': False,
        'deposit_dates': set()
    })
    
    for record in records:
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record.get('product_id'))
        customer = customer_stats[key]
        
        customer['customer_id'] = cid_normalized
        # Store original customer_id for display (use most recent)
        if customer['last_deposit'] is None or record['record_date'] > customer['last_deposit']:
            customer['customer_id_display'] = record['customer_id']
            customer['customer_name'] = record.get('customer_name', record['customer_id'])
        
        customer['product_id'] = record.get('product_id')
        customer['product_name'] = record.get('product_name', 'Unknown')
        customer['total_deposits'] += 1
        customer['total_omset'] += record.get('depo_total', 0) or 0
        customer['deposit_dates'].add(record['record_date'])
        
        # Track first/last deposit in range
        if customer['first_deposit'] is None or record['record_date'] < customer['first_deposit']:
            customer['first_deposit'] = record['record_date']
        if customer['last_deposit'] is None or record['record_date'] > customer['last_deposit']:
            customer['last_deposit'] = record['record_date']
        
        # Check if NDP (first deposit is within date range)
        # If customer has no non-tambahan records, first_ever will be None.
        # In that case, fall back to their earliest record date (including tambahan).
        first_ever = customer_first_date.get(key)
        if first_ever is None:
            # Customer only has "tambahan" records — use their earliest record date
            first_ever = customer['first_deposit']
        if first_ever and start_date <= first_ever <= end_date:
            customer['is_ndp'] = True
    
    # Calculate metrics
    all_customers = list(customer_stats.values())
    total_customers = len(all_customers)
    ndp_customers = sum(1 for c in all_customers if c['is_ndp'])
    rdp_customers = sum(1 for c in all_customers if not c['is_ndp'])
    total_deposits = sum(c['total_deposits'] for c in all_customers)
    total_omset = sum(c['total_omset'] for c in all_customers)
    
    # Retention rate: RDP / Total customers
    retention_rate = round((rdp_customers / total_customers * 100), 1) if total_customers > 0 else 0
    
    # Top loyal customers (by deposit count, then by OMSET)
    top_customers = sorted(all_customers, key=lambda x: (x['total_deposits'], x['total_omset']), reverse=True)[:10]
    top_loyal = []
    for c in top_customers:
        top_loyal.append({
            'customer_id': c.get('customer_id_display', c['customer_id']),  # Use display ID
            'customer_name': c['customer_name'],
            'product_name': c['product_name'],
            'total_deposits': c['total_deposits'],
            'total_omset': c['total_omset'],
            'avg_deposit': round(c['total_omset'] / c['total_deposits'], 2) if c['total_deposits'] > 0 else 0,
            'first_deposit': c['first_deposit'],
            'last_deposit': c['last_deposit'],
            'is_ndp': c['is_ndp'],
            'unique_days': len(c['deposit_dates'])
        })
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'total_customers': total_customers,
        'ndp_customers': ndp_customers,
        'rdp_customers': rdp_customers,
        'retention_rate': retention_rate,
        'total_deposits': total_deposits,
        'total_omset': total_omset,
        'avg_deposits_per_customer': round(total_deposits / total_customers, 1) if total_customers > 0 else 0,
        'avg_omset_per_customer': round(total_omset / total_customers, 2) if total_customers > 0 else 0,
        'top_loyal_customers': top_loyal
    }


@router.get("/retention/customers")
async def get_retention_customers(
    filter_type: str = "all",  # all, ndp, rdp, loyal (3+ deposits)
    sort_by: str = "deposits",  # deposits, omset, recent
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get detailed customer list with retention metrics"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Build query
    query = {'record_date': {'$gte': start_date, '$lte': end_date}}
    if product_id:
        query['product_id'] = product_id
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    # Get records
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    if not records:
        return {'customers': [], 'total': 0}
    
    # Get all records to determine first deposits - USE MONGODB AGGREGATION
    pipeline = [
        {'$match': {'$and': [
            {'$or': [
                {'keterangan': {'$exists': False}}, {'keterangan': None}, {'keterangan': ''},
                {'keterangan': {'$not': {'$regex': 'tambahan', '$options': 'i'}}}
            ]}
        ]}},
        {'$group': {'_id': {'c': {'$ifNull': ['$customer_id_normalized', '$customer_id']}, 'p': '$product_id'}, 'first_date': {'$min': '$record_date'}}}
    ]
    agg_results = await db.omset_records.aggregate(pipeline).to_list(None)
    customer_first_date = {((r['_id']['c'] or '').strip().upper(), r['_id']['p']): r['first_date'] for r in agg_results if r['_id']['c'] and r['_id']['p']}
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Build customer stats
    customer_stats = defaultdict(lambda: {
        'customer_id': '',
        'customer_name': '',
        'product_id': '',
        'product_name': '',
        'staff_name': '',
        'total_deposits': 0,
        'total_omset': 0,
        'first_deposit': None,
        'last_deposit': None,
        'is_ndp': False,
        'deposit_dates': []
    })
    
    for record in records:
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record.get('product_id'))
        customer = customer_stats[key]
        
        customer['customer_id'] = record['customer_id']
        customer['customer_name'] = record.get('customer_name', record['customer_id'])
        customer['product_id'] = record.get('product_id')
        customer['product_name'] = record.get('product_name', 'Unknown')
        customer['staff_name'] = record.get('staff_name', 'Unknown')
        customer['total_deposits'] += 1
        customer['total_omset'] += record.get('depo_total', 0) or 0
        customer['deposit_dates'].append(record['record_date'])
        
        if customer['first_deposit'] is None or record['record_date'] < customer['first_deposit']:
            customer['first_deposit'] = record['record_date']
        if customer['last_deposit'] is None or record['record_date'] > customer['last_deposit']:
            customer['last_deposit'] = record['record_date']
        
        # Check if NDP - fall back to earliest record date if only tambahan records
        first_ever = customer_first_date.get(key)
        if first_ever is None:
            first_ever = customer['first_deposit']
        if first_ever and start_date <= first_ever <= end_date:
            customer['is_ndp'] = True
    
    customers = list(customer_stats.values())
    
    # Apply filter
    if filter_type == 'ndp':
        customers = [c for c in customers if c['is_ndp']]
    elif filter_type == 'rdp':
        customers = [c for c in customers if not c['is_ndp']]
    elif filter_type == 'loyal':
        customers = [c for c in customers if c['total_deposits'] >= 3]
    
    # Sort
    if sort_by == 'deposits':
        customers.sort(key=lambda x: x['total_deposits'], reverse=True)
    elif sort_by == 'omset':
        customers.sort(key=lambda x: x['total_omset'], reverse=True)
    elif sort_by == 'recent':
        customers.sort(key=lambda x: x['last_deposit'] or '', reverse=True)
    
    # Format for response
    result = []
    for c in customers[:limit]:
        unique_days = len(set(c['deposit_dates']))
        result.append({
            'customer_id': c['customer_id'],
            'customer_name': c['customer_name'],
            'product_name': c['product_name'],
            'staff_name': c['staff_name'],
            'total_deposits': c['total_deposits'],
            'total_omset': c['total_omset'],
            'avg_deposit': round(c['total_omset'] / c['total_deposits'], 2) if c['total_deposits'] > 0 else 0,
            'first_deposit': c['first_deposit'],
            'last_deposit': c['last_deposit'],
            'is_ndp': c['is_ndp'],
            'unique_days': unique_days,
            'loyalty_score': min(100, c['total_deposits'] * 10 + unique_days * 5)  # Simple loyalty score
        })
    
    return {
        'customers': result,
        'total': len(customers)
    }


@router.get("/retention/trend")
async def get_retention_trend(
    days: int = 30,
    product_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get daily retention trend showing NDP vs RDP over time"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    
    # Build query
    query = {}
    if product_id:
        query['product_id'] = product_id
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    # Get all records for first deposit calculation
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(500000)
    
    if not all_records:
        return {'trend': [], 'summary': {'total_ndp': 0, 'total_rdp': 0}}
    
    # Helper function to normalize customer ID
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Build customer first deposit map - EXCLUDE "tambahan" records
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record.get('product_id'))
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Calculate daily NDP/RDP counts
    trend = []
    total_ndp = 0
    total_rdp = 0
    
    for i in range(days - 1, -1, -1):
        date = (jakarta_now - timedelta(days=i)).strftime('%Y-%m-%d')
        
        # Get records for this date
        day_records = [r for r in all_records if r['record_date'] == date]
        
        day_ndp = 0
        day_rdp = 0
        day_omset = 0
        seen_customers = set()
        
        for record in day_records:
            cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
            key = (cid_normalized, record.get('product_id'))
            if key not in seen_customers:
                seen_customers.add(key)
                first_date = customer_first_date.get(key)
                # "tambahan" records are excluded from first_date, so they will be RDP
                if first_date == date:
                    day_ndp += 1
                else:
                    day_rdp += 1
            day_omset += record.get('depo_total', 0) or 0
        
        total_ndp += day_ndp
        total_rdp += day_rdp
        
        trend.append({
            'date': date,
            'ndp': day_ndp,
            'rdp': day_rdp,
            'total': day_ndp + day_rdp,
            'omset': day_omset,
            'retention_rate': round((day_rdp / (day_ndp + day_rdp) * 100), 1) if (day_ndp + day_rdp) > 0 else 0
        })
    
    return {
        'trend': trend,
        'summary': {
            'total_ndp': total_ndp,
            'total_rdp': total_rdp,
            'avg_daily_ndp': round(total_ndp / days, 1),
            'avg_daily_rdp': round(total_rdp / days, 1),
            'overall_retention': round((total_rdp / (total_ndp + total_rdp) * 100), 1) if (total_ndp + total_rdp) > 0 else 0
        }
    }


@router.get("/retention/by-product")
async def get_retention_by_product(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get retention metrics broken down by product"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # Build query
    query = {'record_date': {'$gte': start_date, '$lte': end_date}}
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    if not records:
        return {'products': []}
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Build STAFF-SPECIFIC customer first deposit map using MongoDB aggregation
    from utils.db_operations import build_staff_first_date_map
    staff_customer_first_date = await build_staff_first_date_map(db)
    
    # Group by product — track (staff_id, customer_id) pairs for each product
    products = defaultdict(lambda: {
        'product_id': '',
        'product_name': '',
        'total_customers': set(),
        'ndp_customers': set(),
        'rdp_customers': set(),
        'total_deposits': 0,
        'total_omset': 0
    })
    
    for record in records:
        prod_id = record.get('product_id', 'unknown')
        prod = products[prod_id]
        
        prod['product_id'] = prod_id
        prod['product_name'] = record.get('product_name', 'Unknown')
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        staff_cid_pair = (staff_id_rec, cid_normalized)
        prod['total_customers'].add(staff_cid_pair)
        prod['total_deposits'] += 1
        prod['total_omset'] += record.get('depo_total', 0) or 0
        
        key = (staff_id_rec, cid_normalized, prod_id)
        first_date = staff_customer_first_date.get(key)
        if first_date is None:
            # Customer only has tambahan records — use their earliest record date
            first_date = record['record_date']
        if first_date and start_date <= first_date <= end_date:
            prod['ndp_customers'].add(staff_cid_pair)
        else:
            prod['rdp_customers'].add(staff_cid_pair)
    
    # Format result
    result = []
    for prod in products.values():
        total = len(prod['total_customers'])
        ndp = len(prod['ndp_customers'])
        rdp = len(prod['rdp_customers'])
        
        result.append({
            'product_id': prod['product_id'],
            'product_name': prod['product_name'],
            'total_customers': total,
            'ndp_customers': ndp,
            'rdp_customers': rdp,
            'retention_rate': round((rdp / total * 100), 1) if total > 0 else 0,
            'total_deposits': prod['total_deposits'],
            'total_omset': prod['total_omset'],
            'avg_deposits_per_customer': round(prod['total_deposits'] / total, 1) if total > 0 else 0,
            'avg_omset_per_customer': round(prod['total_omset'] / total, 2) if total > 0 else 0
        })
    
    # Sort by total customers
    result.sort(key=lambda x: x['total_customers'], reverse=True)
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'products': result
    }


@router.get("/retention/by-staff")
async def get_retention_by_staff(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get retention metrics broken down by staff (Admin only)"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=90)).strftime('%Y-%m-%d')
    
    records = await db.omset_records.find(
        {'record_date': {'$gte': start_date, '$lte': end_date}},
        {'_id': 0}
    ).to_list(100000)
    
    if not records:
        return {'staff': []}
    
    # Get first deposit dates efficiently using MongoDB aggregation
    pipeline = [
        {'$match': {'$and': [
            {'$or': [
                {'keterangan': {'$exists': False}}, {'keterangan': None}, {'keterangan': ''},
                {'keterangan': {'$not': {'$regex': 'tambahan', '$options': 'i'}}}
            ]}
        ]}},
        {'$group': {'_id': {'c': {'$ifNull': ['$customer_id_normalized', '$customer_id']}, 'p': '$product_id'}, 'first_date': {'$min': '$record_date'}}}
    ]
    agg_results = await db.omset_records.aggregate(pipeline).to_list(None)
    customer_first_date = {((r['_id']['c'] or '').strip().upper(), r['_id']['p']): r['first_date'] for r in agg_results if r['_id']['c'] and r['_id']['p']}
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Group by staff
    # IMPORTANT: Track customers per (customer_id, product_id) to match Overview logic
    staff_data = defaultdict(lambda: {
        'staff_id': '',
        'staff_name': '',
        'total_customers': set(),  # (customer_id, product_id) pairs
        'ndp_customers': set(),    # (customer_id, product_id) pairs  
        'rdp_customers': set(),    # (customer_id, product_id) pairs
        'loyal_customers': set(),  # customer_ids with 3+ deposits
        'total_deposits': 0,
        'total_omset': 0,
        'customer_deposits': defaultdict(int)  # customer_id -> deposit count
    })
    
    for record in records:
        staff_id = record.get('staff_id', 'unknown')
        staff = staff_data[staff_id]
        
        staff['staff_id'] = staff_id
        staff['staff_name'] = record.get('staff_name', 'Unknown')
        
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        prod_id = record.get('product_id')
        
        # Use (customer_id, product_id) as key to match Overview logic
        customer_key = (cid_normalized, prod_id)
        staff['total_customers'].add(customer_key)
        staff['total_deposits'] += 1
        staff['total_omset'] += record.get('depo_total', 0) or 0
        staff['customer_deposits'][cid_normalized] += 1
        
        first_date = customer_first_date.get(customer_key)
        if first_date is None:
            # Customer only has tambahan records — use their earliest record date
            first_date = record['record_date']
        if first_date and start_date <= first_date <= end_date:
            staff['ndp_customers'].add(customer_key)
        else:
            staff['rdp_customers'].add(customer_key)
    
    # Calculate loyal customers
    for staff in staff_data.values():
        for customer_id, count in staff['customer_deposits'].items():
            if count >= 3:
                staff['loyal_customers'].add(customer_id)
    
    # Format result
    result = []
    for staff in staff_data.values():
        total = len(staff['total_customers'])
        ndp = len(staff['ndp_customers'])
        rdp = len(staff['rdp_customers'])
        loyal = len(staff['loyal_customers'])
        
        result.append({
            'staff_id': staff['staff_id'],
            'staff_name': staff['staff_name'],
            'total_customers': total,
            'ndp_customers': ndp,
            'rdp_customers': rdp,
            'loyal_customers': loyal,
            'retention_rate': round((rdp / total * 100), 1) if total > 0 else 0,
            'loyalty_rate': round((loyal / total * 100), 1) if total > 0 else 0,
            'total_deposits': staff['total_deposits'],
            'total_omset': staff['total_omset'],
            'avg_deposits_per_customer': round(staff['total_deposits'] / total, 1) if total > 0 else 0
        })
    
    # Sort by retention rate
    result.sort(key=lambda x: x['retention_rate'], reverse=True)
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'staff': result
    }



# ==================== CUSTOMER SEGMENT ALERTS ====================

@router.get("/retention/alerts")
async def get_customer_alerts(
    product_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """
    Get at-risk customers who haven't deposited recently.
    Risk levels:
    - Critical: 14+ days since last deposit
    - High: 7-13 days since last deposit
    - Medium: 3-6 days since last deposit (only for frequent depositors)
    """
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    today = jakarta_now.strftime('%Y-%m-%d')
    
    # Helper function to normalize customer ID
    # Get all OMSET records
    query = {}
    if product_id:
        query['product_id'] = product_id
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(500000)
    
    if not records:
        return {
            'summary': {'critical': 0, 'high': 0, 'medium': 0, 'total': 0},
            'alerts': []
        }
    
    # Build customer data with last deposit info - USE NORMALIZED CUSTOMER ID
    customer_data = defaultdict(lambda: {
        'customer_id': '',
        'customer_id_display': '',  # Original display name
        'customer_name': '',
        'product_id': '',
        'product_name': '',
        'staff_id': '',
        'staff_name': '',
        'total_deposits': 0,
        'total_omset': 0,
        'last_deposit_date': None,
        'first_deposit_date': None,
        'deposit_dates': []
    })
    
    for record in records:
        # Use normalized customer_id for grouping (same customer with different case = same customer)
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record.get('product_id'))
        customer = customer_data[key]
        
        # Store the original customer_id for display (use most recent one)
        if customer['last_deposit_date'] is None or record['record_date'] > customer['last_deposit_date']:
            customer['customer_id'] = cid_normalized
            customer['customer_id_display'] = record['customer_id']  # Original for display
            customer['customer_name'] = record.get('customer_name', record['customer_id'])
            customer['staff_id'] = record.get('staff_id')
            customer['staff_name'] = record.get('staff_name', 'Unknown')
        
        customer['product_id'] = record.get('product_id')
        customer['product_name'] = record.get('product_name', 'Unknown')
        customer['total_deposits'] += 1
        customer['total_omset'] += record.get('depo_total', 0) or 0
        customer['deposit_dates'].append(record['record_date'])
        
        if customer['last_deposit_date'] is None or record['record_date'] > customer['last_deposit_date']:
            customer['last_deposit_date'] = record['record_date']
        if customer['first_deposit_date'] is None or record['record_date'] < customer['first_deposit_date']:
            customer['first_deposit_date'] = record['record_date']
    
    # Calculate days since last deposit and assign risk levels
    alerts = []
    critical_count = 0
    high_count = 0
    medium_count = 0
    
    for customer in customer_data.values():
        if not customer['last_deposit_date']:
            continue
        
        last_date = datetime.strptime(customer['last_deposit_date'], '%Y-%m-%d')
        today_date = datetime.strptime(today, '%Y-%m-%d')
        days_since = (today_date - last_date).days
        
        # Skip if deposited today
        if days_since == 0:
            continue
        
        # Determine risk level
        risk_level = None
        risk_color = None
        
        if days_since >= 14:
            risk_level = 'critical'
            risk_color = '#ef4444'  # red
            critical_count += 1
        elif days_since >= 7:
            risk_level = 'high'
            risk_color = '#f97316'  # orange
            high_count += 1
        elif days_since >= 3 and customer['total_deposits'] >= 2:
            # Only flag medium risk for customers who deposited at least twice
            risk_level = 'medium'
            risk_color = '#eab308'  # yellow
            medium_count += 1
        
        if risk_level:
            # Calculate average deposit frequency
            unique_days = len(set(customer['deposit_dates']))
            first_date = datetime.strptime(customer['first_deposit_date'], '%Y-%m-%d')
            days_active = max(1, (today_date - first_date).days)
            avg_days_between = round(days_active / max(1, unique_days - 1), 1) if unique_days > 1 else 0
            
            alerts.append({
                'customer_id': customer.get('customer_id_display', customer['customer_id']),  # Use display ID
                'customer_name': customer['customer_name'],
                'product_id': customer['product_id'],
                'product_name': customer['product_name'],
                'staff_id': customer['staff_id'],
                'staff_name': customer['staff_name'],
                'total_deposits': customer['total_deposits'],
                'total_omset': customer['total_omset'],
                'last_deposit_date': customer['last_deposit_date'],
                'days_since_deposit': days_since,
                'risk_level': risk_level,
                'risk_color': risk_color,
                'avg_days_between_deposits': avg_days_between,
                'unique_deposit_days': unique_days
            })
    
    # Sort by risk (critical first, then by days since deposit)
    risk_order = {'critical': 0, 'high': 1, 'medium': 2}
    alerts.sort(key=lambda x: (risk_order[x['risk_level']], -x['days_since_deposit']))
    
    # Enrich alerts with phone numbers and customer details from customer_records, bonanza_records, and memberwd_records
    if alerts:
        # Get all customer IDs from alerts to look up
        customer_ids_to_lookup = set()
        for alert in alerts:
            customer_ids_to_lookup.add(alert['customer_id'].lower().strip())
            customer_ids_to_lookup.add(alert['customer_id'].upper().strip())
            customer_ids_to_lookup.add(alert['customer_id'].strip())
        
        # Build lookup maps (username -> {phone, name, source}) from multiple collections
        customer_info_lookup = {}
        
        # Helper function to extract customer info from row_data
        def extract_info_from_records(records, source_name):
            for record in records:
                row_data = record.get('row_data', {})
                username = None
                phone = None
                name = None
                
                for key, value in row_data.items():
                    key_lower = key.lower()
                    # Find username field
                    if key_lower in ['username', 'user_name', 'user', 'id', 'userid', 'user_id']:
                        username = str(value).strip() if value else None
                    # Find phone field
                    if key_lower in ['telpon', 'phone', 'no_hp', 'nomor', 'hp', 'no hp', 'phone_number', 'telp', 'no_telp', 'telephone', 'whatsapp', 'wa']:
                        phone = str(value).strip() if value else None
                    # Find name field
                    if key_lower in ['name', 'nama', 'full_name', 'fullname', 'customer_name', 'nama_lengkap']:
                        name = str(value).strip() if value else None
                
                if username:
                    # Store with both lowercase and original case
                    info = {
                        'phone': phone,
                        'name': name,
                        'username': username,
                        'source': source_name
                    }
                    # Only update if we have more info or it's a new entry
                    username_lower = username.lower()
                    if username_lower not in customer_info_lookup or (phone and not customer_info_lookup[username_lower].get('phone')):
                        customer_info_lookup[username_lower] = info
                    if username not in customer_info_lookup or (phone and not customer_info_lookup[username].get('phone')):
                        customer_info_lookup[username] = info
        
        # Query customer_records for customer info
        customer_records = await db.customer_records.find(
            {},
            {'_id': 0, 'row_data': 1}
        ).to_list(100000)
        extract_info_from_records(customer_records, 'Database')
        
        # Query bonanza_records for customer info
        bonanza_records = await db.bonanza_records.find(
            {},
            {'_id': 0, 'row_data': 1}
        ).to_list(100000)
        extract_info_from_records(bonanza_records, 'DB Bonanza')
        
        # Query memberwd_records for customer info
        memberwd_records = await db.memberwd_records.find(
            {},
            {'_id': 0, 'row_data': 1}
        ).to_list(100000)
        extract_info_from_records(memberwd_records, 'Member WD')
        
        # Enrich alerts with customer details
        for alert in alerts:
            customer_id = alert['customer_id']
            # Try to find customer info
            info = customer_info_lookup.get(customer_id.lower()) or customer_info_lookup.get(customer_id) or customer_info_lookup.get(customer_id.upper())
            
            if info:
                alert['phone_number'] = info.get('phone') or ''
                alert['matched_name'] = info.get('name') or ''
                alert['matched_username'] = info.get('username') or ''
                alert['matched_source'] = info.get('source') or ''
            else:
                alert['phone_number'] = ''
                alert['matched_name'] = ''
                alert['matched_username'] = ''
                alert['matched_source'] = ''
    
    return {
        'summary': {
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'total': critical_count + high_count + medium_count
        },
        'alerts': alerts
    }


@router.get("/retention/alerts/by-staff")
async def get_alerts_by_staff(
    user: User = Depends(get_admin_user)
):
    """Get at-risk customer counts grouped by staff (Admin only)"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    today = jakarta_now.strftime('%Y-%m-%d')
    
    # Helper function to normalize customer ID
    records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    if not records:
        return {'staff': []}
    
    # Build customer data - USE NORMALIZED CUSTOMER ID
    customer_data = defaultdict(lambda: {
        'staff_id': '',
        'staff_name': '',
        'last_deposit_date': None,
        'total_deposits': 0
    })
    
    for record in records:
        # Use normalized customer_id for grouping
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record.get('product_id'))
        customer = customer_data[key]
        
        # Update staff info based on most recent deposit
        if customer['last_deposit_date'] is None or record['record_date'] > customer['last_deposit_date']:
            customer['staff_id'] = record.get('staff_id')
            customer['staff_name'] = record.get('staff_name', 'Unknown')
        
        customer['total_deposits'] += 1
        
        if customer['last_deposit_date'] is None or record['record_date'] > customer['last_deposit_date']:
            customer['last_deposit_date'] = record['record_date']
    
    # Group alerts by staff
    staff_alerts = defaultdict(lambda: {
        'staff_id': '',
        'staff_name': '',
        'critical': 0,
        'high': 0,
        'medium': 0,
        'total_customers': 0
    })
    
    for customer in customer_data.values():
        if not customer['last_deposit_date'] or not customer['staff_id']:
            continue
        
        staff_id = customer['staff_id']
        staff = staff_alerts[staff_id]
        staff['staff_id'] = staff_id
        staff['staff_name'] = customer['staff_name']
        staff['total_customers'] += 1
        
        last_date = datetime.strptime(customer['last_deposit_date'], '%Y-%m-%d')
        today_date = datetime.strptime(today, '%Y-%m-%d')
        days_since = (today_date - last_date).days
        
        if days_since >= 14:
            staff['critical'] += 1
        elif days_since >= 7:
            staff['high'] += 1
        elif days_since >= 3 and customer['total_deposits'] >= 2:
            staff['medium'] += 1
    
    result = list(staff_alerts.values())
    result.sort(key=lambda x: x['critical'] + x['high'], reverse=True)
    
    return {'staff': result}


@router.post("/retention/alerts/dismiss")
async def dismiss_alert(
    customer_id: str,
    product_id: str,
    user: User = Depends(get_current_user)
):
    """Dismiss an alert for a customer (adds to dismissed list for 7 days)"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    
    # Add to dismissed alerts collection
    await db.dismissed_alerts.update_one(
        {'customer_id': customer_id, 'product_id': product_id, 'user_id': user.id},
        {'$set': {
            'customer_id': customer_id,
            'product_id': product_id,
            'user_id': user.id,
            'dismissed_at': jakarta_now.isoformat(),
            'expires_at': (jakarta_now + timedelta(days=7)).isoformat()
        }},
        upsert=True
    )
    
    return {'message': 'Alert dismissed for 7 days'}
