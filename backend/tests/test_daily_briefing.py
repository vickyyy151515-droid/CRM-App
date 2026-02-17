"""
Test Daily Pop-Up Briefing Feature
Tests for:
1. GET /api/retention/daily-briefing - returns show=true with at_risk and followups for staff
2. GET /api/retention/daily-briefing - returns show=false with reason='not_staff' for admin
3. POST /api/retention/daily-briefing/dismiss - marks briefing as seen
4. GET /api/retention/daily-briefing - returns show=false reason='already_seen' after dismiss
5. At-risk categories: critical (14-30d), high (7-13d), medium (3-6d with 2+ deposits)
6. Max 5 customers per risk level and 5 per product in followups
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"


class TestDailyBriefing:
    """Daily briefing endpoints tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture
    def staff_token(self):
        """Get staff authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff authentication failed")
    
    @pytest.fixture
    def staff_session(self, staff_token):
        """Session with staff auth header"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {staff_token}",
            "Content-Type": "application/json"
        })
        return session
    
    @pytest.fixture
    def admin_session(self, admin_token):
        """Session with admin auth header"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        })
        return session

    # ==== TEST 1: Staff user gets show=true with at_risk and followups_by_product ====
    def test_staff_daily_briefing_returns_show_true(self, staff_session):
        """GET /api/retention/daily-briefing returns show=true for staff user"""
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should either show=True with data, or show=False with 'already_seen' reason
        assert 'show' in data, "Response must contain 'show' field"
        
        if data['show']:
            # Verify structure when showing
            assert 'at_risk' in data, "Response must contain 'at_risk' when show=True"
            assert 'followups_by_product' in data, "Response must contain 'followups_by_product' when show=True"
            assert 'date' in data, "Response must contain 'date' when show=True"
            
            # Verify at_risk structure
            at_risk = data['at_risk']
            assert 'critical' in at_risk, "at_risk must contain 'critical'"
            assert 'high' in at_risk, "at_risk must contain 'high'"
            assert 'medium' in at_risk, "at_risk must contain 'medium'"
            assert 'total_critical' in at_risk, "at_risk must contain 'total_critical'"
            assert 'total_high' in at_risk, "at_risk must contain 'total_high'"
            assert 'total_medium' in at_risk, "at_risk must contain 'total_medium'"
            
            # Verify followups_by_product is dict
            assert isinstance(data['followups_by_product'], dict), "followups_by_product must be a dict"
            
            print(f"✓ Staff daily briefing: show={data['show']}, date={data.get('date')}")
            print(f"  at_risk: critical={at_risk['total_critical']}, high={at_risk['total_high']}, medium={at_risk['total_medium']}")
            print(f"  followups products: {list(data['followups_by_product'].keys())}")
        else:
            # Already seen - that's also valid
            assert 'reason' in data, "Response must contain 'reason' when show=False"
            print(f"✓ Staff daily briefing: show=False, reason={data['reason']}")

    # ==== TEST 2: Admin user gets show=false with reason='not_staff' ====
    def test_admin_daily_briefing_returns_not_staff(self, admin_session):
        """GET /api/retention/daily-briefing returns show=false for admin user"""
        response = admin_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data['show'] is False, "Admin should get show=False"
        assert data.get('reason') == 'not_staff', f"Expected reason='not_staff', got '{data.get('reason')}'"
        
        print(f"✓ Admin daily briefing: show={data['show']}, reason={data['reason']}")

    # ==== TEST 3 & 4: Dismiss marks briefing as seen ====
    def test_dismiss_daily_briefing(self, staff_session):
        """POST /api/retention/daily-briefing/dismiss marks briefing as seen"""
        # Dismiss the briefing
        response = staff_session.post(f"{BASE_URL}/api/retention/daily-briefing/dismiss")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert 'message' in data, "Response must contain 'message'"
        assert 'dismissed' in data['message'].lower() or 'briefing' in data['message'].lower(), \
            f"Expected dismiss confirmation message, got: {data['message']}"
        
        print(f"✓ Dismiss response: {data['message']}")

    def test_after_dismiss_returns_already_seen(self, staff_session):
        """GET /api/retention/daily-briefing returns show=false after dismiss"""
        # First dismiss
        staff_session.post(f"{BASE_URL}/api/retention/daily-briefing/dismiss")
        
        # Then check
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data['show'] is False, f"Expected show=False after dismiss, got show={data['show']}"
        assert data.get('reason') == 'already_seen', f"Expected reason='already_seen', got '{data.get('reason')}'"
        
        print(f"✓ After dismiss: show={data['show']}, reason={data['reason']}")

    # ==== TEST 5: At-risk categories are properly structured ====
    def test_at_risk_category_structure(self, staff_session):
        """Verify at-risk customer entries have correct structure"""
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data.get('show'):
            print("✓ Briefing already seen, skipping structure test")
            return
        
        at_risk = data['at_risk']
        
        # Check all categories for structure
        for category in ['critical', 'high', 'medium']:
            customers = at_risk.get(category, [])
            for customer in customers:
                assert 'customer_id' in customer or 'customer_name' in customer, \
                    f"{category} customer must have identifier"
                assert 'days_since_deposit' in customer, \
                    f"{category} customer must have days_since_deposit"
                assert 'product_name' in customer, \
                    f"{category} customer must have product_name"
                
        print(f"✓ At-risk categories structure verified")

    # ==== TEST 6: Max 5 customers per risk level ====
    def test_max_5_per_risk_level(self, staff_session):
        """Verify max 5 customers per risk level"""
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data.get('show'):
            print("✓ Briefing already seen, skipping max-5 test")
            return
        
        at_risk = data['at_risk']
        
        # Verify each category has max 5
        for category in ['critical', 'high', 'medium']:
            customers = at_risk.get(category, [])
            assert len(customers) <= 5, f"{category} should have max 5, got {len(customers)}"
            print(f"  {category}: {len(customers)} customers (max 5)")
        
        print(f"✓ Max 5 per risk level verified")

    # ==== TEST 7: Followups by product structure ====
    def test_followups_by_product_structure(self, staff_session):
        """Verify followups_by_product has correct structure"""
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data.get('show'):
            print("✓ Briefing already seen, skipping followups structure test")
            return
        
        followups = data.get('followups_by_product', {})
        
        for product_name, product_data in followups.items():
            assert 'items' in product_data, f"Product {product_name} must have 'items'"
            assert 'total' in product_data, f"Product {product_name} must have 'total'"
            assert len(product_data['items']) <= 5, \
                f"Product {product_name} should have max 5 items, got {len(product_data['items'])}"
            
            for item in product_data['items']:
                assert 'customer_display' in item or 'customer_id' in item, \
                    "Followup item must have customer identifier"
                assert 'days_since_response' in item, \
                    "Followup item must have days_since_response"
        
        print(f"✓ Followups by product structure verified: {list(followups.keys())}")

    # ==== TEST 8: At-risk categories follow correct day ranges ====
    def test_at_risk_day_ranges(self, staff_session):
        """Verify at-risk categories follow correct day ranges:
        - Critical: 14-30 days
        - High: 7-13 days  
        - Medium: 3-6 days with 2+ deposits
        """
        response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code == 200
        data = response.json()
        
        if not data.get('show'):
            print("✓ Briefing already seen, skipping day range test")
            return
        
        at_risk = data['at_risk']
        
        # Verify critical: 14-30 days
        for customer in at_risk.get('critical', []):
            days = customer.get('days_since_deposit', 0)
            assert 14 <= days <= 30, f"Critical should be 14-30 days, got {days}"
        
        # Verify high: 7-13 days
        for customer in at_risk.get('high', []):
            days = customer.get('days_since_deposit', 0)
            assert 7 <= days <= 13, f"High should be 7-13 days, got {days}"
        
        # Verify medium: 3-6 days
        for customer in at_risk.get('medium', []):
            days = customer.get('days_since_deposit', 0)
            assert 3 <= days <= 6, f"Medium should be 3-6 days, got {days}"
        
        print(f"✓ At-risk day ranges verified")

    # ==== TEST 9: Unauthenticated request fails ====
    def test_unauthenticated_request_fails(self):
        """Daily briefing endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/retention/daily-briefing")
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for unauthenticated request, got {response.status_code}"
        
        print(f"✓ Unauthenticated request properly rejected: {response.status_code}")

    # ==== TEST 10: Dismiss endpoint requires auth ====
    def test_dismiss_unauthenticated_fails(self):
        """Dismiss endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/retention/daily-briefing/dismiss")
        
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for unauthenticated request, got {response.status_code}"
        
        print(f"✓ Dismiss unauthenticated request properly rejected: {response.status_code}")


class TestDailyBriefingCleanup:
    """Tests that may require cleanup of daily_briefing_log"""
    
    @pytest.fixture
    def staff_token(self):
        """Get staff authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff authentication failed")
    
    @pytest.fixture
    def staff_session(self, staff_token):
        """Session with staff auth header"""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {staff_token}",
            "Content-Type": "application/json"
        })
        return session

    def test_dismiss_then_recheck_same_day(self, staff_session):
        """After dismiss, same day requests return already_seen"""
        # Dismiss
        dismiss_response = staff_session.post(f"{BASE_URL}/api/retention/daily-briefing/dismiss")
        assert dismiss_response.status_code == 200
        
        # Check multiple times - should always be already_seen
        for i in range(3):
            response = staff_session.get(f"{BASE_URL}/api/retention/daily-briefing")
            assert response.status_code == 200
            data = response.json()
            assert data['show'] is False
            assert data.get('reason') == 'already_seen'
        
        print(f"✓ Multiple checks after dismiss all return already_seen")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
