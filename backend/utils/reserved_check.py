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


async def sync_reserved_status_on_add(db, customer_id: str, customer_name: str, staff_id: str, staff_name: str):
    """
    When a reservation is APPROVED, mark matching available records as 'reserved'
    in both memberwd_records and bonanza_records.
    """
    identifiers = set()
    if customer_id and str(customer_id).strip():
        identifiers.add(str(customer_id).strip().upper())
    if customer_name and str(customer_name).strip():
        identifiers.add(str(customer_name).strip().upper())
    if not identifiers:
        return 0

    total_updated = 0
    for collection_name in ['memberwd_records', 'bonanza_records']:
        records = await db[collection_name].find(
            {'status': 'available'},
            {'_id': 0, 'id': 1, 'row_data': 1}
        ).to_list(None)

        ids_to_reserve = []
        for record in records:
            row_data = record.get('row_data', {})
            for value in row_data.values():
                if value and str(value).strip().upper() in identifiers:
                    ids_to_reserve.append(record['id'])
                    break

        if ids_to_reserve:
            await db[collection_name].update_many(
                {'id': {'$in': ids_to_reserve}},
                {'$set': {
                    'status': 'reserved',
                    'is_reserved_member': True,
                    'reserved_by': staff_id,
                    'reserved_by_name': staff_name,
                }}
            )
            total_updated += len(ids_to_reserve)

    return total_updated


async def sync_reserved_status_on_remove(db, customer_id: str, customer_name: str):
    """
    When a reservation is DELETED/EXPIRED, check if ANY other active reservation
    still covers this customer. If not, revert matching 'reserved' records back to 'available'.
    """
    identifiers = set()
    if customer_id and str(customer_id).strip():
        identifiers.add(str(customer_id).strip().upper())
    if customer_name and str(customer_name).strip():
        identifiers.add(str(customer_name).strip().upper())
    if not identifiers:
        return 0

    # Check if any OTHER active reservation still covers this customer
    all_reserved = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1}
    ).to_list(None)

    still_reserved = build_reserved_set(all_reserved)

    # If any of this customer's identifiers are still in the active set, don't unreserve
    if identifiers & still_reserved:
        return 0

    total_updated = 0
    for collection_name in ['memberwd_records', 'bonanza_records']:
        records = await db[collection_name].find(
            {'status': 'reserved'},
            {'_id': 0, 'id': 1, 'row_data': 1}
        ).to_list(None)

        ids_to_unreserve = []
        for record in records:
            row_data = record.get('row_data', {})
            for value in row_data.values():
                if value and str(value).strip().upper() in identifiers:
                    ids_to_unreserve.append(record['id'])
                    break

        if ids_to_unreserve:
            await db[collection_name].update_many(
                {'id': {'$in': ids_to_unreserve}},
                {'$set': {
                    'status': 'available',
                    'is_reserved_member': False,
                    'reserved_by': None,
                    'reserved_by_name': None,
                }}
            )
            total_updated += len(ids_to_unreserve)

    return total_updated


async def sync_all_reserved_statuses(db):
    """
    Full resync: scan ALL available+reserved records and correct their status
    based on the current set of active reservations. Used for migration/repair.
    """
    reserved_members = await db.reserved_members.find(
        {'status': 'approved'},
        {'_id': 0, 'customer_id': 1, 'customer_name': 1, 'staff_id': 1, 'staff_name': 1}
    ).to_list(None)

    reserved_set = build_reserved_set(reserved_members)
    reserved_map = build_reserved_map(reserved_members)

    total_marked_reserved = 0
    total_marked_available = 0

    for collection_name in ['memberwd_records', 'bonanza_records']:
        # Mark available -> reserved
        avail_records = await db[collection_name].find(
            {'status': 'available'},
            {'_id': 0, 'id': 1, 'row_data': 1}
        ).to_list(None)

        to_reserve = []
        reserve_info = {}
        for record in avail_records:
            row_data = record.get('row_data', {})
            for value in row_data.values():
                if value and str(value).strip():
                    normalized = str(value).strip().upper()
                    if normalized in reserved_map:
                        to_reserve.append(record['id'])
                        reserve_info[record['id']] = reserved_map[normalized]
                        break

        for rid in to_reserve:
            info = reserve_info[rid]
            await db[collection_name].update_one(
                {'id': rid},
                {'$set': {
                    'status': 'reserved',
                    'is_reserved_member': True,
                    'reserved_by': info['staff_id'],
                    'reserved_by_name': info['staff_name'],
                }}
            )
        total_marked_reserved += len(to_reserve)

        # Mark reserved -> available (if no longer reserved)
        res_records = await db[collection_name].find(
            {'status': 'reserved'},
            {'_id': 0, 'id': 1, 'row_data': 1}
        ).to_list(None)

        to_unreserve = []
        for record in res_records:
            if not is_record_reserved(record, reserved_set):
                to_unreserve.append(record['id'])

        if to_unreserve:
            await db[collection_name].update_many(
                {'id': {'$in': to_unreserve}},
                {'$set': {
                    'status': 'available',
                    'is_reserved_member': False,
                    'reserved_by': None,
                    'reserved_by_name': None,
                }}
            )
        total_marked_available += len(to_unreserve)

    return {
        'marked_reserved': total_marked_reserved,
        'marked_available': total_marked_available,
    }
