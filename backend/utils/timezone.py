from datetime import datetime, timezone, timedelta

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')
