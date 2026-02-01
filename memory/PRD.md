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

### Bug Fixed: Stuck Invalid Records Alert
When records were recalled that had `validation_status='invalid'`, they would still show in the "Invalid Records Alert" panel. Fixed by:
1. Changing the invalid records query to only show `status='assigned'` records
2. Adding a "Dismiss All Invalid Alerts" button to clear orphaned alerts

### API Endpoints
- `POST /api/memberwd/admin/recall-records` - Recall records to available pool
- `POST /api/memberwd/admin/dismiss-invalid-alerts` - Clear orphaned invalid alerts

### Changes made
- Backend: Added `recall-records` and `dismiss-invalid-alerts` endpoints
- Backend: Fixed `invalid-records` query to only show assigned records
- Frontend: Added "Select All Assigned", "Recall Selected", and "Dismiss All Invalid Alerts" buttons
- Frontend: Enabled checkboxes for assigned records

## Features Implemented

### Member WD Module
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Batch card system for staff
- [x] Validation workflow (valid/invalid)
- [x] Invalid record processing with auto-replacement
- [x] **Recall assigned records back to available pool** (NEW)
- [x] **Dismiss orphaned invalid alerts** (NEW)
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

## Key Endpoints

### Member WD
- `POST /api/memberwd/upload` - Upload database
- `POST /api/memberwd/assign-random` - Random assignment
- `GET /api/memberwd/staff/batches` - Staff batches
- `POST /api/memberwd/staff/validate` - Mark valid/invalid
- `POST /api/memberwd/admin/process-invalid/{staff_id}` - Archive invalid + auto-replace
- `POST /api/memberwd/admin/recall-records` - Recall assigned records (NEW)
- `POST /api/memberwd/admin/dismiss-invalid-alerts` - Clear orphaned alerts (NEW)

## Pending Tasks
None - features complete

## Known Issues
None
