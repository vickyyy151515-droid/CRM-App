"""
Comprehensive tests for CRM Pro new features:
- Daily Summary with Product Breakdown
- Conversion Funnel
- Customer Retention with At-Risk Alerts
- Global Search
- Leaderboard
- Dark Mode (frontend only)
- Sidebar Configuration
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        return data["token"]
    
    def test_staff_login(self):
        """Test staff login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "staff"
        return data["token"]


class TestDailySummary:
    """Daily Summary API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        return response.json()["token"]
    
    def test_get_daily_summary_admin(self, admin_token):
        """Test daily summary endpoint for admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/daily-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Admin should see team data
        assert "total_omset" in data or data is None or "staff_breakdown" in data or data == {}
    
    def test_get_daily_summary_staff(self, staff_token):
        """Test daily summary endpoint for staff"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/daily-summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Staff should see their own data
        assert data is None or "my_stats" in data or data == {}
    
    def test_get_daily_summary_history(self, admin_token):
        """Test daily summary history endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/daily-summary/history?days=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestConversionFunnel:
    """Conversion Funnel API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        return response.json()["token"]
    
    def test_get_funnel_overview(self, admin_token):
        """Test conversion funnel overview"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/funnel", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "date_range" in data
        assert "overall_conversion" in data
    
    def test_get_funnel_by_product(self, admin_token):
        """Test conversion funnel by product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/funnel/by-product", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "date_range" in data
    
    def test_get_funnel_by_staff_admin_only(self, admin_token, staff_token):
        """Test conversion funnel by staff (admin only)"""
        # Admin should have access
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/funnel/by-staff", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "staff" in data
        
        # Staff should get 403
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/funnel/by-staff", headers=headers)
        assert response.status_code == 403
    
    def test_get_funnel_trend(self, admin_token):
        """Test conversion funnel trend"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/funnel/trend?days=7", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "trend" in data
        assert "current_funnel" in data


class TestCustomerRetention:
    """Customer Retention API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        return response.json()["token"]
    
    def test_get_retention_overview(self, admin_token):
        """Test retention overview endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "date_range" in data
        assert "total_customers" in data
        assert "ndp_customers" in data
        assert "rdp_customers" in data
        assert "retention_rate" in data
    
    def test_get_retention_customers(self, admin_token):
        """Test retention customers list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/customers", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "customers" in data
        assert "total" in data
    
    def test_get_retention_customers_filtered(self, admin_token):
        """Test retention customers with filters"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Test NDP filter
        response = requests.get(f"{BASE_URL}/api/retention/customers?filter_type=ndp", headers=headers)
        assert response.status_code == 200
        
        # Test RDP filter
        response = requests.get(f"{BASE_URL}/api/retention/customers?filter_type=rdp", headers=headers)
        assert response.status_code == 200
        
        # Test loyal filter
        response = requests.get(f"{BASE_URL}/api/retention/customers?filter_type=loyal", headers=headers)
        assert response.status_code == 200
    
    def test_get_retention_trend(self, admin_token):
        """Test retention trend endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/trend?days=30", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "trend" in data
        assert "summary" in data
    
    def test_get_retention_by_product(self, admin_token):
        """Test retention by product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/by-product", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
    
    def test_get_retention_by_staff_admin_only(self, admin_token, staff_token):
        """Test retention by staff (admin only)"""
        # Admin should have access
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/by-staff", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "staff" in data
        
        # Staff should get 403
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/by-staff", headers=headers)
        assert response.status_code == 403
    
    def test_get_retention_alerts(self, admin_token):
        """Test at-risk customer alerts"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "alerts" in data
        # Check summary structure
        assert "critical" in data["summary"]
        assert "high" in data["summary"]
        assert "medium" in data["summary"]
        assert "total" in data["summary"]
    
    def test_get_alerts_by_staff_admin_only(self, admin_token, staff_token):
        """Test alerts by staff (admin only)"""
        # Admin should have access
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts/by-staff", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "staff" in data
        
        # Staff should get 403
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts/by-staff", headers=headers)
        assert response.status_code == 403


class TestGlobalSearch:
    """Global Search API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        return response.json()["token"]
    
    def test_search_basic(self, admin_token):
        """Test basic search functionality"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/search?q=test", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should return search results structure
        assert "total" in data
    
    def test_search_empty_query(self, admin_token):
        """Test search with empty query"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/search?q=", headers=headers)
        # Should return 200 with empty results or 400
        assert response.status_code in [200, 400]
    
    def test_search_staff_access(self, staff_token):
        """Test search for staff user"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/search?q=customer", headers=headers)
        assert response.status_code == 200


class TestLeaderboard:
    """Leaderboard API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    @pytest.fixture
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        return response.json()["token"]
    
    def test_get_leaderboard(self, admin_token):
        """Test leaderboard endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/leaderboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "period" in data
    
    def test_get_leaderboard_with_period(self, admin_token):
        """Test leaderboard with different periods"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test daily
        response = requests.get(f"{BASE_URL}/api/leaderboard?period=daily", headers=headers)
        assert response.status_code == 200
        
        # Test weekly
        response = requests.get(f"{BASE_URL}/api/leaderboard?period=weekly", headers=headers)
        assert response.status_code == 200
        
        # Test monthly
        response = requests.get(f"{BASE_URL}/api/leaderboard?period=monthly", headers=headers)
        assert response.status_code == 200
    
    def test_get_leaderboard_targets(self, admin_token):
        """Test leaderboard targets endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/leaderboard/targets", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "targets" in data
    
    def test_staff_can_access_leaderboard(self, staff_token):
        """Test staff can access leaderboard"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/leaderboard", headers=headers)
        assert response.status_code == 200


class TestSidebarConfig:
    """Sidebar Configuration API tests"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_get_sidebar_config(self, admin_token):
        """Test get sidebar configuration"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/user/preferences/sidebar-config", headers=headers)
        assert response.status_code == 200
    
    def test_save_sidebar_config(self, admin_token):
        """Test save sidebar configuration"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        config = {
            "items": [
                {"type": "item", "id": "overview", "label": "Overview"},
                {"type": "item", "id": "leaderboard", "label": "Leaderboard"}
            ]
        }
        response = requests.put(f"{BASE_URL}/api/user/preferences/sidebar-config", 
                               headers=headers, json=config)
        assert response.status_code == 200


class TestExistingEndpoints:
    """Test existing endpoints still work after new features"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        return response.json()["token"]
    
    def test_products_endpoint(self, admin_token):
        """Test products endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200
    
    def test_databases_endpoint(self, admin_token):
        """Test databases endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/databases", headers=headers)
        assert response.status_code == 200
    
    def test_omset_endpoint(self, admin_token):
        """Test OMSET endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/omset", headers=headers)
        assert response.status_code == 200
    
    def test_report_crm_endpoint(self, admin_token):
        """Test Report CRM endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/report-crm/data", headers=headers)
        assert response.status_code == 200
    
    def test_server_time_endpoint(self, admin_token):
        """Test server time endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/server-time", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "timezone" in data
        assert "datetime" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
