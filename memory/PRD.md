# CRM Application - Product Requirements Document

## Original Problem Statement
Build a Customer Relationship Management (CRM) application where:
- Admins can upload customer databases (CSV or Excel)
- Staff can request to download/access the uploaded databases
- System manages customer record assignments and reservations

## User Personas
1. **Admin**: Manages databases, products, users, approves requests, views analytics
2. **Staff**: Browses databases, requests records, contacts customers via WhatsApp, marks reachability status

## Core Features Implemented

### Phase 1: MVP (Completed)
- User authentication (Admin/Staff roles)
- Database upload (CSV/Excel) with product categorization
- Staff download request workflow with admin approval

### Phase 2: Record-Level Assignment (Completed)
- Shifted from file downloads to individual record assignments
- Staff requests quantity of records from a database
- Admin approves → records get assigned to staff
- Staff sees assigned customers with WhatsApp contact capability

### Phase 3: WhatsApp Integration (Completed)
- Copy full WhatsApp URL button (bypasses network blocks)
- WhatsApp reachability status tracking (Ada/Tidak/Ceklis1)
- **Response status tracking (Ya/Tidak)** - track if customer responded
- Staff marks customer WhatsApp status and response status
- Admin sees all statuses in dashboards

### Phase 4: Admin Dashboards (Completed)
- **All Assignments View**: Global view of all assigned records
- **Staff Progress & Quality**: Analytics dashboard with filters (Today, All Time, etc.)
- Performance metrics: records checked, quality rate

### Phase 5: Reserved Member CRM (Completed - Jan 13, 2026)
- **Staff Request Flow**: Staff requests customer name + selects product → pending → admin approval
- **Admin Direct Add**: Admin assigns customer to staff with product selection (auto-approved)
- **Product Categorization**: Each reservation belongs to a specific product
- **Duplicate Prevention**: Case-insensitive check within same product, shows which staff owns the name
- **Admin Controls**: Approve/Reject requests, Move reservations, Delete
- **Visibility**: All approved reservations visible to all staff
- **Filtering**: Filter by product and status (All/Pending/Approved)
- **Notification Badges**: Red badges in sidebar showing pending counts (auto-refresh every 30s)

### Phase 6: OMSET CRM (Completed - Jan 13, 2026)
- **Staff Data Entry**: Staff can add customer deposits with:
  - Customer Name and ID (manual entry)
  - Nominal amount and Kelipatan (multiplier)
  - Auto-calculated Depo Total (Nominal × Kelipatan)
  - Keterangan (notes)
- **Product Separation**: Each deposit is linked to a specific product
- **Date-based Sheets**: Records organized by date with quick date selector
- **Edit/Delete**: Staff can modify their own records
- **Admin Summary View**: 
  - Overall totals (Records, Nominal, OMSET)
  - Daily summary with OMSET per day
  - Staff performance breakdown
  - Product summary with averages
- **Admin Detail View**: Expandable daily records with full details
- **Filters**: Date range (Today/Yesterday/Last 7/30 days/Custom), Product, Staff

### Phase 7: Batch System (Completed - Jan 13, 2026)
- **Batch-based Record Grouping**: Staff's assigned customers organized into selectable "batches"
- **Legacy Batch**: Records assigned before this feature grouped into "Legacy" batch
- **Live Stats**: Batch cards display WhatsApp status (Ada, Ceklis 1, Tidak) and Respond status (Ya, Tidak) counts
- **Custom Titles**: Staff can set custom titles for each batch

### Phase 8: DB Bonanza & Member WD CRM (Completed - Jan 13, 2026)
- **Admin Upload**: Upload CSV/Excel files with product selection
- **Product Categorization**: Each database linked to a specific product
- **Quick Random Assignment**: Assign random records to staff, excluding reserved members
- **Manual Selection**: Admin can manually select and assign specific records
- **Staff View**: Staff see their assigned records grouped by database with product filtering
- **Separate Collections**: DB Bonanza and Member WD CRM operate on separate MongoDB collections

### Phase 9: Product Selection for DB Bonanza & Member WD CRM (Completed - Jan 13, 2026)
- **Admin Upload with Product**: Product selection required when uploading new databases
- **Product Filter for Admin**: Filter databases by product in admin view
- **Product Filter for Staff**: Filter assigned records by product in staff view
- **Legacy Data Handling**: Databases without product show "Unknown" as product name

## Tech Stack
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + PyMongo
- **Database**: MongoDB

## Key API Endpoints
- `/api/auth/*` - Authentication
- `/api/products` - Product management
- `/api/databases` - Database upload/management
- `/api/download-requests` - Record request workflow
- `/api/my-assigned-records` - Staff's assigned customers
- `/api/customer-records/{id}/whatsapp-status` - Update WhatsApp status
- `/api/reserved-members` - Reserved member CRM (POST/GET/PATCH/DELETE)
- `/api/staff-users` - Get list of staff members

## Credentials
- **Admin**: admin@crm.com / admin123
- **Staff**: staff@crm.com / staff123

---

## Backlog / Upcoming Tasks

### P1: OMSET CRM Page
- Analyze Excel file `/app/artifacts/90xd5vgy_MASTER OMSET CRM .xlsx`
- Implement new page in Staff panel replicating Excel functionality
- Likely involves forms for data entry and tables with calculations

### P2: Potential Enhancements
- Export functionality for reports
- Bulk operations for admin
- Mobile-responsive improvements
- Notification system for request updates
