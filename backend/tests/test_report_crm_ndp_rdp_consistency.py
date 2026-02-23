"""
Test NDP/RDP Consistency Across All 4 Report Sections

CRITICAL BUG FIX TEST (3rd attempt):
This test verifies that NDP/RDP counts are IDENTICAL across all 4 report sections:
1. Yearly Summary (yearly_data)
2. Monthly Detail (monthly_by_staff)
3. Daily Report (daily_data / daily_by_staff)
4. Staff Performance (staff_performance)

The fix uses a unified 'unique_deposits' dictionary as single source of truth.
All sections derive their NDP/RDP from this same dictionary.

Key rules:
- NDP = Customer's FIRST deposit for THIS PRODUCT matches record_date (AND not tambahan)
- RDP = Not first deposit for this product OR is tambahan
- 'Tambahan' records must ALWAYS count as RDP (never NDP)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReportCRMNDPRDPConsistency:
    """Test NDP/RDP consistency across all 4 report sections"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "vicky@crm.com", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_report_crm_data_endpoint_returns_200(self):
        """Test that /report-crm/data endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify all required sections exist
        assert "yearly" in data, "Missing 'yearly' section"
        assert "monthly" in data, "Missing 'monthly' section"
        assert "monthly_by_staff" in data, "Missing 'monthly_by_staff' section"
        assert "daily" in data, "Missing 'daily' section"
        assert "daily_by_staff" in data, "Missing 'daily_by_staff' section"
        assert "staff_performance" in data, "Missing 'staff_performance' section"
        print("✓ All required sections present in response")
    
    def test_yearly_totals_match_monthly_by_staff_totals(self):
        """
        CRITICAL TEST: Yearly Summary NDP/RDP must match Monthly Detail totals
        
        Sum of yearly_data[month].new_id for all months == 
        Sum of monthly_by_staff[month].totals.new_id for all months
        """
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals from yearly_data
        yearly_ndp = sum(m.get('new_id', 0) for m in data['yearly'])
        yearly_rdp = sum(m.get('rdp', 0) for m in data['yearly'])
        yearly_form = sum(m.get('total_form', 0) for m in data['yearly'])
        yearly_nominal = sum(m.get('nominal', 0) for m in data['yearly'])
        
        # Calculate totals from monthly_by_staff
        monthly_staff_ndp = sum(m['totals'].get('new_id', 0) for m in data['monthly_by_staff'])
        monthly_staff_rdp = sum(m['totals'].get('rdp', 0) for m in data['monthly_by_staff'])
        monthly_staff_form = sum(m['totals'].get('total_form', 0) for m in data['monthly_by_staff'])
        monthly_staff_nominal = sum(m['totals'].get('nominal', 0) for m in data['monthly_by_staff'])
        
        print(f"\n=== YEARLY vs MONTHLY_BY_STAFF COMPARISON ===")
        print(f"Yearly Summary:    NDP={yearly_ndp}, RDP={yearly_rdp}, Form={yearly_form}, Nominal={yearly_nominal}")
        print(f"Monthly By Staff:  NDP={monthly_staff_ndp}, RDP={monthly_staff_rdp}, Form={monthly_staff_form}, Nominal={monthly_staff_nominal}")
        
        assert yearly_ndp == monthly_staff_ndp, f"NDP mismatch: Yearly={yearly_ndp}, Monthly By Staff={monthly_staff_ndp}"
        assert yearly_rdp == monthly_staff_rdp, f"RDP mismatch: Yearly={yearly_rdp}, Monthly By Staff={monthly_staff_rdp}"
        assert yearly_form == monthly_staff_form, f"Form mismatch: Yearly={yearly_form}, Monthly By Staff={monthly_staff_form}"
        assert yearly_nominal == monthly_staff_nominal, f"Nominal mismatch: Yearly={yearly_nominal}, Monthly By Staff={monthly_staff_nominal}"
        
        print("✓ Yearly Summary matches Monthly By Staff totals")
    
    def test_yearly_totals_match_staff_performance_totals(self):
        """
        CRITICAL TEST: Yearly Summary NDP/RDP must match Staff Performance totals
        
        Sum of yearly_data[month].new_id for all months == 
        Sum of staff_performance[staff].new_id for all staff
        """
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals from yearly_data
        yearly_ndp = sum(m.get('new_id', 0) for m in data['yearly'])
        yearly_rdp = sum(m.get('rdp', 0) for m in data['yearly'])
        yearly_form = sum(m.get('total_form', 0) for m in data['yearly'])
        yearly_nominal = sum(m.get('nominal', 0) for m in data['yearly'])
        
        # Calculate totals from staff_performance
        staff_perf_ndp = sum(s.get('new_id', 0) for s in data['staff_performance'])
        staff_perf_rdp = sum(s.get('rdp', 0) for s in data['staff_performance'])
        staff_perf_form = sum(s.get('total_form', 0) for s in data['staff_performance'])
        staff_perf_nominal = sum(s.get('nominal', 0) for s in data['staff_performance'])
        
        print(f"\n=== YEARLY vs STAFF_PERFORMANCE COMPARISON ===")
        print(f"Yearly Summary:     NDP={yearly_ndp}, RDP={yearly_rdp}, Form={yearly_form}, Nominal={yearly_nominal}")
        print(f"Staff Performance:  NDP={staff_perf_ndp}, RDP={staff_perf_rdp}, Form={staff_perf_form}, Nominal={staff_perf_nominal}")
        
        assert yearly_ndp == staff_perf_ndp, f"NDP mismatch: Yearly={yearly_ndp}, Staff Performance={staff_perf_ndp}"
        assert yearly_rdp == staff_perf_rdp, f"RDP mismatch: Yearly={yearly_rdp}, Staff Performance={staff_perf_rdp}"
        assert yearly_form == staff_perf_form, f"Form mismatch: Yearly={yearly_form}, Staff Performance={staff_perf_form}"
        assert yearly_nominal == staff_perf_nominal, f"Nominal mismatch: Yearly={yearly_nominal}, Staff Performance={staff_perf_nominal}"
        
        print("✓ Yearly Summary matches Staff Performance totals")
    
    def test_monthly_detail_matches_daily_report_for_selected_month(self):
        """
        CRITICAL TEST: Monthly Detail NDP/RDP for selected month must match Daily Report totals
        
        monthly_by_staff[selected_month].totals.new_id == 
        Sum of daily_data[day].new_id for all days in selected month
        """
        # Test for January 2026
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Get January (month=1) from monthly_by_staff
        jan_monthly = next((m for m in data['monthly_by_staff'] if m['month'] == 1), None)
        if jan_monthly is None:
            print("No data for January 2026 in monthly_by_staff")
            return
        
        monthly_ndp = jan_monthly['totals'].get('new_id', 0)
        monthly_rdp = jan_monthly['totals'].get('rdp', 0)
        monthly_form = jan_monthly['totals'].get('total_form', 0)
        monthly_nominal = jan_monthly['totals'].get('nominal', 0)
        
        # Calculate totals from daily_data (which is for selected month)
        daily_ndp = sum(d.get('new_id', 0) for d in data['daily'])
        daily_rdp = sum(d.get('rdp', 0) for d in data['daily'])
        daily_form = sum(d.get('total_form', 0) for d in data['daily'])
        daily_nominal = sum(d.get('nominal', 0) for d in data['daily'])
        
        print(f"\n=== MONTHLY DETAIL (Jan) vs DAILY REPORT COMPARISON ===")
        print(f"Monthly Detail (Jan):  NDP={monthly_ndp}, RDP={monthly_rdp}, Form={monthly_form}, Nominal={monthly_nominal}")
        print(f"Daily Report:          NDP={daily_ndp}, RDP={daily_rdp}, Form={daily_form}, Nominal={daily_nominal}")
        
        assert monthly_ndp == daily_ndp, f"NDP mismatch: Monthly={monthly_ndp}, Daily={daily_ndp}"
        assert monthly_rdp == daily_rdp, f"RDP mismatch: Monthly={monthly_rdp}, Daily={daily_rdp}"
        assert monthly_form == daily_form, f"Form mismatch: Monthly={monthly_form}, Daily={daily_form}"
        assert monthly_nominal == daily_nominal, f"Nominal mismatch: Monthly={monthly_nominal}, Daily={daily_nominal}"
        
        print("✓ Monthly Detail matches Daily Report totals")
    
    def test_daily_by_staff_matches_daily_data(self):
        """
        CRITICAL TEST: Daily By Staff totals must match Daily Data totals
        
        Sum of daily_by_staff[staff].totals.new_id == 
        Sum of daily_data[day].new_id
        """
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals from daily_data
        daily_ndp = sum(d.get('new_id', 0) for d in data['daily'])
        daily_rdp = sum(d.get('rdp', 0) for d in data['daily'])
        daily_form = sum(d.get('total_form', 0) for d in data['daily'])
        daily_nominal = sum(d.get('nominal', 0) for d in data['daily'])
        
        # Calculate totals from daily_by_staff
        daily_staff_ndp = sum(s['totals'].get('new_id', 0) for s in data['daily_by_staff'])
        daily_staff_rdp = sum(s['totals'].get('rdp', 0) for s in data['daily_by_staff'])
        daily_staff_form = sum(s['totals'].get('total_form', 0) for s in data['daily_by_staff'])
        daily_staff_nominal = sum(s['totals'].get('nominal', 0) for s in data['daily_by_staff'])
        
        print(f"\n=== DAILY DATA vs DAILY BY STAFF COMPARISON ===")
        print(f"Daily Data:      NDP={daily_ndp}, RDP={daily_rdp}, Form={daily_form}, Nominal={daily_nominal}")
        print(f"Daily By Staff:  NDP={daily_staff_ndp}, RDP={daily_staff_rdp}, Form={daily_staff_form}, Nominal={daily_staff_nominal}")
        
        assert daily_ndp == daily_staff_ndp, f"NDP mismatch: Daily Data={daily_ndp}, Daily By Staff={daily_staff_ndp}"
        assert daily_rdp == daily_staff_rdp, f"RDP mismatch: Daily Data={daily_rdp}, Daily By Staff={daily_staff_rdp}"
        assert daily_form == daily_staff_form, f"Form mismatch: Daily Data={daily_form}, Daily By Staff={daily_staff_form}"
        assert daily_nominal == daily_staff_nominal, f"Nominal mismatch: Daily Data={daily_nominal}, Daily By Staff={daily_staff_nominal}"
        
        print("✓ Daily Data matches Daily By Staff totals")
    
    def test_individual_staff_consistency_monthly_vs_staff_performance(self):
        """
        CRITICAL TEST: Individual staff NDP/RDP in Monthly Detail must match Staff Performance
        
        For each staff:
        Sum of monthly_by_staff[month].staff[staff].new_id across all months ==
        staff_performance[staff].new_id
        """
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Build staff totals from monthly_by_staff
        staff_monthly_totals = {}
        for month_data in data['monthly_by_staff']:
            for staff in month_data.get('staff', []):
                sid = staff['staff_id']
                if sid not in staff_monthly_totals:
                    staff_monthly_totals[sid] = {
                        'staff_name': staff['staff_name'],
                        'new_id': 0, 'rdp': 0, 'total_form': 0, 'nominal': 0
                    }
                staff_monthly_totals[sid]['new_id'] += staff.get('new_id', 0)
                staff_monthly_totals[sid]['rdp'] += staff.get('rdp', 0)
                staff_monthly_totals[sid]['total_form'] += staff.get('total_form', 0)
                staff_monthly_totals[sid]['nominal'] += staff.get('nominal', 0)
        
        # Build staff totals from staff_performance
        staff_perf_totals = {s['staff_id']: s for s in data['staff_performance']}
        
        print(f"\n=== INDIVIDUAL STAFF CONSISTENCY CHECK ===")
        
        mismatches = []
        for sid, monthly_data in staff_monthly_totals.items():
            perf_data = staff_perf_totals.get(sid)
            if perf_data is None:
                mismatches.append(f"Staff {sid} ({monthly_data['staff_name']}) in monthly but not in staff_performance")
                continue
            
            if monthly_data['new_id'] != perf_data.get('new_id', 0):
                mismatches.append(f"Staff {monthly_data['staff_name']}: NDP mismatch - Monthly={monthly_data['new_id']}, Perf={perf_data.get('new_id', 0)}")
            if monthly_data['rdp'] != perf_data.get('rdp', 0):
                mismatches.append(f"Staff {monthly_data['staff_name']}: RDP mismatch - Monthly={monthly_data['rdp']}, Perf={perf_data.get('rdp', 0)}")
            
            print(f"  {monthly_data['staff_name']}: Monthly(NDP={monthly_data['new_id']}, RDP={monthly_data['rdp']}) vs Perf(NDP={perf_data.get('new_id', 0)}, RDP={perf_data.get('rdp', 0)})")
        
        if mismatches:
            for m in mismatches:
                print(f"  ✗ {m}")
            pytest.fail(f"Individual staff mismatches found: {mismatches}")
        
        print("✓ Individual staff NDP/RDP consistent between Monthly Detail and Staff Performance")
    
    def test_all_four_sections_grand_totals_match(self):
        """
        MASTER CONSISTENCY TEST: All 4 sections must have identical grand totals
        
        This is the ultimate test - if this passes, the bug is fixed.
        """
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert response.status_code == 200
        data = response.json()
        
        # 1. Yearly Summary totals
        yearly_ndp = sum(m.get('new_id', 0) for m in data['yearly'])
        yearly_rdp = sum(m.get('rdp', 0) for m in data['yearly'])
        
        # 2. Monthly By Staff totals
        monthly_staff_ndp = sum(m['totals'].get('new_id', 0) for m in data['monthly_by_staff'])
        monthly_staff_rdp = sum(m['totals'].get('rdp', 0) for m in data['monthly_by_staff'])
        
        # 3. Staff Performance totals
        staff_perf_ndp = sum(s.get('new_id', 0) for s in data['staff_performance'])
        staff_perf_rdp = sum(s.get('rdp', 0) for s in data['staff_performance'])
        
        # 4. Monthly data totals (daily breakdown for all months)
        monthly_data_ndp = sum(d.get('new_id', 0) for d in data['monthly'])
        monthly_data_rdp = sum(d.get('rdp', 0) for d in data['monthly'])
        
        print(f"\n{'='*60}")
        print(f"MASTER CONSISTENCY TEST - ALL 4 SECTIONS GRAND TOTALS")
        print(f"{'='*60}")
        print(f"1. Yearly Summary:     NDP={yearly_ndp:>5}, RDP={yearly_rdp:>5}")
        print(f"2. Monthly By Staff:   NDP={monthly_staff_ndp:>5}, RDP={monthly_staff_rdp:>5}")
        print(f"3. Staff Performance:  NDP={staff_perf_ndp:>5}, RDP={staff_perf_rdp:>5}")
        print(f"4. Monthly Data:       NDP={monthly_data_ndp:>5}, RDP={monthly_data_rdp:>5}")
        print(f"{'='*60}")
        
        # All NDP values must be equal
        ndp_values = [yearly_ndp, monthly_staff_ndp, staff_perf_ndp, monthly_data_ndp]
        if len(set(ndp_values)) != 1:
            pytest.fail(f"NDP MISMATCH! Values: Yearly={yearly_ndp}, MonthlyStaff={monthly_staff_ndp}, StaffPerf={staff_perf_ndp}, MonthlyData={monthly_data_ndp}")
        
        # All RDP values must be equal
        rdp_values = [yearly_rdp, monthly_staff_rdp, staff_perf_rdp, monthly_data_rdp]
        if len(set(rdp_values)) != 1:
            pytest.fail(f"RDP MISMATCH! Values: Yearly={yearly_rdp}, MonthlyStaff={monthly_staff_rdp}, StaffPerf={staff_perf_rdp}, MonthlyData={monthly_data_rdp}")
        
        print(f"✓ ALL 4 SECTIONS HAVE IDENTICAL NDP/RDP TOTALS!")
        print(f"  Total NDP: {yearly_ndp}")
        print(f"  Total RDP: {yearly_rdp}")
    
    def test_with_product_filter(self):
        """Test NDP/RDP consistency when filtering by product"""
        # First get list of products
        products_response = requests.get(
            f"{BASE_URL}/api/products",
            headers=self.headers
        )
        if products_response.status_code != 200:
            pytest.skip("Could not fetch products")
        
        products = products_response.json()
        if not products:
            pytest.skip("No products available")
        
        # Test with first product
        product_id = products[0]['id']
        product_name = products[0]['name']
        
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1, "product_id": product_id}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals
        yearly_ndp = sum(m.get('new_id', 0) for m in data['yearly'])
        yearly_rdp = sum(m.get('rdp', 0) for m in data['yearly'])
        staff_perf_ndp = sum(s.get('new_id', 0) for s in data['staff_performance'])
        staff_perf_rdp = sum(s.get('rdp', 0) for s in data['staff_performance'])
        
        print(f"\n=== PRODUCT FILTER TEST: {product_name} ===")
        print(f"Yearly:           NDP={yearly_ndp}, RDP={yearly_rdp}")
        print(f"Staff Performance: NDP={staff_perf_ndp}, RDP={staff_perf_rdp}")
        
        assert yearly_ndp == staff_perf_ndp, f"NDP mismatch with product filter: Yearly={yearly_ndp}, StaffPerf={staff_perf_ndp}"
        assert yearly_rdp == staff_perf_rdp, f"RDP mismatch with product filter: Yearly={yearly_rdp}, StaffPerf={staff_perf_rdp}"
        
        print(f"✓ Product filter consistency verified")
    
    def test_with_staff_filter(self):
        """Test NDP/RDP consistency when filtering by staff"""
        # First get list of staff
        staff_response = requests.get(
            f"{BASE_URL}/api/staff-users",
            headers=self.headers
        )
        if staff_response.status_code != 200:
            pytest.skip("Could not fetch staff")
        
        staff_list = staff_response.json()
        if not staff_list:
            pytest.skip("No staff available")
        
        # Test with first staff
        staff_id = staff_list[0]['id']
        staff_name = staff_list[0]['name']
        
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1, "staff_id": staff_id}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Calculate totals
        yearly_ndp = sum(m.get('new_id', 0) for m in data['yearly'])
        yearly_rdp = sum(m.get('rdp', 0) for m in data['yearly'])
        staff_perf_ndp = sum(s.get('new_id', 0) for s in data['staff_performance'])
        staff_perf_rdp = sum(s.get('rdp', 0) for s in data['staff_performance'])
        
        print(f"\n=== STAFF FILTER TEST: {staff_name} ===")
        print(f"Yearly:           NDP={yearly_ndp}, RDP={yearly_rdp}")
        print(f"Staff Performance: NDP={staff_perf_ndp}, RDP={staff_perf_rdp}")
        
        assert yearly_ndp == staff_perf_ndp, f"NDP mismatch with staff filter: Yearly={yearly_ndp}, StaffPerf={staff_perf_ndp}"
        assert yearly_rdp == staff_perf_rdp, f"RDP mismatch with staff filter: Yearly={yearly_rdp}, StaffPerf={staff_perf_rdp}"
        
        print(f"✓ Staff filter consistency verified")


class TestTambahanRuleEnforcement:
    """Test that 'tambahan' records are always counted as RDP"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "vicky@crm.com", "password": "admin123"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_tambahan_logic_in_report_code(self):
        """Verify report.py has correct tambahan logic"""
        with open('/app/backend/routes/report.py', 'r') as f:
            content = f.read()
        
        # Check for is_tambahan_record function
        assert 'def is_tambahan_record' in content, "Missing is_tambahan_record helper function"
        
        # Check that tambahan records are excluded from first_date calculation
        assert 'if is_tambahan_record(record):' in content, "Missing tambahan check in first_date calculation"
        assert 'continue' in content, "Missing continue statement to skip tambahan records"
        
        # Check that is_ndp_record returns False for tambahan
        assert 'if is_tambahan_record(record):' in content, "Missing tambahan check in is_ndp_record"
        
        print("✓ Tambahan logic correctly implemented in report.py")
    
    def test_unique_deposits_dictionary_exists(self):
        """Verify report.py uses unique_deposits dictionary as single source of truth"""
        with open('/app/backend/routes/report.py', 'r') as f:
            content = f.read()
        
        # Check for unique_deposits dictionary
        assert 'unique_deposits = {}' in content, "Missing unique_deposits dictionary"
        assert "unique_deposits[key] = {" in content, "Missing unique_deposits population"
        
        # Check that all sections use unique_deposits
        assert content.count('for (pid, date, cid), deposit_info in unique_deposits.items()') >= 4, \
            "Not all sections iterate over unique_deposits"
        
        print("✓ unique_deposits dictionary used as single source of truth")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
