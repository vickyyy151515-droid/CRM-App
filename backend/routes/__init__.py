# Routes package initialization
from .deps import set_database, get_db

# Import all routers
from .auth import router as auth_router
from .leave import router as leave_router
from .notifications import router as notifications_router
from .bulk import router as bulk_router
from .products import router as products_router
from .analytics import router as analytics_router

__all__ = [
    'set_database', 
    'get_db',
    'auth_router',
    'leave_router',
    'notifications_router',
    'bulk_router',
    'products_router',
    'analytics_router'
]
