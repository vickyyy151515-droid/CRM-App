# Conversion Funnel Routes
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from .deps import get_db, get_current_user, get_admin_user, get_jakarta_now, User

router = APIRouter(tags=["Conversion Funnel"])

# ==================== HELPER FUNCTIONS ====================

# Extended list of possible username fields in row_data
USERNAME_KEYS = [
    'username', 'Username', 'USERNAME', 'USER', 'user', 
    'name', 'Name', 'NAME',
    'customer_id', 'customer', 'Customer', 'CUSTOMER',
    'id', 'ID', 'Id',
    'userid', 'UserId', 'user_id', 'UserID',
    'member', 'Member', 'MEMBER',
    'account', 'Account', 'ACCOUNT'
]

def extract_username(record: dict) -> tuple:
    """
    Extract username from a customer record.
    Returns (normalized_username, original_username) or (None, None) if not found.
    """
    row_data = record.get('row_data', {})
    
    # Try to get username from row_data
    for key in USERNAME_KEYS:
        if key in row_data and row_data[key]:
            val = row_data[key]
            if isinstance(val, (str, int, float)):
                original = str(val).strip()
                if original:
                    return (original.upper(), original)
    
    # Fallback to record's customer_id
    if record.get('customer_id'):
        original = str(record['customer_id']).strip()
        if original:
            return (original.upper(), original)
    
    return (None, None)


# ==================== CONVERSION FUNNEL ENDPOINTS ====================

@router.get("/funnel")
async def get_conversion_funnel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    database_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """
    Get conversion funnel data showing:
    Records Assigned → WhatsApp Reached → Responded → Deposited
    """
    db = get_db()
    
    # If staff, force filter by their ID
    if user.role == 'staff':
        staff_id = user.id
    
    # Default to last 30 days if no date range specified
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Build query for assigned records
    query = {'status': 'assigned'}
    
    if staff_id:
        query['assigned_to'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
        
    if database_id:
        query['database_id'] = database_id
    
    # Get all assigned records with row_data to extract username
    assigned_records = await db.customer_records.find(
        query,
        {'_id': 0, 'id': 1, 'customer_id': 1, 'product_id': 1, 'database_id': 1, 
         'whatsapp_status': 1, 'respond_status': 1, 'assigned_to': 1, 'row_data': 1}
    ).to_list(100000)
    
    total_assigned = len(assigned_records)
    
    # Stage 2: WhatsApp Reached (whatsapp_status = 'ada' or 'ceklis1')
    wa_reached = [r for r in assigned_records if r.get('whatsapp_status') in ['ada', 'ceklis1']]
    total_wa_reached = len(wa_reached)
    
    # Stage 3: Responded (respond_status = 'ya')
    responded = [r for r in assigned_records if r.get('respond_status') == 'ya']
    total_responded = len(responded)
    
    # Stage 4: Deposited - get customer_ids that have OMSET records
    # IMPORTANT: Don't filter by date here - we want to check if assigned customers
    # have EVER deposited, not just within the date range
    omset_query = {}
    if staff_id:
        omset_query['staff_id'] = staff_id
    if product_id:
        omset_query['product_id'] = product_id
    
    omset_records = await db.omset_records.find(
        omset_query,
        {'_id': 0, 'customer_id': 1, 'customer_id_normalized': 1, 'product_id': 1}
    ).to_list(500000)
    
    # Create set of deposited customer identifiers (normalized username)
    deposited_customers = set()
    for omset in omset_records:
        # Use normalized customer_id (uppercase username)
        cust_id = omset.get('customer_id_normalized') or omset.get('customer_id', '').strip().upper()
        prod_id = omset.get('product_id')
        if cust_id:
            deposited_customers.add((cust_id, prod_id))
            # Also add without product for looser matching
            deposited_customers.add((cust_id, None))
    
    # Check how many assigned records have deposited
    # Match by username from row_data
    deposited_from_assigned = 0
    deposited_customer_list = []  # Track deposited customers with details
    
    for record in assigned_records:
        # Use helper function to extract username
        username, original_username = extract_username(record)
        
        if not username:
            continue
            
        prod_id = record.get('product_id')
        
        # Check if this customer deposited (with or without product match)
        if (username, prod_id) in deposited_customers or (username, None) in deposited_customers:
            deposited_from_assigned += 1
            # Add to deposited list with details
            deposited_customer_list.append({
                'username': original_username,
                'product_id': prod_id,
                'assigned_to': record.get('assigned_to')
            })
    
    total_deposited = deposited_from_assigned
    
    # Calculate conversion rates
    def calc_rate(current, previous):
        if previous == 0:
            return 0
        return round((current / previous) * 100, 1)
    
    funnel_data = {
        'date_range': {
            'start': start_date,
            'end': end_date
        },
        'stages': [
            {
                'name': 'Assigned',
                'count': total_assigned,
                'rate': 100,
                'color': '#6366f1'
            },
            {
                'name': 'WhatsApp Reached',
                'count': total_wa_reached,
                'rate': calc_rate(total_wa_reached, total_assigned),
                'color': '#22c55e'
            },
            {
                'name': 'Responded',
                'count': total_responded,
                'rate': calc_rate(total_responded, total_wa_reached),
                'color': '#f59e0b'
            },
            {
                'name': 'Deposited',
                'count': total_deposited,
                'rate': calc_rate(total_deposited, total_responded),
                'color': '#10b981',
                'customers': deposited_customer_list[:50]  # Limit to first 50 for performance
            }
        ],
        'overall_conversion': calc_rate(total_deposited, total_assigned),
        'filters': {
            'product_id': product_id,
            'staff_id': staff_id,
            'database_id': database_id
        },
        'debug': {
            'total_omset_records': len(omset_records),
            'unique_depositors_in_omset': len(deposited_customers),
            'assigned_records_with_username': sum(1 for r in assigned_records if r.get('row_data') or r.get('customer_id'))
        }
    }
    
    return funnel_data


@router.get("/funnel/by-product")
async def get_funnel_by_product(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get conversion funnel breakdown by product"""
    db = get_db()
    
    # Default date range (for display purposes only)
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Build base query
    query = {'status': 'assigned'}
    if user.role == 'staff':
        query['assigned_to'] = user.id
    
    # Get all assigned records with row_data
    assigned_records = await db.customer_records.find(
        query,
        {'_id': 0, 'id': 1, 'customer_id': 1, 'product_id': 1, 'product_name': 1,
         'whatsapp_status': 1, 'respond_status': 1, 'row_data': 1}
    ).to_list(500000)
    
    # Get ALL OMSET records (no date filter - check if customer ever deposited)
    omset_query = {}
    if user.role == 'staff':
        omset_query['staff_id'] = user.id
    
    omset_records = await db.omset_records.find(
        omset_query,
        {'_id': 0, 'customer_id': 1, 'customer_id_normalized': 1, 'product_id': 1}
    ).to_list(500000)
    
    # Create set of ALL deposited customers (regardless of product for matching)
    all_deposited = set()
    deposited_by_product = {}  # product_id -> set of usernames
    for omset in omset_records:
        cust_id = omset.get('customer_id_normalized') or omset.get('customer_id', '').strip().upper()
        prod_id = omset.get('product_id')
        if cust_id:
            all_deposited.add(cust_id)
            if prod_id not in deposited_by_product:
                deposited_by_product[prod_id] = set()
            deposited_by_product[prod_id].add(cust_id)
    
    # Group by product
    products = {}
    for record in assigned_records:
        prod_id = record.get('product_id', 'unknown')
        prod_name = record.get('product_name', 'Unknown Product')
        
        if prod_id not in products:
            products[prod_id] = {
                'product_id': prod_id,
                'product_name': prod_name,
                'assigned': 0,
                'wa_reached': 0,
                'responded': 0,
                'deposited': 0,
                'deposited_customers': []
            }
        
        products[prod_id]['assigned'] += 1
        
        if record.get('whatsapp_status') in ['ada', 'ceklis1']:
            products[prod_id]['wa_reached'] += 1
        
        if record.get('respond_status') == 'ya':
            products[prod_id]['responded'] += 1
        
        # Check if deposited using helper function
        username, original_username = extract_username(record)
        
        # Match: customer deposited with same product OR deposited at all
        if username and (username in deposited_by_product.get(prod_id, set()) or username in all_deposited):
            products[prod_id]['deposited'] += 1
            if original_username:
                products[prod_id]['deposited_customers'].append(original_username)
    
    # Calculate conversion rates
    result = []
    for prod in products.values():
        assigned = prod['assigned']
        wa_reached = prod['wa_reached']
        responded = prod['responded']
        deposited = prod['deposited']
        
        result.append({
            'product_id': prod['product_id'],
            'product_name': prod['product_name'],
            'stages': {
                'assigned': assigned,
                'wa_reached': wa_reached,
                'responded': responded,
                'deposited': deposited
            },
            'deposited_customers': prod['deposited_customers'][:50],  # Limit for performance
            'conversion_rates': {
                'assigned_to_wa': round((wa_reached / assigned * 100), 1) if assigned > 0 else 0,
                'wa_to_responded': round((responded / wa_reached * 100), 1) if wa_reached > 0 else 0,
                'responded_to_deposited': round((deposited / responded * 100), 1) if responded > 0 else 0,
                'overall': round((deposited / assigned * 100), 1) if assigned > 0 else 0
            }
        })
    
    # Sort by assigned count
    result.sort(key=lambda x: x['stages']['assigned'], reverse=True)
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'products': result,
        'debug': {
            'total_omset_records': len(omset_records),
            'unique_depositors': len(all_deposited)
        }
    }


@router.get("/funnel/by-staff")
async def get_funnel_by_staff(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get conversion funnel breakdown by staff (Admin only)"""
    db = get_db()
    
    # Default date range (for display purposes only)
    jakarta_now = get_jakarta_now()
    if not end_date:
        end_date = jakarta_now.strftime('%Y-%m-%d')
    if not start_date:
        start_date = (jakarta_now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Get all assigned records with row_data to extract username
    assigned_records = await db.customer_records.find(
        {'status': 'assigned'},
        {'_id': 0, 'id': 1, 'customer_id': 1, 'product_id': 1, 'assigned_to': 1,
         'whatsapp_status': 1, 'respond_status': 1, 'row_data': 1}
    ).to_list(500000)
    
    # Get staff info
    all_staff = await db.users.find(
        {'role': 'staff'},
        {'_id': 0, 'id': 1, 'name': 1}
    ).to_list(1000)
    staff_map = {s['id']: s['name'] for s in all_staff}
    
    # Get ALL OMSET records (no date filter - check if customer ever deposited)
    omset_records = await db.omset_records.find(
        {},
        {'_id': 0, 'customer_id': 1, 'customer_id_normalized': 1, 'product_id': 1, 'staff_id': 1}
    ).to_list(500000)
    
    # Build set of ALL deposited customers (regardless of which staff)
    all_deposited = set()
    for omset in omset_records:
        cust_id = omset.get('customer_id_normalized') or omset.get('customer_id', '').strip().upper()
        if cust_id:
            all_deposited.add(cust_id)
    
    # Group by staff
    staff_data = {}
    for record in assigned_records:
        staff_id = record.get('assigned_to')
        if not staff_id:
            continue
        
        staff_name = staff_map.get(staff_id, 'Unknown Staff')
        
        if staff_id not in staff_data:
            staff_data[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'assigned': 0,
                'wa_reached': 0,
                'responded': 0,
                'deposited': 0,
                'deposited_customers': []
            }
        
        staff_data[staff_id]['assigned'] += 1
        
        if record.get('whatsapp_status') in ['ada', 'ceklis1']:
            staff_data[staff_id]['wa_reached'] += 1
        
        if record.get('respond_status') == 'ya':
            staff_data[staff_id]['responded'] += 1
        
        # Check if deposited using helper function
        username, original_username = extract_username(record)
        
        # Match: customer deposited with ANY staff (not just this staff)
        if username and username in all_deposited:
            staff_data[staff_id]['deposited'] += 1
            if original_username:
                staff_data[staff_id]['deposited_customers'].append(original_username)
    
    # Calculate conversion rates
    result = []
    for staff in staff_data.values():
        assigned = staff['assigned']
        wa_reached = staff['wa_reached']
        responded = staff['responded']
        deposited = staff['deposited']
        
        result.append({
            'staff_id': staff['staff_id'],
            'staff_name': staff['staff_name'],
            'stages': {
                'assigned': assigned,
                'wa_reached': wa_reached,
                'responded': responded,
                'deposited': deposited
            },
            'deposited_customers': staff['deposited_customers'][:50],  # Limit for performance
            'conversion_rates': {
                'assigned_to_wa': round((wa_reached / assigned * 100), 1) if assigned > 0 else 0,
                'wa_to_responded': round((responded / wa_reached * 100), 1) if wa_reached > 0 else 0,
                'responded_to_deposited': round((deposited / responded * 100), 1) if responded > 0 else 0,
                'overall': round((deposited / assigned * 100), 1) if assigned > 0 else 0
            }
        })
    
    # Sort by overall conversion rate
    result.sort(key=lambda x: x['conversion_rates']['overall'], reverse=True)
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'staff': result,
        'debug': {
            'total_omset_records': len(omset_records),
            'unique_depositors': len(all_deposited)
        }
    }


@router.get("/funnel/trend")
async def get_funnel_trend(
    days: int = 7,
    user: User = Depends(get_current_user)
):
    """Get daily conversion funnel trend for the past N days"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    
    # Build base query for records
    query = {'status': 'assigned'}
    if user.role == 'staff':
        query['assigned_to'] = user.id
    
    # Get all assigned records (we'll track when they were modified)
    assigned_records = await db.customer_records.find(
        query,
        {'_id': 0, 'id': 1, 'customer_id': 1, 'product_id': 1,
         'whatsapp_status': 1, 'respond_status': 1, 'assigned_at': 1}
    ).to_list(100000)
    
    # Get daily OMSET counts
    trend_data = []
    for i in range(days - 1, -1, -1):
        date = (jakarta_now - timedelta(days=i)).strftime('%Y-%m-%d')
        
        omset_query = {'record_date': date}
        if user.role == 'staff':
            omset_query['staff_id'] = user.id
        
        daily_deposits = await db.omset_records.count_documents(omset_query)
        
        trend_data.append({
            'date': date,
            'deposited': daily_deposits
        })
    
    return {
        'trend': trend_data,
        'current_funnel': {
            'assigned': len(assigned_records),
            'wa_reached': len([r for r in assigned_records if r.get('whatsapp_status') in ['ada', 'ceklis1']]),
            'responded': len([r for r in assigned_records if r.get('respond_status') == 'ya'])
        }
    }
