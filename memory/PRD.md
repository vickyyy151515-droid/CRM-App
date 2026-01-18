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
- Fixed Monitor Izin admin translations (Jan 17, 2026)

### 7. Performance Tracking
- Sales funnels
- Customer retention/at-risk alerts
- Daily performance summaries

### 8. Real-time Features
- User activity tracking (Online/Idle/Offline)
- Auto-logout after 1 hour inactivity
- Scheduled daily summary reports via Telegram

## What's Implemented (Latest Session - Jan 2026)

### At-Risk Customer Database Matching - COMPLETED (Jan 17, 2026)
- At-risk customers now checked against 3 databases: Uploaded Database, DB Bonanza, Member WD CRM
- When match found, displays: Username, Name, WhatsApp phone number
- Copy buttons for username, name, and phone number
- Direct WhatsApp link button
- Source badge showing which database matched

### At-Risk Alert 3-Day Rotation - COMPLETED (Jan 17, 2026)
- At-risk customers now rotate on 3-day interval (same customer won't appear for 3 days after being shown)
- New collection `atrisk_alert_history` tracks alerted customers
- New endpoints: `/api/scheduled-reports/atrisk-rotation-status` and `/api/scheduled-reports/atrisk-rotation-reset`
- Auto-cleanup of history records older than 7 days

### Export Bug Fixes - COMPLETED (Jan 17, 2026)
- Fixed "Export Summary" button in OMSET CRM (changed to fetch+blob approach)
- Fixed "Export Excel" button in CRM Report (added token auth via query params)
- Renamed "Report CRM" to "CRM Report" throughout the app

### Staff Progress - Ceklis 1 Count - COMPLETED (Jan 17, 2026)
- Added "Ceklis 1" count to Overall Statistics cards
- Added "Ceklis 1" to Period Performance banner
- Added "Ceklis 1" to Staff Performance cards (4-column grid)
- Updated WhatsApp check progress calculation to include Ceklis 1

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

### Staff Notification Indicators - COMPLETED (Jan 18, 2026)
- Added notification badges on sidebar for "DB Bonanza" and "Member WD CRM" menu items
- Red badge shows count of newly assigned records since last view
- Badge count resets to 0 when staff navigates to the respective page
- Backend: New `/api/staff/notifications/summary` endpoint returns bonanza_new and memberwd_new counts
- Backend: New `/api/staff/notifications/mark-viewed/{page_type}` endpoint updates last viewed timestamp
- New MongoDB collection: `staff_last_viewed` tracks when staff last viewed each page
- Frontend: `StaffDashboard.js` fetches counts and passes badge prop to menuItems

### Dark Mode Fixes for DB Bonanza & Member WD CRM - COMPLETED (Jan 18, 2026)
- Fixed all text visibility issues in `StaffDBBonanza.js` and `StaffMemberWDCRM.js`
- Added proper dark mode classes: dark:bg-slate-800, dark:text-white, dark:text-slate-300
- Fixed gradient headers: dark:from-indigo-900/30 dark:to-purple-900/30
- Fixed table headers, borders, and hover states for dark mode
- Fixed input fields and select dropdowns with proper dark backgrounds

### Pin Batches Feature - COMPLETED (Jan 18, 2026)
- Added pin button on batch cards in "My Assigned Customers" page
- Pinned batches show yellow border/ring effect and pin icon in top-right corner
- Pinned batches sorted to top of the list automatically
- Backend: New `PATCH /api/my-request-batches/{batch_id}/pin` endpoint to toggle pin status
- Backend: Modified `GET /api/my-request-batches` to include `is_pinned` field and sort pinned first
- Works for both regular batches (stored in download_requests) and legacy batches (stored in batch_titles)
- Translations added for pin/unpin actions in both English and Indonesian

### Default Language for Staff - COMPLETED (Jan 18, 2026)
- Staff users automatically get Indonesian language on first login
- Uses `language_preference_set` localStorage key to track if user has manually changed language
- If user manually toggles language, their preference is preserved and auto-switch is skipped
- Frontend: `LanguageContext.js` has `setDefaultLanguageForRole` function
- Frontend: `StaffDashboard.js` calls this function when staff user logs in

## Test Credentials
- **Master Admin**: vicky@crm.com / vicky123
- **Admin**: admin@crm.com / admin123
- **Staff**: staff@crm.com / staff123

## Known Issues
- WebSocket connection fails in preview environment (infrastructure limitation)

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
- `GET /retention/alerts` - At-risk customers with matched_name, matched_username, matched_source, phone_number
- `GET /scheduled-reports/atrisk-rotation-status` - Check at-risk alert rotation status
- `DELETE /scheduled-reports/atrisk-rotation-reset` - Reset at-risk alert rotation history
- `GET /report-crm/export` - Export CRM Report (supports token query param)
- `GET /omset/export-summary` - Export OMSET summary (supports token query param)
- `GET /staff/notifications/summary` - Get staff notification counts (bonanza_new, memberwd_new)
- `POST /staff/notifications/mark-viewed/{page_type}` - Mark page as viewed (bonanza or memberwd)

## New Route
- `/batch/:batchId` - Standalone batch view page (opens in new tab)

## Database Collections
- `users` - User accounts with role-based permissions
- `products` - Product categories
- `customer_records` - Main customer database
- `omset_records` - Daily OMSET tracking
- `bonanza_records` - DB Bonanza records
- `memberwd_records` - Member WD records
- `reserved_members` - Reserved member list (with phone_number)
- `leave_requests` - Staff leave tracking
- `izin_records` - Short break tracking
- `notifications` - In-app notifications
- `atrisk_alert_history` - Tracks at-risk customers shown in alerts (for 3-day rotation)
- `staff_last_viewed` - Tracks when staff last viewed DB Bonanza/Member WD pages (for notification badges)

## Third Party Integrations
- @dnd-kit/core, @dnd-kit/sortable - Sidebar customization
- xlsx - Excel/CSV export
- recharts - Charts
- pytz - Timezone handling
- python-telegram-bot - Telegram notifications
- APScheduler - Background jobs
- emergentintegrations - Telegram helper

