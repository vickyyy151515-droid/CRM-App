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

## Latest Update: Drill-Down Interactivity (2026-02-14)

Clicking on any staff/product/data point in the 5 new charts opens a detailed slide-over panel:

1. **Response Time** → Click staff row → Individual records with WA/response timestamps
2. **Follow-up Effectiveness** → Click staff tag → Responded customers with deposit status (converted/pending)
3. **Product Performance** → Click product → Staff-level NDP/RDP breakdown for that product
4. **Customer Value** → Click staff bar → Top customers by deposit value (NDP vs RDP)
5. **Deposit Trends** → Click data point → That day's individual deposits

### New Drill-Down Endpoints:
- `GET /api/analytics/drill-down/response-time?staff_id=X&period=X`
- `GET /api/analytics/drill-down/followup-detail?staff_id=X&period=X`
- `GET /api/analytics/drill-down/product-staff?product_id=X&period=X`
- `GET /api/analytics/drill-down/staff-customers?staff_id=X&period=X`
- `GET /api/analytics/drill-down/date-deposits?date=X&granularity=X`

Testing: 22/22 tests passed (100%) — Backend + Frontend

---

## Previous Update: 5 New Analytics Charts — Operational & Strategic (2026-02-14)

### New Charts (Medium Value — Operational Efficiency):
1. **Response Time by Staff** — Shows avg time to WA check and first response per staff with speed grades (Excellent/Good/Average/Slow), dual bars
2. **Follow-up Effectiveness** — Grouped bar chart showing WA Checked → Responded → Deposited per staff with effectiveness % ranking
3. **Product Performance** — Donut pie chart showing NDP/RDP counts and deposit amounts per product with percentage breakdown

### New Charts (Nice to Have — Strategic Insights):
4. **New vs Returning Customer Value (LTV)** — Stacked bar chart comparing NDP vs RDP deposit values per staff with NDP share indicator
5. **Deposit Trends Over Time** — Area+line chart with Daily/Weekly/Monthly granularity toggle, summary stats (Total Volume, Deposits, Avg/Period, Peak)

### New Endpoints:
- `GET /api/analytics/response-time-by-staff` (period, product_id filters)
- `GET /api/analytics/followup-effectiveness` (period, product_id filters)
- `GET /api/analytics/product-performance` (period filter)
- `GET /api/analytics/customer-value-comparison` (period, product_id filters)
- `GET /api/analytics/deposit-trends` (period, granularity, product_id filters)

Testing: 38/38 tests passed (100%) — Backend + Frontend

---

## Previous Update: 3 High-Value Analytics Charts (2026-02-14)

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
