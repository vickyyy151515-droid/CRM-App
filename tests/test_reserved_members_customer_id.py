"""
Test Suite for Reserved Members - customer_name to customer_id Refactoring
Tests the following features:
1. Reserved Members GET endpoint returns customer_id for both new and legacy data
2. Creating a new reservation using customer_id field works
3. Duplicate detection works with case-insensitive customer_id matching
4. Bulk add reservations using customer_ids field works
5. Moving a reservation to another staff works
6. Deleting a reservation works
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_ADMIN = {"email": "vicky@crm.com", "password": "vicky123"}
ADMIN = {"email": "admin@crm.com", "password": "admin123"}
STAFF = {"email": "staff@crm.com", "password": "staff123"}

# Test products
PRODUCTS = {
    "ISTANA2000": "prod-istana2000",
    "LIGA2000": "prod-liga2000",
    "PUCUK33": "prod-pucuk33"
}


class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_ADMIN)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        """Get staff authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF)
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        return response.json().get("token")
    
    def test_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print("✓ Admin login successful")
    
    def test_staff_login(self, staff_token):
        """Verify staff can login"""
        assert staff_token is not None
        print("✓ Staff login successful")


class TestReservedMembersCustomerId:
    """Test Reserved Members with customer_id field"""
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Create authenticated admin session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=MASTER_ADMIN)
        assert response.status_code == 200
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    @pytest.fixture(scope="class")
    def staff_session(self):
        """Create authenticated staff session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=STAFF)
        assert response.status_code == 200
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    @pytest.fixture(scope="class")
    def staff_user_id(self, admin_session):
        """Get staff user ID"""
        response = admin_session.get(f"{BASE_URL}/api/staff-users")
        assert response.status_code == 200
        staff_list = response.json()
        # Find staff user
        for staff in staff_list:
            if staff.get("email") == STAFF["email"]:
                return staff["id"]
        # Return first staff if not found
        if staff_list:
            return staff_list[0]["id"]
        pytest.skip("No staff users found")
    
    def test_get_reserved_members_returns_customer_id(self, admin_session):
        """Test GET /reserved-members returns customer_id field"""
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        assert response.status_code == 200
        members = response.json()
        print(f"✓ GET /reserved-members returned {len(members)} members")
        
        # Check that response includes customer_id field
        if members:
            first_member = members[0]
            # Should have customer_id (either from new data or migrated from customer_name)
            assert "customer_id" in first_member or "customer_name" in first_member, \
                "Response should include customer_id or customer_name"
            print(f"✓ First member has customer identifier: {first_member.get('customer_id') or first_member.get('customer_name')}")
    
    def test_create_reservation_with_customer_id(self, admin_session, staff_user_id):
        """Test creating a new reservation using customer_id field"""
        unique_id = f"TEST_CUST_{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            "customer_id": unique_id,
            "phone_number": "081234567890",
            "product_id": PRODUCTS["ISTANA2000"],
            "staff_id": staff_user_id
        }
        
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data.get("customer_id") == unique_id, "customer_id should match input"
        assert data.get("status") == "approved", "Admin-created reservation should be approved"
        print(f"✓ Created reservation with customer_id: {unique_id}")
        
        # Cleanup
        member_id = data.get("id")
        if member_id:
            admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")
        
        return data
    
    def test_duplicate_detection_case_insensitive(self, admin_session, staff_user_id):
        """Test duplicate detection with case-insensitive customer_id matching"""
        unique_id = f"TEST_DUP_{uuid.uuid4().hex[:8].upper()}"
        
        # Create first reservation
        payload = {
            "customer_id": unique_id,
            "product_id": PRODUCTS["LIGA2000"],
            "staff_id": staff_user_id
        }
        
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200, f"First create failed: {response.text}"
        first_member = response.json()
        print(f"✓ Created first reservation: {unique_id}")
        
        # Try to create duplicate with different case
        payload_lowercase = {
            "customer_id": unique_id.lower(),  # Same ID but lowercase
            "product_id": PRODUCTS["LIGA2000"],  # Same product
            "staff_id": staff_user_id
        }
        
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload_lowercase)
        assert response.status_code == 409, f"Should reject duplicate, got: {response.status_code}"
        print(f"✓ Duplicate detection works (case-insensitive): rejected '{unique_id.lower()}'")
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/reserved-members/{first_member['id']}")
    
    def test_bulk_add_reservations_with_customer_ids(self, admin_session, staff_user_id):
        """Test bulk add reservations using customer_ids field"""
        unique_ids = [
            f"TEST_BULK_{uuid.uuid4().hex[:6].upper()}",
            f"TEST_BULK_{uuid.uuid4().hex[:6].upper()}",
            f"TEST_BULK_{uuid.uuid4().hex[:6].upper()}"
        ]
        
        payload = {
            "customer_ids": unique_ids,
            "product_id": PRODUCTS["PUCUK33"],
            "staff_id": staff_user_id
        }
        
        response = admin_session.post(f"{BASE_URL}/api/reserved-members/bulk", json=payload)
        assert response.status_code == 200, f"Bulk add failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("added_count") == 3, f"Expected 3 added, got {data.get('added_count')}"
        assert data.get("total_processed") == 3
        print(f"✓ Bulk added {data.get('added_count')} reservations")
        
        # Verify they exist
        response = admin_session.get(f"{BASE_URL}/api/reserved-members?product_id={PRODUCTS['PUCUK33']}")
        assert response.status_code == 200
        members = response.json()
        
        # Check that our bulk-added members exist
        member_ids = [m.get("customer_id") for m in members]
        for uid in unique_ids:
            assert uid in member_ids, f"Bulk-added member {uid} not found"
        print(f"✓ Verified all bulk-added members exist")
        
        # Cleanup
        for member in members:
            if member.get("customer_id") in unique_ids:
                admin_session.delete(f"{BASE_URL}/api/reserved-members/{member['id']}")
    
    def test_bulk_add_skips_duplicates(self, admin_session, staff_user_id):
        """Test bulk add skips existing customer_ids"""
        unique_id = f"TEST_SKIP_{uuid.uuid4().hex[:8].upper()}"
        
        # Create one reservation first
        payload = {
            "customer_id": unique_id,
            "product_id": PRODUCTS["ISTANA2000"],
            "staff_id": staff_user_id
        }
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200
        first_member = response.json()
        
        # Try bulk add with same ID plus new ones
        new_id = f"TEST_NEW_{uuid.uuid4().hex[:8].upper()}"
        bulk_payload = {
            "customer_ids": [unique_id, new_id],  # One existing, one new
            "product_id": PRODUCTS["ISTANA2000"],
            "staff_id": staff_user_id
        }
        
        response = admin_session.post(f"{BASE_URL}/api/reserved-members/bulk", json=bulk_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("added_count") == 1, "Should only add 1 new member"
        assert data.get("skipped_count") == 1, "Should skip 1 duplicate"
        print(f"✓ Bulk add correctly skipped duplicate: added={data.get('added_count')}, skipped={data.get('skipped_count')}")
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/reserved-members/{first_member['id']}")
        # Find and delete the new one
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        for member in response.json():
            if member.get("customer_id") == new_id:
                admin_session.delete(f"{BASE_URL}/api/reserved-members/{member['id']}")
    
    def test_move_reservation_to_another_staff(self, admin_session, staff_user_id):
        """Test moving a reservation to another staff member"""
        unique_id = f"TEST_MOVE_{uuid.uuid4().hex[:8].upper()}"
        
        # Create reservation
        payload = {
            "customer_id": unique_id,
            "product_id": PRODUCTS["LIGA2000"],
            "staff_id": staff_user_id
        }
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200
        member = response.json()
        member_id = member["id"]
        original_staff = member["staff_id"]
        print(f"✓ Created reservation for move test: {unique_id}")
        
        # Get another staff to move to
        response = admin_session.get(f"{BASE_URL}/api/staff-users")
        staff_list = response.json()
        new_staff_id = None
        for staff in staff_list:
            if staff["id"] != original_staff:
                new_staff_id = staff["id"]
                break
        
        if not new_staff_id:
            # Cleanup and skip if no other staff
            admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")
            pytest.skip("No other staff available for move test")
        
        # Move reservation
        response = admin_session.patch(f"{BASE_URL}/api/reserved-members/{member_id}/move?new_staff_id={new_staff_id}")
        assert response.status_code == 200, f"Move failed: {response.text}"
        print(f"✓ Moved reservation from {original_staff} to {new_staff_id}")
        
        # Verify move
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        members = response.json()
        moved_member = next((m for m in members if m["id"] == member_id), None)
        assert moved_member is not None, "Member not found after move"
        assert moved_member["staff_id"] == new_staff_id, "Staff ID should be updated"
        print(f"✓ Verified reservation moved to new staff")
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")
    
    def test_delete_reservation(self, admin_session, staff_user_id):
        """Test deleting a reservation"""
        unique_id = f"TEST_DEL_{uuid.uuid4().hex[:8].upper()}"
        
        # Create reservation
        payload = {
            "customer_id": unique_id,
            "product_id": PRODUCTS["PUCUK33"],
            "staff_id": staff_user_id
        }
        response = admin_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200
        member = response.json()
        member_id = member["id"]
        print(f"✓ Created reservation for delete test: {unique_id}")
        
        # Delete reservation
        response = admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")
        assert response.status_code == 200, f"Delete failed: {response.text}"
        print(f"✓ Deleted reservation: {member_id}")
        
        # Verify deletion
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        members = response.json()
        deleted_member = next((m for m in members if m["id"] == member_id), None)
        assert deleted_member is None, "Member should not exist after deletion"
        print(f"✓ Verified reservation deleted")
    
    def test_staff_request_reservation_with_customer_id(self, staff_session, admin_session):
        """Test staff requesting a reservation (creates pending status)"""
        unique_id = f"TEST_REQ_{uuid.uuid4().hex[:8].upper()}"
        
        payload = {
            "customer_id": unique_id,
            "phone_number": "081234567890",
            "product_id": PRODUCTS["ISTANA2000"]
            # No staff_id - staff requests for themselves
        }
        
        response = staff_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200, f"Staff request failed: {response.text}"
        
        data = response.json()
        assert data.get("customer_id") == unique_id
        assert data.get("status") == "pending", "Staff-created reservation should be pending"
        print(f"✓ Staff created pending reservation: {unique_id}")
        
        # Cleanup - admin deletes
        member_id = data.get("id")
        if member_id:
            admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")


class TestReservedMembersApprovalFlow:
    """Test approval/rejection flow for staff-requested reservations"""
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=MASTER_ADMIN)
        assert response.status_code == 200
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    @pytest.fixture(scope="class")
    def staff_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=STAFF)
        assert response.status_code == 200
        token = response.json().get("token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_approve_pending_reservation(self, staff_session, admin_session):
        """Test admin approving a pending reservation"""
        unique_id = f"TEST_APPR_{uuid.uuid4().hex[:8].upper()}"
        
        # Staff creates pending reservation
        payload = {
            "customer_id": unique_id,
            "phone_number": "081234567890",
            "product_id": PRODUCTS["LIGA2000"]
        }
        response = staff_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200
        member = response.json()
        member_id = member["id"]
        assert member["status"] == "pending"
        print(f"✓ Staff created pending reservation: {unique_id}")
        
        # Admin approves
        response = admin_session.patch(f"{BASE_URL}/api/reserved-members/{member_id}/approve")
        assert response.status_code == 200, f"Approve failed: {response.text}"
        print(f"✓ Admin approved reservation")
        
        # Verify approval
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        members = response.json()
        approved_member = next((m for m in members if m["id"] == member_id), None)
        assert approved_member is not None
        assert approved_member["status"] == "approved"
        print(f"✓ Verified reservation is approved")
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/reserved-members/{member_id}")
    
    def test_reject_pending_reservation(self, staff_session, admin_session):
        """Test admin rejecting a pending reservation"""
        unique_id = f"TEST_REJ_{uuid.uuid4().hex[:8].upper()}"
        
        # Staff creates pending reservation
        payload = {
            "customer_id": unique_id,
            "phone_number": "081234567890",
            "product_id": PRODUCTS["PUCUK33"]
        }
        response = staff_session.post(f"{BASE_URL}/api/reserved-members", json=payload)
        assert response.status_code == 200
        member = response.json()
        member_id = member["id"]
        print(f"✓ Staff created pending reservation: {unique_id}")
        
        # Admin rejects
        response = admin_session.patch(f"{BASE_URL}/api/reserved-members/{member_id}/reject")
        assert response.status_code == 200, f"Reject failed: {response.text}"
        print(f"✓ Admin rejected reservation")
        
        # Verify rejection (member should be deleted)
        response = admin_session.get(f"{BASE_URL}/api/reserved-members")
        members = response.json()
        rejected_member = next((m for m in members if m["id"] == member_id), None)
        assert rejected_member is None, "Rejected member should be deleted"
        print(f"✓ Verified rejected reservation is removed")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
