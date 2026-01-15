from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ==================== CONFIGURATION ====================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Jakarta timezone (UTC+7)
JAKARTA_TZ = timezone(timedelta(hours=7))

def get_jakarta_now():
    """Get current datetime in Jakarta timezone"""
    return datetime.now(JAKARTA_TZ)

def get_jakarta_date_string():
    """Get current date string in Jakarta timezone (YYYY-MM-DD)"""
    return get_jakarta_now().strftime('%Y-%m-%d')

# Database connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# App initialization
app = FastAPI(title="CRM Pro API", version="3.0.0")  # Major version for fully modular architecture
api_router = APIRouter(prefix="/api")

# ==================== INITIALIZE MODULAR ROUTES ====================

from routes.deps import set_database
from routes.izin import router as izin_router
from routes.bonanza import router as bonanza_router
from routes.memberwd import router as memberwd_router
from routes.omset import router as omset_router
from routes.report import router as report_router
from routes.bonus import router as bonus_router
from routes.records import router as records_router
from routes.auth import router as auth_router
from routes.leave import router as leave_router
from routes.notifications import router as notifications_router
from routes.bulk import router as bulk_router
from routes.products import router as products_router
from routes.analytics import router as analytics_router
from routes.leaderboard import router as leaderboard_router
from routes.followup import router as followup_router
from routes.daily_summary import router as daily_summary_router
from routes.funnel import router as funnel_router
from routes.retention import router as retention_router
from routes.search import router as search_router
from routes.websocket import router as websocket_router
from routes.scheduled_reports import router as scheduled_reports_router, init_scheduler

# Initialize database connection for all route modules
set_database(db)

# Register all modular routes
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(records_router)
api_router.include_router(omset_router)
api_router.include_router(report_router)
api_router.include_router(bonus_router)
api_router.include_router(leave_router)
api_router.include_router(izin_router)
api_router.include_router(bonanza_router)
api_router.include_router(memberwd_router)
api_router.include_router(notifications_router)
api_router.include_router(bulk_router)
api_router.include_router(analytics_router)
api_router.include_router(leaderboard_router)
api_router.include_router(followup_router)
api_router.include_router(daily_summary_router)
api_router.include_router(funnel_router)
api_router.include_router(retention_router)
api_router.include_router(search_router)
api_router.include_router(scheduled_reports_router)
# WebSocket routes are added at the app level (not under /api)
app.include_router(websocket_router)

# ==================== CORE ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes"""
    return {"status": "healthy", "service": "crm-pro-api"}

@api_router.get("/server-time")
async def get_server_time():
    """Get current server time in Jakarta timezone"""
    jakarta_now = get_jakarta_now()
    return {
        'timezone': 'Asia/Jakarta (UTC+7)',
        'datetime': jakarta_now.isoformat(),
        'date': jakarta_now.strftime('%Y-%m-%d'),
        'time': jakarta_now.strftime('%H:%M:%S'),
        'formatted': jakarta_now.strftime('%A, %d %B %Y %H:%M:%S WIB')
    }

# ==================== APP SETUP ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
