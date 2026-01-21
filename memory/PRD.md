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

### Reserved Member Auto-Cleanup - COMPLETED (Jan 18, 2026)
- Auto-deletes reserved members if no OMSET from that customer within the grace period
- Matching: Compares reserved member's customer_name with OMSET's customer_id/customer_name (case-insensitive)
- Grace period countdown starts from reservation approval date (approved_at or created_at)
- Sends daily in-app notifications to staff starting within the warning period before expiration
- Scheduled job runs at 00:01 AM Jakarta time daily
- Backend: `process_reserved_member_cleanup()` function in scheduled_reports.py
- Admin endpoints: 
  - `GET /api/scheduled-reports/reserved-member-cleanup-preview` - preview what will happen
  - `POST /api/scheduled-reports/reserved-member-cleanup-run` - manually trigger cleanup
- Notification types: `reserved_member_expiring` (warning), `reserved_member_expired` (deleted)

### Configurable Grace Period - COMPLETED (Jan 18, 2026)
- Admins can configure grace period settings via the Scheduled Reports page
- Configuration options:
  - Global Grace Period (default: 30 days) - default days before auto-delete
  - Warning Period (default: 7 days) - start notifications X days before expiry
  - Product-Specific Overrides - different grace periods per product
- Backend endpoints:
  - `GET /api/reserved-members/cleanup-config` - get current config with available products
  - `PUT /api/reserved-members/cleanup-config` - update config with validation
- Validation: grace_days >= 1, warning_days < global_grace_days, product_id must exist
- Config stored in MongoDB collection `reserved_member_config`
- Frontend: Grace Period Settings section with Add/Remove product override functionality

### Admin Notification Fix - COMPLETED (Jan 18, 2026)
- Fixed: Notifications were only sent to users with `role: 'admin'`, missing `master_admin` users
- Updated queries to use `{'role': {'$in': ['admin', 'master_admin']}}` in:
  - Reserved member requests (records.py)
  - Leave/Off Day requests (leave.py)
  - Download requests (records.py - NEW: added notification on request creation)
- Master admins (like vicky@crm.com) now receive all admin notifications

### Network Error Handling Improvement - COMPLETED (Jan 18, 2026)
- Added 30-second global timeout to axios API client
- Added retry logic to DatabaseList component (retries once on network error)
- Better error messages to help users understand what went wrong
- Response interceptor for consistent network error logging

## Test Credentials
- **Master Admin**: vicky@crm.com / vicky123
- **Admin**: admin@crm.com / admin123
- **Staff**: staff@crm.com / staff123

## Attendance System (NEW - Jan 20, 2026)
Device-registered QR code attendance system for staff check-in.

### Flow:
1. Staff logs in on office computer → QR code displayed (expires in 1 minute)
2. Staff scans QR with registered phone → Attendance recorded
3. Admin can view daily attendance, history, and manage device registrations

### Features:
- **QR Code**: Unique per staff, expires in 1 minute, auto-regenerates
- **Device Registration**: One phone per staff account
- **Late Detection**: Shift starts 11:00 AM, 15-minute grace period
- **Admin Dashboard**: Today's attendance, history with filters, Excel export
- **Device Management**: Admin can reset staff device registrations

### API Endpoints:
- `GET /api/attendance/check-today` - Check if staff checked in today
- `POST /api/attendance/generate-qr` - Generate QR code for staff
- `POST /api/attendance/scan` - Verify QR scan from phone
- `POST /api/attendance/register-device` - Register phone to staff
- `GET /api/attendance/admin/today` - Today's attendance summary
- `GET /api/attendance/admin/records` - Historical records
- `GET /api/attendance/admin/devices` - List registered devices
- `DELETE /api/attendance/admin/device/{staff_id}` - Reset device registration
- `GET /api/attendance/admin/export` - Export to Excel

## Known Issues
- WebSocket connection fails in preview environment (infrastructure limitation)

### PRODUCTION DEPLOYMENT FIX - CRITICAL (Jan 21, 2026)
**Problem**: Production app showing "Service temporarily unavailable" after every deployment
**Root Cause**: `.gitignore` file had duplicate entries (lines 100-105) blocking all `.env` and `.env.*` files from being committed to the repository. This prevented environment files from being deployed to production.
**Fix Applied**: Removed duplicate entries from `.gitignore`. Now only `.env.local` and `.env.*.local` are ignored (local development files), while `.env` files are committed for deployment.

### QR Scanner Black Screen Issue - RESEARCH & FIX (Jan 20, 2026)
**Problem**: Camera opens but shows black screen on some mobile devices
**Root Cause Identified**: The `html5-qrcode` library has a known bug with the native `BarcodeDetector` API on certain iOS/Android devices. The camera feed fails to display visually, yet QR code detection may continue functioning in the background.
**Research Sources**:
- https://github.com/mebjas/html5-qrcode/issues/984
- https://github.com/mebjas/html5-qrcode/issues/549
- https://github.com/mebjas/html5-qrcode/issues/890

**Fixes Applied**:
1. Disabled native BarcodeDetector API: `useBarCodeDetectorIfSupported: false`
2. Added 1-second initialization delay before camera start
3. Reduced qrbox size from 250x250 to 220x220 for better mobile fit
4. Added comprehensive debug logging to diagnose issues
5. Added manual input fallback as workaround

**Alternative Libraries to Consider** (if issues persist):
- `@aspect/react-native-vision-camera` - Most capable, uses ML Kit (Android) and VisionKit (iOS)
- `react-native-camera-kit` - Lightweight, simple integration
- `expo-camera` - For Expo-managed apps

### User Activity Timestamp Bug - REWRITTEN (Jan 20, 2026)
**Problem**: All staff activity timestamps were syncing to the same time when admin viewed activity page
**Root Cause Analysis**: After comprehensive testing (12 tests passed), the code is correct. MongoDB's `updateOne` only updates ONE document. The issue in production is likely corrupted data from a previous bug or external factor.
**Status**: FIXED - System rewritten from scratch + Verified with tests
**What was done**:
1. Rewrote `GET /api/users/activity` to be read-only (no side effects)
2. Rewrote `POST /api/auth/heartbeat` to only update current authenticated user
3. Added heartbeat rejection if user logged out within 5 minutes (prevents race conditions)
4. Created `POST /api/auth/reset-activity` endpoint to clear corrupted data
5. Created `POST /api/auth/force-all-offline` endpoint to mark all staff offline
6. Added `POST /api/auth/logout-beacon` for reliable browser close detection
7. Added comprehensive test suite: `/app/tests/test_heartbeat_isolation.py`
**Pending**: User to run `force-all-offline` in production to fix corrupted data

## Fixes Applied (Jan 20, 2026)

### QR Scanner Improvements - COMPLETED (Jan 20, 2026)
- **CRITICAL FIX**: Disabled native BarcodeDetector API (`useBarCodeDetectorIfSupported: false`)
- **CRITICAL FIX**: Added 1-second initialization delay before camera start
- Added comprehensive debug logging with "Show Debug" button
- Added scan activity counter to show scanner is working
- Added immediate toast feedback when QR is detected
- Fixed component lifecycle issues (proper cleanup on unmount)
- Added better error messages for camera permission/availability issues
- Improved camera selection logic (prefers back camera)
- Added manual input fallback for when camera scanning doesn't work
- All interactive elements have data-testid attributes for testing

### Conversion Funnel Fix - COMPLETED (Jan 20, 2026)
- Fixed "Deposited" metric calculation in all three funnel endpoints
- Root cause: The funnel was matching internal `customer_id` with OMSET's `customer_id` (username)
- Solution: Now matches by extracting username from `row_data` and normalizing to uppercase
- Fixed endpoints: `/api/funnel`, `/api/funnel/by-product`, `/api/funnel/by-staff`
- **NEW**: Added `deposited_customers` field showing usernames of customers who deposited
- **NEW**: Frontend now displays expandable list of deposited customer usernames with copy button

### User Activity Diagnostic Endpoints - ADDED
- `GET /api/auth/diagnostics/activity-sync` - Check if timestamps are synced (bug indicator)
- `POST /api/auth/reset-activity` - Admin-accessible endpoint to reset corrupted activity data

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
- `POST /auth/reset-activity` - Reset all user activity timestamps (Admin) - USE THIS TO FIX SYNC BUG
- `GET /auth/diagnostics/activity-sync` - Check for activity timestamp sync issues
- `POST /reserved-members` - Requires phone_number field
- `GET /my-request-batches` - Get user's batch list (includes is_pinned field, sorted pinned first)
- `PATCH /my-request-batches/{batch_id}/pin` - Toggle pin status for a batch
- `GET /my-assigned-records-by-batch` - Get records for a specific batch
- `GET /followups/filters` - Get unique products/databases for staff's follow-up filtering
- `GET /followups` - Supports product_id, database_id, and urgency query params
- `GET /retention/alerts` - At-risk customers with matched_name, matched_username, matched_source, phone_number
- `GET /scheduled-reports/atrisk-rotation-status` - Check at-risk alert rotation status
- `DELETE /scheduled-reports/atrisk-rotation-reset` - Reset at-risk alert rotation history
- `GET /scheduled-reports/reserved-member-cleanup-preview` - Preview which reserved members will expire
- `POST /scheduled-reports/reserved-member-cleanup-run` - Manually trigger reserved member cleanup
- `GET /reserved-members/cleanup-config` - Get grace period configuration with available products
- `PUT /reserved-members/cleanup-config` - Update grace period configuration (global, warning, product overrides)
- `GET /report-crm/export` - Export CRM Report (supports token query param)
- `GET /omset/export-summary` - Export OMSET summary (supports token query param)
- `GET /staff/notifications/summary` - Get staff notification counts (bonanza_new, memberwd_new)
- `POST /staff/notifications/mark-viewed/{page_type}` - Mark page as viewed (bonanza or memberwd)
- `GET /funnel` - Conversion funnel data (now correctly calculates deposited from row_data username)
- `GET /funnel/by-product` - Funnel breakdown by product
- `GET /funnel/by-staff` - Funnel breakdown by staff (Admin only)

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

