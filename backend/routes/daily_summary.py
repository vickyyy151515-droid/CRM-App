# Daily Summary Routes
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import asyncio

from .deps import get_db, get_current_user, get_admin_user, User
from utils.helpers import normalize_customer_id, get_jakarta_now

router = APIRouter(tags=["Daily Summary"])

# Helper function to check if record has "tambahan" in notes
def is_tambahan_record(record) -> bool:
    """Check if record has 'tambahan' in keterangan field"""
    keterangan = record.get('keterangan', '') or ''
    return 'tambahan' in keterangan.lower()

# ==================== HELPER FUNCTIONS ====================

async def generate_daily_summary(date_str: str = None):
    """Generate daily summary for a specific date"""
    db = get_db()
    
    if date_str is None:
        jakarta_now = get_jakarta_now()
        date_str = jakarta_now.strftime('%Y-%m-%d')
    
    # Get all OMSET records for the date
    records = await db.omset_records.find(
        {'record_date': date_str},
        {'_id': 0}
    ).to_list(100000)
    
    if not records:
        return None
    
    # Get all records for NDP/RDP calculation
    all_records = await db.omset_records.find({}, {'_id': 0}).to_list(500000)
    
    # Build PER-STAFF customer first deposit date map (SINGLE SOURCE OF TRUTH)
    # Key: (staff_id, customer_id_normalized, product_id) -> first_date
    # IMPORTANT: Exclude records with "tambahan" in notes from first_date calculation
    staff_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        staff_id_rec = record['staff_id']
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (staff_id_rec, cid_normalized, record['product_id'])
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Calculate totals
    total_omset = 0
    total_ndp = 0
    total_rdp = 0
    total_forms = len(records)
    
    # Track unique (staff, customer, product) tuples for NDP/RDP — SINGLE SOURCE OF TRUTH
    daily_ndp_tuples = set()
    daily_rdp_tuples = set()
    
    # Staff breakdown — track (customer, product) pairs per staff
    staff_stats = {}
    staff_ndp_pairs = {}
    staff_rdp_pairs = {}
    
    # Product breakdown within staff — track (customer) per (staff, product)
    
    # Overall product stats — track (staff, customer) pairs per product
    product_stats = {}
    product_ndp_pairs = {}
    product_rdp_pairs = {}
    
    for record in records:
        staff_id = record['staff_id']
        staff_name = record['staff_name']
        product_id = record.get('product_id', 'unknown')
        product_name = record.get('product_name', 'Unknown Product')
        depo_total = record.get('depo_total', 0) or 0
        
        # Normalized customer_id
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        
        # SINGLE NDP definition: per (staff, customer, product)
        staff_key = (staff_id, cid_normalized, record['product_id'])
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        # Determine NDP/RDP using staff-specific first date
        if is_tambahan_record(record):
            is_ndp = False
        else:
            is_ndp = staff_first_date == date_str
        
        total_omset += depo_total
        
        # --- Daily totals: track (staff, customer, product) tuples ---
        ndp_tuple = (staff_id, cid_normalized, product_id)
        if is_ndp:
            if ndp_tuple not in daily_ndp_tuples:
                daily_ndp_tuples.add(ndp_tuple)
                total_ndp += 1
        else:
            if ndp_tuple not in daily_rdp_tuples:
                daily_rdp_tuples.add(ndp_tuple)
                total_rdp += 1
        
        # --- Staff stats ---
        if staff_id not in staff_stats:
            staff_stats[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0,
                'product_breakdown': {}
            }
            staff_ndp_pairs[staff_id] = set()
            staff_rdp_pairs[staff_id] = set()
        
        staff_stats[staff_id]['total_omset'] += depo_total
        staff_stats[staff_id]['form_count'] += 1
        
        # Track (customer, product) pairs per staff — each product is independent
        customer_product_pair = (cid_normalized, product_id)
        if is_ndp:
            if customer_product_pair not in staff_ndp_pairs[staff_id]:
                staff_ndp_pairs[staff_id].add(customer_product_pair)
                staff_stats[staff_id]['ndp_count'] += 1
        else:
            if customer_product_pair not in staff_rdp_pairs[staff_id]:
                staff_rdp_pairs[staff_id].add(customer_product_pair)
                staff_stats[staff_id]['rdp_count'] += 1
        
        # --- Staff's product breakdown ---
        if product_id not in staff_stats[staff_id]['product_breakdown']:
            staff_stats[staff_id]['product_breakdown'][product_id] = {
                'product_id': product_id,
                'product_name': product_name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0,
                '_ndp_customers': set(),
                '_rdp_customers': set()
            }
        
        pb = staff_stats[staff_id]['product_breakdown'][product_id]
        pb['total_omset'] += depo_total
        pb['form_count'] += 1
        # Per-product within staff: track customer_id
        if is_ndp:
            if cid_normalized not in pb['_ndp_customers']:
                pb['_ndp_customers'].add(cid_normalized)
                pb['ndp_count'] += 1
        else:
            if cid_normalized not in pb['_rdp_customers']:
                pb['_rdp_customers'].add(cid_normalized)
                pb['rdp_count'] += 1
        
        # --- Overall product stats ---
        if product_id not in product_stats:
            product_stats[product_id] = {
                'product_id': product_id,
                'product_name': product_name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0
            }
            product_ndp_pairs[product_id] = set()
            product_rdp_pairs[product_id] = set()
        
        product_stats[product_id]['total_omset'] += depo_total
        product_stats[product_id]['form_count'] += 1
        
        # Track (staff, customer) pairs per product — each staff is independent
        staff_customer_pair = (staff_id, cid_normalized)
        if is_ndp:
            if staff_customer_pair not in product_ndp_pairs[product_id]:
                product_ndp_pairs[product_id].add(staff_customer_pair)
                product_stats[product_id]['ndp_count'] += 1
        else:
            if staff_customer_pair not in product_rdp_pairs[product_id]:
                product_rdp_pairs[product_id].add(staff_customer_pair)
                product_stats[product_id]['rdp_count'] += 1
    
    # Convert staff stats to list and sort by OMSET
    # Also clean up the internal tracking sets from product breakdown
    for staff_id in staff_stats:
        for product_id in staff_stats[staff_id]['product_breakdown']:
            pb = staff_stats[staff_id]['product_breakdown'][product_id]
            del pb['_ndp_customers']
            del pb['_rdp_customers']
        staff_stats[staff_id]['product_breakdown'] = sorted(
            staff_stats[staff_id]['product_breakdown'].values(),
            key=lambda x: x['total_omset'],
            reverse=True
        )
    staff_list = sorted(staff_stats.values(), key=lambda x: x['total_omset'], reverse=True)
    
    # Convert product stats to list and sort by OMSET
    product_list = sorted(product_stats.values(), key=lambda x: x['total_omset'], reverse=True)
    
    # Determine top performer
    top_performer = staff_list[0] if staff_list else None
    
    # Build summary document
    summary = {
        'date': date_str,
        'total_omset': total_omset,
        'total_ndp': total_ndp,
        'total_rdp': total_rdp,
        'total_forms': total_forms,
        'top_performer': {
            'staff_id': top_performer['staff_id'],
            'staff_name': top_performer['staff_name'],
            'omset': top_performer['total_omset'],
            'ndp': top_performer['ndp_count'],
            'rdp': top_performer['rdp_count']
        } if top_performer else None,
        'staff_breakdown': staff_list,
        'product_breakdown': product_list,
        'generated_at': get_jakarta_now().isoformat()
    }
    
    return summary

async def save_daily_summary(summary: dict):
    """Save daily summary to database"""
    db = get_db()
    
    # Check if summary already exists for this date
    existing = await db.daily_summaries.find_one({'date': summary['date']})
    
    if existing:
        # Update existing
        await db.daily_summaries.update_one(
            {'date': summary['date']},
            {'$set': summary}
        )
    else:
        # Insert new
        await db.daily_summaries.insert_one(summary)
    
    return summary


async def generate_daily_summary_filtered(date_str: str, filter_product_id: str):
    """Generate daily summary for a specific date filtered by product"""
    db = get_db()
    
    if date_str is None:
        jakarta_now = get_jakarta_now()
        date_str = jakarta_now.strftime('%Y-%m-%d')
    
    # Get OMSET records for the date filtered by product
    records = await db.omset_records.find(
        {'record_date': date_str, 'product_id': filter_product_id},
        {'_id': 0}
    ).to_list(100000)
    
    if not records:
        return None
    
    # Get all records for NDP/RDP calculation (for this product only)
    all_records = await db.omset_records.find(
        {'product_id': filter_product_id},
        {'_id': 0}
    ).to_list(500000)
    
    # Build GLOBAL customer first deposit date map
    global_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = cid_normalized
        if key not in global_customer_first_date:
            global_customer_first_date[key] = record['record_date']
    
    # Build PER-STAFF customer first deposit date map
    staff_customer_first_date = {}
    for record in sorted(all_records, key=lambda x: x['record_date']):
        if is_tambahan_record(record):
            continue
        staff_id = record['staff_id']
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        key = (staff_id, cid_normalized)
        if key not in staff_customer_first_date:
            staff_customer_first_date[key] = record['record_date']
    
    # Calculate statistics
    total_omset = 0
    total_ndp = 0
    total_rdp = 0
    total_forms = len(records)
    
    staff_stats = {}
    staff_ndp_customers = {}
    staff_rdp_customers = {}
    
    global_ndp_customers = set()
    global_rdp_customers = set()
    
    # Get product name
    product_name = records[0].get('product_name', 'Unknown') if records else 'Unknown'
    
    for record in records:
        staff_id = record['staff_id']
        staff_name = record['staff_name']
        depo_total = record.get('depo_total', 0) or 0
        cid_normalized = record.get('customer_id_normalized') or normalize_customer_id(record['customer_id'])
        
        total_omset += depo_total
        
        # Determine NDP/RDP
        is_tambahan = is_tambahan_record(record)
        global_first_date = global_customer_first_date.get(cid_normalized)
        staff_key = (staff_id, cid_normalized)
        staff_first_date = staff_customer_first_date.get(staff_key)
        
        if is_tambahan:
            is_global_ndp = False
            is_staff_ndp = False
        else:
            is_global_ndp = global_first_date == date_str
            is_staff_ndp = staff_first_date == date_str
        
        # Global NDP/RDP count
        if is_global_ndp:
            if cid_normalized not in global_ndp_customers:
                global_ndp_customers.add(cid_normalized)
                total_ndp += 1
        else:
            if cid_normalized not in global_rdp_customers:
                global_rdp_customers.add(cid_normalized)
                total_rdp += 1
        
        # Staff stats
        if staff_id not in staff_stats:
            staff_stats[staff_id] = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0,
                'product_breakdown': []
            }
            staff_ndp_customers[staff_id] = set()
            staff_rdp_customers[staff_id] = set()
        
        staff_stats[staff_id]['total_omset'] += depo_total
        staff_stats[staff_id]['form_count'] += 1
        
        if is_staff_ndp:
            if cid_normalized not in staff_ndp_customers[staff_id]:
                staff_ndp_customers[staff_id].add(cid_normalized)
                staff_stats[staff_id]['ndp_count'] += 1
        else:
            if cid_normalized not in staff_rdp_customers[staff_id]:
                staff_rdp_customers[staff_id].add(cid_normalized)
                staff_stats[staff_id]['rdp_count'] += 1
    
    staff_list = sorted(staff_stats.values(), key=lambda x: x['total_omset'], reverse=True)
    top_performer = staff_list[0] if staff_list else None
    
    summary = {
        'date': date_str,
        'product_filter': filter_product_id,
        'product_name': product_name,
        'total_omset': total_omset,
        'total_ndp': total_ndp,
        'total_rdp': total_rdp,
        'total_forms': total_forms,
        'top_performer': {
            'staff_id': top_performer['staff_id'],
            'staff_name': top_performer['staff_name'],
            'omset': top_performer['total_omset'],
            'ndp': top_performer['ndp_count'],
            'rdp': top_performer['rdp_count']
        } if top_performer else None,
        'staff_breakdown': staff_list,
        'product_breakdown': [{
            'product_id': filter_product_id,
            'product_name': product_name,
            'total_omset': total_omset,
            'ndp_count': total_ndp,
            'rdp_count': total_rdp,
            'form_count': total_forms
        }],
        'generated_at': get_jakarta_now().isoformat()
    }
    
    return summary

# ==================== DAILY SUMMARY ENDPOINTS ====================

@router.get("/daily-summary")
async def get_daily_summary(
    date: Optional[str] = None,
    product_id: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Get daily summary for a specific date (defaults to today), optionally filtered by product"""
    db = get_db()
    
    if date is None:
        jakarta_now = get_jakarta_now()
        date = jakarta_now.strftime('%Y-%m-%d')
    
    # If product_id filter is specified, generate fresh filtered summary
    if product_id:
        summary = await generate_daily_summary_filtered(date, product_id)
        if summary is None:
            if user.role == 'staff':
                return {
                    'date': date,
                    'product_filter': product_id,
                    'my_stats': {
                        'staff_id': user.id,
                        'staff_name': user.name,
                        'total_omset': 0,
                        'ndp_count': 0,
                        'rdp_count': 0,
                        'form_count': 0,
                        'product_breakdown': []
                    },
                    'my_rank': None,
                    'total_staff': 0,
                    'team_total_omset': 0,
                    'team_total_ndp': 0,
                    'team_total_rdp': 0,
                    'top_performer': None,
                    'product_breakdown': [],
                    'staff_breakdown': []
                }
            return {
                'date': date,
                'product_filter': product_id,
                'total_omset': 0,
                'total_ndp': 0,
                'total_rdp': 0,
                'form_count': 0,
                'staff_breakdown': [],
                'product_breakdown': [],
                'top_performer': None
            }
        
        # For staff, filter to show only their own stats
        if user.role == 'staff':
            staff_breakdown = [s for s in summary.get('staff_breakdown', []) if s['staff_id'] == user.id]
            my_stats = staff_breakdown[0] if staff_breakdown else {
                'staff_id': user.id,
                'staff_name': user.name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0,
                'product_breakdown': []
            }
            all_staff = summary.get('staff_breakdown', [])
            my_rank = next((i + 1 for i, s in enumerate(all_staff) if s['staff_id'] == user.id), None)
            return {
                'date': date,
                'product_filter': product_id,
                'my_stats': my_stats,
                'my_rank': my_rank,
                'total_staff': len(all_staff),
                'team_total_omset': summary.get('total_omset', 0),
                'team_total_ndp': summary.get('total_ndp', 0),
                'team_total_rdp': summary.get('total_rdp', 0),
                'top_performer': summary.get('top_performer'),
                'product_breakdown': summary.get('product_breakdown', []),
                'generated_at': summary.get('generated_at')
            }
        return summary
    
    # Try to get from database first (unfiltered)
    saved_summary = await db.daily_summaries.find_one({'date': date}, {'_id': 0})
    
    if saved_summary:
        # For staff, filter to show only their own stats
        if user.role == 'staff':
            staff_breakdown = [s for s in saved_summary.get('staff_breakdown', []) if s['staff_id'] == user.id]
            my_stats = staff_breakdown[0] if staff_breakdown else {
                'staff_id': user.id,
                'staff_name': user.name,
                'total_omset': 0,
                'ndp_count': 0,
                'rdp_count': 0,
                'form_count': 0,
                'product_breakdown': []
            }
            
            # Calculate rank
            all_staff = saved_summary.get('staff_breakdown', [])
            my_rank = next((i + 1 for i, s in enumerate(all_staff) if s['staff_id'] == user.id), None)
            
            return {
                'date': date,
                'my_stats': my_stats,
                'my_rank': my_rank,
                'total_staff': len(all_staff),
                'team_total_omset': saved_summary.get('total_omset', 0),
                'team_total_ndp': saved_summary.get('total_ndp', 0),
                'team_total_rdp': saved_summary.get('total_rdp', 0),
                'top_performer': saved_summary.get('top_performer'),
                'product_breakdown': saved_summary.get('product_breakdown', []),
                'generated_at': saved_summary.get('generated_at')
            }
        
        return saved_summary
    
    # Generate fresh summary
    summary = await generate_daily_summary(date)
    
    if summary is None:
        # Return empty summary
        if user.role == 'staff':
            return {
                'date': date,
                'my_stats': {
                    'staff_id': user.id,
                    'staff_name': user.name,
                    'total_omset': 0,
                    'ndp_count': 0,
                    'rdp_count': 0,
                    'form_count': 0,
                    'product_breakdown': []
                },
                'my_rank': None,
                'total_staff': 0,
                'team_total_omset': 0,
                'team_total_ndp': 0,
                'team_total_rdp': 0,
                'top_performer': None,
                'product_breakdown': [],
                'generated_at': get_jakarta_now().isoformat()
            }
        
        return {
            'date': date,
            'total_omset': 0,
            'total_ndp': 0,
            'total_rdp': 0,
            'total_forms': 0,
            'top_performer': None,
            'staff_breakdown': [],
            'product_breakdown': [],
            'generated_at': get_jakarta_now().isoformat()
        }
    
    # For staff, filter to show only their own stats
    if user.role == 'staff':
        staff_breakdown = [s for s in summary.get('staff_breakdown', []) if s['staff_id'] == user.id]
        my_stats = staff_breakdown[0] if staff_breakdown else {
            'staff_id': user.id,
            'staff_name': user.name,
            'total_omset': 0,
            'ndp_count': 0,
            'rdp_count': 0,
            'form_count': 0,
            'product_breakdown': []
        }
        
        # Calculate rank
        all_staff = summary.get('staff_breakdown', [])
        my_rank = next((i + 1 for i, s in enumerate(all_staff) if s['staff_id'] == user.id), None)
        
        return {
            'date': date,
            'my_stats': my_stats,
            'my_rank': my_rank,
            'total_staff': len(all_staff),
            'team_total_omset': summary.get('total_omset', 0),
            'team_total_ndp': summary.get('total_ndp', 0),
            'team_total_rdp': summary.get('total_rdp', 0),
            'top_performer': summary.get('top_performer'),
            'product_breakdown': summary.get('product_breakdown', []),
            'generated_at': summary.get('generated_at')
        }
    
    return summary

@router.get("/daily-summary/history")
async def get_daily_summary_history(
    days: int = 7,
    user: User = Depends(get_current_user)
):
    """Get daily summary history for the past N days"""
    db = get_db()
    
    jakarta_now = get_jakarta_now()
    
    summaries = []
    for i in range(days):
        date = (jakarta_now - timedelta(days=i)).strftime('%Y-%m-%d')
        
        # Try to get from database
        saved_summary = await db.daily_summaries.find_one({'date': date}, {'_id': 0})
        
        if saved_summary:
            if user.role == 'staff':
                # Filter for staff
                staff_breakdown = [s for s in saved_summary.get('staff_breakdown', []) if s['staff_id'] == user.id]
                my_stats = staff_breakdown[0] if staff_breakdown else None
                
                if my_stats:
                    all_staff = saved_summary.get('staff_breakdown', [])
                    my_rank = next((idx + 1 for idx, s in enumerate(all_staff) if s['staff_id'] == user.id), None)
                    
                    summaries.append({
                        'date': date,
                        'my_stats': my_stats,
                        'my_rank': my_rank,
                        'total_staff': len(all_staff),
                        'team_total_omset': saved_summary.get('total_omset', 0),
                        'top_performer': saved_summary.get('top_performer')
                    })
            else:
                summaries.append(saved_summary)
        else:
            # Generate fresh for this date
            summary = await generate_daily_summary(date)
            if summary:
                if user.role == 'staff':
                    staff_breakdown = [s for s in summary.get('staff_breakdown', []) if s['staff_id'] == user.id]
                    my_stats = staff_breakdown[0] if staff_breakdown else None
                    
                    if my_stats:
                        all_staff = summary.get('staff_breakdown', [])
                        my_rank = next((idx + 1 for idx, s in enumerate(all_staff) if s['staff_id'] == user.id), None)
                        
                        summaries.append({
                            'date': date,
                            'my_stats': my_stats,
                            'my_rank': my_rank,
                            'total_staff': len(all_staff),
                            'team_total_omset': summary.get('total_omset', 0),
                            'top_performer': summary.get('top_performer')
                        })
                else:
                    summaries.append(summary)
    
    return summaries

@router.post("/daily-summary/generate")
async def trigger_daily_summary_generation(
    date: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Manually trigger daily summary generation (Admin only)"""
    if date is None:
        jakarta_now = get_jakarta_now()
        date = jakarta_now.strftime('%Y-%m-%d')
    
    summary = await generate_daily_summary(date)
    
    if summary:
        await save_daily_summary(summary)
        return {'message': f'Daily summary generated for {date}', 'summary': summary}
    
    return {'message': f'No data found for {date}', 'summary': None}

@router.post("/daily-summary/generate-range")
async def generate_summary_range(
    start_date: str,
    end_date: str,
    user: User = Depends(get_admin_user)
):
    """Generate daily summaries for a date range (Admin only)"""
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    generated = []
    current = start
    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        summary = await generate_daily_summary(date_str)
        if summary:
            await save_daily_summary(summary)
            generated.append(date_str)
        current += timedelta(days=1)
    
    return {'message': f'Generated {len(generated)} summaries', 'dates': generated}

@router.get("/daily-summary/my-performance")
async def get_my_performance_trend(
    days: int = 30,
    user: User = Depends(get_current_user)
):
    """Get performance trend for the current user over N days"""
    if user.role != 'staff':
        raise HTTPException(status_code=403, detail="This endpoint is for staff only")
    
    db = get_db()
    jakarta_now = get_jakarta_now()
    
    # Get ALL records for this staff to build customer_first_date map
    all_records = await db.omset_records.find(
        {'staff_id': user.id},
        {'_id': 0}
    ).to_list(100000)
    
    # Build customer first deposit map (using normalized customer_id)
    # IMPORTANT: Exclude records with "tambahan" from first_date calculation
    customer_first_date = {}
    for rec in sorted(all_records, key=lambda x: x['record_date']):
        # Skip "tambahan" records when determining first deposit date
        if is_tambahan_record(rec):
            continue
        cid_normalized = rec.get('customer_id_normalized') or normalize_customer_id(rec['customer_id'])
        key = (cid_normalized, rec['product_id'])
        if key not in customer_first_date:
            customer_first_date[key] = rec['record_date']
    
    performance = []
    for i in range(days):
        date = (jakarta_now - timedelta(days=i)).strftime('%Y-%m-%d')
        
        # Get OMSET records for this staff on this date
        records = await db.omset_records.find(
            {'staff_id': user.id, 'record_date': date},
            {'_id': 0}
        ).to_list(1000)
        
        if records:
            total_omset = sum(r.get('depo_total', 0) or 0 for r in records)
            
            # Track unique (customer, product) pairs for NDP and RDP
            ndp_pairs = set()
            rdp_pairs = set()
            
            for r in records:
                cid_normalized = r.get('customer_id_normalized') or normalize_customer_id(r['customer_id'])
                key = (cid_normalized, r['product_id'])
                first_date = customer_first_date.get(key)
                
                # Determine NDP/RDP:
                # 1. If notes contain "tambahan" (case-insensitive), always RDP
                # 2. Otherwise, NDP if this is the first deposit date for this customer+product
                if is_tambahan_record(r):
                    is_ndp = False
                else:
                    is_ndp = first_date == date
                
                if is_ndp:
                    ndp_pairs.add(key)
                else:
                    rdp_pairs.add(key)
            
            performance.append({
                'date': date,
                'total_omset': total_omset,
                'ndp_count': len(ndp_pairs),
                'rdp_count': len(rdp_pairs),
                'form_count': len(records)
            })
    
    return performance
