"""
Comprehensive API Tests for CRM Pro v3.0.0 - Modular Routes Architecture
Tests all API endpoints after server.py refactoring from 3945 lines to 104 lines
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestAuthModule:
    """Test Authentication Routes (/api/auth/*)"""
    
    def test_admin_login_success(self):
        """Test admin login returns token and user info"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - user: {data['user']['name']}")
    
    def test_staff_login_success(self):
        """Test staff login returns token and user info"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == STAFF_EMAIL
        assert data["user"]["role"] == "staff"
        print(f"✓ Staff login successful - user: {data['user']['name']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_auth_me_endpoint(self):
        """Test /api/auth/me returns current user info"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["token"]
        
        # Get current user
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        print(f"✓ /api/auth/me returns correct user: {data['name']}")


class TestProductsModule:
    """Test Products Routes (/api/products/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_products(self, admin_token):
        """Test GET /api/products returns list of products"""
        response = requests.get(f"{BASE_URL}/api/products", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/products returned {len(data)} products")
    
    def test_staff_can_get_products(self, staff_token):
        """Test staff can also access products list"""
        response = requests.get(f"{BASE_URL}/api/products", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 200
        print("✓ Staff can access products list")


class TestDatabasesModule:
    """Test Databases/Records Routes (/api/databases/*, /api/download-requests/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_databases(self, admin_token):
        """Test GET /api/databases returns list of databases"""
        response = requests.get(f"{BASE_URL}/api/databases", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/databases returned {len(data)} databases")
    
    def test_get_download_requests(self, admin_token):
        """Test GET /api/download-requests returns list"""
        response = requests.get(f"{BASE_URL}/api/download-requests", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/download-requests returned {len(data)} requests")
    
    def test_get_reserved_members(self, admin_token):
        """Test GET /api/reserved-members returns list"""
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/reserved-members returned {len(data)} members")


class TestOmsetModule:
    """Test OMSET CRM Routes (/api/omset/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_omset_records(self, admin_token):
        """Test GET /api/omset returns list of records"""
        response = requests.get(f"{BASE_URL}/api/omset", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/omset returned {len(data)} records")
    
    def test_get_omset_summary(self, admin_token):
        """Test GET /api/omset/summary returns summary data"""
        response = requests.get(f"{BASE_URL}/api/omset/summary", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "daily" in data
        assert "by_staff" in data
        assert "by_product" in data
        print(f"✓ GET /api/omset/summary returned summary with {data['total']['total_records']} records")
    
    def test_get_omset_dates(self, admin_token):
        """Test GET /api/omset/dates returns list of dates"""
        response = requests.get(f"{BASE_URL}/api/omset/dates", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/omset/dates returned {len(data)} dates")


class TestReportCRMModule:
    """Test Report CRM Routes (/api/report-crm/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_report_crm_data(self, admin_token):
        """Test GET /api/report-crm/data returns comprehensive report"""
        response = requests.get(f"{BASE_URL}/api/report-crm/data", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "yearly" in data
        assert "monthly" in data
        assert "monthly_by_staff" in data
        assert "daily" in data
        assert "staff_performance" in data
        print(f"✓ GET /api/report-crm/data returned comprehensive report")
    
    def test_report_crm_requires_admin(self):
        """Test /api/report-crm/data requires admin access"""
        # Login as staff
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        staff_token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/report-crm/data", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 403
        print("✓ Report CRM correctly requires admin access")


class TestBonusCalculationModule:
    """Test Bonus Calculation Routes (/api/bonus-calculation/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_bonus_config(self, admin_token):
        """Test GET /api/bonus-calculation/config returns configuration"""
        response = requests.get(f"{BASE_URL}/api/bonus-calculation/config", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "main_tiers" in data
        assert "ndp_tiers" in data
        assert "rdp_tiers" in data
        print(f"✓ GET /api/bonus-calculation/config returned config with {len(data['main_tiers'])} main tiers")
    
    def test_get_bonus_data(self, admin_token):
        """Test GET /api/bonus-calculation/data returns bonus calculations"""
        response = requests.get(f"{BASE_URL}/api/bonus-calculation/data", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "month" in data
        assert "staff_bonuses" in data
        assert "grand_total" in data
        print(f"✓ GET /api/bonus-calculation/data returned data for {len(data['staff_bonuses'])} staff")


class TestLeaveModule:
    """Test Leave Request Routes (/api/leave/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_leave_balance(self, staff_token):
        """Test GET /api/leave/balance returns balance info"""
        response = requests.get(f"{BASE_URL}/api/leave/balance", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "total_hours" in data
        assert "used_hours" in data
        assert "remaining_hours" in data
        assert data["total_hours"] == 24  # Monthly limit
        print(f"✓ GET /api/leave/balance returned balance: {data['remaining_hours']}/{data['total_hours']} hours")
    
    def test_get_all_leave_requests_admin(self, admin_token):
        """Test GET /api/leave/all-requests (admin only)"""
        response = requests.get(f"{BASE_URL}/api/leave/all-requests", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "pending_count" in data
        print(f"✓ GET /api/leave/all-requests returned {len(data['requests'])} requests")


class TestIzinModule:
    """Test Izin (Break) Routes (/api/izin/*)"""
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_izin_status(self, staff_token):
        """Test GET /api/izin/status returns current status"""
        response = requests.get(f"{BASE_URL}/api/izin/status", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "is_on_break" in data
        assert "total_minutes_used" in data
        assert "remaining_minutes" in data
        assert "daily_limit" in data
        print(f"✓ GET /api/izin/status returned status: on_break={data['is_on_break']}, used={data['total_minutes_used']}min")
    
    def test_get_izin_today(self, staff_token):
        """Test GET /api/izin/today returns today's records"""
        response = requests.get(f"{BASE_URL}/api/izin/today", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "records" in data
        assert "total_minutes" in data
        assert "daily_limit" in data
        print(f"✓ GET /api/izin/today returned {len(data['records'])} records")


class TestNotificationsModule:
    """Test Notifications Routes (/api/notifications/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_notifications(self, admin_token):
        """Test GET /api/notifications returns notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        print(f"✓ GET /api/notifications returned {len(data['notifications'])} notifications, {data['unread_count']} unread")


class TestAnalyticsModule:
    """Test Analytics Routes (/api/analytics/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_staff_performance(self, admin_token):
        """Test GET /api/analytics/staff-performance returns analytics"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "summary" in data
        assert "staff_metrics" in data
        print(f"✓ GET /api/analytics/staff-performance returned data for {len(data['staff_metrics'])} staff")
    
    def test_analytics_requires_admin(self):
        """Test analytics endpoints require admin access"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        staff_token = login_resp.json()["token"]
        
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance", headers={
            "Authorization": f"Bearer {staff_token}"
        })
        assert response.status_code == 403
        print("✓ Analytics correctly requires admin access")


class TestBonanzaModule:
    """Test DB Bonanza Routes (/api/bonanza/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_bonanza_databases(self, admin_token):
        """Test GET /api/bonanza/databases returns list"""
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/bonanza/databases returned {len(data)} databases")


class TestMemberWDModule:
    """Test Member WD CRM Routes (/api/memberwd/*)"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_memberwd_databases(self, admin_token):
        """Test GET /api/memberwd/databases returns list"""
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/memberwd/databases returned {len(data)} databases")


class TestServerTimeEndpoint:
    """Test Core Server Endpoint"""
    
    def test_server_time(self):
        """Test GET /api/server-time returns Jakarta time"""
        response = requests.get(f"{BASE_URL}/api/server-time")
        assert response.status_code == 200
        data = response.json()
        assert "timezone" in data
        assert "datetime" in data
        assert "date" in data
        assert "Asia/Jakarta" in data["timezone"]
        print(f"✓ GET /api/server-time returned: {data['formatted']}")


class TestUserPreferencesModule:
    """Test User Preferences Routes"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_widget_layout(self, admin_token):
        """Test GET /api/user/preferences/widget-layout"""
        response = requests.get(f"{BASE_URL}/api/user/preferences/widget-layout", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "widget_order" in data
        print(f"✓ GET /api/user/preferences/widget-layout returned layout")
    
    def test_get_sidebar_config(self, admin_token):
        """Test GET /api/user/preferences/sidebar-config"""
        response = requests.get(f"{BASE_URL}/api/user/preferences/sidebar-config", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        print(f"✓ GET /api/user/preferences/sidebar-config returned config")


class TestStaffUsersEndpoint:
    """Test Staff Users Endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_staff_users(self, admin_token):
        """Test GET /api/staff-users returns staff list"""
        response = requests.get(f"{BASE_URL}/api/staff-users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/staff-users returned {len(data)} staff members")


class TestLeaveCalendar:
    """Test Leave Calendar Endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_leave_calendar(self, admin_token):
        """Test GET /api/leave/calendar returns calendar data"""
        response = requests.get(f"{BASE_URL}/api/leave/calendar", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "month" in data
        assert "calendar_data" in data
        assert "staff_list" in data
        print(f"✓ GET /api/leave/calendar returned calendar for {data['year']}-{data['month']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
