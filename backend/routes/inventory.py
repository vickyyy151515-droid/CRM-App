# Office Inventory Routes
# Track office assets/equipment assigned to staff

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
import uuid

from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Office Inventory"])

# ==================== PYDANTIC MODELS ====================

class InventoryItemCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: Optional[str] = None
    category: str  # e.g., "Laptop", "Monitor", "Phone", "Furniture", "Other"
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_price: Optional[float] = None
    condition: str = "good"  # good, fair, poor
    notes: Optional[str] = None
    # Optional: Assign to staff immediately when creating
    assign_to_staff_id: Optional[str] = None
    assignment_notes: Optional[str] = None

class InventoryItemUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_price: Optional[float] = None
    condition: Optional[str] = None
    notes: Optional[str] = None

class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    staff_id: str
    notes: Optional[str] = None

class ReturnItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    condition: str = "good"
    notes: Optional[str] = None


# ==================== INVENTORY ENDPOINTS ====================

@router.get("/inventory")
async def get_inventory(
    category: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    user: User = Depends(get_admin_user)
):
    """Get all inventory items with optional filters"""
    db = get_db()
    
    query = {}
    if category:
        query['category'] = category
    if status:
        query['status'] = status
    if assigned_to:
        query['assigned_to'] = assigned_to
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'serial_number': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}}
        ]
    
    items = await db.inventory_items.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    
    # Get categories for filter dropdown
    categories = await db.inventory_items.distinct('category')
    
    # Get stats
    total_items = await db.inventory_items.count_documents({})
    assigned_items = await db.inventory_items.count_documents({'status': 'assigned'})
    available_items = await db.inventory_items.count_documents({'status': 'available'})
    
    return {
        'items': items,
        'categories': categories,
        'stats': {
            'total': total_items,
            'assigned': assigned_items,
            'available': available_items
        }
    }


@router.get("/inventory/{item_id}")
async def get_inventory_item(item_id: str, user: User = Depends(get_admin_user)):
    """Get a single inventory item with its assignment history"""
    db = get_db()
    
    item = await db.inventory_items.find_one({'id': item_id}, {'_id': 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Get assignment history
    history = await db.inventory_assignments.find(
        {'item_id': item_id},
        {'_id': 0}
    ).sort('assigned_at', -1).to_list(100)
    
    return {
        'item': item,
        'assignment_history': history
    }


@router.post("/inventory")
async def create_inventory_item(item_data: InventoryItemCreate, user: User = Depends(get_admin_user)):
    """Create a new inventory item, optionally assigning it to a staff member"""
    db = get_db()
    
    now = get_jakarta_now()
    item_id = str(uuid.uuid4())
    
    # Check if we need to assign to a staff member
    staff = None
    if item_data.assign_to_staff_id:
        staff = await db.users.find_one({'id': item_data.assign_to_staff_id})
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found")
    
    item = {
        'id': item_id,
        'name': item_data.name,
        'description': item_data.description,
        'category': item_data.category,
        'serial_number': item_data.serial_number,
        'purchase_date': item_data.purchase_date,
        'purchase_price': item_data.purchase_price,
        'condition': item_data.condition,
        'notes': item_data.notes,
        'status': 'assigned' if staff else 'available',
        'assigned_to': staff['id'] if staff else None,
        'assigned_to_name': staff['name'] if staff else None,
        'assigned_at': now.isoformat() if staff else None,
        'created_at': now.isoformat(),
        'created_by': user.id,
        'created_by_name': user.name,
        'updated_at': now.isoformat()
    }
    
    await db.inventory_items.insert_one(item)
    item.pop('_id', None)
    
    # Create assignment record if assigned
    if staff:
        assignment_record = {
            'id': str(uuid.uuid4()),
            'item_id': item_id,
            'item_name': item_data.name,
            'staff_id': staff['id'],
            'staff_name': staff['name'],
            'assigned_at': now.isoformat(),
            'assigned_by': user.id,
            'assigned_by_name': user.name,
            'returned_at': None,
            'return_condition': None,
            'notes': item_data.assignment_notes
        }
        await db.inventory_assignments.insert_one(assignment_record)
    
    return item


@router.put("/inventory/{item_id}")
async def update_inventory_item(item_id: str, item_data: InventoryItemUpdate, user: User = Depends(get_admin_user)):
    """Update an inventory item"""
    db = get_db()
    
    item = await db.inventory_items.find_one({'id': item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = {k: v for k, v in item_data.model_dump().items() if v is not None}
    update_data['updated_at'] = get_jakarta_now().isoformat()
    
    await db.inventory_items.update_one({'id': item_id}, {'$set': update_data})
    
    updated_item = await db.inventory_items.find_one({'id': item_id}, {'_id': 0})
    return updated_item


@router.delete("/inventory/{item_id}")
async def delete_inventory_item(item_id: str, user: User = Depends(get_admin_user)):
    """Delete an inventory item"""
    db = get_db()
    
    item = await db.inventory_items.find_one({'id': item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.get('status') == 'assigned':
        raise HTTPException(status_code=400, detail="Cannot delete assigned item. Return it first.")
    
    await db.inventory_items.delete_one({'id': item_id})
    await db.inventory_assignments.delete_many({'item_id': item_id})
    
    return {'message': 'Item deleted successfully'}


# ==================== ASSIGNMENT ENDPOINTS ====================

@router.post("/inventory/{item_id}/assign")
async def assign_inventory_item(item_id: str, assignment: AssignmentCreate, user: User = Depends(get_admin_user)):
    """Assign an inventory item to a staff member"""
    db = get_db()
    
    item = await db.inventory_items.find_one({'id': item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.get('status') == 'assigned':
        raise HTTPException(status_code=400, detail="Item is already assigned")
    
    # Get staff info
    staff = await db.users.find_one({'id': assignment.staff_id})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    now = get_jakarta_now()
    
    # Create assignment record
    assignment_record = {
        'id': str(uuid.uuid4()),
        'item_id': item_id,
        'item_name': item['name'],
        'staff_id': assignment.staff_id,
        'staff_name': staff['name'],
        'assigned_at': now.isoformat(),
        'assigned_by': user.id,
        'assigned_by_name': user.name,
        'returned_at': None,
        'return_condition': None,
        'notes': assignment.notes
    }
    
    await db.inventory_assignments.insert_one(assignment_record)
    
    # Update item status
    await db.inventory_items.update_one(
        {'id': item_id},
        {'$set': {
            'status': 'assigned',
            'assigned_to': assignment.staff_id,
            'assigned_to_name': staff['name'],
            'assigned_at': now.isoformat(),
            'updated_at': now.isoformat()
        }}
    )
    
    return {'message': f'Item assigned to {staff["name"]}', 'assignment_id': assignment_record['id']}


@router.post("/inventory/{item_id}/return")
async def return_inventory_item(item_id: str, return_data: ReturnItem, user: User = Depends(get_admin_user)):
    """Return an inventory item from a staff member"""
    db = get_db()
    
    item = await db.inventory_items.find_one({'id': item_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.get('status') != 'assigned':
        raise HTTPException(status_code=400, detail="Item is not currently assigned")
    
    now = get_jakarta_now()
    
    # Update the latest assignment record
    await db.inventory_assignments.update_one(
        {'item_id': item_id, 'returned_at': None},
        {'$set': {
            'returned_at': now.isoformat(),
            'return_condition': return_data.condition,
            'return_notes': return_data.notes,
            'returned_by': user.id,
            'returned_by_name': user.name
        }}
    )
    
    # Update item status
    await db.inventory_items.update_one(
        {'id': item_id},
        {'$set': {
            'status': 'available',
            'condition': return_data.condition,
            'assigned_to': None,
            'assigned_to_name': None,
            'assigned_at': None,
            'updated_at': now.isoformat()
        }}
    )
    
    return {'message': 'Item returned successfully'}


@router.get("/inventory/staff/{staff_id}")
async def get_staff_inventory(staff_id: str, user: User = Depends(get_admin_user)):
    """Get all items assigned to a specific staff member"""
    db = get_db()
    
    items = await db.inventory_items.find(
        {'assigned_to': staff_id},
        {'_id': 0}
    ).to_list(100)
    
    staff = await db.users.find_one({'id': staff_id}, {'_id': 0, 'id': 1, 'name': 1, 'email': 1})
    
    return {
        'staff': staff,
        'items': items,
        'total_items': len(items)
    }


@router.get("/inventory/categories")
async def get_inventory_categories(user: User = Depends(get_admin_user)):
    """Get list of all categories with item counts"""
    db = get_db()
    
    pipeline = [
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    
    categories = await db.inventory_items.aggregate(pipeline).to_list(100)
    
    return [{'name': c['_id'], 'count': c['count']} for c in categories if c['_id']]


@router.get("/inventory/summary")
async def get_inventory_summary(user: User = Depends(get_admin_user)):
    """Get inventory summary by staff"""
    db = get_db()
    
    # Get all staff with assigned items
    pipeline = [
        {'$match': {'status': 'assigned'}},
        {'$group': {
            '_id': '$assigned_to',
            'staff_name': {'$first': '$assigned_to_name'},
            'item_count': {'$sum': 1},
            'items': {'$push': {'name': '$name', 'category': '$category'}}
        }},
        {'$sort': {'item_count': -1}}
    ]
    
    staff_summary = await db.inventory_items.aggregate(pipeline).to_list(100)
    
    # Get category breakdown
    category_pipeline = [
        {'$group': {'_id': '$category', 'total': {'$sum': 1}, 'assigned': {'$sum': {'$cond': [{'$eq': ['$status', 'assigned']}, 1, 0]}}}},
        {'$sort': {'total': -1}}
    ]
    
    category_summary = await db.inventory_items.aggregate(category_pipeline).to_list(100)
    
    return {
        'by_staff': staff_summary,
        'by_category': [{'category': c['_id'], 'total': c['total'], 'assigned': c['assigned']} for c in category_summary if c['_id']]
    }
