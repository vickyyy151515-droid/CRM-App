# Customer Follow-up Reminders Routes
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta

from .deps import get_db, get_current_user, User
from utils.helpers import get_jakarta_now, JAKARTA_TZ

router = APIRouter(tags=["Follow-ups"])

# Fixed reminder intervals (in days)
REMINDER_INTERVALS = [1, 3, 7]

# ==================== HELPER FUNCTIONS ====================

def get_reminder_level(days_since_response: int) -> dict:
    """Determine reminder level based on days since response"""
    if days_since_response >= 7:
        return {'level': 3, 'label': '7+ days', 'urgency': 'critical', 'color': 'red'}
    elif days_since_response >= 3:
        return {'level': 2, 'label': '3+ days', 'urgency': 'high', 'color': 'orange'}
    elif days_since_response >= 1:
        return {'level': 1, 'label': '1+ day', 'urgency': 'medium', 'color': 'yellow'}
    else:
        return {'level': 0, 'label': 'Today', 'urgency': 'low', 'color': 'green'}

# ==================== FOLLOW-UP ENDPOINTS ====================

@router.get("/followups/filters")
async def get_followup_filters(
    staff_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get unique products and databases from assigned records for filtering"""
    db = get_db()
    
    # Determine target staff
    if user.role == 'admin':
        target_staff_id = staff_id  # None means all staff
    else:
        target_staff_id = user.id
    
    # Get unique products and databases from assigned records with respond_status='ya'
    match_query = {
        'status': 'assigned',
        'respond_status': 'ya'
    }
    if target_staff_id:
        match_query['assigned_to'] = target_staff_id
    
    pipeline = [
        {'$match': match_query},
        {
            '$group': {
                '_id': {
                    'product_id': '$product_id',
                    'product_name': '$product_name',
                    'database_id': '$database_id',
                    'database_name': '$database_name'
                }
            }
        }
    ]
    
    results = await db.customer_records.aggregate(pipeline).to_list(1000)
    
    products = {}
    databases = {}
    
    for r in results:
        data = r['_id']
        pid = data.get('product_id')
        pname = data.get('product_name', 'Unknown')
        did = data.get('database_id')
        dname = data.get('database_name', 'Unknown')
        
        if pid and pid not in products:
            products[pid] = {'id': pid, 'name': pname}
        
        if did and did not in databases:
            databases[did] = {'id': did, 'name': dname, 'product_id': pid}
    
    return {
        'products': sorted(list(products.values()), key=lambda x: x['name']),
        'databases': sorted(list(databases.values()), key=lambda x: x['name'])
    }


@router.get("/followups")
async def get_followups(
    product_id: Optional[str] = None,
    database_id: Optional[str] = None,
    urgency: Optional[str] = None,
    staff_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get all pending follow-ups for the current staff or a specific staff (admin)"""
    db = get_db()
    
    # Determine target staff
    if user.role == 'admin':
        target_staff_id = staff_id  # None means all staff
    else:
        target_staff_id = user.id
    
    jakarta_now = get_jakarta_now()
    today = jakarta_now.strftime('%Y-%m-%d')
    
    # Find all assigned records with respond_status = 'ya'
    query = {
        'status': 'assigned',
        'respond_status': 'ya'
    }
    if target_staff_id:
        query['assigned_to'] = target_staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if database_id:
        query['database_id'] = database_id
    
    responded_records = await db.customer_records.find(query, {'_id': 0}).to_list(10000)
    
    if not responded_records:
        return {
            'followups': [],
            'summary': {
                'total': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'deposited': 0
            }
        }
    
    # Get all OMSET records for this staff to check who has deposited
    omset_records = await db.omset_records.find(
        {'staff_id': user.id},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1, 'product_id': 1}
    ).to_list(100000)
    
    # Build set of deposited customer IDs (per product)
    deposited_customers = set()
    for omset in omset_records:
        # Key is (customer_id, product_id) to match correctly
        key = (omset.get('customer_id', '').lower().strip(), omset.get('product_id', ''))
        deposited_customers.add(key)
        # Also add by customer name for matching
        name_key = (omset.get('customer_name', '').lower().strip(), omset.get('product_id', ''))
        deposited_customers.add(name_key)
    
    followups = []
    summary = {
        'total': 0,
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0,
        'deposited': 0
    }
    
    for record in responded_records:
        # Get customer identifier from row_data
        row_data = record.get('row_data', {})
        
        # Try to find customer ID or name from row_data
        customer_id = None
        customer_name = None
        
        # Common field names for customer ID
        for field in ['customer_id', 'id', 'ID', 'Id', 'user_id', 'userid', 'username']:
            if field in row_data and row_data[field]:
                customer_id = str(row_data[field]).lower().strip()
                break
        
        # Common field names for customer name
        for field in ['name', 'Name', 'nama', 'Nama', 'customer_name', 'customer']:
            if field in row_data and row_data[field]:
                customer_name = str(row_data[field]).lower().strip()
                break
        
        # Check if this customer has deposited
        product_id_rec = record.get('product_id', '')
        is_deposited = False
        
        if customer_id:
            is_deposited = (customer_id, product_id_rec) in deposited_customers
        if not is_deposited and customer_name:
            is_deposited = (customer_name, product_id_rec) in deposited_customers
        
        if is_deposited:
            summary['deposited'] += 1
            continue  # Skip deposited customers
        
        # Calculate days since response
        respond_date_str = record.get('respond_status_updated_at')
        if respond_date_str:
            if isinstance(respond_date_str, str):
                try:
                    respond_date = datetime.fromisoformat(respond_date_str.replace('Z', '+00:00'))
                except:
                    respond_date = jakarta_now
            else:
                respond_date = respond_date_str
        else:
            # Use assigned_at as fallback
            assigned_at = record.get('assigned_at')
            if assigned_at:
                if isinstance(assigned_at, str):
                    try:
                        respond_date = datetime.fromisoformat(assigned_at.replace('Z', '+00:00'))
                    except:
                        respond_date = jakarta_now
                else:
                    respond_date = assigned_at
            else:
                respond_date = jakarta_now
        
        # Make respond_date timezone aware if it isn't
        if respond_date.tzinfo is None:
            from datetime import timezone, timedelta
            JAKARTA_TZ = timezone(timedelta(hours=7))
            respond_date = respond_date.replace(tzinfo=JAKARTA_TZ)
        
        days_since = (jakarta_now - respond_date).days
        reminder_info = get_reminder_level(days_since)
        
        # Filter by urgency if specified
        if urgency and urgency != 'all':
            if reminder_info['urgency'] != urgency:
                continue
        
        # Build display name from row_data
        display_name = customer_name or customer_id or 'Unknown'
        for field in ['name', 'Name', 'nama', 'Nama', 'customer_name']:
            if field in row_data and row_data[field]:
                display_name = str(row_data[field])
                break
        
        followup = {
            'record_id': record['id'],
            'customer_display': display_name,
            'customer_id': customer_id,
            'product_id': record.get('product_id'),
            'product_name': record.get('product_name', 'Unknown'),
            'database_name': record.get('database_name', 'Unknown'),
            'row_data': row_data,
            'respond_date': respond_date.isoformat(),
            'days_since_response': days_since,
            'reminder_level': reminder_info['level'],
            'reminder_label': reminder_info['label'],
            'urgency': reminder_info['urgency'],
            'urgency_color': reminder_info['color'],
            'whatsapp_status': record.get('whatsapp_status')
        }
        
        followups.append(followup)
        summary['total'] += 1
        
        if reminder_info['urgency'] == 'critical':
            summary['critical'] += 1
        elif reminder_info['urgency'] == 'high':
            summary['high'] += 1
        elif reminder_info['urgency'] == 'medium':
            summary['medium'] += 1
        else:
            summary['low'] += 1
    
    # Sort by days_since_response descending (most urgent first)
    followups.sort(key=lambda x: x['days_since_response'], reverse=True)
    
    return {
        'followups': followups,
        'summary': summary
    }

@router.get("/followups/notifications")
async def get_followup_notifications(user: User = Depends(get_current_user)):
    """Get follow-up reminder notifications for the current staff"""
    db = get_db()
    
    if user.role != 'staff':
        return {'notifications': [], 'count': 0}
    
    # Get followups data - call the internal logic directly instead of the route function
    jakarta_now = get_jakarta_now()
    today = jakarta_now.strftime('%Y-%m-%d')
    
    # Find all assigned records with respond_status = 'ya'
    query = {
        'assigned_to': user.id,
        'status': 'assigned',
        'respond_status': 'ya'
    }
    
    records = await db.customer_records.find(query, {'_id': 0}).to_list(10000)
    
    # Calculate summary counts
    critical = 0
    high = 0
    medium = 0
    
    for record in records:
        respond_date = record.get('respond_date', '')
        if not respond_date:
            continue
            
        try:
            respond_dt = datetime.strptime(respond_date, '%Y-%m-%d').replace(tzinfo=JAKARTA_TZ)
            days_since = (jakarta_now - respond_dt).days
            
            # Check if already deposited after respond
            is_deposited = await db.omset_records.find_one({
                'customer_id_normalized': record.get('customer_id_normalized') or record.get('customer_id', '').strip().upper(),
                'record_date': {'$gte': respond_date}
            })
            
            if is_deposited:
                continue
            
            if days_since >= 7:
                critical += 1
            elif days_since >= 3:
                high += 1
            elif days_since >= 1:
                medium += 1
        except:
            continue
    
    notifications = []
    
    # Generate notifications for critical and high urgency
    if critical > 0:
        notifications.append({
            'type': 'followup_critical',
            'title': 'Critical Follow-ups',
            'message': f'You have {critical} customer(s) waiting 7+ days for follow-up!',
            'urgency': 'critical',
            'count': critical
        })
    
    if high > 0:
        notifications.append({
            'type': 'followup_high',
            'title': 'High Priority Follow-ups',
            'message': f'You have {high} customer(s) waiting 3+ days for follow-up',
            'urgency': 'high',
            'count': high
        })
    
    return {
        'notifications': notifications,
        'count': critical + high,
        'summary': {'critical': critical, 'high': high, 'medium': medium, 'total': critical + high + medium}
    }

@router.get("/followups/check-deposited/{record_id}")
async def check_if_deposited(record_id: str, user: User = Depends(get_current_user)):
    """Check if a specific customer has deposited"""
    db = get_db()
    
    record = await db.customer_records.find_one({'id': record_id}, {'_id': 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if user.role == 'staff' and record.get('assigned_to') != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    row_data = record.get('row_data', {})
    product_id = record.get('product_id', '')
    
    # Get customer identifiers
    customer_id = None
    customer_name = None
    
    for field in ['customer_id', 'id', 'ID', 'Id', 'user_id', 'userid', 'username']:
        if field in row_data and row_data[field]:
            customer_id = str(row_data[field]).lower().strip()
            break
    
    for field in ['name', 'Name', 'nama', 'Nama', 'customer_name', 'customer']:
        if field in row_data and row_data[field]:
            customer_name = str(row_data[field]).lower().strip()
            break
    
    # Search in OMSET records
    omset_query = {'product_id': product_id}
    if user.role == 'staff':
        omset_query['staff_id'] = user.id
    
    omset_records = await db.omset_records.find(omset_query, {'_id': 0}).to_list(100000)
    
    is_deposited = False
    deposit_info = None
    
    for omset in omset_records:
        omset_customer_id = str(omset.get('customer_id', '')).lower().strip()
        omset_customer_name = str(omset.get('customer_name', '')).lower().strip()
        
        if customer_id and omset_customer_id == customer_id:
            is_deposited = True
            deposit_info = {
                'record_date': omset.get('record_date'),
                'nominal': omset.get('nominal'),
                'depo_total': omset.get('depo_total')
            }
            break
        elif customer_name and omset_customer_name == customer_name:
            is_deposited = True
            deposit_info = {
                'record_date': omset.get('record_date'),
                'nominal': omset.get('nominal'),
                'depo_total': omset.get('depo_total')
            }
            break
    
    return {
        'record_id': record_id,
        'is_deposited': is_deposited,
        'deposit_info': deposit_info
    }
