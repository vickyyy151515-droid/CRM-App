# Leave Request (Off Day/Sakit) Routes

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import uuid
from .deps import (
    User, get_db, get_current_user, get_admin_user, get_jakarta_now
)

router = APIRouter(tags=["Leave Requests"])

MONTHLY_LEAVE_HOURS = 24
OFF_DAY_HOURS = 12

class LeaveRequestCreate(BaseModel):
    leave_type: str
    date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = None

class LeaveRequestAction(BaseModel):
    action: str
    admin_note: Optional[str] = None

def calculate_leave_hours(leave_type: str, start_time: str = None, end_time: str = None) -> float:
    if leave_type == 'off_day':
        return OFF_DAY_HOURS
    elif leave_type == 'sakit' and start_time and end_time:
        start_parts = start_time.split(':')
        end_parts = end_time.split(':')
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
        return max(0, (end_minutes - start_minutes) / 60)
    return 0

@router.get("/leave/balance")
async def get_leave_balance(year: int = None, month: int = None, user: User = Depends(get_current_user)):
    db = get_db()
    if year is None:
        year = get_jakarta_now().year
    if month is None:
        month = get_jakarta_now().month
    
    month_str = f"{year}-{str(month).zfill(2)}"
    query = {'staff_id': user.id, 'date': {'$regex': f'^{month_str}'}, 'status': 'approved'}
    approved_requests = await db.leave_requests.find(query, {'_id': 0}).to_list(1000)
    
    used_hours = sum(req.get('hours_deducted', 0) for req in approved_requests)
    return {
        'year': year, 'month': month,
        'total_hours': MONTHLY_LEAVE_HOURS,
        'used_hours': used_hours,
        'remaining_hours': max(0, MONTHLY_LEAVE_HOURS - used_hours),
        'approved_requests': len(approved_requests)
    }

@router.get("/leave/my-requests")
async def get_my_leave_requests(year: int = None, month: int = None, user: User = Depends(get_current_user)):
    db = get_db()
    query = {'staff_id': user.id}
    if year and month:
        query['date'] = {'$regex': f'^{year}-{str(month).zfill(2)}'}
    requests = await db.leave_requests.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return requests

@router.post("/leave/request")
async def create_leave_request(request_data: LeaveRequestCreate, user: User = Depends(get_current_user)):
    db = get_db()
    if request_data.leave_type not in ['off_day', 'sakit']:
        raise HTTPException(status_code=400, detail="Invalid leave type")
    
    if request_data.leave_type == 'sakit' and (not request_data.start_time or not request_data.end_time):
        raise HTTPException(status_code=400, detail="Start and end time required for sick leave")
    
    hours_deducted = calculate_leave_hours(request_data.leave_type, request_data.start_time, request_data.end_time)
    date_parts = request_data.date.split('-')
    year, month = int(date_parts[0]), int(date_parts[1])
    
    balance = await get_leave_balance(year, month, user)
    pending_query = {'staff_id': user.id, 'date': {'$regex': f'^{year}-{str(month).zfill(2)}'}, 'status': 'pending'}
    pending_requests = await db.leave_requests.find(pending_query, {'_id': 0}).to_list(1000)
    pending_hours = sum(req.get('hours_deducted', 0) for req in pending_requests)
    available_hours = balance['remaining_hours'] - pending_hours
    
    if hours_deducted > available_hours:
        raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {available_hours} hours")
    
    existing = await db.leave_requests.find_one({'staff_id': user.id, 'date': request_data.date, 'status': {'$in': ['pending', 'approved']}})
    if existing:
        raise HTTPException(status_code=400, detail="You already have a leave request for this date")
    
    request_id = str(uuid.uuid4())
    leave_request = {
        'id': request_id, 'staff_id': user.id, 'staff_name': user.name,
        'leave_type': request_data.leave_type, 'date': request_data.date,
        'start_time': request_data.start_time, 'end_time': request_data.end_time,
        'hours_deducted': hours_deducted, 'reason': request_data.reason,
        'status': 'pending', 'created_at': get_jakarta_now().isoformat(),
        'reviewed_at': None, 'reviewed_by': None, 'reviewed_by_name': None, 'admin_note': None
    }
    await db.leave_requests.insert_one(leave_request)
    
    admin_users = await db.users.find({'role': {'$in': ['admin', 'master_admin']}}, {'_id': 0}).to_list(100)
    for admin in admin_users:
        notification = {
            'id': str(uuid.uuid4()), 'user_id': admin['id'], 'type': 'leave_request',
            'title': 'New Leave Request',
            'message': f"{user.name} requested {request_data.leave_type.replace('_', ' ')} for {request_data.date}",
            'data': {'request_id': request_id}, 'read': False, 'created_at': get_jakarta_now().isoformat()
        }
        await db.notifications.insert_one(notification)
    
    leave_request.pop('_id', None)
    return leave_request

@router.delete("/leave/request/{request_id}")
async def cancel_leave_request(request_id: str, user: User = Depends(get_current_user)):
    db = get_db()
    request = await db.leave_requests.find_one({'id': request_id, 'staff_id': user.id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Can only cancel pending requests")
    await db.leave_requests.delete_one({'id': request_id})
    return {'message': 'Leave request cancelled'}

@router.get("/leave/all-requests")
async def get_all_leave_requests(status: Optional[str] = None, year: int = None, month: int = None, user: User = Depends(get_admin_user)):
    db = get_db()
    query = {}
    if status:
        query['status'] = status
    
    # Don't filter by date when viewing pending requests - show all pending
    # Only apply date filter for approved/rejected/all statuses
    if year and month and status != 'pending':
        query['date'] = {'$regex': f'^{year}-{str(month).zfill(2)}'}
    
    requests = await db.leave_requests.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    pending_count = await db.leave_requests.count_documents({'status': 'pending'})
    return {'requests': requests, 'pending_count': pending_count}

@router.get("/leave/staff-balance/{staff_id}")
async def get_staff_leave_balance(staff_id: str, year: int = None, month: int = None, user: User = Depends(get_admin_user)):
    db = get_db()
    year = year or get_jakarta_now().year
    month = month or get_jakarta_now().month
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0, 'password_hash': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    query = {'staff_id': staff_id, 'date': {'$regex': f'^{year}-{str(month).zfill(2)}'}, 'status': 'approved'}
    approved_requests = await db.leave_requests.find(query, {'_id': 0}).to_list(1000)
    used_hours = sum(req.get('hours_deducted', 0) for req in approved_requests)
    
    return {
        'staff_id': staff_id, 'staff_name': staff['name'], 'year': year, 'month': month,
        'total_hours': MONTHLY_LEAVE_HOURS, 'used_hours': used_hours,
        'remaining_hours': max(0, MONTHLY_LEAVE_HOURS - used_hours)
    }

@router.put("/leave/request/{request_id}/action")
async def process_leave_request(request_id: str, action_data: LeaveRequestAction, user: User = Depends(get_admin_user)):
    db = get_db()
    request = await db.leave_requests.find_one({'id': request_id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")
    if action_data.action not in ['approve', 'reject']:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    new_status = 'approved' if action_data.action == 'approve' else 'rejected'
    await db.leave_requests.update_one({'id': request_id}, {'$set': {
        'status': new_status, 'reviewed_at': get_jakarta_now().isoformat(),
        'reviewed_by': user.id, 'reviewed_by_name': user.name, 'admin_note': action_data.admin_note
    }})
    
    notification = {
        'id': str(uuid.uuid4()), 'user_id': request['staff_id'], 'type': 'leave_response',
        'title': f"Leave Request {new_status.title()}",
        'message': f"Your {request['leave_type'].replace('_', ' ')} request for {request['date']} has been {new_status}",
        'data': {'request_id': request_id}, 'read': False, 'created_at': get_jakarta_now().isoformat()
    }
    await db.notifications.insert_one(notification)
    return {'message': f'Leave request {new_status}', 'status': new_status}

@router.get("/leave/calendar")
async def get_leave_calendar(year: int = Query(default=None), month: int = Query(default=None), user: User = Depends(get_admin_user)):
    db = get_db()
    now = get_jakarta_now()
    year = year or now.year
    month = month or now.month
    
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    
    query = {'status': 'approved', 'date': {'$gte': first_day, '$lt': last_day}}
    requests = await db.leave_requests.find(query, {'_id': 0}).sort('date', 1).to_list(1000)
    
    calendar_data = {}
    for req in requests:
        date = req['date']
        if date not in calendar_data:
            calendar_data[date] = []
        calendar_data[date].append({
            'id': req['id'], 'staff_id': req['staff_id'], 'staff_name': req['staff_name'],
            'leave_type': req['leave_type'], 'hours_deducted': req['hours_deducted'],
            'start_time': req.get('start_time'), 'end_time': req.get('end_time'), 'reason': req.get('reason')
        })
    
    staff_list = await db.users.find({'role': 'staff'}, {'_id': 0, 'id': 1, 'name': 1}).to_list(100)
    return {'year': year, 'month': month, 'calendar_data': calendar_data, 'staff_list': staff_list, 'total_leave_days': len(calendar_data)}
