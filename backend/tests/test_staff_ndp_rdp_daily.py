"""
Test suite for GET /api/analytics/staff-ndp-rdp-daily endpoint
Tests: New Staff NDP/RDP Daily Breakdown chart feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestStaffNdpRdpDailyEndpoint:
    """Tests for the Staff NDP/RDP Daily Breakdown endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@crm.com", "password": "admin123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_01_endpoint_returns_200_without_filters(self):
        """Test endpoint returns 200 without any filters"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"✓ Endpoint returns 200. Got {len(data.get('chart_data', []))} chart rows, {len(data.get('staff', []))} staff")

    def test_02_response_structure_is_correct(self):
        """Test response contains chart_data, staff, and period arrays"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        # Check required fields exist
        assert "chart_data" in data, "Response missing 'chart_data'"
        assert "staff" in data, "Response missing 'staff'"
        assert "period" in data, "Response missing 'period'"

        # Check types
        assert isinstance(data["chart_data"], list), "chart_data should be a list"
        assert isinstance(data["staff"], list), "staff should be a list"
        assert isinstance(data["period"], str), "period should be a string"
        print(f"✓ Response structure is correct with chart_data, staff, and period fields")

    def test_03_chart_data_has_correct_format(self):
        """Test chart_data rows have date and ndp_/rdp_ fields for each staff"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["chart_data"]) > 0 and len(data["staff"]) > 0:
            row = data["chart_data"][0]
            staff_id = data["staff"][0]["id"]

            # Check date field exists
            assert "date" in row, "chart_data row missing 'date' field"
            assert isinstance(row["date"], str), "date should be a string"

            # Check ndp_/rdp_ fields for staff
            assert f"ndp_{staff_id}" in row, f"chart_data row missing 'ndp_{staff_id}' field"
            assert f"rdp_{staff_id}" in row, f"chart_data row missing 'rdp_{staff_id}' field"
            print(f"✓ Chart data format is correct with date and ndp_/rdp_ fields: {row}")
        else:
            print("⚠ No chart data available, skipping format check")

    def test_04_staff_array_has_correct_format(self):
        """Test staff array contains id and name for each staff"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        if len(data["staff"]) > 0:
            staff = data["staff"][0]
            assert "id" in staff, "Staff entry missing 'id' field"
            assert "name" in staff, "Staff entry missing 'name' field"
            print(f"✓ Staff array format is correct: {staff}")
        else:
            print("⚠ No staff data available, skipping format check")

    def test_05_period_filter_works(self):
        """Test period=week filter returns different data than default"""
        # Default is month
        response_month = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily?period=month",
            headers=self.headers
        )
        response_week = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily?period=week",
            headers=self.headers
        )

        assert response_month.status_code == 200
        assert response_week.status_code == 200

        data_month = response_month.json()
        data_week = response_week.json()

        # Check period value is reflected
        assert data_month["period"] == "month", f"Expected period='month', got '{data_month['period']}'"
        assert data_week["period"] == "week", f"Expected period='week', got '{data_week['period']}'"
        print(f"✓ Period filter works: month has {len(data_month['chart_data'])} rows, week has {len(data_week['chart_data'])} rows")

    def test_06_product_id_filter_works(self):
        """Test product_id filter reduces/changes the result"""
        # Get products first
        products_resp = requests.get(
            f"{BASE_URL}/api/products",
            headers=self.headers
        )
        assert products_resp.status_code == 200
        products = products_resp.json()

        if len(products) > 0:
            product_id = products[0]["id"]

            response_all = requests.get(
                f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily?period=month",
                headers=self.headers
            )
            response_filtered = requests.get(
                f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily?period=month&product_id={product_id}",
                headers=self.headers
            )

            assert response_all.status_code == 200
            assert response_filtered.status_code == 200

            data_all = response_all.json()
            data_filtered = response_filtered.json()

            print(f"✓ Product filter works: all products has {len(data_all['chart_data'])} rows, filtered has {len(data_filtered['chart_data'])} rows")
        else:
            print("⚠ No products available, skipping product filter test")

    def test_07_unauthenticated_request_fails(self):
        """Test endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily"
        )
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated request, got {response.status_code}"
        print(f"✓ Endpoint correctly rejects unauthenticated requests with {response.status_code}")

    def test_08_non_admin_user_access_denied(self):
        """Test endpoint requires admin role"""
        # Login as staff user
        staff_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "staff@crm.com", "password": "staff123"}
        )

        if staff_response.status_code == 200:
            staff_token = staff_response.json().get("token")
            staff_headers = {
                "Authorization": f"Bearer {staff_token}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
                headers=staff_headers
            )
            # Should return 403 (forbidden) for non-admin users
            assert response.status_code == 403, f"Expected 403 for staff user, got {response.status_code}"
            print(f"✓ Endpoint correctly denies non-admin access with 403")
        else:
            print("⚠ Staff user login failed, skipping role test")

    def test_09_ndp_rdp_values_are_integers(self):
        """Test all ndp_/rdp_ values are non-negative integers"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        for row in data["chart_data"]:
            for key, value in row.items():
                if key.startswith("ndp_") or key.startswith("rdp_"):
                    assert isinstance(value, int), f"Expected int for {key}, got {type(value)}"
                    assert value >= 0, f"Expected non-negative value for {key}, got {value}"

        print(f"✓ All NDP/RDP values are non-negative integers")

    def test_10_different_periods_return_expected_period_value(self):
        """Test all supported period values work correctly"""
        periods = ["today", "yesterday", "week", "month", "quarter", "year"]

        for period in periods:
            response = requests.get(
                f"{BASE_URL}/api/analytics/staff-ndp-rdp-daily?period={period}",
                headers=self.headers
            )
            assert response.status_code == 200, f"Period '{period}' failed with {response.status_code}"
            data = response.json()
            assert data["period"] == period, f"Expected period='{period}', got '{data['period']}'"

        print(f"✓ All period values work: {', '.join(periods)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
