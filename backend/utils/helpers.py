"""
Shared utility functions for CRM backend.
Centralizes common operations to avoid code duplication.
"""

from datetime import datetime, timezone, timedelta
import re
from typing import Optional

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))


def get_jakarta_now() -> datetime:
    """Get current datetime in Jakarta timezone (UTC+7)."""
    return datetime.now(JAKARTA_TZ)


def get_jakarta_date_string() -> str:
    """Get current date string in Jakarta timezone (YYYY-MM-DD format)."""
    return get_jakarta_now().strftime('%Y-%m-%d')


def get_jakarta_datetime_string() -> str:
    """Get current datetime string in Jakarta timezone (ISO format)."""
    return get_jakarta_now().isoformat()


def normalize_customer_id(customer_id: str) -> str:
    """
    Normalize customer ID for consistent comparison.
    - Converts to lowercase
    - Strips whitespace
    - Removes special characters except alphanumeric and hyphens
    
    Args:
        customer_id: Raw customer ID string
        
    Returns:
        Normalized customer ID string, or empty string if input is None/empty
    """
    if not customer_id:
        return ''
    # Convert to lowercase, strip whitespace
    normalized = str(customer_id).lower().strip()
    # Remove special characters except alphanumeric, hyphens, underscores
    normalized = re.sub(r'[^a-z0-9\-_]', '', normalized)
    return normalized


def normalize_name(name: str) -> Optional[str]:
    """
    Normalize a name for consistent comparison.
    - Converts to lowercase
    - Strips whitespace
    
    Args:
        name: Raw name string
        
    Returns:
        Normalized name string, or None if input is None/empty
    """
    if not name:
        return None
    return str(name).lower().strip()


def parse_date_string(date_str: str, default: Optional[str] = None) -> Optional[str]:
    """
    Parse and validate a date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to parse
        default: Default value if date_str is invalid
        
    Returns:
        Valid date string in YYYY-MM-DD format, or default
    """
    if not date_str:
        return default or get_jakarta_date_string()
    try:
        # Validate format
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        return default or get_jakarta_date_string()


def format_currency(amount: float, currency: str = 'IDR') -> str:
    """
    Format a number as currency string.
    
    Args:
        amount: Amount to format
        currency: Currency code (default: IDR)
        
    Returns:
        Formatted currency string
    """
    if currency == 'IDR':
        return f"Rp {amount:,.0f}"
    return f"{currency} {amount:,.2f}"


def safe_int(value, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def extract_customer_info(record: dict) -> dict:
    """
    Extract and normalize customer information from a record.
    
    Args:
        record: Record dictionary with customer data
        
    Returns:
        Dictionary with normalized customer_id and customer_name
    """
    row_data = record.get('row_data', {})
    
    # Try common field names for customer ID
    customer_id = None
    for field in ['customer_id', 'id_customer', 'user_id', 'username', 'id']:
        if field in row_data and row_data[field]:
            customer_id = str(row_data[field])
            break
    
    # Try common field names for customer name
    customer_name = None
    for field in ['customer_name', 'name', 'nama', 'full_name']:
        if field in row_data and row_data[field]:
            customer_name = str(row_data[field])
            break
    
    return {
        'customer_id': customer_id,
        'customer_id_normalized': normalize_customer_id(customer_id) if customer_id else None,
        'customer_name': customer_name
    }
