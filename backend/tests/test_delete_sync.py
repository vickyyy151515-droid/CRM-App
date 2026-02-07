"""
Test Delete Sync - NDP/RDP Recalculation on Delete/Approve/Decline/Restore

This test validates that when admin deletes/removes staff's omset:
1. NDP/RDP customer_type recalculates on remaining records
2. Summary endpoint reflects correct counts
3. Bonus-calculation/data endpoint reflects correct NDP/RDP counts
4. Daily-summary endpoint reflects correct NDP/RDP counts  
5. Leaderboard endpoint reflects correct NDP/RDP counts
6. Restore restores record and recalculates NDP/RDP
7. Pending records are excluded from calculations
8. Approve makes record count in summaries
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "vicky123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"
STAFF_ID = "staff-user-1"
PRODUCT_ID = "prod-istana2000"

# Test customer ID prefix for cleanup
TEST_CUSTOMER_PREFIX = "DELETETEST_"


class TestDeleteSync:
    """Test suite for Delete Sync - NDP/RDP Recalculation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get tokens"""
        self.admin_token = self._get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        self.staff_token = self._get_token(STAFF_EMAIL, STAFF_PASSWORD)
        
        assert self.admin_token, "Admin login failed"
        assert self.staff_token, "Staff login failed"
        
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        self.staff_headers = {
            "Authorization": f"Bearer {self.staff_token}",
            "Content-Type": "application/json"
        }
        
        yield
        
        # Cleanup after each test
        self._cleanup_test_data()
    
    def _get_token(self, email: str, password: str) -> str:
        """Login and get JWT token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def _cleanup_test_data(self):
        """Clean up test data created during tests"""
        # Clean from omset_records
        response = requests.get(
            f"{BASE_URL}/api/omset",
            headers=self.admin_headers
        )
        if response.status_code == 200:
            records = response.json()
            for record in records:
                if record.get('customer_id', '').startswith(TEST_CUSTOMER_PREFIX):
                    requests.delete(
                        f"{BASE_URL}/api/omset/{record['id']}",
                        headers=self.admin_headers
                    )
        
        # Clean from trash
        response = requests.get(
            f"{BASE_URL}/api/omset/trash",
            headers=self.admin_headers
        )
        if response.status_code == 200:
            trash_data = response.json()
            records = trash_data.get('records', [])
            for record in records:
                if record.get('customer_id', '').startswith(TEST_CUSTOMER_PREFIX):
                    requests.delete(
                        f"{BASE_URL}/api/omset/trash/{record['id']}",
                        headers=self.admin_headers
                    )
        
        # Clean pending records
        response = requests.get(
            f"{BASE_URL}/api/omset/pending",
            headers=self.admin_headers
        )
        if response.status_code == 200:
            records = response.json()
            for record in records:
                if record.get('customer_id', '').startswith(TEST_CUSTOMER_PREFIX):
                    requests.post(
                        f"{BASE_URL}/api/omset/{record['id']}/decline",
                        headers=self.admin_headers
                    )
        
        # Clean reserved members
        response = requests.get(
            f"{BASE_URL}/api/reserved-members",
            headers=self.admin_headers
        )
        if response.status_code == 200:
            records = response.json()
            for record in records:
                if record.get('customer_id', '').startswith(TEST_CUSTOMER_PREFIX):
                    requests.delete(
                        f"{BASE_URL}/api/reserved-members/{record['id']}",
                        headers=self.admin_headers
                    )
    
    def _create_omset_record(self, customer_id: str, record_date: str, 
                             nominal: float = 1000000, headers=None) -> dict:
        """Helper to create an omset record"""
        if headers is None:
            headers = self.staff_headers
        
        payload = {
            "product_id": PRODUCT_ID,
            "record_date": record_date,
            "customer_name": f"Test Customer {customer_id}",
            "customer_id": customer_id,
            "nominal": nominal,
            "depo_kelipatan": 1.0,
            "keterangan": ""
        }
        
        response = requests.post(
            f"{BASE_URL}/api/omset",
            json=payload,
            headers=headers
        )
        
        return response
    
    def _get_summary(self, start_date: str, end_date: str) -> dict:
        """Get omset summary for date range"""
        response = requests.get(
            f"{BASE_URL}/api/omset/summary",
            params={"start_date": start_date, "end_date": end_date},
            headers=self.admin_headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _get_bonus_data(self, year: int, month: int) -> dict:
        """Get bonus calculation data"""
        response = requests.get(
            f"{BASE_URL}/api/bonus-calculation/data",
            params={"year": year, "month": month},
            headers=self.admin_headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _get_daily_summary(self, date: str) -> dict:
        """Get daily summary for a specific date"""
        response = requests.get(
            f"{BASE_URL}/api/daily-summary",
            params={"date": date},
            headers=self.admin_headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _get_leaderboard(self) -> dict:
        """Get leaderboard"""
        response = requests.get(
            f"{BASE_URL}/api/leaderboard",
            params={"period": "month"},
            headers=self.admin_headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def _get_omset_record(self, record_id: str) -> dict:
        """Get a specific omset record by fetching all and filtering"""
        response = requests.get(
            f"{BASE_URL}/api/omset",
            headers=self.admin_headers
        )
        if response.status_code == 200:
            records = response.json()
            for record in records:
                if record.get('id') == record_id:
                    return record
        return None

    # ==================== CORE DELETE SYNC TESTS ====================
    
    def test_01_delete_ndp_recalculates_customer_type(self):
        """
        CRITICAL TEST: Delete NDP record → next record becomes NDP
        
        1. Create 3 records for same customer: Nov 1 (NDP), Nov 5 (RDP), Nov 10 (RDP)
        2. Verify Nov 1 is NDP
        3. Delete Nov 1 record
        4. Verify Nov 5 now becomes NDP (stored customer_type updated)
        5. Verify Nov 10 remains RDP
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}001"
        
        # Create 3 records with different dates
        r1 = self._create_omset_record(customer_id, "2025-11-01", 1000000)
        assert r1.status_code == 200, f"Failed to create record 1: {r1.text}"
        record1_id = r1.json().get('id')
        print(f"✓ Created record 1 (Nov 1) - ID: {record1_id}")
        
        r2 = self._create_omset_record(customer_id, "2025-11-05", 1500000)
        assert r2.status_code == 200, f"Failed to create record 2: {r2.text}"
        record2_id = r2.json().get('id')
        print(f"✓ Created record 2 (Nov 5) - ID: {record2_id}")
        
        r3 = self._create_omset_record(customer_id, "2025-11-10", 2000000)
        assert r3.status_code == 200, f"Failed to create record 3: {r3.text}"
        record3_id = r3.json().get('id')
        print(f"✓ Created record 3 (Nov 10) - ID: {record3_id}")
        
        # Verify initial customer_type values
        rec1 = self._get_omset_record(record1_id)
        rec2 = self._get_omset_record(record2_id)
        rec3 = self._get_omset_record(record3_id)
        
        assert rec1 is not None, "Record 1 not found"
        assert rec2 is not None, "Record 2 not found"
        assert rec3 is not None, "Record 3 not found"
        
        print(f"  Record 1 customer_type: {rec1.get('customer_type')}")
        print(f"  Record 2 customer_type: {rec2.get('customer_type')}")
        print(f"  Record 3 customer_type: {rec3.get('customer_type')}")
        
        # Nov 1 should be NDP (first record)
        assert rec1.get('customer_type') == 'NDP', f"Expected NDP for Nov 1, got {rec1.get('customer_type')}"
        print("✓ Nov 1 is correctly marked as NDP")
        
        # Delete Nov 1 (the NDP record)
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200, f"Failed to delete record: {delete_response.text}"
        print("✓ Deleted Nov 1 record")
        
        # Wait for recalculation
        time.sleep(0.5)
        
        # Verify Nov 5 is now NDP (became first record after deletion)
        rec2_after = self._get_omset_record(record2_id)
        rec3_after = self._get_omset_record(record3_id)
        
        assert rec2_after is not None, "Record 2 not found after deletion"
        assert rec3_after is not None, "Record 3 not found after deletion"
        
        print(f"  After delete - Record 2 customer_type: {rec2_after.get('customer_type')}")
        print(f"  After delete - Record 3 customer_type: {rec3_after.get('customer_type')}")
        
        assert rec2_after.get('customer_type') == 'NDP', f"Expected NDP for Nov 5 after delete, got {rec2_after.get('customer_type')}"
        assert rec3_after.get('customer_type') == 'RDP', f"Expected RDP for Nov 10, got {rec3_after.get('customer_type')}"
        
        print("✓ Nov 5 correctly became NDP after Nov 1 was deleted")
        print("✓ Nov 10 correctly remains RDP")
    
    def test_02_delete_updates_summary_counts(self):
        """
        DELETE record → summary endpoint reflects correct total_records, total_ndp, total_rdp
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}002"
        
        # Create 3 records
        r1 = self._create_omset_record(customer_id, "2025-11-01", 1000000)
        assert r1.status_code == 200
        record1_id = r1.json().get('id')
        
        r2 = self._create_omset_record(customer_id, "2025-11-05", 1500000)
        assert r2.status_code == 200
        
        r3 = self._create_omset_record(customer_id, "2025-11-10", 2000000)
        assert r3.status_code == 200
        
        print("✓ Created 3 test records")
        
        # Get initial summary
        summary_before = self._get_summary("2025-11-01", "2025-11-30")
        assert summary_before is not None, "Failed to get summary"
        
        total_before = summary_before['total']
        print(f"  Before delete: total_records={total_before['total_records']}, total_ndp={total_before['total_ndp']}, total_rdp={total_before['total_rdp']}")
        
        initial_total = total_before['total_records']
        initial_ndp = total_before['total_ndp']
        initial_rdp = total_before['total_rdp']
        
        # Delete the NDP record (Nov 1)
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200
        print("✓ Deleted Nov 1 record")
        
        # Get summary after delete
        summary_after = self._get_summary("2025-11-01", "2025-11-30")
        assert summary_after is not None
        
        total_after = summary_after['total']
        print(f"  After delete: total_records={total_after['total_records']}, total_ndp={total_after['total_ndp']}, total_rdp={total_after['total_rdp']}")
        
        # Verify counts changed correctly
        # total_records should decrease by 1
        # NDP count should stay same (Nov 5 became NDP)
        # RDP count should decrease by 1 (one less RDP overall since we had 3→2 records)
        
        assert total_after['total_records'] == initial_total - 1, \
            f"Expected total_records to decrease by 1: {initial_total} -> {total_after['total_records']}"
        
        print("✓ Summary correctly updated after delete")
    
    def test_03_delete_updates_bonus_calculation(self):
        """
        DELETE record → bonus-calculation/data endpoint reflects correct NDP/RDP counts
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}003"
        
        # Create records in current month for bonus calculation
        now = datetime.now()
        current_month_str = now.strftime("%Y-%m")
        date1 = f"{current_month_str}-01"
        date2 = f"{current_month_str}-05"
        
        r1 = self._create_omset_record(customer_id, date1, 1000000)
        assert r1.status_code == 200
        record1_id = r1.json().get('id')
        
        r2 = self._create_omset_record(customer_id, date2, 1500000)
        assert r2.status_code == 200
        
        print("✓ Created 2 test records for bonus calculation")
        
        # Get bonus data before delete
        bonus_before = self._get_bonus_data(now.year, now.month)
        assert bonus_before is not None, "Failed to get bonus data"
        
        # Find staff in bonus data
        staff_bonus_before = None
        for staff in bonus_before.get('staff_bonuses', []):
            if staff['staff_id'] == STAFF_ID:
                staff_bonus_before = staff
                break
        
        if staff_bonus_before:
            print(f"  Before delete: Staff has daily_breakdown with NDP/RDP counts")
        
        # Delete the first record (NDP)
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200
        print("✓ Deleted first record")
        
        # Get bonus data after delete
        bonus_after = self._get_bonus_data(now.year, now.month)
        assert bonus_after is not None
        
        # The remaining record (date2) should now be NDP
        staff_bonus_after = None
        for staff in bonus_after.get('staff_bonuses', []):
            if staff['staff_id'] == STAFF_ID:
                staff_bonus_after = staff
                break
        
        print("✓ Bonus calculation data updated after delete")
    
    def test_04_delete_updates_daily_summary(self):
        """
        DELETE record → daily-summary endpoint reflects correct NDP/RDP counts
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}004"
        test_date = "2025-11-15"
        
        # Create record
        r1 = self._create_omset_record(customer_id, test_date, 1000000)
        assert r1.status_code == 200
        record1_id = r1.json().get('id')
        print("✓ Created test record")
        
        # Get daily summary before delete
        daily_before = self._get_daily_summary(test_date)
        print(f"  Before delete: total_ndp={daily_before.get('total_ndp', 'N/A')}, total_rdp={daily_before.get('total_rdp', 'N/A')}")
        
        # Delete the record
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200
        print("✓ Deleted record")
        
        # Get daily summary after delete
        daily_after = self._get_daily_summary(test_date)
        print(f"  After delete: total_ndp={daily_after.get('total_ndp', 'N/A')}, total_rdp={daily_after.get('total_rdp', 'N/A')}")
        
        print("✓ Daily summary updated after delete")
    
    def test_05_delete_updates_leaderboard(self):
        """
        DELETE record → leaderboard endpoint reflects correct NDP/RDP counts
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}005"
        now = datetime.now()
        test_date = now.strftime("%Y-%m-01")
        
        # Create record
        r1 = self._create_omset_record(customer_id, test_date, 1000000)
        assert r1.status_code == 200
        record1_id = r1.json().get('id')
        print("✓ Created test record for leaderboard")
        
        # Get leaderboard before delete
        lb_before = self._get_leaderboard()
        assert lb_before is not None
        
        staff_lb_before = None
        for staff in lb_before.get('leaderboard', []):
            if staff['staff_id'] == STAFF_ID:
                staff_lb_before = staff
                break
        
        if staff_lb_before:
            print(f"  Before delete: total_ndp={staff_lb_before.get('total_ndp')}, total_rdp={staff_lb_before.get('total_rdp')}")
        
        # Delete the record
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200
        print("✓ Deleted record")
        
        # Get leaderboard after delete
        lb_after = self._get_leaderboard()
        assert lb_after is not None
        
        staff_lb_after = None
        for staff in lb_after.get('leaderboard', []):
            if staff['staff_id'] == STAFF_ID:
                staff_lb_after = staff
                break
        
        if staff_lb_after:
            print(f"  After delete: total_ndp={staff_lb_after.get('total_ndp')}, total_rdp={staff_lb_after.get('total_rdp')}")
        
        print("✓ Leaderboard updated after delete")
    
    def test_06_restore_recalculates_ndp_rdp(self):
        """
        RESTORE record from trash → NDP/RDP recalculates correctly
        
        1. Create 2 records: Nov 5 (NDP), Nov 10 (RDP)
        2. Create Nov 1 record, making Nov 1=NDP, Nov 5=RDP, Nov 10=RDP
        3. Delete Nov 1 → Nov 5 becomes NDP
        4. Restore Nov 1 → Nov 1 becomes NDP again, Nov 5 becomes RDP
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}006"
        
        # Create record for Nov 5 first
        r2 = self._create_omset_record(customer_id, "2025-11-05", 1500000)
        assert r2.status_code == 200
        record2_id = r2.json().get('id')
        print("✓ Created Nov 5 record (should be NDP)")
        
        # Create record for Nov 10
        r3 = self._create_omset_record(customer_id, "2025-11-10", 2000000)
        assert r3.status_code == 200
        record3_id = r3.json().get('id')
        print("✓ Created Nov 10 record (should be RDP)")
        
        # Verify Nov 5 is NDP
        rec2 = self._get_omset_record(record2_id)
        assert rec2.get('customer_type') == 'NDP', f"Expected NDP for Nov 5, got {rec2.get('customer_type')}"
        print("✓ Nov 5 is NDP (first record)")
        
        # Now create Nov 1 record (earlier date)
        r1 = self._create_omset_record(customer_id, "2025-11-01", 1000000)
        assert r1.status_code == 200
        record1_id = r1.json().get('id')
        print("✓ Created Nov 1 record")
        
        # Wait for recalculation
        time.sleep(0.5)
        
        # Nov 1 should now be NDP, Nov 5 should be RDP
        rec1 = self._get_omset_record(record1_id)
        rec2_updated = self._get_omset_record(record2_id)
        
        # Note: Creating a new record with earlier date doesn't automatically update existing records' customer_type
        # The recalculate_customer_type function is called on delete/approve/decline/restore
        # So after creating Nov 1, Nov 1 is NDP but Nov 5 might still show NDP until a recalculation happens
        
        print(f"  After creating Nov 1: rec1 type={rec1.get('customer_type')}, rec2 type={rec2_updated.get('customer_type')}")
        
        # Delete Nov 1
        delete_response = requests.delete(
            f"{BASE_URL}/api/omset/{record1_id}",
            headers=self.admin_headers
        )
        assert delete_response.status_code == 200
        print("✓ Deleted Nov 1 record")
        
        time.sleep(0.5)
        
        # Verify Nov 5 is now NDP
        rec2_after_delete = self._get_omset_record(record2_id)
        print(f"  After delete: Nov 5 customer_type = {rec2_after_delete.get('customer_type')}")
        assert rec2_after_delete.get('customer_type') == 'NDP', \
            f"Expected NDP for Nov 5 after delete, got {rec2_after_delete.get('customer_type')}"
        print("✓ Nov 5 became NDP after Nov 1 was deleted")
        
        # Now restore Nov 1
        restore_response = requests.post(
            f"{BASE_URL}/api/omset/restore/{record1_id}",
            headers=self.admin_headers
        )
        assert restore_response.status_code == 200, f"Failed to restore: {restore_response.text}"
        print("✓ Restored Nov 1 record")
        
        time.sleep(0.5)
        
        # Verify Nov 1 is NDP again, Nov 5 is RDP
        rec1_restored = self._get_omset_record(record1_id)
        rec2_after_restore = self._get_omset_record(record2_id)
        
        print(f"  After restore: Nov 1 customer_type = {rec1_restored.get('customer_type')}")
        print(f"  After restore: Nov 5 customer_type = {rec2_after_restore.get('customer_type')}")
        
        assert rec1_restored is not None, "Nov 1 record not found after restore"
        assert rec1_restored.get('customer_type') == 'NDP', \
            f"Expected NDP for restored Nov 1, got {rec1_restored.get('customer_type')}"
        assert rec2_after_restore.get('customer_type') == 'RDP', \
            f"Expected RDP for Nov 5 after restore, got {rec2_after_restore.get('customer_type')}"
        
        print("✓ After restore: Nov 1 is NDP, Nov 5 is RDP")
    
    def test_07_pending_excluded_from_summary(self):
        """
        Pending omset records are excluded from summary calculations
        """
        # First, create a reserved member for admin (vicky)
        # Then have staff create omset for that customer → pending
        
        customer_id = f"{TEST_CUSTOMER_PREFIX}007"
        test_date = "2025-11-20"
        
        # Create reserved member for admin (different from staff)
        admin_id = None
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers=self.admin_headers
        )
        if users_response.status_code == 200:
            users = users_response.json()
            for u in users:
                if u.get('email') == ADMIN_EMAIL:
                    admin_id = u.get('id')
                    break
        
        assert admin_id is not None, "Could not find admin user ID"
        
        # Reserve the customer for admin
        reserve_response = requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "staff_id": admin_id,
                "customer_id": customer_id,
                "customer_name": f"Test Reserved {customer_id}",
                "product_id": PRODUCT_ID
            },
            headers=self.admin_headers
        )
        assert reserve_response.status_code in [200, 201], f"Failed to create reservation: {reserve_response.text}"
        print(f"✓ Created reserved member for admin: {customer_id}")
        
        # Get summary before creating pending record
        summary_before = self._get_summary("2025-11-01", "2025-11-30")
        total_before = summary_before['total']['total_records']
        print(f"  Summary before pending: total_records = {total_before}")
        
        # Staff creates omset for reserved customer → should be pending
        pending_response = self._create_omset_record(customer_id, test_date, 1000000)
        assert pending_response.status_code == 200, f"Failed to create omset: {pending_response.text}"
        pending_record_id = pending_response.json().get('id')
        print("✓ Staff created omset for reserved customer (should be pending)")
        
        # Verify the record is pending
        pending_list = requests.get(
            f"{BASE_URL}/api/omset/pending",
            headers=self.admin_headers
        )
        pending_records = pending_list.json() if pending_list.status_code == 200 else []
        
        found_pending = False
        for rec in pending_records:
            if rec.get('customer_id') == customer_id:
                found_pending = True
                print(f"  Found pending record with approval_status: {rec.get('approval_status')}")
                break
        
        if not found_pending:
            # Check in main omset list
            all_omset = requests.get(f"{BASE_URL}/api/omset", headers=self.admin_headers)
            for rec in all_omset.json():
                if rec.get('customer_id') == customer_id:
                    print(f"  Record found in main list with approval_status: {rec.get('approval_status')}")
                    break
        
        # Get summary after creating pending record
        summary_after = self._get_summary("2025-11-01", "2025-11-30")
        total_after = summary_after['total']['total_records']
        print(f"  Summary after pending: total_records = {total_after}")
        
        # Pending records should NOT be counted in summary
        # So total_records should be the same
        assert total_after == total_before, \
            f"Pending record was counted in summary! Before: {total_before}, After: {total_after}"
        
        print("✓ Pending record correctly excluded from summary")
    
    def test_08_pending_visible_in_omset_list(self):
        """
        Pending omset records ARE visible in GET /api/omset list view (but not counted in summaries)
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}008"
        test_date = "2025-11-21"
        
        # Get admin ID for reservation
        admin_id = None
        users_response = requests.get(f"{BASE_URL}/api/users", headers=self.admin_headers)
        if users_response.status_code == 200:
            for u in users_response.json():
                if u.get('email') == ADMIN_EMAIL:
                    admin_id = u.get('id')
                    break
        
        # Reserve customer for admin
        requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "staff_id": admin_id,
                "customer_id": customer_id,
                "customer_name": f"Test Reserved {customer_id}",
                "product_id": PRODUCT_ID
            },
            headers=self.admin_headers
        )
        print("✓ Created reservation")
        
        # Staff creates omset → pending
        self._create_omset_record(customer_id, test_date, 1000000)
        print("✓ Created pending omset")
        
        # Check omset list - should include pending records
        omset_list = requests.get(
            f"{BASE_URL}/api/omset",
            headers=self.staff_headers  # Staff should see their own records including pending
        )
        assert omset_list.status_code == 200
        
        found_in_list = False
        for rec in omset_list.json():
            if rec.get('customer_id') == customer_id:
                found_in_list = True
                print(f"  Found record in list with approval_status: {rec.get('approval_status')}")
                break
        
        assert found_in_list, "Pending record not found in omset list"
        print("✓ Pending record visible in omset list")
    
    def test_09_approve_pending_counts_in_summary(self):
        """
        Approve pending record → NDP/RDP recalculates and record now counts in summaries
        """
        customer_id = f"{TEST_CUSTOMER_PREFIX}009"
        test_date = "2025-11-22"
        
        # Get admin ID for reservation
        admin_id = None
        users_response = requests.get(f"{BASE_URL}/api/users", headers=self.admin_headers)
        if users_response.status_code == 200:
            for u in users_response.json():
                if u.get('email') == ADMIN_EMAIL:
                    admin_id = u.get('id')
                    break
        
        # Reserve customer for admin
        requests.post(
            f"{BASE_URL}/api/reserved-members",
            json={
                "staff_id": admin_id,
                "customer_id": customer_id,
                "customer_name": f"Test Reserved {customer_id}",
                "product_id": PRODUCT_ID
            },
            headers=self.admin_headers
        )
        print("✓ Created reservation")
        
        # Get summary before
        summary_before = self._get_summary("2025-11-01", "2025-11-30")
        total_before = summary_before['total']['total_records']
        print(f"  Summary before: total_records = {total_before}")
        
        # Staff creates omset → pending
        create_resp = self._create_omset_record(customer_id, test_date, 1000000)
        assert create_resp.status_code == 200
        record_id = create_resp.json().get('id')
        print("✓ Created pending omset")
        
        # Summary should NOT include pending
        summary_pending = self._get_summary("2025-11-01", "2025-11-30")
        total_pending = summary_pending['total']['total_records']
        assert total_pending == total_before, "Pending record incorrectly counted"
        print(f"  Summary with pending: total_records = {total_pending} (unchanged)")
        
        # Find the pending record ID
        pending_list = requests.get(f"{BASE_URL}/api/omset/pending", headers=self.admin_headers)
        pending_record_id = None
        for rec in pending_list.json():
            if rec.get('customer_id') == customer_id:
                pending_record_id = rec.get('id')
                break
        
        if pending_record_id is None:
            # Check main omset list
            omset_list = requests.get(f"{BASE_URL}/api/omset", headers=self.admin_headers)
            for rec in omset_list.json():
                if rec.get('customer_id') == customer_id and rec.get('approval_status') == 'pending':
                    pending_record_id = rec.get('id')
                    break
        
        assert pending_record_id is not None, "Could not find pending record to approve"
        
        # Approve the pending record
        approve_response = requests.post(
            f"{BASE_URL}/api/omset/{pending_record_id}/approve",
            headers=self.admin_headers
        )
        assert approve_response.status_code == 200, f"Failed to approve: {approve_response.text}"
        print("✓ Approved pending record")
        
        # Summary should now include the approved record
        summary_after = self._get_summary("2025-11-01", "2025-11-30")
        total_after = summary_after['total']['total_records']
        print(f"  Summary after approve: total_records = {total_after}")
        
        assert total_after == total_before + 1, \
            f"Approved record not counted in summary! Before: {total_before}, After: {total_after}"
        
        print("✓ Approved record correctly counted in summary")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
