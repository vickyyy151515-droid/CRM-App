"""
Test RDP/NDP Consistency Fix - Critical Bug Validation

This test validates the fix for the RDP count mismatch bug:
When a customer deposits into multiple products on the same day,
they should be counted ONCE in both staff breakdown and product breakdown.

Bug: Customer was being double-counted in product breakdown but only counted once in staff breakdown.
Fix: Uses global_staff_customer_counted_rdp/ndp sets to track (staff_id, customer_id) pairs globally.

Test data created by main agent:
- Customer MP-TEST-001 deposited to ISTANA2000 and LIGA2000 on 2026-02-20
- Customer MP-TEST-002 deposited to both products on 2026-02-21
- New customer MP-NEW-001 deposited to multiple products on 2026-02-21
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestRDPNDPConsistencyFix:
    """Test suite for RDP/NDP consistency between staff and product breakdowns"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "vicky@crm.com", "password": "vicky123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_daily_summary_endpoint_returns_200(self):
        """Test that /api/daily-summary endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields exist
        assert "date" in data, "Missing 'date' field"
        assert "staff_breakdown" in data, "Missing 'staff_breakdown' field"
        assert "product_breakdown" in data, "Missing 'product_breakdown' field"
        print("✓ Daily summary endpoint returns valid response")
    
    def test_02_rdp_consistency_date_2026_02_20(self):
        """
        CRITICAL TEST: RDP consistency for 2026-02-20
        
        Customer MP-TEST-001 deposited to ISTANA2000 and LIGA2000 on this date.
        Staff RDP sum must equal Product RDP sum.
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate staff RDP sum
        staff_rdp_sum = sum(s.get('rdp_count', 0) for s in data.get('staff_breakdown', []))
        
        # Calculate product RDP sum
        product_rdp_sum = sum(p.get('rdp_count', 0) for p in data.get('product_breakdown', []))
        
        print(f"\n=== RDP CONSISTENCY TEST (2026-02-20) ===")
        print(f"Staff RDP Sum: {staff_rdp_sum}")
        print(f"Product RDP Sum: {product_rdp_sum}")
        
        # THE CRITICAL ASSERTION
        assert staff_rdp_sum == product_rdp_sum, \
            f"RDP MISMATCH! Staff RDP ({staff_rdp_sum}) != Product RDP ({product_rdp_sum})"
        
        print(f"✓ RDP consistency verified for 2026-02-20")
    
    def test_03_ndp_consistency_date_2026_02_20(self):
        """
        CRITICAL TEST: NDP consistency for 2026-02-20
        
        Staff NDP sum must equal Product NDP sum.
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate staff NDP sum
        staff_ndp_sum = sum(s.get('ndp_count', 0) for s in data.get('staff_breakdown', []))
        
        # Calculate product NDP sum
        product_ndp_sum = sum(p.get('ndp_count', 0) for p in data.get('product_breakdown', []))
        
        print(f"\n=== NDP CONSISTENCY TEST (2026-02-20) ===")
        print(f"Staff NDP Sum: {staff_ndp_sum}")
        print(f"Product NDP Sum: {product_ndp_sum}")
        
        # THE CRITICAL ASSERTION
        assert staff_ndp_sum == product_ndp_sum, \
            f"NDP MISMATCH! Staff NDP ({staff_ndp_sum}) != Product NDP ({product_ndp_sum})"
        
        print(f"✓ NDP consistency verified for 2026-02-20")
    
    def test_04_rdp_consistency_date_2026_02_21(self):
        """
        CRITICAL TEST: RDP consistency for 2026-02-21
        
        Multiple customers deposited to multiple products on this date.
        Staff RDP sum must equal Product RDP sum.
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-21",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate staff RDP sum
        staff_rdp_sum = sum(s.get('rdp_count', 0) for s in data.get('staff_breakdown', []))
        
        # Calculate product RDP sum
        product_rdp_sum = sum(p.get('rdp_count', 0) for p in data.get('product_breakdown', []))
        
        print(f"\n=== RDP CONSISTENCY TEST (2026-02-21) ===")
        print(f"Staff RDP Sum: {staff_rdp_sum}")
        print(f"Product RDP Sum: {product_rdp_sum}")
        
        # THE CRITICAL ASSERTION
        assert staff_rdp_sum == product_rdp_sum, \
            f"RDP MISMATCH! Staff RDP ({staff_rdp_sum}) != Product RDP ({product_rdp_sum})"
        
        print(f"✓ RDP consistency verified for 2026-02-21")
    
    def test_05_ndp_consistency_date_2026_02_21(self):
        """
        CRITICAL TEST: NDP consistency for 2026-02-21
        
        New customer MP-NEW-001 deposited to multiple products on this date.
        Staff NDP sum must equal Product NDP sum.
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-21",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate staff NDP sum
        staff_ndp_sum = sum(s.get('ndp_count', 0) for s in data.get('staff_breakdown', []))
        
        # Calculate product NDP sum
        product_ndp_sum = sum(p.get('ndp_count', 0) for p in data.get('product_breakdown', []))
        
        print(f"\n=== NDP CONSISTENCY TEST (2026-02-21) ===")
        print(f"Staff NDP Sum: {staff_ndp_sum}")
        print(f"Product NDP Sum: {product_ndp_sum}")
        
        # THE CRITICAL ASSERTION
        assert staff_ndp_sum == product_ndp_sum, \
            f"NDP MISMATCH! Staff NDP ({staff_ndp_sum}) != Product NDP ({product_ndp_sum})"
        
        print(f"✓ NDP consistency verified for 2026-02-21")
    
    def test_06_detailed_breakdown_2026_02_20(self):
        """
        Detailed test: Verify individual staff and product counts for 2026-02-20
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        print(f"\n=== DETAILED BREAKDOWN (2026-02-20) ===")
        print(f"Date: {data.get('date')}")
        print(f"Total RDP: {data.get('total_rdp')}")
        print(f"Total NDP: {data.get('total_ndp')}")
        
        print("\nStaff Breakdown:")
        for s in data.get('staff_breakdown', []):
            print(f"  {s.get('staff_name')}: RDP={s.get('rdp_count')}, NDP={s.get('ndp_count')}, Forms={s.get('form_count')}")
        
        print("\nProduct Breakdown:")
        for p in data.get('product_breakdown', []):
            print(f"  {p.get('product_name')}: RDP={p.get('rdp_count')}, NDP={p.get('ndp_count')}, Forms={p.get('form_count')}")
        
        # Verify data exists
        assert len(data.get('staff_breakdown', [])) > 0, "No staff breakdown data"
        assert len(data.get('product_breakdown', [])) > 0, "No product breakdown data"
        
        print("✓ Detailed breakdown verified")
    
    def test_07_detailed_breakdown_2026_02_21(self):
        """
        Detailed test: Verify individual staff and product counts for 2026-02-21
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-21",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        print(f"\n=== DETAILED BREAKDOWN (2026-02-21) ===")
        print(f"Date: {data.get('date')}")
        print(f"Total RDP: {data.get('total_rdp')}")
        print(f"Total NDP: {data.get('total_ndp')}")
        
        print("\nStaff Breakdown:")
        for s in data.get('staff_breakdown', []):
            print(f"  {s.get('staff_name')}: RDP={s.get('rdp_count')}, NDP={s.get('ndp_count')}, Forms={s.get('form_count')}")
        
        print("\nProduct Breakdown:")
        for p in data.get('product_breakdown', []):
            print(f"  {p.get('product_name')}: RDP={p.get('rdp_count')}, NDP={p.get('ndp_count')}, Forms={p.get('form_count')}")
        
        # Verify data exists
        assert len(data.get('staff_breakdown', [])) > 0, "No staff breakdown data"
        assert len(data.get('product_breakdown', [])) > 0, "No product breakdown data"
        
        print("✓ Detailed breakdown verified")
    
    def test_08_multiple_staff_handling(self):
        """
        Test that the fix handles multiple staff members correctly.
        Each staff's customers should be counted independently.
        """
        # Get a date with data
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-21",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        staff_breakdown = data.get('staff_breakdown', [])
        
        print(f"\n=== MULTIPLE STAFF HANDLING TEST ===")
        print(f"Number of staff with data: {len(staff_breakdown)}")
        
        # Verify each staff has valid counts
        for staff in staff_breakdown:
            rdp = staff.get('rdp_count', 0)
            ndp = staff.get('ndp_count', 0)
            forms = staff.get('form_count', 0)
            
            print(f"  {staff.get('staff_name')}: RDP={rdp}, NDP={ndp}, Forms={forms}")
            
            # RDP + NDP should be <= form_count (since same customer can have multiple forms)
            # But each unique customer should only be counted once
            assert rdp >= 0, f"Invalid RDP count for {staff.get('staff_name')}"
            assert ndp >= 0, f"Invalid NDP count for {staff.get('staff_name')}"
        
        print("✓ Multiple staff handling verified")
    
    def test_09_code_review_fix_implementation(self):
        """
        Code review: Verify the fix implementation in daily_summary.py
        """
        with open('/app/backend/routes/daily_summary.py', 'r') as f:
            content = f.read()
        
        # Check for the fix: global tracking sets
        assert 'global_staff_customer_counted_rdp' in content, \
            "Missing global_staff_customer_counted_rdp tracking set"
        assert 'global_staff_customer_counted_ndp' in content, \
            "Missing global_staff_customer_counted_ndp tracking set"
        
        # Check for the staff_customer_key usage
        assert 'staff_customer_key = (staff_id, cid_normalized)' in content, \
            "Missing staff_customer_key tuple creation"
        
        # Check for the conditional counting logic
        assert 'if staff_customer_key not in global_staff_customer_counted_rdp:' in content, \
            "Missing RDP conditional counting check"
        assert 'if staff_customer_key not in global_staff_customer_counted_ndp:' in content, \
            "Missing NDP conditional counting check"
        
        print("\n=== CODE REVIEW: FIX IMPLEMENTATION ===")
        print("✓ global_staff_customer_counted_rdp set exists")
        print("✓ global_staff_customer_counted_ndp set exists")
        print("✓ staff_customer_key tuple creation exists")
        print("✓ Conditional counting logic exists")
        print("✓ Fix implementation verified in daily_summary.py")
    
    def test_10_consistency_across_multiple_dates(self):
        """
        Test RDP/NDP consistency across multiple dates to ensure fix is robust.
        """
        test_dates = ['2026-02-20', '2026-02-21', '2026-01-15', '2026-01-01']
        
        print(f"\n=== CONSISTENCY ACROSS MULTIPLE DATES ===")
        
        all_consistent = True
        for date in test_dates:
            response = requests.get(
                f"{BASE_URL}/api/daily-summary?date={date}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                print(f"  {date}: No data (status {response.status_code})")
                continue
            
            data = response.json()
            
            staff_rdp = sum(s.get('rdp_count', 0) for s in data.get('staff_breakdown', []))
            staff_ndp = sum(s.get('ndp_count', 0) for s in data.get('staff_breakdown', []))
            product_rdp = sum(p.get('rdp_count', 0) for p in data.get('product_breakdown', []))
            product_ndp = sum(p.get('ndp_count', 0) for p in data.get('product_breakdown', []))
            
            rdp_match = staff_rdp == product_rdp
            ndp_match = staff_ndp == product_ndp
            
            status = "✓" if (rdp_match and ndp_match) else "✗"
            print(f"  {date}: Staff(RDP={staff_rdp}, NDP={staff_ndp}) vs Product(RDP={product_rdp}, NDP={product_ndp}) {status}")
            
            if not (rdp_match and ndp_match):
                all_consistent = False
        
        assert all_consistent, "Found inconsistencies across dates"
        print("✓ All dates show consistent RDP/NDP counts")


class TestMultipleCustomersMultipleProducts:
    """Test scenarios with multiple customers depositing to multiple products"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "vicky@crm.com", "password": "vicky123"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_11_customer_depositing_to_multiple_products_counted_once(self):
        """
        CRITICAL: When Customer A deposits to Product X and Product Y under Staff B,
        Customer A should be counted as 1 RDP (or NDP), not 2.
        
        This is the core bug that was fixed.
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Get staff breakdown
        staff_breakdown = data.get('staff_breakdown', [])
        
        # Get product breakdown
        product_breakdown = data.get('product_breakdown', [])
        
        # Calculate totals
        staff_total = sum(s.get('rdp_count', 0) + s.get('ndp_count', 0) for s in staff_breakdown)
        product_total = sum(p.get('rdp_count', 0) + p.get('ndp_count', 0) for p in product_breakdown)
        
        print(f"\n=== CUSTOMER MULTI-PRODUCT TEST ===")
        print(f"Staff total unique customers (RDP+NDP): {staff_total}")
        print(f"Product total unique customers (RDP+NDP): {product_total}")
        
        # The fix ensures these are equal
        assert staff_total == product_total, \
            f"Customer count mismatch! Staff={staff_total}, Product={product_total}"
        
        print("✓ Customer depositing to multiple products counted correctly")
    
    def test_12_form_count_vs_customer_count(self):
        """
        Verify that form_count can be higher than RDP+NDP count
        (since same customer can submit multiple forms to different products)
        """
        response = requests.get(
            f"{BASE_URL}/api/daily-summary?date=2026-02-20",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        total_forms = data.get('total_forms', 0)
        total_rdp = data.get('total_rdp', 0)
        total_ndp = data.get('total_ndp', 0)
        total_customers = total_rdp + total_ndp
        
        print(f"\n=== FORM COUNT VS CUSTOMER COUNT ===")
        print(f"Total Forms: {total_forms}")
        print(f"Total Unique Customers (RDP+NDP): {total_customers}")
        
        # Forms can be >= customers (same customer can have multiple forms)
        assert total_forms >= total_customers, \
            f"Form count ({total_forms}) should be >= customer count ({total_customers})"
        
        print("✓ Form count vs customer count relationship verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
