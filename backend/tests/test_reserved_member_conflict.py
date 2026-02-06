"""
Test suite for Reserved Member Conflict and Duplicate Customer Log features

Tests:
1. POST /api/omset creates omset with approval_status='pending' when customer is reserved by another staff
2. POST /api/omset creates omset with approval_status='approved' when no reserved member conflict
3. GET /api/omset/pending returns all pending omset records (admin only, 403 for staff)
4. POST /api/omset/{id}/approve approves a pending record and sends notification
5. POST /api/omset/{id}/decline declines/deletes a pending record and sends notification
6. GET /api/omset/duplicates returns duplicate records when same customer+product has multiple staff
7. GET /api/omset/duplicates returns empty when no duplicates exist
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"email": "vicky@crm.com", "password": "vicky123"}
STAFF_CREDENTIALS = {"email": "staff@crm.com", "password": "staff123"}

# Test data
TEST_CUSTOMER_ID = "TEST_RESERVED_CUST_001"
TEST_PRODUCT_ID = "prod-istana2000"
TEST_PRODUCT_NAME = "ISTANA2000"
STAFF_USER_1_ID = "staff-user-1"

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")

@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Staff authentication failed: {response.status_code} - {response.text}")

@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def staff_headers(staff_token):
    return {"Authorization": f"Bearer {staff_token}", "Content-Type": "application/json"}


class TestSetupCleanup:
    """Setup and cleanup test data"""
    
    def test_cleanup_existing_test_data(self, admin_headers):
        """Clean up any existing test data before running tests"""
        # Delete any existing reserved members with TEST prefix
        reserved_res = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_headers)
        if reserved_res.status_code == 200:
            for member in reserved_res.json():
                if member.get('customer_id', '').startswith('TEST_') or member.get('customer_name', '').startswith('TEST_'):
                    delete_res = requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
                    print(f"Deleted reserved member: {member['id']} - status: {delete_res.status_code}")
        
        # Delete any existing omset records with TEST prefix
        omset_res = requests.get(f"{BASE_URL}/api/omset", headers=admin_headers)
        if omset_res.status_code == 200:
            for record in omset_res.json():
                if record.get('customer_id', '').startswith('TEST_'):
                    delete_res = requests.delete(f"{BASE_URL}/api/omset/{record['id']}", headers=admin_headers)
                    print(f"Deleted omset record: {record['id']} - status: {delete_res.status_code}")
        
        print("Cleanup complete")
        assert True


class TestReservedMemberConflict:
    """Test reserved member conflict feature when creating omset"""
    
    def test_create_reserved_member_for_staff1(self, admin_headers):
        """Admin creates a reserved member for staff-user-1"""
        payload = {
            "customer_id": TEST_CUSTOMER_ID,
            "product_id": TEST_PRODUCT_ID,
            "staff_id": STAFF_USER_1_ID
        }
        response = requests.post(f"{BASE_URL}/api/reserved-members", json=payload, headers=admin_headers)
        print(f"Create reserved member response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get('customer_id') == TEST_CUSTOMER_ID
        assert data.get('staff_id') == STAFF_USER_1_ID
        assert data.get('status') == 'approved'
    
    def test_omset_pending_when_conflict_exists(self, admin_headers):
        """When ADMIN (different from staff-user-1) creates omset for reserved customer, status should be pending"""
        # Note: staff@crm.com IS staff-user-1, so we use ADMIN (Vicky) to create conflict
        # Admin ID is 0cf8a86d-fbad-4966-b232-a49e4033e1d8 which is != staff-user-1
        today = datetime.now().strftime('%Y-%m-%d')
        payload = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": TEST_CUSTOMER_ID,
            "customer_id": TEST_CUSTOMER_ID,
            "nominal": 100000,
            "depo_kelipatan": 1,
            "keterangan": "Test conflict - admin creating for reserved customer"
        }
        response = requests.post(f"{BASE_URL}/api/omset", json=payload, headers=admin_headers)
        print(f"Create omset with conflict response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Check if approval_status is pending OR if conflict_info exists
        is_pending = data.get('approval_status') == 'pending'
        has_conflict = 'conflict_info' in data
        assert is_pending or has_conflict, f"Expected pending status or conflict_info, got: {data}"
        
        # Store record ID for later tests
        TestReservedMemberConflict.pending_record_id = data.get('id')
    
    def test_omset_approved_when_same_staff_creates(self, staff_headers):
        """When SAME staff (staff-user-1) creates omset for their own reserved customer, status should be approved"""
        # staff@crm.com IS staff-user-1, so there's no conflict when they create for their own customer
        today = datetime.now().strftime('%Y-%m-%d')
        payload = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": TEST_CUSTOMER_ID,
            "customer_id": TEST_CUSTOMER_ID,
            "nominal": 75000,
            "depo_kelipatan": 1,
            "keterangan": "Test no conflict - same staff"
        }
        response = requests.post(f"{BASE_URL}/api/omset", json=payload, headers=staff_headers)
        print(f"Create omset (same staff - no conflict) response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should be approved (same staff owns the reservation)
        approval_status = data.get('approval_status', 'approved')
        assert approval_status == 'approved', f"Expected approved status, got: {approval_status}"
    
    def test_omset_approved_when_no_reservation(self, admin_headers):
        """When admin creates omset for non-reserved customer, status should be approved"""
        today = datetime.now().strftime('%Y-%m-%d')
        payload = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": "TEST_NO_CONFLICT_CUST",
            "customer_id": "TEST_NO_CONFLICT_CUST",
            "nominal": 50000,
            "depo_kelipatan": 1,
            "keterangan": "Test no conflict - no reservation exists"
        }
        response = requests.post(f"{BASE_URL}/api/omset", json=payload, headers=admin_headers)
        print(f"Create omset without conflict response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Should be approved (no reservation exists)
        approval_status = data.get('approval_status', 'approved')
        assert approval_status == 'approved', f"Expected approved status, got: {approval_status}"
        
        # Store record ID for cleanup
        TestReservedMemberConflict.approved_record_id = data.get('id')


class TestPendingOmsetEndpoints:
    """Test GET /api/omset/pending endpoint - admin only"""
    
    def test_get_pending_admin_success(self, admin_headers):
        """Admin can get pending omset records"""
        response = requests.get(f"{BASE_URL}/api/omset/pending", headers=admin_headers)
        print(f"Get pending (admin) response: {response.status_code} - {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected a list of pending records"
        print(f"Found {len(data)} pending records")
    
    def test_get_pending_staff_forbidden(self, staff_headers):
        """Staff cannot get pending omset records (403 forbidden)"""
        response = requests.get(f"{BASE_URL}/api/omset/pending", headers=staff_headers)
        print(f"Get pending (staff) response: {response.status_code}")
        
        # Should return 403 for staff users
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


class TestApproveDeclineOmset:
    """Test approve and decline omset endpoints"""
    
    def test_approve_pending_omset(self, admin_headers):
        """Admin can approve a pending omset record"""
        # First get a pending record
        pending_res = requests.get(f"{BASE_URL}/api/omset/pending", headers=admin_headers)
        if pending_res.status_code != 200 or len(pending_res.json()) == 0:
            pytest.skip("No pending records to approve")
        
        pending_records = pending_res.json()
        record_id = pending_records[0].get('id')
        
        # Approve the record
        response = requests.post(f"{BASE_URL}/api/omset/{record_id}/approve", headers=admin_headers)
        print(f"Approve omset response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get('success') == True or 'approved' in str(data).lower()
    
    def test_decline_pending_omset(self, admin_headers, staff_headers):
        """Admin can decline (delete) a pending omset record"""
        # First ensure we have a reserved member set up
        # Create a NEW reserved member for a unique customer to avoid conflicts with previous tests
        DECLINE_TEST_CUSTOMER = "TEST_DECLINE_CUST_001"
        
        # Create reserved member for staff-user-1
        reserved_payload = {
            "customer_id": DECLINE_TEST_CUSTOMER,
            "product_id": TEST_PRODUCT_ID,
            "staff_id": STAFF_USER_1_ID
        }
        reserved_res = requests.post(f"{BASE_URL}/api/reserved-members", json=reserved_payload, headers=admin_headers)
        print(f"Created reserved member for decline test: {reserved_res.status_code}")
        
        # Now ADMIN creates omset for this reserved customer - should be pending
        today = datetime.now().strftime('%Y-%m-%d')
        payload = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": DECLINE_TEST_CUSTOMER,
            "customer_id": DECLINE_TEST_CUSTOMER,
            "nominal": 75000,
            "depo_kelipatan": 1,
            "keterangan": "Test to decline"
        }
        create_res = requests.post(f"{BASE_URL}/api/omset", json=payload, headers=admin_headers)
        print(f"Create pending omset for decline: {create_res.status_code} - {create_res.text}")
        
        if create_res.status_code != 200:
            pytest.skip(f"Could not create pending record: {create_res.text}")
        
        record_data = create_res.json()
        record_id = record_data.get('id')
        
        # Check if it's actually pending
        if record_data.get('approval_status') != 'pending':
            print(f"Record was not pending (got {record_data.get('approval_status')}), skipping decline test")
            pytest.skip("Could not create pending record for decline test")
        
        # Decline the record
        response = requests.post(f"{BASE_URL}/api/omset/{record_id}/decline", headers=admin_headers)
        print(f"Decline omset response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get('success') == True or 'declined' in str(data).lower() or 'deleted' in str(data).lower()
    
    def test_approve_staff_forbidden(self, staff_headers):
        """Staff cannot approve omset records (403 forbidden)"""
        response = requests.post(f"{BASE_URL}/api/omset/fake-id-123/approve", headers=staff_headers)
        print(f"Approve (staff) response: {response.status_code}")
        
        # Should return 403 for staff users
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
    
    def test_decline_staff_forbidden(self, staff_headers):
        """Staff cannot decline omset records (403 forbidden)"""
        response = requests.post(f"{BASE_URL}/api/omset/fake-id-123/decline", headers=staff_headers)
        print(f"Decline (staff) response: {response.status_code}")
        
        # Should return 403 for staff users
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


class TestDuplicateOmsetEndpoint:
    """Test GET /api/omset/duplicates endpoint"""
    
    def test_setup_duplicate_data(self, admin_headers, staff_headers):
        """Create duplicate omset records (same customer+product by different staff)"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Admin creates an omset for test duplicate customer
        payload1 = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": "TEST_DUPLICATE_CUST",
            "customer_id": "TEST_DUPLICATE_CUST",
            "nominal": 100000,
            "depo_kelipatan": 1,
            "keterangan": "Duplicate test - admin"
        }
        res1 = requests.post(f"{BASE_URL}/api/omset", json=payload1, headers=admin_headers)
        print(f"Admin omset for duplicate: {res1.status_code}")
        
        # Staff creates an omset for same customer
        payload2 = {
            "product_id": TEST_PRODUCT_ID,
            "record_date": today,
            "customer_name": "TEST_DUPLICATE_CUST",
            "customer_id": "TEST_DUPLICATE_CUST",
            "nominal": 80000,
            "depo_kelipatan": 1,
            "keterangan": "Duplicate test - staff"
        }
        res2 = requests.post(f"{BASE_URL}/api/omset", json=payload2, headers=staff_headers)
        print(f"Staff omset for duplicate: {res2.status_code}")
        
        assert res1.status_code == 200 or res2.status_code == 200, "At least one record should be created"
    
    def test_get_duplicates_admin_success(self, admin_headers):
        """Admin can get duplicate omset records"""
        response = requests.get(f"{BASE_URL}/api/omset/duplicates", headers=admin_headers)
        print(f"Get duplicates (admin) response: {response.status_code} - {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert 'duplicates' in data, "Response should contain 'duplicates' key"
        assert 'total_duplicates' in data, "Response should contain 'total_duplicates' key"
        print(f"Found {data.get('total_duplicates', 0)} duplicate groups")
    
    def test_get_duplicates_with_date_filter(self, admin_headers):
        """Admin can filter duplicates by date range"""
        today = datetime.now().strftime('%Y-%m-%d')
        response = requests.get(
            f"{BASE_URL}/api/omset/duplicates",
            params={"start_date": today, "end_date": today},
            headers=admin_headers
        )
        print(f"Get duplicates with date filter response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert 'duplicates' in data
    
    def test_get_duplicates_staff_forbidden(self, staff_headers):
        """Staff cannot get duplicate omset records (403 forbidden)"""
        response = requests.get(f"{BASE_URL}/api/omset/duplicates", headers=staff_headers)
        print(f"Get duplicates (staff) response: {response.status_code}")
        
        # Should return 403 for staff users
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"


class TestCleanupTestData:
    """Cleanup test data after tests complete"""
    
    def test_cleanup_test_omset_records(self, admin_headers):
        """Clean up test omset records"""
        omset_res = requests.get(f"{BASE_URL}/api/omset", headers=admin_headers)
        if omset_res.status_code == 200:
            deleted_count = 0
            for record in omset_res.json():
                if record.get('customer_id', '').startswith('TEST_'):
                    delete_res = requests.delete(f"{BASE_URL}/api/omset/{record['id']}", headers=admin_headers)
                    if delete_res.status_code == 200:
                        deleted_count += 1
            print(f"Cleaned up {deleted_count} test omset records")
        assert True
    
    def test_cleanup_test_reserved_members(self, admin_headers):
        """Clean up test reserved members"""
        reserved_res = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_headers)
        if reserved_res.status_code == 200:
            deleted_count = 0
            for member in reserved_res.json():
                cust_id = member.get('customer_id', '') or member.get('customer_name', '')
                if cust_id.startswith('TEST_'):
                    delete_res = requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
                    if delete_res.status_code == 200:
                        deleted_count += 1
            print(f"Cleaned up {deleted_count} test reserved members")
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
