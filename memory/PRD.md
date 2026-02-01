# CRM Boost PRD

## Original Problem Statement
CRM system for managing member data with batch assignment to staff.

## Latest Feature: Auto-Replace Invalid Records (2026-02-01)

### What it does
When staff marks a record as invalid, the system can automatically assign a replacement record from the same database.

### Settings
- **Auto-Replace Invalid Records** (toggle): Enable/disable auto-replacement
- **Max Replacements Per Batch** (number): Limit how many invalid records can be replaced per batch card (default: 10)

### How it works
1. Staff marks record(s) as invalid
2. If auto-replace is enabled:
   - System finds available records from SAME database
   - Checks if batch hasn't exceeded replacement limit
   - Auto-assigns replacement to staff in same batch
   - Archives the invalid record
3. If no records available or limit reached:
   - Staff sees warning notification
   - Admin notification created for manual processing

### API Endpoints
- `GET /api/memberwd/admin/settings` - Get settings
- `PUT /api/memberwd/admin/settings` - Update settings
  - Body: `{ "auto_replace_invalid": bool, "max_replacements_per_batch": int }`

### Key Rules
- Replacement MUST be from same database_id (same product)
- Replacement goes to SAME batch as invalid record
- Maximum replacements per batch is configurable (default: 10)
- If staff has 11 invalid in 1 batch with limit 10 → only 10 can be replaced

## Features Implemented

### Member WD Module
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Batch card system for staff
- [x] Validation workflow (valid/invalid)
- [x] Invalid record processing with auto-replacement
- [x] **Auto-replace invalid records** (NEW - configurable)
- [x] **Max replacements per batch limit** (NEW - configurable)
- [x] Recall assigned records back to available pool
- [x] Dismiss orphaned invalid alerts
- [x] Excluded count (reserved members in available pool)

### Other Modules
- Authentication (JWT + TOTP)
- Product management
- Leaderboard & Analytics
- Attendance tracking
- Inventory management
- Scheduled reports
- Cek Bonus Member

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React.js
- Database: MongoDB (Motor async driver)
- UI: Tailwind CSS + Shadcn components

## Data Models

### App Settings (memberwd_settings)
```
{
  id: 'memberwd_settings',
  auto_replace_invalid: boolean,
  max_replacements_per_batch: number,
  updated_at: string,
  updated_by: string
}
```

## Pending Tasks
None - features complete

## Known Issues
None
