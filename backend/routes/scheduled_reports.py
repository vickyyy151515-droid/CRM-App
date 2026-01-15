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

from db import get_db
from models.user import User
from routes.auth import get_admin_user

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

class ScheduledReportConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = "scheduled_report_config"
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    enabled: bool = False
    report_hour: int = 1
    report_minute: int = 0
    last_sent: Optional[str] = None
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


def start_scheduler(hour: int = 1, minute: int = 0):
    """Start the APScheduler with the configured schedule"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    
    scheduler = AsyncIOScheduler(timezone=JAKARTA_TZ)
    
    # Schedule the job to run daily at the specified time
    scheduler.add_job(
        send_scheduled_report,
        CronTrigger(hour=hour, minute=minute, timezone=JAKARTA_TZ),
        id='daily_report',
        replace_existing=True
    )
    
    scheduler.start()
    print(f"Scheduler started - Daily report will be sent at {hour:02d}:{minute:02d} WIB")


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
            'last_sent': None
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
    
    update_data = {
        'id': 'scheduled_report_config',
        'telegram_bot_token': config.bot_token,
        'telegram_chat_id': config.chat_id,
        'enabled': config.enabled,
        'report_hour': config.report_hour,
        'report_minute': config.report_minute,
        'updated_at': now.isoformat()
    }
    
    # Check if config exists
    existing = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'})
    
    if existing:
        await db.scheduled_report_config.update_one(
            {'id': 'scheduled_report_config'},
            {'$set': update_data}
        )
    else:
        update_data['created_at'] = now.isoformat()
        await db.scheduled_report_config.insert_one(update_data)
    
    # Restart scheduler if enabled
    if config.enabled:
        start_scheduler(config.report_hour, config.report_minute)
    else:
        stop_scheduler()
    
    return {'success': True, 'message': 'Configuration updated successfully'}


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


# Initialize scheduler on startup
async def init_scheduler():
    """Initialize scheduler from saved config"""
    db = get_db()
    config = await db.scheduled_report_config.find_one({'id': 'scheduled_report_config'}, {'_id': 0})
    
    if config and config.get('enabled'):
        start_scheduler(
            config.get('report_hour', 1),
            config.get('report_minute', 0)
        )
