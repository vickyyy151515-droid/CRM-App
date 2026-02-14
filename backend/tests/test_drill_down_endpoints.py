"""
Tests for Analytics Drill-Down Endpoints
Tests the 5 new drill-down detail endpoints:
1. /api/analytics/drill-down/response-time - Individual records with WA/response timestamps
2. /api/analytics/drill-down/followup-detail - Responded customers with deposit status
3. /api/analytics/drill-down/product-staff - Staff breakdown for a product
4. /api/analytics/drill-down/staff-customers - Top customers for a staff
5. /api/analytics/drill-down/date-deposits - Deposits for a specific date
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDrillDownEndpoints:
    """Test all 5 drill-down analytics endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Authentication failed - skipping tests")
    
    # ==================== RESPONSE TIME DRILL-DOWN ====================
    
    def test_response_time_drilldown_returns_200(self):
        """Test /api/analytics/drill-down/response-time returns 200"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/response-time", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/analytics/drill-down/response-time returns 200")
    
    def test_response_time_drilldown_has_records_field(self):
        """Test response-time drill-down has records array"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/response-time", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        assert "records" in data, "Response should have 'records' field"
        assert isinstance(data["records"], list), "'records' should be a list"
        print(f"✓ Response has {len(data['records'])} records")
    
    def test_response_time_drilldown_record_fields(self):
        """Test response-time drill-down record has correct fields"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/response-time", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        if data.get("records") and len(data["records"]) > 0:
            record = data["records"][0]
            expected_fields = ["record_id", "customer_id", "product", "assigned_at", "wa_status", "wa_hours", "respond_status", "respond_hours"]
            for field in expected_fields:
                assert field in record, f"Record should have '{field}' field"
            print(f"✓ Record has all expected fields: {expected_fields}")
        else:
            print("⚠ No records returned to verify fields")
    
    def test_response_time_drilldown_total_count(self):
        """Test response-time drill-down has total field"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/response-time", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        assert "total" in data, "Response should have 'total' field"
        assert isinstance(data["total"], int), "'total' should be an integer"
        print(f"✓ Total count: {data['total']}")
    
    # ==================== FOLLOWUP DETAIL DRILL-DOWN ====================
    
    def test_followup_detail_drilldown_returns_200(self):
        """Test /api/analytics/drill-down/followup-detail returns 200"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/followup-detail", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/analytics/drill-down/followup-detail returns 200")
    
    def test_followup_detail_drilldown_has_records_and_stats(self):
        """Test followup-detail drill-down has records, converted, pending"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/followup-detail", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        assert "records" in data, "Response should have 'records' field"
        assert "converted" in data, "Response should have 'converted' field"
        assert "pending" in data, "Response should have 'pending' field"
        assert "total" in data, "Response should have 'total' field"
        print(f"✓ Followup detail: {data['converted']} converted, {data['pending']} pending, {data['total']} total")
    
    def test_followup_detail_record_has_deposit_status(self):
        """Test followup-detail records have deposited boolean"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/followup-detail", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        if data.get("records") and len(data["records"]) > 0:
            record = data["records"][0]
            expected_fields = ["customer_id", "product", "deposited", "deposit_total", "deposit_count"]
            for field in expected_fields:
                assert field in record, f"Record should have '{field}' field"
            assert isinstance(record["deposited"], bool), "'deposited' should be boolean"
            print(f"✓ Followup records have deposit status fields")
        else:
            print("⚠ No records returned to verify fields")
    
    # ==================== PRODUCT-STAFF DRILL-DOWN ====================
    
    def test_product_staff_drilldown_returns_200(self):
        """Test /api/analytics/drill-down/product-staff returns 200"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/product-staff", params={
            "product_id": "prod-istana2000",
            "period": "year"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/analytics/drill-down/product-staff returns 200")
    
    def test_product_staff_drilldown_has_staff_breakdown(self):
        """Test product-staff drill-down has staff_breakdown array"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/product-staff", params={
            "product_id": "prod-istana2000",
            "period": "year"
        })
        data = response.json()
        assert "staff_breakdown" in data, "Response should have 'staff_breakdown' field"
        assert "total_staff" in data, "Response should have 'total_staff' field"
        assert isinstance(data["staff_breakdown"], list), "'staff_breakdown' should be a list"
        print(f"✓ Product staff breakdown: {data['total_staff']} staff found")
    
    def test_product_staff_breakdown_fields(self):
        """Test product-staff breakdown has NDP/RDP breakdown"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/product-staff", params={
            "product_id": "prod-istana2000",
            "period": "year"
        })
        data = response.json()
        if data.get("staff_breakdown") and len(data["staff_breakdown"]) > 0:
            staff = data["staff_breakdown"][0]
            expected_fields = ["staff_id", "staff_name", "ndp_count", "rdp_count", "ndp_amount", "rdp_amount", "total_amount", "total_count"]
            for field in expected_fields:
                assert field in staff, f"Staff breakdown should have '{field}' field"
            print(f"✓ Staff breakdown has NDP/RDP fields: {staff['staff_name']} - NDP: {staff['ndp_count']}, RDP: {staff['rdp_count']}")
        else:
            print("⚠ No staff breakdown returned to verify fields")
    
    def test_product_staff_with_different_products(self):
        """Test product-staff endpoint with different product IDs"""
        for product_id in ["prod-istana2000", "prod-liga2000", "prod-pucuk33"]:
            response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/product-staff", params={
                "product_id": product_id,
                "period": "year"
            })
            assert response.status_code == 200, f"Expected 200 for {product_id}, got {response.status_code}"
            print(f"✓ Product {product_id} returns valid response")
    
    # ==================== STAFF-CUSTOMERS DRILL-DOWN ====================
    
    def test_staff_customers_drilldown_returns_200(self):
        """Test /api/analytics/drill-down/staff-customers returns 200"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/staff-customers", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/analytics/drill-down/staff-customers returns 200")
    
    def test_staff_customers_has_customers_array(self):
        """Test staff-customers drill-down has customers array"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/staff-customers", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        assert "customers" in data, "Response should have 'customers' field"
        assert "total" in data, "Response should have 'total' field"
        assert isinstance(data["customers"], list), "'customers' should be a list"
        print(f"✓ Staff customers: {data['total']} customers found")
    
    def test_staff_customers_record_fields(self):
        """Test staff-customers records have customer details"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/staff-customers", params={
            "staff_id": "staff-user-1",
            "period": "year"
        })
        data = response.json()
        if data.get("customers") and len(data["customers"]) > 0:
            customer = data["customers"][0]
            expected_fields = ["customer_id", "customer_name", "product", "type", "total_amount", "deposit_count", "first_deposit", "last_deposit"]
            for field in expected_fields:
                assert field in customer, f"Customer should have '{field}' field"
            assert customer["type"] in ["NDP", "RDP"], f"Customer type should be 'NDP' or 'RDP', got {customer['type']}"
            print(f"✓ Customer record has all fields: {customer['customer_name']} ({customer['type']}) - {customer['total_amount']}")
        else:
            print("⚠ No customers returned to verify fields")
    
    # ==================== DATE-DEPOSITS DRILL-DOWN ====================
    
    def test_date_deposits_drilldown_returns_200(self):
        """Test /api/analytics/drill-down/date-deposits returns 200"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/date-deposits", params={
            "date": "2026-02-10"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/analytics/drill-down/date-deposits returns 200")
    
    def test_date_deposits_has_required_fields(self):
        """Test date-deposits drill-down has deposits array and totals"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/date-deposits", params={
            "date": "2026-02-10"
        })
        data = response.json()
        assert "deposits" in data, "Response should have 'deposits' field"
        assert "total_count" in data, "Response should have 'total_count' field"
        assert "total_amount" in data, "Response should have 'total_amount' field"
        assert isinstance(data["deposits"], list), "'deposits' should be a list"
        print(f"✓ Date deposits: {data['total_count']} deposits, total: {data['total_amount']}")
    
    def test_date_deposits_record_fields(self):
        """Test date-deposits records have deposit details"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/date-deposits", params={
            "date": "2026-02-10"
        })
        data = response.json()
        if data.get("deposits") and len(data["deposits"]) > 0:
            deposit = data["deposits"][0]
            expected_fields = ["staff_name", "customer_id", "customer_name", "product", "amount", "date"]
            for field in expected_fields:
                assert field in deposit, f"Deposit should have '{field}' field"
            print(f"✓ Deposit record: {deposit['customer_name']} - {deposit['amount']} from {deposit['staff_name']}")
        else:
            print("⚠ No deposits returned for this date (may be expected)")
    
    def test_date_deposits_with_granularity(self):
        """Test date-deposits endpoint accepts granularity parameter"""
        for granularity in ["daily", "weekly", "monthly"]:
            response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/date-deposits", params={
                "date": "2026-02",
                "granularity": granularity
            })
            assert response.status_code == 200, f"Expected 200 for granularity={granularity}, got {response.status_code}"
            print(f"✓ Granularity '{granularity}' works")
    
    def test_date_deposits_with_product_filter(self):
        """Test date-deposits endpoint accepts product_id filter"""
        response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/date-deposits", params={
            "date": "2026-02-10",
            "product_id": "prod-istana2000"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ Date deposits with product_id filter works")
    
    # ==================== AUTHENTICATION TESTS ====================
    
    def test_drill_down_endpoints_require_auth(self):
        """Test all drill-down endpoints require authentication"""
        no_auth_session = requests.Session()
        endpoints = [
            ("/api/analytics/drill-down/response-time", {"staff_id": "staff-user-1", "period": "month"}),
            ("/api/analytics/drill-down/followup-detail", {"staff_id": "staff-user-1", "period": "month"}),
            ("/api/analytics/drill-down/product-staff", {"product_id": "prod-istana2000", "period": "month"}),
            ("/api/analytics/drill-down/staff-customers", {"staff_id": "staff-user-1", "period": "month"}),
            ("/api/analytics/drill-down/date-deposits", {"date": "2026-02-10"}),
        ]
        
        for endpoint, params in endpoints:
            response = no_auth_session.get(f"{BASE_URL}{endpoint}", params=params)
            assert response.status_code in [401, 403], f"{endpoint} should require auth, got {response.status_code}"
            print(f"✓ {endpoint} requires authentication")
    
    # ==================== PERIOD FILTER TESTS ====================
    
    def test_response_time_period_filters(self):
        """Test response-time accepts different period filters"""
        for period in ["today", "week", "month", "quarter", "year"]:
            response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/response-time", params={
                "staff_id": "staff-user-1",
                "period": period
            })
            assert response.status_code == 200, f"Expected 200 for period={period}, got {response.status_code}"
            print(f"✓ Response time period '{period}' works")
    
    def test_followup_detail_period_filters(self):
        """Test followup-detail accepts different period filters"""
        for period in ["today", "week", "month", "quarter", "year"]:
            response = self.session.get(f"{BASE_URL}/api/analytics/drill-down/followup-detail", params={
                "staff_id": "staff-user-1",
                "period": period
            })
            assert response.status_code == 200, f"Expected 200 for period={period}, got {response.status_code}"
            print(f"✓ Followup detail period '{period}' works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
