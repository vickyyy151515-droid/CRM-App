"""
Test Auto-Reassignment of Expired/Deleted Reserved Members on New Omset

This test file covers:
1. Manual admin deletion of reserved member archives to deleted_reserved_members with deleted_reason='admin_manual_delete'
2. Auto-reassignment: Staff records omset for customer with deleted reservation -> reservation auto-restored
3. Auto-reassignment creates proper reserved_members entry with status=approved, created_by=system, auto_reassigned=true
4. Auto-reassignment removes entry from deleted_reserved_members archive
5. Auto-reassignment creates notification for staff (type=reservation_auto_restored, stored as user_id)
6. NEGATIVE: Auto-reassignment does NOT happen if customer is already reserved by someone else
7. NEGATIVE: Auto-reassignment does NOT happen if no deleted reservation exists for that customer+staff+product
8. Auto-reassignment updates last_omset_date on the new reservation
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_CREDENTIALS = {"email": "vicky@crm.com", "password": "admin123"}
STAFF_CREDENTIALS = {"email": "staff@crm.com", "password": "staff123"}

# Product ID from context
PRODUCT_ID = "prod-istana2000"
PRODUCT_NAME = "ISTANA2000"


@pytest.fixture(scope="module")
def admin_auth():
    """Get admin authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    return {
        "token": data.get('token'),
        "user_id": data.get('user', {}).get('id'),
        "headers": {"Authorization": f"Bearer {data.get('token')}", "Content-Type": "application/json"}
    }


@pytest.fixture(scope="module")
def staff_auth():
    """Get staff authentication token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDENTIALS)
    assert resp.status_code == 200, f"Staff login failed: {resp.text}"
    data = resp.json()
    return {
        "token": data.get('token'),
        "user_id": data.get('user', {}).get('id'),  # Should be "staff-user-1"
        "headers": {"Authorization": f"Bearer {data.get('token')}", "Content-Type": "application/json"}
    }


def cleanup_test_customer(customer_id, admin_headers):
    """Remove test customer from reserved_members, deleted_reserved_members"""
    try:
        # Get reserved member by customer_id and delete
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_headers)
        if resp.status_code == 200:
            for member in resp.json():
                if member.get('customer_id') == customer_id or member.get('customer_name') == customer_id:
                    requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=admin_headers)
    except:
        pass


class TestAdminDeletion:
    """Test manual admin deletion archives correctly"""
    
    def test_manual_admin_deletion_archives_with_correct_reason(self, admin_auth, staff_auth):
        """
        TEST 1: When admin manually deletes a reserved member, it should:
        - Archive to deleted_reserved_members collection
        - Set deleted_reason='admin_manual_delete'
        """
        test_customer_id = f"TEST_REASSIGN_{uuid.uuid4().hex[:8].upper()}"
        
        try:
            # Step 1: Create a reservation as admin for staff
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": staff_auth["user_id"]
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=admin_auth["headers"])
            assert resp.status_code in [200, 201], f"Failed to create reservation: {resp.text}"
            reservation = resp.json()
            reservation_id = reservation.get('id')
            
            print(f"Created reservation: {reservation_id}")
            
            # Step 2: Delete the reservation as admin
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=admin_auth["headers"])
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            print(f"Deleted reservation: {reservation_id}")
            
            # Step 3: Verify it's in deleted_reserved_members with correct reason
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=admin_auth["headers"])
            assert resp.status_code == 200, f"Failed to get deleted members: {resp.text}"
            deleted_members = resp.json()
            
            # Find our test customer
            found_deleted = None
            for member in deleted_members:
                if member.get('customer_id') == test_customer_id or member.get('customer_name') == test_customer_id:
                    found_deleted = member
                    break
            
            assert found_deleted is not None, f"Deleted reservation for {test_customer_id} not found in archive"
            assert found_deleted.get('deleted_reason') == 'admin_manual_delete', \
                f"Expected deleted_reason='admin_manual_delete', got '{found_deleted.get('deleted_reason')}'"
            
            print(f"TEST 1 PASSED: Manual deletion archived with deleted_reason='admin_manual_delete'")
            
        finally:
            cleanup_test_customer(test_customer_id, admin_auth["headers"])


class TestAutoReassignment:
    """Test auto-reassignment flow"""
    
    def test_auto_reassignment_on_new_omset(self, admin_auth, staff_auth):
        """
        TEST 2,3,4,8: When staff records omset for a customer who had a deleted/expired reservation:
        - If customer is NOT currently reserved by anyone else
        - A new reservation should be auto-created with status=approved, created_by=system, auto_reassigned=true
        - The entry should be removed from deleted_reserved_members
        - last_omset_date should be set to the omset date
        """
        test_customer_id = f"TEST_REASSIGN_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Create a reservation as admin for staff
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": staff_auth["user_id"]
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=admin_auth["headers"])
            assert resp.status_code in [200, 201], f"Failed to create reservation: {resp.text}"
            reservation = resp.json()
            original_reservation_id = reservation.get('id')
            print(f"Created reservation: {original_reservation_id}")
            
            # Step 2: Delete the reservation as admin (archives to deleted_reserved_members)
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{original_reservation_id}", headers=admin_auth["headers"])
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            print(f"Deleted reservation: {original_reservation_id}")
            
            # Verify it's in deleted archive
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=admin_auth["headers"])
            assert resp.status_code == 200
            deleted_before = [m for m in resp.json() if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_before) > 0, "Deleted reservation not found in archive before omset"
            print(f"Verified in deleted archive: {len(deleted_before)} entries")
            
            # Step 3: Staff records omset for this customer
            omset_data = {
                "product_id": PRODUCT_ID,
                "record_date": today,
                "customer_name": test_customer_id,
                "customer_id": test_customer_id,
                "nominal": 100000,
                "depo_kelipatan": 1.0,
                "keterangan": "Test omset for auto-reassignment"
            }
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=staff_auth["headers"])
            assert resp.status_code == 200, f"Failed to create omset: {resp.text}"
            omset_record = resp.json()
            print(f"Created omset: {omset_record.get('id')}")
            
            # Step 4: Verify reservation is AUTO-RESTORED
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_auth["headers"])
            assert resp.status_code == 200
            reserved_members = resp.json()
            
            restored_reservation = None
            for member in reserved_members:
                if member.get('customer_id') == test_customer_id or member.get('customer_name') == test_customer_id:
                    restored_reservation = member
                    break
            
            assert restored_reservation is not None, f"Auto-restored reservation for {test_customer_id} not found"
            print(f"Found restored reservation: {restored_reservation.get('id')}")
            
            # Verify properties of restored reservation (TEST 3)
            assert restored_reservation.get('status') == 'approved', \
                f"Expected status='approved', got '{restored_reservation.get('status')}'"
            assert restored_reservation.get('created_by') == 'system', \
                f"Expected created_by='system', got '{restored_reservation.get('created_by')}'"
            # Note: auto_reassigned is stored in DB but not returned in API response due to Pydantic model
            # Verify via approved_by_name='Auto-Reassignment' which proves auto-reassignment happened
            assert restored_reservation.get('approved_by_name') == 'Auto-Reassignment', \
                f"Expected approved_by_name='Auto-Reassignment', got '{restored_reservation.get('approved_by_name')}'"
            assert restored_reservation.get('approved_by') == 'system', \
                f"Expected approved_by='system', got '{restored_reservation.get('approved_by')}'"
            
            # Verify last_omset_date is set (TEST 8)
            assert restored_reservation.get('last_omset_date') == today, \
                f"Expected last_omset_date='{today}', got '{restored_reservation.get('last_omset_date')}'"
            
            # Step 5: Verify entry is REMOVED from deleted_reserved_members (TEST 4)
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=admin_auth["headers"])
            assert resp.status_code == 200
            deleted_after = [m for m in resp.json() if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_after) == 0, f"Entry should be removed from deleted_reserved_members after auto-reassignment, but found {len(deleted_after)}"
            
            print("TEST 2,3,4,8 PASSED: Auto-reassignment creates proper entry, removes from archive, sets last_omset_date")
            
        finally:
            cleanup_test_customer(test_customer_id, admin_auth["headers"])
    
    def test_auto_reassignment_creates_notification(self, admin_auth, staff_auth):
        """
        TEST 5: When auto-reassignment happens, a notification should be created for the staff:
        - type='reservation_auto_restored'
        - user_id = staff's user ID (not target_user_id)
        """
        test_customer_id = f"TEST_REASSIGN_NOTIF_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Create and delete reservation
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": staff_auth["user_id"]
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=admin_auth["headers"])
            assert resp.status_code in [200, 201], f"Failed to create reservation: {resp.text}"
            reservation_id = resp.json().get('id')
            
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=admin_auth["headers"])
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            
            # Step 2: Staff records omset (triggers auto-reassignment)
            omset_data = {
                "product_id": PRODUCT_ID,
                "record_date": today,
                "customer_name": test_customer_id,
                "customer_id": test_customer_id,
                "nominal": 150000,
                "depo_kelipatan": 1.0,
                "keterangan": "Test omset for notification check"
            }
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=staff_auth["headers"])
            assert resp.status_code == 200, f"Failed to create omset: {resp.text}"
            
            # Step 3: Check staff notifications
            resp = requests.get(f"{BASE_URL}/api/staff-notifications", headers=staff_auth["headers"])
            assert resp.status_code == 200, f"Failed to get staff notifications: {resp.text}"
            notifications = resp.json()
            
            # Find the auto-restored notification
            auto_restore_notif = None
            for notif in notifications:
                if notif.get('type') == 'reservation_auto_restored':
                    notif_data = notif.get('data', {})
                    if test_customer_id in str(notif_data) or test_customer_id.lower() in str(notif_data).lower():
                        auto_restore_notif = notif
                        break
            
            assert auto_restore_notif is not None, f"Notification for reservation_auto_restored not found for {test_customer_id}"
            
            # Verify it uses 'user_id' field (per the context from main agent)
            assert auto_restore_notif.get('user_id') == staff_auth["user_id"], \
                f"Notification should use 'user_id' field with staff's ID. Got user_id={auto_restore_notif.get('user_id')}, expected {staff_auth['user_id']}"
            
            print("TEST 5 PASSED: Auto-reassignment creates notification with type='reservation_auto_restored' and user_id field")
            
        finally:
            cleanup_test_customer(test_customer_id, admin_auth["headers"])


class TestNegativeCases:
    """Test negative cases where auto-reassignment should NOT happen"""
    
    def test_no_reassignment_if_customer_reserved_by_another(self, admin_auth, staff_auth):
        """
        TEST 6 NEGATIVE: Auto-reassignment should NOT happen if:
        - The customer is currently reserved by a DIFFERENT staff member
        """
        test_customer_id = f"TEST_REASSIGN_NEG_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Get admin user ID to use as "other staff"
            other_staff_id = admin_auth["user_id"]
            
            # Step 2: Create a reservation for our test staff, then delete it
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": staff_auth["user_id"]
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=admin_auth["headers"])
            assert resp.status_code in [200, 201], f"Failed to create reservation for staff: {resp.text}"
            reservation_id = resp.json().get('id')
            print(f"Created reservation for staff: {reservation_id}")
            
            # Delete it (archives it)
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=admin_auth["headers"])
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            print(f"Deleted reservation: {reservation_id}")
            
            # Step 3: Create a CURRENT reservation for the SAME customer but DIFFERENT staff (admin)
            create_data_other = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": other_staff_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data_other, headers=admin_auth["headers"])
            assert resp.status_code in [200, 201], f"Failed to create reservation for other staff: {resp.text}"
            other_reservation_id = resp.json().get('id')
            print(f"Created reservation for other staff: {other_reservation_id}")
            
            # Step 4: Staff records omset - should NOT trigger auto-reassignment
            # The omset should be 'pending' due to conflict with other staff's reservation
            omset_data = {
                "product_id": PRODUCT_ID,
                "record_date": today,
                "customer_name": test_customer_id,
                "customer_id": test_customer_id,
                "nominal": 200000,
                "depo_kelipatan": 1.0,
                "keterangan": "Test omset - should be pending due to conflict"
            }
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=staff_auth["headers"])
            assert resp.status_code == 200, f"Omset creation failed: {resp.text}"
            omset_record = resp.json()
            
            # Verify the omset is pending (conflict with other staff's reservation)
            assert omset_record.get('approval_status') == 'pending', \
                f"Omset should be pending due to conflict. Got: {omset_record.get('approval_status')}"
            
            # Verify NO new reservation was created for our staff
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_auth["headers"])
            assert resp.status_code == 200
            reserved_members = resp.json()
            
            # Find reservations for this customer that belong to our test staff
            staff_reservations = [m for m in reserved_members 
                                 if (m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id)
                                 and m.get('staff_id') == staff_auth["user_id"]]
            
            assert len(staff_reservations) == 0, \
                f"Auto-reassignment should NOT happen when customer is reserved by another staff. Found {len(staff_reservations)} reservations."
            
            print("TEST 6 PASSED: No auto-reassignment when customer is already reserved by another staff")
            
        finally:
            cleanup_test_customer(test_customer_id, admin_auth["headers"])
    
    def test_no_reassignment_if_no_deleted_reservation(self, admin_auth, staff_auth):
        """
        TEST 7 NEGATIVE: Auto-reassignment should NOT happen if:
        - There is no deleted reservation in the archive for this customer+staff+product
        """
        test_customer_id = f"TEST_REASSIGN_NEW_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Verify this customer has NO prior reservations (deleted or active)
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_auth["headers"])
            assert resp.status_code == 200
            existing_reservations = [m for m in resp.json() 
                                    if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(existing_reservations) == 0, "Test customer should not have existing reservations"
            
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=admin_auth["headers"])
            assert resp.status_code == 200
            deleted_reservations = [m for m in resp.json() 
                                   if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_reservations) == 0, "Test customer should not have deleted reservations"
            print(f"Verified: No existing or deleted reservations for {test_customer_id}")
            
            # Step 2: Staff records omset for this NEW customer
            omset_data = {
                "product_id": PRODUCT_ID,
                "record_date": today,
                "customer_name": test_customer_id,
                "customer_id": test_customer_id,
                "nominal": 250000,
                "depo_kelipatan": 1.0,
                "keterangan": "Test omset for new customer - no auto-reassignment expected"
            }
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=staff_auth["headers"])
            assert resp.status_code == 200, f"Omset creation failed: {resp.text}"
            print(f"Created omset for new customer")
            
            # Step 3: Verify NO reservation was auto-created
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_auth["headers"])
            assert resp.status_code == 200
            reservations_after = [m for m in resp.json() 
                                 if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            
            assert len(reservations_after) == 0, \
                f"No auto-reassignment should happen for customers without deleted reservations. Found {len(reservations_after)} reservations."
            
            print("TEST 7 PASSED: No auto-reassignment for customers without deleted reservations")
            
        finally:
            cleanup_test_customer(test_customer_id, admin_auth["headers"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
