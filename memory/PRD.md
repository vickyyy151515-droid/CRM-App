# CRM Pro - Product Requirements Document

## Original Problem Statement
CRM application for sales tracking, customer retention, and staff management. Includes Member WD assignment, DB Bonanza, reserved member protection, analytics dashboards, and more.

## Architecture
- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Shadcn/ui + Recharts
- **Backend**: Python + FastAPI + MongoDB (via pymongo/motor)
- **Auth**: JWT-based with master_admin and staff roles

## What's Been Implemented

### Core Features (Complete)
- Sales tracking and customer records management
- Staff management with role-based access
- Member WD CRM with batch assignment system
- DB Bonanza assignment system
- Reserved member protection system (with permanent toggle)
- Advanced Analytics page with 10+ interactive charts and drill-downs
- Data sync and health check utilities
- Scheduled cleanup jobs for expired reservations

### P0 Bug Fix: Reserved Member Assignment (2026-02-15) - COMPLETE
**Root Cause**: Reserved member checks were built using `customer_id OR customer_name` (only adding ONE identifier per member). If a member had both fields with different values, the check could be bypassed when the uploaded data matched the un-added field.

**Fix**: Created centralized utility (`backend/utils/reserved_check.py`) that:
1. Adds BOTH customer_id AND customer_name to the reserved set
2. Checks ALL row_data values field-agnostically (no hardcoded column names)
3. Is used by ALL code paths: upload, manual assign, random assign, auto-replace, process-invalid

**Files Changed**:
- NEW: `backend/utils/reserved_check.py` - Centralized utility
- UPDATED: `backend/routes/memberwd.py` - All assignment paths
- UPDATED: `backend/routes/bonanza.py` - All assignment paths
- UPDATED: `backend/utils/repair_helpers.py` - Conflict detection

**Testing**: 27/27 tests passed (16 new + 11 existing)

### Deep Audit Sync Bug Fixes (2026-02-15) - COMPLETE
**3 high-priority sync/logic bugs found and fixed:**

1. **`omset.py` last_omset_date sync** — Now searches BOTH `customer_id` AND `customer_name` using `$or`. Legacy reserved members get deposit dates synced correctly.

2. **`delete_reserved_member` + cleanup job** — Now restores records invalidated by the deleted/expired reservation via new `restore_invalidated_records_for_reservation()` helper.

3. **`move_reserved_member`** — Now restores OLD staff's invalidations and creates NEW ones for the new owner.

**Testing**: 7/7 tests passed (iteration_54)

### Configurable Working Hours (2026-02-20) - COMPLETE
Added admin setting to configure staff working hours from the Attendance page (Today tab). Previously hardcoded to 11:00-23:00, now stored in DB `system_settings`. Lateness is calculated based on the configured start time. Backend: `GET/PUT /api/attendance/admin/working-hours`. Frontend: Working Hours card with time picker inputs.

### Per-Database Auto-Approve Control (2026-02-20) - COMPLETE
Added per-database auto-approve setting with clear visual toggle. Each database shows "Auto-Approve" (green) or "Manual" (amber) button. Global toggle is master switch — when OFF, everything is manual. When ON, per-database setting takes over. Fixed: Pydantic model now includes `auto_approve` field, API properly persists and returns the setting.

### Export Authentication Fix (2026-02-20) - COMPLETE
Fixed "Not authenticated" error on CSV/Excel export across the entire app. Root cause: `window.open()` doesn't send JWT header.
- `BonusCalculation.js`: Changed to `api.get()` with blob response
- `analytics.py`: 4 export endpoints now use `token` query param auth
- `bonus.py`: Added `token` param support
- `deps.py`: Added reusable `get_user_from_token_param()` helper

### Advanced Analytics Date Range Filter (2026-02-18) - COMPLETE
Added "Custom Range" option to the Advanced Analytics period filter with date picker inputs. Backend `get_date_range()` updated to accept `custom_start`/`custom_end` params across all analytics endpoints. Frontend shows date pickers when "Custom Range" is selected, auto-loads when both dates are filled.

### Record Assignment Randomization (2026-02-17) - COMPLETE
Changed normal database record assignment from sequential (by row_number) to random. Staff now receives randomized records when requesting from a database. Reserved member exclusion unchanged.

### Izin Overage Fee Removal Option (2026-02-17) - COMPLETE
Added ability for admins to manually remove/waive izin overage fees per staff per date:
- Backend: `POST /api/attendance/admin/fees/{staff_id}/waive-izin?date=YYYY-MM-DD` and `DELETE .../waive-izin/{date}` to reinstate
- Uses `izin_overage_waivers` collection, waived records excluded from fee summary
- Frontend: "Remove" button on each izin overage row with confirmation dialog
- Both endpoints verified via curl

### Daily Briefing Pop-up for Staff (2026-02-17) - COMPLETE
Staff sees a daily pop-up on first login showing randomized priority customers:
- At-Risk: 5 Critical (14-30d), 5 High (7-13d), 5 Medium (3-6d, 2+ deposits)
- Follow-Up Reminders: 5 random per product from their follow-up list
- Randomized daily (seed = staff_id + date), dismissable, won't re-show same day
- Backend: `GET /api/retention/daily-briefing`, `POST /api/retention/daily-briefing/dismiss`
- Frontend: `DailyBriefingModal.js` rendered in `StaffDashboard.js`
- Testing: 11/11 backend, 8/8 frontend passed

### At-Risk Telegram Alert Fix (2026-02-17) - COMPLETE
Fixed at-risk customer alert to exclude "lost" customers (31+ days inactive). Added `lost_boundary_date` (30 days) as upper bound in `generate_atrisk_alert()` so only customers between `inactive_days` threshold and 30 days are included, matching the retention page's at-risk vs lost categorization.

### Izin Overage Fee System (2026-02-17) - COMPLETE
Staff has a 30-minute daily izin (break/permission) limit. For every minute past the threshold, a $5/minute fine is applied (seconds handled via float precision). Connected to the Fee & Payment tab in Attendance:
- Backend: `fees.py` calculates izin overage from `izin_records` per staff per day
- Frontend: New "Izin Overage" summary card, info bar showing "Izin Limit: 30 min/day", and `IzinOverageTable` in StaffFeeCard
- Testing: 12/12 backend, 8/8 frontend tests passed

### Code Quality Cleanup (2026-02-15) - COMPLETE
Fixed 19 linting issues in `scheduled_reports.py`:
- 13 f-string without placeholders (auto-fixed)
- 3 unused local variables (`staff_map`, `staff_name`, `no_deposit_members`, `to_delete`) removed
- 2 bare `except` clauses replaced with specific exception types (`ValueError, TypeError, AttributeError`)
- Verified all related backend files (`memberwd.py`, `bonanza.py`, `records.py`, `omset.py`, `utils/`) pass linting with zero issues.

### Auto-Reassignment of Expired/Deleted Reserved Members (2026-02-22) - COMPLETE
When a staff member records a new omset for a customer whose reservation was previously deleted/expired, the system automatically re-establishes the reservation under that staff member if the customer is not currently reserved by anyone else.
- **Trigger**: `POST /api/omset` with `approval_status=approved`
- **Conditions**: Customer not currently reserved by anyone + deleted reservation exists for same customer+staff+product
- **Actions**: Creates new `reserved_members` entry (created_by=system), removes from `deleted_reserved_members` archive, sends notification (type=reservation_auto_restored)
- **Also fixed**: Manual admin deletion (`DELETE /api/reserved-members/{id}`) now archives to `deleted_reserved_members` (previously only auto-expiration did this)
- **Bug fix**: Fixed duplicate entries in `deleted_reserved_members` - all archiving paths now deduplicate before inserting, and GET endpoint auto-cleans duplicates on fetch
- **Testing**: 5/5 backend tests passed including negative cases (iteration_58)

### NDP/RDP Data Consistency Audit (2026-02-23) - COMPLETE
Full audit of all reporting endpoints for NDP/RDP calculation consistency, as requested by user.
- **Bug found in `report.py`**: `unique_deposits` deduplication key was `(product_id, date, customer_id)` without `staff_id`, causing incorrect staff attribution and wrong NDP/RDP counts when multiple staff record the same customer.
- **Fix**: Changed key to `(staff_id, product_id, date, customer_id)` — all loop iterations updated.
- **`daily_summary.py`**: Already correct (single-day operations with proper staff-specific tracking).
- **Verification**: All 3 endpoints (`/api/omset/summary`, `/api/report-crm/data`, `/api/daily-summary`) now return identical NDP/RDP counts for same date ranges and staff filters.
- **Testing**: 50/50 tests passed (iteration_59) — cross-endpoint, per-staff, per-date, with product/staff filters.

### Frosted Glass Button System (2026-02-22) - COMPLETE
Applied Style D (Frosted Glass) to ALL buttons app-wide via global CSS overrides in `App.css` — no individual file edits needed.
- **Light mode**: Semi-transparent backgrounds, subtle borders with color-matched tint, inner glow (inset shadow), hover lift animation
- **Dark mode**: Enhanced glow effects on borders/shadows, slightly more vibrant translucency, color bleed glow
- **Coverage**: All color variants (indigo, blue, emerald, green, red, rose, amber, yellow, teal, purple, slate, gray), ghost/outline buttons, icon buttons, Shadcn Button component
- **Files changed**: `App.css` (global glass system), `components/ui/button.jsx` (Shadcn base)

## Prioritized Backlog

### P1 - Upcoming
- ~~UI/UX consistency standardization across the app~~ (Buttons completed 2026-02-22)

### P2 - Future
- "Smart Message Queue" WhatsApp follow-up app
- Staging/testing environment setup
- Centralized logging & monitoring (Sentry/LogRocket)

## Key API Endpoints
- `POST /api/memberwd/upload` - Upload member database
- `POST /api/memberwd/assign` - Manual assign records
- `POST /api/memberwd/assign-random` - Random assign records
- `POST /api/bonanza/upload` - Upload bonanza database
- `POST /api/bonanza/assign` - Manual assign bonanza records
- `POST /api/bonanza/assign-random` - Random assign bonanza records
- `PATCH /api/reserved-members/{id}/permanent` - Toggle permanent status
- `GET /api/analytics/drilldown/*` - Chart drill-down data

## DB Schema (Key Collections)
- `reserved_members`: {customer_id, customer_name, staff_id, staff_name, status, is_permanent, product_id, auto_reassigned, auto_reassigned_at}
- `deleted_reserved_members`: {<all reserved_members fields>, deleted_at, deleted_reason, deleted_by, deleted_by_name}
- `memberwd_records`: {row_data, status, assigned_to, is_reserved_member, batch_id}
- `bonanza_records`: {row_data, status, assigned_to, is_reserved_member}
- `customer_records`: {row_data, status, assigned_to}
