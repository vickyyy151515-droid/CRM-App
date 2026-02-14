"""
Test suite for Advanced Analytics Widget endpoints:
1. Staff Conversion Funnel - /api/analytics/staff-conversion-funnel
2. Revenue Heatmap - /api/analytics/revenue-heatmap  
3. Deposit Lifecycle - /api/analytics/deposit-lifecycle

These 3 endpoints power the new high-value analytics charts added to the CRM.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Credentials
ADMIN_CREDS = {"email": "admin@crm.com", "password": "admin123"}
STAFF_CREDS = {"email": "staff@crm.com", "password": "staff123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    return None  # Staff user may not exist


class TestStaffConversionFunnel:
    """Tests for GET /api/analytics/staff-conversion-funnel"""

    def test_01_returns_funnel_data_structure(self, admin_token):
        """Verify endpoint returns funnel_data array"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-conversion-funnel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "funnel_data" in data, "Response missing 'funnel_data' key"
        assert isinstance(data["funnel_data"], list), "funnel_data should be a list"

    def test_02_funnel_data_has_required_fields(self, admin_token):
        """Verify each funnel entry has all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-conversion-funnel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["funnel_data"]) > 0:
            entry = data["funnel_data"][0]
            required_fields = ["staff_id", "staff_name", "assigned", "wa_checked", "responded", "deposited"]
            for field in required_fields:
                assert field in entry, f"Funnel entry missing '{field}' field"
                
    def test_03_funnel_counts_are_integers(self, admin_token):
        """Verify assigned/wa_checked/responded/deposited are integers"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-conversion-funnel",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["funnel_data"]:
            assert isinstance(entry["assigned"], int), "assigned should be int"
            assert isinstance(entry["wa_checked"], int), "wa_checked should be int"
            assert isinstance(entry["responded"], int), "responded should be int"
            assert isinstance(entry["deposited"], int), "deposited should be int"
            # Values should be non-negative
            assert entry["assigned"] >= 0, "assigned should be >= 0"
            assert entry["wa_checked"] >= 0, "wa_checked should be >= 0"
            assert entry["responded"] >= 0, "responded should be >= 0"
            assert entry["deposited"] >= 0, "deposited should be >= 0"

    def test_04_period_filter_works(self, admin_token):
        """Verify period query parameter is accepted"""
        for period in ["today", "week", "month", "quarter"]:
            response = requests.get(
                f"{BASE_URL}/api/analytics/staff-conversion-funnel?period={period}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Period '{period}' failed: {response.text}"

    def test_05_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-conversion-funnel")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_06_requires_admin_role(self, staff_token):
        """Verify endpoint requires admin role"""
        if staff_token is None:
            pytest.skip("Staff user not available")
        response = requests.get(
            f"{BASE_URL}/api/analytics/staff-conversion-funnel",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff user, got {response.status_code}"


class TestRevenueHeatmap:
    """Tests for GET /api/analytics/revenue-heatmap"""

    def test_01_returns_heatmap_structure(self, admin_token):
        """Verify endpoint returns grid, max_count, max_amount, day_names"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-heatmap",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "grid" in data, "Response missing 'grid' key"
        assert "max_count" in data, "Response missing 'max_count' key"
        assert "max_amount" in data, "Response missing 'max_amount' key"
        assert "day_names" in data, "Response missing 'day_names' key"

    def test_02_day_names_are_correct(self, admin_token):
        """Verify day_names contains Mon-Sun"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-heatmap",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        expected_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        assert data["day_names"] == expected_days, f"day_names mismatch: {data['day_names']}"

    def test_03_grid_row_has_seven_days(self, admin_token):
        """Verify each staff row has exactly 7 days"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-heatmap",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for row in data["grid"]:
            assert "days" in row, "Grid row missing 'days' key"
            assert len(row["days"]) == 7, f"Expected 7 days, got {len(row['days'])}"
            for day in row["days"]:
                assert "day" in day, "Day entry missing 'day' key"
                assert "count" in day, "Day entry missing 'count' key"
                assert "amount" in day, "Day entry missing 'amount' key"

    def test_04_grid_row_has_staff_info(self, admin_token):
        """Verify each grid row has staff_id and staff_name"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-heatmap",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for row in data["grid"]:
            assert "staff_id" in row, "Grid row missing 'staff_id'"
            assert "staff_name" in row, "Grid row missing 'staff_name'"

    def test_05_period_filter_works(self, admin_token):
        """Verify period query parameter is accepted"""
        for period in ["today", "week", "month", "quarter"]:
            response = requests.get(
                f"{BASE_URL}/api/analytics/revenue-heatmap?period={period}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Period '{period}' failed: {response.text}"

    def test_06_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/revenue-heatmap")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_07_requires_admin_role(self, staff_token):
        """Verify endpoint requires admin role"""
        if staff_token is None:
            pytest.skip("Staff user not available")
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-heatmap",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff user, got {response.status_code}"


class TestDepositLifecycle:
    """Tests for GET /api/analytics/deposit-lifecycle"""

    def test_01_returns_lifecycle_data_structure(self, admin_token):
        """Verify endpoint returns lifecycle_data array"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "lifecycle_data" in data, "Response missing 'lifecycle_data' key"
        assert isinstance(data["lifecycle_data"], list), "lifecycle_data should be a list"

    def test_02_lifecycle_data_has_required_fields(self, admin_token):
        """Verify each lifecycle entry has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["lifecycle_data"]) > 0:
            entry = data["lifecycle_data"][0]
            required_fields = [
                "staff_id", "staff_name", "total_responded", "converted_count",
                "pending_count", "avg_days", "min_days", "max_days", "conversion_rate"
            ]
            for field in required_fields:
                assert field in entry, f"Lifecycle entry missing '{field}' field"

    def test_03_numeric_values_are_valid(self, admin_token):
        """Verify numeric fields are properly typed"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["lifecycle_data"]:
            assert isinstance(entry["total_responded"], int), "total_responded should be int"
            assert isinstance(entry["converted_count"], int), "converted_count should be int"
            assert isinstance(entry["pending_count"], int), "pending_count should be int"
            assert isinstance(entry["conversion_rate"], (int, float)), "conversion_rate should be numeric"
            
            # avg_days/min_days/max_days can be None or numeric
            if entry["avg_days"] is not None:
                assert isinstance(entry["avg_days"], (int, float)), "avg_days should be numeric or None"
            if entry["min_days"] is not None:
                assert isinstance(entry["min_days"], (int, float)), "min_days should be numeric or None"
            if entry["max_days"] is not None:
                assert isinstance(entry["max_days"], (int, float)), "max_days should be numeric or None"

    def test_04_conversion_rate_in_valid_range(self, admin_token):
        """Verify conversion_rate is between 0 and 100"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["lifecycle_data"]:
            assert 0 <= entry["conversion_rate"] <= 100, \
                f"conversion_rate out of range: {entry['conversion_rate']}"

    def test_05_period_filter_works(self, admin_token):
        """Verify period query parameter is accepted"""
        for period in ["today", "week", "month", "quarter"]:
            response = requests.get(
                f"{BASE_URL}/api/analytics/deposit-lifecycle?period={period}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Period '{period}' failed: {response.text}"

    def test_06_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/deposit-lifecycle")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_07_requires_admin_role(self, staff_token):
        """Verify endpoint requires admin role"""
        if staff_token is None:
            pytest.skip("Staff user not available")
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff user, got {response.status_code}"

    def test_08_pending_plus_converted_equals_total(self, admin_token):
        """Verify pending_count + converted_count == total_responded"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        for entry in data["lifecycle_data"]:
            total = entry["pending_count"] + entry["converted_count"]
            assert total == entry["total_responded"], \
                f"pending + converted ({total}) != total_responded ({entry['total_responded']})"


class TestProductIdFilter:
    """Test product_id filter across all 3 endpoints"""

    def test_01_funnel_with_product_id(self, admin_token):
        """Verify funnel endpoint accepts product_id filter"""
        # First get available products
        products_resp = requests.get(
            f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            product_id = products_resp.json()[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/analytics/staff-conversion-funnel?product_id={product_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Product filter failed: {response.text}"
        else:
            pytest.skip("No products available")

    def test_02_heatmap_with_product_id(self, admin_token):
        """Verify heatmap endpoint accepts product_id filter"""
        products_resp = requests.get(
            f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            product_id = products_resp.json()[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/analytics/revenue-heatmap?product_id={product_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Product filter failed: {response.text}"
        else:
            pytest.skip("No products available")

    def test_03_lifecycle_with_product_id(self, admin_token):
        """Verify lifecycle endpoint accepts product_id filter"""
        products_resp = requests.get(
            f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if products_resp.status_code == 200 and len(products_resp.json()) > 0:
            product_id = products_resp.json()[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/analytics/deposit-lifecycle?product_id={product_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Product filter failed: {response.text}"
        else:
            pytest.skip("No products available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
