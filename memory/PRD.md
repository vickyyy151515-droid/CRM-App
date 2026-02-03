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

## Latest Update: Grace Period Cleanup Fix (2026-02-04)

### ✅ Bug Fix: Reserved Member Cleanup Not Deleting Members
- **Root Cause 1:** Old reserved member records used `customer_name` field instead of `customer_id`
  - Fix: Now supports both field names: `customer_id` OR `customer_name`
- **Root Cause 2:** Days calculation used datetime comparison instead of date-only
  - Fix: Now uses `.date()` comparison for accurate day count
- **Result:** Members with `days_since >= grace_period` are now correctly deleted

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
