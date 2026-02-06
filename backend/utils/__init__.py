"""
Shared utilities package for CRM backend.
Import commonly used functions from here.
"""

from .helpers import (
    # Timezone utilities
    JAKARTA_TZ,
    get_jakarta_now,
    get_jakarta_date_string,
    get_jakarta_datetime_string,
    
    # Customer utilities
    normalize_customer_id,
    normalize_name,
    extract_customer_info,
    
    # Data parsing utilities
    parse_date_string,
    safe_int,
    safe_float,
    format_currency,
)

from .records_helpers import (
    invalidate_customer_records_for_other_staff,
    parse_file_to_records,
    extract_customer_id_from_record,
    extract_customer_name_from_record,
    get_available_records_count,
    get_assigned_records_count,
)

__all__ = [
    # From helpers
    'JAKARTA_TZ',
    'get_jakarta_now',
    'get_jakarta_date_string',
    'get_jakarta_datetime_string',
    'normalize_customer_id',
    'normalize_name',
    'extract_customer_info',
    'parse_date_string',
    'safe_int',
    'safe_float',
    'format_currency',
    # From records_helpers
    'invalidate_customer_records_for_other_staff',
    'parse_file_to_records',
    'extract_customer_id_from_record',
    'extract_customer_name_from_record',
    'get_available_records_count',
    'get_assigned_records_count',
]
