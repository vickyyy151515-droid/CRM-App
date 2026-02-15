# Scheduled Reports with Telegram Integration
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .deps import get_db, get_admin_user, User
from .notifications import create_notification
from .records import restore_invalidated_records_for_reservation
from utils.helpers import normalize_customer_id

router = APIRouter()

# Jakarta timezone
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Global scheduler instance
scheduler = None

class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    bot_token: str
    chat_id: str
    enabled: bool = True
    report_hour: int = 1  # Default 1 AM
    report_minute: int = 0

class AtRiskAlertConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    bot_token: str
    group_chat_id: str
    enabled: bool = True
    alert_hour: int = 11  # Default 11 AM
    alert_minute: int = 0
    inactive_days_threshold: int = 14  # Alert for customers inactive 14+ days

class StaffOfflineAlertConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool = True
    alert_hour: int = 11  # Default 11 AM
    alert_minute: int = 0

class ScheduledReportConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "scheduled_report_config"
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    enabled: bool = False
    report_hour: int = 1
    report_minute: int = 0
    last_sent: Optional[str] = None
    # At-risk alert settings
    atrisk_enabled: bool = False
    atrisk_group_chat_id: Optional[str] = None
    atrisk_hour: int = 11
    atrisk_minute: int = 0
    atrisk_inactive_days: int = 14
    atrisk_last_sent: Optional[str] = None
    # Staff offline alert settings
    staff_offline_enabled: bool = False
    staff_offline_hour: int = 11
    staff_offline_minute: int = 0
    staff_offline_last_sent: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


async def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Send a message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=30.0)
            
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API error: {response.text}")
                return False
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False


async def generate_daily_report(target_date: datetime = None) -> str:
    """Generate daily summary report for all staff and products"""
    db = get_db()
    
    if target_date is None:
        # Get yesterday's date in Jakarta timezone
        jakarta_now = datetime.now(JAKARTA_TZ)
        target_date = jakarta_now - timedelta(days=1)
    
    date_str = target_date.strftime('%Y-%m-%d')
    
    # Get all OMSET records for the target date
    records = await db.omset_records.find({
        'record_date': date_str
    }, {'_id': 0}).to_list(10000)
    
    if not records:
        return f"📊 <b>Daily CRM Report</b>\n📅 {date_str}\n\n<i>No records found for this date.</i>"
    
    # Get products for grouping
    products = await db.products.find({}, {'_id': 0}).to_list(100)
    product_map = {p['id']: p['name'] for p in products}
    
    # Group by product and staff
    product_staff_data = {}
    
    # Track unique customers per product-staff for RDP
    staff_ndp_customers = {}  # {(product_id, staff_id): set()}
    staff_rdp_customers = {}  # {(product_id, staff_id): set()}
    
    # Helper function to check if record has "tambahan" in notes
    def is_tambahan_record(record) -> bool:
        keterangan = record.get('keterangan', '') or ''
        return 'tambahan' in keterangan.lower()
    
    # Get ALL omset records to build first deposit map properly
    # We need to exclude "tambahan" records from first deposit calculation
    all_omset_records = await db.omset_records.find(
        {'$or': [{'approval_status': 'approved'}, {'approval_status': {'$exists': False}}]},
        {'_id': 0, 'staff_id': 1, 'staff_name': 1, 'customer_id': 1, 'customer_id_normalized': 1,
         'product_id': 1, 'product_name': 1, 'record_date': 1, 'keterangan': 1, 
         'depo_total': 1, 'nominal': 1, 'customer_name': 1}
    ).to_list(50000)
    
    # Build customer first deposit map - EXCLUDE "tambahan" records
    first_deposits = {}
    for record in sorted(all_omset_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        key = (cid_normalized, record.get('product_id', ''))
        if key not in first_deposits:
            first_deposits[key] = record['record_date']
    
    for record in records:
        product_id = record.get('product_id', 'unknown')
        product_name = product_map.get(product_id, product_id)
        staff_id = record.get('staff_id', 'unknown')
        staff_name = record.get('staff_name', 'Unknown Staff')
        
        if product_id not in product_staff_data:
            product_staff_data[product_id] = {
                'product_name': product_name,
                'staff': {},
                'totals': {'ndp': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
            }
        
        if staff_id not in product_staff_data[product_id]['staff']:
            product_staff_data[product_id]['staff'][staff_id] = {
                'staff_name': staff_name,
                'ndp': 0,
                'rdp': 0,
                'total_form': 0,
                'nominal': 0
            }
            staff_ndp_customers[(product_id, staff_id)] = set()
            staff_rdp_customers[(product_id, staff_id)] = set()
        
        # Calculate NDP/RDP
        # Note: "tambahan" records are always RDP (excluded from first_deposits)
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record.get('customer_id', ''))
        key = (cid_normalized, product_id)
        first_date = first_deposits.get(key)
        
        # If this record has "tambahan", it's always RDP
        if is_tambahan_record(record):
            is_ndp = False
        else:
            is_ndp = first_date == date_str
        
        nominal = record.get('depo_total', 0) or record.get('nominal', 0) or 0
        
        tracking_key = (product_id, staff_id)
        
        if is_ndp:
            if cid_normalized not in staff_ndp_customers[tracking_key]:
                staff_ndp_customers[tracking_key].add(cid_normalized)
                product_staff_data[product_id]['staff'][staff_id]['ndp'] += 1
                product_staff_data[product_id]['totals']['ndp'] += 1
        else:
            if cid_normalized not in staff_rdp_customers[tracking_key]:
                staff_rdp_customers[tracking_key].add(cid_normalized)
                product_staff_data[product_id]['staff'][staff_id]['rdp'] += 1
                product_staff_data[product_id]['totals']['rdp'] += 1
        
        product_staff_data[product_id]['staff'][staff_id]['total_form'] += 1
        product_staff_data[product_id]['staff'][staff_id]['nominal'] += nominal
        product_staff_data[product_id]['totals']['total_form'] += 1
        product_staff_data[product_id]['totals']['nominal'] += nominal
    
    # Format the report
    def format_rupiah(amount):
        return f"Rp {amount:,.0f}".replace(',', '.')
    
    report_lines = [
        f"📊 <b>Daily CRM Report</b>",
        f"📅 <b>Date:</b> {date_str}",
        f"⏰ <b>Generated:</b> {datetime.now(JAKARTA_TZ).strftime('%Y-%m-%d %H:%M')} WIB",
        ""
    ]
    
    grand_totals = {'ndp': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0}
    
    for product_id, product_data in sorted(product_staff_data.items(), key=lambda x: x[1]['totals']['nominal'], reverse=True):
        report_lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        report_lines.append(f"🏷 <b>{product_data['product_name']}</b>")
        report_lines.append("")
        
        # Sort staff by nominal
        sorted_staff = sorted(product_data['staff'].items(), key=lambda x: x[1]['nominal'], reverse=True)
        
        for idx, (staff_id, staff_data) in enumerate(sorted_staff, 1):
            emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "👤"
            report_lines.append(
                f"{emoji} <b>{staff_data['staff_name']}</b>\n"
                f"   NDP: {staff_data['ndp']} | RDP: {staff_data['rdp']} | Form: {staff_data['total_form']}\n"
                f"   💰 {format_rupiah(staff_data['nominal'])}"
            )
        
        report_lines.append("")
        report_lines.append(
            f"📈 <b>Product Total:</b>\n"
            f"   NDP: {product_data['totals']['ndp']} | RDP: {product_data['totals']['rdp']} | Form: {product_data['totals']['total_form']}\n"
            f"   💰 {format_rupiah(product_data['totals']['nominal'])}"
        )
        report_lines.append("")
        
        # Add to grand totals
        for k in grand_totals:
            grand_totals[k] += product_data['totals'][k]
    
    # Grand totals
    report_lines.append("━━━━━━━━━━━━━━━━━━━━")
    report_lines.append(f"🏆 <b>GRAND TOTAL</b>")
    report_lines.append(
        f"   NDP: {grand_totals['ndp']} | RDP: {grand_totals['rdp']} | Form: {grand_totals['total_form']}\n"
        f"   💰 <b>{format_rupiah(grand_totals['nominal'])}</b>"
    )
    
    return "\n".join(report_lines)


async def generate_atrisk_alert(inactive_days: int = 14) -> str:
    """Generate at-risk customer alert for customers inactive for N+ days.
    Rotates customers so the same customer only appears again after 3 days."""
    db = get_db()
    
    jakarta_now = datetime.now(JAKARTA_TZ)
    cutoff_date = (jakarta_now - timedelta(days=inactive_days)).strftime('%Y-%m-%d')
    
    # Get customers that were alerted in the last 3 days (to exclude them)
    # Now using (customer_id, product_id) pairs for more accurate rotation
    three_days_ago = (jakarta_now - timedelta(days=3)).isoformat()
    recently_alerted = await db.atrisk_alert_history.find(
        {'alerted_at': {'$gte': three_days_ago}},
        {'_id': 0, 'customer_id': 1, 'product_id': 1}
    ).to_list(10000)
    recently_alerted_keys = set((r['customer_id'], r.get('product_id', '')) for r in recently_alerted)
    
    # Get all OMSET records
    all_records = await db.omset_records.find({}, {'_id': 0}).to_list(100000)
    
    if not all_records:
        return f"⚠️ <b>At-Risk Customer Alert</b>\n\n<i>No customer data found.</i>"
    
    # Get products for grouping
    products = await db.products.find({}, {'_id': 0}).to_list(100)
    product_map = {p['id']: p['name'] for p in products}
    
    # Get staff for grouping
    staff_list = await db.users.find({'role': 'staff'}, {'_id': 0}).to_list(100)
    staff_map = {s['id']: s['name'] for s in staff_list}
    
    # Track customer last deposit dates - use normalized IDs AND product_id
    # CRITICAL: Must track (customer_id, product_id) pairs, not just customer_id
    # because a customer can deposit to different products at different times
    customer_data = {}  # {(normalized_customer_id, product_id): {last_date, ...}}
    
    for record in all_records:
        # Use .lower() for consistent normalization (matches retention.py)
        cid_normalized = record.get('customer_id_normalized') or record.get('customer_id', '').strip().lower()
        product_id = record.get('product_id', '')
        record_date = record.get('record_date', '')
        
        # Key is (customer_id, product_id) to track each customer-product combination
        key = (cid_normalized, product_id)
        
        if key not in customer_data:
            customer_data[key] = {
                'last_date': record_date,
                'total_deposits': 1,
                'total_nominal': record.get('depo_total', 0) or record.get('nominal', 0) or 0,
                'product_id': product_id,
                'staff_id': record.get('staff_id', ''),
                'customer_name': record.get('customer_id', cid_normalized),
                'staff_name': record.get('staff_name', 'Unknown')
            }
        else:
            # Update if this record is more recent
            if record_date > customer_data[key]['last_date']:
                customer_data[key]['last_date'] = record_date
                customer_data[key]['staff_id'] = record.get('staff_id', '')
                customer_data[key]['staff_name'] = record.get('staff_name', 'Unknown')
            customer_data[key]['total_deposits'] += 1
            customer_data[key]['total_nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    # Find at-risk customers (last deposit before cutoff date AND has deposited at least twice)
    # EXCLUDE customers that were alerted in the last 3 days (per customer+product pair)
    at_risk_customers = []
    for (cid, product_id), data in customer_data.items():
        if data['last_date'] < cutoff_date and data['total_deposits'] >= 2:
            # Skip if this customer+product was alerted in the last 3 days
            if (cid, product_id) in recently_alerted_keys:
                continue
                
            days_since = (jakarta_now - datetime.strptime(data['last_date'], '%Y-%m-%d').replace(tzinfo=JAKARTA_TZ)).days
            at_risk_customers.append({
                'customer_id': cid,
                'customer_name': data['customer_name'],
                'last_date': data['last_date'],
                'days_since': days_since,
                'total_deposits': data['total_deposits'],
                'total_nominal': data['total_nominal'],
                'product_id': product_id,
                'product_name': product_map.get(product_id, product_id),
                'staff_id': data['staff_id'],
                'staff_name': data['staff_name']
            })
    
    # Sort by days since last deposit (most urgent first)
    at_risk_customers.sort(key=lambda x: x['days_since'], reverse=True)
    
    # Format the alert
    def format_rupiah(amount):
        return f"Rp {amount:,.0f}".replace(',', '.')
    
    # Count total at-risk (including those not shown today)
    total_at_risk_count = len(at_risk_customers) + len(recently_alerted_keys)
    
    alert_lines = [
        f"🚨 <b>AT-RISK CUSTOMER ALERT</b>",
        f"📅 <b>Date:</b> {jakarta_now.strftime('%Y-%m-%d')}",
        f"⚠️ <b>Threshold:</b> {inactive_days}+ days inactive",
        f"👥 <b>Today's At-Risk:</b> {len(at_risk_customers)} customers",
        f"📊 <b>Total Pool:</b> {total_at_risk_count} customers (rotating every 3 days)",
        ""
    ]
    
    if not at_risk_customers:
        if recently_alerted_keys:
            alert_lines.append("✅ <i>All at-risk customers were shown recently.</i>")
            alert_lines.append(f"<i>Next rotation in 1-3 days ({len(recently_alerted_keys)} customers in cooldown)</i>")
        else:
            alert_lines.append("✅ <i>No at-risk customers found! Great job!</i>")
        return "\n".join(alert_lines)
    
    # Group by staff for better actionability
    staff_groups = {}
    for customer in at_risk_customers:
        staff_id = customer['staff_id']
        if staff_id not in staff_groups:
            staff_groups[staff_id] = {
                'staff_name': customer['staff_name'],
                'customers': []
            }
        staff_groups[staff_id]['customers'].append(customer)
    
    # Limit to top 30 most urgent customers to avoid message being too long
    shown_count = 0
    max_show = 30
    customers_to_mark = []  # Track which customers we're showing today
    
    for staff_id, staff_data in sorted(staff_groups.items(), key=lambda x: len(x[1]['customers']), reverse=True):
        if shown_count >= max_show:
            break
            
        alert_lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        alert_lines.append(f"👤 <b>{staff_data['staff_name']}</b> ({len(staff_data['customers'])} at-risk)")
        alert_lines.append("")
        
        for customer in staff_data['customers'][:10]:  # Max 10 per staff
            if shown_count >= max_show:
                break
            
            urgency = "🔴" if customer['days_since'] >= 30 else "🟠" if customer['days_since'] >= 21 else "🟡"
            alert_lines.append(
                f"{urgency} <b>{customer['customer_name']}</b>\n"
                f"   📦 {customer['product_name']}\n"
                f"   ⏰ {customer['days_since']} days ago (Last: {customer['last_date']})\n"
                f"   💰 Total: {format_rupiah(customer['total_nominal'])} ({customer['total_deposits']} deposits)"
            )
            alert_lines.append("")
            shown_count += 1
            # Store both customer_id and product_id for accurate rotation
            customers_to_mark.append({'customer_id': customer['customer_id'], 'product_id': customer['product_id']})
        
        if len(staff_data['customers']) > 10:
            alert_lines.append(f"   <i>...and {len(staff_data['customers']) - 10} more</i>")
            alert_lines.append("")
    
    if len(at_risk_customers) > max_show:
        alert_lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        alert_lines.append(f"<i>Showing {max_show} of {len(at_risk_customers)} at-risk customers today</i>")
    
    alert_lines.append("")
    alert_lines.append("💡 <b>Action Required:</b> Follow up with these customers to re-engage!")
    alert_lines.append(f"🔄 <i>These customers will rotate out for 3 days</i>")
    
    # Store which customers were shown today (for 3-day rotation)
    # Now includes product_id for accurate per-product tracking
    if customers_to_mark:
        alert_history_records = [
            {
                'customer_id': item['customer_id'],
                'product_id': item['product_id'],
                'alerted_at': jakarta_now.isoformat()
            }
            for item in customers_to_mark
        ]
        await db.atrisk_alert_history.insert_many(alert_history_records)
        
        # Clean up old records (older than 7 days to save space)
        seven_days_ago = (jakarta_now - timedelta(days=7)).isoformat()
        await db.atrisk_alert_history.delete_many({'alerted_at': {'$lt': seven_days_ago}})
    
    return "\n".join(alert_lines)


async def send_atrisk_alert():
    """Task that runs daily to send at-risk customer alerts to group"""
    db = get_db()
    
    # Get config
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('atrisk_enabled'):
        print("At-risk alerts are disabled")
        return
    
    # Use atomic operation to prevent duplicate sends
    jakarta_now = datetime.now(JAKARTA_TZ)
    thirty_mins_ago = (jakarta_now - timedelta(minutes=30)).isoformat()
    
    result = await db.scheduled_report_config.update_one(
        {
            'id': 'scheduled_report_config',
            '$or': [
                {'atrisk_last_sent': {'$exists': False}},
                {'atrisk_last_sent': None},
                {'atrisk_last_sent': {'$lt': thirty_mins_ago}}
            ]
        },
        {'$set': {'atrisk_last_sent': jakarta_now.isoformat()}}
    )
    
    if result.modified_count == 0:
        print(f"At-risk alert already sent recently, skipping duplicate")
        return
    
    bot_token = config.get('telegram_bot_token')
    group_chat_id = config.get('atrisk_group_chat_id')
    inactive_days = config.get('atrisk_inactive_days', 14)
    
    if not bot_token or not group_chat_id:
        print("Telegram bot token or group chat ID not configured for at-risk alerts")
        return
    
    try:
        # Generate and send alert
        alert = await generate_atrisk_alert(inactive_days)
        success = await send_telegram_message(bot_token, group_chat_id, alert)
        
        if success:
            print(f"At-risk alert sent successfully at {jakarta_now}")
        else:
            print("Failed to send at-risk alert")
            # Reset last_sent so it can try again
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'atrisk_last_sent': config.get('atrisk_last_sent')}}
            )
            
    except Exception as e:
        print(f"Error sending at-risk alert: {e}")
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'atrisk_last_sent': config.get('atrisk_last_sent')}}
        )


async def generate_staff_offline_alert() -> str:
    """Generate alert for staff members who are not online"""
    db = get_db()
    
    jakarta_now = datetime.now(JAKARTA_TZ)
    
    # Consider staff offline if no activity in last 30 minutes
    OFFLINE_THRESHOLD_MINUTES = 30
    
    # Get all staff users
    staff_users = await db.users.find({'role': 'staff'}, {'_id': 0}).to_list(100)
    
    if not staff_users:
        return "📋 <b>Staff Status Check</b>\n\n<i>No staff users found in the system.</i>"
    
    online_staff = []
    offline_staff = []
    
    for staff in staff_users:
        last_activity_str = staff.get('last_activity')
        is_online = staff.get('is_online', False)
        status = 'offline'
        
        if last_activity_str and is_online:
            try:
                last_activity = datetime.fromisoformat(last_activity_str.replace('Z', '+00:00'))
                if last_activity.tzinfo is None:
                    last_activity = JAKARTA_TZ.localize(last_activity)
                
                minutes_since_activity = (jakarta_now - last_activity).total_seconds() / 60
                
                if minutes_since_activity < OFFLINE_THRESHOLD_MINUTES:
                    status = 'online'
            except:
                pass
        
        staff_info = {
            'name': staff.get('name', 'Unknown'),
            'email': staff.get('email', ''),
            'last_login': staff.get('last_login'),
            'last_activity': last_activity_str
        }
        
        if status == 'online':
            online_staff.append(staff_info)
        else:
            offline_staff.append(staff_info)
    
    # Format the alert
    alert_lines = [
        f"👥 <b>STAFF STATUS REPORT</b>",
        f"📅 <b>Date:</b> {jakarta_now.strftime('%Y-%m-%d')}",
        f"⏰ <b>Time:</b> {jakarta_now.strftime('%H:%M')} WIB",
        ""
    ]
    
    # Summary
    total_staff = len(staff_users)
    online_count = len(online_staff)
    offline_count = len(offline_staff)
    
    alert_lines.append(f"📊 <b>Summary:</b>")
    alert_lines.append(f"   Total Staff: {total_staff}")
    alert_lines.append(f"   🟢 Online: {online_count}")
    alert_lines.append(f"   🔴 Offline: {offline_count}")
    alert_lines.append("")
    
    # If all staff are online
    if offline_count == 0:
        alert_lines.append("✅ <b>All staff members are currently online!</b>")
        return "\n".join(alert_lines)
    
    # List offline staff
    alert_lines.append("━━━━━━━━━━━━━━━━━━━━")
    alert_lines.append(f"🔴 <b>OFFLINE STAFF ({offline_count})</b>")
    alert_lines.append("")
    
    for staff in offline_staff:
        last_login = staff.get('last_login')
        if last_login:
            try:
                login_dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                last_login_str = login_dt.strftime('%d %b %H:%M')
            except:
                last_login_str = 'Unknown'
        else:
            last_login_str = 'Never logged in'
        
        alert_lines.append(f"❌ <b>{staff['name']}</b>")
        alert_lines.append(f"   📧 {staff['email']}")
        alert_lines.append(f"   🕐 Last login: {last_login_str}")
        alert_lines.append("")
    
    # List online staff (brief)
    if online_count > 0:
        alert_lines.append("━━━━━━━━━━━━━━━━━━━━")
        alert_lines.append(f"🟢 <b>ONLINE STAFF ({online_count})</b>")
        online_names = [s['name'] for s in online_staff]
        alert_lines.append(f"   {', '.join(online_names)}")
    
    alert_lines.append("")
    alert_lines.append("💡 <i>Please check on offline staff members.</i>")
    
    return "\n".join(alert_lines)


async def send_staff_offline_alert():
    """Task that runs daily to check and alert about offline staff"""
    db = get_db()
    
    # Get config
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('staff_offline_enabled'):
        print("Staff offline alerts are disabled")
        return
    
    # Use atomic operation to prevent duplicate sends
    jakarta_now = datetime.now(JAKARTA_TZ)
    thirty_mins_ago = (jakarta_now - timedelta(minutes=30)).isoformat()
    
    result = await db.scheduled_report_config.update_one(
        {
            'id': 'scheduled_report_config',
            '$or': [
                {'staff_offline_last_sent': {'$exists': False}},
                {'staff_offline_last_sent': None},
                {'staff_offline_last_sent': {'$lt': thirty_mins_ago}}
            ]
        },
        {'$set': {'staff_offline_last_sent': jakarta_now.isoformat()}}
    )
    
    if result.modified_count == 0:
        print(f"Staff offline alert already sent recently, skipping duplicate")
        return
    
    bot_token = config.get('telegram_bot_token')
    # Send to admin's personal chat
    chat_id = config.get('telegram_chat_id')
    
    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID not configured for staff offline alerts")
        return
    
    try:
        # Generate and send alert
        alert = await generate_staff_offline_alert()
        success = await send_telegram_message(bot_token, chat_id, alert)
        
        if success:
            print(f"Staff offline alert sent successfully at {jakarta_now}")
        else:
            print("Failed to send staff offline alert")
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'staff_offline_last_sent': config.get('staff_offline_last_sent')}}
            )
            
    except Exception as e:
        print(f"Error sending staff offline alert: {e}")
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'staff_offline_last_sent': config.get('staff_offline_last_sent')}}
        )


async def process_reserved_member_cleanup():
    """
    Task that runs daily at 00:01 AM to:
    1. Send notifications to staff whose reserved members will expire soon
    2. Auto-delete reserved members that have been inactive for the configured grace period
    
    IMPORTANT: Grace period is counted from the customer's LAST DEPOSIT DATE (last_omset_date),
    NOT from when they were reserved. If a customer hasn't deposited in X days,
    they should be removed regardless of when they were reserved.
    
    Example:
    - Grace period = 21 days
    - Customer's last deposit was 25 days ago
    - Result: Customer should be DELETED (25 > 21)
    """
    db = get_db()
    jakarta_now = datetime.now(JAKARTA_TZ)
    
    print(f"[{jakarta_now}] Starting reserved member cleanup job...")
    
    # Get grace period configuration
    config = await db.reserved_member_config.find_one({'id': 'reserved_member_config'}, {'_id': 0})
    global_grace_days = 30  # Default
    warning_days = 7  # Default - notify X days before expiry
    product_overrides = {}
    
    if config:
        global_grace_days = config.get('global_grace_days', 30)
        warning_days = config.get('warning_days', 7)
        product_overrides = {p['product_id']: p['grace_days'] for p in config.get('product_overrides', [])}
    
    print(f"Config: global_grace_days={global_grace_days}, warning_days={warning_days}")
    
    # Get all approved reserved members
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0}
    ).to_list(10000)
    
    if not reserved_members:
        print("No approved reserved members to process")
        return {'warnings_sent': 0, 'members_removed': 0}
    
    print(f"Processing {len(reserved_members)} approved reserved members...")
    
    # Track stats
    notifications_sent = 0
    members_deleted = 0
    
    for member in reserved_members:
        member_id = member.get('id')
        # Skip permanent reservations - they never expire
        if member.get('is_permanent', False):
            print(f"  {member.get('customer_id') or member.get('customer_name', '')}: PERMANENT - skipping")
            continue
        # Support both old field name (customer_name) and new field name (customer_id)
        customer_id = member.get('customer_id') or member.get('customer_name') or ''
        staff_id = member.get('staff_id')
        staff_name = member.get('staff_name', 'Unknown')
        product_id = member.get('product_id', '')
        product_name = member.get('product_name', 'Unknown')
        
        # Get grace period for this member (product-specific or global)
        grace_days = product_overrides.get(product_id, global_grace_days)
        
        # Get the customer's LAST DEPOSIT DATE from reserved member record
        # This is stored as 'last_omset_date' field
        last_omset_date_str = member.get('last_omset_date')
        has_deposit = False
        
        if last_omset_date_str:
            # Use the stored last_omset_date
            has_deposit = True
            try:
                if isinstance(last_omset_date_str, str):
                    last_deposit_date = datetime.fromisoformat(last_omset_date_str.replace('Z', '+00:00'))
                else:
                    last_deposit_date = last_omset_date_str
                if last_deposit_date.tzinfo is None:
                    last_deposit_date = JAKARTA_TZ.localize(last_deposit_date)
            except Exception as e:
                print(f"Error parsing last_omset_date for {customer_id}: {e}")
                has_deposit = False
        
        if not has_deposit:
            # No last_omset_date stored - try to get from omset_records
            # IMPORTANT: Use 'record_date' field (the actual deposit date), NOT 'created_at'
            last_omset = await db.omset_records.find_one(
                {
                    'customer_id': {'$regex': f'^{customer_id}$', '$options': 'i'},
                    'staff_id': staff_id
                },
                {'_id': 0, 'record_date': 1},
                sort=[('record_date', -1)]  # Get the most recent by actual deposit date
            )
            
            if last_omset and last_omset.get('record_date'):
                has_deposit = True
                try:
                    record_date_str = last_omset['record_date']
                    # record_date is stored as 'YYYY-MM-DD' string
                    if isinstance(record_date_str, str):
                        # Parse as date and convert to datetime at start of day
                        last_deposit_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                        last_deposit_date = JAKARTA_TZ.localize(last_deposit_date)
                    else:
                        last_deposit_date = record_date_str
                        if last_deposit_date.tzinfo is None:
                            last_deposit_date = JAKARTA_TZ.localize(last_deposit_date)
                except Exception as e:
                    print(f"Error parsing record_date for {customer_id}: {e}")
                    has_deposit = False
        
        # If NO DEPOSIT at all - DELETE immediately
        if not has_deposit:
            print(f"  {customer_id}: NO DEPOSIT - deleting immediately")
            
            # Archive to deleted_reserved_members collection
            member_data = await db.reserved_members.find_one({'id': member_id}, {'_id': 0})
            
            if member_data:
                archived_member = {
                    **member_data,
                    'deleted_at': jakarta_now.isoformat(),
                    'deleted_reason': 'no_deposit',
                    'grace_days_used': grace_days,
                    'days_since_last_deposit': None,
                    'last_deposit_date': None
                }
                await db.deleted_reserved_members.insert_one(archived_member)
            
            # Delete from active reserved members
            await db.reserved_members.delete_one({'id': member_id})
            members_deleted += 1
            
            # SYNC: Delete related bonus_check_submissions for this customer+staff
            await db.bonus_check_submissions.delete_many({
                'customer_id_normalized': customer_id.strip().upper(),
                'staff_id': staff_id
            })
            
            # SYNC: Restore records that were invalidated by this reservation
            await restore_invalidated_records_for_reservation(db, customer_id, staff_id, product_id)
            
            print(f"  -> DELETED: {customer_id} (no deposit)")
            continue
        
        # Calculate days since LAST DEPOSIT (the key logic!)
        # Compare dates only (ignore time portion) to get accurate day count
        today_date = jakarta_now.date()
        last_deposit_date_only = last_deposit_date.date()
        days_since_last_deposit = (today_date - last_deposit_date_only).days
        days_remaining = grace_days - days_since_last_deposit
        
        print(f"  {customer_id}: last_deposit={last_deposit_date_only}, days_since={days_since_last_deposit}, grace={grace_days}, remaining={days_remaining}")
        
        # Check if grace period has passed
        if days_remaining <= 0:
            # Grace period passed - DELETE this member
            # First, archive to deleted_reserved_members collection
            member_data = await db.reserved_members.find_one({'id': member_id}, {'_id': 0})
            
            if member_data:
                archived_member = {
                    **member_data,
                    'deleted_at': jakarta_now.isoformat(),
                    'deleted_reason': 'no_omset_grace_period',
                    'grace_days_used': grace_days,
                    'days_since_last_deposit': days_since_last_deposit,
                    'last_deposit_date': last_deposit_date.isoformat()
                }
                await db.deleted_reserved_members.insert_one(archived_member)
            
            # Delete from active reserved members
            await db.reserved_members.delete_one({'id': member_id})
            members_deleted += 1
            
            # SYNC: Delete related bonus_check_submissions for this customer+staff
            # When a reserved member expires, their bonus check submissions should also be removed
            await db.bonus_check_submissions.delete_many({
                'customer_id_normalized': customer_id.strip().upper(),
                'staff_id': staff_id
            })
            
            # Send notification to staff
            await create_notification(
                user_id=staff_id,
                type='reserved_member_expired',
                title='Reserved Member Removed',
                message=f'Your reservation for "{customer_id}" ({product_name}) has been removed. Last deposit was {days_since_last_deposit} days ago (grace period: {grace_days} days).',
                data={
                    'customer_id': customer_id,
                    'product_name': product_name,
                    'grace_days': grace_days,
                    'days_since_last_deposit': days_since_last_deposit,
                    'reason': 'no_omset_grace_period'
                }
            )
            print(f"  -> DELETED: {customer_id} (last deposit {days_since_last_deposit} days ago, grace: {grace_days})")
            
        elif days_remaining <= warning_days:
            # Within warning period - send notification
            today_str = jakarta_now.strftime('%Y-%m-%d')
            existing_notification = await db.notifications.find_one({
                'user_id': staff_id,
                'type': 'reserved_member_expiring',
                'data.member_id': member_id,
                'created_at': {'$regex': f'^{today_str}'}
            })
            
            if not existing_notification:
                await create_notification(
                    user_id=staff_id,
                    type='reserved_member_expiring',
                    title='Reserved Member Expiring Soon',
                    message=f'Your reservation for "{customer_id}" ({product_name}) will expire in {days_remaining} day(s). Last deposit was {days_since_last_deposit} days ago.',
                    data={
                        'member_id': member_id,
                        'customer_id': customer_id,
                        'product_name': product_name,
                        'days_remaining': days_remaining,
                        'days_since_last_deposit': days_since_last_deposit,
                        'grace_days': grace_days
                    }
                )
                notifications_sent += 1
                print(f"  -> WARNING: {customer_id} ({days_remaining} days left)")
    
    print(f"Reserved member cleanup completed: {notifications_sent} warnings sent, {members_deleted} members removed")
    return {'warnings_sent': notifications_sent, 'members_removed': members_deleted}


async def send_reserved_member_cleanup():
    """Wrapper for the reserved member cleanup job"""
    try:
        await process_reserved_member_cleanup()
    except Exception as e:
        print(f"Error in reserved member cleanup: {e}")


async def cleanup_omset_trash():
    """
    Automatically clean up OMSET trash records older than 30 days.
    This prevents the trash collection from growing indefinitely.
    Runs daily at 00:05 AM Jakarta time.
    """
    db = get_db()
    
    try:
        # Calculate cutoff date (30 days ago)
        cutoff_date = datetime.now(JAKARTA_TZ) - timedelta(days=30)
        cutoff_iso = cutoff_date.isoformat()
        
        # Find and delete old records
        result = await db.omset_trash.delete_many({
            'deleted_at': {'$lt': cutoff_iso}
        })
        
        deleted_count = result.deleted_count
        
        if deleted_count > 0:
            print(f"OMSET trash cleanup: Permanently deleted {deleted_count} records older than 30 days")
            
            # Log the cleanup action
            await db.system_logs.insert_one({
                'type': 'omset_trash_cleanup',
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_iso,
                'executed_at': datetime.now(JAKARTA_TZ).isoformat()
            })
        else:
            print("OMSET trash cleanup: No records older than 30 days to delete")
            
    except Exception as e:
        print(f"Error in OMSET trash cleanup: {e}")


async def send_scheduled_report():
    """Task that runs daily to send the report"""
    db = get_db()
    
    # Get config
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('enabled'):
        print("Scheduled report is disabled")
        return
    
    # Use atomic operation to prevent duplicate sends
    # Try to acquire a "lock" by setting last_sent only if it's been more than 30 mins
    jakarta_now = datetime.now(JAKARTA_TZ)
    thirty_mins_ago = (jakarta_now - timedelta(minutes=30)).isoformat()
    
    # Attempt to atomically update last_sent only if current last_sent is old enough
    result = await db.scheduled_report_config.update_one(
        {
            'id': 'scheduled_report_config',
            '$or': [
                {'last_sent': {'$exists': False}},
                {'last_sent': None},
                {'last_sent': {'$lt': thirty_mins_ago}}
            ]
        },
        {'$set': {'last_sent': jakarta_now.isoformat(), 'sending_in_progress': True}}
    )
    
    # If no document was modified, another process already sent/is sending the report
    if result.modified_count == 0:
        print(f"Daily report already sent recently or send in progress, skipping duplicate")
        return
    
    bot_token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    
    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID not configured")
        # Reset the lock since we didn't actually send
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$unset': {'sending_in_progress': ''}}
        )
        return
    
    try:
        # Generate and send report
        report = await generate_daily_report()
        success = await send_telegram_message(bot_token, chat_id, report)
        
        if success:
            # Clear the in_progress flag
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$unset': {'sending_in_progress': ''}}
            )
            print(f"Daily report sent successfully at {jakarta_now}")
        else:
            print("Failed to send daily report")
            # Reset so it can try again
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'last_sent': config.get('last_sent')}, '$unset': {'sending_in_progress': ''}}
            )
            
    except Exception as e:
        print(f"Error sending scheduled report: {e}")
        # Reset so it can try again
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'last_sent': config.get('last_sent')}, '$unset': {'sending_in_progress': ''}}
        )


def start_scheduler(report_hour: int = 1, report_minute: int = 0, 
                    atrisk_hour: int = None, atrisk_minute: int = None, 
                    atrisk_enabled: bool = False,
                    staff_offline_hour: int = None, staff_offline_minute: int = None,
                    staff_offline_enabled: bool = False,
                    report_enabled: bool = True):
    """Start the APScheduler with the configured schedules
    
    CRITICAL JOBS (always run):
    - Reserved member cleanup (00:01 daily)
    - OMSET trash cleanup (00:05 daily)
    
    OPTIONAL JOBS (based on settings):
    - Daily report (if report_enabled)
    - At-risk alerts (if atrisk_enabled)
    - Staff offline alerts (if staff_offline_enabled)
    """
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    
    scheduler = AsyncIOScheduler(timezone=JAKARTA_TZ)
    
    # Schedule daily report only if enabled
    if report_enabled:
        scheduler.add_job(
            send_scheduled_report,
            CronTrigger(hour=report_hour, minute=report_minute, timezone=JAKARTA_TZ),
            id='daily_report',
            replace_existing=True
        )
        print(f"Daily report scheduled at {report_hour:02d}:{report_minute:02d} WIB")
    else:
        print("Daily report scheduling skipped (disabled)")
    
    # Schedule at-risk alerts if enabled
    if atrisk_enabled and atrisk_hour is not None:
        scheduler.add_job(
            send_atrisk_alert,
            CronTrigger(hour=atrisk_hour, minute=atrisk_minute or 0, timezone=JAKARTA_TZ),
            id='atrisk_alert',
            replace_existing=True
        )
        print(f"At-risk alerts scheduled at {atrisk_hour:02d}:{atrisk_minute or 0:02d} WIB")
    
    # Schedule staff offline alerts if enabled
    if staff_offline_enabled and staff_offline_hour is not None:
        scheduler.add_job(
            send_staff_offline_alert,
            CronTrigger(hour=staff_offline_hour, minute=staff_offline_minute or 0, timezone=JAKARTA_TZ),
            id='staff_offline_alert',
            replace_existing=True
        )
        print(f"Staff offline alerts scheduled at {staff_offline_hour:02d}:{staff_offline_minute or 0:02d} WIB")
    
    # Schedule reserved member cleanup at 00:01 AM daily (always enabled)
    scheduler.add_job(
        send_reserved_member_cleanup,
        CronTrigger(hour=0, minute=1, timezone=JAKARTA_TZ),
        id='reserved_member_cleanup',
        replace_existing=True
    )
    print("Reserved member cleanup scheduled at 00:01 WIB daily")
    
    # Schedule OMSET trash cleanup at 00:05 AM daily (always enabled)
    # Removes records older than 30 days from the trash
    scheduler.add_job(
        cleanup_omset_trash,
        CronTrigger(hour=0, minute=5, timezone=JAKARTA_TZ),
        id='omset_trash_cleanup',
        replace_existing=True
    )
    print("OMSET trash cleanup scheduled at 00:05 WIB daily (30-day retention)")
    
    scheduler.start()
    print("Scheduler started successfully")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        print("Scheduler stopped")


# API Endpoints

@router.get("/scheduled-reports/config")
async def get_config(user: User = Depends(get_admin_user)):
    """Get current scheduled report configuration"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config:
        return {
            'id': 'scheduled_report_config',
            'telegram_bot_token': None,
            'telegram_chat_id': None,
            'enabled': False,
            'report_hour': 1,
            'report_minute': 0,
            'last_sent': None,
            'atrisk_enabled': False,
            'atrisk_group_chat_id': None,
            'atrisk_hour': 11,
            'atrisk_minute': 0,
            'atrisk_inactive_days': 14,
            'atrisk_last_sent': None,
            'staff_offline_enabled': False,
            'staff_offline_hour': 11,
            'staff_offline_minute': 0,
            'staff_offline_last_sent': None
        }
    
    # Mask the bot token for security
    if config.get('telegram_bot_token'):
        token = config['telegram_bot_token']
        config['telegram_bot_token_masked'] = f"{token[:10]}...{token[-5:]}" if len(token) > 15 else "***"
    
    return config


@router.post("/scheduled-reports/config")
async def update_config(config: TelegramConfig, user: User = Depends(get_admin_user)):
    """Update scheduled report configuration"""
    db = get_db()
    
    now = datetime.now(JAKARTA_TZ)
    
    # Get existing config to preserve at-risk and staff offline settings
    existing = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'})
    
    update_data = {
        'id': 'scheduled_report_config',
        'telegram_bot_token': config.bot_token,
        'telegram_chat_id': config.chat_id,
        'enabled': config.enabled,
        'report_hour': config.report_hour,
        'report_minute': config.report_minute,
        'updated_at': now.isoformat()
    }
    
    if existing:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': update_data}
        )
        # Get updated config for scheduler
        updated_config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    else:
        update_data['created_at'] = now.isoformat()
        await db.scheduled_report_config.insert_one(update_data)
        updated_config = update_data
    
    # ALWAYS restart scheduler - critical cleanup jobs must run
    start_scheduler(
        report_hour=config.report_hour,
        report_minute=config.report_minute,
        report_enabled=config.enabled,
        atrisk_hour=updated_config.get('atrisk_hour', 11),
        atrisk_minute=updated_config.get('atrisk_minute', 0),
        atrisk_enabled=updated_config.get('atrisk_enabled', False),
        staff_offline_hour=updated_config.get('staff_offline_hour', 11),
        staff_offline_minute=updated_config.get('staff_offline_minute', 0),
        staff_offline_enabled=updated_config.get('staff_offline_enabled', False)
    )
    
    return {'success': True, 'message': 'Configuration updated successfully'}


@router.post("/scheduled-reports/atrisk-config")
async def update_atrisk_config(config: AtRiskAlertConfig, user: User = Depends(get_admin_user)):
    """Update at-risk alert configuration"""
    db = get_db()
    
    now = datetime.now(JAKARTA_TZ)
    
    # Get existing config
    existing = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'})
    
    update_data = {
        'telegram_bot_token': config.bot_token,
        'atrisk_enabled': config.enabled,
        'atrisk_group_chat_id': config.group_chat_id,
        'atrisk_hour': config.alert_hour,
        'atrisk_minute': config.alert_minute,
        'atrisk_inactive_days': config.inactive_days_threshold,
        'updated_at': now.isoformat()
    }
    
    if existing:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': update_data}
        )
        updated_config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    else:
        update_data['id'] = 'scheduled_report_config'
        update_data['created_at'] = now.isoformat()
        await db.scheduled_report_config.insert_one(update_data)
        updated_config = update_data
    
    # ALWAYS restart scheduler - critical cleanup jobs must run
    start_scheduler(
        report_hour=updated_config.get('report_hour', 1),
        report_minute=updated_config.get('report_minute', 0),
        report_enabled=updated_config.get('enabled', False),
        atrisk_hour=config.alert_hour,
        atrisk_minute=config.alert_minute,
        atrisk_enabled=config.enabled,
        staff_offline_hour=updated_config.get('staff_offline_hour', 11),
        staff_offline_minute=updated_config.get('staff_offline_minute', 0),
        staff_offline_enabled=updated_config.get('staff_offline_enabled', False)
    )
    
    return {'success': True, 'message': 'At-risk alert configuration updated successfully'}


@router.post("/scheduled-reports/staff-offline-config")
async def update_staff_offline_config(config: StaffOfflineAlertConfig, user: User = Depends(get_admin_user)):
    """Update staff offline alert configuration"""
    db = get_db()
    
    now = datetime.now(JAKARTA_TZ)
    
    # Get existing config
    existing = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'})
    
    update_data = {
        'staff_offline_enabled': config.enabled,
        'staff_offline_hour': config.alert_hour,
        'staff_offline_minute': config.alert_minute,
        'updated_at': now.isoformat()
    }
    
    if existing:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': update_data}
        )
        updated_config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    else:
        update_data['id'] = 'scheduled_report_config'
        update_data['created_at'] = now.isoformat()
        await db.scheduled_report_config.insert_one(update_data)
        updated_config = update_data
    
    # ALWAYS restart scheduler - critical cleanup jobs must run
    start_scheduler(
        report_hour=updated_config.get('report_hour', 1),
        report_minute=updated_config.get('report_minute', 0),
        report_enabled=updated_config.get('enabled', False),
        atrisk_hour=updated_config.get('atrisk_hour', 11),
        atrisk_minute=updated_config.get('atrisk_minute', 0),
        atrisk_enabled=updated_config.get('atrisk_enabled', False),
        staff_offline_hour=config.alert_hour,
        staff_offline_minute=config.alert_minute,
        staff_offline_enabled=config.enabled
    )
    
    return {'success': True, 'message': 'Staff offline alert configuration updated successfully'}


@router.post("/scheduled-reports/staff-offline-send-now")
async def send_staff_offline_now(user: User = Depends(get_admin_user)):
    """Manually trigger the staff offline alert"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('telegram_bot_token') or not config.get('telegram_chat_id'):
        raise HTTPException(status_code=400, detail="Telegram configuration not set")
    
    alert = await generate_staff_offline_alert()
    
    success = await send_telegram_message(
        config['telegram_bot_token'],
        config['telegram_chat_id'],
        alert
    )
    
    if success:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'staff_offline_last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
        )
        return {'success': True, 'message': 'Staff offline alert sent successfully'}
    else:
        raise HTTPException(status_code=500, detail="Failed to send staff offline alert")


@router.post("/scheduled-reports/test")
async def test_telegram(user: User = Depends(get_admin_user)):
    """Send a test message to verify Telegram configuration"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('telegram_bot_token') or not config.get('telegram_chat_id'):
        raise HTTPException(status_code=400, detail="Telegram configuration not set")
    
    test_message = (
        "✅ <b>CRM Telegram Integration Test</b>\n\n"
        f"Your scheduled report is configured to run daily at "
        f"<b>{config.get('report_hour', 1):02d}:{config.get('report_minute', 0):02d} WIB</b>\n\n"
        f"Status: {'🟢 Enabled' if config.get('enabled') else '🔴 Disabled'}\n\n"
        f"<i>Test sent at {datetime.now(JAKARTA_TZ).strftime('%Y-%m-%d %H:%M:%S')} WIB</i>"
    )
    
    success = await send_telegram_message(
        config['telegram_bot_token'],
        config['telegram_chat_id'],
        test_message
    )
    
    if success:
        return {'success': True, 'message': 'Test message sent successfully'}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message. Please check your bot token and chat ID.")


@router.post("/scheduled-reports/send-now")
async def send_report_now(user: User = Depends(get_admin_user)):
    """Manually trigger the daily report"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('telegram_bot_token') or not config.get('telegram_chat_id'):
        raise HTTPException(status_code=400, detail="Telegram configuration not set")
    
    report = await generate_daily_report()
    
    success = await send_telegram_message(
        config['telegram_bot_token'],
        config['telegram_chat_id'],
        report
    )
    
    if success:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
        )
        return {'success': True, 'message': 'Report sent successfully'}
    else:
        raise HTTPException(status_code=500, detail="Failed to send report")


@router.get("/scheduled-reports/preview")
async def preview_report(user: User = Depends(get_admin_user)):
    """Preview the daily report without sending"""
    report = await generate_daily_report()
    return {'report': report}


@router.post("/scheduled-reports/atrisk-test")
async def test_atrisk_telegram(user: User = Depends(get_admin_user)):
    """Send a test message to verify at-risk Telegram group configuration"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('telegram_bot_token') or not config.get('atrisk_group_chat_id'):
        raise HTTPException(status_code=400, detail="At-risk Telegram group configuration not set")
    
    test_message = (
        "✅ <b>CRM At-Risk Alert Integration Test</b>\n\n"
        f"At-risk alerts are configured to run daily at "
        f"<b>{config.get('atrisk_hour', 11):02d}:{config.get('atrisk_minute', 0):02d} WIB</b>\n\n"
        f"Threshold: <b>{config.get('atrisk_inactive_days', 14)}+ days</b> inactive\n\n"
        f"Status: {'🟢 Enabled' if config.get('atrisk_enabled') else '🔴 Disabled'}\n\n"
        f"<i>Test sent at {datetime.now(JAKARTA_TZ).strftime('%Y-%m-%d %H:%M:%S')} WIB</i>"
    )
    
    success = await send_telegram_message(
        config['telegram_bot_token'],
        config['atrisk_group_chat_id'],
        test_message
    )
    
    if success:
        return {'success': True, 'message': 'Test message sent to group successfully'}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message. Please check your bot token and group chat ID.")


@router.post("/scheduled-reports/atrisk-send-now")
async def send_atrisk_now(user: User = Depends(get_admin_user)):
    """Manually trigger the at-risk customer alert"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('telegram_bot_token') or not config.get('atrisk_group_chat_id'):
        raise HTTPException(status_code=400, detail="At-risk Telegram group configuration not set")
    
    inactive_days = config.get('atrisk_inactive_days', 14)
    alert = await generate_atrisk_alert(inactive_days)
    
    success = await send_telegram_message(
        config['telegram_bot_token'],
        config['atrisk_group_chat_id'],
        alert
    )
    
    if success:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': {'atrisk_last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
        )
        return {'success': True, 'message': 'At-risk alert sent successfully'}
    else:
        raise HTTPException(status_code=500, detail="Failed to send at-risk alert")


@router.get("/scheduled-reports/atrisk-preview")
async def preview_atrisk(user: User = Depends(get_admin_user)):
    """Preview the at-risk alert without sending"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    inactive_days = config.get('atrisk_inactive_days', 14) if config else 14
    alert = await generate_atrisk_alert(inactive_days)
    return {'alert': alert}


@router.get("/scheduled-reports/atrisk-rotation-status")
async def get_atrisk_rotation_status(user: User = Depends(get_admin_user)):
    """Get the status of at-risk customer rotation (how many in cooldown)"""
    db = get_db()
    
    jakarta_now = datetime.now(JAKARTA_TZ)
    three_days_ago = (jakarta_now - timedelta(days=3)).isoformat()
    
    # Count customers in cooldown (alerted in last 3 days)
    cooldown_count = await db.atrisk_alert_history.count_documents(
        {'alerted_at': {'$gte': three_days_ago}}
    )
    
    # Get total history count
    total_history = await db.atrisk_alert_history.count_documents({})
    
    return {
        'customers_in_cooldown': cooldown_count,
        'total_history_records': total_history,
        'cooldown_period_days': 3,
        'message': f'{cooldown_count} customers are in 3-day cooldown and will not appear in today\'s alert'
    }


@router.delete("/scheduled-reports/atrisk-rotation-reset")
async def reset_atrisk_rotation(user: User = Depends(get_admin_user)):
    """Reset the at-risk alert rotation history (all customers can appear again)"""
    db = get_db()
    
    result = await db.atrisk_alert_history.delete_many({})
    
    return {
        'deleted_count': result.deleted_count,
        'message': f'Cleared {result.deleted_count} alert history records. All at-risk customers can now appear in the next alert.'
    }


@router.get("/scheduled-reports/reserved-member-cleanup-preview")
async def preview_reserved_member_cleanup(user: User = Depends(get_admin_user)):
    """Preview which reserved members will receive warnings or be deleted"""
    db = get_db()
    jakarta_now = datetime.now(JAKARTA_TZ)
    
    # Get grace period configuration
    config = await db.reserved_member_config.find_one({'id': 'reserved_member_config'}, {'_id': 0})
    global_grace_days = 30
    warning_days = 7
    product_overrides = {}
    
    if config:
        global_grace_days = config.get('global_grace_days', 30)
        warning_days = config.get('warning_days', 7)
        product_overrides = {p['product_id']: p['grace_days'] for p in config.get('product_overrides', [])}
    
    # Get all approved reserved members
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0}
    ).to_list(10000)
    
    expiring_soon = []  # Within warning period
    will_be_deleted = []  # 0 days or less remaining OR no deposit
    active_members = []  # Has OMSET
    safe_members = []  # No OMSET but still within grace period (outside warning)
    no_deposit_members = []  # Members with no deposit record (will be deleted)
    permanent_members = []  # Permanent reservations (never expire)
    
    for member in reserved_members:
        member_id = member.get('id')
        # Skip permanent reservations
        if member.get('is_permanent', False):
            permanent_members.append({
                'id': member_id,
                'customer_id': member.get('customer_id') or member.get('customer_name') or '',
                'staff_name': member.get('staff_name', 'Unknown'),
                'product_name': member.get('product_name', 'Unknown'),
                'status': 'permanent'
            })
            continue
        # Support both old field name (customer_name) and new field name (customer_id)
        customer_id = member.get('customer_id') or member.get('customer_name') or ''
        staff_id = member.get('staff_id')
        staff_name = member.get('staff_name', 'Unknown')
        product_id = member.get('product_id', '')
        product_name = member.get('product_name', 'Unknown')
        
        # Get grace period for this member
        grace_days = product_overrides.get(product_id, global_grace_days)
        
        # First check if there's a stored last_omset_date
        last_omset_date_str = member.get('last_omset_date')
        has_deposit = False
        
        if last_omset_date_str:
            has_deposit = True
            try:
                if isinstance(last_omset_date_str, str):
                    last_deposit_date = datetime.fromisoformat(last_omset_date_str.replace('Z', '+00:00'))
                else:
                    last_deposit_date = last_omset_date_str
                if last_deposit_date.tzinfo is None:
                    last_deposit_date = JAKARTA_TZ.localize(last_deposit_date)
            except Exception:
                has_deposit = False
        
        if not has_deposit:
            # Get the customer's LAST DEPOSIT DATE from omset_records
            last_omset = await db.omset_records.find_one(
                {
                    'customer_id': {'$regex': f'^{customer_id}$', '$options': 'i'},
                    'staff_id': staff_id
                },
                {'_id': 0, 'record_date': 1},
                sort=[('record_date', -1)]
            )
            
            if last_omset and last_omset.get('record_date'):
                has_deposit = True
                try:
                    record_date_str = last_omset['record_date']
                    last_deposit_date = datetime.strptime(record_date_str, '%Y-%m-%d')
                    last_deposit_date = JAKARTA_TZ.localize(last_deposit_date)
                except Exception:
                    has_deposit = False
        
        # If NO DEPOSIT - mark for immediate deletion
        if not has_deposit:
            member_info = {
                'id': member_id,
                'customer_id': customer_id,
                'staff_name': staff_name,
                'product_id': product_id,
                'product_name': product_name,
                'last_deposit_date': None,
                'days_since_last_deposit': None,
                'days_remaining': None,
                'grace_days': grace_days,
                'reason': 'no_deposit'
            }
            will_be_deleted.append(member_info)
            continue
        
        # Compare dates only (ignore time portion) to get accurate day count
        today_date = jakarta_now.date()
        last_deposit_date_only = last_deposit_date.date()
        days_since_last_deposit = (today_date - last_deposit_date_only).days
        days_remaining = grace_days - days_since_last_deposit
        
        member_info = {
            'id': member_id,
            'customer_id': customer_id,
            'staff_name': staff_name,
            'product_id': product_id,
            'product_name': product_name,
            'last_deposit_date': last_deposit_date_only.strftime('%Y-%m-%d'),
            'days_since_last_deposit': days_since_last_deposit,
            'days_remaining': days_remaining,
            'grace_days': grace_days
        }
        
        # Categorize based on days_remaining (from last deposit, not reservation)
        if days_remaining <= 0:
            will_be_deleted.append(member_info)
        elif days_remaining <= warning_days:
            expiring_soon.append(member_info)
        else:
            safe_members.append(member_info)
    
    return {
        'config': {
            'global_grace_days': global_grace_days,
            'warning_days': warning_days,
            'product_overrides_count': len(product_overrides)
        },
        'total_approved_members': len(reserved_members),
        'permanent_members_count': len(permanent_members),
        'active_members_with_omset': len(active_members),
        'safe_members_count': len(safe_members),
        'expiring_soon_count': len(expiring_soon),
        'will_be_deleted_count': len(will_be_deleted),
        'expiring_soon': expiring_soon,
        'will_be_deleted': will_be_deleted,
        'permanent_members': permanent_members,
        'message': f'{len(expiring_soon)} members will receive warning notifications, {len(will_be_deleted)} will be auto-deleted at next cleanup (00:01 WIB), {len(permanent_members)} permanent (never expire)'
    }


@router.post("/scheduled-reports/reserved-member-cleanup-run")
async def run_reserved_member_cleanup(user: User = Depends(get_admin_user)):
    """Manually trigger the reserved member cleanup job"""
    try:
        result = await process_reserved_member_cleanup()
        return {
            'success': True, 
            'message': 'Reserved member cleanup completed successfully',
            'warnings_sent': result.get('warnings_sent', 0) if result else 0,
            'members_removed': result.get('members_removed', 0) if result else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


# ==================== RESERVED MEMBER GRACE PERIOD CONFIG ====================

class ProductGracePeriod(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_id: str
    product_name: str
    grace_days: int

class ReservedMemberConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    global_grace_days: int = 30
    warning_days: int = 7
    product_overrides: List[ProductGracePeriod] = []


@router.get("/reserved-members/cleanup-config")
async def get_reserved_member_config(user: User = Depends(get_admin_user)):
    """Get reserved member cleanup configuration (grace periods)"""
    db = get_db()
    
    config = await db.reserved_member_config.find_one({'id': 'reserved_member_config'}, {'_id': 0})
    
    # Get all products for reference
    products = await db.products.find({}, {'_id': 0, 'id': 1, 'name': 1}).to_list(100)
    
    if not config:
        config = {
            'id': 'reserved_member_config',
            'global_grace_days': 30,
            'warning_days': 7,
            'product_overrides': []
        }
    
    return {
        **config,
        'available_products': products
    }


@router.put("/reserved-members/cleanup-config")
async def update_reserved_member_config(config_update: ReservedMemberConfigUpdate, user: User = Depends(get_admin_user)):
    """Update reserved member cleanup configuration (grace periods)"""
    db = get_db()
    
    # Validate grace_days values
    if config_update.global_grace_days < 1:
        raise HTTPException(status_code=400, detail="Global grace days must be at least 1")
    if config_update.warning_days < 1:
        raise HTTPException(status_code=400, detail="Warning days must be at least 1")
    if config_update.warning_days >= config_update.global_grace_days:
        raise HTTPException(status_code=400, detail="Warning days must be less than global grace days")
    
    # Validate product overrides
    for override in config_update.product_overrides:
        if override.grace_days < 1:
            raise HTTPException(status_code=400, detail=f"Grace days for {override.product_name} must be at least 1")
        # Verify product exists
        product = await db.products.find_one({'id': override.product_id})
        if not product:
            raise HTTPException(status_code=400, detail=f"Product {override.product_id} not found")
    
    now = datetime.now(JAKARTA_TZ)
    
    update_data = {
        'id': 'reserved_member_config',
        'global_grace_days': config_update.global_grace_days,
        'warning_days': config_update.warning_days,
        'product_overrides': [p.model_dump() for p in config_update.product_overrides],
        'updated_at': now.isoformat(),
        'updated_by': user.id,
        'updated_by_name': user.name
    }
    
    await db.reserved_member_config.update_one(
        {'id': 'reserved_member_config'},
        {'$set': update_data, '$setOnInsert': {'created_at': now.isoformat()}},
        upsert=True
    )
    
    return {
        'success': True,
        'message': 'Configuration updated successfully',
        'config': update_data
    }


# ==================== OMSET TRASH CLEANUP ENDPOINTS ====================

@router.get("/scheduled-reports/omset-trash-status")
async def get_omset_trash_status(user: User = Depends(get_admin_user)):
    """Get OMSET trash cleanup status and statistics"""
    db = get_db()
    
    # Get total count in trash
    total_in_trash = await db.omset_trash.count_documents({})
    
    # Calculate how many are older than 30 days (would be deleted in next cleanup)
    cutoff_date = datetime.now(JAKARTA_TZ) - timedelta(days=30)
    cutoff_iso = cutoff_date.isoformat()
    
    expiring_count = await db.omset_trash.count_documents({
        'deleted_at': {'$lt': cutoff_iso}
    })
    
    # Get last cleanup log
    last_cleanup = await db.system_logs.find_one(
        {'type': 'omset_trash_cleanup'},
        {'_id': 0},
        sort=[('executed_at', -1)]
    )
    
    return {
        'total_in_trash': total_in_trash,
        'expiring_soon': expiring_count,
        'retention_days': 30,
        'next_cleanup': '00:05 WIB daily',
        'last_cleanup': last_cleanup
    }


@router.post("/scheduled-reports/omset-trash-cleanup")
async def manual_omset_trash_cleanup(user: User = Depends(get_admin_user)):
    """Manually trigger OMSET trash cleanup (removes records older than 30 days)"""
    db = get_db()
    
    # Calculate cutoff date (30 days ago)
    cutoff_date = datetime.now(JAKARTA_TZ) - timedelta(days=30)
    cutoff_iso = cutoff_date.isoformat()
    
    # Find records that will be deleted (for reporting)
    to_delete = await db.omset_trash.find(
        {'deleted_at': {'$lt': cutoff_iso}},
        {'_id': 0, 'customer_id': 1, 'deleted_at': 1, 'depo_total': 1}
    ).to_list(1000)
    
    # Delete old records
    result = await db.omset_trash.delete_many({
        'deleted_at': {'$lt': cutoff_iso}
    })
    
    deleted_count = result.deleted_count
    
    # Log the cleanup action
    if deleted_count > 0:
        await db.system_logs.insert_one({
            'type': 'omset_trash_cleanup',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_iso,
            'triggered_by': user.id,
            'triggered_by_name': user.name,
            'manual': True,
            'executed_at': datetime.now(JAKARTA_TZ).isoformat()
        })
    
    return {
        'success': True,
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_iso,
        'message': f'Permanently deleted {deleted_count} records older than 30 days' if deleted_count > 0 else 'No records older than 30 days to delete'
    }


# Initialize scheduler on startup
async def init_scheduler():
    """Initialize scheduler from saved config.
    
    IMPORTANT: Scheduler is ALWAYS started because:
    - Reserved member cleanup must run daily (at 00:01)
    - OMSET trash cleanup must run daily (at 00:05)
    These critical jobs run regardless of report/alert settings.
    """
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    # ALWAYS start scheduler - critical cleanup jobs must run even if reports/alerts are disabled
    start_scheduler(
        report_hour=config.get('report_hour', 1) if config else 1,
        report_minute=config.get('report_minute', 0) if config else 0,
        report_enabled=config.get('enabled', False) if config else False,
        atrisk_hour=config.get('atrisk_hour', 11) if config else 11,
        atrisk_minute=config.get('atrisk_minute', 0) if config else 0,
        atrisk_enabled=config.get('atrisk_enabled', False) if config else False,
        staff_offline_hour=config.get('staff_offline_hour', 11) if config else 11,
        staff_offline_minute=config.get('staff_offline_minute', 0) if config else 0,
        staff_offline_enabled=config.get('staff_offline_enabled', False) if config else False
    )
