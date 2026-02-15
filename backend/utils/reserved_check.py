"""
Centralized Reserved Member Checking Utility
=============================================
This is the SINGLE SOURCE OF TRUTH for all reserved member checks.
Every code path that needs to check if a record/customer is reserved MUST use these functions.

CRITICAL DESIGN DECISIONS:
1. We add BOTH customer_id AND customer_name to the reserved set.
   A reserved member may have different values in these fields, and the uploaded
   Excel/CSV may match either one. Using only one (via `or`) was the ROOT CAUSE
   of the recurring bug where reserved customers could be assigned to wrong staff.

2. We check ALL row_data values (field-agnostic). The uploaded file may use any
   column name (Username, NAMA, user, etc.), so we cannot rely on specific field names.

3. We normalize to UPPERCASE and strip whitespace for consistent comparison.
"""


def build_reserved_set(reserved_members: list) -> set:
    """
    Build a set of ALL normalized customer identifiers from reserved members.
    
    IMPORTANT: Adds BOTH customer_id AND customer_name for each member.
    This ensures we catch matches regardless of which field the uploaded data uses.
    
    Args:
        reserved_members: List of reserved member dicts from DB query
        
    Returns:
        Set of normalized (uppercase, stripped) customer identifiers
    """
    reserved = set()
    for m in reserved_members:
        cid = m.get('customer_id')
        if cid and str(cid).strip():
            reserved.add(str(cid).strip().upper())
        cname = m.get('customer_name')
        if cname and str(cname).strip():
            reserved.add(str(cname).strip().upper())
    return reserved


def build_reserved_map(reserved_members: list) -> dict:
    """
    Build a map of normalized customer identifiers -> staff info.
    
    IMPORTANT: Maps BOTH customer_id AND customer_name for each member.
    This ensures we catch matches regardless of which field the uploaded data uses.
    
    Args:
        reserved_members: List of reserved member dicts from DB query
        
    Returns:
        Dict mapping normalized identifier -> {'staff_id': ..., 'staff_name': ...}
    """
    reserved = {}
    for m in reserved_members:
        staff_info = {
            'staff_id': m.get('staff_id'),
            'staff_name': m.get('staff_name', 'Unknown')
        }
        cid = m.get('customer_id')
        if cid and str(cid).strip():
            reserved[str(cid).strip().upper()] = staff_info
        cname = m.get('customer_name')
        if cname and str(cname).strip():
            reserved[str(cname).strip().upper()] = staff_info
    return reserved


def is_record_reserved(record: dict, reserved_set: set) -> bool:
    """
    Check if a record matches any reserved customer.
    
    Performs TWO checks:
    1. Upload-time flag (is_reserved_member) - set when database was uploaded
    2. Runtime check - compares ALL row_data values against the reserved set
    
    The runtime check is essential because:
    - New reservations may have been created after the database was uploaded
    - The upload-time flag may have been set incorrectly
    
    Args:
        record: The record dict with 'row_data' and optional 'is_reserved_member'
        reserved_set: Set of normalized customer identifiers (from build_reserved_set)
        
    Returns:
        True if the record matches a reserved customer
    """
    if record.get('is_reserved_member'):
        return True
    
    row_data = record.get('row_data', {})
    for value in row_data.values():
        if value and str(value).strip():
            if str(value).strip().upper() in reserved_set:
                return True
    return False


def find_reservation_owner(record: dict, reserved_map: dict):
    """
    Check if a record is reserved and return who reserved it.
    
    Args:
        record: The record dict with 'row_data' and optional 'is_reserved_member'
        reserved_map: Dict from build_reserved_map()
        
    Returns:
        (True, staff_name) if reserved, (False, None) if not
    """
    if record.get('is_reserved_member'):
        return True, record.get('reserved_by_name', 'Another staff')
    
    row_data = record.get('row_data', {})
    for value in row_data.values():
        if value and str(value).strip():
            normalized = str(value).strip().upper()
            if normalized in reserved_map:
                return True, reserved_map[normalized].get('staff_name', 'Another staff')
    return False, None
