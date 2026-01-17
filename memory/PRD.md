# CRM Pro - Product Requirements Document

## Original Problem Statement
Build a sophisticated CRM (Customer Relationship Management) application for managing customer records, sales workflows, staff performance tracking, and HR features.

## Core Architecture
- **Frontend**: React with TailwindCSS, Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Authentication**: JWT-based auth with three-tier role system (Master Admin, Admin, Staff)

## Key Features Implemented

### 1. Core CRM Features
- Product Categorization (multiple products)
- Record-Level Assignment
- Reserved Member system with duplicate checking
- Customer Status Tracking (NDP/RDP)

### 2. Sales Workflows
- **OMSET CRM**: Daily deposit tracking with NDP/RDP statistics
- **DB Bonanza**: Bonus database management
- **Member WD**: Member withdrawal management
- Conversion Funnel tracking

### 3. Admin Tooling
- User Management with hierarchical permissions
- Dashboard with overview statistics
- Bulk operations (assign, export)
- Notification system with Telegram integration

### 4. Reporting & Analytics
- Report CRM page
- CRM Bonus Calculation
- Staff Leaderboard with targets
- Advanced Analytics Dashboard

### 5. HR Features
- Leave tracking ("Off Day/Sakit")
- Short Break tracking ("Izin")
- Leave balance management

### 6. UI/UX
- Customizable dark-mode-ready sidebar
- Role-based themes
- Global search
- **FULLY TRANSLATED to Indonesian** for staff panel
- **NEW: Open batch in new tab** for efficient multi-tasking

### 7. Performance Tracking
- Sales funnels
- Customer retention/at-risk alerts
- Daily performance summaries

### 8. Real-time Features
- User activity tracking (Online/Idle/Offline)
- Auto-logout after 1 hour inactivity
- Scheduled daily summary reports via Telegram

## What's Implemented (Latest Session - Jan 2026)

### Follow-up Reminders Filtering - COMPLETED (Jan 17, 2026)
- Added product and database filtering to Follow-up Reminders page
- Backend: New `/api/followups/filters` endpoint returns unique products/databases for staff
- Backend: `/api/followups` now accepts `database_id` parameter in addition to `product_id`
- Frontend: Collapsible filter panel with Product and Database dropdowns
- Frontend: Filter badge shows active filter count
- Frontend: Clear Filter button to reset selections
- Frontend: Database dropdown filters based on selected product
- All filter UI translated to Indonesian

### Indonesian Translation - COMPLETED
All staff-facing components now fully translated to casual Indonesian.

### Open Batch in New Tab Feature - COMPLETED
- Added "Open in New Tab" button to batch cards in "My Assigned Customers"
- Created standalone `/batch/:batchId` route
- New `BatchRecordsView.js` component with full functionality
- Staff can now work on multiple batches simultaneously in different tabs
- Stats summary, search, WhatsApp/Respond status buttons all functional

## Test Credentials
- **Master Admin**: vicky@crm.com / vicky123
- **Admin**: admin@crm.com / admin123
- **Staff**: staff@crm.com / staff123

## Known Issues
- WebSocket connection fails in preview environment (infrastructure limitation)

## Upcoming Tasks (P1)
- Pin Batches - Allow staff to pin important batches to top of list
- Default Language for Staff - Auto-set Indonesian for staff role

## Upcoming Tasks (P2)
- WhatsApp Quick Actions button
- Email Notifications
- Scheduled Reports from Export Center
- CSV Import for Reserved Members

## Future Tasks (P3)
- Quick Actions on Overview
- Financial ROI Tracking
- Izin Analytics
- AI-Powered Suggestions
- User Activity History

## Key API Endpoints
- `GET /auth/session-status` - Check session validity
- `DELETE /notifications` - Bulk delete notifications
- `GET /users/activity` - User activity status (timestamp-based)
- `POST /reserved-members` - Requires phone_number field
- `GET /my-request-batches` - Get user's batch list
- `GET /my-assigned-records-by-batch` - Get records for a specific batch
- `GET /followups/filters` - Get unique products/databases for staff's follow-up filtering
- `GET /followups` - Supports product_id, database_id, and urgency query params

## New Route
- `/batch/:batchId` - Standalone batch view page (opens in new tab)

## Database Collections
- `users` - User accounts with role-based permissions
- `products` - Product categories
- `customer_records` - Main customer database
- `omset_records` - Daily OMSET tracking
- `bonanza_records` - DB Bonanza records
- `member_wd_records` - Member WD records
- `reserved_members` - Reserved member list (with phone_number)
- `leave_requests` - Staff leave tracking
- `izin_records` - Short break tracking
- `notifications` - In-app notifications

## Third Party Integrations
- @dnd-kit/core, @dnd-kit/sortable - Sidebar customization
- xlsx - Excel/CSV export
- recharts - Charts
- pytz - Timezone handling
- python-telegram-bot - Telegram notifications
- APScheduler - Background jobs
- emergentintegrations - Telegram helper

