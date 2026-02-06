"""
Records Helper Functions
Common utilities for records management across all modules (Normal DB, Bonanza, MemberWD)
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd
import os

from utils.helpers import get_jakarta_now, normalize_customer_id


async def invalidate_customer_records_for_other_staff(
    db, 
    customer_id: str, 
    reserved_by_staff_id: str, 
    reserved_by_staff_name: str,
    product_id: str = None,
    module: str = 'records'  # 'records', 'bonanza', or 'memberwd'
) -> Dict[str, Any]:
    """
    When a customer is reserved by a staff member, invalidate all records 
    for that customer assigned to OTHER staff members.
    
    IMPORTANT: Only invalidates records with the SAME product_id to avoid
    cross-product invalidation issues.
    
    Args:
        db: Database connection
        customer_id: The customer ID to check
        reserved_by_staff_id: The staff member who is reserving
        reserved_by_staff_name: Name of the staff member
        product_id: The product ID - records with different products are NOT invalidated
        module: Which module ('records', 'bonanza', 'memberwd')
        
    Returns:
        Dict with invalidation results
    """
    if not customer_id or not product_id:
        return {'invalidated_count': 0, 'affected_staff': []}
    
    # Normalize customer ID for consistent matching
    customer_id_normalized = normalize_customer_id(customer_id)
    
    # Determine collection based on module
    collection_name = {
        'records': 'customer_records',
        'bonanza': 'bonanza_records',
        'memberwd': 'memberwd_records'
    }.get(module, 'customer_records')
    
    collection = db[collection_name]
    
    # Build query - MUST match both customer AND product
    query = {
        '$or': [
            {'customer_id': customer_id},
            {'customer_id_normalized': customer_id_normalized}
        ],
        'product_id': product_id,  # Critical: only same product
        'staff_id': {'$ne': reserved_by_staff_id},  # Different staff
        'status': 'assigned'  # Only currently assigned records
    }
    
    # Find affected records
    affected_records = await collection.find(query).to_list(None)
    
    if not affected_records:
        return {'invalidated_count': 0, 'affected_staff': []}
    
    # Track affected staff for notification
    affected_staff = {}
    invalidated_ids = []
    
    for record in affected_records:
        staff_id = record.get('staff_id')
        staff_name = record.get('staff_name', 'Unknown')
        
        if staff_id not in affected_staff:
            affected_staff[staff_id] = {
                'staff_name': staff_name,
                'records': []
            }
        affected_staff[staff_id]['records'].append(record.get('id'))
        invalidated_ids.append(record.get('id'))
    
    # Update records to invalid status
    if invalidated_ids:
        now = get_jakarta_now().isoformat()
        await collection.update_many(
            {'id': {'$in': invalidated_ids}},
            {
                '$set': {
                    'status': 'invalid',
                    'invalid_reason': f'Customer reserved by {reserved_by_staff_name}',
                    'invalidated_at': now,
                    'invalidated_by_reservation': True
                }
            }
        )
    
    return {
        'invalidated_count': len(invalidated_ids),
        'affected_staff': [
            {
                'staff_id': sid,
                'staff_name': info['staff_name'],
                'records_count': len(info['records'])
            }
            for sid, info in affected_staff.items()
        ]
    }


def parse_file_to_records(file_path: str, file_type: str) -> tuple:
    """
    Parse uploaded CSV/Excel file into records.
    
    Args:
        file_path: Path to the uploaded file
        file_type: File extension (csv, xlsx, xls)
        
    Returns:
        Tuple of (columns list, records list of dicts)
    """
    try:
        if file_type == 'csv':
            df = pd.read_csv(file_path, dtype=str)
        else:
            df = pd.read_excel(file_path, dtype=str)
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Convert to records
        columns = df.columns.tolist()
        records = df.fillna('').to_dict('records')
        
        return columns, records
    except Exception as e:
        raise ValueError(f"Failed to parse file: {str(e)}")


def extract_customer_id_from_record(row_data: dict) -> tuple:
    """
    Extract customer ID from record row data.
    Tries common field names.
    
    Args:
        row_data: Dictionary of row data from uploaded file
        
    Returns:
        Tuple of (customer_id, customer_id_normalized)
    """
    customer_id = None
    
    # Try common field names (case-insensitive)
    id_fields = ['customer_id', 'id_customer', 'user_id', 'username', 'id', 'member_id', 'no_member']
    
    for key, value in row_data.items():
        if key.lower().replace(' ', '_') in id_fields and value:
            customer_id = str(value).strip()
            break
    
    customer_id_normalized = normalize_customer_id(customer_id) if customer_id else None
    
    return customer_id, customer_id_normalized


def extract_customer_name_from_record(row_data: dict) -> Optional[str]:
    """
    Extract customer name from record row data.
    
    Args:
        row_data: Dictionary of row data
        
    Returns:
        Customer name or None
    """
    name_fields = ['customer_name', 'name', 'nama', 'full_name', 'nama_lengkap']
    
    for key, value in row_data.items():
        if key.lower().replace(' ', '_') in name_fields and value:
            return str(value).strip()
    
    return None


async def get_available_records_count(db, database_id: str, collection_name: str = 'customer_records') -> int:
    """
    Get count of available (unassigned) records in a database.
    
    Args:
        db: Database connection
        database_id: Database ID
        collection_name: Collection to query
        
    Returns:
        Count of available records
    """
    return await db[collection_name].count_documents({
        'database_id': database_id,
        'status': 'available'
    })


async def get_assigned_records_count(db, database_id: str, collection_name: str = 'customer_records') -> int:
    """
    Get count of assigned records in a database.
    
    Args:
        db: Database connection
        database_id: Database ID
        collection_name: Collection to query
        
    Returns:
        Count of assigned records
    """
    return await db[collection_name].count_documents({
        'database_id': database_id,
        'status': 'assigned'
    })
