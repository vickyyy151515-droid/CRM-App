# CRM Boost PRD

## Original Problem Statement
CRM system for managing member data with batch assignment to staff. Core feature is the "Member WD" module where:
- Admin uploads member databases
- Admin assigns records to staff in batches
- Staff validates records (valid/invalid)
- Admin replaces invalid records with new ones
- **Admin can recall assigned records back to available pool**

## Latest Feature: Recall Records (2026-02-01)

### What it does
Allows admin to recall (take back) assigned records from staff and return them to the available pool.

### How it works
1. Admin expands a database in Member WD CRM
2. Admin can select assigned records using checkboxes or "Select All Assigned" button
3. Admin clicks "Recall Selected" button
4. Records are returned to available status, removed from staff's list

### API Endpoint
- `POST /api/memberwd/admin/recall-records`
- Request: `{ "record_ids": ["id1", "id2", ...] }`
- Response: `{ "success": true, "recalled_count": N, "message": "..." }`

### Changes made
- Backend: Added `recall-records` endpoint in `routes/memberwd.py`
- Frontend: Added "Select All Assigned" and "Recall Selected" buttons in `AdminMemberWDCRM.js`
- Frontend: Enabled checkboxes for assigned records (previously only available records had checkboxes)

## Features Implemented

### Member WD Module
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Batch card system for staff
- [x] Validation workflow (valid/invalid)
- [x] Invalid record processing with auto-replacement
- [x] **Recall assigned records back to available pool** (NEW)
- [x] Excluded count (reserved members in available pool)

### Cek Bonus Member
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
- `POST /api/memberwd/admin/recall-records` - Recall assigned records (NEW)

## Data Models

### MemberWDRecord
```
{
  id: string,
  database_id: string,
  database_name: string,
  batch_id: string,
  assigned_to: string,
  status: 'available' | 'assigned' | 'invalid_archived',
  validation_status: 'validated' | 'invalid' | null,
  recalled_at: string,     // NEW - when record was recalled
  recalled_by: string,     // NEW - who recalled
  recalled_by_name: string // NEW
}
```

## Pending Tasks
None - recall feature is complete

## Known Issues
None
