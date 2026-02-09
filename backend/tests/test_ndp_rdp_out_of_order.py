"""
Test NDP/RDP Out-of-Order Entry Bug Fix

Critical Bug: NDP/RDP customer_type is incorrectly assigned when omset records 
are entered out of chronological order.

Example: customer 'syahmara' shows as NDP on both Feb 7 and Feb 9 when entered 
out of order. NDP should only appear once (first deposit date), all subsequent 
should be RDP.

The fix adds recalculate_customer_type() call after each new omset record insertion.

Test Credentials:
- Admin: admin@crm.com / admin123
- Staff: staff@crm.com / staff123
- Product: prod-istana2000
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestNDPRDPOutOfOrderBugFix:
    """Test suite for NDP/RDP out-of-order entry bug fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """Setup: Login as staff and get auth token"""
        # Login as staff
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "staff@crm.com", "password": "staff123"}
        )
        assert login_response.status_code == 200, f"Staff login failed: {login_response.text}"
        self.staff_token = login_response.json()["token"]
        self.staff_headers = {"Authorization": f"Bearer {self.staff_token}"}
        
        # Login as admin
        admin_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@crm.com", "password": "admin123"}
        )
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        self.admin_token = admin_login.json()["token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Generate unique test prefix
        self.test_prefix = f"OUTOFORDER_{uuid.uuid4().hex[:8]}"
        self.created_record_ids = []
        self.product_id = "prod-istana2000"
        
        print(f"\n✓ Auth tokens obtained, test prefix: {self.test_prefix}")
        
        # Cleanup after test
        def cleanup():
            for record_id in self.created_record_ids:
                try:
                    requests.delete(
                        f"{BASE_URL}/api/omset/{record_id}",
                        headers=self.admin_headers
                    )
                except:
                    pass
        
        request.addfinalizer(cleanup)
    
    def create_omset_record(self, customer_name, record_date, nominal=100000):
        """Helper to create an omset record"""
        payload = {
            "product_id": self.product_id,
            "record_date": record_date,
            "customer_name": customer_name,
            "customer_id": customer_name,  # Use same as name for simplicity
            "nominal": nominal,
            "depo_kelipatan": 1,
            "keterangan": ""
        }
        response = requests.post(
            f"{BASE_URL}/api/omset",
            json=payload,
            headers=self.staff_headers
        )
        return response
    
    def get_omset_records(self, customer_id=None):
        """Helper to get omset records"""
        response = requests.get(
            f"{BASE_URL}/api/omset",
            headers=self.admin_headers
        )
        if response.status_code != 200:
            return []
        records = response.json()
        if customer_id:
            records = [r for r in records if r.get('customer_id') == customer_id]
        return records
    
    # ==================== CORE BUG FIX TESTS ====================
    
    def test_01_out_of_order_entry_later_date_first(self):
        """
        CRITICAL: Creating records out of order (later date first) should result 
        in correct NDP/RDP: earlier date = NDP, later date = RDP
        
        Scenario:
        1. Create Feb 9 record first
        2. Create Feb 7 record second
        3. Feb 7 should be NDP (first deposit), Feb 9 should be RDP
        """
        customer_name = f"{self.test_prefix}_syahmara"
        date_later = "2025-02-09"
        date_earlier = "2025-02-07"
        
        # Step 1: Create Feb 9 record FIRST (out of order)
        response_later = self.create_omset_record(customer_name, date_later)
        assert response_later.status_code == 200, f"Failed to create later record: {response_later.text}"
        record_later = response_later.json()
        self.created_record_ids.append(record_later['id'])
        print(f"✓ Created Feb 9 record first: {record_later['id']}")
        
        # At this point, Feb 9 should be NDP (it's the only record)
        initial_type = record_later.get('customer_type')
        print(f"  Initial Feb 9 customer_type (before Feb 7): {initial_type}")
        
        # Step 2: Create Feb 7 record SECOND (earlier date)
        response_earlier = self.create_omset_record(customer_name, date_earlier)
        assert response_earlier.status_code == 200, f"Failed to create earlier record: {response_earlier.text}"
        record_earlier = response_earlier.json()
        self.created_record_ids.append(record_earlier['id'])
        print(f"✓ Created Feb 7 record second: {record_earlier['id']}")
        
        # Step 3: Verify NDP/RDP via GET /api/omset
        records = self.get_omset_records(customer_name)
        assert len(records) >= 2, f"Expected at least 2 records, got {len(records)}"
        
        # Find our test records
        feb7_record = next((r for r in records if r['record_date'] == date_earlier), None)
        feb9_record = next((r for r in records if r['record_date'] == date_later), None)
        
        assert feb7_record is not None, "Feb 7 record not found"
        assert feb9_record is not None, "Feb 9 record not found"
        
        feb7_type = feb7_record.get('customer_type')
        feb9_type = feb9_record.get('customer_type')
        
        print(f"\n=== VERIFICATION ===")
        print(f"Feb 7 customer_type: {feb7_type} (expected: NDP)")
        print(f"Feb 9 customer_type: {feb9_type} (expected: RDP)")
        
        # CRITICAL ASSERTIONS
        assert feb7_type == 'NDP', f"Feb 7 should be NDP (first deposit), got: {feb7_type}"
        assert feb9_type == 'RDP', f"Feb 9 should be RDP (redepo), got: {feb9_type}"
        
        print("✓ PASSED: Out-of-order entry correctly assigns NDP to earliest date")
    
    def test_02_in_order_entry_works_correctly(self):
        """
        Creating records in chronological order should still work correctly:
        first record NDP, second RDP
        """
        customer_name = f"{self.test_prefix}_inorder"
        date_first = "2025-03-01"
        date_second = "2025-03-05"
        
        # Create in chronological order
        response1 = self.create_omset_record(customer_name, date_first)
        assert response1.status_code == 200
        record1 = response1.json()
        self.created_record_ids.append(record1['id'])
        
        response2 = self.create_omset_record(customer_name, date_second)
        assert response2.status_code == 200
        record2 = response2.json()
        self.created_record_ids.append(record2['id'])
        
        # Verify via GET
        records = self.get_omset_records(customer_name)
        mar1_record = next((r for r in records if r['record_date'] == date_first), None)
        mar5_record = next((r for r in records if r['record_date'] == date_second), None)
        
        assert mar1_record is not None
        assert mar5_record is not None
        
        print(f"Mar 1 customer_type: {mar1_record.get('customer_type')}")
        print(f"Mar 5 customer_type: {mar5_record.get('customer_type')}")
        
        assert mar1_record.get('customer_type') == 'NDP', "First record should be NDP"
        assert mar5_record.get('customer_type') == 'RDP', "Second record should be RDP"
        
        print("✓ PASSED: In-order entry correctly assigns NDP/RDP")
    
    def test_03_multiple_out_of_order_entries(self):
        """
        Test multiple out-of-order entries:
        Create: Mar 15, Mar 5, Mar 10, Mar 1
        Expected: Mar 1=NDP, rest=RDP
        """
        customer_name = f"{self.test_prefix}_multi"
        dates = ["2025-03-15", "2025-03-05", "2025-03-10", "2025-03-01"]
        
        # Create in given (non-chronological) order
        for date in dates:
            response = self.create_omset_record(customer_name, date)
            assert response.status_code == 200, f"Failed to create record for {date}"
            self.created_record_ids.append(response.json()['id'])
        
        # Verify
        records = self.get_omset_records(customer_name)
        
        for r in records:
            expected_type = 'NDP' if r['record_date'] == "2025-03-01" else 'RDP'
            actual_type = r.get('customer_type')
            print(f"{r['record_date']}: {actual_type} (expected: {expected_type})")
            assert actual_type == expected_type, \
                f"Date {r['record_date']} should be {expected_type}, got {actual_type}"
        
        print("✓ PASSED: Multiple out-of-order entries correctly handled")
    
    def test_04_tambahan_record_is_always_rdp(self):
        """
        Records with 'tambahan' in keterangan should always be RDP,
        even if it's the first record for a customer
        """
        customer_name = f"{self.test_prefix}_tambahan"
        date = "2025-04-01"
        
        # Create record with "tambahan" in notes
        payload = {
            "product_id": self.product_id,
            "record_date": date,
            "customer_name": customer_name,
            "customer_id": customer_name,
            "nominal": 100000,
            "depo_kelipatan": 1,
            "keterangan": "depo tambahan"  # Contains "tambahan"
        }
        response = requests.post(
            f"{BASE_URL}/api/omset",
            json=payload,
            headers=self.staff_headers
        )
        assert response.status_code == 200
        self.created_record_ids.append(response.json()['id'])
        
        # Verify via GET
        records = self.get_omset_records(customer_name)
        tambahan_record = next((r for r in records if r['customer_id'] == customer_name), None)
        
        assert tambahan_record is not None
        customer_type = tambahan_record.get('customer_type')
        print(f"Tambahan record customer_type: {customer_type}")
        
        assert customer_type == 'RDP', f"Tambahan record should always be RDP, got: {customer_type}"
        print("✓ PASSED: Tambahan records are always RDP")
    
    # ==================== MIGRATE/RECALCULATE ENDPOINT TEST ====================
    
    def test_05_migrate_normalize_endpoint(self):
        """
        Test POST /api/omset/migrate-normalize recalculates all existing records correctly
        """
        response = requests.post(
            f"{BASE_URL}/api/omset/migrate-normalize",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Migrate failed: {response.text}"
        data = response.json()
        
        assert 'message' in data, "Missing 'message' in response"
        assert 'updated_count' in data, "Missing 'updated_count' in response"
        
        print(f"✓ Migrate endpoint response:")
        print(f"  Message: {data.get('message')}")
        print(f"  Updated count: {data.get('updated_count')}")
        print(f"  Total records: {data.get('total_records')}")
        
        print("✓ PASSED: migrate-normalize endpoint works correctly")
    
    # ==================== GET OMSET VERIFICATION ====================
    
    def test_06_get_omset_returns_customer_type(self):
        """
        Verify GET /api/omset returns customer_type field for all records
        """
        response = requests.get(
            f"{BASE_URL}/api/omset",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"GET omset failed: {response.text}"
        
        records = response.json()
        assert isinstance(records, list), "Expected list response"
        
        if records:
            # Check first few records have customer_type
            for i, record in enumerate(records[:5]):
                customer_type = record.get('customer_type')
                assert customer_type in ['NDP', 'RDP', None], \
                    f"Invalid customer_type: {customer_type}"
                print(f"Record {i+1}: {record.get('customer_id')} - {customer_type}")
        
        print("✓ PASSED: GET /api/omset returns customer_type field")
    
    def test_07_verify_no_duplicate_ndp_for_same_customer(self):
        """
        After fix, same customer should have only ONE NDP record per (staff, product) combo
        """
        customer_name = f"{self.test_prefix}_nodup"
        dates = ["2025-05-10", "2025-05-05", "2025-05-15"]  # Out of order
        
        for date in dates:
            response = self.create_omset_record(customer_name, date)
            assert response.status_code == 200
            self.created_record_ids.append(response.json()['id'])
        
        records = self.get_omset_records(customer_name)
        ndp_count = sum(1 for r in records if r.get('customer_type') == 'NDP')
        
        print(f"Records for {customer_name}:")
        for r in records:
            print(f"  {r['record_date']}: {r.get('customer_type')}")
        
        assert ndp_count == 1, f"Expected exactly 1 NDP record, got {ndp_count}"
        
        # Verify the NDP is the earliest date
        ndp_record = next(r for r in records if r.get('customer_type') == 'NDP')
        assert ndp_record['record_date'] == "2025-05-05", \
            f"NDP should be earliest date (2025-05-05), got {ndp_record['record_date']}"
        
        print("✓ PASSED: Only one NDP per customer, and it's the earliest date")


class TestRecalculateFunction:
    """Test the recalculate_customer_type function behavior"""
    
    @pytest.fixture(autouse=True)
    def setup(self, request):
        """Setup"""
        admin_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@crm.com", "password": "admin123"}
        )
        assert admin_login.status_code == 200
        self.admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}
        
        staff_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "staff@crm.com", "password": "staff123"}
        )
        assert staff_login.status_code == 200
        self.staff_headers = {"Authorization": f"Bearer {staff_login.json()['token']}"}
        
        self.test_prefix = f"RECALC_{uuid.uuid4().hex[:8]}"
        self.created_ids = []
        self.product_id = "prod-istana2000"
        
        def cleanup():
            for rid in self.created_ids:
                try:
                    requests.delete(f"{BASE_URL}/api/omset/{rid}", headers=self.admin_headers)
                except:
                    pass
        request.addfinalizer(cleanup)
    
    def test_08_delete_ndp_promotes_next_to_ndp(self):
        """
        When NDP record is deleted, the next oldest record should become NDP
        """
        customer_name = f"{self.test_prefix}_delete"
        
        # Create two records in order
        r1 = requests.post(
            f"{BASE_URL}/api/omset",
            json={
                "product_id": self.product_id,
                "record_date": "2025-06-01",
                "customer_name": customer_name,
                "customer_id": customer_name,
                "nominal": 100000,
                "depo_kelipatan": 1,
                "keterangan": ""
            },
            headers=self.staff_headers
        )
        assert r1.status_code == 200
        id1 = r1.json()['id']
        self.created_ids.append(id1)
        
        r2 = requests.post(
            f"{BASE_URL}/api/omset",
            json={
                "product_id": self.product_id,
                "record_date": "2025-06-05",
                "customer_name": customer_name,
                "customer_id": customer_name,
                "nominal": 100000,
                "depo_kelipatan": 1,
                "keterangan": ""
            },
            headers=self.staff_headers
        )
        assert r2.status_code == 200
        id2 = r2.json()['id']
        self.created_ids.append(id2)
        
        # Delete the first (NDP) record
        delete_resp = requests.delete(
            f"{BASE_URL}/api/omset/{id1}",
            headers=self.admin_headers
        )
        assert delete_resp.status_code == 200
        self.created_ids.remove(id1)  # Already deleted
        
        # Verify second record is now NDP
        get_resp = requests.get(f"{BASE_URL}/api/omset", headers=self.admin_headers)
        records = [r for r in get_resp.json() if r['customer_id'] == customer_name]
        
        if records:
            remaining = records[0]
            print(f"After delete - remaining record type: {remaining.get('customer_type')}")
            assert remaining.get('customer_type') == 'NDP', "After deleting NDP, next record should become NDP"
        
        print("✓ PASSED: Delete NDP promotes next record to NDP")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
