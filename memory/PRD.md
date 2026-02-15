# CRM Pro - Product Requirements Document

## Original Problem Statement
CRM application for sales tracking, customer retention, and staff management. Includes Member WD assignment, DB Bonanza, reserved member protection, analytics dashboards, and more.

## Architecture
- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Shadcn/ui + Recharts
- **Backend**: Python + FastAPI + MongoDB (via pymongo/motor)
- **Auth**: JWT-based with master_admin and staff roles

## What's Been Implemented

### Core Features (Complete)
- Sales tracking and customer records management
- Staff management with role-based access
- Member WD CRM with batch assignment system
- DB Bonanza assignment system
- Reserved member protection system (with permanent toggle)
- Advanced Analytics page with 10+ interactive charts and drill-downs
- Data sync and health check utilities
- Scheduled cleanup jobs for expired reservations

### P0 Bug Fix: Reserved Member Assignment (2026-02-15) - COMPLETE
**Root Cause**: Reserved member checks were built using `customer_id OR customer_name` (only adding ONE identifier per member). If a member had both fields with different values, the check could be bypassed when the uploaded data matched the un-added field.

**Fix**: Created centralized utility (`backend/utils/reserved_check.py`) that:
1. Adds BOTH customer_id AND customer_name to the reserved set
2. Checks ALL row_data values field-agnostically (no hardcoded column names)
3. Is used by ALL code paths: upload, manual assign, random assign, auto-replace, process-invalid

**Files Changed**:
- NEW: `backend/utils/reserved_check.py` - Centralized utility
- UPDATED: `backend/routes/memberwd.py` - All assignment paths
- UPDATED: `backend/routes/bonanza.py` - All assignment paths
- UPDATED: `backend/utils/repair_helpers.py` - Conflict detection

**Testing**: 27/27 tests passed (16 new + 11 existing)

## Prioritized Backlog

### P1 - Upcoming
- UI/UX consistency standardization across the app

### P2 - Future
- "Smart Message Queue" WhatsApp follow-up app
- Staging/testing environment setup
- Centralized logging & monitoring (Sentry/LogRocket)

## Key API Endpoints
- `POST /api/memberwd/upload` - Upload member database
- `POST /api/memberwd/assign` - Manual assign records
- `POST /api/memberwd/assign-random` - Random assign records
- `POST /api/bonanza/upload` - Upload bonanza database
- `POST /api/bonanza/assign` - Manual assign bonanza records
- `POST /api/bonanza/assign-random` - Random assign bonanza records
- `PATCH /api/reserved-members/{id}/permanent` - Toggle permanent status
- `GET /api/analytics/drilldown/*` - Chart drill-down data

## DB Schema (Key Collections)
- `reserved_members`: {customer_id, customer_name, staff_id, staff_name, status, is_permanent, product_id}
- `memberwd_records`: {row_data, status, assigned_to, is_reserved_member, batch_id}
- `bonanza_records`: {row_data, status, assigned_to, is_reserved_member}
- `customer_records`: {row_data, status, assigned_to}
