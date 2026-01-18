# Staff Notifications Routes
# Tracks when staff last viewed their DB Bonanza and Member WD records
# Returns counts of newly assigned records since last view

from fastapi import APIRouter, Depends
from .deps import User, get_db, get_current_user, get_jakarta_now

router = APIRouter(tags=["Staff Notifications"])


@router.get("/staff/notifications/summary")
async def get_staff_notification_summary(user: User = Depends(get_current_user)):
    """
    Get counts of newly assigned records for staff.
    Returns the number of records assigned since the staff last viewed each page.
    """
    if user.role != 'staff':
        return {"bonanza_new": 0, "memberwd_new": 0}
    
    db = get_db()
    
    # Get the user's last viewed timestamps
    last_viewed = await db.staff_last_viewed.find_one(
        {'user_id': user.id},
        {'_id': 0}
    )
    
    bonanza_last_viewed = None
    memberwd_last_viewed = None
    
    if last_viewed:
        bonanza_last_viewed = last_viewed.get('bonanza_last_viewed')
        memberwd_last_viewed = last_viewed.get('memberwd_last_viewed')
    
    # Count bonanza records assigned after last view
    bonanza_query = {'assigned_to': user.id, 'status': 'assigned'}
    if bonanza_last_viewed:
        bonanza_query['assigned_at'] = {'$gt': bonanza_last_viewed}
    
    bonanza_new = await db.bonanza_records.count_documents(bonanza_query)
    
    # Count memberwd records assigned after last view
    memberwd_query = {'assigned_to': user.id, 'status': 'assigned'}
    if memberwd_last_viewed:
        memberwd_query['assigned_at'] = {'$gt': memberwd_last_viewed}
    
    memberwd_new = await db.memberwd_records.count_documents(memberwd_query)
    
    return {
        "bonanza_new": bonanza_new,
        "memberwd_new": memberwd_new
    }


@router.post("/staff/notifications/mark-viewed/{page_type}")
async def mark_page_viewed(page_type: str, user: User = Depends(get_current_user)):
    """
    Mark a page as viewed by the staff member.
    page_type: 'bonanza' or 'memberwd'
    """
    if user.role != 'staff':
        return {"success": True}
    
    if page_type not in ['bonanza', 'memberwd']:
        return {"success": False, "error": "Invalid page type"}
    
    db = get_db()
    current_time = get_jakarta_now().isoformat()
    
    field_name = f"{page_type}_last_viewed"
    
    await db.staff_last_viewed.update_one(
        {'user_id': user.id},
        {
            '$set': {
                field_name: current_time,
                'updated_at': current_time
            },
            '$setOnInsert': {
                'user_id': user.id,
                'created_at': current_time
            }
        },
        upsert=True
    )
    
    return {"success": True}
