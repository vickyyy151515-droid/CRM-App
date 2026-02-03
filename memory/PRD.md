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

## Latest Update: Bug Fixes (2026-02-03)

### Fixed Bugs:
1. **Grace Period Cleanup Bug** - Reserved members without omset were NOT being moved to "Deleted - No Omset" archive
   - Root cause: Scheduler only started when reports were enabled; cleanup jobs never ran
   - Fix: Scheduler now ALWAYS starts for cleanup jobs (00:01 WIB daily)

2. **Database Count Bug** - Available/assigned counts were incorrect after re-assigning invalid records
   - Root cause: MemberWD didn't subtract archived records from available count
   - Fix: Formula now correctly uses: `available = total - assigned - archived - excluded`

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
None - all features complete and bugs fixed

## Known Issues
None
