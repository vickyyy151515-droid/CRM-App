#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Test and verify Reserved Member Conflict (pending omset workflow) and Duplicate Customer Log features"

backend:
  - task: "POST /api/omset creates record with pending status when customer is on another staff reserved list"
    implemented: true
    working: true
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Code implemented. When creating omset, checks reserved_members collection for conflicts. If customer is reserved by another staff, sets approval_status to 'pending' and creates a notification for admin."
        - working: true
          agent: "testing"
          comment: "Testing agent confirmed: POST /api/omset correctly sets approval_status=pending when customer is reserved by another staff."
        - working: true
          agent: "main"
          comment: "Fixed bug: added approval_status and conflict_info fields to OmsetRecord model so they appear in API response. Staff can now see pending warning toast."

  - task: "POST /api/omset creates record with approved status when no reserved member conflict"
    implemented: true
    working: true
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Code implemented. Non-conflicting omset records should get approval_status='approved' by default."
        - working: true
          agent: "testing"
          comment: "Testing agent confirmed."

  - task: "GET /api/omset/pending returns all pending omset records (admin only)"
    implemented: true
    working: true
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Curl test passed - returns empty list [] when no pending records. Returns 200."

  - task: "POST /api/omset/{id}/approve approves a pending record (admin only)"
    implemented: true
    working: "NA"
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Code implemented. Sets approval_status to 'approved', updates reserved_members last_omset_date, and sends notification to staff."

  - task: "POST /api/omset/{id}/decline declines and deletes a pending record (admin only)"
    implemented: true
    working: "NA"
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Code implemented. Deletes the record and sends notification to staff."

  - task: "GET /api/omset/duplicates returns duplicate customer records by different staff (admin only)"
    implemented: true
    working: true
    file: "backend/routes/omset.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Curl test passed - returns {total_duplicates: 0, total_records_involved: 0, duplicates: []}. Uses MongoDB aggregation to find same customer+product recorded by multiple staff."

frontend:
  - task: "Admin OMSET CRM Pending tab shows pending records with approve/decline actions"
    implemented: true
    working: "NA"
    file: "frontend/src/components/shared/OmsetPendingApprovals.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Screenshot verified: Pending tab renders correctly, shows 'No pending approvals' when empty. Has approve/decline buttons per record."

  - task: "Admin OMSET CRM Duplicates tab shows duplicate records with expandable details"
    implemented: true
    working: "NA"
    file: "frontend/src/components/shared/OmsetDuplicates.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Screenshot verified: Duplicate tab renders, shows stats cards (Duplicate Groups, Records Involved), date filters, and 'No duplicates found' when empty."

  - task: "Staff OMSET CRM shows pending status warning when omset conflicts with reserved member"
    implemented: true
    working: "NA"
    file: "frontend/src/components/StaffOmsetCRM.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Code shows toast warning when record has approval_status='pending'. Also shows pending badge on records in list."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 3
  run_ui: true

test_plan:
  current_focus:
    - "Reserved Member Conflict pending workflow (end-to-end)"
    - "Duplicate Customer Log feature"
    - "Approve and Decline pending omset actions"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "Two new features implemented and need comprehensive testing: 1) Reserved Member Conflict - when staff creates omset for customer reserved by another staff, it should be set to 'pending' and require admin approval. 2) Duplicate Customer Log - admin can view all instances where same customer/product is recorded by multiple staff. ALSO: Critical fix for NDP/RDP sync after delete - when an admin deletes a staff's omset record, the NDP/RDP customer_type on remaining records is now recalculated automatically. The `recalculate_customer_type()` helper in db_operations.py is called after delete, approve, decline, and restore operations. Additionally, all calculation endpoints (summary, bonus, daily_summary, leaderboard, analytics, retention, report) now filter out 'pending' records via `add_approved_filter()`. Only approved records count in NDP/RDP and omset total calculations. Test workflow: 1) Create 3 omset records for same customer/product/staff on different dates. 2) Delete the first one (NDP). 3) Verify the second record becomes NDP and all summary/bonus/leaderboard counts update. 4) Also test the pending workflow by creating a reserved member, then having a different staff create omset for that customer. Admin credentials: vicky@crm.com / vicky123. Staff credentials: staff@crm.com / staff123."