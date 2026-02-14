# CRM Boost PRD

## Original Problem Statement
CRM system for managing member data with three main modules:
1. **Normal Database** - Staff request records from admin-uploaded databases
2. **Member WD CRM** - Batch-based assignment system
3. **DB Bonanza** - Database-based assignment system

All modules support:
- Database upload (CSV/Excel)
- Random/manual assignment to staff
- Validation workflow (valid/invalid)
- Auto-replace invalid records (configurable)
- Recall assigned records
- Reserved member filtering

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React.js
- Database: MongoDB (Motor async driver)
- UI: Tailwind CSS + Shadcn components
- Scheduler: APScheduler (daily cleanup jobs)

## Latest Update: 3 New High-Value Analytics Charts (2026-02-14)

### New Features:
1. **Staff Conversion Funnel** — Dark navy theme, shows Assigned → WA Checked → Responded → Deposited per staff with gradient bars and percentages
2. **Revenue Heatmap** — Dark slate theme, Staff × Day-of-Week grid with heat-colored cells, toggle between Deposits/Amount views
3. **Deposit Lifecycle** — Deep purple gradient theme, shows avg time from customer response to first deposit per staff, with speed labels (Fast/Good/Average/Slow)

### New Endpoints:
- `GET /api/analytics/staff-conversion-funnel`
- `GET /api/analytics/revenue-heatmap`
- `GET /api/analytics/deposit-lifecycle`

Testing: 24/24 tests passed (100%)

---

## Previous Update: Staff NDP/RDP Daily Breakdown Chart (2026-02-14)

### Bug Fix: Admin Follow-up page showing 0 counts for master_admin users

**Problem:** The Admin Follow-up Reminders page (`/admin/follow-ups`) showed "0" for all summary counters (Total, Critical, High, Medium, Low, Deposited) when accessed by users with `master_admin` role.

**Root Cause:** In `backend/routes/followup.py`, the role check used `user.role == 'admin'` which excluded `master_admin` users. When a `master_admin` accessed the page, the code fell to the `else` branch and filtered follow-ups by the master_admin's own user ID — who has no assigned customer records.

**Fix Applied:**
| File | Line | Change |
|------|------|--------|
| `followup.py` | Line 38 | `user.role == 'admin'` → `user.role in ['admin', 'master_admin']` |
| `followup.py` | Line 101 | `user.role == 'admin'` → `user.role in ['admin', 'master_admin']` |

**Testing:** 10/10 backend tests passed. Both admin and master_admin roles now return identical follow-up data.

---

## Completed Tasks (All Sessions)
- Status Column in OMSET CRM
- NDP/RDP Out-of-Order Entry Bug Fix
- Recalculate NDP/RDP Button
- Frontend Unused Dependencies Cleanup
- Customer Retention RDP=0 Bug Fix
- At-Risk Auto-Remove After 31 Days
- Lost Customers Section
- Retention Approval Status Filter Fix
- Staff Progress Daily Breakdown Dropdown
- Staff Progress RDP Undercount Fix
- Admin Follow-up Reminders Page
- Admin Follow-up Reminders 0 Count Bug Fix (master_admin role)
- Frontend Refactoring (shared components)
- Backend Utils centralization
- MongoDB Index Optimization (28 indexes)
- Reserved Member protection & conflict resolution
- Data Sync Dashboard
- Member WD CRM count mismatch fix
- RDP Double-Counting Fix

## Pending Tasks
- P1: UI/UX consistency standardization across the app
- P2: Staging/testing environment setup
- P2: Centralized logging & monitoring (Sentry/LogRocket)
- P2: Review & cleanup of potentially unused frontend components

## Key API Endpoints
- `GET /api/followups` - Follow-up reminders (admin sees all staff, staff sees own)
- `GET /api/followups/filters` - Filter options for follow-ups
- `GET /api/followups/notifications` - Staff notification counts
- `GET /api/followups/check-deposited/{record_id}` - Check deposit status
- `POST /api/omset` - Create sales record
- `GET /api/retention/summary` - Retention dashboard
- `GET /api/leaderboard/admin-progress` - Staff progress

## Key DB Schema
- `omset_records`: Transaction records with NDP/RDP status
- `customer_records`: Customer contact/status, used by follow-up system
- `staff_targets`: Daily NDP/RDP targets per staff
- `users`: User accounts with roles (staff, admin, master_admin)
