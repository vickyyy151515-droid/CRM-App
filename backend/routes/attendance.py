"""
Attendance System API - TOTP Based (Google Authenticator compatible)
- Staff sets up Google Authenticator ONCE
- Daily: Staff types 6-digit code to check in
- Code changes every 30 seconds (standard TOTP interval)

NOTE: Fee & Payment endpoints have been moved to routes/fees.py
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import pyotp
import qrcode
import io
import base64
from routes.deps import get_db
from routes.auth import get_current_user, User
from utils.helpers import get_jakarta_now, get_jakarta_date_string, JAKARTA_TZ

router = APIRouter(tags=["Attendance"])

# Shift configuration
SHIFT_START_HOUR = 11  # 11:00 AM
SHIFT_END_HOUR = 23    # 11:00 PM

# TOTP Configuration
TOTP_INTERVAL = 30  # Code changes every 30 seconds (Google Authenticator standard)
TOTP_ISSUER = "CRM Attendance"

def get_database():
    return get_db()

# ==================== MODELS ====================

class TOTPVerifyRequest(BaseModel):
    code: str

# ==================== TOTP SETUP ====================

@router.get("/attendance/totp/status")
async def get_totp_status(user: User = Depends(get_current_user)):
    """Check if current user has TOTP set up"""
    db = get_database()
    
    totp_data = await db.attendance_totp.find_one({'staff_id': user.id})
    
    if totp_data:
        return {
            'is_setup': True,
            'setup_date': totp_data.get('setup_date')
        }
    return {'is_setup': False}

@router.post("/attendance/totp/setup")
async def setup_totp(user: User = Depends(get_current_user)):
    """Generate TOTP secret and return setup QR code"""
    db = get_database()
    
    # Check if already set up
    existing = await db.attendance_totp.find_one({'staff_id': user.id})
    if existing:
        # Return existing setup info
        secret = existing['secret']
    else:
        # Generate new secret
        secret = pyotp.random_base32()
        
        await db.attendance_totp.insert_one({
            'staff_id': user.id,
            'staff_name': user.name,
            'secret': secret,
            'setup_date': get_jakarta_now().isoformat(),
            'is_verified': False
        })
    
    # Create TOTP object
    totp = pyotp.TOTP(secret, interval=TOTP_INTERVAL)
    
    # Generate provisioning URI for authenticator apps
    uri = totp.provisioning_uri(
        name=user.email or user.name,
        issuer_name=TOTP_ISSUER
    )
    
    # Generate QR code as base64
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        'qr_code': f"data:image/png;base64,{qr_base64}",
        'secret': secret,  # For manual entry if QR doesn't work
        'uri': uri,
        'message': 'Scan this QR code with Google Authenticator or any TOTP app'
    }

@router.post("/attendance/totp/verify-setup")
async def verify_totp_setup(data: TOTPVerifyRequest, user: User = Depends(get_current_user)):
    """Verify TOTP setup by checking a code (called during initial setup)"""
    db = get_database()
    
    totp_data = await db.attendance_totp.find_one({'staff_id': user.id})
    if not totp_data:
        raise HTTPException(status_code=400, detail="TOTP not set up. Please set up first.")
    
    secret = totp_data['secret']
    totp = pyotp.TOTP(secret, interval=TOTP_INTERVAL)
    
    # Verify with some tolerance (allow previous and next codes)
    if totp.verify(data.code, valid_window=1):
        # Mark as verified
        await db.attendance_totp.update_one(
            {'staff_id': user.id},
            {'$set': {'is_verified': True, 'verified_date': get_jakarta_now().isoformat()}}
        )
        return {'success': True, 'message': 'Authenticator setup verified!'}
    else:
        raise HTTPException(status_code=400, detail="Invalid code. Please try again.")

# ==================== DAILY ATTENDANCE ====================

@router.post("/attendance/checkin")
async def check_in_with_totp(data: TOTPVerifyRequest, user: User = Depends(get_current_user)):
    """Check in using TOTP code"""
    db = get_database()
    
    today = get_jakarta_date_string()
    now = get_jakarta_now()
    
    # Check if already checked in today
    existing_record = await db.attendance_records.find_one({
        'staff_id': user.id,
        'date': today
    })
    
    if existing_record:
        raise HTTPException(
            status_code=400,
            detail=f"You have already checked in today at {existing_record.get('check_in_time')}"
        )
    
    # Check if staff has APPROVED leave for today (off_day or sakit)
    # If they have approved leave, they should NOT be marked late
    approved_leave = await db.leave_requests.find_one({
        'staff_id': user.id,
        'date': today,
        'status': 'approved'
    })
    
    has_approved_leave = approved_leave is not None
    leave_type = approved_leave.get('leave_type') if approved_leave else None
    
    # Get TOTP secret
    totp_data = await db.attendance_totp.find_one({'staff_id': user.id})
    if not totp_data:
        raise HTTPException(
            status_code=400,
            detail="Authenticator not set up. Please set up Google Authenticator first."
        )
    
    if not totp_data.get('is_verified'):
        raise HTTPException(
            status_code=400,
            detail="Authenticator setup not verified. Please complete setup first."
        )
    
    # Verify TOTP code
    secret = totp_data['secret']
    totp = pyotp.TOTP(secret, interval=TOTP_INTERVAL)
    
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code. Please check your authenticator app.")
    
    # Calculate lateness - but SKIP if staff has approved leave
    is_late = False
    late_minutes = 0
    
    if not has_approved_leave:
        # Only calculate lateness if no approved leave
        is_late = now.hour > SHIFT_START_HOUR or (now.hour == SHIFT_START_HOUR and now.minute > 0)
        if is_late:
            shift_start = now.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
            late_delta = now - shift_start
            late_minutes = int(late_delta.total_seconds() / 60)
    
    # Record attendance
    check_in_time = now.strftime('%H:%M:%S')
    
    attendance_record = {
        'staff_id': user.id,
        'staff_name': user.name,
        'date': today,
        'check_in_time': check_in_time,
        'check_in_datetime': now.isoformat(),
        'is_late': is_late,
        'late_minutes': late_minutes,
        'method': 'totp',
        'has_approved_leave': has_approved_leave,
        'leave_type': leave_type
    }
    
    await db.attendance_records.insert_one(attendance_record)
    
    # Build response message
    if has_approved_leave:
        status_message = f'On Leave ({leave_type})'
    elif is_late:
        status_message = 'Late'
    else:
        status_message = 'On Time'
    
    return {
        'success': True,
        'message': 'Attendance recorded successfully!',
        'staff_name': user.name,
        'check_in_time': check_in_time,
        'is_late': is_late,
        'late_minutes': late_minutes,
        'has_approved_leave': has_approved_leave,
        'leave_type': leave_type,
        'attendance_status': status_message
    }

@router.get("/attendance/check-today")
async def check_today_attendance(user: User = Depends(get_current_user)):
    """Check if current user has checked in today"""
    db = get_database()
    
    today = get_jakarta_date_string()
    record = await db.attendance_records.find_one({
        'staff_id': user.id,
        'date': today
    })
    
    if record:
        return {
            'checked_in': True,
            'check_in_time': record.get('check_in_time'),
            'is_late': record.get('is_late', False),
            'late_minutes': record.get('late_minutes', 0)
        }
    
    return {'checked_in': False}

# ==================== ADMIN ENDPOINTS ====================

@router.get("/attendance/admin/today")
async def get_today_attendance(user: User = Depends(get_current_user)):
    """Get today's attendance records (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    today = get_jakarta_date_string()
    
    # Get all attendance records for today
    records = await db.attendance_records.find(
        {'date': today},
        {'_id': 0}
    ).sort('check_in_time', 1).to_list(1000)
    
    # Get all staff
    all_staff = await db.users.find(
        {'role': 'staff'},
        {'_id': 0, 'id': 1, 'name': 1, 'email': 1}
    ).to_list(1000)
    
    checked_in_ids = {r['staff_id'] for r in records}
    not_checked_in = [s for s in all_staff if s['id'] not in checked_in_ids]
    
    # Summary stats
    total_staff = len(all_staff)
    checked_in_count = len(records)
    late_count = sum(1 for r in records if r.get('is_late'))
    on_time_count = checked_in_count - late_count
    
    return {
        'date': today,
        'summary': {
            'total_staff': total_staff,
            'checked_in': checked_in_count,
            'not_checked_in': total_staff - checked_in_count,
            'on_time': on_time_count,
            'late': late_count
        },
        'records': records,
        'not_checked_in': not_checked_in
    }

@router.get("/attendance/admin/totp-status")
async def get_all_totp_status(user: User = Depends(get_current_user)):
    """Get TOTP setup status for all staff (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all staff
    all_staff = await db.users.find(
        {'role': 'staff'},
        {'_id': 0, 'id': 1, 'name': 1, 'email': 1}
    ).to_list(1000)
    
    # Get TOTP setup data
    totp_data = await db.attendance_totp.find({}, {'_id': 0}).to_list(1000)
    totp_by_staff = {t['staff_id']: t for t in totp_data}
    
    result = []
    for staff in all_staff:
        totp = totp_by_staff.get(staff['id'])
        result.append({
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'email': staff.get('email'),
            'is_setup': totp is not None,
            'is_verified': totp.get('is_verified', False) if totp else False,
            'setup_date': totp.get('setup_date') if totp else None
        })
    
    return {'staff': result}

@router.delete("/attendance/admin/totp/{staff_id}")
async def reset_staff_totp(staff_id: str, user: User = Depends(get_current_user)):
    """Reset TOTP for a staff member (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.attendance_totp.delete_one({'staff_id': staff_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No TOTP setup found for this staff")
    
    return {'success': True, 'message': 'TOTP reset. Staff will need to set up again.'}

@router.get("/attendance/admin/records")
async def get_attendance_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    staff_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get attendance history with filters (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not start_date:
        start_date = (get_jakarta_now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = get_jakarta_date_string()
    
    query = {'date': {'$gte': start_date, '$lte': end_date}}
    if staff_id:
        query['staff_id'] = staff_id
    
    records = await db.attendance_records.find(query, {'_id': 0}).sort('date', -1).to_list(10000)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_records': len(records),
        'records': records
    }
