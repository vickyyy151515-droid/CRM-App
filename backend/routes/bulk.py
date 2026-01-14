# Bulk Operations Routes

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
import random
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Bulk Operations"])

class BulkRequestAction(BaseModel):
    request_ids: List[str]
    action: str  # approve or reject

class BulkStatusUpdate(BaseModel):
    record_ids: List[str]
    whatsapp_status: Optional[str] = None
    respond_status: Optional[str] = None

class BulkDeleteRecords(BaseModel):
    record_ids: List[str]

@router.post("/bulk/requests")
async def bulk_request_action(bulk: BulkRequestAction, user: User = Depends(get_admin_user)):
    """Bulk approve or reject download requests (Admin only)"""
    db = get_db()
    if bulk.action not in ['approve', 'reject']:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    processed = 0
    errors = []
    notifications = []
    
    for request_id in bulk.request_ids:
        request = await db.download_requests.find_one({'id': request_id, 'status': 'pending'})
        if not request:
            errors.append(f"Request {request_id} not found or not pending")
            continue
        
        if bulk.action == 'approve':
            database = await db.databases.find_one({'id': request['database_id']})
            if not database:
                errors.append(f"Database not found for request {request_id}")
                continue
            
            available_records = await db.customer_records.find({
                'database_id': request['database_id'],
                'status': 'available'
            }, {'_id': 0}).to_list(request['record_count'])
            
            if len(available_records) < request['record_count']:
                errors.append(f"Not enough records for request {request_id}")
                continue
            
            random.shuffle(available_records)
            selected = available_records[:request['record_count']]
            selected_ids = [r['id'] for r in selected]
            
            await db.customer_records.update_many(
                {'id': {'$in': selected_ids}},
                {'$set': {
                    'status': 'assigned',
                    'assigned_to': request['requested_by'],
                    'assigned_to_name': request['requested_by_name'],
                    'assigned_at': get_jakarta_now().isoformat(),
                    'request_id': request_id
                }}
            )
            
            await db.download_requests.update_one(
                {'id': request_id},
                {'$set': {
                    'status': 'approved',
                    'reviewed_at': get_jakarta_now().isoformat(),
                    'reviewed_by': user.id,
                    'reviewed_by_name': user.name,
                    'record_ids': selected_ids
                }}
            )
            
            notifications.append({
                'id': str(uuid.uuid4()),
                'user_id': request['requested_by'],
                'type': 'request_approved',
                'title': 'Request Approved',
                'message': f'Your request for {request["record_count"]} records from {request["database_name"]} has been approved',
                'data': {'request_id': request_id, 'record_count': request['record_count']},
                'read': False,
                'created_at': get_jakarta_now().isoformat()
            })
        else:
            await db.download_requests.update_one(
                {'id': request_id},
                {'$set': {
                    'status': 'rejected',
                    'reviewed_at': get_jakarta_now().isoformat(),
                    'reviewed_by': user.id,
                    'reviewed_by_name': user.name
                }}
            )
            
            notifications.append({
                'id': str(uuid.uuid4()),
                'user_id': request['requested_by'],
                'type': 'request_rejected',
                'title': 'Request Rejected',
                'message': f'Your request for {request["record_count"]} records from {request["database_name"]} has been rejected',
                'data': {'request_id': request_id},
                'read': False,
                'created_at': get_jakarta_now().isoformat()
            })
        
        processed += 1
    
    if notifications:
        await db.notifications.insert_many(notifications)
    
    return {'message': f'{processed} requests {bulk.action}d successfully', 'processed': processed, 'errors': errors}

@router.post("/bulk/status-update")
async def bulk_status_update(bulk: BulkStatusUpdate, user: User = Depends(get_current_user)):
    """Bulk update WhatsApp/Respond status for multiple records"""
    db = get_db()
    update_fields = {}
    if bulk.whatsapp_status:
        if bulk.whatsapp_status not in ['ada', 'tidak', 'ceklis1']:
            raise HTTPException(status_code=400, detail="Invalid whatsapp_status")
        update_fields['whatsapp_status'] = bulk.whatsapp_status
    if bulk.respond_status:
        if bulk.respond_status not in ['ya', 'tidak']:
            raise HTTPException(status_code=400, detail="Invalid respond_status")
        update_fields['respond_status'] = bulk.respond_status
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No status fields to update")
    
    update_fields['updated_at'] = get_jakarta_now().isoformat()
    
    query = {'id': {'$in': bulk.record_ids}}
    if user.role == 'staff':
        query['assigned_to'] = user.id
    
    result = await db.customer_records.update_many(query, {'$set': update_fields})
    return {'message': f'{result.modified_count} records updated', 'modified_count': result.modified_count}

@router.delete("/bulk/bonanza-records")
async def bulk_delete_bonanza_records(bulk: BulkDeleteRecords, user: User = Depends(get_admin_user)):
    """Bulk delete Bonanza records (Admin only)"""
    db = get_db()
    result = await db.bonanza_records.delete_many({'id': {'$in': bulk.record_ids}})
    return {'message': f'{result.deleted_count} records deleted', 'deleted_count': result.deleted_count}

@router.delete("/bulk/memberwd-records")
async def bulk_delete_memberwd_records(bulk: BulkDeleteRecords, user: User = Depends(get_admin_user)):
    """Bulk delete Member WD records (Admin only)"""
    db = get_db()
    result = await db.memberwd_records.delete_many({'id': {'$in': bulk.record_ids}})
    return {'message': f'{result.deleted_count} records deleted', 'deleted_count': result.deleted_count}
