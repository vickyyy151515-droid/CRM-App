# OMSET CRM Routes
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import io
import csv
import jwt

from .deps import get_db, get_current_user, get_admin_user, get_jakarta_now, User, JWT_SECRET, JWT_ALGORITHM

router = APIRouter(tags=["OMSET CRM"])

# Helper function to normalize customer ID for consistent NDP/RDP comparison
def normalize_customer_id(customer_id: str) -> str:
    """Normalize customer ID by removing leading/trailing spaces and converting to lowercase"""
    if not customer_id:
        return ""
    return customer_id.strip().lower()

# ==================== PYDANTIC MODELS ====================

class OmsetRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: str
    staff_id: str
    staff_name: str
    record_date: str
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    depo_total: float
    keterangan: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())
    updated_at: Optional[datetime] = None

class OmsetRecordCreate(BaseModel):
    product_id: str
    record_date: str
    customer_name: str
    customer_id: str
    nominal: float
    depo_kelipatan: float = 1.0
    keterangan: Optional[str] = None

class OmsetRecordUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    nominal: Optional[float] = None
    depo_kelipatan: Optional[float] = None
    keterangan: Optional[str] = None

# ==================== OMSET ENDPOINTS ====================

@router.get("/omset/dashboard-stats")
async def get_omset_dashboard_stats(user: User = Depends(get_current_user)):
    """Get dashboard stats: Total OMSET for current year and Monthly ATH (All-Time High)"""
    db = get_db()
    
    # Get current year and month in Jakarta timezone
    jakarta_now = get_jakarta_now()
    current_year = jakarta_now.year
    current_month = jakarta_now.month
    
    # Calculate total OMSET for the current year (all staff, all products)
    year_start = f"{current_year}-01-01"
    year_end = f"{current_year}-12-31"
    
    year_records = await db.omset_records.find(
        {'record_date': {'$gte': year_start, '$lte': year_end}},
        {'_id': 0, 'depo_total': 1}
    ).to_list(500000)
    
    total_omset_year = sum(r.get('depo_total', 0) or 0 for r in year_records)
    
    # Calculate Monthly ATH (highest single day OMSET in current month)
    month_str = f"{current_year}-{str(current_month).zfill(2)}"
    
    month_records = await db.omset_records.find(
        {'record_date': {'$regex': f'^{month_str}'}},
        {'_id': 0, 'record_date': 1, 'depo_total': 1}
    ).to_list(100000)
    
    # Group by date and sum
    daily_totals = {}
    for record in month_records:
        date = record['record_date']
        if date not in daily_totals:
            daily_totals[date] = 0
        daily_totals[date] += record.get('depo_total', 0) or 0
    
    # Find the ATH (All-Time High) for the month
    ath_date = None
    ath_amount = 0
    
    for date, total in daily_totals.items():
        if total > ath_amount:
            ath_amount = total
            ath_date = date
    
    return {
        'year': current_year,
        'month': current_month,
        'total_omset_year': total_omset_year,
        'monthly_ath': {
            'date': ath_date,
            'amount': ath_amount
        }
    }

@router.post("/omset", response_model=OmsetRecord)
async def create_omset_record(record_data: OmsetRecordCreate, user: User = Depends(get_current_user)):
    db = get_db()
    product = await db.products.find_one({'id': record_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    depo_total = record_data.nominal * record_data.depo_kelipatan
    
    # Normalize customer_id for consistent NDP/RDP comparison
    normalized_cid = normalize_customer_id(record_data.customer_id)
    
    # Check if notes contain "tambahan" (case-insensitive) - if so, force RDP
    is_tambahan = record_data.keterangan and 'tambahan' in record_data.keterangan.lower()
    
    # Determine if this is NDP or RDP
    if is_tambahan:
        # If "tambahan" in notes, always count as RDP regardless of history
        customer_type = 'RDP'
    else:
        # Normal logic: Check for existing records with same normalized customer_id before this date
        existing_record = await db.omset_records.find_one({
            'customer_id_normalized': normalized_cid,
            'product_id': record_data.product_id,
            'record_date': {'$lt': record_data.record_date}
        })
        
        # Also check old records that might not have normalized field
        if not existing_record:
            # Query all records for this product and check normalized match
            potential_matches = await db.omset_records.find({
                'product_id': record_data.product_id,
                'record_date': {'$lt': record_data.record_date}
            }, {'customer_id': 1, 'customer_id_normalized': 1}).to_list(10000)
            
            for match in potential_matches:
                match_normalized = match.get('customer_id_normalized') or normalize_customer_id(match['customer_id'])
                if match_normalized == normalized_cid:
                    existing_record = match
                    break
        
        customer_type = 'RDP' if existing_record else 'NDP'
    
    record = OmsetRecord(
        product_id=record_data.product_id,
        product_name=product['name'],
        staff_id=user.id,
        staff_name=user.name,
        record_date=record_data.record_date,
        customer_name=record_data.customer_name.strip(),  # Trim whitespace from name
        customer_id=record_data.customer_id.strip(),  # Trim whitespace from original ID
        nominal=record_data.nominal,
        depo_kelipatan=record_data.depo_kelipatan,
        depo_total=depo_total,
        keterangan=record_data.keterangan
    )
    
    doc = record.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['customer_id_normalized'] = normalized_cid  # Store normalized version for comparison
    doc['customer_type'] = customer_type  # Store NDP/RDP classification
    
    await db.omset_records.insert_one(doc)
    return record

@router.get("/omset")
async def get_omset_records(
    product_id: Optional[str] = None,
    record_date: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    db = get_db()
    query = {}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if record_date:
        query['record_date'] = record_date
    elif start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).sort([('record_date', -1), ('created_at', -1)]).to_list(10000)
    
    for record in records:
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
        if record.get('updated_at') and isinstance(record['updated_at'], str):
            record['updated_at'] = datetime.fromisoformat(record['updated_at'])
    
    return records

@router.put("/omset/{record_id}")
async def update_omset_record(record_id: str, update_data: OmsetRecordUpdate, user: User = Depends(get_current_user)):
    db = get_db()
    record = await db.omset_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    if user.role == 'staff' and record['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only update your own records")
    
    update_fields = {}
    if update_data.customer_name is not None:
        update_fields['customer_name'] = update_data.customer_name
    if update_data.customer_id is not None:
        update_fields['customer_id'] = update_data.customer_id
    if update_data.nominal is not None:
        update_fields['nominal'] = update_data.nominal
    if update_data.depo_kelipatan is not None:
        update_fields['depo_kelipatan'] = update_data.depo_kelipatan
    if update_data.keterangan is not None:
        update_fields['keterangan'] = update_data.keterangan
    
    nominal = update_data.nominal if update_data.nominal is not None else record['nominal']
    kelipatan = update_data.depo_kelipatan if update_data.depo_kelipatan is not None else record['depo_kelipatan']
    update_fields['depo_total'] = nominal * kelipatan
    update_fields['updated_at'] = get_jakarta_now().isoformat()
    
    await db.omset_records.update_one({'id': record_id}, {'$set': update_fields})
    
    return {'message': 'Record updated successfully'}

@router.delete("/omset/{record_id}")
async def delete_omset_record(record_id: str, user: User = Depends(get_current_user)):
    """Soft delete - moves record to trash for potential restore"""
    db = get_db()
    record = await db.omset_records.find_one({'id': record_id})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Admins can delete any record, staff can only delete their own
    if user.role == 'staff' and record['staff_id'] != user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own records")
    
    # Move to trash collection instead of permanent delete
    trash_record = {**record}
    trash_record.pop('_id', None)  # Remove MongoDB _id
    trash_record['deleted_at'] = datetime.now(timezone.utc).isoformat()
    trash_record['deleted_by'] = user.id
    trash_record['deleted_by_name'] = user.name
    
    await db.omset_trash.insert_one(trash_record)
    await db.omset_records.delete_one({'id': record_id})
    
    return {
        'message': 'Record moved to trash',
        'deleted_id': record_id,
        'can_restore': True
    }

@router.post("/omset/restore/{record_id}")
async def restore_omset_record(record_id: str, user: User = Depends(get_current_user)):
    """Restore a deleted OMSET record from trash"""
    db = get_db()
    
    # Only admins can restore
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Only admins can restore records")
    
    # Find in trash
    trash_record = await db.omset_trash.find_one({'id': record_id})
    if not trash_record:
        raise HTTPException(status_code=404, detail="Record not found in trash")
    
    # Check if already exists in main collection (prevent duplicates)
    existing = await db.omset_records.find_one({'id': record_id})
    if existing:
        # Remove from trash since it's already restored
        await db.omset_trash.delete_one({'id': record_id})
        raise HTTPException(status_code=400, detail="Record already exists, removed from trash")
    
    # Restore to main collection
    restored_record = {**trash_record}
    restored_record.pop('_id', None)
    restored_record.pop('deleted_at', None)
    restored_record.pop('deleted_by', None)
    restored_record.pop('deleted_by_name', None)
    
    await db.omset_records.insert_one(restored_record)
    await db.omset_trash.delete_one({'id': record_id})
    
    return {
        'message': 'Record restored successfully',
        'restored_id': record_id,
        'record': {
            'id': restored_record['id'],
            'customer_id': restored_record['customer_id'],
            'staff_name': restored_record['staff_name'],
            'product_name': restored_record['product_name'],
            'depo_total': restored_record.get('depo_total', 0),
            'record_date': restored_record['record_date']
        }
    }

@router.get("/omset/trash")
async def get_omset_trash(
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get recently deleted OMSET records (admin only)"""
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Only admins can view trash")
    
    db = get_db()
    
    # Get recent deletions, sorted by deletion time
    trash_records = await db.omset_trash.find(
        {},
        {'_id': 0}
    ).sort('deleted_at', -1).limit(limit).to_list(limit)
    
    return {
        'records': trash_records,
        'count': len(trash_records)
    }

@router.delete("/omset/trash/{record_id}")
async def permanently_delete_omset(record_id: str, user: User = Depends(get_current_user)):
    """Permanently delete a record from trash (cannot be undone)"""
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Only admins can permanently delete")
    
    db = get_db()
    result = await db.omset_trash.delete_one({'id': record_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found in trash")
    
    return {'message': 'Record permanently deleted', 'deleted_id': record_id}

@router.delete("/omset/trash")
async def empty_omset_trash(user: User = Depends(get_current_user)):
    """Empty all records from trash (admin only)"""
    if user.role != 'master_admin':
        raise HTTPException(status_code=403, detail="Only master admin can empty trash")
    
    db = get_db()
    result = await db.omset_trash.delete_many({})
    
    return {'message': f'Trash emptied, {result.deleted_count} records permanently deleted'}

@router.get("/omset/summary")
async def get_omset_summary(
    product_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    db = get_db()
    query = {}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Helper function to normalize customer ID
    def normalize_customer_id(customer_id: str) -> str:
        if not customer_id:
            return ""
        return customer_id.strip().lower()
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get ALL records (unfiltered by date) for building customer_first_date maps
    # We need this to determine if a customer is NDP or RDP for each staff
    all_query = {}
    if product_id:
        all_query['product_id'] = product_id
    all_records_for_ndp = await db.omset_records.find(all_query, {'_id': 0}).to_list(100000)
    
    # Build customer_first_date PER STAFF (for staff-level NDP/RDP calculation)
    # Key: (staff_id, customer_id_normalized, product_id) -> first_date
    staff_customer_first_date = {}
    for record in sorted(all_records_for_ndp, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        staff_id_rec = record['staff_id']
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (staff_id_rec, cid_normalized, record['product_id'])
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Build global customer_first_date (for daily totals - customer's first deposit ever)
    # This is for the overall NDP/RDP totals shown in daily view
    global_customer_first_date = {}
    for record in sorted(all_records_for_ndp, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        if key not in global_customer_first_date:
            global_customer_first_date[key] = record['record_date']
    
    daily_summary = {}
    staff_summary = {}
    product_summary = {}
    total_nominal = 0
    total_depo = 0
    total_records = len(records)
    total_ndp = 0
    total_rdp = 0
    
    # Tracking sets for staff and product unique customers
    staff_ndp_customers = {}
    staff_rdp_customers = {}
    product_ndp_customers = {}
    product_rdp_customers = {}
    
    for record in records:
        date = record['record_date']
        staff_name = record['staff_name']
        staff_id_rec = record['staff_id']
        product_name = record['product_name']
        product_id_rec = record['product_id']
        nominal = record.get('nominal', 0) or 0
        depo_total = record.get('depo_total', 0) or 0
        
        # Use normalized customer_id
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        
        # Determine global NDP/RDP (for daily totals - customer's first deposit EVER)
        global_key = (cid_normalized, product_id_rec)
        global_first_date = global_customer_first_date.get(global_key)
        
        # Determine staff-specific NDP/RDP (for staff breakdown - customer's first deposit WITH THIS STAFF)
        staff_key = (staff_id_rec, cid_normalized, product_id_rec)
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        # Check if tambahan record
        is_tambahan = is_tambahan_record(record)
        
        # Global NDP/RDP (for daily summary)
        if is_tambahan:
            is_global_ndp = False
        else:
            is_global_ndp = global_first_date == date
        
        # Staff-specific NDP/RDP (for staff breakdown)
        if is_tambahan:
            is_staff_ndp = False
        else:
            is_staff_ndp = staff_first_date == date
        
        total_nominal += nominal
        total_depo += depo_total
        
        # Initialize daily summary with tracking sets
        if date not in daily_summary:
            daily_summary[date] = {
                'date': date, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_customers': set(),  # Track unique NDP customers
                'rdp_customers': set(),  # Track unique RDP customers
                'ndp_total': 0,
                'rdp_total': 0
            }
        daily_summary[date]['total_nominal'] += nominal
        daily_summary[date]['total_depo'] += depo_total
        daily_summary[date]['count'] += 1
        
        if is_global_ndp:
            daily_summary[date]['ndp_customers'].add(cid_normalized)
            daily_summary[date]['ndp_total'] += depo_total
        else:
            daily_summary[date]['rdp_customers'].add(cid_normalized)
            daily_summary[date]['rdp_total'] += depo_total
        
        # Initialize staff summary with tracking sets
        if staff_id_rec not in staff_summary:
            staff_summary[staff_id_rec] = {
                'staff_id': staff_id_rec, 
                'staff_name': staff_name, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_count': 0,
                'rdp_count': 0
            }
            staff_ndp_customers[staff_id_rec] = set()
            staff_rdp_customers[staff_id_rec] = set()
        
        staff_summary[staff_id_rec]['total_nominal'] += nominal
        staff_summary[staff_id_rec]['total_depo'] += depo_total
        staff_summary[staff_id_rec]['count'] += 1
        
        # Use STAFF-SPECIFIC NDP/RDP for staff breakdown
        if is_staff_ndp:
            if cid_normalized not in staff_ndp_customers[staff_id_rec]:
                staff_ndp_customers[staff_id_rec].add(cid_normalized)
                staff_summary[staff_id_rec]['ndp_count'] += 1
        else:
            if cid_normalized not in staff_rdp_customers[staff_id_rec]:
                staff_rdp_customers[staff_id_rec].add(cid_normalized)
                staff_summary[staff_id_rec]['rdp_count'] += 1
        
        # Initialize product summary with tracking sets
        if product_id_rec not in product_summary:
            product_summary[product_id_rec] = {
                'product_id': product_id_rec, 
                'product_name': product_name, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_count': 0,
                'rdp_count': 0
            }
            product_ndp_customers[product_id_rec] = set()
            product_rdp_customers[product_id_rec] = set()
        
        product_summary[product_id_rec]['total_nominal'] += nominal
        product_summary[product_id_rec]['total_depo'] += depo_total
        product_summary[product_id_rec]['count'] += 1
        
        # Use global NDP/RDP for product summary (consistent with daily totals)
        if is_global_ndp:
            if cid_normalized not in product_ndp_customers[product_id_rec]:
                product_ndp_customers[product_id_rec].add(cid_normalized)
                product_summary[product_id_rec]['ndp_count'] += 1
        else:
            if cid_normalized not in product_rdp_customers[product_id_rec]:
                product_rdp_customers[product_id_rec].add(cid_normalized)
                product_summary[product_id_rec]['rdp_count'] += 1
    
    daily_list = []
    for date, data in daily_summary.items():
        daily_list.append({
            'date': data['date'],
            'total_nominal': data['total_nominal'],
            'total_depo': data['total_depo'],
            'count': data['count'],
            'ndp_count': len(data['ndp_customers']),
            'rdp_count': len(data['rdp_customers']),  # Count unique RDP customers
            'ndp_total': data['ndp_total'],
            'rdp_total': data['rdp_total']
        })
        total_ndp += len(data['ndp_customers'])
        total_rdp += len(data['rdp_customers'])  # Sum unique RDP customers
    
    return {
        'total': {
            'total_nominal': total_nominal,
            'total_depo': total_depo,
            'total_records': total_records,
            'total_ndp': total_ndp,
            'total_rdp': total_rdp
        },
        'daily': sorted(daily_list, key=lambda x: x['date'], reverse=True),
        'by_staff': sorted(staff_summary.values(), key=lambda x: x['total_depo'], reverse=True),
        'by_product': sorted(product_summary.values(), key=lambda x: x['total_depo'], reverse=True)
    }

@router.get("/omset/dates")
async def get_omset_dates(product_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """Get list of dates that have omset records"""
    db = get_db()
    query = {}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    if product_id:
        query['product_id'] = product_id
    
    records = await db.omset_records.find(query, {'_id': 0, 'record_date': 1}).to_list(100000)
    
    dates = sorted(set(r['record_date'] for r in records), reverse=True)
    return dates

@router.get("/omset/export")
async def export_omset_records(
    request: Request,
    product_id: Optional[str] = None,
    record_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    staff_id: Optional[str] = None,
    format: str = "csv",
    token: Optional[str] = None
):
    """Export OMSET records to CSV format"""
    db = get_db()
    
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user_data:
                raise HTTPException(status_code=401, detail="User not found")
            user = User(**user_data)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        security = HTTPBearer()
        credentials = await security(request)
        user = await get_current_user(credentials)
    
    query = {}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    elif staff_id:
        query['staff_id'] = staff_id
    
    if product_id:
        query['product_id'] = product_id
    
    if record_date:
        query['record_date'] = record_date
    elif start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).sort([('record_date', -1), ('created_at', -1)]).to_list(100000)
    
    all_query = {'product_id': product_id} if product_id else {}
    if user.role == 'staff':
        all_query['staff_id'] = user.id
    
    all_records = await db.omset_records.find(all_query, {'_id': 0}).to_list(100000)
    
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Use normalized customer_id for comparison
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Date', 'Product', 'Staff', 'Customer ID', 'Nominal', 'Kelipatan', 'Depo Total', 'Type', 'Keterangan'])
    
    for record in records:
        # Use normalized customer_id for comparison
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        first_date = customer_first_date.get(key)
        
        # Check if "tambahan" in notes - if so, always RDP
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            record_type = 'RDP'
        else:
            record_type = 'NDP' if first_date == record['record_date'] else 'RDP'
        
        writer.writerow([
            record['record_date'],
            record['product_name'],
            record['staff_name'],
            record['customer_id'],
            record.get('nominal', 0),
            record.get('depo_kelipatan', 1),
            record.get('depo_total', 0),
            record_type,
            record.get('keterangan', '')
        ])
    
    output.seek(0)
    
    date_part = record_date if record_date else f"{start_date or 'all'}_to_{end_date or 'now'}"
    filename = f"omset_export_{date_part}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/octet-stream",
            "Cache-Control": "no-cache"
        }
    )

@router.get("/omset/export-summary")
async def export_omset_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    token: Optional[str] = None
):
    """Export OMSET summary to CSV (Admin only)"""
    db = get_db()
    
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_data = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user_data:
                raise HTTPException(status_code=401, detail="User not found")
            user = User(**user_data)
            if user.role != 'admin':
                raise HTTPException(status_code=403, detail="Admin access required")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        from fastapi.security import HTTPBearer
        security = HTTPBearer()
        credentials = await security(request)
        user = await get_admin_user(await get_current_user(credentials))
    
    query = {}
    
    if product_id:
        query['product_id'] = product_id
    
    if start_date and end_date:
        query['record_date'] = {'$gte': start_date, '$lte': end_date}
    elif start_date:
        query['record_date'] = {'$gte': start_date}
    elif end_date:
        query['record_date'] = {'$lte': end_date}
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    all_records = await db.omset_records.find({} if not product_id else {'product_id': product_id}, {'_id': 0}).to_list(100000)
    
    # Build customer_first_date, excluding "tambahan" records
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        key = (record['customer_id'], record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    daily_summary = {}
    for record in records:
        date = record['record_date']
        key = (record['customer_id'], record['product_id'])
        first_date = customer_first_date.get(key)
        
        # Check if "tambahan" in notes - if so, always RDP
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            is_ndp = False
        else:
            is_ndp = first_date == date
        
        if date not in daily_summary:
            daily_summary[date] = {
                'date': date,
                'total_depo': 0,
                'ndp_customers': set(),
                'rdp_count': 0,
                'total_form': 0
            }
        
        daily_summary[date]['total_depo'] += record.get('depo_total', 0)
        daily_summary[date]['total_form'] += record.get('depo_kelipatan', 1)
        
        if is_ndp:
            daily_summary[date]['ndp_customers'].add(record['customer_id'])
        else:
            daily_summary[date]['rdp_count'] += 1
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Date', 'Total Form', 'NDP', 'RDP', 'Total OMSET'])
    
    for date in sorted(daily_summary.keys(), reverse=True):
        data = daily_summary[date]
        writer.writerow([
            date,
            data['total_form'],
            len(data['ndp_customers']),
            data['rdp_count'],
            data['total_depo']
        ])
    
    output.seek(0)
    
    date_part = f"{start_date or 'all'}_to_{end_date or 'now'}"
    filename = f"omset_summary_{date_part}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/octet-stream",
            "Cache-Control": "no-cache"
        }
    )

@router.get("/omset/ndp-rdp")
async def get_omset_ndp_rdp(
    product_id: str,
    record_date: str,
    user: User = Depends(get_current_user)
):
    """Calculate NDP and RDP for a specific date and product"""
    db = get_db()
    query = {'product_id': product_id}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    customer_first_date = {}
    
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        # Use normalized customer_id for comparison (handle old records without normalized field)
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        if cid not in customer_first_date:
            customer_first_date[cid] = record['record_date']
    
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    ndp_customers = set()
    rdp_customers = set()  # Track unique RDP customers (NEW)
    ndp_total = 0
    rdp_total = 0
    
    for record in date_records:
        # Use normalized customer_id for comparison
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        first_date = customer_first_date.get(cid)
        
        # Check if "tambahan" in notes - if so, always RDP
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            rdp_customers.add(cid)
            rdp_total += record.get('depo_total', 0)
        elif first_date == record_date:
            ndp_customers.add(cid)
            ndp_total += record.get('depo_total', 0)
        else:
            # RDP - count unique customers (NEW LOGIC)
            rdp_customers.add(cid)
            rdp_total += record.get('depo_total', 0)
    
    return {
        'date': record_date,
        'product_id': product_id,
        'ndp_count': len(ndp_customers),
        'ndp_total': ndp_total,
        'rdp_count': len(rdp_customers),  # Count unique RDP customers
        'rdp_total': rdp_total,
        'total_records': len(date_records)
    }

@router.get("/omset/record-types")
async def get_omset_record_types(
    product_id: str,
    record_date: str,
    user: User = Depends(get_current_user)
):
    """Get all records with NDP/RDP classification for a specific date"""
    db = get_db()
    query = {'product_id': product_id}
    
    if user.role == 'staff':
        query['staff_id'] = user.id
    
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        # Use normalized customer_id for comparison
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        if cid not in customer_first_date:
            customer_first_date[cid] = record['record_date']
    
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    for record in date_records:
        # Use normalized customer_id for comparison
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        first_date = customer_first_date.get(cid)
        
        # Check if "tambahan" in notes - if so, always RDP
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            record['record_type'] = 'RDP'
        else:
            record['record_type'] = 'NDP' if first_date == record_date else 'RDP'
        
        if isinstance(record.get('created_at'), str):
            record['created_at'] = datetime.fromisoformat(record['created_at'])
    
    return date_records

@router.post("/omset/migrate-normalize")
async def migrate_normalize_customer_ids(user: User = Depends(get_admin_user)):
    """
    Admin-only endpoint to migrate existing records:
    1. Add customer_id_normalized field to all records
    2. Recalculate and update customer_type (NDP/RDP) based on normalized customer_id
    Note: Records with "tambahan" in keterangan are always marked as RDP
    """
    db = get_db()
    
    # Get all omset records
    all_records = await db.omset_records.find({}).to_list(500000)
    
    # Build customer first deposit map using normalized IDs
    # Exclude "tambahan" records from first_date calculation
    customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        cid_normalized = normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = record['record_date']
    
    # Update all records
    updated_count = 0
    for record in all_records:
        cid_normalized = normalize_customer_id(record['customer_id'])
        key = (cid_normalized, record['product_id'])
        first_date = customer_first_date.get(key)
        
        # Check if "tambahan" in notes - if so, always RDP
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            customer_type = 'RDP'
        else:
            customer_type = 'NDP' if first_date == record['record_date'] else 'RDP'
        
        # Update the record
        await db.omset_records.update_one(
            {'_id': record['_id']},
            {'$set': {
                'customer_id_normalized': cid_normalized,
                'customer_type': customer_type
            }}
        )
        updated_count += 1
    
    return {
        'message': f'Successfully migrated {updated_count} records',
        'total_records': len(all_records),
        'updated_count': updated_count
    }
