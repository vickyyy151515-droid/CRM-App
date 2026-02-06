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

user_problem_statement: "Backend refactoring P2 - Replace inline repair/health-check/product-mismatch/reserved-conflicts logic in memberwd.py and bonanza.py with shared utility functions from repair_helpers.py"

backend:
  - task: "MemberWD data-health endpoint uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored get_memberwd_data_health to use run_full_health_check + check_batch_health. Curl test passed: returns is_healthy, databases, batches."

  - task: "MemberWD diagnose-product-mismatch uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored diagnose_memberwd_product_mismatch to use shared diagnose_product_mismatch. Curl test passed."

  - task: "MemberWD repair-product-mismatch uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored repair_memberwd_product_mismatch to use shared repair_product_mismatch."

  - task: "MemberWD diagnose-reserved-conflicts uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored diagnose_memberwd_reserved_conflicts to use shared diagnose_reserved_conflicts. Curl test passed."

  - task: "MemberWD fix-reserved-conflicts uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored fix_memberwd_reserved_conflicts to use shared fix_reserved_conflicts."

  - task: "Bonanza diagnose-product-mismatch uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored diagnose_product_mismatch to use shared utility. Curl test passed."

  - task: "Bonanza repair-product-mismatch uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored repair_product_mismatch to use shared utility."

  - task: "Bonanza diagnose-reserved-conflicts uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored diagnose_reserved_conflicts to use shared utility. Curl test passed."

  - task: "Bonanza fix-reserved-conflicts uses shared utilities"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Refactored fix_reserved_conflicts to use shared utility."

  - task: "MemberWD repair-data still works (already uses shared utils)"
    implemented: true
    working: true
    file: "backend/routes/memberwd.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Was already refactored. Curl test confirmed: success=True, Fixed 0 issues."

  - task: "Bonanza repair-data still works (already uses shared utils)"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Was already refactored. Curl test confirmed: success=True, Fixed 0 issues."

  - task: "Bonanza data-health still works (already uses shared utils)"
    implemented: true
    working: true
    file: "backend/routes/bonanza.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        - working: true
          agent: "main"
          comment: "Was already refactored. Curl test confirmed: is_healthy=True."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "MemberWD data-health endpoint uses shared utilities"
    - "MemberWD diagnose-product-mismatch uses shared utilities"
    - "MemberWD repair-product-mismatch uses shared utilities"
    - "MemberWD diagnose-reserved-conflicts uses shared utilities"
    - "MemberWD fix-reserved-conflicts uses shared utilities"
    - "Bonanza diagnose-product-mismatch uses shared utilities"
    - "Bonanza repair-product-mismatch uses shared utilities"
    - "Bonanza diagnose-reserved-conflicts uses shared utilities"
    - "Bonanza fix-reserved-conflicts uses shared utilities"
    - "MemberWD repair-data still works"
    - "Bonanza repair-data still works"
    - "Bonanza data-health still works"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "Completed P2 backend refactoring for both memberwd.py and bonanza.py. Extracted 5 shared functions (check_batch_health, diagnose_product_mismatch, repair_product_mismatch, diagnose_reserved_conflicts, fix_reserved_conflicts) into repair_helpers.py. Also added helper functions (_build_reserved_map, _find_customer_id_in_row) and centralized USERNAME_FIELDS constant. All curl tests pass. Need full regression test of all admin endpoints for both modules."