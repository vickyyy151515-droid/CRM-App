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
    
    # Get customer first deposit dates for NDP/RDP calculation
    all_customer_ids = list(set([r.get('customer_id_normalized') or r.get('customer_id', '').strip().upper() for r in records]))
    
    # Get first deposit dates
    first_deposits = {}
    for cid in all_customer_ids:
        first_record = await db.omset_records.find_one(
            {'$or': [
                {'customer_id_normalized': cid},
                {'customer_id': {'$regex': f'^{cid}$', '$options': 'i'}}
            ]},
            {'_id': 0, 'record_date': 1, 'product_id': 1},
            sort=[('record_date', 1)]
        )
        if first_record:
            key = (cid, first_record.get('product_id', ''))
            first_deposits[key] = first_record['record_date']
    
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
        cid_normalized = record.get('customer_id_normalized') or record.get('customer_id', '').strip().upper()
        key = (cid_normalized, product_id)
        first_date = first_deposits.get(key)
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
    """Generate at-risk customer alert for customers inactive for N+ days"""
    db = get_db()
    
    jakarta_now = datetime.now(JAKARTA_TZ)
    cutoff_date = (jakarta_now - timedelta(days=inactive_days)).strftime('%Y-%m-%d')
    
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
    
    # Track customer last deposit dates - use normalized IDs
    customer_data = {}  # {normalized_customer_id: {last_date, last_nominal, product_id, staff_id, customer_name}}
    
    for record in all_records:
        cid_normalized = record.get('customer_id_normalized') or record.get('customer_id', '').strip().upper()
        record_date = record.get('record_date', '')
        
        if cid_normalized not in customer_data:
            customer_data[cid_normalized] = {
                'last_date': record_date,
                'total_deposits': 1,
                'total_nominal': record.get('depo_total', 0) or record.get('nominal', 0) or 0,
                'product_id': record.get('product_id', ''),
                'staff_id': record.get('staff_id', ''),
                'customer_name': record.get('customer_id', cid_normalized),
                'staff_name': record.get('staff_name', 'Unknown')
            }
        else:
            # Update if this record is more recent
            if record_date > customer_data[cid_normalized]['last_date']:
                customer_data[cid_normalized]['last_date'] = record_date
                customer_data[cid_normalized]['product_id'] = record.get('product_id', '')
                customer_data[cid_normalized]['staff_id'] = record.get('staff_id', '')
                customer_data[cid_normalized]['staff_name'] = record.get('staff_name', 'Unknown')
            customer_data[cid_normalized]['total_deposits'] += 1
            customer_data[cid_normalized]['total_nominal'] += record.get('depo_total', 0) or record.get('nominal', 0) or 0
    
    # Find at-risk customers (last deposit before cutoff date AND has deposited at least twice)
    at_risk_customers = []
    for cid, data in customer_data.items():
        if data['last_date'] < cutoff_date and data['total_deposits'] >= 2:
            days_since = (jakarta_now - datetime.strptime(data['last_date'], '%Y-%m-%d').replace(tzinfo=JAKARTA_TZ)).days
            at_risk_customers.append({
                'customer_id': cid,
                'customer_name': data['customer_name'],
                'last_date': data['last_date'],
                'days_since': days_since,
                'total_deposits': data['total_deposits'],
                'total_nominal': data['total_nominal'],
                'product_id': data['product_id'],
                'product_name': product_map.get(data['product_id'], data['product_id']),
                'staff_id': data['staff_id'],
                'staff_name': data['staff_name']
            })
    
    # Sort by days since last deposit (most urgent first)
    at_risk_customers.sort(key=lambda x: x['days_since'], reverse=True)
    
    # Format the alert
    def format_rupiah(amount):
        return f"Rp {amount:,.0f}".replace(',', '.')
    
    alert_lines = [
        f"🚨 <b>AT-RISK CUSTOMER ALERT</b>",
        f"📅 <b>Date:</b> {jakarta_now.strftime('%Y-%m-%d')}",
        f"⚠️ <b>Threshold:</b> {inactive_days}+ days inactive",
        f"👥 <b>Total At-Risk:</b> {len(at_risk_customers)} customers",
        ""
    ]
    
    if not at_risk_customers:
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
        
        if len(staff_data['customers']) > 10:
            alert_lines.append(f"   <i>...and {len(staff_data['customers']) - 10} more</i>")
            alert_lines.append("")
    
    if len(at_risk_customers) > max_show:
        alert_lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        alert_lines.append(f"<i>Showing {max_show} of {len(at_risk_customers)} at-risk customers</i>")
    
    alert_lines.append("")
    alert_lines.append("💡 <b>Action Required:</b> Follow up with these customers to re-engage!")
    
    return "\n".join(alert_lines)


async def send_atrisk_alert():
    """Task that runs daily to send at-risk customer alerts to group"""
    db = get_db()
    
    # Get config
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('atrisk_enabled'):
        print("At-risk alerts are disabled")
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
            # Update last_sent timestamp
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'atrisk_last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
            )
            print(f"At-risk alert sent successfully at {datetime.now(JAKARTA_TZ)}")
        else:
            print("Failed to send at-risk alert")
            
    except Exception as e:
        print(f"Error sending at-risk alert: {e}")


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
            # Update last_sent timestamp
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'staff_offline_last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
            )
            print(f"Staff offline alert sent successfully at {datetime.now(JAKARTA_TZ)}")
        else:
            print("Failed to send staff offline alert")
            
    except Exception as e:
        print(f"Error sending staff offline alert: {e}")


async def send_scheduled_report():
    """Task that runs daily to send the report"""
    db = get_db()
    
    # Get config
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if not config or not config.get('enabled'):
        print("Scheduled report is disabled")
        return
    
    bot_token = config.get('telegram_bot_token')
    chat_id = config.get('telegram_chat_id')
    
    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID not configured")
        return
    
    try:
        # Generate and send report
        report = await generate_daily_report()
        success = await send_telegram_message(bot_token, chat_id, report)
        
        if success:
            # Update last_sent timestamp
            await db.scheduled_report_config.update_one(
                {'id': 'scheduled_report_config'},
                {'$set': {'last_sent': datetime.now(JAKARTA_TZ).isoformat()}}
            )
            print(f"Daily report sent successfully at {datetime.now(JAKARTA_TZ)}")
        else:
            print("Failed to send daily report")
            
    except Exception as e:
        print(f"Error sending scheduled report: {e}")


def start_scheduler(report_hour: int = 1, report_minute: int = 0, 
                    atrisk_hour: int = None, atrisk_minute: int = None, 
                    atrisk_enabled: bool = False,
                    staff_offline_hour: int = None, staff_offline_minute: int = None,
                    staff_offline_enabled: bool = False):
    """Start the APScheduler with the configured schedules"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    
    scheduler = AsyncIOScheduler(timezone=JAKARTA_TZ)
    
    # Schedule daily report
    scheduler.add_job(
        send_scheduled_report,
        CronTrigger(hour=report_hour, minute=report_minute, timezone=JAKARTA_TZ),
        id='daily_report',
        replace_existing=True
    )
    print(f"Daily report scheduled at {report_hour:02d}:{report_minute:02d} WIB")
    
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
    
    # Restart scheduler with all alert settings
    if config.enabled or updated_config.get('atrisk_enabled') or updated_config.get('staff_offline_enabled'):
        start_scheduler(
            report_hour=config.report_hour,
            report_minute=config.report_minute,
            atrisk_hour=updated_config.get('atrisk_hour', 11),
            atrisk_minute=updated_config.get('atrisk_minute', 0),
            atrisk_enabled=updated_config.get('atrisk_enabled', False),
            staff_offline_hour=updated_config.get('staff_offline_hour', 11),
            staff_offline_minute=updated_config.get('staff_offline_minute', 0),
            staff_offline_enabled=updated_config.get('staff_offline_enabled', False)
        )
    else:
        stop_scheduler()
    
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
    
    # Restart scheduler
    if updated_config.get('enabled') or config.enabled:
        start_scheduler(
            report_hour=updated_config.get('report_hour', 1),
            report_minute=updated_config.get('report_minute', 0),
            atrisk_hour=config.alert_hour,
            atrisk_minute=config.alert_minute,
            atrisk_enabled=config.enabled
        )
    
    return {'success': True, 'message': 'At-risk alert configuration updated successfully'}


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


# Initialize scheduler on startup
async def init_scheduler():
    """Initialize scheduler from saved config"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if config and (config.get('enabled') or config.get('atrisk_enabled')):
        start_scheduler(
            report_hour=config.get('report_hour', 1),
            report_minute=config.get('report_minute', 0),
            atrisk_hour=config.get('atrisk_hour', 11),
            atrisk_minute=config.get('atrisk_minute', 0),
            atrisk_enabled=config.get('atrisk_enabled', False)
        )
