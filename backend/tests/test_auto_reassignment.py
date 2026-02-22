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

class TestAutoReassignment:
    """Test suite for auto-reassignment feature"""
    
    admin_token = None
    staff_token = None
    staff_user_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin and staff tokens"""
        # Login as admin
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        self.admin_token = resp.json().get('access_token')
        
        # Login as staff
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDENTIALS)
        assert resp.status_code == 200, f"Staff login failed: {resp.text}"
        staff_data = resp.json()
        self.staff_token = staff_data.get('access_token')
        self.staff_user_id = staff_data.get('user', {}).get('id')
        
    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
    
    def staff_headers(self):
        return {"Authorization": f"Bearer {self.staff_token}", "Content-Type": "application/json"}
    
    # Helper functions for cleanup
    def cleanup_test_customer(self, customer_id):
        """Remove test customer from reserved_members, deleted_reserved_members, notifications"""
        try:
            # Get reserved member by customer_id and delete
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.admin_headers())
            if resp.status_code == 200:
                for member in resp.json():
                    if member.get('customer_id') == customer_id or member.get('customer_name') == customer_id:
                        requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=self.admin_headers())
        except:
            pass
    
    # TEST 1: Manual admin deletion archives to deleted_reserved_members
    def test_1_manual_admin_deletion_archives_with_correct_reason(self):
        """
        When admin manually deletes a reserved member, it should:
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
                "staff_id": self.staff_user_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=self.admin_headers())
            assert resp.status_code in [200, 201], f"Failed to create reservation: {resp.text}"
            reservation = resp.json()
            reservation_id = reservation.get('id')
            
            # Step 2: Delete the reservation as admin
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=self.admin_headers())
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            
            # Step 3: Verify it's in deleted_reserved_members with correct reason
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=self.admin_headers())
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
            # Cleanup
            self.cleanup_test_customer(test_customer_id)
    
    # TEST 2 & 3 & 4: Auto-reassignment flow
    def test_2_auto_reassignment_on_new_omset(self):
        """
        When staff records omset for a customer who had a deleted/expired reservation:
        - If customer is NOT currently reserved by anyone else
        - A new reservation should be auto-created
        - The entry should be removed from deleted_reserved_members
        """
        test_customer_id = f"TEST_REASSIGN_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Create a reservation as admin for staff
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": self.staff_user_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=self.admin_headers())
            assert resp.status_code in [200, 201], f"Failed to create reservation: {resp.text}"
            reservation = resp.json()
            original_reservation_id = reservation.get('id')
            
            # Step 2: Delete the reservation as admin (archives to deleted_reserved_members)
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{original_reservation_id}", headers=self.admin_headers())
            assert resp.status_code == 200, f"Failed to delete reservation: {resp.text}"
            
            # Verify it's in deleted archive
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=self.admin_headers())
            assert resp.status_code == 200
            deleted_before = [m for m in resp.json() if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_before) > 0, "Deleted reservation not found in archive before omset"
            
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
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=self.staff_headers())
            assert resp.status_code == 200, f"Failed to create omset: {resp.text}"
            omset_record = resp.json()
            
            # Step 4: Verify reservation is AUTO-RESTORED
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.admin_headers())
            assert resp.status_code == 200
            reserved_members = resp.json()
            
            restored_reservation = None
            for member in reserved_members:
                if member.get('customer_id') == test_customer_id or member.get('customer_name') == test_customer_id:
                    restored_reservation = member
                    break
            
            assert restored_reservation is not None, f"Auto-restored reservation for {test_customer_id} not found"
            
            # Verify properties of restored reservation (TEST 3)
            assert restored_reservation.get('status') == 'approved', \
                f"Expected status='approved', got '{restored_reservation.get('status')}'"
            assert restored_reservation.get('created_by') == 'system', \
                f"Expected created_by='system', got '{restored_reservation.get('created_by')}'"
            assert restored_reservation.get('auto_reassigned') == True, \
                f"Expected auto_reassigned=True, got '{restored_reservation.get('auto_reassigned')}'"
            
            # Verify last_omset_date is set (TEST 8)
            assert restored_reservation.get('last_omset_date') == today, \
                f"Expected last_omset_date='{today}', got '{restored_reservation.get('last_omset_date')}'"
            
            # Step 5: Verify entry is REMOVED from deleted_reserved_members (TEST 4)
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=self.admin_headers())
            assert resp.status_code == 200
            deleted_after = [m for m in resp.json() if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_after) == 0, f"Entry should be removed from deleted_reserved_members after auto-reassignment, but found {len(deleted_after)}"
            
            print("TEST 2,3,4,8 PASSED: Auto-reassignment creates proper entry, removes from archive, sets last_omset_date")
            
        finally:
            # Cleanup - delete the omset record and reservation
            self.cleanup_test_customer(test_customer_id)
    
    # TEST 5: Notification created for staff
    def test_5_auto_reassignment_creates_notification(self):
        """
        When auto-reassignment happens, a notification should be created for the staff:
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
                "staff_id": self.staff_user_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=self.admin_headers())
            assert resp.status_code in [200, 201]
            reservation_id = resp.json().get('id')
            
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=self.admin_headers())
            assert resp.status_code == 200
            
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
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=self.staff_headers())
            assert resp.status_code == 200
            
            # Step 3: Check staff notifications
            resp = requests.get(f"{BASE_URL}/api/staff-notifications", headers=self.staff_headers())
            assert resp.status_code == 200, f"Failed to get staff notifications: {resp.text}"
            notifications = resp.json()
            
            # Find the auto-restored notification
            auto_restore_notif = None
            for notif in notifications:
                if notif.get('type') == 'reservation_auto_restored' and test_customer_id in str(notif.get('data', {})):
                    auto_restore_notif = notif
                    break
            
            assert auto_restore_notif is not None, f"Notification for reservation_auto_restored not found"
            assert auto_restore_notif.get('user_id') == self.staff_user_id, \
                f"Notification should use 'user_id' field with staff's ID"
            
            print("TEST 5 PASSED: Auto-reassignment creates notification with type='reservation_auto_restored' and user_id field")
            
        finally:
            self.cleanup_test_customer(test_customer_id)
    
    # TEST 6: NEGATIVE - No auto-reassignment if customer already reserved by someone else
    def test_6_no_reassignment_if_customer_reserved_by_another(self):
        """
        NEGATIVE TEST: Auto-reassignment should NOT happen if:
        - The customer is currently reserved by a DIFFERENT staff member
        """
        test_customer_id = f"TEST_REASSIGN_NEG_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Create a second staff user or use another existing staff
            # For this test, we'll create a reservation for the admin as the "other staff"
            # First, get admin user ID
            resp = requests.get(f"{BASE_URL}/api/users", headers=self.admin_headers())
            other_staff_id = None
            if resp.status_code == 200:
                for user in resp.json():
                    if user.get('email') == 'vicky@crm.com':
                        other_staff_id = user.get('id')
                        break
            
            # If we can't find another staff, we'll simulate with admin
            if not other_staff_id:
                # Use admin's ID as the "other staff"
                resp = requests.get(f"{BASE_URL}/api/auth/me", headers=self.admin_headers())
                other_staff_id = resp.json().get('id')
            
            # Step 2: Create a reservation for our test staff, then delete it
            create_data = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": self.staff_user_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data, headers=self.admin_headers())
            assert resp.status_code in [200, 201]
            reservation_id = resp.json().get('id')
            
            # Delete it (archives it)
            resp = requests.delete(f"{BASE_URL}/api/reserved-members/{reservation_id}", headers=self.admin_headers())
            assert resp.status_code == 200
            
            # Step 3: Create a CURRENT reservation for the SAME customer but DIFFERENT staff (admin)
            create_data_other = {
                "customer_id": test_customer_id,
                "phone_number": "08123456789",
                "product_id": PRODUCT_ID,
                "staff_id": other_staff_id
            }
            resp = requests.post(f"{BASE_URL}/api/reserved-members", json=create_data_other, headers=self.admin_headers())
            # This should create or could be duplicate, either way customer is now reserved by other
            other_reservation_id = None
            if resp.status_code in [200, 201]:
                other_reservation_id = resp.json().get('id')
            
            # Step 4: Staff records omset - should NOT trigger auto-reassignment
            # (because customer is already reserved by someone else)
            omset_data = {
                "product_id": PRODUCT_ID,
                "record_date": today,
                "customer_name": test_customer_id,
                "customer_id": test_customer_id,
                "nominal": 200000,
                "depo_kelipatan": 1.0,
                "keterangan": "Test omset - should be pending due to conflict"
            }
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=self.staff_headers())
            # The omset might be created as 'pending' due to conflict
            assert resp.status_code == 200, f"Omset creation failed: {resp.text}"
            omset_record = resp.json()
            
            # Verify the omset is pending (conflict with other staff's reservation)
            # OR if approved, verify NO new reservation was created for our staff
            if omset_record.get('approval_status') == 'pending':
                print("TEST 6 PASSED: Omset is pending because customer is reserved by another staff")
            else:
                # Check that no auto-reassignment happened - the reservation should still be with other_staff
                resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.admin_headers())
                assert resp.status_code == 200
                reserved_members = resp.json()
                
                # Find reservations for this customer
                reservations_for_customer = [m for m in reserved_members 
                                            if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
                
                # Should only be the other staff's reservation (the one we created in step 3)
                staff_reservations = [m for m in reservations_for_customer if m.get('staff_id') == self.staff_user_id]
                assert len(staff_reservations) == 0, \
                    f"Auto-reassignment should NOT happen when customer is reserved by another staff"
                
                print("TEST 6 PASSED: No auto-reassignment when customer is already reserved by another staff")
            
        finally:
            # Cleanup
            self.cleanup_test_customer(test_customer_id)
    
    # TEST 7: NEGATIVE - No auto-reassignment if no deleted reservation exists
    def test_7_no_reassignment_if_no_deleted_reservation(self):
        """
        NEGATIVE TEST: Auto-reassignment should NOT happen if:
        - There is no deleted reservation in the archive for this customer+staff+product
        """
        test_customer_id = f"TEST_REASSIGN_NEW_{uuid.uuid4().hex[:8].upper()}"
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Step 1: Verify this customer has NO prior reservations (deleted or active)
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.admin_headers())
            assert resp.status_code == 200
            existing_reservations = [m for m in resp.json() 
                                    if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(existing_reservations) == 0, "Test customer should not have existing reservations"
            
            resp = requests.get(f"{BASE_URL}/api/reserved-members/deleted", headers=self.admin_headers())
            assert resp.status_code == 200
            deleted_reservations = [m for m in resp.json() 
                                   if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            assert len(deleted_reservations) == 0, "Test customer should not have deleted reservations"
            
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
            resp = requests.post(f"{BASE_URL}/api/omset", json=omset_data, headers=self.staff_headers())
            assert resp.status_code == 200, f"Omset creation failed: {resp.text}"
            
            # Step 3: Verify NO reservation was auto-created
            resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.admin_headers())
            assert resp.status_code == 200
            reservations_after = [m for m in resp.json() 
                                 if m.get('customer_id') == test_customer_id or m.get('customer_name') == test_customer_id]
            
            assert len(reservations_after) == 0, \
                f"No auto-reassignment should happen for customers without deleted reservations. Found {len(reservations_after)} reservations."
            
            print("TEST 7 PASSED: No auto-reassignment for customers without deleted reservations")
            
        finally:
            self.cleanup_test_customer(test_customer_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
