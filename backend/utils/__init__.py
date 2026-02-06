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

__all__ = [
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
]
