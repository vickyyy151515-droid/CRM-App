# CRM Application - Product Requirements Document

## Original Problem Statement
Build a Customer Relationship Management (CRM) application where:
- Admins can upload customer databases (CSV or Excel)
- Staff can request to download/access the uploaded databases
- System manages customer record assignments and reservations

## User Personas
1. **Admin**: Manages databases, products, users, approves requests, views analytics
2. **Staff**: Browses databases, requests records, contacts customers via WhatsApp, marks reachability status

## Core Features Implemented

### Phase 1: MVP (Completed)
- User authentication (Admin/Staff roles)
- Database upload (CSV/Excel) with product categorization
- Staff download request workflow with admin approval

### Phase 2: Record-Level Assignment (Completed)
- Shifted from file downloads to individual record assignments
- Staff requests quantity of records from a database
- Admin approves → records get assigned to staff
- Staff sees assigned customers with WhatsApp contact capability

### Phase 3: WhatsApp Integration (Completed)
- Copy full WhatsApp URL button (bypasses network blocks)
- WhatsApp reachability status tracking (Ada/Tidak/Ceklis1)
- **Response status tracking (Ya/Tidak)** - track if customer responded
- Staff marks customer WhatsApp status and response status
- Admin sees all statuses in dashboards

### Phase 4: Admin Dashboards (Completed)
- **All Assignments View**: Global view of all assigned records
- **Staff Progress & Quality**: Analytics dashboard with filters (Today, All Time, etc.)
- Performance metrics: records checked, quality rate

### Phase 5: Reserved Member CRM (Completed - Jan 13, 2026)
- **Staff Request Flow**: Staff requests customer name + selects product → pending → admin approval
- **Admin Direct Add**: Admin assigns customer to staff with product selection (auto-approved)
- **Product Categorization**: Each reservation belongs to a specific product
- **Duplicate Prevention**: Case-insensitive check within same product, shows which staff owns the name
- **Admin Controls**: Approve/Reject requests, Move reservations, Delete
- **Visibility**: All approved reservations visible to all staff
- **Filtering**: Filter by product and status (All/Pending/Approved)
- **Notification Badges**: Red badges in sidebar showing pending counts (auto-refresh every 30s)

### Phase 6: OMSET CRM (Completed - Jan 13, 2026)
- **Staff Data Entry**: Staff can add customer deposits with:
  - Customer Name and ID (manual entry)
  - Nominal amount and Kelipatan (multiplier)
  - Auto-calculated Depo Total (Nominal × Kelipatan)
  - Keterangan (notes)
- **Product Separation**: Each deposit is linked to a specific product
- **Date-based Sheets**: Records organized by date with quick date selector
- **Edit/Delete**: Staff can modify their own records
- **Admin Summary View**: 
  - Overall totals (Records, Nominal, OMSET)
  - Daily summary with OMSET per day
  - Staff performance breakdown
  - Product summary with averages
- **Admin Detail View**: Expandable daily records with full details
- **Filters**: Date range (Today/Yesterday/Last 7/30 days/Custom), Product, Staff

### Phase 7: Batch System (Completed - Jan 13, 2026)
- **Batch-based Record Grouping**: Staff's assigned customers organized into selectable "batches"
- **Legacy Batch**: Records assigned before this feature grouped into "Legacy" batch
- **Live Stats**: Batch cards display WhatsApp status (Ada, Ceklis 1, Tidak) and Respond status (Ya, Tidak) counts
- **Custom Titles**: Staff can set custom titles for each batch

### Phase 8: DB Bonanza & Member WD CRM (Completed - Jan 13, 2026)
- **Admin Upload**: Upload CSV/Excel files with product selection
- **Product Categorization**: Each database linked to a specific product
- **Quick Random Assignment**: Assign random records to staff, excluding reserved members
- **Manual Selection**: Admin can manually select and assign specific records
- **Staff View**: Staff see their assigned records grouped by database with product filtering
- **Separate Collections**: DB Bonanza and Member WD CRM operate on separate MongoDB collections

### Phase 9: Product Selection for DB Bonanza & Member WD CRM (Completed - Jan 13, 2026)
- **Admin Upload with Product**: Product selection required when uploading new databases
- **Product Filter for Admin**: Filter databases by product in admin view
- **Product Filter for Staff**: Filter assigned records by product in staff view
- **Legacy Data Handling**: Databases without product show "Unknown" as product name

### Phase 10: Bulk Operations (Completed - Jan 13, 2026)
- **Bulk Approve/Reject**: Admin can select multiple download requests and approve/reject them all at once
- **Bulk Delete Records**: Admin can select and delete multiple records in DB Bonanza and Member WD CRM
- **Bulk Status Update**: Endpoint available for bulk updating WhatsApp/Respond status
- **Selection UI**: Checkboxes on records/requests with Select All/Clear buttons

### Phase 11: Mobile Responsive Design (Completed - Jan 13, 2026)
- **Collapsible Sidebar**: Hamburger menu on screens < 1024px width
- **Slide-in Animation**: Smooth sidebar slide-in with dark overlay
- **Mobile Header**: Shows hamburger menu, CRM Pro title, and notification bell
- **Touch-friendly**: All buttons and controls sized for touch interaction
- **Responsive Forms**: Forms stack vertically on mobile
- **Desktop Collapse** (Enhanced - Jan 14, 2026):
  - Toggle button on sidebar edge to collapse/expand
  - Collapsed mode shows only icons with "C" logo
  - Hover tooltips show menu labels when collapsed
  - State persisted in localStorage across sessions
  - User avatar with hover card when collapsed
  - Badge indicators repositioned for collapsed state
- **Sidebar Customization** (Enhanced - Jan 14, 2026):
  - "Configure Sidebar" button (Admin only) opens configuration modal
  - **Drag-and-drop reordering** of all menu items
  - **Folder creation**: Group related pages into collapsible folders
  - **Folder management**: Edit folder names, delete folders, remove items from folders
  - **Persistent configuration**: Saved to database per user
  - **Reset to default**: One-click restore to original order
  - Example: Group "Leave Requests" + "Leave Calendar" into "Leave Management" folder

### Phase 12: Notification System (Completed - Jan 13, 2026)
- **In-App Notifications**: Bell icon in header with unread count badge
- **Notification Dropdown**: Click bell to see recent notifications
- **Notification Events**:
  - Request approved/rejected → Staff notified
  - Reserved member approved/rejected → Staff notified
  - New reserved member request → Admin notified
- **Actions**: Mark as read, Mark all as read, Delete notification
- **Auto-refresh**: Polls for new notifications every 30 seconds
- **Toast Notifications**: Shows toast when new notifications arrive

### Phase 13: Edit Product Feature (Completed - Jan 13, 2026)
- **Edit Button**: Pencil icon next to product badge on database cards
- **Inline Editing**: Click edit, select new product from dropdown, save
- **Cascading Update**: Updates product on database and all associated records

### Phase 14: Advanced Analytics Dashboard (Completed - Jan 13, 2026)
- **Staff Performance Analytics**:
  - Records processed per period (daily, weekly, monthly charts)
  - WhatsApp reachability rate (Ada vs Tidak vs Ceklis1)
  - Response rate (Respond Ya vs Tidak)
  - Staff comparison bar charts
  - Completion rate metrics
- **Business Analytics**:
  - OMSET trends over time (line charts)
  - Top performing products by OMSET (bar charts)
  - NDP vs RDP analysis (pie charts)
  - Database utilization rate (table with progress bars)
- **Configurable Widgets**: Show/hide toggle for all 8 widget types
- **Filters**: Period (Today/Week/Month/Quarter/Year), Product, Staff
- **Drag & Drop Reorder**: Reorder widgets by dragging grip handle
- **Layout Persistence**: Widget order saved to database per user account

### Phase 15: Export Center (Completed - Jan 13, 2026)
- **Export Types**:
  - Customer Records (with product, status, staff, date filters)
  - OMSET Data (with product, staff, customer type, date filters)
  - Staff Performance Report (with period filter)
  - Reserved Members (with product, staff, status filters)
  - DB Bonanza Records (with database, product, staff, status filters)
  - Member WD Records (with database, product, staff, status filters)
- **Formats**: Both Excel (.xlsx) and CSV (.csv) supported
- **Dynamic Filters**: Filter options change based on export type

### Phase 16: Timezone Bug Fix (Completed - Jan 14, 2026)
- **Issue**: OMSET CRM date filters (Today/Yesterday) were showing incorrect data due to timezone mismatch
- **Root Cause**: Frontend was using browser's local time (`new Date()`) instead of Jakarta timezone
- **Fix**: Frontend now fetches server time (`/api/server-time`) on mount and uses Jakarta date (UTC+7) for all date calculations
- **Components Updated**:
  - `AdminOmsetCRM.js`: Now uses server date for Today/Yesterday/Last7/Last30/ThisMonth filters
  - `StaffOmsetCRM.js`: Now initializes date picker with server date (Jakarta timezone)

### Phase 17: Report CRM (Completed - Jan 14, 2026)
- **New Admin Page**: Comprehensive OMSET reporting connected to staff's daily OMSET CRM data
- **Yearly Summary Tab**:
  - Summary cards: Total NDP, Total RDP, Total Form, Total OMSET
  - **NEW**: Monthly Progress Chart for NDP/RDP/Form (ComposedChart with bars and line)
  - **NEW**: Monthly Progress Chart for OMSET/Nominal (AreaChart with gradient)
  - Monthly breakdown table with NDP/RDP/Form/Nominal columns
- **Monthly Detail Tab** (Enhanced):
  - Collapsible sections for each month
  - **Staff-level breakdown** with collapsible cards
  - **CRM Efficiency** calculation per staff (Rp 278M = 100%)
  - Progress bar visualization for efficiency
  - Month total summary with combined CRM efficiency
- **Daily Report Tab** (Enhanced):
  - **Collapsible Staff Boxes**: Each staff has their own expandable card with avatar, summary stats
  - **Product Separation**: Within each staff, products are shown as collapsible sections with indigo badges
  - **Daily Data Tables**: When a product is expanded, shows daily breakdown (Tanggal, NDP, RDP, Form, Nominal, AVG/Form)
  - **Grand Total Bar**: Dark gradient bar at bottom showing combined totals
- **Staff Performance Tab**:
  - Per-staff metrics: NDP, RDP, Total Form, Total OMSET
  - AVG/FORM and % NDP calculations
- **Filters**: Year, Month, Product, Staff
- **Export**: Excel export with multiple sheets (YEARLY, MONTHLY, STAFF PERFORMANCE, DEPOSIT TIERS)
- **Data Source**: Pulls from existing OMSET CRM records, separated by product

### Phase 18: CRM Bonus Calculation (Completed - Jan 14, 2026)
- **New Admin Page**: Automatic monthly bonus calculation for staff
- **Main Bonus Tiers** (based on monthly total nominal):
  - ≥ Rp 280.000.000 = $100
  - ≥ Rp 210.000.000 = $75
  - ≥ Rp 140.000.000 = $50
  - ≥ Rp 100.000.000 = $30
  - ≥ Rp 70.000.000 = $20
- **Daily NDP Bonus**:
  - >10 NDP/day = $5
  - 8-10 NDP/day = $2.50
- **Daily RDP Bonus**:
  - >15 RDP/day = $5
  - 12-15 RDP/day = $2.50
- **Features**:
  - Year/Month filters
  - Grand Total summary bar (green gradient)
  - Collapsible staff cards with bonus breakdown
  - 4 metric cards: Total Nominal, Main Bonus, NDP Bonus, RDP Bonus
  - Daily breakdown table with NDP/RDP counts and bonuses
  - Total bonus formula display ($Main + $NDP + $RDP)
  - Excel export with summary sheet and per-staff daily breakdown

### Phase 19: Off Day / Sakit (Leave Request System) (Completed - Jan 14, 2026)
- **New Staff Page**: Staff can request time off
- **Leave Types**:
  - **Off Day**: Full day off = 12 hours deducted
  - **Sakit**: Sick leave with custom start/end time = calculated hours
- **Monthly Balance**: 24 hours per month per staff member
- **Staff Features**:
  - View remaining leave balance
  - Create new leave requests with date, time (for Sakit), and optional reason
  - View request history with status (Pending/Approved/Rejected)
  - Cancel pending requests
  - See admin notes on processed requests
- **Admin Features**:
  - View all leave requests with filters (Status, Year, Month)
  - Pending request count badge
  - Approve/Reject requests with optional notes
  - View staff leave balances
- **Leave Calendar** (Admin):
  - Monthly calendar view of all approved leave days
  - Color-coded staff members for easy identification
  - Click on any date to see detailed leave information
  - Staff legend and leave type legend
  - Month navigation with "Today" button
  - Shows count of days with leave per month
- **Balance Calculation**:
  - Only approved requests deduct from balance
  - Pending requests are considered when validating new requests (prevents over-requesting)
  - Rejected requests do not affect balance
- **API Endpoints**:
  - `GET /api/leave/balance` - Staff's leave balance
  - `GET /api/leave/my-requests` - Staff's leave requests
  - `POST /api/leave/request` - Create leave request
  - `DELETE /api/leave/request/{id}` - Cancel pending request
  - `GET /api/leave/all-requests` - Admin view all requests
  - `PUT /api/leave/request/{id}/action` - Admin approve/reject
  - `GET /api/leave/staff-balance/{id}` - Admin view staff's balance
  - `GET /api/leave/calendar` - Admin calendar view data

### Phase 20: Izin (Short Break Permission System) (Completed - Jan 14, 2026)
- **Staff Page "Izin"**: Track short breaks during work hours
- **Core Features**:
  - "Izin" button: Start a break (clock starts)
  - "Kembali" button: End break (clock stops, duration calculated)
  - Real-time timer showing elapsed break time
  - Daily limit: 30 minutes maximum
  - Progress bar showing daily usage
- **Automatic Notifications**:
  - When staff exceeds 30-minute limit, admins receive notification
  - Toast notifications for break start/end
- **Admin Monitoring**:
  - "Monitor Izin" page in admin panel
  - Summary cards: Staff with breaks, currently on break, exceeded limit
  - Expandable staff list showing individual break records
  - Auto-refresh every 30 seconds
- **Database**:
  - `izin_records` collection: id, staff_id, staff_name, date, start_time, end_time, duration_minutes
- **API Endpoints**:
  - `GET /api/izin/status` - Current break status
  - `GET /api/izin/today` - Today's break records
  - `POST /api/izin/start` - Start break
  - `POST /api/izin/end` - End break
  - `GET /api/izin/admin/today` - Admin view all staff breaks
  - `GET /api/izin/admin/history` - Admin view break history

## Tech Stack
- **Frontend**: React + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + PyMongo + Pandas + Openpyxl
- **Database**: MongoDB

## Key API Endpoints
- `/api/auth/*` - Authentication
- `/api/products` - Product management
- `/api/databases` - Database upload/management
- `/api/download-requests` - Record request workflow
- `/api/my-assigned-records` - Staff's assigned customers
- `/api/customer-records/{id}/whatsapp-status` - Update WhatsApp status
- `/api/reserved-members` - Reserved member CRM (POST/GET/PATCH/DELETE)
- `/api/staff-users` - Get list of staff members
- `/api/bonanza/*` - DB Bonanza endpoints (upload, databases, records, assign)
- `/api/memberwd/*` - Member WD CRM endpoints (upload, databases, records, assign)
- `/api/notifications` - Notification system (GET/PATCH/DELETE)
- `/api/analytics/staff-performance` - Staff performance analytics
- `/api/analytics/business` - Business analytics (OMSET, utilization)
- `/api/export/*` - Export endpoints (customer-records, omset, staff-report, reserved-members, bonanza-records, memberwd-records)
- `/api/bulk/*` - Bulk operations (requests, status-update, bonanza-records, memberwd-records)
- `/api/user/preferences/widget-layout` - Save/load user widget layout order
- `/api/leave/*` - Leave request system (balance, my-requests, request, all-requests, staff-balance)
- `/api/user/preferences/sidebar-config` - Sidebar configuration (GET, PUT, DELETE)

## Credentials
- **Admin**: admin@crm.com / admin123
- **Staff**: staff@crm.com / staff123

---

## Backlog / Upcoming Tasks

### ✅ COMPLETED: Backend Refactoring (Jan 15, 2026)
- **server.py reduced from 3,945 lines to 104 lines (97% reduction!)**
- **Fully modular architecture with 14 route modules**:
  - `routes/deps.py` - Shared dependencies, auth helpers, DB connection
  - `routes/auth.py` - Authentication & user management
  - `routes/leave.py` - Leave request system
  - `routes/notifications.py` - Notifications & preferences
  - `routes/bulk.py` - Bulk operations
  - `routes/products.py` - Product management
  - `routes/analytics.py` - Analytics & export
  - `routes/izin.py` - Break/permission system
  - `routes/bonanza.py` - DB Bonanza
  - `routes/memberwd.py` - Member WD CRM
  - `routes/omset.py` - OMSET CRM system (NEW)
  - `routes/report.py` - Report CRM (NEW)
  - `routes/bonus.py` - Bonus Calculation (NEW)
  - `routes/records.py` - Core database/records/reserved members (NEW)
  - `routes/leaderboard.py` - Staff leaderboard & targets (NEW)
  - `routes/followup.py` - Customer follow-up reminders (NEW)
  - `routes/daily_summary.py` - Daily summary with product breakdown (NEW)
  - `routes/funnel.py` - Conversion funnel analytics (NEW)
- **Total modular code: ~5,000 lines across 18 modules**
- **All 90+ API endpoints working correctly**
- **API Version upgraded to 3.0.0**

### ✅ COMPLETED: Daily Summary Product Breakdown (Jan 15, 2026)
- **Enhanced Daily Summary** with per-product performance breakdown
- **Admin View**:
  - Overall stats: Total OMSET, NDP, RDP, Forms
  - Staff breakdown with expandable product details per staff member
  - Overall Product Performance section
- **Staff View**:
  - Personal stats with product breakdown
  - Team product performance for comparison
- **API Endpoint**: `/api/daily-summary` (enhanced with product_breakdown)

### ✅ COMPLETED: Conversion Funnel (Jan 15, 2026)
- **Sales Funnel Visualization**:
  - Assigned → WhatsApp Reached → Responded → Deposited
  - Visual funnel bars with conversion percentages
  - Drop indicators showing customer loss at each stage
- **Three Views**:
  - **Overview**: Main funnel visualization with stage cards
  - **By Product**: Table showing funnel metrics per product
  - **By Staff**: Table showing funnel metrics per staff member (Admin only)
- **Filters**: Date range (7/30/90/365 days), Product filter
- **API Endpoints**:
  - `GET /api/funnel` - Main funnel data
  - `GET /api/funnel/by-product` - Product breakdown
  - `GET /api/funnel/by-staff` - Staff breakdown (Admin only)
  - `GET /api/funnel/trend` - Daily trend data

### ✅ COMPLETED: Customer Retention Tracking (Jan 15, 2026)
- **Track RDP (Repeat Depositors)** and loyalty metrics
- **Overview Dashboard**:
  - Key metrics: Total Customers, NDP, RDP, Retention Rate
  - Secondary metrics: Total Deposits, Total OMSET, Avg per Customer
  - Daily NDP vs RDP trend chart (stacked area)
  - Top Loyal Customers list with loyalty badges (VIP, Loyal, Regular, New)
- **Four Views**:
  - **Overview**: Main retention metrics and charts
  - **Customer List**: Detailed customer table with filters and sorting
  - **By Product**: Product-level retention breakdown
  - **By Staff**: Staff-level retention metrics (Admin only)
- **Loyalty Scoring**: Calculated based on deposit count and unique days
- **API Endpoints**:
  - `GET /api/retention/overview` - Main retention metrics
  - `GET /api/retention/customers` - Customer list with filters
  - `GET /api/retention/trend` - Daily NDP/RDP trend
  - `GET /api/retention/by-product` - Product breakdown
  - `GET /api/retention/by-staff` - Staff breakdown (Admin only)

### ✅ COMPLETED: Customer Segment Alerts (Jan 15, 2026)
- **At-Risk Customer Detection** to prevent churn
- **Risk Levels**:
  - **Critical**: 14+ days since last deposit
  - **High**: 7-13 days since last deposit
  - **Medium**: 3-6 days (only for frequent depositors with 2+ deposits)
- **Features**:
  - Summary cards showing counts per risk level
  - Detailed alert list with customer info, OMSET, and last deposit date
  - Deposit pattern analysis ("typically deposits every X days")
  - Overdue indicator for customers past their usual pattern
  - Filter by risk level (All/Critical/High/Medium)
  - Dismiss alerts for 7 days
- **API Endpoints**:
  - `GET /api/retention/alerts` - Get at-risk customers
  - `GET /api/retention/alerts/by-staff` - Staff breakdown (Admin only)
  - `POST /api/retention/alerts/dismiss` - Dismiss alert for 7 days

### ✅ COMPLETED: Dark Mode (Jan 15, 2026)
- **Theme Toggle**: Sun/Moon icon in header to switch between light/dark modes
- **System Preference Detection**: Automatically detects user's OS preference
- **Persistence**: Saves theme preference in localStorage
- **Keyboard Shortcut**: Works with global UI
- **Components Updated**: Sidebar, header, navigation items with dark mode classes
- **New Files**: `frontend/src/contexts/ThemeContext.js`
- **Dark Mode Fix (Jan 15, 2026)**: Enhanced dark mode styling for:
  - AdminDashboard Overview stat cards
  - CRM Bonus Calculation page (tier cards, staff breakdown, tables, settings modal)
  - Leaderboard/Staff Progress page (stats, progress bars, rank indicators)
  - Daily Summary page (gradient cards, performer badges)
  - Customer Retention page (tabs, metric cards, alert sections)
  - Export Center page (form elements, labels, cards)
  - Leave Calendar page (calendar grid, day cells, sidebar)
  - Staff Progress & Quality page (filter dropdowns, progress bars, daily stats)
  - DB Bonanza page (upload section, database cards)
  - Member WD CRM page (upload section, database cards)
  - Notification Bell dropdown (proper dark mode styling)

### ✅ COMPLETED: Real-time Notifications with WebSockets (Jan 15, 2026)
- **WebSocket Backend**: FastAPI WebSocket endpoint at `/ws/notifications`
- **Connection Manager**: Handles multiple concurrent WebSocket connections per user
- **Authentication**: JWT token-based WebSocket authentication
- **Features**:
  - Real-time notification delivery when events occur
  - Automatic heartbeat (30-second keepalive)
  - Automatic reconnection with exponential backoff (up to 5 attempts)
  - Graceful fallback to polling (60 seconds) when WebSocket unavailable
- **Frontend Updates**:
  - WebSocket connection status indicator (green = connected, amber = connecting, gray = offline)
  - Toast notifications for new real-time notifications
  - Reduced polling frequency when WebSocket is connected
- **New Files**:
  - `backend/routes/websocket.py` - WebSocket route and connection manager
- **Modified Files**:
  - `backend/routes/notifications.py` - Send real-time notifications on creation
  - `backend/server.py` - Include WebSocket router
  - `frontend/src/components/NotificationBell.js` - WebSocket client integration
- **Note**: WebSocket may require proper ingress configuration for production. Fallback polling ensures notifications always work.

### ✅ COMPLETED: NDP/RDP Customer Name Normalization Fix (Jan 15, 2026)
- **Problem**: Customer names with different capitalization, leading/trailing spaces were treated as different customers for NDP/RDP logic
  - Example: "John Doe", "john doe", " JOHN DOE " were counted as separate customers
- **Solution**: Normalize customer IDs before comparison
- **Changes**:
  - Added `normalize_customer_id()` helper function (trims spaces, converts to lowercase)
  - New records store `customer_id_normalized` field for efficient comparison
  - New records store `customer_type` field (NDP/RDP) at insert time
  - Added migration endpoint `/api/omset/migrate-normalize` to update existing records
- **Modified Files**:
  - `backend/routes/omset.py` - Create, NDP/RDP calculation, migration endpoint
  - `backend/routes/bonus.py` - Bonus calculation uses normalized comparison
  - `backend/routes/daily_summary.py` - Daily summary uses normalized comparison
- **Migration**: Run `POST /api/omset/migrate-normalize` (admin only) to update existing records

### ✅ COMPLETED: Global Search (Jan 15, 2026)
- **Keyboard Shortcut**: Ctrl/Cmd + K to open search modal
- **Multi-Category Search**: Searches across:
  - Customers (name, ID, WhatsApp)
  - Staff (name, email) - Admin only
  - Products (name, category)
  - Databases (name, product)
  - OMSET Records (customer name, ID, username)
- **Features**:
  - Real-time search with 300ms debounce
  - Keyboard navigation (↑↓ to navigate, Enter to select)
  - Categorized results with icons
  - Click-to-navigate to relevant pages
  - ESC to close
- **New Files**: 
  - `backend/routes/search.py`
  - `frontend/src/components/GlobalSearch.js`

### ✅ COMPLETED: Internationalization (i18n) - English/Indonesian (Jan 15, 2026)
- **Language Toggle**: Globe icon in header to switch between English and Indonesian
- **Language Options**: English (EN) and Indonesian (ID) - using casual Indonesian translations
- **Persistence**: Language preference saved to localStorage under 'language' key
- **HTML Lang Attribute**: Updates document.documentElement.lang when language changes
- **Coverage** - Translated elements:
  - Sidebar menu items (Overview→Ringkasan, Leaderboard→Papan Peringkat, etc.)
  - Dashboard titles and stat card labels
  - Form labels and buttons
  - Login page elements
  - Database overview section
  - Common UI elements (Search, Filter, Save, Cancel, etc.)
- **New Files**:
  - `frontend/src/contexts/LanguageContext.js` - Context provider with toggleLanguage function
  - `frontend/src/translations/en.js` - English translations (~400 keys)
  - `frontend/src/translations/id.js` - Indonesian translations (~400 keys)
  - `frontend/src/translations/index.js` - Translation function and utilities
- **Modified Files**:
  - `frontend/src/App.js` - Wrapped with LanguageProvider
  - `frontend/src/components/DashboardLayout.js` - Added language toggle button
  - `frontend/src/pages/AdminDashboard.js` - Menu items use translations
  - `frontend/src/pages/StaffDashboard.js` - Menu items use translations
  - `frontend/src/pages/Login.js` - Form labels use translations
  - Multiple components updated to use useLanguage() hook

### P1: Next Priority Tasks
- None - All P1 tasks completed!

### ✅ COMPLETED: User Activity Monitor (Jan 15, 2026)
- **New Page**: "User Activity" showing real-time user status
- **Status Types**:
  - 🟢 **Online** - Active within last 5 minutes
  - 🟡 **Idle** - No activity for 5-30 minutes (shows idle duration)
  - ⚫ **Offline** - Inactive > 30 minutes or logged out
- **Backend Endpoints**:
  - `POST /api/auth/logout` - Marks user as offline
  - `POST /api/auth/heartbeat` - Updates last_activity timestamp
  - `GET /api/users/activity` - Returns all users with status (Admin only)
- **Frontend Features**:
  - Summary cards (Total, Online, Idle, Offline counts)
  - User list with avatars, role badges, status indicators
  - Login, Activity, Logout timestamps
  - Auto-refresh every 30 seconds
  - Activity tracking on mouse/keyboard/click events
- **Files Created/Modified**:
  - `backend/routes/auth.py` - Added logout, heartbeat, activity endpoints
  - `frontend/src/pages/UserActivity.js` - New monitoring page
  - `frontend/src/App.js` - Added heartbeat logic and proper logout

### ✅ COMPLETED: Database Request Duplicate Check (Jan 15, 2026)
- **Feature**: When staff requests database records, system automatically filters out records where `username` matches Reserved Members' `customer_name`
- **Logic**:
  - Compares `username` field in database records against `customer_name` in Reserved Members for the same product
  - Case-insensitive comparison (e.g., "JOHN" matches "John")
  - Skips reserved records and replaces with next available records
  - Staff always receives exact count requested (if enough non-reserved records exist)
- **Username Fields Checked**: username, user_name, user, id, userid, user_id
- **Error Handling**: If not enough non-reserved records available, returns detailed error message
- **File Modified**: `backend/routes/records.py` - `create_download_request` function

### ✅ COMPLETED: Scheduled Telegram Reports Feature (Jan 15, 2026)
- **Daily Report** (1:00 AM WIB to personal chat):
  - NDP, RDP, Total Form, Nominal per staff per product
  - Staff ranking by performance
- **At-Risk Customer Alerts** (11:00 AM WIB to group chat):
  - Customers inactive for 14+ days with 2+ previous deposits
  - Grouped by staff for actionability
  - Color-coded urgency (🔴 30+ days, 🟠 21+ days, 🟡 14+ days)
- **Backend Endpoints**:
  - `POST /api/scheduled-reports/config` - Daily report config
  - `POST /api/scheduled-reports/atrisk-config` - At-risk alert config
  - `POST /api/scheduled-reports/test` - Test personal chat
  - `POST /api/scheduled-reports/atrisk-test` - Test group chat
  - `POST /api/scheduled-reports/send-now` - Manual daily report
  - `POST /api/scheduled-reports/atrisk-send-now` - Manual at-risk alert
- **Frontend**: Updated `pages/ScheduledReports.js` with both configurations
- **Dependencies**: `python-telegram-bot`, `apscheduler`, `httpx`

### ✅ COMPLETED: Bulk Add Reserved Members Feature (Jan 15, 2026)
- **New Backend Endpoint**: `POST /api/reserved-members/bulk`
  - Accepts list of customer names, product ID, and staff ID
  - Processes all names in one request
  - Skips duplicates (case-insensitive) with detailed skip reasons
  - Returns summary with added count, skipped count, and details
- **New Frontend UI**: Expandable "Bulk Add Reservations" panel
  - Product and Staff dropdowns
  - Large textarea for entering customer names (one per line)
  - Real-time count of entered names
  - Results panel showing added/skipped counts and details
- **Files Modified**:
  - `backend/routes/records.py` - Added BulkReservedMemberCreate model and bulk endpoint
  - `frontend/src/components/AdminReservedMembers.js` - Added bulk add UI

### ✅ COMPLETED: Report CRM Bug Fixes (Jan 15, 2026)
- **Issue 1 - Dark Mode Fix**: Report CRM page now fully supports dark mode
  - Fixed header, filters, tabs, yearly table, monthly detail, and staff performance sections
  - Added dark:bg-slate-800/900 classes to all card elements
  - Added dark:text-white/slate-300 classes to all text elements
  - Fixed select dropdowns with dark mode backgrounds
- **Issue 2 - RDP Unique Customer Count Fix**: RDP now counts unique customers per day, not total records
  - Updated `daily_by_staff` section to track unique customers per staff-product-date
  - Updated `daily_data` section to track unique customers per day
  - Updated `staff_performance` section to track unique customers per staff for the year
  - All sections now use normalized customer IDs for consistent comparison
- **Issue 3 - Customer Retention At-Risk Alerts Fix**: Confirmed working correctly
  - Retention alerts already use normalized customer IDs
  - Days since deposit calculation is accurate
- **Files Modified**:
  - `frontend/src/components/ReportCRM.js` - Added dark mode classes throughout
  - `frontend/src/components/DashboardLayout.js` - Added dark:bg-slate-950 to main element
  - `backend/routes/report.py` - Fixed RDP logic in daily_by_staff, daily_data, and staff_performance
- **Test Coverage**: Created `/app/tests/test_report_crm.py` with 7 passing tests

### ✅ COMPLETED: Staff Offline Alerts Feature (Jan 15, 2026)
- **Purpose**: Notify admins when staff members haven't logged in by a specific time
- **Backend Endpoints**:
  - `POST /api/scheduled-reports/staff-offline-config` - Save alert configuration
  - `POST /api/scheduled-reports/staff-offline-send-now` - Manually trigger alert
  - `GET /api/scheduled-reports/config` - Returns staff_offline_enabled, staff_offline_hour, staff_offline_minute fields
- **Alert Content**:
  - Summary: Total staff, online count, offline count
  - Detailed list of offline staff with email and last login time
  - List of currently online staff
- **Features**:
  - Configurable alert time (default 11:00 AM WIB)
  - Enable/disable toggle
  - Uses same Bot Token and Chat ID as Daily Reports (sent to admin's personal chat)
  - Scheduler automatically sends at configured time
  - Manual "Check Staff Status Now" button for instant check
- **Staff Status Logic**:
  - Online: Active within last 30 minutes
  - Offline: No activity for 30+ minutes or logged out
- **Frontend UI** (in ScheduledReports.js):
  - Staff Offline Alerts section with red theme
  - Status card showing schedule and last sent time
  - Configuration form with hour/minute dropdowns and enable toggle
  - Alert Actions panel with "Check Staff Status Now" button
  - Info section explaining how it works
- **Files Modified**:
  - `backend/routes/scheduled_reports.py` - Added generate_staff_offline_alert, send_staff_offline_alert, config endpoint
  - `frontend/src/pages/ScheduledReports.js` - Added Staff Offline Alerts UI section
- **Test Coverage**: Created `/app/tests/test_staff_offline_alerts.py` with 6 passing tests

### P2: Future Enhancements
- Email notifications for important updates
- Scheduled automated reports from Export Center
- Financial ROI tracking in Report CRM
- Izin analytics (break patterns, total time per period)
- Leave Calendar statistics (total hours, most common leave day)
- Keyboard shortcuts for power users
- Sidebar search/filter functionality
- Quick Actions on Overview cards
