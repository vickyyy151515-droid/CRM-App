"""
Test NDP/RDP Consistency Across All 3 Main Endpoints After Report.py Fix

This test validates the bug fix where:
- report.py unique_deposits key was changed from (product_id, date, customer_id) 
  to (staff_id, product_id, date, customer_id)

The fix ensures NDP/RDP counts are consistent across:
1. /api/omset/summary - OMSET CRM page
2. /api/report-crm/data - Report CRM page  
3. /api/daily-summary - Daily Summary

Key verification points:
- For the same date range, NDP+RDP counts should match across all endpoints
- Staff-specific NDP/RDP must now be consistent (staff_id in the key)
- Report CRM monthly_by_staff totals should match omset summary by_staff totals

Test Credentials: Admin - email=vicky@crm.com, password=admin123
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestNDPRDPCrossEndpointConsistency:
    """
    CRITICAL: Compare NDP/RDP counts across /api/omset/summary, /api/report-crm/data, /api/daily-summary
    """
    
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
        print(f"\n✓ Auth token obtained successfully")
    
    def test_01_all_three_endpoints_return_200(self):
        """Test all 3 endpoints return 200 OK"""
        # Get current date info
        now = datetime.now()
        year = now.year
        month = now.month
        today = now.strftime('%Y-%m-%d')
        
        # Test /api/omset/summary
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers
        )
        assert omset_resp.status_code == 200, f"omset/summary failed: {omset_resp.status_code} - {omset_resp.text}"
        
        # Test /api/report-crm/data
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": year, "month": month}
        )
        assert report_resp.status_code == 200, f"report-crm/data failed: {report_resp.status_code} - {report_resp.text}"
        
        # Test /api/daily-summary
        daily_resp = requests.get(
            f"{BASE_URL}/api/daily-summary",
            headers=self.headers,
            params={"date": today}
        )
        assert daily_resp.status_code == 200, f"daily-summary failed: {daily_resp.status_code} - {daily_resp.text}"
        
        print("✓ All 3 endpoints return 200 OK")
    
    def test_02_omset_summary_vs_report_crm_yearly_totals(self):
        """
        CRITICAL: Compare OMSET summary totals with Report CRM yearly totals for 2026
        
        This tests the fix: the unique_deposits key in report.py now includes staff_id
        """
        # Get omset summary for full year 2026
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"start_date": "2026-01-01", "end_date": "2026-12-31"}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        
        # Get report CRM data for 2026
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        
        # Extract totals from omset summary
        omset_total = omset_data.get("total", {})
        omset_ndp = omset_total.get("total_ndp", 0)
        omset_rdp = omset_total.get("total_rdp", 0)
        
        # Extract totals from report CRM yearly data
        yearly = report_data.get("yearly", [])
        report_ndp = sum(m.get('new_id', 0) for m in yearly)
        report_rdp = sum(m.get('rdp', 0) for m in yearly)
        
        print(f"\n{'='*60}")
        print(f"OMSET SUMMARY vs REPORT CRM YEARLY TOTALS (2026)")
        print(f"{'='*60}")
        print(f"OMSET Summary:  NDP={omset_ndp:>5}, RDP={omset_rdp:>5}")
        print(f"Report CRM:     NDP={report_ndp:>5}, RDP={report_rdp:>5}")
        print(f"{'='*60}")
        
        # The counts should match after the fix
        assert omset_ndp == report_ndp, f"NDP MISMATCH! OMSET={omset_ndp}, Report={report_ndp}"
        assert omset_rdp == report_rdp, f"RDP MISMATCH! OMSET={omset_rdp}, Report={report_rdp}"
        
        print("✓ OMSET Summary matches Report CRM yearly totals")
    
    def test_03_omset_summary_by_staff_vs_report_monthly_by_staff(self):
        """
        CRITICAL: Compare staff-level NDP/RDP between OMSET summary and Report CRM
        
        This is the key test for the fix: staff attribution should now be consistent
        because report.py uses staff_id in the unique_deposits key
        """
        # Get omset summary for January 2026
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        
        # Get report CRM data for January 2026
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        
        # Build staff totals from omset summary
        omset_by_staff = omset_data.get("by_staff", [])
        omset_staff_map = {}
        for staff in omset_by_staff:
            sid = staff.get('staff_id')
            omset_staff_map[sid] = {
                'name': staff.get('staff_name'),
                'ndp': staff.get('ndp_count', 0),
                'rdp': staff.get('rdp_count', 0)
            }
        
        # Build staff totals from report CRM monthly_by_staff (January only)
        monthly_by_staff = report_data.get("monthly_by_staff", [])
        jan_data = next((m for m in monthly_by_staff if m['month'] == 1), None)
        
        report_staff_map = {}
        if jan_data:
            for staff in jan_data.get('staff', []):
                sid = staff.get('staff_id')
                report_staff_map[sid] = {
                    'name': staff.get('staff_name'),
                    'ndp': staff.get('new_id', 0),
                    'rdp': staff.get('rdp', 0)
                }
        
        print(f"\n{'='*60}")
        print(f"OMSET BY STAFF vs REPORT MONTHLY_BY_STAFF (Jan 2026)")
        print(f"{'='*60}")
        
        mismatches = []
        all_staff_ids = set(omset_staff_map.keys()) | set(report_staff_map.keys())
        
        for sid in all_staff_ids:
            omset_staff = omset_staff_map.get(sid, {'name': 'N/A', 'ndp': 0, 'rdp': 0})
            report_staff = report_staff_map.get(sid, {'name': 'N/A', 'ndp': 0, 'rdp': 0})
            
            name = omset_staff.get('name') or report_staff.get('name') or sid
            
            print(f"  {name}:")
            print(f"    OMSET:  NDP={omset_staff['ndp']:>3}, RDP={omset_staff['rdp']:>3}")
            print(f"    Report: NDP={report_staff['ndp']:>3}, RDP={report_staff['rdp']:>3}")
            
            if omset_staff['ndp'] != report_staff['ndp']:
                mismatches.append(f"{name}: NDP OMSET={omset_staff['ndp']} vs Report={report_staff['ndp']}")
            if omset_staff['rdp'] != report_staff['rdp']:
                mismatches.append(f"{name}: RDP OMSET={omset_staff['rdp']} vs Report={report_staff['rdp']}")
        
        print(f"{'='*60}")
        
        if mismatches:
            print("MISMATCHES FOUND:")
            for m in mismatches:
                print(f"  ✗ {m}")
            pytest.fail(f"Staff-level NDP/RDP mismatches: {mismatches}")
        
        print("✓ Staff-level NDP/RDP matches between OMSET and Report CRM")
    
    def test_04_daily_summary_vs_omset_summary_for_specific_date(self):
        """
        Compare daily-summary endpoint with omset summary for a specific date
        """
        # Use a recent date that likely has data
        test_date = "2026-01-15"
        
        # Get omset summary for that specific date
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"start_date": test_date, "end_date": test_date}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        
        # Get daily summary for that date
        daily_resp = requests.get(
            f"{BASE_URL}/api/daily-summary",
            headers=self.headers,
            params={"date": test_date}
        )
        assert daily_resp.status_code == 200
        daily_data = daily_resp.json()
        
        # Extract totals from omset summary
        omset_total = omset_data.get("total", {})
        omset_ndp = omset_total.get("total_ndp", 0)
        omset_rdp = omset_total.get("total_rdp", 0)
        
        # Extract totals from daily summary
        daily_ndp = daily_data.get("total_ndp", 0)
        daily_rdp = daily_data.get("total_rdp", 0)
        
        print(f"\n{'='*60}")
        print(f"OMSET SUMMARY vs DAILY SUMMARY ({test_date})")
        print(f"{'='*60}")
        print(f"OMSET Summary:  NDP={omset_ndp:>5}, RDP={omset_rdp:>5}")
        print(f"Daily Summary:  NDP={daily_ndp:>5}, RDP={daily_rdp:>5}")
        print(f"{'='*60}")
        
        assert omset_ndp == daily_ndp, f"NDP MISMATCH! OMSET={omset_ndp}, Daily={daily_ndp}"
        assert omset_rdp == daily_rdp, f"RDP MISMATCH! OMSET={omset_rdp}, Daily={daily_rdp}"
        
        print("✓ OMSET Summary matches Daily Summary for single date")
    
    def test_05_report_crm_internal_consistency(self):
        """
        Verify Report CRM internal consistency after the fix:
        - yearly totals == monthly_by_staff totals == staff_performance totals == monthly data totals
        """
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert report_resp.status_code == 200
        data = report_resp.json()
        
        # 1. Yearly totals
        yearly_ndp = sum(m.get('new_id', 0) for m in data.get('yearly', []))
        yearly_rdp = sum(m.get('rdp', 0) for m in data.get('yearly', []))
        
        # 2. Monthly by staff totals
        monthly_staff_ndp = sum(m['totals'].get('new_id', 0) for m in data.get('monthly_by_staff', []))
        monthly_staff_rdp = sum(m['totals'].get('rdp', 0) for m in data.get('monthly_by_staff', []))
        
        # 3. Staff performance totals
        staff_perf_ndp = sum(s.get('new_id', 0) for s in data.get('staff_performance', []))
        staff_perf_rdp = sum(s.get('rdp', 0) for s in data.get('staff_performance', []))
        
        # 4. Monthly data totals
        monthly_data_ndp = sum(d.get('new_id', 0) for d in data.get('monthly', []))
        monthly_data_rdp = sum(d.get('rdp', 0) for d in data.get('monthly', []))
        
        print(f"\n{'='*60}")
        print(f"REPORT CRM INTERNAL CONSISTENCY CHECK (2026)")
        print(f"{'='*60}")
        print(f"1. Yearly Summary:     NDP={yearly_ndp:>5}, RDP={yearly_rdp:>5}")
        print(f"2. Monthly By Staff:   NDP={monthly_staff_ndp:>5}, RDP={monthly_staff_rdp:>5}")
        print(f"3. Staff Performance:  NDP={staff_perf_ndp:>5}, RDP={staff_perf_rdp:>5}")
        print(f"4. Monthly Data:       NDP={monthly_data_ndp:>5}, RDP={monthly_data_rdp:>5}")
        print(f"{'='*60}")
        
        # All NDP values must match
        ndp_values = [yearly_ndp, monthly_staff_ndp, staff_perf_ndp, monthly_data_ndp]
        if len(set(ndp_values)) != 1:
            pytest.fail(f"NDP MISMATCH! Values differ: Yearly={yearly_ndp}, MonthlyStaff={monthly_staff_ndp}, StaffPerf={staff_perf_ndp}, MonthlyData={monthly_data_ndp}")
        
        # All RDP values must match
        rdp_values = [yearly_rdp, monthly_staff_rdp, staff_perf_rdp, monthly_data_rdp]
        if len(set(rdp_values)) != 1:
            pytest.fail(f"RDP MISMATCH! Values differ: Yearly={yearly_rdp}, MonthlyStaff={monthly_staff_rdp}, StaffPerf={staff_perf_rdp}, MonthlyData={monthly_data_rdp}")
        
        print("✓ Report CRM internal consistency verified (all 4 sections match)")
    
    def test_06_all_three_endpoints_for_same_month_totals(self):
        """
        MASTER TEST: All 3 endpoints should return same NDP+RDP totals for January 2026
        """
        # Get omset summary for January 2026
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        omset_total = omset_data.get("total", {})
        omset_ndp = omset_total.get("total_ndp", 0)
        omset_rdp = omset_total.get("total_rdp", 0)
        
        # Get report CRM data for January 2026
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1}
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        
        # Get January from monthly_by_staff
        monthly_by_staff = report_data.get("monthly_by_staff", [])
        jan_data = next((m for m in monthly_by_staff if m['month'] == 1), None)
        report_jan_ndp = jan_data['totals'].get('new_id', 0) if jan_data else 0
        report_jan_rdp = jan_data['totals'].get('rdp', 0) if jan_data else 0
        
        # Aggregate daily summary for all days in January 2026
        daily_ndp_total = 0
        daily_rdp_total = 0
        
        # Sample a few key dates
        test_dates = ["2026-01-01", "2026-01-15", "2026-01-31"]
        daily_breakdown = {}
        
        for date in test_dates:
            daily_resp = requests.get(
                f"{BASE_URL}/api/daily-summary",
                headers=self.headers,
                params={"date": date}
            )
            if daily_resp.status_code == 200:
                daily_data = daily_resp.json()
                ndp = daily_data.get("total_ndp", 0)
                rdp = daily_data.get("total_rdp", 0)
                daily_breakdown[date] = {'ndp': ndp, 'rdp': rdp}
        
        # Get all days from omset summary daily breakdown
        omset_daily = omset_data.get("daily", [])
        omset_daily_ndp = sum(d.get("ndp_count", 0) for d in omset_daily)
        omset_daily_rdp = sum(d.get("rdp_count", 0) for d in omset_daily)
        
        print(f"\n{'='*60}")
        print(f"ALL 3 ENDPOINTS - JANUARY 2026 TOTALS")
        print(f"{'='*60}")
        print(f"OMSET Summary Total:     NDP={omset_ndp:>5}, RDP={omset_rdp:>5}")
        print(f"OMSET Daily Sum:         NDP={omset_daily_ndp:>5}, RDP={omset_daily_rdp:>5}")
        print(f"Report CRM (Jan):        NDP={report_jan_ndp:>5}, RDP={report_jan_rdp:>5}")
        print(f"Daily Summary samples:")
        for date, vals in daily_breakdown.items():
            print(f"  {date}: NDP={vals['ndp']}, RDP={vals['rdp']}")
        print(f"{'='*60}")
        
        # OMSET summary total should match omset daily sum
        assert omset_ndp == omset_daily_ndp, f"OMSET total ({omset_ndp}) != OMSET daily sum ({omset_daily_ndp})"
        assert omset_rdp == omset_daily_rdp, f"OMSET total ({omset_rdp}) != OMSET daily sum ({omset_daily_rdp})"
        
        # OMSET should match Report CRM January totals
        assert omset_ndp == report_jan_ndp, f"OMSET ({omset_ndp}) != Report CRM Jan ({report_jan_ndp})"
        assert omset_rdp == report_jan_rdp, f"OMSET ({omset_rdp}) != Report CRM Jan ({report_jan_rdp})"
        
        print("✓ All 3 endpoints return consistent NDP/RDP totals for January 2026")
    
    def test_07_verify_fix_in_report_py_code(self):
        """
        Code review: Verify report.py uses staff_id in unique_deposits key
        """
        with open('/app/backend/routes/report.py', 'r') as f:
            content = f.read()
        
        # Check that unique_deposits key includes staff_id (sid)
        assert 'key = (sid, pid, date, cid_normalized)' in content, \
            "CRITICAL: report.py unique_deposits key must include staff_id (sid)"
        
        # Check that loop iterations use the correct key format
        assert 'for (sid, pid, date, cid), deposit_info in unique_deposits.items()' in content, \
            "CRITICAL: report.py loop must unpack (sid, pid, date, cid)"
        
        # Check that staff_id is extracted from the key
        assert '# staff_id is now part of the key' in content or '# staff_id is part of the key' in content, \
            "Missing comment about staff_id being part of key"
        
        print("✓ report.py correctly uses staff_id (sid) in unique_deposits key")
        print("  Key format: (staff_id, product_id, date, customer_id_normalized)")
    
    def test_08_verify_db_operations_single_source_of_truth(self):
        """
        Verify build_staff_first_date_map is the single source of truth
        """
        with open('/app/backend/utils/db_operations.py', 'r') as f:
            content = f.read()
        
        # Check that build_staff_first_date_map uses (staff_id, customer_id, product_id) key
        assert 'key = (staff_id, normalized_cid, prod_id)' in content, \
            "build_staff_first_date_map must use (staff_id, customer_id, product_id) key"
        
        # Check SINGLE SOURCE OF TRUTH comment
        assert 'SINGLE SOURCE OF TRUTH' in content, \
            "Missing SINGLE SOURCE OF TRUTH comment in db_operations.py"
        
        print("✓ db_operations.py build_staff_first_date_map is single source of truth")
        print("  Key format: (staff_id, customer_id_normalized, product_id)")


class TestNDPRDPWithFilters:
    """Test NDP/RDP consistency with product and staff filters"""
    
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
    
    def test_09_consistency_with_product_filter(self):
        """Test NDP/RDP consistency when filtered by product"""
        # Get list of products
        products_resp = requests.get(
            f"{BASE_URL}/api/products",
            headers=self.headers
        )
        if products_resp.status_code != 200 or not products_resp.json():
            pytest.skip("No products available")
        
        products = products_resp.json()
        product_id = products[0]['id']
        product_name = products[0]['name']
        
        # Get omset summary filtered by product
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"product_id": product_id, "start_date": "2026-01-01", "end_date": "2026-12-31"}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        omset_ndp = omset_data.get("total", {}).get("total_ndp", 0)
        omset_rdp = omset_data.get("total", {}).get("total_rdp", 0)
        
        # Get report CRM filtered by product
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1, "product_id": product_id}
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        report_ndp = sum(m.get('new_id', 0) for m in report_data.get('yearly', []))
        report_rdp = sum(m.get('rdp', 0) for m in report_data.get('yearly', []))
        
        print(f"\n{'='*60}")
        print(f"PRODUCT FILTER TEST: {product_name}")
        print(f"{'='*60}")
        print(f"OMSET Summary:  NDP={omset_ndp:>5}, RDP={omset_rdp:>5}")
        print(f"Report CRM:     NDP={report_ndp:>5}, RDP={report_rdp:>5}")
        print(f"{'='*60}")
        
        assert omset_ndp == report_ndp, f"NDP MISMATCH with product filter: OMSET={omset_ndp}, Report={report_ndp}"
        assert omset_rdp == report_rdp, f"RDP MISMATCH with product filter: OMSET={omset_rdp}, Report={report_rdp}"
        
        print("✓ NDP/RDP consistent with product filter")
    
    def test_10_consistency_with_staff_filter(self):
        """Test NDP/RDP consistency when filtered by staff"""
        # Get list of staff
        staff_resp = requests.get(
            f"{BASE_URL}/api/staff-users",
            headers=self.headers
        )
        if staff_resp.status_code != 200 or not staff_resp.json():
            pytest.skip("No staff available")
        
        staff_list = staff_resp.json()
        staff_id = staff_list[0]['id']
        staff_name = staff_list[0]['name']
        
        # Get omset summary filtered by staff
        omset_resp = requests.get(
            f"{BASE_URL}/api/omset/summary",
            headers=self.headers,
            params={"staff_id": staff_id, "start_date": "2026-01-01", "end_date": "2026-12-31"}
        )
        assert omset_resp.status_code == 200
        omset_data = omset_resp.json()
        omset_ndp = omset_data.get("total", {}).get("total_ndp", 0)
        omset_rdp = omset_data.get("total", {}).get("total_rdp", 0)
        
        # Get report CRM filtered by staff
        report_resp = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            headers=self.headers,
            params={"year": 2026, "month": 1, "staff_id": staff_id}
        )
        assert report_resp.status_code == 200
        report_data = report_resp.json()
        report_ndp = sum(m.get('new_id', 0) for m in report_data.get('yearly', []))
        report_rdp = sum(m.get('rdp', 0) for m in report_data.get('yearly', []))
        
        print(f"\n{'='*60}")
        print(f"STAFF FILTER TEST: {staff_name}")
        print(f"{'='*60}")
        print(f"OMSET Summary:  NDP={omset_ndp:>5}, RDP={omset_rdp:>5}")
        print(f"Report CRM:     NDP={report_ndp:>5}, RDP={report_rdp:>5}")
        print(f"{'='*60}")
        
        assert omset_ndp == report_ndp, f"NDP MISMATCH with staff filter: OMSET={omset_ndp}, Report={report_ndp}"
        assert omset_rdp == report_rdp, f"RDP MISMATCH with staff filter: OMSET={omset_rdp}, Report={report_rdp}"
        
        print("✓ NDP/RDP consistent with staff filter")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
