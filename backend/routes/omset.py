# OMSET CRM Routes
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
from uuid import uuid4
import io
import csv
import jwt

from .deps import get_db, get_current_user, get_admin_user, User, JWT_SECRET, JWT_ALGORITHM
from utils.helpers import normalize_customer_id, get_jakarta_now

router = APIRouter(tags=["OMSET CRM"])

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
    approval_status: Optional[str] = 'approved'
    conflict_info: Optional[dict] = None
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
    """Get dashboard stats with trend indicators comparing today vs yesterday, this month vs last month."""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    current_year = jakarta_now.year
    current_month = jakarta_now.month
    today = jakarta_now.strftime('%Y-%m-%d')
    yesterday = (jakarta_now - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Approved-only filter for all aggregations
    approved_match = {'$or': [{'approval_status': 'approved'}, {'approval_status': {'$exists': False}}]}
    
    # Run all aggregations in parallel via gather-style sequential calls (motor doesn't support true parallel)
    # 1) Year total
    year_start = f"{current_year}-01-01"
    year_end = f"{current_year}-12-31"
    year_total = await db.omset_records.aggregate([
        {'$match': {'record_date': {'$gte': year_start, '$lte': year_end}, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}, 'count': {'$sum': 1}}}
    ]).to_list(1)
    
    # 2) Last year same period (for YoY comparison)
    last_year = current_year - 1
    ly_start = f"{last_year}-01-01"
    ly_end = (jakarta_now.replace(year=last_year)).strftime('%Y-%m-%d')
    ly_total = await db.omset_records.aggregate([
        {'$match': {'record_date': {'$gte': ly_start, '$lte': ly_end}, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}}}
    ]).to_list(1)
    
    # 3) Monthly ATH (best day this month)
    month_str = f"{current_year}-{str(current_month).zfill(2)}"
    month_start = f"{month_str}-01"
    month_end = f"{month_str}-31"
    daily_totals_agg = await db.omset_records.aggregate([
        {'$match': {'record_date': {'$gte': month_start, '$lte': month_end}, **approved_match}},
        {'$group': {'_id': '$record_date', 'daily_total': {'$sum': {'$ifNull': ['$depo_total', 0]}}}},
        {'$sort': {'daily_total': -1}},
        {'$limit': 1}
    ]).to_list(1)
    
    # 4) Today's stats (omset + NDP/RDP counts)
    today_stats = await db.omset_records.aggregate([
        {'$match': {'record_date': today, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}, 'count': {'$sum': 1}}}
    ]).to_list(1)
    
    # 5) Yesterday's stats
    yesterday_stats = await db.omset_records.aggregate([
        {'$match': {'record_date': yesterday, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}, 'count': {'$sum': 1}}}
    ]).to_list(1)
    
    # 6) This month total
    this_month_total = await db.omset_records.aggregate([
        {'$match': {'record_date': {'$gte': month_start, '$lte': month_end}, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}, 'count': {'$sum': 1}}}
    ]).to_list(1)
    
    # 7) Last month total
    if current_month == 1:
        lm_year, lm_month = current_year - 1, 12
    else:
        lm_year, lm_month = current_year, current_month - 1
    lm_str = f"{lm_year}-{str(lm_month).zfill(2)}"
    last_month_total = await db.omset_records.aggregate([
        {'$match': {'record_date': {'$gte': f'{lm_str}-01', '$lte': f'{lm_str}-31'}, **approved_match}},
        {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$depo_total', 0]}}, 'count': {'$sum': 1}}}
    ]).to_list(1)
    
    # 8) Today's NDP count (unique new customers today)
    from utils.db_operations import build_staff_first_date_map
    first_date_map = await build_staff_first_date_map(db)
    
    today_records = await db.omset_records.find(
        {'record_date': today, **approved_match},
        {'_id': 0, 'staff_id': 1, 'customer_id_normalized': 1, 'product_id': 1, 'keterangan': 1}
    ).to_list(5000)
    
    yesterday_records = await db.omset_records.find(
        {'record_date': yesterday, **approved_match},
        {'_id': 0, 'staff_id': 1, 'customer_id_normalized': 1, 'product_id': 1, 'keterangan': 1}
    ).to_list(5000)
    
    def count_ndp_rdp(records):
        ndp, rdp = 0, 0
        for r in records:
            keterangan = r.get('keterangan', '') or ''
            if 'tambahan' in keterangan.lower():
                continue
            key = (r.get('staff_id', ''), r.get('customer_id_normalized', ''), r.get('product_id', ''))
            first = first_date_map.get(key)
            if first and first == today:
                ndp += 1
            elif first and first == yesterday and r.get('staff_id'):
                ndp += 1
            else:
                rdp += 1
        return ndp, rdp
    
    # Simpler approach: count unique customer+product combos for today/yesterday
    today_ndp = 0
    today_rdp = 0
    for r in today_records:
        keterangan = r.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        key = (r.get('staff_id', ''), r.get('customer_id_normalized', ''), r.get('product_id', ''))
        first = first_date_map.get(key)
        if first and first == today:
            today_ndp += 1
        else:
            today_rdp += 1
    
    yesterday_ndp = 0
    yesterday_rdp = 0
    for r in yesterday_records:
        keterangan = r.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        key = (r.get('staff_id', ''), r.get('customer_id_normalized', ''), r.get('product_id', ''))
        first = first_date_map.get(key)
        if first and first == yesterday:
            yesterday_ndp += 1
        else:
            yesterday_rdp += 1
    
    # Build response (keeping ALL existing fields + adding trends)
    total_omset_year = year_total[0]['total'] if year_total else 0
    ath_date = daily_totals_agg[0]['_id'] if daily_totals_agg else None
    ath_amount = daily_totals_agg[0]['daily_total'] if daily_totals_agg else 0
    
    return {
        # Existing fields (unchanged)
        'year': current_year,
        'month': current_month,
        'total_omset_year': total_omset_year,
        'monthly_ath': {'date': ath_date, 'amount': ath_amount},
        # New trend data
        'trends': {
            'today_omset': today_stats[0]['total'] if today_stats else 0,
            'yesterday_omset': yesterday_stats[0]['total'] if yesterday_stats else 0,
            'today_records': today_stats[0]['count'] if today_stats else 0,
            'yesterday_records': yesterday_stats[0]['count'] if yesterday_stats else 0,
            'today_ndp': today_ndp,
            'yesterday_ndp': yesterday_ndp,
            'today_rdp': today_rdp,
            'yesterday_rdp': yesterday_rdp,
            'this_month_omset': this_month_total[0]['total'] if this_month_total else 0,
            'last_month_omset': last_month_total[0]['total'] if last_month_total else 0,
            'last_year_ytd': ly_total[0]['total'] if ly_total else 0,
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
    
    # Determine if this is NDP or RDP (PER-STAFF: only check this staff's history)
    if is_tambahan:
        customer_type = 'RDP'
    else:
        existing_record = await db.omset_records.find_one({
            'customer_id_normalized': normalized_cid,
            'product_id': record_data.product_id,
            'staff_id': user.id,
            'record_date': {'$lt': record_data.record_date},
            'approval_status': {'$ne': 'declined'}
        })
        
        if not existing_record:
            potential_matches = await db.omset_records.find({
                'product_id': record_data.product_id,
                'staff_id': user.id,
                'record_date': {'$lt': record_data.record_date},
                'approval_status': {'$ne': 'declined'}
            }, {'customer_id': 1, 'customer_id_normalized': 1}).to_list(10000)
            
            for match in potential_matches:
                match_normalized = match.get('customer_id_normalized') or normalize_customer_id(match['customer_id'])
                if match_normalized == normalized_cid:
                    existing_record = match
                    break
        
        customer_type = 'RDP' if existing_record else 'NDP'
    
    # Check reserved member conflict:
    # If customer belongs to ANOTHER staff's reserved list → pending approval
    approval_status = 'approved'
    conflict_info = None
    
    reserved_conflict = await db.reserved_members.find_one({
        'status': 'approved',
        'staff_id': {'$ne': user.id},
        '$or': [
            {'customer_id': {'$regex': f'^{record_data.customer_id.strip()}$', '$options': 'i'}},
            {'customer_name': {'$regex': f'^{record_data.customer_id.strip()}$', '$options': 'i'}}
        ]
    }, {'_id': 0})
    
    if reserved_conflict:
        approval_status = 'pending'
        conflict_info = {
            'reserved_by_staff_id': reserved_conflict.get('staff_id'),
            'reserved_by_staff_name': reserved_conflict.get('staff_name', 'Unknown'),
            'reason': f"Customer '{record_data.customer_id.strip()}' is reserved by {reserved_conflict.get('staff_name', 'Unknown')}"
        }
    
    record = OmsetRecord(
        product_id=record_data.product_id,
        product_name=product['name'],
        staff_id=user.id,
        staff_name=user.name,
        record_date=record_data.record_date,
        customer_name=record_data.customer_name.strip(),
        customer_id=record_data.customer_id.strip(),
        nominal=record_data.nominal,
        depo_kelipatan=record_data.depo_kelipatan,
        depo_total=depo_total,
        keterangan=record_data.keterangan,
        approval_status=approval_status,
        conflict_info=conflict_info
    )
    
    doc = record.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['customer_id_normalized'] = normalized_cid
    doc['customer_type'] = customer_type
    doc['approval_status'] = approval_status
    if conflict_info:
        doc['conflict_info'] = conflict_info
    
    await db.omset_records.insert_one(doc)
    
    # SYNC: Recalculate NDP/RDP for ALL records of this (staff, customer, product)
    # This handles out-of-order entry (e.g., Feb 9 entered before Feb 7)
    if approval_status == 'approved':
        from utils.db_operations import recalculate_customer_type
        await recalculate_customer_type(db, user.id, record_data.customer_id.strip(), record_data.product_id)
    
    # If pending, notify admin
    if approval_status == 'pending':
        now = get_jakarta_now()
        await db.notifications.insert_one({
            'id': str(uuid4()),
            'type': 'omset_pending_approval',
            'title': 'Omset Pending Approval',
            'message': f"{user.name} recorded omset for customer '{record_data.customer_id.strip()}' ({product['name']}), but this customer is reserved by {conflict_info['reserved_by_staff_name']}. Please approve or decline.",
            'data': {'omset_record_id': record.id, 'staff_name': user.name, 'customer_id': record_data.customer_id.strip(), 'product_name': product['name'], 'reserved_by': conflict_info['reserved_by_staff_name']},
            'target_role': 'admin',
            'read': False,
            'created_at': now.isoformat()
        })
    
    # SYNC: Update reserved_members last_omset_date if this customer is reserved by THIS staff
    # Search BOTH customer_id AND customer_name fields to handle legacy data
    if approval_status == 'approved':
        customer_id_clean = record_data.customer_id.strip()
        await db.reserved_members.update_many(
            {
                '$or': [
                    {'customer_id': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}},
                    {'customer_name': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}}
                ],
                'staff_id': user.id,
                'status': 'approved'
            },
            {'$set': {'last_omset_date': record_data.record_date}}
        )
    
    # AUTO-REASSIGNMENT: If this customer had a deleted/expired reservation
    # under THIS staff, and they're not currently reserved by anyone,
    # automatically re-establish the reservation
    if approval_status == 'approved':
        customer_id_clean = record_data.customer_id.strip()
        
        # Check if customer is NOT currently reserved by ANYONE
        current_reservation = await db.reserved_members.find_one({
            'status': 'approved',
            '$or': [
                {'customer_id': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}},
                {'customer_name': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}}
            ]
        })
        
        if not current_reservation:
            # Check if there's a deleted reservation for this customer + staff + product
            deleted_reservation = await db.deleted_reserved_members.find_one({
                'staff_id': user.id,
                'product_id': record_data.product_id,
                '$or': [
                    {'customer_id': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}},
                    {'customer_name': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}}
                ]
            }, {'_id': 0})
            
            if deleted_reservation:
                # Auto-create a new reservation
                now = get_jakarta_now()
                new_reservation = {
                    'id': str(uuid4()),
                    'customer_id': deleted_reservation.get('customer_id') or customer_id_clean,
                    'customer_name': deleted_reservation.get('customer_name'),
                    'phone_number': deleted_reservation.get('phone_number'),
                    'product_id': deleted_reservation.get('product_id'),
                    'product_name': deleted_reservation.get('product_name', ''),
                    'staff_id': user.id,
                    'staff_name': user.name,
                    'status': 'approved',
                    'is_permanent': False,
                    'created_by': 'system',
                    'created_by_name': 'Auto-Reassignment',
                    'created_at': now.isoformat(),
                    'approved_at': now.isoformat(),
                    'approved_by': 'system',
                    'approved_by_name': 'Auto-Reassignment',
                    'last_omset_date': record_data.record_date,
                    'auto_reassigned': True,
                    'auto_reassigned_at': now.isoformat(),
                }
                
                await db.reserved_members.insert_one(new_reservation)
                
                # Remove from deleted_reserved_members archive
                await db.deleted_reserved_members.delete_one({
                    'id': deleted_reservation['id']
                })
                
                # Notify the staff
                await db.notifications.insert_one({
                    'id': str(uuid4()),
                    'type': 'reservation_auto_restored',
                    'title': 'Reservation Auto-Restored',
                    'message': f"Your reservation for '{customer_id_clean}' ({deleted_reservation.get('product_name', '')}) has been automatically restored because you recorded a new omset.",
                    'data': {
                        'customer_id': customer_id_clean,
                        'product_name': deleted_reservation.get('product_name', ''),
                        'new_reservation_id': new_reservation['id']
                    },
                    'user_id': user.id,
                    'read': False,
                    'created_at': now.isoformat()
                })
    
    return record


@router.get("/omset/pending")
async def get_pending_omset(user: User = Depends(get_admin_user)):
    """Get all omset records pending approval (reserved member conflicts)."""
    db = get_db()
    records = await db.omset_records.find(
        {'approval_status': 'pending'},
        {'_id': 0}
    ).sort('created_at', -1).to_list(1000)
    return records


@router.post("/omset/{record_id}/approve")
async def approve_omset(record_id: str, user: User = Depends(get_admin_user)):
    """Admin approves a pending omset record."""
    db = get_db()
    record = await db.omset_records.find_one({'id': record_id}, {'_id': 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.get('approval_status') != 'pending':
        raise HTTPException(status_code=400, detail="Record is not pending approval")
    
    await db.omset_records.update_one(
        {'id': record_id},
        {'$set': {'approval_status': 'approved', 'approved_by': user.id, 'approved_at': get_jakarta_now().isoformat()}}
    )
    
    # Update reserved_members last_omset_date
    # Search BOTH customer_id AND customer_name fields to handle legacy data
    customer_id_clean = record['customer_id'].strip() if record.get('customer_id') else ''
    if customer_id_clean:
        await db.reserved_members.update_many(
            {
                '$or': [
                    {'customer_id': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}},
                    {'customer_name': {'$regex': f'^{customer_id_clean}$', '$options': 'i'}}
                ],
                'staff_id': record['staff_id'],
                'status': 'approved'
            },
            {'$set': {'last_omset_date': record['record_date']}}
        )
    
    # Recalculate NDP/RDP customer_type now that this record is approved
    from utils.db_operations import recalculate_customer_type
    await recalculate_customer_type(
        db, record['staff_id'], record['customer_id'], record['product_id']
    )
    
    # Notify staff
    await db.notifications.insert_one({
        'id': str(uuid4()),
        'type': 'omset_approved',
        'title': 'Omset Approved',
        'message': f"Your omset for customer '{record['customer_id']}' ({record['product_name']}) has been approved by admin.",
        'data': {'omset_record_id': record_id},
        'target_user_id': record['staff_id'],
        'read': False,
        'created_at': get_jakarta_now().isoformat()
    })
    
    return {'success': True, 'message': 'Omset record approved'}


@router.post("/omset/{record_id}/decline")
async def decline_omset(record_id: str, user: User = Depends(get_admin_user)):
    """Admin declines a pending omset record (deletes it)."""
    db = get_db()
    record = await db.omset_records.find_one({'id': record_id}, {'_id': 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.get('approval_status') != 'pending':
        raise HTTPException(status_code=400, detail="Record is not pending approval")
    
    await db.omset_records.delete_one({'id': record_id})
    
    # Recalculate NDP/RDP customer_type for remaining records of this (staff, customer, product)
    from utils.db_operations import recalculate_customer_type
    await recalculate_customer_type(
        db, record['staff_id'], record['customer_id'], record['product_id']
    )
    
    # Notify staff
    await db.notifications.insert_one({
        'id': str(uuid4()),
        'type': 'omset_declined',
        'title': 'Omset Declined',
        'message': f"Your omset for customer '{record['customer_id']}' ({record['product_name']}) was declined by admin because this customer is reserved by another staff.",
        'data': {'customer_id': record['customer_id'], 'product_name': record['product_name']},
        'target_user_id': record['staff_id'],
        'read': False,
        'created_at': get_jakarta_now().isoformat()
    })
    
    return {'success': True, 'message': 'Omset record declined and deleted'}


@router.get("/omset/duplicates")
async def get_omset_duplicates(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get duplicate omset records — same customer recorded by different staff for same product."""
    db = get_db()
    
    match_stage = {'approval_status': {'$ne': 'declined'}}
    if start_date:
        match_stage['record_date'] = {'$gte': start_date}
    if end_date:
        match_stage.setdefault('record_date', {})['$lte'] = end_date
    if product_id:
        match_stage['product_id'] = product_id
    
    pipeline = [
        {'$match': match_stage},
        {'$group': {
            '_id': {
                'cid': {'$ifNull': ['$customer_id_normalized', '$customer_id']},
                'pid': '$product_id'
            },
            'staff_ids': {'$addToSet': '$staff_id'},
            'staff_names': {'$addToSet': '$staff_name'},
            'product_name': {'$first': '$product_name'},
            'records': {'$push': {
                'id': '$id',
                'staff_id': '$staff_id',
                'staff_name': '$staff_name',
                'record_date': '$record_date',
                'customer_id': '$customer_id',
                'customer_name': '$customer_name',
                'nominal': '$nominal',
                'depo_total': '$depo_total',
                'keterangan': '$keterangan'
            }},
            'total_records': {'$sum': 1},
            'total_depo': {'$sum': '$depo_total'}
        }},
        {'$match': {'staff_ids.1': {'$exists': True}}},
        {'$sort': {'total_records': -1}},
        {'$project': {
            '_id': 0,
            'customer_id': '$_id.cid',
            'product_id': '$_id.pid',
            'product_name': 1,
            'staff_names': 1,
            'staff_count': {'$size': '$staff_ids'},
            'total_records': 1,
            'total_depo': 1,
            'records': 1
        }}
    ]
    
    duplicates = await db.omset_records.aggregate(pipeline).to_list(1000)
    
    return {
        'total_duplicates': len(duplicates),
        'total_records_involved': sum(d['total_records'] for d in duplicates),
        'duplicates': duplicates
    }


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
    
    # Recalculate NDP/RDP customer_type for remaining records of this (staff, customer, product)
    from utils.db_operations import recalculate_customer_type
    await recalculate_customer_type(
        db, record['staff_id'], record['customer_id'], record['product_id']
    )
    
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
    
    # SYNC: Update reserved_members last_omset_date if this customer is reserved
    customer_id = restored_record.get('customer_id', '')
    staff_id = restored_record.get('staff_id', '')
    record_date = restored_record.get('record_date', '')
    
    if customer_id and staff_id and record_date:
        await db.reserved_members.update_many(
            {
                'customer_id': {'$regex': f'^{customer_id}$', '$options': 'i'},
                'staff_id': staff_id,
                'status': 'approved'
            },
            {
                '$set': {
                    'last_omset_date': record_date
                }
            }
        )
    
    # Recalculate NDP/RDP customer_type for this (staff, customer, product) after restore
    product_id = restored_record.get('product_id', '')
    if customer_id and staff_id and product_id:
        from utils.db_operations import recalculate_customer_type
        await recalculate_customer_type(db, staff_id, customer_id, product_id)
    
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
    
    # Only count approved records in summary calculations
    query['$or'] = [{'approval_status': 'approved'}, {'approval_status': {'$exists': False}}]
    
    records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get ALL records for building customer_first_date maps
    # Use MongoDB aggregation for efficiency (instead of loading 500K records into memory)
    from utils.db_operations import build_staff_first_date_map
    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)
    
    daily_summary = {}
    staff_summary = {}
    product_summary = {}
    total_nominal = 0
    total_depo = 0
    total_records = len(records)
    total_ndp = 0
    total_rdp = 0
    
    # Use (staff_id, customer_id, product_id) tuples for consistent tracking everywhere
    # This ensures NDP/RDP counts ALWAYS match across daily, staff, and product views
    staff_ndp_pairs = {}     # staff_id -> set of (customer_id, product_id)
    staff_rdp_pairs = {}     # staff_id -> set of (customer_id, product_id)
    product_ndp_pairs = {}   # product_id -> set of (staff_id, customer_id)
    product_rdp_pairs = {}   # product_id -> set of (staff_id, customer_id)
    
    # UNIQUE CUSTOMERS tracking (deduplicated across ALL dates, for the new section)
    # Per staff: set of (cid_normalized, product_id) -> track original customer_id for display
    staff_unique_ndp = {}    # staff_id -> {(cid_normalized, product_id): {'customer_id': str, 'product_name': str, 'dates': set, 'total_depo': int}}
    staff_unique_rdp = {}    # staff_id -> {(cid_normalized, product_id): {'customer_id': str, 'product_name': str, 'dates': set, 'total_depo': int}}
    
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
        
        # SINGLE NDP/RDP definition: per (staff, customer, product)
        staff_key = (staff_id_rec, cid_normalized, product_id_rec)
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        is_tambahan = is_tambahan_record(record)
        
        if is_tambahan:
            is_ndp = False
        else:
            is_ndp = staff_first_date == date
        
        total_nominal += nominal
        total_depo += depo_total
        
        # --- Daily Summary ---
        if date not in daily_summary:
            daily_summary[date] = {
                'date': date, 
                'total_nominal': 0, 
                'total_depo': 0, 
                'count': 0,
                'ndp_tuples': set(),   # Track (staff_id, customer_id, product_id)
                'rdp_tuples': set(),   # Track (staff_id, customer_id, product_id)
                'ndp_total': 0,
                'rdp_total': 0
            }
        daily_summary[date]['total_nominal'] += nominal
        daily_summary[date]['total_depo'] += depo_total
        daily_summary[date]['count'] += 1
        
        ndp_tuple = (staff_id_rec, cid_normalized, product_id_rec)
        if is_ndp:
            if ndp_tuple not in daily_summary[date]['ndp_tuples']:
                daily_summary[date]['ndp_tuples'].add(ndp_tuple)
                daily_summary[date]['ndp_total'] += depo_total
        else:
            if ndp_tuple not in daily_summary[date]['rdp_tuples']:
                daily_summary[date]['rdp_tuples'].add(ndp_tuple)
                daily_summary[date]['rdp_total'] += depo_total
        
        # --- Staff Summary ---
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
            staff_ndp_pairs[staff_id_rec] = set()
            staff_rdp_pairs[staff_id_rec] = set()
        
        staff_summary[staff_id_rec]['total_nominal'] += nominal
        staff_summary[staff_id_rec]['total_depo'] += depo_total
        staff_summary[staff_id_rec]['count'] += 1
        
        # Track (customer_id, product_id, date) per staff — include date to match daily totals
        customer_product_date = (cid_normalized, product_id_rec, date)
        if is_ndp:
            if customer_product_date not in staff_ndp_pairs[staff_id_rec]:
                staff_ndp_pairs[staff_id_rec].add(customer_product_date)
                staff_summary[staff_id_rec]['ndp_count'] += 1
        else:
            if customer_product_date not in staff_rdp_pairs[staff_id_rec]:
                staff_rdp_pairs[staff_id_rec].add(customer_product_date)
                staff_summary[staff_id_rec]['rdp_count'] += 1
        
        # --- Product Summary ---
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
            product_ndp_pairs[product_id_rec] = set()
            product_rdp_pairs[product_id_rec] = set()
        
        product_summary[product_id_rec]['total_nominal'] += nominal
        product_summary[product_id_rec]['total_depo'] += depo_total
        product_summary[product_id_rec]['count'] += 1
        
        # Track (staff_id, customer_id, date) per product — include date to match daily totals
        staff_customer_date = (staff_id_rec, cid_normalized, date)
        if is_ndp:
            if staff_customer_date not in product_ndp_pairs[product_id_rec]:
                product_ndp_pairs[product_id_rec].add(staff_customer_date)
                product_summary[product_id_rec]['ndp_count'] += 1
        else:
            if staff_customer_date not in product_rdp_pairs[product_id_rec]:
                product_rdp_pairs[product_id_rec].add(staff_customer_date)
                product_summary[product_id_rec]['rdp_count'] += 1
        
        # --- UNIQUE CUSTOMERS tracking (deduped across ALL dates) ---
        original_customer_id = record.get('customer_id', cid_normalized)
        if staff_id_rec not in staff_unique_ndp:
            staff_unique_ndp[staff_id_rec] = {}
            staff_unique_rdp[staff_id_rec] = {}
        
        unique_key = (cid_normalized, product_id_rec)
        if is_ndp:
            if unique_key not in staff_unique_ndp[staff_id_rec]:
                staff_unique_ndp[staff_id_rec][unique_key] = {
                    'customer_id': original_customer_id,
                    'product_id': product_id_rec,
                    'product_name': product_name,
                    'dates': set(),
                    'total_depo': 0,
                    'deposit_count': 0
                }
            staff_unique_ndp[staff_id_rec][unique_key]['dates'].add(date)
            staff_unique_ndp[staff_id_rec][unique_key]['total_depo'] += depo_total
            staff_unique_ndp[staff_id_rec][unique_key]['deposit_count'] += 1
        else:
            if unique_key not in staff_unique_rdp[staff_id_rec]:
                staff_unique_rdp[staff_id_rec][unique_key] = {
                    'customer_id': original_customer_id,
                    'product_id': product_id_rec,
                    'product_name': product_name,
                    'dates': set(),
                    'total_depo': 0,
                    'deposit_count': 0
                }
            staff_unique_rdp[staff_id_rec][unique_key]['dates'].add(date)
            staff_unique_rdp[staff_id_rec][unique_key]['total_depo'] += depo_total
            staff_unique_rdp[staff_id_rec][unique_key]['deposit_count'] += 1
    
    daily_list = []
    for date, data in daily_summary.items():
        daily_list.append({
            'date': data['date'],
            'total_nominal': data['total_nominal'],
            'total_depo': data['total_depo'],
            'count': data['count'],
            'ndp_count': len(data['ndp_tuples']),
            'rdp_count': len(data['rdp_tuples']),
            'ndp_total': data['ndp_total'],
            'rdp_total': data['rdp_total']
        })
        total_ndp += len(data['ndp_tuples'])
        total_rdp += len(data['rdp_tuples'])
    
    # Build unique customers summary per staff
    unique_customers_by_staff = []
    for sid, sdata in staff_summary.items():
        ndp_customers = []
        for key, cdata in staff_unique_ndp.get(sid, {}).items():
            ndp_customers.append({
                'customer_id': cdata['customer_id'],
                'product_id': cdata['product_id'],
                'product_name': cdata['product_name'],
                'deposit_count': cdata['deposit_count'],
                'total_depo': cdata['total_depo'],
                'dates': sorted(cdata['dates'])
            })
        rdp_customers = []
        for key, cdata in staff_unique_rdp.get(sid, {}).items():
            rdp_customers.append({
                'customer_id': cdata['customer_id'],
                'product_id': cdata['product_id'],
                'product_name': cdata['product_name'],
                'deposit_count': cdata['deposit_count'],
                'total_depo': cdata['total_depo'],
                'dates': sorted(cdata['dates'])
            })
        unique_customers_by_staff.append({
            'staff_id': sid,
            'staff_name': sdata['staff_name'],
            'unique_ndp_count': len(ndp_customers),
            'unique_rdp_count': len(rdp_customers),
            'ndp_customers': sorted(ndp_customers, key=lambda x: x['total_depo'], reverse=True),
            'rdp_customers': sorted(rdp_customers, key=lambda x: x['total_depo'], reverse=True)
        })
    
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
        'by_product': sorted(product_summary.values(), key=lambda x: x['total_depo'], reverse=True),
        'unique_customers': sorted(unique_customers_by_staff, key=lambda x: x['unique_rdp_count'], reverse=True)
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
    
    # Build STAFF-SPECIFIC customer first deposit map using MongoDB aggregation
    from utils.db_operations import build_staff_first_date_map
    staff_customer_first_date = await build_staff_first_date_map(db, product_id=product_id)
    
    daily_summary = {}
    for record in records:
        date = record['record_date']
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        product_id_rec = record['product_id']
        key = (staff_id_rec, cid_normalized, product_id_rec)
        first_date = staff_customer_first_date.get(key)
        
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
                'ndp_tuples': set(),
                'rdp_tuples': set(),
                'total_form': 0
            }
        
        daily_summary[date]['total_depo'] += record.get('depo_total', 0)
        daily_summary[date]['total_form'] += record.get('depo_kelipatan', 1)
        
        ndp_tuple = (staff_id_rec, cid_normalized, product_id_rec)
        if is_ndp:
            daily_summary[date]['ndp_tuples'].add(ndp_tuple)
        else:
            daily_summary[date]['rdp_tuples'].add(ndp_tuple)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Date', 'Total Form', 'NDP', 'RDP', 'Total OMSET'])
    
    for date in sorted(daily_summary.keys(), reverse=True):
        data = daily_summary[date]
        writer.writerow([
            date,
            data['total_form'],
            len(data['ndp_tuples']),
            len(data['rdp_tuples']),
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
    
    # Build STAFF-SPECIFIC customer first deposit map
    # Since we're already filtered to a single product, key is (staff_id, customer_id)
    staff_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            continue
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        key = (staff_id_rec, cid)
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    # Track (staff_id, customer_id) pairs for consistent NDP/RDP
    ndp_pairs = set()
    rdp_pairs = set()
    ndp_total = 0
    rdp_total = 0
    
    for record in date_records:
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        staff_id_rec = record['staff_id']
        staff_cid_pair = (staff_id_rec, cid)
        first_date = staff_customer_first_date.get(staff_cid_pair)
        
        keterangan = record.get('keterangan', '') or ''
        if 'tambahan' in keterangan.lower():
            rdp_pairs.add(staff_cid_pair)
            rdp_total += record.get('depo_total', 0)
        elif first_date == record_date:
            ndp_pairs.add(staff_cid_pair)
            ndp_total += record.get('depo_total', 0)
        else:
            rdp_pairs.add(staff_cid_pair)
            rdp_total += record.get('depo_total', 0)
    
    return {
        'date': record_date,
        'product_id': product_id,
        'ndp_count': len(ndp_pairs),
        'ndp_total': ndp_total,
        'rdp_count': len(rdp_pairs),
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
    
    # Build STAFF-SPECIFIC first deposit map using MongoDB aggregation
    from utils.db_operations import build_staff_first_date_map
    full_map = await build_staff_first_date_map(db, product_id=product_id)
    
    all_records = await db.omset_records.find(query, {'_id': 0}).to_list(100000)
    
    # Re-key to (staff_id, customer_id) since product is fixed
    staff_customer_first_date = {}
    for (sid, cid, pid), first_date in full_map.items():
        key = (sid, cid)
        if key not in staff_customer_first_date or first_date < staff_customer_first_date[key]:
            staff_customer_first_date[key] = first_date
    
    date_records = [r for r in all_records if r['record_date'] == record_date]
    
    for record in date_records:
        cid = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (record['staff_id'], cid)
        first_date = staff_customer_first_date.get(key)
        
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
    
    # Get all omset records (only fields needed for type recalculation)
    all_records = await db.omset_records.find(
        {},
        {'id': 1, 'staff_id': 1, 'customer_id': 1, 'customer_id_normalized': 1,
         'product_id': 1, 'record_date': 1, 'keterangan': 1, 'customer_type': 1}
    ).to_list(50000)
    
    # Build STAFF-SPECIFIC customer first deposit map using MongoDB aggregation
    from utils.db_operations import build_staff_first_date_map
    staff_customer_first_date = await build_staff_first_date_map(db)
    
    # Update all records
    updated_count = 0
    for record in all_records:
        cid_normalized = normalize_customer_id(record['customer_id'])
        key = (record['staff_id'], cid_normalized, record['product_id'])
        first_date = staff_customer_first_date.get(key)
        
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
