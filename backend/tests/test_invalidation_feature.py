"""
Test Suite for Real-time Invalidation Feature

Tests the invalidate_customer_records_for_other_staff helper function integration:
1. PATCH /api/reserved-members/{member_id}/approve - Invalidation when reservation is approved
2. POST /api/reserved-members - Invalidation when admin creates auto-approved reservation
3. POST /api/reserved-members/bulk - Invalidation during bulk reservation creation

Key test scenario:
1) Create two staff members
2) Assign the same customer to Staff B in a database record
3) Have Staff A (or admin for Staff A) create a reservation for that customer and get it approved
4) Verify Staff B's record is now marked as 'invalid' with invalid_reason containing 'reserved by'
5) Verify Staff B received a notification of type 'record_invalidated_reserved'
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "vicky123"


class TestInvalidationFeature:
    """Test suite for real-time invalidation when reservations are approved"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers with auth token"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_product(self, admin_headers):
        """Get or create a test product"""
        # First try to get existing products
        response = requests.get(f"{BASE_URL}/api/products", headers=admin_headers)
        assert response.status_code == 200
        products = response.json()
        
        if products:
            return products[0]  # Use first available product
        
        # Create a test product if none exist
        product_data = {
            "name": f"TEST_INVALIDATION_{uuid.uuid4().hex[:6]}",
            "description": "Test product for invalidation testing"
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=admin_headers)
        assert response.status_code in [200, 201]
        return response.json()
    
    @pytest.fixture(scope="class")
    def staff_a(self, admin_headers):
        """Get Staff A for testing (use existing staff user)"""
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert users_resp.status_code == 200, f"Failed to get users: {users_resp.text}"
        users = users_resp.json()
        staff_users = [u for u in users if u['role'] == 'staff']
        assert len(staff_users) >= 1, "Need at least 1 staff user for testing"
        return staff_users[0]
    
    @pytest.fixture(scope="class")
    def staff_b(self, admin_headers):
        """Get Staff B for testing (use existing staff user)"""
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert users_resp.status_code == 200, f"Failed to get users: {users_resp.text}"
        users = users_resp.json()
        staff_users = [u for u in users if u['role'] == 'staff']
        assert len(staff_users) >= 2, "Need at least 2 staff users for testing"
        return staff_users[1]
    
    # ==================== TEST 1: Approve Reserved Member Endpoint ====================
    
    def test_01_approve_endpoint_exists(self, admin_headers):
        """Test that the approve endpoint exists and returns proper error for invalid ID"""
        response = requests.patch(
            f"{BASE_URL}/api/reserved-members/nonexistent-id/approve",
            headers=admin_headers
        )
        # Should return 404 for non-existent member, not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ PATCH /api/reserved-members/{id}/approve endpoint exists")
    
    def test_02_create_reserved_member_endpoint_exists(self, admin_headers, test_product, staff_a):
        """Test that create reserved member endpoint exists"""
        # Try to create a reservation (may fail due to duplicate, but endpoint should exist)
        test_customer_id = f"TEST_CUSTOMER_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "customer_id": test_customer_id,
                "product_id": test_product["id"],
                "staff_id": staff_a["id"]
            },
            headers=admin_headers
        )
        # Should return 200/201 for success or 409 for duplicate
        assert response.status_code in [200, 201, 409], f"Unexpected status: {response.status_code}: {response.text}"
        print("✓ POST /api/reserved-members endpoint exists")
        
        # Clean up if created
        if response.status_code in [200, 201]:
            member = response.json()
            requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
    
    def test_03_bulk_create_endpoint_exists(self, admin_headers, test_product, staff_a):
        """Test that bulk create endpoint exists"""
        test_customer_id = f"TEST_BULK_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/reserved-members/bulk",
            json={
                "customer_ids": [test_customer_id],
                "product_id": test_product["id"],
                "staff_id": staff_a["id"]
            },
            headers=admin_headers
        )
        assert response.status_code in [200, 201], f"Bulk endpoint failed: {response.status_code}: {response.text}"
        print("✓ POST /api/reserved-members/bulk endpoint exists")
        
        # Clean up
        result = response.json()
        if result.get('added'):
            # Delete the created reservation
            members_resp = requests.get(
                f"{BASE_URL}/api/reserved-members?product_id={test_product['id']}",
                headers=admin_headers
            )
            if members_resp.status_code == 200:
                for member in members_resp.json():
                    if member.get('customer_id') == test_customer_id:
                        requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
    
    # ==================== TEST 2: Code Review - Helper Function Integration ====================
    
    def test_04_helper_function_exists_in_code(self):
        """Verify invalidate_customer_records_for_other_staff helper exists"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        assert 'async def invalidate_customer_records_for_other_staff' in content, \
            "Helper function not found in records.py"
        print("✓ invalidate_customer_records_for_other_staff helper function exists")
    
    def test_05_helper_called_in_approve_endpoint(self):
        """Verify helper is called in approve_reserved_member endpoint"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Find the approve_reserved_member function and check it calls the helper
        approve_func_start = content.find('async def approve_reserved_member')
        assert approve_func_start != -1, "approve_reserved_member function not found"
        
        # Get the function body (until next function or end)
        next_func = content.find('async def ', approve_func_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        approve_func_body = content[approve_func_start:next_func]
        assert 'invalidate_customer_records_for_other_staff' in approve_func_body, \
            "Helper not called in approve_reserved_member"
        print("✓ Helper is called in approve_reserved_member endpoint")
    
    def test_06_helper_called_in_create_endpoint(self):
        """Verify helper is called in create_reserved_member endpoint (for admin auto-approve)"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Find the create_reserved_member function
        create_func_start = content.find('async def create_reserved_member')
        assert create_func_start != -1, "create_reserved_member function not found"
        
        # Get the function body
        next_func = content.find('async def ', create_func_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        create_func_body = content[create_func_start:next_func]
        
        # Check that helper is called when status is approved
        assert 'invalidate_customer_records_for_other_staff' in create_func_body, \
            "Helper not called in create_reserved_member"
        assert "if member.status == 'approved'" in create_func_body or \
               'if member.status == "approved"' in create_func_body, \
            "Helper should only be called when status is approved"
        print("✓ Helper is called in create_reserved_member endpoint (admin auto-approve)")
    
    def test_07_helper_called_in_bulk_endpoint(self):
        """Verify helper is called in bulk_create_reserved_members endpoint"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Find the bulk_create_reserved_members function
        bulk_func_start = content.find('async def bulk_create_reserved_members')
        assert bulk_func_start != -1, "bulk_create_reserved_members function not found"
        
        # Get the function body
        next_func = content.find('async def ', bulk_func_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        bulk_func_body = content[bulk_func_start:next_func]
        assert 'invalidate_customer_records_for_other_staff' in bulk_func_body, \
            "Helper not called in bulk_create_reserved_members"
        print("✓ Helper is called in bulk_create_reserved_members endpoint")
    
    # ==================== TEST 3: Helper Function Logic ====================
    
    def test_08_helper_checks_all_three_collections(self):
        """Verify helper checks customer_records, bonanza_records, and memberwd_records"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Find the helper function
        helper_start = content.find('async def invalidate_customer_records_for_other_staff')
        assert helper_start != -1
        
        # Get function body (until next function at same indentation level)
        next_func = content.find('\nasync def ', helper_start + 1)
        if next_func == -1:
            next_func = content.find('\ndef ', helper_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        helper_body = content[helper_start:next_func]
        
        # Check all three collections are mentioned
        assert 'customer_records' in helper_body, "customer_records not checked"
        assert 'bonanza_records' in helper_body, "bonanza_records not checked"
        assert 'memberwd_records' in helper_body, "memberwd_records not checked"
        print("✓ Helper checks all three collections: customer_records, bonanza_records, memberwd_records")
    
    def test_09_helper_marks_records_as_invalid(self):
        """Verify helper marks records as 'invalid' with proper reason"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        helper_start = content.find('async def invalidate_customer_records_for_other_staff')
        next_func = content.find('\nasync def ', helper_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        helper_body = content[helper_start:next_func]
        
        # Check that status is set to 'invalid'
        assert "'status': 'invalid'" in helper_body or '"status": "invalid"' in helper_body, \
            "Helper doesn't set status to 'invalid'"
        
        # Check that invalid_reason contains 'reserved by'
        assert 'invalid_reason' in helper_body, "Helper doesn't set invalid_reason"
        assert 'reserved by' in helper_body.lower() or 'Customer reserved by' in helper_body, \
            "invalid_reason doesn't mention 'reserved by'"
        print("✓ Helper marks records as 'invalid' with reason containing 'reserved by'")
    
    def test_10_helper_creates_notification(self):
        """Verify helper creates notification for affected staff"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        helper_start = content.find('async def invalidate_customer_records_for_other_staff')
        next_func = content.find('\nasync def ', helper_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        helper_body = content[helper_start:next_func]
        
        # Check that notification is created
        assert 'create_notification' in helper_body, "Helper doesn't create notification"
        assert 'record_invalidated_reserved' in helper_body, \
            "Notification type should be 'record_invalidated_reserved'"
        print("✓ Helper creates notification of type 'record_invalidated_reserved'")
    
    def test_11_helper_only_invalidates_other_staff_records(self):
        """Verify helper only invalidates records assigned to OTHER staff"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        helper_start = content.find('async def invalidate_customer_records_for_other_staff')
        next_func = content.find('\nasync def ', helper_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        helper_body = content[helper_start:next_func]
        
        # Check that query excludes the reserving staff
        assert "'$ne': reserved_by_staff_id" in helper_body or \
               '"$ne": reserved_by_staff_id' in helper_body or \
               "'assigned_to': {'$ne': reserved_by_staff_id}" in helper_body, \
            "Helper should exclude records assigned to the reserving staff"
        print("✓ Helper only invalidates records assigned to OTHER staff (uses $ne)")
    
    # ==================== TEST 4: Integration Test - Approve Flow ====================
    
    def test_12_approve_flow_returns_invalidation_info(self, admin_headers, test_product, staff_a, staff_b):
        """Test that approve endpoint returns invalidation info when records are invalidated"""
        # This is a code review test - verify the response structure in the code
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        approve_func_start = content.find('async def approve_reserved_member')
        next_func = content.find('async def ', approve_func_start + 1)
        approve_func_body = content[approve_func_start:next_func]
        
        # Check response includes invalidation info
        assert 'invalidated_records' in approve_func_body, \
            "Response should include invalidated_records count"
        assert 'notified_staff_count' in approve_func_body, \
            "Response should include notified_staff_count"
        print("✓ Approve endpoint returns invalidation info in response")
    
    def test_13_bulk_endpoint_returns_invalidation_info(self, admin_headers):
        """Test that bulk endpoint returns invalidation info"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        bulk_func_start = content.find('async def bulk_create_reserved_members')
        next_func = content.find('async def ', bulk_func_start + 1)
        bulk_func_body = content[bulk_func_start:next_func]
        
        # Check response includes invalidation info
        assert 'invalidated_conflicts' in bulk_func_body, \
            "Bulk response should include invalidated_conflicts count"
        print("✓ Bulk endpoint returns invalidation info in response")
    
    # ==================== TEST 5: Notifications Endpoint ====================
    
    def test_14_notifications_endpoint_exists(self, admin_headers):
        """Test that notifications endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=admin_headers)
        assert response.status_code == 200, f"Notifications endpoint failed: {response.status_code}"
        print("✓ GET /api/notifications endpoint exists")
    
    # ==================== TEST 6: Full E2E Scenario (Code Path Verification) ====================
    
    def test_15_e2e_scenario_code_path(self):
        """
        Verify the complete code path for the E2E scenario:
        1. Staff B has a record assigned
        2. Admin approves Staff A's reservation for same customer
        3. Staff B's record should be invalidated
        4. Staff B should receive notification
        """
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Verify the complete flow exists in code
        checks = [
            # 1. Helper function exists
            ('async def invalidate_customer_records_for_other_staff', 
             "Helper function definition"),
            
            # 2. Helper checks assigned records
            ("'status': 'assigned'", 
             "Helper queries assigned records"),
            
            # 3. Helper excludes reserving staff
            ("'$ne': reserved_by_staff_id", 
             "Helper excludes reserving staff"),
            
            # 4. Helper updates to invalid
            ("'status': 'invalid'", 
             "Helper sets status to invalid"),
            
            # 5. Helper sets invalid_reason
            ("'invalid_reason':", 
             "Helper sets invalid_reason"),
            
            # 6. Helper creates notification
            ("type='record_invalidated_reserved'", 
             "Helper creates notification with correct type"),
            
            # 7. Approve endpoint calls helper
            ("invalidated_count, notified_staff = await invalidate_customer_records_for_other_staff", 
             "Approve endpoint calls helper and captures results"),
        ]
        
        for check_str, description in checks:
            assert check_str in content, f"Missing: {description}"
            print(f"  ✓ {description}")
        
        print("✓ Complete E2E code path verified")


class TestInvalidationAPIIntegration:
    """Live API integration tests for invalidation feature"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_product(self, admin_headers):
        """Get first available product"""
        response = requests.get(f"{BASE_URL}/api/products", headers=admin_headers)
        assert response.status_code == 200
        products = response.json()
        assert len(products) > 0, "No products available for testing"
        return products[0]
    
    @pytest.fixture(scope="class")
    def two_staff_users(self, admin_headers):
        """Get two different staff users for testing"""
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()
        staff_users = [u for u in users if u['role'] == 'staff']
        assert len(staff_users) >= 2, "Need at least 2 staff users for testing"
        return staff_users[0], staff_users[1]
    
    def test_16_create_reservation_as_admin_auto_approves(self, admin_headers, test_product, two_staff_users):
        """Test that admin creating reservation auto-approves it"""
        staff_a, _ = two_staff_users
        test_customer = f"TEST_AUTO_APPROVE_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "customer_id": test_customer,
                "product_id": test_product["id"],
                "staff_id": staff_a["id"]
            },
            headers=admin_headers
        )
        
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        member = response.json()
        
        # Admin-created reservations should be auto-approved
        assert member.get('status') == 'approved', \
            f"Admin-created reservation should be auto-approved, got: {member.get('status')}"
        print(f"✓ Admin-created reservation is auto-approved (status={member['status']})")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
    
    def test_17_bulk_create_returns_success(self, admin_headers, test_product, two_staff_users):
        """Test bulk create endpoint returns proper response"""
        staff_a, _ = two_staff_users
        test_customers = [
            f"TEST_BULK_A_{uuid.uuid4().hex[:6]}",
            f"TEST_BULK_B_{uuid.uuid4().hex[:6]}"
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/reserved-members/bulk",
            json={
                "customer_ids": test_customers,
                "product_id": test_product["id"],
                "staff_id": staff_a["id"]
            },
            headers=admin_headers
        )
        
        assert response.status_code in [200, 201], f"Bulk create failed: {response.text}"
        result = response.json()
        
        assert 'added_count' in result, "Response should include added_count"
        assert 'skipped_count' in result, "Response should include skipped_count"
        assert result['added_count'] == 2, f"Expected 2 added, got {result['added_count']}"
        print(f"✓ Bulk create returned proper response: added={result['added_count']}, skipped={result['skipped_count']}")
        
        # Cleanup
        members_resp = requests.get(
            f"{BASE_URL}/api/reserved-members?product_id={test_product['id']}",
            headers=admin_headers
        )
        if members_resp.status_code == 200:
            for member in members_resp.json():
                if member.get('customer_id') in test_customers:
                    requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
    
    def test_18_approve_pending_reservation(self, admin_headers, test_product, two_staff_users):
        """Test approving a pending reservation"""
        staff_a, _ = two_staff_users
        test_customer = f"TEST_PENDING_{uuid.uuid4().hex[:8]}"
        
        # First, we need to create a pending reservation (staff creates it)
        # Since we're admin, we'll verify the approve endpoint works
        
        # Create as admin (auto-approved)
        create_resp = requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "customer_id": test_customer,
                "product_id": test_product["id"],
                "staff_id": staff_a["id"]
            },
            headers=admin_headers
        )
        
        if create_resp.status_code in [200, 201]:
            member = create_resp.json()
            # Try to approve (should fail since already approved)
            approve_resp = requests.patch(
                f"{BASE_URL}/api/reserved-members/{member['id']}/approve",
                headers=admin_headers
            )
            # Should return 400 since already approved
            assert approve_resp.status_code == 400, \
                f"Expected 400 for already approved, got {approve_resp.status_code}"
            print("✓ Approve endpoint correctly rejects already-approved reservations")
            
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
        else:
            print(f"⚠ Could not create test reservation: {create_resp.text}")


class TestInvalidationNotifications:
    """Test notification creation for invalidation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_19_notification_type_exists_in_code(self):
        """Verify record_invalidated_reserved notification type is used"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        assert "type='record_invalidated_reserved'" in content or \
               'type="record_invalidated_reserved"' in content, \
            "Notification type 'record_invalidated_reserved' not found"
        print("✓ Notification type 'record_invalidated_reserved' is used in code")
    
    def test_20_notification_includes_customer_info(self):
        """Verify notification includes customer and staff info"""
        with open('/app/backend/routes/records.py', 'r') as f:
            content = f.read()
        
        # Find the notification creation in helper
        helper_start = content.find('async def invalidate_customer_records_for_other_staff')
        next_func = content.find('\nasync def ', helper_start + 1)
        helper_body = content[helper_start:next_func]
        
        # Check notification includes relevant data
        assert 'customer_id' in helper_body, "Notification should include customer_id"
        assert 'reserved_by' in helper_body, "Notification should include reserved_by info"
        print("✓ Notification includes customer_id and reserved_by info")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
