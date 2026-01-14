# Routes package initialization
from .deps import set_database, get_db

# Import all routers
from .auth import router as auth_router
from .leave import router as leave_router
from .notifications import router as notifications_router
from .bulk import router as bulk_router
from .products import router as products_router
from .analytics import router as analytics_router
from .izin import router as izin_router
from .bonanza import router as bonanza_router
from .memberwd import router as memberwd_router
from .omset import router as omset_router
from .report import router as report_router
from .bonus import router as bonus_router
from .records import router as records_router
from .leaderboard import router as leaderboard_router

__all__ = [
    'set_database', 
    'get_db',
    'auth_router',
    'leave_router',
    'notifications_router',
    'bulk_router',
    'products_router',
    'analytics_router',
    'izin_router',
    'bonanza_router',
    'memberwd_router',
    'omset_router',
    'report_router',
    'bonus_router',
    'records_router',
    'leaderboard_router'
]
