# Member Monthly Bonus Routes
# Shows customers with total omset >= 10,000,000 in a month, grouped by staff and product

from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from .deps import User, get_db, get_admin_user, get_current_user, get_jakarta_now

router = APIRouter(tags=["Member Monthly Bonus"])

MINIMUM_OMSET_FOR_BONUS = 10_000_000  # 10 juta


@router.get("/member-monthly-bonus")
async def get_member_monthly_bonus(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    staff_id: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """
    Get customers with total omset >= 10,000,000 in a specific month.
    Results are grouped by staff and product. Admin only.
    """
    db = get_db()
    
    now = get_jakarta_now()
    target_month = month or now.month
    target_year = year or now.year
    
    # Build date range for the month
    start_date = f"{target_year}-{target_month:02d}-01"
    if target_month == 12:
        end_date = f"{target_year + 1}-01-01"
    else:
        end_date = f"{target_year}-{target_month + 1:02d}-01"
    
    # Build match query
    match_query = {
        'record_date': {'$gte': start_date, '$lt': end_date}
    }
    if staff_id:
        match_query['staff_id'] = staff_id
    if product_id:
        match_query['product_id'] = product_id
    
    # Aggregate omset by customer, staff, and product
    pipeline = [
        {'$match': match_query},
        {
            '$group': {
                '_id': {
                    'customer_id_normalized': {'$toLower': {'$trim': {'input': {'$ifNull': ['$customer_id_normalized', '$customer_id']}}}},
                    'staff_id': '$staff_id',
                    'product_id': '$product_id'
                },
                'customer_name': {'$first': '$customer_name'},
                'customer_id': {'$first': '$customer_id'},
                'staff_name': {'$first': '$staff_name'},
                'product_name': {'$first': '$product_name'},
                'total_omset': {'$sum': '$depo_total'},
                'transaction_count': {'$sum': 1},
                'first_transaction': {'$min': '$record_date'},
                'last_transaction': {'$max': '$record_date'}
            }
        },
        # Filter by minimum omset
        {'$match': {'total_omset': {'$gte': MINIMUM_OMSET_FOR_BONUS}}},
        # Sort by total omset descending
        {'$sort': {'total_omset': -1}}
    ]
    
    results = await db.omset_records.aggregate(pipeline).to_list(10000)
    
    # Group by staff and product for frontend display
    grouped_data = {}
    total_qualifying_customers = 0
    total_qualifying_omset = 0
    
    for record in results:
        staff_id = record['_id']['staff_id']
        product_id = record['_id']['product_id']
        staff_name = record['staff_name'] or 'Unknown Staff'
        product_name = record['product_name'] or 'Unknown Product'
        
        # Create staff group if not exists
        if staff_id not in grouped_data:
            grouped_data[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'products': {},
                'total_customers': 0,
                'total_omset': 0
            }
        
        # Create product group if not exists
        if product_id not in grouped_data[staff_id]['products']:
            grouped_data[staff_id]['products'][product_id] = {
                'product_id': product_id,
                'product_name': product_name,
                'customers': [],
                'total_customers': 0,
                'total_omset': 0
            }
        
        # Add customer to product
        customer_data = {
            'customer_id': record['customer_id'],
            'customer_name': record['customer_name'],
            'total_omset': record['total_omset'],
            'transaction_count': record['transaction_count'],
            'first_transaction': record['first_transaction'],
            'last_transaction': record['last_transaction']
        }
        
        grouped_data[staff_id]['products'][product_id]['customers'].append(customer_data)
        grouped_data[staff_id]['products'][product_id]['total_customers'] += 1
        grouped_data[staff_id]['products'][product_id]['total_omset'] += record['total_omset']
        grouped_data[staff_id]['total_customers'] += 1
        grouped_data[staff_id]['total_omset'] += record['total_omset']
        
        total_qualifying_customers += 1
        total_qualifying_omset += record['total_omset']
    
    # Convert products dict to list for each staff
    staff_list = []
    for staff_id, staff_data in grouped_data.items():
        staff_data['products'] = list(staff_data['products'].values())
        staff_list.append(staff_data)
    
    # Sort by total omset
    staff_list.sort(key=lambda x: x['total_omset'], reverse=True)
    
    return {
        'month': target_month,
        'year': target_year,
        'month_name': datetime(target_year, target_month, 1).strftime('%B'),
        'minimum_omset': MINIMUM_OMSET_FOR_BONUS,
        'summary': {
            'total_qualifying_customers': total_qualifying_customers,
            'total_qualifying_omset': total_qualifying_omset,
            'total_staff_with_bonus_members': len(staff_list)
        },
        'data': staff_list
    }


@router.get("/member-monthly-bonus/export")
async def export_member_monthly_bonus(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2020, le=2100),
    user: User = Depends(get_admin_user)
):
    """
    Export member monthly bonus data in a flat format for CSV/Excel export.
    """
    db = get_db()
    
    now = get_jakarta_now()
    target_month = month or now.month
    target_year = year or now.year
    
    # Build date range for the month
    start_date = f"{target_year}-{target_month:02d}-01"
    if target_month == 12:
        end_date = f"{target_year + 1}-01-01"
    else:
        end_date = f"{target_year}-{target_month + 1:02d}-01"
    
    # Aggregate omset by customer, staff, and product
    pipeline = [
        {'$match': {'record_date': {'$gte': start_date, '$lt': end_date}}},
        {
            '$group': {
                '_id': {
                    'customer_id_normalized': {'$toLower': {'$trim': {'input': {'$ifNull': ['$customer_id_normalized', '$customer_id']}}}},
                    'staff_id': '$staff_id',
                    'product_id': '$product_id'
                },
                'customer_name': {'$first': '$customer_name'},
                'customer_id': {'$first': '$customer_id'},
                'staff_name': {'$first': '$staff_name'},
                'product_name': {'$first': '$product_name'},
                'total_omset': {'$sum': '$depo_total'},
                'transaction_count': {'$sum': 1}
            }
        },
        {'$match': {'total_omset': {'$gte': MINIMUM_OMSET_FOR_BONUS}}},
        {'$sort': {'staff_name': 1, 'product_name': 1, 'total_omset': -1}}
    ]
    
    results = await db.omset_records.aggregate(pipeline).to_list(10000)
    
    # Flatten for export
    export_data = []
    for record in results:
        export_data.append({
            'staff_name': record['staff_name'],
            'product_name': record['product_name'],
            'customer_id': record['customer_id'],
            'customer_name': record['customer_name'],
            'total_omset': record['total_omset'],
            'transaction_count': record['transaction_count']
        })
    
    return {
        'month': target_month,
        'year': target_year,
        'data': export_data
    }
