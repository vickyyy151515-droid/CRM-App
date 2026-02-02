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

## Latest Update: DB Bonanza Feature Parity (2026-02-02)

Implemented all Member WD CRM features in DB Bonanza:
- Settings (auto-replace toggle, max limit)
- Auto-replace invalid records
- Recall records
- Dismiss invalid alerts
- Excluded count

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

### DB Bonanza
- [x] Database upload (CSV/Excel)
- [x] Random assignment with reserved member filtering
- [x] Validation workflow (valid/invalid)
- [x] Auto-replace invalid records (configurable)
- [x] Max replacements per database limit (default: 10)
- [x] Recall assigned records back to available pool
- [x] Dismiss orphaned invalid alerts
- [x] Excluded count (reserved members)

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

## Key API Endpoints

### Member WD
- `GET/PUT /api/memberwd/admin/settings` - Settings
- `POST /api/memberwd/admin/recall-records` - Recall
- `POST /api/memberwd/admin/dismiss-invalid-alerts` - Dismiss alerts

### DB Bonanza
- `GET/PUT /api/bonanza/admin/settings` - Settings
- `POST /api/bonanza/admin/recall-records` - Recall
- `POST /api/bonanza/admin/dismiss-invalid-alerts` - Dismiss alerts

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: React.js
- Database: MongoDB (Motor async driver)
- UI: Tailwind CSS + Shadcn components

## Pending Tasks
None - all features complete

## Known Issues
None
