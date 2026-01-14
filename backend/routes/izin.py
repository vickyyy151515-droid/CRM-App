# Izin (Break/Permission) Routes

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Izin"])

DAILY_IZIN_LIMIT_MINUTES = 30

class IzinRecord(BaseModel):
    id: str
    staff_id: str
    staff_name: str
    date: str
    start_time: str
    end_time: Optional[str] = None
    duration_minutes: Optional[float] = None
    created_at: str

@router.get("/izin/status")
async def get_izin_status(user: User = Depends(get_current_user)):
    """Get current izin status for staff - whether they are on break or not"""
    db = get_db()
    today = get_jakarta_now().strftime('%Y-%m-%d')
    
    # Check if there's an active izin (no end_time)
    active_izin = await db.izin_records.find_one({
        'staff_id': user.id,
        'date': today,
        'end_time': None
    }, {'_id': 0})
    
    # Get all completed izin records for today
    completed_records = await db.izin_records.find({
        'staff_id': user.id,
        'date': today,
        'end_time': {'$ne': None}
    }, {'_id': 0}).to_list(100)
    
    # Calculate total minutes used today
    total_minutes_used = sum(r.get('duration_minutes', 0) for r in completed_records)
    
    # If there's an active izin, calculate elapsed time
    elapsed_minutes = 0
    if active_izin:
        start_time = active_izin['start_time']
        now = get_jakarta_now()
        start_parts = start_time.split(':')
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        current_minutes = now.hour * 60 + now.minute
        elapsed_minutes = max(0, current_minutes - start_minutes)
    
    return {
        'is_on_break': active_izin is not None,
        'active_izin': active_izin,
        'elapsed_minutes': elapsed_minutes,
        'total_minutes_used': total_minutes_used,
        'remaining_minutes': max(0, DAILY_IZIN_LIMIT_MINUTES - total_minutes_used),
        'daily_limit': DAILY_IZIN_LIMIT_MINUTES,
        'exceeded_limit': total_minutes_used > DAILY_IZIN_LIMIT_MINUTES
    }

@router.get("/izin/today")
async def get_today_izin_records(user: User = Depends(get_current_user)):
    """Get all izin records for today"""
    db = get_db()
    today = get_jakarta_now().strftime('%Y-%m-%d')
    
    records = await db.izin_records.find({
        'staff_id': user.id,
        'date': today
    }, {'_id': 0}).sort('created_at', -1).to_list(100)
    
    total_minutes = sum(r.get('duration_minutes', 0) for r in records if r.get('duration_minutes'))
    
    return {
        'records': records,
        'total_minutes': total_minutes,
        'remaining_minutes': max(0, DAILY_IZIN_LIMIT_MINUTES - total_minutes),
        'daily_limit': DAILY_IZIN_LIMIT_MINUTES
    }

@router.post("/izin/start")
async def start_izin(user: User = Depends(get_current_user)):
    """Start an izin (break) - Staff clicks 'Izin' button"""
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')
    
    # Check if already on break
    active_izin = await db.izin_records.find_one({
        'staff_id': user.id,
        'date': today,
        'end_time': None
    })
    
    if active_izin:
        raise HTTPException(status_code=400, detail="Anda sudah dalam status izin. Silakan klik 'Kembali' terlebih dahulu.")
    
    # Create new izin record
    izin_id = str(uuid.uuid4())
    izin_record = {
        'id': izin_id,
        'staff_id': user.id,
        'staff_name': user.name,
        'date': today,
        'start_time': current_time,
        'end_time': None,
        'duration_minutes': None,
        'created_at': now.isoformat()
    }
    
    await db.izin_records.insert_one(izin_record)
    
    izin_record.pop('_id', None)
    return {
        'message': 'Izin dimulai',
        'izin': izin_record,
        'start_time': current_time
    }

@router.post("/izin/end")
async def end_izin(user: User = Depends(get_current_user)):
    """End an izin (break) - Staff clicks 'Kembali' button"""
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M:%S')
    
    # Find active izin
    active_izin = await db.izin_records.find_one({
        'staff_id': user.id,
        'date': today,
        'end_time': None
    })
    
    if not active_izin:
        raise HTTPException(status_code=400, detail="Tidak ada izin aktif. Silakan klik 'Izin' terlebih dahulu.")
    
    # Calculate duration
    start_time = active_izin['start_time']
    start_parts = start_time.split(':')
    end_parts = current_time.split(':')
    
    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1]) + int(start_parts[2]) / 60
    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1]) + int(end_parts[2]) / 60
    duration_minutes = round(end_minutes - start_minutes, 2)
    
    # Update the izin record
    await db.izin_records.update_one(
        {'id': active_izin['id']},
        {'$set': {
            'end_time': current_time,
            'duration_minutes': duration_minutes
        }}
    )
    
    # Calculate total minutes used today after this izin
    all_records = await db.izin_records.find({
        'staff_id': user.id,
        'date': today,
        'end_time': {'$ne': None}
    }, {'_id': 0}).to_list(100)
    
    total_minutes_today = sum(r.get('duration_minutes', 0) for r in all_records) + duration_minutes
    exceeded_limit = total_minutes_today > DAILY_IZIN_LIMIT_MINUTES
    
    # If exceeded limit, send notification to all admins
    if exceeded_limit:
        admin_users = await db.users.find({'role': 'admin'}, {'_id': 0}).to_list(100)
        for admin in admin_users:
            notification = {
                'id': str(uuid.uuid4()),
                'user_id': admin['id'],
                'type': 'izin_exceeded',
                'title': 'Batas Izin Terlampaui',
                'message': f"{user.name} telah melebihi batas izin harian ({round(total_minutes_today, 1)} menit dari {DAILY_IZIN_LIMIT_MINUTES} menit)",
                'data': {
                    'staff_id': user.id,
                    'staff_name': user.name,
                    'total_minutes': total_minutes_today,
                    'date': today
                },
                'read': False,
                'created_at': now.isoformat()
            }
            await db.notifications.insert_one(notification)
    
    return {
        'message': 'Selamat datang kembali!',
        'duration_minutes': duration_minutes,
        'total_minutes_today': total_minutes_today,
        'remaining_minutes': max(0, DAILY_IZIN_LIMIT_MINUTES - total_minutes_today),
        'exceeded_limit': exceeded_limit
    }

# Admin endpoints to view all staff izin records
@router.get("/izin/admin/today")
async def get_all_staff_izin_today(user: User = Depends(get_admin_user)):
    """Admin view: Get all staff izin records for today"""
    db = get_db()
    today = get_jakarta_now().strftime('%Y-%m-%d')
    
    records = await db.izin_records.find({
        'date': today
    }, {'_id': 0}).sort('created_at', -1).to_list(1000)
    
    # Group by staff
    staff_summary = {}
    for record in records:
        staff_id = record['staff_id']
        if staff_id not in staff_summary:
            staff_summary[staff_id] = {
                'staff_id': staff_id,
                'staff_name': record['staff_name'],
                'total_minutes': 0,
                'records': [],
                'is_on_break': False
            }
        
        if record.get('duration_minutes'):
            staff_summary[staff_id]['total_minutes'] += record['duration_minutes']
        
        if record.get('end_time') is None:
            staff_summary[staff_id]['is_on_break'] = True
        
        staff_summary[staff_id]['records'].append(record)
    
    # Mark exceeded limit
    for staff_id in staff_summary:
        staff_summary[staff_id]['exceeded_limit'] = staff_summary[staff_id]['total_minutes'] > DAILY_IZIN_LIMIT_MINUTES
    
    return {
        'date': today,
        'staff_summary': list(staff_summary.values()),
        'total_records': len(records),
        'daily_limit': DAILY_IZIN_LIMIT_MINUTES
    }

@router.get("/izin/admin/history")
async def get_izin_history(
    staff_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Admin view: Get izin history with filters"""
    db = get_db()
    
    query = {}
    if staff_id:
        query['staff_id'] = staff_id
    if start_date:
        query['date'] = {'$gte': start_date}
    if end_date:
        if 'date' in query:
            query['date']['$lte'] = end_date
        else:
            query['date'] = {'$lte': end_date}
    
    records = await db.izin_records.find(query, {'_id': 0}).sort('created_at', -1).to_list(10000)
    
    # Calculate daily totals
    daily_totals = {}
    for record in records:
        date = record['date']
        staff_id = record['staff_id']
        key = f"{date}_{staff_id}"
        
        if key not in daily_totals:
            daily_totals[key] = {
                'date': date,
                'staff_id': staff_id,
                'staff_name': record['staff_name'],
                'total_minutes': 0,
                'record_count': 0
            }
        
        if record.get('duration_minutes'):
            daily_totals[key]['total_minutes'] += record['duration_minutes']
        daily_totals[key]['record_count'] += 1
    
    return {
        'records': records,
        'daily_totals': list(daily_totals.values()),
        'daily_limit': DAILY_IZIN_LIMIT_MINUTES
    }
