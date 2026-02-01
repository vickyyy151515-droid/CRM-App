# CRM Boost PRD

## Original Problem Statement
CRM system for managing member data with batch assignment to staff. Core feature is the "Member WD" module where:
- Admin uploads member databases
- Admin assigns records to staff in batches
- Staff validates records (valid/invalid)
- Admin replaces invalid records with new ones

## Critical Issue (P0) - Member WD Batch Data Integrity

### Problem
When staff marks records as "invalid" and admin assigns replacements:
1. Replacements were going to wrong batches (using `batch_ids[0]` instead of specific batch)
2. Previous repair logic used fallback methods that assigned to ANY matching batch
3. This caused incorrect record counts and distributions in the UI

### Root Cause
1. `process-invalid` endpoint assigned ALL replacements to first batch
2. `repair-batches` used broad fallback logic instead of precise matching
3. Previous migrations deleted batches but kept `batch_id` on archived records

### Solution Implemented (2026-02-01)
1. **Fixed `process-invalid`**: Groups invalid records by `batch_id + database_id`, each replacement goes to EXACT same batch
2. **Fixed `repair-batches`**: Uses precise linking:
   - Method 1: Archived record's `batch_id` if exists
   - Method 2: Exact timestamp match (`staff_id + database_name + assigned_at`)
   - Method 3: Same-day closest timestamp match
   - Method 4: Last resort same staff+database fallback
3. **Enhanced `diagnose-batches`**: Staff-level summary, health status, detailed orphan tracing

### Key Principle
**1 invalid = 1 replacement, in the SAME batch, from the SAME product**

## Features Implemented

### Member WD Module
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Batch card system for staff
- [x] Validation workflow (valid/invalid)
- [x] Invalid record processing with auto-replacement
- [x] Diagnose and repair tools for data integrity
- [x] Excluded count (reserved members in available pool)

### Cek Bonus Member (2026-01)
- [x] Staff submission form
- [x] Customer ID validation against reserved members
- [x] Admin review page
- [x] CSV/Excel export

### Other Modules
- Authentication (JWT + TOTP)
- Product management
- Leaderboard & Analytics
- Attendance tracking
- Inventory management
- Scheduled reports

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React.js
- Database: MongoDB (Motor async driver)
- UI: Tailwind CSS + Shadcn components

## Key Endpoints

### Member WD
- `POST /api/memberwd/upload` - Upload database
- `POST /api/memberwd/assign-random` - Random assignment
- `GET /api/memberwd/staff/batches` - Staff batches
- `POST /api/memberwd/staff/validate` - Mark valid/invalid
- `POST /api/memberwd/admin/process-invalid/{staff_id}` - Archive invalid + auto-replace
- `GET /api/memberwd/admin/diagnose-batches` - Diagnose data issues
- `POST /api/memberwd/admin/repair-batches` - Fix data issues

## Data Models

### MemberWDRecord
```
{
  id: string,
  database_id: string,
  database_name: string,
  batch_id: string,  // Links to batch
  assigned_to: string,  // staff_id
  status: 'available' | 'assigned' | 'invalid_archived',
  validation_status: 'validated' | 'invalid' | null,
  auto_replaced: boolean,  // True if this is a replacement
  replaced_invalid_ids: string[]  // IDs of invalid records this replaced
}
```

### Batch
```
{
  id: string,
  staff_id: string,
  database_id: string,
  database_name: string,
  created_at: string,  // ISO timestamp - used for matching
  initial_count: number,
  current_count: number
}
```

## Pending Tasks
1. Verify fix on production environment
2. Clean up deprecated migration code after fix is confirmed

## Known Issues
- None after 2026-02-01 fix (pending production verification)
