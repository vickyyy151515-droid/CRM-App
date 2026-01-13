"""
Test suite for Reserved Member CRM feature
Tests: Admin add, Staff request, Approve/Reject, Duplicate check, Move, Delete
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestAuth:
    """Authentication tests for Reserved Member feature"""
    
    def test_admin_login(self):
        """Test admin login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "admin", "User is not admin"
        print(f"SUCCESS: Admin login - token received, role={data['user']['role']}")
    
    def test_staff_login(self):
        """Test staff login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "staff", "User is not staff"
        print(f"SUCCESS: Staff login - token received, role={data['user']['role']}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Admin authentication failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STAFF_EMAIL,
        "password": STAFF_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Staff authentication failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_user_id(admin_token):
    """Get staff user ID for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/staff-users", headers=headers)
    if response.status_code != 200 or len(response.json()) == 0:
        pytest.skip("No staff users found")
    return response.json()[0]["id"]


class TestStaffUsersEndpoint:
    """Test /api/staff-users endpoint"""
    
    def test_get_staff_users_as_admin(self, admin_token):
        """Admin can get list of staff users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/staff-users", headers=headers)
        assert response.status_code == 200, f"Failed to get staff users: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} staff users")
        if len(data) > 0:
            assert "id" in data[0], "Staff user should have id"
            assert "name" in data[0], "Staff user should have name"
            print(f"  First staff: {data[0].get('name', 'N/A')}")
    
    def test_get_staff_users_as_staff(self, staff_token):
        """Staff can also get list of staff users"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/staff-users", headers=headers)
        assert response.status_code == 200, f"Staff should be able to get staff users: {response.text}"
        print("SUCCESS: Staff can view staff users list")


class TestAdminReservedMemberOperations:
    """Test admin operations on reserved members"""
    
    def test_admin_add_reserved_member_directly(self, admin_token, staff_user_id):
        """Admin can add a reserved member directly (status=approved)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_AdminDirect_{int(time.time())}"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        assert response.status_code == 200, f"Failed to add reserved member: {response.text}"
        data = response.json()
        
        # Verify response data
        assert data["customer_name"] == unique_name, "Customer name mismatch"
        assert data["status"] == "approved", f"Admin-added member should be approved, got: {data['status']}"
        assert data["staff_id"] == staff_user_id, "Staff ID mismatch"
        assert "id" in data, "Response should have id"
        
        print(f"SUCCESS: Admin added reserved member '{unique_name}' with status=approved")
        return data["id"]
    
    def test_admin_add_without_staff_id_fails(self, admin_token):
        """Admin must provide staff_id when adding reserved member"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": "TEST_NoStaffId"
        })
        assert response.status_code == 400, f"Should fail without staff_id, got: {response.status_code}"
        print("SUCCESS: Admin cannot add reserved member without staff_id")
    
    def test_get_all_reserved_members(self, admin_token):
        """Admin can get all reserved members"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        assert response.status_code == 200, f"Failed to get reserved members: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} reserved members")
    
    def test_filter_reserved_members_by_status(self, admin_token):
        """Admin can filter reserved members by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Filter by approved
        response = requests.get(f"{BASE_URL}/api/reserved-members?status=approved", headers=headers)
        assert response.status_code == 200, f"Failed to filter by approved: {response.text}"
        approved = response.json()
        for member in approved:
            assert member["status"] == "approved", f"Expected approved, got {member['status']}"
        print(f"SUCCESS: Filtered approved members: {len(approved)}")
        
        # Filter by pending
        response = requests.get(f"{BASE_URL}/api/reserved-members?status=pending", headers=headers)
        assert response.status_code == 200, f"Failed to filter by pending: {response.text}"
        pending = response.json()
        for member in pending:
            assert member["status"] == "pending", f"Expected pending, got {member['status']}"
        print(f"SUCCESS: Filtered pending members: {len(pending)}")


class TestStaffReservedMemberOperations:
    """Test staff operations on reserved members"""
    
    def test_staff_request_reservation(self, staff_token):
        """Staff can request a reservation (status=pending)"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_StaffRequest_{int(time.time())}"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name
        })
        assert response.status_code == 200, f"Failed to request reservation: {response.text}"
        data = response.json()
        
        # Verify response data
        assert data["customer_name"] == unique_name, "Customer name mismatch"
        assert data["status"] == "pending", f"Staff request should be pending, got: {data['status']}"
        assert "id" in data, "Response should have id"
        
        print(f"SUCCESS: Staff requested reservation '{unique_name}' with status=pending")
        return data["id"]
    
    def test_staff_can_view_all_approved_reservations(self, staff_token):
        """Staff can view all approved reservations"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        assert response.status_code == 200, f"Failed to get reserved members: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Staff can view {len(data)} reserved members")


class TestDuplicateCheck:
    """Test duplicate customer name prevention"""
    
    def test_duplicate_approved_member_rejected(self, admin_token, staff_user_id):
        """Cannot add duplicate customer name when one is already approved"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_Duplicate_{int(time.time())}"
        
        # First, add a member
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        assert response1.status_code == 200, f"First add failed: {response1.text}"
        first_id = response1.json()["id"]
        print(f"SUCCESS: First member added with id={first_id}")
        
        # Try to add duplicate
        response2 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        assert response2.status_code == 409, f"Duplicate should be rejected with 409, got: {response2.status_code}"
        assert "already reserved" in response2.json().get("detail", "").lower(), "Error message should mention already reserved"
        print(f"SUCCESS: Duplicate rejected with 409 - {response2.json().get('detail')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{first_id}", headers=headers)
    
    def test_duplicate_case_insensitive(self, admin_token, staff_user_id):
        """Duplicate check should be case-insensitive"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        base_name = f"TEST_CaseCheck_{int(time.time())}"
        
        # Add with lowercase
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": base_name.lower(),
            "staff_id": staff_user_id
        })
        assert response1.status_code == 200, f"First add failed: {response1.text}"
        first_id = response1.json()["id"]
        
        # Try with uppercase - should fail
        response2 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": base_name.upper(),
            "staff_id": staff_user_id
        })
        assert response2.status_code == 409, f"Case-insensitive duplicate should be rejected, got: {response2.status_code}"
        print("SUCCESS: Case-insensitive duplicate check works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{first_id}", headers=headers)
    
    def test_staff_cannot_request_already_reserved_name(self, admin_token, staff_token, staff_user_id):
        """Staff cannot request a name that's already reserved by another staff"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_StaffDupe_{int(time.time())}"
        
        # Admin adds a reservation
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=admin_headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        assert response1.status_code == 200, f"Admin add failed: {response1.text}"
        first_id = response1.json()["id"]
        
        # Staff tries to request same name
        response2 = requests.post(f"{BASE_URL}/api/reserved-members", headers=staff_headers, json={
            "customer_name": unique_name
        })
        assert response2.status_code == 409, f"Staff duplicate request should be rejected, got: {response2.status_code}"
        print(f"SUCCESS: Staff cannot request already reserved name - {response2.json().get('detail')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{first_id}", headers=admin_headers)


class TestApproveRejectWorkflow:
    """Test admin approve/reject workflow for staff requests"""
    
    def test_approve_pending_request(self, admin_token, staff_token):
        """Admin can approve a pending staff request"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_Approve_{int(time.time())}"
        
        # Staff creates request
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=staff_headers, json={
            "customer_name": unique_name
        })
        assert response1.status_code == 200, f"Staff request failed: {response1.text}"
        member_id = response1.json()["id"]
        assert response1.json()["status"] == "pending", "Initial status should be pending"
        
        # Admin approves
        response2 = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/approve", headers=admin_headers)
        assert response2.status_code == 200, f"Approve failed: {response2.text}"
        
        # Verify status changed
        response3 = requests.get(f"{BASE_URL}/api/reserved-members?status=approved", headers=admin_headers)
        approved_members = response3.json()
        found = any(m["id"] == member_id and m["status"] == "approved" for m in approved_members)
        assert found, "Approved member not found in approved list"
        print(f"SUCCESS: Admin approved request - member {member_id} is now approved")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=admin_headers)
    
    def test_reject_pending_request(self, admin_token, staff_token):
        """Admin can reject a pending staff request (deletes the record)"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_Reject_{int(time.time())}"
        
        # Staff creates request
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=staff_headers, json={
            "customer_name": unique_name
        })
        assert response1.status_code == 200, f"Staff request failed: {response1.text}"
        member_id = response1.json()["id"]
        
        # Admin rejects
        response2 = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/reject", headers=admin_headers)
        assert response2.status_code == 200, f"Reject failed: {response2.text}"
        
        # Verify member is deleted
        response3 = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_headers)
        all_members = response3.json()
        found = any(m["id"] == member_id for m in all_members)
        assert not found, "Rejected member should be deleted"
        print(f"SUCCESS: Admin rejected request - member {member_id} is deleted")
    
    def test_cannot_approve_already_processed(self, admin_token, staff_user_id):
        """Cannot approve an already approved member"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_AlreadyApproved_{int(time.time())}"
        
        # Admin adds (already approved)
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        member_id = response1.json()["id"]
        
        # Try to approve again
        response2 = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/approve", headers=headers)
        assert response2.status_code == 400, f"Should fail for already processed, got: {response2.status_code}"
        print("SUCCESS: Cannot approve already processed member")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=headers)


class TestMoveReservation:
    """Test admin move reservation to different staff"""
    
    def test_move_reservation_to_different_staff(self, admin_token, staff_user_id):
        """Admin can move an approved reservation to a different staff"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_Move_{int(time.time())}"
        
        # Get all staff users
        staff_response = requests.get(f"{BASE_URL}/api/staff-users", headers=headers)
        staff_list = staff_response.json()
        
        if len(staff_list) < 1:
            pytest.skip("Need at least 1 staff user to test move")
        
        # Add reservation
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        assert response1.status_code == 200, f"Add failed: {response1.text}"
        member_id = response1.json()["id"]
        original_staff_id = response1.json()["staff_id"]
        
        # Find a different staff (or use same if only one)
        new_staff_id = staff_list[0]["id"]
        if new_staff_id == original_staff_id and len(staff_list) > 1:
            new_staff_id = staff_list[1]["id"]
        
        # Move to new staff
        response2 = requests.patch(
            f"{BASE_URL}/api/reserved-members/{member_id}/move?new_staff_id={new_staff_id}", 
            headers=headers
        )
        assert response2.status_code == 200, f"Move failed: {response2.text}"
        
        # Verify move
        response3 = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        members = response3.json()
        moved_member = next((m for m in members if m["id"] == member_id), None)
        assert moved_member is not None, "Member not found after move"
        assert moved_member["staff_id"] == new_staff_id, f"Staff ID not updated: {moved_member['staff_id']} != {new_staff_id}"
        print(f"SUCCESS: Moved reservation from {original_staff_id} to {new_staff_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=headers)
    
    def test_move_to_nonexistent_staff_fails(self, admin_token, staff_user_id):
        """Move to non-existent staff should fail"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_MoveInvalid_{int(time.time())}"
        
        # Add reservation
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        member_id = response1.json()["id"]
        
        # Try to move to non-existent staff
        response2 = requests.patch(
            f"{BASE_URL}/api/reserved-members/{member_id}/move?new_staff_id=nonexistent-id", 
            headers=headers
        )
        assert response2.status_code == 404, f"Should fail with 404, got: {response2.status_code}"
        print("SUCCESS: Move to non-existent staff fails with 404")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=headers)


class TestDeleteReservation:
    """Test admin delete reservation"""
    
    def test_admin_delete_reservation(self, admin_token, staff_user_id):
        """Admin can delete a reservation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_Delete_{int(time.time())}"
        
        # Add reservation
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        member_id = response1.json()["id"]
        
        # Delete
        response2 = requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=headers)
        assert response2.status_code == 200, f"Delete failed: {response2.text}"
        
        # Verify deleted
        response3 = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        members = response3.json()
        found = any(m["id"] == member_id for m in members)
        assert not found, "Deleted member should not exist"
        print(f"SUCCESS: Admin deleted reservation {member_id}")
    
    def test_delete_nonexistent_fails(self, admin_token):
        """Delete non-existent member should fail"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.delete(f"{BASE_URL}/api/reserved-members/nonexistent-id", headers=headers)
        assert response.status_code == 404, f"Should fail with 404, got: {response.status_code}"
        print("SUCCESS: Delete non-existent member fails with 404")
    
    def test_staff_cannot_delete(self, staff_token, admin_token, staff_user_id):
        """Staff cannot delete reservations (admin only)"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_StaffDelete_{int(time.time())}"
        
        # Admin adds reservation
        response1 = requests.post(f"{BASE_URL}/api/reserved-members", headers=admin_headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id
        })
        member_id = response1.json()["id"]
        
        # Staff tries to delete
        response2 = requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=staff_headers)
        assert response2.status_code == 403, f"Staff delete should be forbidden, got: {response2.status_code}"
        print("SUCCESS: Staff cannot delete reservations (403 Forbidden)")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=admin_headers)


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, admin_token):
        """Clean up all TEST_ prefixed reserved members"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        members = response.json()
        
        deleted_count = 0
        for member in members:
            if member["customer_name"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=headers)
                deleted_count += 1
        
        print(f"SUCCESS: Cleaned up {deleted_count} test reserved members")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
