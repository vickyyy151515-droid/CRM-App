# CRM Boost PRD

## Original Problem Statement
CRM system for managing member data with two main modules:
1. **Member WD CRM** - Batch-based assignment system
2. **DB Bonanza** - Database-based assignment system

Both modules support:
- Database upload (CSV/Excel)
- Random/manual assignment to staff
- Validation workflow (valid/invalid)
- Auto-replace invalid records (configurable)
- Recall assigned records
- Reserved member filtering

## Latest Update: Conflict Resolution Log (2026-02-05)

### ✅ NEW: Conflict Resolution Log Dashboard

**New Admin Page:** `Conflict Resolution Log` - accessible from sidebar

**Features:**
- Track all auto-invalidated records due to reservation conflicts
- Stats cards: Total Invalidated, Today, This Week, This Month
- Top affected staff breakdown (who lost the most records)
- Top reserved by staff breakdown (who made the most reservations)
- Filter by staff member
- Export to CSV functionality
- Paginated history table with details:
  - Customer ID
  - Source (Normal Database / DB Bonanza / Member WD CRM)
  - Database name
  - Affected staff (who lost the record)
  - Reserved by staff (who made the reservation)
  - Timestamp

**New API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /api/data-sync/conflict-resolution-log` | Fetch paginated conflict history |
| `GET /api/data-sync/conflict-resolution-stats` | Get aggregated statistics |

**Query Parameters (log endpoint):**
- `limit` - Number of records per page (default: 100)
- `skip` - Pagination offset
- `staff_id` - Filter by affected staff
- `date_from` / `date_to` - Date range filter

---

## Previous Update: Frontend Refactoring & Proactive Monitoring (2026-02-05)

### ✅ Proactive Monitoring System

**New Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `POST /api/data-sync/proactive-check` | Run health check and notify admins if critical issues found |
| `GET /api/data-sync/monitoring-config` | Get monitoring configuration |
| `PUT /api/data-sync/monitoring-config` | Update monitoring config (enabled, interval, thresholds) |

**Features:**
- Automatically sends notifications to all admins when critical data issues are detected
- Configurable check interval (default: 6 hours)
- Option to notify on warnings or only critical issues
- Activity logging for all proactive checks

**UI Enhancement:**
- "Run Proactive Check" button added to Data Sync Dashboard header
- Shows results: health score, issues found, notifications sent

### ✅ NEW: Shared AdminActionsPanel Component

**Location:** `/app/frontend/src/components/shared/AdminActionsPanel.js`

**Features:**
- Reusable component for both DB Bonanza and Member WD CRM
- Includes: Fix Product Mismatch, Fix Reserved Conflicts, Settings buttons
- Supports both `bonanza` and `memberwd` module types

**Code Reduction:**
- `AdminDBBonanza.js`: 1425 → 1331 lines (-94 lines)

### ✅ NEW: Member WD Product Mismatch Endpoints

**New Endpoints (parity with Bonanza):**
| Endpoint | Purpose |
|----------|---------|
| `GET /api/memberwd/admin/diagnose-product-mismatch` | Preview records in wrong databases |
| `POST /api/memberwd/admin/repair-product-mismatch` | Move records to correct databases |

---

## Previous Update: Real-Time Invalidation of Conflicting Assignments (2026-02-05)

### ✅ Automatic Conflict Resolution

**When a reservation is approved:**
1. System finds all records for that customer assigned to OTHER staff
2. Records in `customer_records`, `bonanza_records`, and `memberwd_records` are marked as `invalid`
3. Invalid reason: "Customer reserved by {staff_name}"
4. Affected staff receive a notification of type `record_invalidated_reserved`

**Implemented in 3 endpoints:**
- `PATCH /api/reserved-members/{id}/approve` - Manual approval by admin
- `POST /api/reserved-members` - Admin auto-approved reservations
- `POST /api/reserved-members/bulk` - Bulk reservation creation

**Response includes:**
- `invalidated_records` - Count of records marked invalid
- `notified_staff_count` - Number of staff notified
- `invalidated_conflicts` - (bulk endpoint) Total conflicts resolved

### ✅ UI Enhancement: Visual Feedback for Invalidation

**Toast notifications now show:**
- ✓ Request/Reservation approved
- 📋 X conflicting record(s) invalidated
- 🔔 Y staff member(s) notified

**Updated components:**
- `/app/frontend/src/components/AdminReservedMembers.js` - `handleApprove`, `handleAddMember`, `handleBulkAdd`
- `/app/frontend/src/components/ReservedMemberCRM.js` - `handleApprove`

### Helper Function: `invalidate_customer_records_for_other_staff`
- Location: `/app/backend/routes/records.py` (lines 24-110)
- Checks all 3 collections: `customer_records`, `bonanza_records`, `memberwd_records`
- Uses case-insensitive matching on customer ID fields
- Supports multiple customer ID field names (Username, USERNAME, USER, ID, etc.)

---

## Previous Update: Reserved Member Assignment Protection (2026-02-05)

### 🚨 CRITICAL Bug Fixes

**Bug #1: Manual Assignment Not Checking Reserved Members**
- `/bonanza/assign` and `/memberwd/assign` did NOT check reserved members
- ✅ FIXED: Now blocks assignment of reserved members and shows warning

**Bug #2: Random Assignment Including Deleted Reserved Members**  
- `/bonanza/assign-random` and `/memberwd/assign-random` checked ALL reserved members
- This meant deleted reserved members were still being excluded
- ✅ FIXED: Now only checks `status: 'approved'` reserved members
- Customers removed from reserved members are now available for new assignments

**Bug #3: Reserved Member Conflicts (Assigned to Wrong Staff)**
- Records were being assigned to staff A while reserved by staff B
- ✅ NEW: Added diagnose & fix endpoints
- ✅ NEW: "Fix Reserved Conflicts" button in UI

### Reserved Member Lifecycle (Fully Synced)
1. Customer reserved by Staff A → Added to `reserved_members` with `status: 'approved'`
2. Customer excluded from random assignment to other staff
3. Grace period expires (no omset in X days) → Moved to `deleted_reserved_members`
4. Customer becomes available for new assignments in ALL systems:
   - DB Bonanza random assignment ✅
   - Member WD random assignment ✅
   - Manual assignment ✅
5. Bonus check submissions cleaned up ✅
6. **NEW:** Conflicting records auto-invalidated when reservation approved ✅

### Key Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/bonanza/admin/diagnose-reserved-conflicts` | Find conflicts |
| `POST /api/bonanza/admin/fix-reserved-conflicts` | Reassign to correct staff |
| `GET /api/memberwd/admin/diagnose-reserved-conflicts` | Find conflicts |
| `POST /api/memberwd/admin/fix-reserved-conflicts` | Reassign to correct staff |
| `PATCH /api/reserved-members/{id}/approve` | Approve reservation + auto-invalidate conflicts |
| `POST /api/reserved-members/bulk` | Bulk create + auto-invalidate conflicts |

## Previous Updates

### ✅ Bug Fix: Staff RDP vs Product RDP Mismatch
- **Issue:** Staff's total RDP count didn't match sum of Product Summary RDP counts
- **Root Cause:** Product Summary used `is_global_ndp` while Staff used `is_staff_ndp`
  - Global NDP = customer's first deposit EVER
  - Staff NDP = customer's first deposit WITH THIS STAFF
- **Fix:** Changed Product Summary to use `is_staff_ndp` for consistency
- **Files Fixed:**
  - `/app/backend/routes/daily_summary.py` - lines 201-209
  - `/app/backend/routes/omset.py` - lines 596-604
- **Result:** Staff RDP sum now equals Product RDP sum

### ✅ Bug Fix: Reserved Member Cleanup (2026-02-04)
- **Root Cause 1:** Old reserved member records used `customer_name` field instead of `customer_id`
  - Fix: Now supports both field names: `customer_id` OR `customer_name`
- **Root Cause 2:** Days calculation used datetime comparison instead of date-only
  - Fix: Now uses `.date()` comparison for accurate day count
- **Result:** Members with `days_since >= grace_period` are now correctly deleted

### ✅ No-Deposit Cleanup (2026-02-04)
- Members with NO deposit record are now deleted immediately on cleanup
- Stored with reason: `no_deposit`

### Data Sync Dashboard (2026-02-03)
- **Health Check System** - Real-time monitoring of data integrity
  - Health score calculation (0-100%)
  - Detection of orphaned data, sync conflicts
  - Collection stats and scheduler status
- **Auto-Repair Tools** - One-click fixes for detected issues
  - Fix orphaned reserved members
  - Clean orphaned bonus submissions
  - Sync attendance-leave conflicts
  - Populate missing `last_omset_date` values
- **Feature Sync Status** - Visual status of all sync points
- **Activity Logging** - Audit trail of repairs

### ✅ Completed Sync Features (All 26 tests passed):

1. **Attendance + Leave Integration**
   - Staff with approved leave are NOT marked late when checking in
   - `has_approved_leave` and `leave_type` stored in attendance record

2. **Lateness Fees + Leave Integration**
   - Fee calculation now EXCLUDES days with approved leave
   - Query filters out records where `has_approved_leave=True`

3. **Bonus Check Expiration Fix**
   - Uses `record_date` from omset_records (actual deposit date)
   - NOT `approved_at` (reservation approval date)

4. **Reserved Member Cleanup Fix**
   - Grace period calculated from `last_omset_date` (customer's last deposit)
   - NOT from reservation date

5. **Manual Delete Sync**
   - Deleting a reserved member also cleans up `bonus_check_submissions`

6. **User Delete Cascade**
   - Deleting a user cascades to: `reserved_members`, `bonus_check_submissions`, `notifications`, `attendance_records`, `leave_requests`, `izin_records`

7. **At-Risk Alert Bug Fix**
   - Fixed variable name: `recently_alerted_ids` → `recently_alerted_keys`

### Previous Bug Fixes (2026-02-03):
1. **Grace Period Cleanup Bug** - Scheduler now ALWAYS starts for cleanup jobs
2. **Database Count Bug** - Formula: `available = total - assigned - archived - excluded`

### Frontend Components:
- `/app/frontend/src/components/shared/` - 9 reusable components
- `/app/frontend/src/components/DataSyncDashboard.js` - NEW monitoring dashboard

## Features Implemented

### Member WD CRM
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Batch card system for staff
- [x] Validation workflow (valid/invalid)
- [x] Auto-replace invalid records (configurable)
- [x] Max replacements per batch limit (default: 10)
- [x] Recall assigned records back to available pool
- [x] Dismiss orphaned invalid alerts
- [x] Excluded count (reserved members)
- [x] Archived count display

### DB Bonanza
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Validation workflow (valid/invalid)
- [x] Auto-replace invalid records (configurable)
- [x] Max replacements per database limit (default: 10)
- [x] Recall assigned records back to available pool
- [x] Dismiss orphaned invalid alerts
- [x] Excluded count (reserved members)
- [x] Archived count display

### Reserved Members
- [x] Grace period cleanup (daily at 00:01 WIB)
- [x] Deleted - No Omset archive
- [x] Manual cleanup trigger endpoint
- [x] Configurable grace period per product

## Settings

### Member WD Settings (`memberwd_settings`)
```json
{
  "id": "memberwd_settings",
  "auto_replace_invalid": false,
  "max_replacements_per_batch": 10
}
```

### DB Bonanza Settings (`bonanza_settings`)
```json
{
  "id": "bonanza_settings",
  "auto_replace_invalid": false,
  "max_replacements_per_batch": 10
}
```

### Reserved Member Config (`reserved_member_config`)
```json
{
  "id": "reserved_member_config",
  "global_grace_days": 30,
  "warning_days": 7,
  "product_overrides": []
}
```

## Key API Endpoints

### Data Sync (NEW)
- `GET /api/data-sync/health-check` - Run comprehensive health check
- `POST /api/data-sync/repair?repair_type=all` - Auto-repair detected issues
- `GET /api/data-sync/sync-status` - Get feature sync status
- `GET /api/data-sync/activity-log` - Get repair history

### Member WD
- `GET/PUT /api/memberwd/admin/settings` - Settings
- `POST /api/memberwd/admin/recall-records` - Recall
- `POST /api/memberwd/admin/dismiss-invalid-alerts` - Dismiss alerts
- `POST /api/memberwd/admin/process-invalid/{staff_id}` - Process invalid records

### DB Bonanza
- `GET/PUT /api/bonanza/admin/settings` - Settings
- `POST /api/bonanza/admin/recall-records` - Recall
- `POST /api/bonanza/admin/dismiss-invalid-alerts` - Dismiss alerts
- `POST /api/bonanza/admin/process-invalid/{staff_id}` - Process invalid records

### Reserved Members
- `GET/PUT /api/reserved-members/cleanup-config` - Grace period config
- `POST /api/scheduled-reports/reserved-member-cleanup-run` - Manual cleanup trigger
- `GET /api/scheduled-reports/reserved-member-cleanup-preview` - Preview cleanup

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React.js
- Database: MongoDB (Motor async driver)
- UI: Tailwind CSS + Shadcn components
- Scheduler: APScheduler (daily cleanup jobs)

## Scheduled Jobs
| Job | Schedule | Description |
|-----|----------|-------------|
| Reserved Member Cleanup | 00:01 WIB | Archive members without omset past grace period |
| OMSET Trash Cleanup | 00:05 WIB | Delete trash older than 30 days |

## Pending Tasks
- P1: Further frontend refactoring of `AdminDBBonanza.js` (1331 lines) and `AdminMemberWDCRM.js` (1526 lines) - could be broken down further

## Future Enhancements
- Real-time WebSocket alerts for data inconsistencies
- Scheduled health check reports via Telegram
- Data validation before import

## Known Issues
None - all sync features verified working (100% health score)
