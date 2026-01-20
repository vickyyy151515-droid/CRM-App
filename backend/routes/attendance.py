# Attendance System with Device-Registered QR Code
# - Staff must scan unique QR with registered phone for first login of day
# - QR expires in 1 minute
# - One device per staff account
# - Shift: 11:00 AM - 23:00 PM Jakarta time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import pytz
from .deps import (
    User, get_db, get_current_user, get_admin_user,
    get_jakarta_now
)

router = APIRouter(tags=["Attendance"])

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Shift configuration
SHIFT_START_HOUR = 11  # 11:00 AM
SHIFT_START_MINUTE = 0
SHIFT_END_HOUR = 23    # 11:00 PM
SHIFT_END_MINUTE = 0
LATE_GRACE_MINUTES = 15  # 15 minutes grace period

# QR expiry time in seconds
QR_EXPIRY_SECONDS = 60  # 1 minute


class DeviceRegistration(BaseModel):
    device_token: str
    device_name: Optional[str] = None


class QRScanRequest(BaseModel):
    qr_code: str
    device_token: str


# ==================== STAFF ENDPOINTS ====================

@router.get("/attendance/check-today")
async def check_today_attendance(user: User = Depends(get_current_user)):
    """Check if current user has checked in today"""
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    
    # Check if already checked in today
    record = await db.attendance_records.find_one({
        'staff_id': user.id,
        'date': today
    }, {'_id': 0})
    
    if record:
        return {
            'checked_in': True,
            'check_in_time': record.get('check_in_time'),
            'status': record.get('status'),
            'date': today
        }
    
    return {
        'checked_in': False,
        'date': today,
        'message': 'Please scan QR code to check in'
    }


@router.post("/attendance/generate-qr")
async def generate_qr_code(user: User = Depends(get_current_user)):
    """Generate a unique QR code for attendance (expires in 1 minute)"""
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    
    # Check if already checked in today
    existing = await db.attendance_records.find_one({
        'staff_id': user.id,
        'date': today
    })
    
    if existing:
        return {
            'already_checked_in': True,
            'check_in_time': existing.get('check_in_time'),
            'message': 'You have already checked in today'
        }
    
    # Generate unique QR code
    qr_code = f"ATT-{user.id}-{secrets.token_urlsafe(16)}"
    expires_at = now + timedelta(seconds=QR_EXPIRY_SECONDS)
    
    # Delete any existing unused QR codes for this user
    await db.attendance_qr_codes.delete_many({
        'staff_id': user.id,
        'used': False
    })
    
    # Store QR code
    await db.attendance_qr_codes.insert_one({
        'staff_id': user.id,
        'staff_name': user.name,
        'qr_code': qr_code,
        'created_at': now.isoformat(),
        'expires_at': expires_at.isoformat(),
        'used': False
    })
    
    return {
        'qr_code': qr_code,
        'expires_at': expires_at.isoformat(),
        'expires_in_seconds': QR_EXPIRY_SECONDS,
        'staff_name': user.name
    }


@router.get("/attendance/device-status")
async def get_device_status(user: User = Depends(get_current_user)):
    """Check if current user has a registered device"""
    db = get_db()
    
    device = await db.device_registrations.find_one({
        'staff_id': user.id,
        'is_active': True
    }, {'_id': 0})
    
    if device:
        return {
            'has_device': True,
            'device_name': device.get('device_name', 'Unknown Device'),
            'registered_at': device.get('registered_at')
        }
    
    return {
        'has_device': False,
        'message': 'No device registered. Please register your phone first.'
    }


@router.post("/attendance/register-device")
async def register_device(data: DeviceRegistration, user: User = Depends(get_current_user)):
    """Register a phone device to staff account (one device per staff)"""
    db = get_db()
    now = get_jakarta_now()
    
    # Check if this device is already registered to another user
    existing_device = await db.device_registrations.find_one({
        'device_token': data.device_token,
        'is_active': True
    })
    
    if existing_device and existing_device['staff_id'] != user.id:
        raise HTTPException(
            status_code=400,
            detail="This device is already registered to another staff member"
        )
    
    # Check if user already has a device registered
    existing_user_device = await db.device_registrations.find_one({
        'staff_id': user.id,
        'is_active': True
    })
    
    if existing_user_device:
        # Update existing registration
        await db.device_registrations.update_one(
            {'staff_id': user.id, 'is_active': True},
            {'$set': {
                'device_token': data.device_token,
                'device_name': data.device_name or 'Mobile Device',
                'updated_at': now.isoformat()
            }}
        )
        return {
            'status': 'updated',
            'message': 'Device registration updated successfully'
        }
    
    # Register new device
    await db.device_registrations.insert_one({
        'staff_id': user.id,
        'staff_name': user.name,
        'device_token': data.device_token,
        'device_name': data.device_name or 'Mobile Device',
        'registered_at': now.isoformat(),
        'is_active': True
    })
    
    return {
        'status': 'registered',
        'message': 'Device registered successfully'
    }


@router.post("/attendance/scan")
async def scan_qr_code(data: QRScanRequest):
    """
    Verify QR code scan from phone.
    Called from the phone scanner - verifies device registration and QR validity.
    """
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    
    # Find the QR code
    qr_record = await db.attendance_qr_codes.find_one({
        'qr_code': data.qr_code,
        'used': False
    })
    
    if not qr_record:
        raise HTTPException(status_code=400, detail="Invalid or expired QR code")
    
    # Check if QR is expired
    expires_at = datetime.fromisoformat(qr_record['expires_at'].replace('Z', '+00:00'))
    if expires_at.tzinfo is None:
        expires_at = JAKARTA_TZ.localize(expires_at)
    
    if now > expires_at:
        # Mark as used to prevent reuse
        await db.attendance_qr_codes.update_one(
            {'qr_code': data.qr_code},
            {'$set': {'used': True}}
        )
        raise HTTPException(status_code=400, detail="QR code has expired. Please generate a new one.")
    
    staff_id = qr_record['staff_id']
    
    # Verify device is registered to this staff
    device = await db.device_registrations.find_one({
        'staff_id': staff_id,
        'device_token': data.device_token,
        'is_active': True
    })
    
    if not device:
        # Check if device belongs to another user
        other_device = await db.device_registrations.find_one({
            'device_token': data.device_token,
            'is_active': True
        })
        
        if other_device:
            raise HTTPException(
                status_code=403,
                detail="This device is registered to another staff member"
            )
        else:
            raise HTTPException(
                status_code=403,
                detail="This device is not registered. Please register your device first."
            )
    
    # Check if already checked in today
    existing_attendance = await db.attendance_records.find_one({
        'staff_id': staff_id,
        'date': today
    })
    
    if existing_attendance:
        return {
            'status': 'already_checked_in',
            'message': 'You have already checked in today',
            'check_in_time': existing_attendance.get('check_in_time')
        }
    
    # Determine if late
    shift_start = now.replace(hour=SHIFT_START_HOUR, minute=SHIFT_START_MINUTE, second=0, microsecond=0)
    grace_end = shift_start + timedelta(minutes=LATE_GRACE_MINUTES)
    
    if now <= grace_end:
        status = 'on_time'
    else:
        status = 'late'
        minutes_late = int((now - shift_start).total_seconds() / 60)
    
    # Mark QR as used
    await db.attendance_qr_codes.update_one(
        {'qr_code': data.qr_code},
        {'$set': {'used': True, 'used_at': now.isoformat()}}
    )
    
    # Record attendance
    attendance_record = {
        'staff_id': staff_id,
        'staff_name': qr_record.get('staff_name', 'Unknown'),
        'date': today,
        'check_in_time': now.isoformat(),
        'check_in_hour': now.strftime('%H:%M'),
        'status': status,
        'device_used': device.get('device_name', 'Mobile Device'),
        'device_token': data.device_token
    }
    
    if status == 'late':
        attendance_record['minutes_late'] = minutes_late
    
    await db.attendance_records.insert_one(attendance_record)
    
    return {
        'status': 'success',
        'message': f'Checked in successfully! Status: {status.upper()}',
        'check_in_time': now.strftime('%H:%M'),
        'attendance_status': status,
        'staff_name': qr_record.get('staff_name')
    }


@router.get("/attendance/my-records")
async def get_my_attendance_records(
    month: Optional[str] = None,  # Format: YYYY-MM
    user: User = Depends(get_current_user)
):
    """Get current user's attendance records"""
    db = get_db()
    now = get_jakarta_now()
    
    if not month:
        month = now.strftime('%Y-%m')
    
    # Get records for the month
    records = await db.attendance_records.find(
        {
            'staff_id': user.id,
            'date': {'$regex': f'^{month}'}
        },
        {'_id': 0}
    ).sort('date', -1).to_list(100)
    
    # Calculate summary
    total_days = len(records)
    on_time = sum(1 for r in records if r.get('status') == 'on_time')
    late = sum(1 for r in records if r.get('status') == 'late')
    
    return {
        'month': month,
        'records': records,
        'summary': {
            'total_days': total_days,
            'on_time': on_time,
            'late': late
        }
    }


# ==================== ADMIN ENDPOINTS ====================

@router.get("/attendance/admin/today")
async def get_today_attendance(admin: User = Depends(get_admin_user)):
    """Get today's attendance summary (Admin only)"""
    db = get_db()
    now = get_jakarta_now()
    today = now.strftime('%Y-%m-%d')
    
    # Get all staff
    all_staff = await db.users.find(
        {'role': 'staff'},
        {'_id': 0, 'id': 1, 'name': 1, 'email': 1}
    ).to_list(1000)
    
    # Get today's attendance records
    attendance_records = await db.attendance_records.find(
        {'date': today},
        {'_id': 0}
    ).to_list(1000)
    
    # Map attendance by staff_id
    attendance_map = {r['staff_id']: r for r in attendance_records}
    
    # Build response
    staff_attendance = []
    checked_in_count = 0
    on_time_count = 0
    late_count = 0
    not_checked_in_count = 0
    
    for staff in all_staff:
        record = attendance_map.get(staff['id'])
        if record:
            checked_in_count += 1
            if record.get('status') == 'on_time':
                on_time_count += 1
            else:
                late_count += 1
            
            staff_attendance.append({
                'staff_id': staff['id'],
                'name': staff['name'],
                'email': staff['email'],
                'checked_in': True,
                'check_in_time': record.get('check_in_hour'),
                'status': record.get('status'),
                'minutes_late': record.get('minutes_late', 0)
            })
        else:
            not_checked_in_count += 1
            staff_attendance.append({
                'staff_id': staff['id'],
                'name': staff['name'],
                'email': staff['email'],
                'checked_in': False,
                'check_in_time': None,
                'status': 'not_checked_in'
            })
    
    # Sort: not checked in first, then late, then on time
    status_order = {'not_checked_in': 0, 'late': 1, 'on_time': 2}
    staff_attendance.sort(key=lambda x: (status_order.get(x['status'], 3), x['name']))
    
    return {
        'date': today,
        'current_time': now.strftime('%H:%M'),
        'shift_start': f'{SHIFT_START_HOUR:02d}:{SHIFT_START_MINUTE:02d}',
        'staff': staff_attendance,
        'summary': {
            'total_staff': len(all_staff),
            'checked_in': checked_in_count,
            'not_checked_in': not_checked_in_count,
            'on_time': on_time_count,
            'late': late_count
        }
    }


@router.get("/attendance/admin/records")
async def get_attendance_records(
    start_date: Optional[str] = None,  # Format: YYYY-MM-DD
    end_date: Optional[str] = None,    # Format: YYYY-MM-DD
    staff_id: Optional[str] = None,
    admin: User = Depends(get_admin_user)
):
    """Get attendance records with filters (Admin only)"""
    db = get_db()
    now = get_jakarta_now()
    
    # Default to current month
    if not start_date:
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = now.strftime('%Y-%m-%d')
    
    # Build query
    query = {
        'date': {'$gte': start_date, '$lte': end_date}
    }
    
    if staff_id:
        query['staff_id'] = staff_id
    
    records = await db.attendance_records.find(
        query,
        {'_id': 0}
    ).sort('date', -1).to_list(10000)
    
    # Calculate summary
    total_records = len(records)
    on_time = sum(1 for r in records if r.get('status') == 'on_time')
    late = sum(1 for r in records if r.get('status') == 'late')
    
    # Group by staff for summary
    staff_summary = {}
    for r in records:
        sid = r['staff_id']
        if sid not in staff_summary:
            staff_summary[sid] = {
                'staff_id': sid,
                'staff_name': r.get('staff_name', 'Unknown'),
                'total_days': 0,
                'on_time': 0,
                'late': 0
            }
        staff_summary[sid]['total_days'] += 1
        if r.get('status') == 'on_time':
            staff_summary[sid]['on_time'] += 1
        else:
            staff_summary[sid]['late'] += 1
    
    return {
        'date_range': {'start': start_date, 'end': end_date},
        'records': records,
        'summary': {
            'total_records': total_records,
            'on_time': on_time,
            'late': late
        },
        'by_staff': list(staff_summary.values())
    }


@router.get("/attendance/admin/devices")
async def get_registered_devices(admin: User = Depends(get_admin_user)):
    """Get all registered devices (Admin only)"""
    db = get_db()
    
    devices = await db.device_registrations.find(
        {'is_active': True},
        {'_id': 0}
    ).to_list(1000)
    
    return {
        'devices': devices,
        'total': len(devices)
    }


@router.delete("/attendance/admin/device/{staff_id}")
async def reset_device_registration(staff_id: str, admin: User = Depends(get_admin_user)):
    """Reset device registration for a staff member (Admin only)"""
    db = get_db()
    now = get_jakarta_now()
    
    # Verify staff exists
    staff = await db.users.find_one({'id': staff_id, 'role': 'staff'})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Deactivate device registration
    result = await db.device_registrations.update_many(
        {'staff_id': staff_id},
        {'$set': {
            'is_active': False,
            'deactivated_at': now.isoformat(),
            'deactivated_by': admin.id
        }}
    )
    
    return {
        'status': 'success',
        'message': f'Device registration reset for {staff["name"]}',
        'modified_count': result.modified_count
    }


@router.get("/attendance/admin/export")
async def export_attendance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    token: Optional[str] = None,
    admin: User = Depends(get_admin_user)
):
    """Export attendance records to JSON (can be converted to Excel on frontend)"""
    db = get_db()
    now = get_jakarta_now()
    
    if not start_date:
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = now.strftime('%Y-%m-%d')
    
    records = await db.attendance_records.find(
        {'date': {'$gte': start_date, '$lte': end_date}},
        {'_id': 0}
    ).sort([('date', 1), ('staff_name', 1)]).to_list(10000)
    
    # Format for export
    export_data = []
    for r in records:
        export_data.append({
            'Date': r.get('date'),
            'Staff Name': r.get('staff_name'),
            'Check-in Time': r.get('check_in_hour'),
            'Status': r.get('status', '').upper(),
            'Minutes Late': r.get('minutes_late', 0) if r.get('status') == 'late' else 0,
            'Device': r.get('device_used', 'Unknown')
        })
    
    return {
        'data': export_data,
        'date_range': {'start': start_date, 'end': end_date},
        'total_records': len(export_data)
    }
