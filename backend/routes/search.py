# Global Search Routes
from fastapi import APIRouter, Depends, Query
from typing import Optional
import re

from .deps import get_db, get_current_user, User

router = APIRouter(tags=["Search"])

@router.get("/search")
async def global_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, le=20),
    user: User = Depends(get_current_user)
):
    """
    Global search across customers, staff, products, databases, and OMSET records.
    Staff can only see their own customers and OMSET records.
    """
    db = get_db()
    
    # Create case-insensitive regex pattern
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    
    results = {
        'customers': [],
        'staff': [],
        'products': [],
        'databases': [],
        'omset_records': [],
        'total': 0
    }
    
    # Search customers (from customer_records)
    customer_query = {
        '$or': [
            {'customer_name': {'$regex': pattern}},
            {'customer_id': {'$regex': pattern}},
            {'whatsapp': {'$regex': pattern}}
        ]
    }
    
    # Staff can only see their assigned customers
    if user.role == 'staff':
        customer_query['assigned_to'] = user.id
    
    customers = await db.customer_records.find(
        customer_query,
        {'_id': 0, 'id': 1, 'customer_name': 1, 'customer_id': 1, 'product_name': 1, 'status': 1, 'whatsapp': 1}
    ).limit(limit).to_list(limit)
    
    results['customers'] = [
        {
            'id': c.get('id') or c.get('customer_id'),
            'name': c.get('customer_name', c.get('customer_id', 'Unknown')),
            'product_name': c.get('product_name', 'Unknown'),
            'status': c.get('status', 'unknown'),
            'whatsapp': c.get('whatsapp', '')
        }
        for c in customers
    ]
    
    # Search staff (admin only)
    if user.role == 'admin':
        staff = await db.users.find(
            {
                '$or': [
                    {'name': {'$regex': pattern}},
                    {'email': {'$regex': pattern}}
                ]
            },
            {'_id': 0, 'id': 1, 'name': 1, 'email': 1, 'role': 1}
        ).limit(limit).to_list(limit)
        
        results['staff'] = [
            {
                'id': s.get('id'),
                'name': s.get('name', 'Unknown'),
                'email': s.get('email', ''),
                'role': s.get('role', 'staff')
            }
            for s in staff
        ]
    
    # Search products
    products = await db.products.find(
        {
            '$or': [
                {'name': {'$regex': pattern}},
                {'category': {'$regex': pattern}}
            ]
        },
        {'_id': 0, 'id': 1, 'name': 1, 'category': 1}
    ).limit(limit).to_list(limit)
    
    results['products'] = [
        {
            'id': p.get('id'),
            'name': p.get('name', 'Unknown'),
            'category': p.get('category', '')
        }
        for p in products
    ]
    
    # Search databases
    databases = await db.databases.find(
        {
            '$or': [
                {'name': {'$regex': pattern}},
                {'product_name': {'$regex': pattern}}
            ]
        },
        {'_id': 0, 'id': 1, 'name': 1, 'product_name': 1, 'total_records': 1}
    ).limit(limit).to_list(limit)
    
    results['databases'] = [
        {
            'id': d.get('id'),
            'name': d.get('name', 'Unknown'),
            'product_name': d.get('product_name', ''),
            'total_records': d.get('total_records', 0)
        }
        for d in databases
    ]
    
    # Search OMSET records
    omset_query = {
        '$or': [
            {'customer_name': {'$regex': pattern}},
            {'customer_id': {'$regex': pattern}},
            {'username': {'$regex': pattern}}
        ]
    }
    
    # Staff can only see their own OMSET records
    if user.role == 'staff':
        omset_query['staff_id'] = user.id
    
    omset_records = await db.omset_records.find(
        omset_query,
        {'_id': 0, 'id': 1, 'customer_name': 1, 'customer_id': 1, 'depo_total': 1, 'record_date': 1, 'product_name': 1}
    ).sort('record_date', -1).limit(limit).to_list(limit)
    
    results['omset_records'] = [
        {
            'id': o.get('id'),
            'customer_name': o.get('customer_name', o.get('customer_id', 'Unknown')),
            'depo_total': o.get('depo_total', 0),
            'record_date': o.get('record_date', ''),
            'product_name': o.get('product_name', '')
        }
        for o in omset_records
    ]
    
    # Calculate total
    results['total'] = (
        len(results['customers']) +
        len(results['staff']) +
        len(results['products']) +
        len(results['databases']) +
        len(results['omset_records'])
    )
    
    return results
