"""
Attendance System API - TOTP Based (Google Authenticator compatible)
- Staff sets up Google Authenticator ONCE
- Daily: Staff types 6-digit code to check in
- Code changes every 30 seconds (standard TOTP interval)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import pyotp
import qrcode
import io
import base64
from routes.deps import get_db
from routes.auth import get_current_user, User

router = APIRouter(tags=["Attendance"])

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

# Shift configuration
SHIFT_START_HOUR = 11  # 11:00 AM
SHIFT_END_HOUR = 23    # 11:00 PM

# TOTP Configuration
TOTP_INTERVAL = 30  # Code changes every 30 seconds (Google Authenticator standard)
TOTP_ISSUER = "CRM Attendance"

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')

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
        'method': 'totp'
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

# ==================== FEE & PAYMENT SYSTEM ====================
# $5 per minute of lateness

LATENESS_FEE_PER_MINUTE = 5  # $5 per minute

# Default currency rates (can be updated via API)
DEFAULT_CURRENCY_RATES = {
    'USD': 1,
    'THB': 3100,  # $1 = 3100 THB
    'IDR': 16700  # $1 = 16700 IDR
}

class WaiveFeeRequest(BaseModel):
    reason: str

class InstallmentRequest(BaseModel):
    num_months: int  # 1 or 2

class ManualFeeRequest(BaseModel):
    amount_usd: float
    reason: str
    date: Optional[str] = None  # If not provided, use today

class PaymentRequest(BaseModel):
    amount: float
    currency: str  # USD, THB, or IDR
    note: Optional[str] = None

class CurrencyRateUpdate(BaseModel):
    thb_rate: float
    idr_rate: float

async def get_currency_rates(db):
    """Get currency rates from database or use defaults"""
    settings = await db.system_settings.find_one({'key': 'currency_rates'})
    if settings:
        return settings['rates']
    return DEFAULT_CURRENCY_RATES

@router.get("/attendance/admin/fees/currency-rates")
async def get_currency_rates_endpoint(user: User = Depends(get_current_user)):
    """Get current currency rates"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rates = await get_currency_rates(db)
    return {'rates': rates}

@router.put("/attendance/admin/fees/currency-rates")
async def update_currency_rates(data: CurrencyRateUpdate, user: User = Depends(get_current_user)):
    """Update currency rates"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    rates = {
        'USD': 1,
        'THB': data.thb_rate,
        'IDR': data.idr_rate
    }
    
    await db.system_settings.update_one(
        {'key': 'currency_rates'},
        {'$set': {'key': 'currency_rates', 'rates': rates, 'updated_at': get_jakarta_now().isoformat(), 'updated_by': user.name}},
        upsert=True
    )
    
    return {'success': True, 'rates': rates}

@router.get("/attendance/admin/fees/summary")
async def get_fees_summary(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    """Get lateness fee summary for all staff"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = get_jakarta_now()
    year = year or now.year
    month = month or now.month
    
    # Get currency rates
    currency_rates = await get_currency_rates(db)
    
    # Build date filter for the month
    date_prefix = f"{year}-{str(month).zfill(2)}"
    
    # Get all attendance records with lateness for the month
    attendance_records = await db.attendance_records.find({
        'date': {'$regex': f'^{date_prefix}'},
        'is_late': True,
        'late_minutes': {'$gt': 0}
    }, {'_id': 0}).to_list(100000)
    
    # Get existing fee waivers
    fee_waivers = await db.lateness_fee_waivers.find({
        'year': year, 'month': month
    }, {'_id': 0}).to_list(10000)
    waiver_map = {(w['staff_id'], w.get('date', '')): w for w in fee_waivers}
    
    # Get manual fees for the month
    manual_fees = await db.lateness_manual_fees.find({
        'year': year, 'month': month
    }, {'_id': 0}).to_list(10000)
    manual_fee_map = {}
    for mf in manual_fees:
        if mf['staff_id'] not in manual_fee_map:
            manual_fee_map[mf['staff_id']] = []
        manual_fee_map[mf['staff_id']].append(mf)
    
    # Get partial payments for the month
    partial_payments = await db.lateness_partial_payments.find({
        'year': year, 'month': month
    }, {'_id': 0}).to_list(10000)
    payment_map = {}
    for p in partial_payments:
        if p['staff_id'] not in payment_map:
            payment_map[p['staff_id']] = []
        payment_map[p['staff_id']].append(p)
    
    # Get installment plans
    installments = await db.lateness_fee_installments.find({
        'year': year, 'month': month
    }, {'_id': 0}).to_list(1000)
    installment_map = {i['staff_id']: i for i in installments}
    
    # Get all staff
    all_staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'id': 1, 'name': 1}).to_list(1000)
    staff_name_map = {s['id']: s['name'] for s in all_staff}
    
    # Calculate fees per staff
    staff_fees = {}
    
    # Process attendance-based fees
    for record in attendance_records:
        staff_id = record['staff_id']
        staff_name = record.get('staff_name', staff_name_map.get(staff_id, 'Unknown'))
        late_minutes = record.get('late_minutes', 0)
        record_date = record.get('date', '')
        
        # Check if this specific record was waived
        waiver_key = (staff_id, record_date)
        if waiver_key in waiver_map:
            continue  # Skip waived records
        
        if staff_id not in staff_fees:
            staff_fees[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'total_late_minutes': 0,
                'total_fee': 0,
                'total_paid': 0,
                'remaining_fee': 0,
                'late_days': 0,
                'records': [],
                'manual_fees': [],
                'payments': []
            }
        
        fee = late_minutes * LATENESS_FEE_PER_MINUTE
        staff_fees[staff_id]['total_late_minutes'] += late_minutes
        staff_fees[staff_id]['total_fee'] += fee
        staff_fees[staff_id]['late_days'] += 1
        staff_fees[staff_id]['records'].append({
            'date': record_date,
            'late_minutes': late_minutes,
            'fee': fee,
            'check_in_time': record.get('check_in_time'),
            'type': 'attendance'
        })
    
    # Add manual fees
    for staff_id, fees in manual_fee_map.items():
        staff_name = staff_name_map.get(staff_id, 'Unknown')
        if staff_id not in staff_fees:
            staff_fees[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'total_late_minutes': 0,
                'total_fee': 0,
                'total_paid': 0,
                'remaining_fee': 0,
                'late_days': 0,
                'records': [],
                'manual_fees': [],
                'payments': []
            }
        
        for mf in fees:
            staff_fees[staff_id]['total_fee'] += mf['amount_usd']
            staff_fees[staff_id]['manual_fees'].append({
                'id': mf.get('id'),
                'date': mf.get('date'),
                'amount_usd': mf['amount_usd'],
                'reason': mf.get('reason'),
                'added_by': mf.get('added_by_name'),
                'added_at': mf.get('added_at'),
                'type': 'manual'
            })
    
    # Add partial payments and calculate remaining
    for staff_id, payments in payment_map.items():
        if staff_id in staff_fees:
            for p in payments:
                staff_fees[staff_id]['total_paid'] += p['amount_usd']
                staff_fees[staff_id]['payments'].append({
                    'id': p.get('id'),
                    'date': p.get('paid_at'),
                    'amount_usd': p['amount_usd'],
                    'original_amount': p.get('original_amount'),
                    'original_currency': p.get('original_currency'),
                    'note': p.get('note'),
                    'recorded_by': p.get('recorded_by_name')
                })
    
    # Calculate remaining fees and add installment info
    for staff_id, data in staff_fees.items():
        data['remaining_fee'] = max(0, data['total_fee'] - data['total_paid'])
        
        # Add currency conversions
        data['total_fee_thb'] = data['total_fee'] * currency_rates['THB']
        data['total_fee_idr'] = data['total_fee'] * currency_rates['IDR']
        data['remaining_fee_thb'] = data['remaining_fee'] * currency_rates['THB']
        data['remaining_fee_idr'] = data['remaining_fee'] * currency_rates['IDR']
        data['total_paid_thb'] = data['total_paid'] * currency_rates['THB']
        data['total_paid_idr'] = data['total_paid'] * currency_rates['IDR']
        
        # Installment info
        installment = installment_map.get(staff_id)
        if installment:
            data['installment'] = {
                'num_months': installment['num_months'],
                'monthly_amount': installment['monthly_amount'],
                'paid_months': installment.get('paid_months', []),
                'created_at': installment.get('created_at')
            }
        else:
            data['installment'] = None
    
    # Calculate global totals
    total_fees = sum(d['total_fee'] for d in staff_fees.values())
    total_paid = sum(d['total_paid'] for d in staff_fees.values())
    total_remaining = sum(d['remaining_fee'] for d in staff_fees.values())
    total_late_minutes = sum(d['total_late_minutes'] for d in staff_fees.values())
    
    # Get all-time collected (from partial payments)
    all_payments = await db.lateness_partial_payments.find({}, {'_id': 0}).to_list(100000)
    total_collected_all_time = sum(p.get('amount_usd', 0) for p in all_payments)
    
    return {
        'year': year,
        'month': month,
        'fee_per_minute': LATENESS_FEE_PER_MINUTE,
        'currency_rates': currency_rates,
        'total_fees_this_month': total_fees,
        'total_fees_this_month_thb': total_fees * currency_rates['THB'],
        'total_fees_this_month_idr': total_fees * currency_rates['IDR'],
        'total_paid_this_month': total_paid,
        'total_remaining_this_month': total_remaining,
        'total_late_minutes': total_late_minutes,
        'total_collected_all_time': total_collected_all_time,
        'total_collected_all_time_thb': total_collected_all_time * currency_rates['THB'],
        'total_collected_all_time_idr': total_collected_all_time * currency_rates['IDR'],
        'staff_count_with_fees': len(staff_fees),
        'staff_fees': list(staff_fees.values())
    }

@router.post("/attendance/admin/fees/{staff_id}/waive")
async def waive_fee(
    staff_id: str,
    date: str,  # Waive fee for specific date
    data: WaiveFeeRequest,
    user: User = Depends(get_current_user)
):
    """Waive/cancel lateness fee for a specific date"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse date to get year/month
    try:
        parsed_date = datetime.strptime(date, '%Y-%m-%d')
        year = parsed_date.year
        month = parsed_date.month
    except:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Check if record exists
    record = await db.attendance_records.find_one({
        'staff_id': staff_id,
        'date': date,
        'is_late': True
    })
    
    if not record:
        raise HTTPException(status_code=404, detail="No late attendance record found for this date")
    
    # Create waiver
    waiver = {
        'staff_id': staff_id,
        'staff_name': record.get('staff_name', 'Unknown'),
        'date': date,
        'year': year,
        'month': month,
        'late_minutes': record.get('late_minutes', 0),
        'fee_waived': record.get('late_minutes', 0) * LATENESS_FEE_PER_MINUTE,
        'reason': data.reason,
        'waived_by': user.id,
        'waived_by_name': user.name,
        'waived_at': get_jakarta_now().isoformat()
    }
    
    await db.lateness_fee_waivers.insert_one(waiver)
    
    return {
        'success': True,
        'message': f'Fee waived for {record.get("staff_name")} on {date}',
        'fee_waived': waiver['fee_waived']
    }

@router.delete("/attendance/admin/fees/{staff_id}/waive/{date}")
async def remove_waiver(
    staff_id: str,
    date: str,
    user: User = Depends(get_current_user)
):
    """Remove a fee waiver (reinstate the fee)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.lateness_fee_waivers.delete_one({
        'staff_id': staff_id,
        'date': date
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No waiver found for this date")
    
    return {'success': True, 'message': 'Fee waiver removed, fee is now active'}

@router.post("/attendance/admin/fees/{staff_id}/installment")
async def setup_installment(
    staff_id: str,
    year: int,
    month: int,
    data: InstallmentRequest,
    user: User = Depends(get_current_user)
):
    """Set up installment plan for staff's lateness fees (max 2 months)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if data.num_months < 1 or data.num_months > 2:
        raise HTTPException(status_code=400, detail="Installment must be 1 or 2 months")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Calculate total fee for the month (excluding waivers)
    date_prefix = f"{year}-{str(month).zfill(2)}"
    
    attendance_records = await db.attendance_records.find({
        'staff_id': staff_id,
        'date': {'$regex': f'^{date_prefix}'},
        'is_late': True,
        'late_minutes': {'$gt': 0}
    }, {'_id': 0}).to_list(100)
    
    waivers = await db.lateness_fee_waivers.find({
        'staff_id': staff_id,
        'year': year,
        'month': month
    }, {'_id': 0}).to_list(100)
    waived_dates = set(w['date'] for w in waivers)
    
    total_fee = 0
    for record in attendance_records:
        if record['date'] not in waived_dates:
            total_fee += record.get('late_minutes', 0) * LATENESS_FEE_PER_MINUTE
    
    if total_fee == 0:
        raise HTTPException(status_code=400, detail="No fees to set up installment for")
    
    monthly_amount = total_fee / data.num_months
    
    # Create or update installment plan
    installment = {
        'staff_id': staff_id,
        'staff_name': staff['name'],
        'year': year,
        'month': month,
        'total_fee': total_fee,
        'num_months': data.num_months,
        'monthly_amount': monthly_amount,
        'paid_months': [],
        'created_by': user.id,
        'created_at': get_jakarta_now().isoformat()
    }
    
    await db.lateness_fee_installments.update_one(
        {'staff_id': staff_id, 'year': year, 'month': month},
        {'$set': installment},
        upsert=True
    )
    
    return {
        'success': True,
        'message': f'Installment plan created: ${monthly_amount:.2f}/month for {data.num_months} month(s)',
        'installment': installment
    }

@router.delete("/attendance/admin/fees/{staff_id}/installment")
async def cancel_installment(
    staff_id: str,
    year: int,
    month: int,
    user: User = Depends(get_current_user)
):
    """Cancel installment plan"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.lateness_fee_installments.delete_one({
        'staff_id': staff_id,
        'year': year,
        'month': month
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No installment plan found")
    
    return {'success': True, 'message': 'Installment plan cancelled'}

@router.post("/attendance/admin/fees/{staff_id}/pay")
async def record_payment(
    staff_id: str,
    year: int,
    month: int,
    payment_month: int,  # Which installment month is being paid (1 or 2)
    user: User = Depends(get_current_user)
):
    """Record a payment for an installment"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get installment plan
    installment = await db.lateness_fee_installments.find_one({
        'staff_id': staff_id,
        'year': year,
        'month': month
    })
    
    if not installment:
        raise HTTPException(status_code=404, detail="No installment plan found")
    
    if payment_month in installment.get('paid_months', []):
        raise HTTPException(status_code=400, detail=f"Month {payment_month} already paid")
    
    if payment_month > installment['num_months']:
        raise HTTPException(status_code=400, detail="Invalid payment month")
    
    # Record payment
    payment = {
        'staff_id': staff_id,
        'staff_name': installment['staff_name'],
        'year': year,
        'month': month,
        'payment_month': payment_month,
        'amount': installment['monthly_amount'],
        'recorded_by': user.id,
        'recorded_by_name': user.name,
        'paid_at': get_jakarta_now().isoformat()
    }
    
    await db.lateness_fee_payments.insert_one(payment)
    
    # Update installment with paid month
    await db.lateness_fee_installments.update_one(
        {'staff_id': staff_id, 'year': year, 'month': month},
        {'$push': {'paid_months': payment_month}}
    )
    
    return {
        'success': True,
        'message': f'Payment of ${installment["monthly_amount"]:.2f} recorded',
        'amount': installment['monthly_amount']
    }

@router.get("/attendance/admin/fees/waivers")
async def get_all_waivers(
    year: Optional[int] = None,
    month: Optional[int] = None,
    user: User = Depends(get_current_user)
):
    """Get all fee waivers for a month"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    now = get_jakarta_now()
    year = year or now.year
    month = month or now.month
    
    waivers = await db.lateness_fee_waivers.find({
        'year': year, 'month': month
    }, {'_id': 0}).to_list(10000)
    
    return {'year': year, 'month': month, 'waivers': waivers}

@router.post("/attendance/admin/fees/{staff_id}/manual")
async def add_manual_fee(
    staff_id: str,
    year: int,
    month: int,
    data: ManualFeeRequest,
    user: User = Depends(get_current_user)
):
    """Manually add a lateness fee for a staff member"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    fee_date = data.date or get_jakarta_date_string()
    
    manual_fee = {
        'id': str(uuid.uuid4()),
        'staff_id': staff_id,
        'staff_name': staff['name'],
        'year': year,
        'month': month,
        'date': fee_date,
        'amount_usd': data.amount_usd,
        'reason': data.reason,
        'added_by': user.id,
        'added_by_name': user.name,
        'added_at': get_jakarta_now().isoformat()
    }
    
    await db.lateness_manual_fees.insert_one(manual_fee)
    
    return {
        'success': True,
        'message': f'Manual fee of ${data.amount_usd} added for {staff["name"]}',
        'fee': {k: v for k, v in manual_fee.items() if k != '_id'}
    }

@router.delete("/attendance/admin/fees/manual/{fee_id}")
async def delete_manual_fee(
    fee_id: str,
    user: User = Depends(get_current_user)
):
    """Delete a manual fee"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.lateness_manual_fees.delete_one({'id': fee_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Manual fee not found")
    
    return {'success': True, 'message': 'Manual fee deleted'}

@router.post("/attendance/admin/fees/{staff_id}/payment")
async def record_partial_payment(
    staff_id: str,
    year: int,
    month: int,
    data: PaymentRequest,
    user: User = Depends(get_current_user)
):
    """Record a partial payment from staff (supports multiple currencies)"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if data.currency not in ['USD', 'THB', 'IDR']:
        raise HTTPException(status_code=400, detail="Currency must be USD, THB, or IDR")
    
    # Get staff info
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    # Get currency rates
    currency_rates = await get_currency_rates(db)
    
    # Convert to USD
    if data.currency == 'USD':
        amount_usd = data.amount
    elif data.currency == 'THB':
        amount_usd = data.amount / currency_rates['THB']
    else:  # IDR
        amount_usd = data.amount / currency_rates['IDR']
    
    payment = {
        'id': str(uuid.uuid4()),
        'staff_id': staff_id,
        'staff_name': staff['name'],
        'year': year,
        'month': month,
        'amount_usd': amount_usd,
        'original_amount': data.amount,
        'original_currency': data.currency,
        'note': data.note,
        'recorded_by': user.id,
        'recorded_by_name': user.name,
        'paid_at': get_jakarta_now().isoformat()
    }
    
    await db.lateness_partial_payments.insert_one(payment)
    
    return {
        'success': True,
        'message': f'Payment of {data.currency} {data.amount:,.0f} (${amount_usd:.2f} USD) recorded for {staff["name"]}',
        'payment': {k: v for k, v in payment.items() if k != '_id'}
    }

@router.delete("/attendance/admin/fees/payment/{payment_id}")
async def delete_payment(
    payment_id: str,
    user: User = Depends(get_current_user)
):
    """Delete a payment record"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.lateness_partial_payments.delete_one({'id': payment_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {'success': True, 'message': 'Payment deleted'}

@router.get("/attendance/admin/fees/staff-list")
async def get_staff_list_for_fees(user: User = Depends(get_current_user)):
    """Get list of all staff for manual fee assignment"""
    db = get_database()
    
    if user.role not in ['admin', 'master_admin']:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    staff = await db.users.find({'role': 'staff'}, {'_id': 0, 'id': 1, 'name': 1}).to_list(1000)
    return {'staff': staff}

