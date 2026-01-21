"""
Attendance System API
- QR Code based attendance with device registration
- 1 Staff = 1 Phone (prevents cheating)
- 1 QR Code = 1 Use (prevents sharing)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import secrets
from routes.deps import get_database
from routes.auth import get_current_user, User

router = APIRouter(tags=["Attendance"])

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

# Shift configuration
SHIFT_START_HOUR = 11  # 11:00 AM
SHIFT_END_HOUR = 23    # 11:00 PM

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')

# ==================== MODELS ====================

class DeviceRegistration(BaseModel):
    device_id: str
    device_name: Optional[str] = "Mobile Device"

class QRScanRequest(BaseModel):
    qr_code: str
    device_id: str

# ==================== QR CODE GENERATION (Computer) ====================

@router.post("/attendance/generate-qr")
async def generate_qr_code(user: User = Depends(get_current_user)):
    """Generate a unique QR code for staff to scan. Called from computer."""
    db = get_database()
    
    today = get_jakarta_date_string()
    
    # Check if staff already checked in today
    existing_record = await db.attendance_records.find_one({
        'staff_id': user.id,
        'date': today
    })
    
    if existing_record:
        return {
            'already_checked_in': True,
            'check_in_time': existing_record.get('check_in_time'),
            'message': 'You have already checked in today'
        }
    
    # Invalidate any existing unused QR codes for this staff
    await db.attendance_qr_codes.update_many(
        {'staff_id': user.id, 'used': False},
        {'$set': {'used': True, 'invalidated': True}}
    )
    
    # Generate new unique QR code
    qr_code = f"ATT-{user.id}-{secrets.token_urlsafe(16)}-{int(datetime.now().timestamp())}"
    expires_at = get_jakarta_now() + timedelta(seconds=60)  # Valid for 1 minute
    
    await db.attendance_qr_codes.insert_one({
        'qr_code': qr_code,
        'staff_id': user.id,
        'staff_name': user.name,
        'created_at': get_jakarta_now().isoformat(),
        'expires_at': expires_at.isoformat(),
        'used': False,
        'used_by': None,
        'used_at': None
    })
    
    return {
        'qr_code': qr_code,
        'expires_in_seconds': 60,
        'staff_name': user.name
    }

# ==================== DEVICE REGISTRATION (Phone) ====================

@router.get("/attendance/device-status")
async def get_device_status(user: User = Depends(get_current_user)):
    """Check if current user has a registered device"""
    db = get_database()
    
    device = await db.attendance_devices.find_one({'staff_id': user.id})
    
    return {
        'has_device': device is not None,
        'device_name': device.get('device_name') if device else None,
        'registered_at': device.get('registered_at') if device else None
    }

@router.post("/attendance/register-device")
async def register_device(data: DeviceRegistration, user: User = Depends(get_current_user)):
    """Register a phone for attendance scanning. 1 staff = 1 phone."""
    db = get_database()
    
    # Check if staff already has a registered device
    existing = await db.attendance_devices.find_one({'staff_id': user.id})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a registered device: {existing.get('device_name')}. Contact admin to change."
        )
    
    # Check if this device_id is already registered to another staff
    device_used = await db.attendance_devices.find_one({'device_id': data.device_id})
    if device_used:
        raise HTTPException(
            status_code=400,
            detail="This device is already registered to another staff member."
        )
    
    # Register the device
    await db.attendance_devices.insert_one({
        'staff_id': user.id,
        'staff_name': user.name,
        'device_id': data.device_id,
        'device_name': data.device_name,
        'registered_at': get_jakarta_now().isoformat()
    })
    
    return {'success': True, 'message': 'Device registered successfully'}

# ==================== QR SCANNING (Phone) ====================

@router.post("/attendance/scan")
async def scan_qr_code(data: QRScanRequest, user: User = Depends(get_current_user)):
    """Process scanned QR code and record attendance."""
    db = get_database()
    
    today = get_jakarta_date_string()
    now = get_jakarta_now()
    
    # Verify device is registered to this staff
    device = await db.attendance_devices.find_one({
        'staff_id': user.id,
        'device_id': data.device_id
    })
    
    if not device:
        raise HTTPException(
            status_code=403,
            detail="This device is not registered for your account. Please use your registered phone."
        )
    
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
    
    # Find and validate QR code
    qr_record = await db.attendance_qr_codes.find_one({'qr_code': data.qr_code})
    
    if not qr_record:
        raise HTTPException(status_code=400, detail="Invalid QR code")
    
    if qr_record.get('used'):
        raise HTTPException(status_code=400, detail="This QR code has already been used")
    
    # Check expiration
    expires_at = datetime.fromisoformat(qr_record['expires_at'])
    if now > expires_at:
        raise HTTPException(status_code=400, detail="This QR code has expired. Please ask for a new one.")
    
    # Verify QR belongs to the scanning user
    if qr_record['staff_id'] != user.id:
        raise HTTPException(
            status_code=403,
            detail="This QR code belongs to another staff member"
        )
    
    # Mark QR as used (CRITICAL: Single use)
    await db.attendance_qr_codes.update_one(
        {'qr_code': data.qr_code},
        {
            '$set': {
                'used': True,
                'used_by': user.id,
                'used_at': now.isoformat()
            }
        }
    )
    
    # Calculate lateness
    is_late = now.hour > SHIFT_START_HOUR or (now.hour == SHIFT_START_HOUR and now.minute > 0)
    late_minutes = 0
    if is_late:
        shift_start = now.replace(hour=SHIFT_START_HOUR, minute=0, second=0, microsecond=0)
        late_delta = now - shift_start
        late_minutes = int(late_delta.total_seconds() / 60)
    
    # Record attendance
    check_in_time = now.strftime('%H:%M:%S')
    
    await db.attendance_records.insert_one({
        'staff_id': user.id,
        'staff_name': user.name,
        'date': today,
        'check_in_time': check_in_time,
        'check_in_datetime': now.isoformat(),
        'is_late': is_late,
        'late_minutes': late_minutes,
        'device_id': data.device_id,
        'device_name': device.get('device_name'),
        'qr_code': data.qr_code
    })
    
    return {
        'success': True,
        'message': 'Attendance recorded successfully!',
        'staff_name': user.name,
        'check_in_time': check_in_time,
        'is_late': is_late,
        'late_minutes': late_minutes,
        'attendance_status': 'Late' if is_late else 'On Time'
    }

# ==================== CHECK STATUS ====================

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
    
    # Get all staff to show who hasn't checked in
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
    
    # Default to last 30 days
    if not start_date:
        start_date = (get_jakarta_now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = get_jakarta_date_string()
    
    query = {
        'date': {'$gte': start_date, '$lte': end_date}
    }
    
    if staff_id:
        query['staff_id'] = staff_id
    
    records = await db.attendance_records.find(
        query,
        {'_id': 0}
    ).sort('date', -1).to_list(10000)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_records': len(records),
        'records': records
    }

@router.get("/attendance/admin/devices")
async def get_registered_devices(user: User = Depends(get_current_user)):
    """Get all registered devices (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    devices = await db.attendance_devices.find(
        {},
        {'_id': 0}
    ).to_list(1000)
    
    return {'devices': devices}

@router.delete("/attendance/admin/device/{staff_id}")
async def delete_device_registration(staff_id: str, user: User = Depends(get_current_user)):
    """Delete a staff's device registration (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.attendance_devices.delete_one({'staff_id': staff_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No device found for this staff")
    
    return {'success': True, 'message': 'Device registration deleted'}

@router.get("/attendance/admin/export")
async def export_attendance(
    start_date: str,
    end_date: str,
    user: User = Depends(get_current_user)
):
    """Export attendance data (admin only)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    records = await db.attendance_records.find(
        {'date': {'$gte': start_date, '$lte': end_date}},
        {'_id': 0, 'qr_code': 0, 'device_id': 0}
    ).sort([('date', -1), ('check_in_time', 1)]).to_list(50000)
    
    return {'records': records}
