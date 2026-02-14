"""
Tests for the 5 new Advanced Analytics endpoints:
1. Response Time by Staff - GET /api/analytics/response-time-by-staff
2. Follow-up Effectiveness - GET /api/analytics/followup-effectiveness
3. Product Performance - GET /api/analytics/product-performance
4. Customer Value Comparison (LTV) - GET /api/analytics/customer-value-comparison
5. Deposit Trends Over Time - GET /api/analytics/deposit-trends
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuth:
    """Authentication helper for tests"""
    
    @staticmethod
    def get_admin_token():
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token once per module"""
    token = TestAuth.get_admin_token()
    if not token:
        pytest.skip("Admin authentication failed")
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Auth headers fixture"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


# ==================== RESPONSE TIME BY STAFF TESTS ====================

class TestResponseTimeByStaff:
    """Tests for GET /api/analytics/response-time-by-staff endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Response time endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/response-time-by-staff",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Response time endpoint returns 200")
    
    def test_response_structure(self, auth_headers):
        """Response contains response_time_data array"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/response-time-by-staff",
            headers=auth_headers
        )
        data = response.json()
        assert 'response_time_data' in data, "Missing response_time_data field"
        assert isinstance(data['response_time_data'], list), "response_time_data should be a list"
        print(f"✓ Response contains response_time_data with {len(data['response_time_data'])} items")
    
    def test_data_fields(self, auth_headers):
        """Each item has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/response-time-by-staff",
            headers=auth_headers
        )
        data = response.json()
        if data['response_time_data']:
            item = data['response_time_data'][0]
            required_fields = ['staff_id', 'staff_name', 'total_assigned', 'avg_wa_hours', 
                             'avg_respond_hours', 'wa_checked_count', 'responded_count',
                             'fastest_wa', 'slowest_wa']
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            print(f"✓ Data has all required fields: {required_fields}")
        else:
            print("✓ Empty data array (valid)")
    
    def test_period_filter(self, auth_headers):
        """Accepts period filter parameter"""
        for period in ['today', 'week', 'month', 'quarter']:
            response = requests.get(
                f"{BASE_URL}/api/analytics/response-time-by-staff?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed for period={period}"
        print("✓ Period filter works (today/week/month/quarter)")
    
    def test_product_filter(self, auth_headers):
        """Accepts product_id filter parameter"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/response-time-by-staff?product_id=test_product",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✓ Product filter accepted")
    
    def test_auth_required(self):
        """Endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/response-time-by-staff")
        assert response.status_code in [401, 403], "Should require auth"
        print("✓ Authentication required (401/403 without token)")


# ==================== FOLLOW-UP EFFECTIVENESS TESTS ====================

class TestFollowupEffectiveness:
    """Tests for GET /api/analytics/followup-effectiveness endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Follow-up effectiveness endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/followup-effectiveness",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Follow-up effectiveness endpoint returns 200")
    
    def test_response_structure(self, auth_headers):
        """Response contains effectiveness_data array"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/followup-effectiveness",
            headers=auth_headers
        )
        data = response.json()
        assert 'effectiveness_data' in data, "Missing effectiveness_data field"
        assert isinstance(data['effectiveness_data'], list), "effectiveness_data should be a list"
        print(f"✓ Response contains effectiveness_data with {len(data['effectiveness_data'])} items")
    
    def test_data_fields(self, auth_headers):
        """Each item has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/followup-effectiveness",
            headers=auth_headers
        )
        data = response.json()
        if data['effectiveness_data']:
            item = data['effectiveness_data'][0]
            required_fields = ['staff_id', 'staff_name', 'total_assigned', 'wa_checked',
                             'wa_ada', 'responded', 'deposited', 'effectiveness']
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            # Effectiveness should be 0-100
            assert 0 <= item['effectiveness'] <= 100, "effectiveness should be 0-100"
            print(f"✓ Data has all required fields with valid effectiveness value")
        else:
            print("✓ Empty data array (valid)")
    
    def test_period_filter(self, auth_headers):
        """Accepts period filter parameter"""
        for period in ['today', 'week', 'month']:
            response = requests.get(
                f"{BASE_URL}/api/analytics/followup-effectiveness?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed for period={period}"
        print("✓ Period filter works")
    
    def test_product_filter(self, auth_headers):
        """Accepts product_id filter parameter"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/followup-effectiveness?product_id=test_product",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✓ Product filter accepted")
    
    def test_auth_required(self):
        """Endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/followup-effectiveness")
        assert response.status_code in [401, 403], "Should require auth"
        print("✓ Authentication required")


# ==================== PRODUCT PERFORMANCE TESTS ====================

class TestProductPerformance:
    """Tests for GET /api/analytics/product-performance endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Product performance endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/product-performance",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Product performance endpoint returns 200")
    
    def test_response_structure(self, auth_headers):
        """Response contains product_data array"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/product-performance",
            headers=auth_headers
        )
        data = response.json()
        assert 'product_data' in data, "Missing product_data field"
        assert isinstance(data['product_data'], list), "product_data should be a list"
        print(f"✓ Response contains product_data with {len(data['product_data'])} items")
    
    def test_data_fields(self, auth_headers):
        """Each item has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/product-performance",
            headers=auth_headers
        )
        data = response.json()
        if data['product_data']:
            item = data['product_data'][0]
            required_fields = ['product_id', 'product_name', 'ndp_count', 'rdp_count',
                             'total_count', 'ndp_amount', 'rdp_amount', 'total_amount', 
                             'ndp_percentage']
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            # NDP percentage should be 0-100
            assert 0 <= item['ndp_percentage'] <= 100, "ndp_percentage should be 0-100"
            # Total count should equal NDP + RDP
            assert item['total_count'] == item['ndp_count'] + item['rdp_count'], \
                "total_count should equal ndp_count + rdp_count"
            print(f"✓ Data has all required fields with valid values")
        else:
            print("✓ Empty data array (valid)")
    
    def test_period_filter(self, auth_headers):
        """Accepts period filter parameter"""
        for period in ['today', 'week', 'month', 'quarter', 'year']:
            response = requests.get(
                f"{BASE_URL}/api/analytics/product-performance?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed for period={period}"
        print("✓ Period filter works for all options")
    
    def test_auth_required(self):
        """Endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/product-performance")
        assert response.status_code in [401, 403], "Should require auth"
        print("✓ Authentication required")


# ==================== CUSTOMER VALUE COMPARISON (LTV) TESTS ====================

class TestCustomerValueComparison:
    """Tests for GET /api/analytics/customer-value-comparison endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Customer value comparison endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Customer value comparison endpoint returns 200")
    
    def test_response_structure(self, auth_headers):
        """Response contains staff_data, daily_chart, and summary"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison",
            headers=auth_headers
        )
        data = response.json()
        assert 'staff_data' in data, "Missing staff_data field"
        assert 'daily_chart' in data, "Missing daily_chart field"
        assert 'summary' in data, "Missing summary field"
        assert isinstance(data['staff_data'], list), "staff_data should be a list"
        assert isinstance(data['daily_chart'], list), "daily_chart should be a list"
        print(f"✓ Response has staff_data ({len(data['staff_data'])} items), daily_chart ({len(data['daily_chart'])} items), summary")
    
    def test_staff_data_fields(self, auth_headers):
        """Staff data has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison",
            headers=auth_headers
        )
        data = response.json()
        if data['staff_data']:
            item = data['staff_data'][0]
            required_fields = ['staff_id', 'staff_name', 'ndp_amount', 'rdp_amount',
                             'total_amount', 'ndp_count', 'rdp_count', 'avg_ndp', 'avg_rdp']
            for field in required_fields:
                assert field in item, f"Missing field: {field}"
            # Total should equal NDP + RDP
            assert item['total_amount'] == item['ndp_amount'] + item['rdp_amount'], \
                "total_amount should equal ndp_amount + rdp_amount"
            print(f"✓ Staff data has all required fields with valid values")
        else:
            print("✓ Empty staff_data array (valid)")
    
    def test_summary_fields(self, auth_headers):
        """Summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison",
            headers=auth_headers
        )
        data = response.json()
        summary = data['summary']
        required_fields = ['total_ndp_amount', 'total_rdp_amount', 'total_amount', 'ndp_share']
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
        # NDP share should be 0-100
        assert 0 <= summary['ndp_share'] <= 100, "ndp_share should be 0-100"
        print(f"✓ Summary has all required fields")
    
    def test_daily_chart_fields(self, auth_headers):
        """Daily chart has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison",
            headers=auth_headers
        )
        data = response.json()
        if data['daily_chart']:
            item = data['daily_chart'][0]
            required_fields = ['date', 'ndp_amount', 'rdp_amount']
            for field in required_fields:
                assert field in item, f"Missing daily_chart field: {field}"
            print(f"✓ Daily chart has date and NDP/RDP amounts")
        else:
            print("✓ Empty daily_chart array (valid)")
    
    def test_period_and_product_filters(self, auth_headers):
        """Accepts period and product_id filters"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/customer-value-comparison?period=week&product_id=test_product",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✓ Period and product filters accepted")
    
    def test_auth_required(self):
        """Endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/customer-value-comparison")
        assert response.status_code in [401, 403], "Should require auth"
        print("✓ Authentication required")


# ==================== DEPOSIT TRENDS TESTS ====================

class TestDepositTrends:
    """Tests for GET /api/analytics/deposit-trends endpoint"""
    
    def test_endpoint_returns_200(self, auth_headers):
        """Deposit trends endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Deposit trends endpoint returns 200")
    
    def test_response_structure(self, auth_headers):
        """Response contains chart_data, granularity, and summary"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends",
            headers=auth_headers
        )
        data = response.json()
        assert 'chart_data' in data, "Missing chart_data field"
        assert 'granularity' in data, "Missing granularity field"
        assert 'summary' in data, "Missing summary field"
        assert isinstance(data['chart_data'], list), "chart_data should be a list"
        print(f"✓ Response has chart_data ({len(data['chart_data'])} items), granularity='{data['granularity']}', summary")
    
    def test_default_granularity_is_daily(self, auth_headers):
        """Default granularity is daily"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends",
            headers=auth_headers
        )
        data = response.json()
        assert data['granularity'] == 'daily', f"Expected granularity='daily', got '{data['granularity']}'"
        print("✓ Default granularity is 'daily'")
    
    def test_chart_data_fields(self, auth_headers):
        """Chart data has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends",
            headers=auth_headers
        )
        data = response.json()
        if data['chart_data']:
            item = data['chart_data'][0]
            required_fields = ['date', 'amount', 'count', 'unique_customers', 'avg_deposit']
            for field in required_fields:
                assert field in item, f"Missing chart_data field: {field}"
            print(f"✓ Chart data has all required fields")
        else:
            print("✓ Empty chart_data array (valid)")
    
    def test_summary_fields(self, auth_headers):
        """Summary has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends",
            headers=auth_headers
        )
        data = response.json()
        summary = data['summary']
        required_fields = ['total_amount', 'total_deposits', 'avg_per_period', 'peak_period', 'peak_amount']
        for field in required_fields:
            assert field in summary, f"Missing summary field: {field}"
        print(f"✓ Summary has all required fields")
    
    def test_granularity_daily(self, auth_headers):
        """Granularity filter: daily"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends?granularity=daily",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['granularity'] == 'daily'
        print("✓ Daily granularity works")
    
    def test_granularity_weekly(self, auth_headers):
        """Granularity filter: weekly"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends?granularity=weekly",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['granularity'] == 'weekly'
        print("✓ Weekly granularity works")
    
    def test_granularity_monthly(self, auth_headers):
        """Granularity filter: monthly"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends?granularity=monthly",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data['granularity'] == 'monthly'
        print("✓ Monthly granularity works")
    
    def test_period_filter(self, auth_headers):
        """Accepts period filter parameter"""
        for period in ['week', 'month', 'quarter']:
            response = requests.get(
                f"{BASE_URL}/api/analytics/deposit-trends?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed for period={period}"
        print("✓ Period filter works")
    
    def test_product_filter(self, auth_headers):
        """Accepts product_id filter parameter"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends?product_id=test_product",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✓ Product filter accepted")
    
    def test_combined_filters(self, auth_headers):
        """Combined filters: period + granularity + product"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/deposit-trends?period=month&granularity=weekly&product_id=test",
            headers=auth_headers
        )
        assert response.status_code == 200
        print("✓ Combined filters work")
    
    def test_auth_required(self):
        """Endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/analytics/deposit-trends")
        assert response.status_code in [401, 403], "Should require auth"
        print("✓ Authentication required")


# ==================== INTEGRATION TEST ====================

class TestAllEndpointsIntegration:
    """Integration tests for all 5 new analytics endpoints"""
    
    def test_all_endpoints_with_same_period(self, auth_headers):
        """All endpoints work with the same period filter"""
        period = 'month'
        endpoints = [
            '/api/analytics/response-time-by-staff',
            '/api/analytics/followup-effectiveness',
            '/api/analytics/product-performance',
            '/api/analytics/customer-value-comparison',
            '/api/analytics/deposit-trends'
        ]
        
        for endpoint in endpoints:
            response = requests.get(
                f"{BASE_URL}{endpoint}?period={period}",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed: {endpoint}"
        print(f"✓ All 5 endpoints work with period={period}")
    
    def test_all_endpoints_with_filters(self, auth_headers):
        """All filterable endpoints work with product_id filter"""
        endpoints_with_product_filter = [
            '/api/analytics/response-time-by-staff',
            '/api/analytics/followup-effectiveness',
            '/api/analytics/customer-value-comparison',
            '/api/analytics/deposit-trends'
        ]
        
        for endpoint in endpoints_with_product_filter:
            response = requests.get(
                f"{BASE_URL}{endpoint}?period=month&product_id=test",
                headers=auth_headers
            )
            assert response.status_code == 200, f"Failed: {endpoint}"
        print(f"✓ All filterable endpoints accept product_id filter")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
