"""
Test Staff Offline Alerts Feature
Tests the new Staff Offline Alerts functionality for CRM scheduled reports
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStaffOfflineAlerts:
    """Staff Offline Alerts endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_config_returns_staff_offline_fields(self):
        """Test GET /api/scheduled-reports/config returns staff_offline fields"""
        response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Data assertions - validate staff_offline fields exist
        data = response.json()
        assert "staff_offline_enabled" in data, "staff_offline_enabled field missing"
        assert "staff_offline_hour" in data, "staff_offline_hour field missing"
        assert "staff_offline_minute" in data, "staff_offline_minute field missing"
        
        # Validate field types
        assert isinstance(data["staff_offline_enabled"], bool), "staff_offline_enabled should be boolean"
        assert isinstance(data["staff_offline_hour"], int), "staff_offline_hour should be integer"
        assert isinstance(data["staff_offline_minute"], int), "staff_offline_minute should be integer"
        
        # Validate hour/minute ranges
        assert 0 <= data["staff_offline_hour"] <= 23, "staff_offline_hour should be 0-23"
        assert data["staff_offline_minute"] in [0, 15, 30, 45], "staff_offline_minute should be 0, 15, 30, or 45"
    
    def test_save_staff_offline_config(self):
        """Test POST /api/scheduled-reports/staff-offline-config saves configuration"""
        # Save new config
        save_response = self.session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-config", json={
            "enabled": True,
            "alert_hour": 10,
            "alert_minute": 15
        })
        
        # Status assertion
        assert save_response.status_code == 200, f"Expected 200, got {save_response.status_code}"
        
        # Data assertions
        save_data = save_response.json()
        assert save_data.get("success") == True, "Expected success: true"
        assert "message" in save_data, "Expected message in response"
        
        # Verify config was persisted by fetching it
        get_response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        assert get_response.status_code == 200
        
        config_data = get_response.json()
        assert config_data["staff_offline_enabled"] == True, "staff_offline_enabled should be True"
        assert config_data["staff_offline_hour"] == 10, "staff_offline_hour should be 10"
        assert config_data["staff_offline_minute"] == 15, "staff_offline_minute should be 15"
    
    def test_disable_staff_offline_alerts(self):
        """Test disabling staff offline alerts"""
        # Disable alerts
        save_response = self.session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-config", json={
            "enabled": False,
            "alert_hour": 11,
            "alert_minute": 0
        })
        
        assert save_response.status_code == 200
        
        # Verify disabled
        get_response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        config_data = get_response.json()
        assert config_data["staff_offline_enabled"] == False, "staff_offline_enabled should be False"
    
    def test_send_staff_offline_alert_now(self):
        """Test POST /api/scheduled-reports/staff-offline-send-now sends alert to Telegram"""
        # First ensure config is set up (enable alerts)
        self.session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-config", json={
            "enabled": True,
            "alert_hour": 11,
            "alert_minute": 0
        })
        
        # Send alert now
        response = self.session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-send-now")
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert data.get("success") == True, "Expected success: true"
        assert "message" in data, "Expected message in response"
        assert "sent successfully" in data["message"].lower(), "Expected success message"
    
    def test_send_staff_offline_alert_updates_last_sent(self):
        """Test that sending alert updates staff_offline_last_sent timestamp"""
        # Get initial config
        initial_response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        initial_last_sent = initial_response.json().get("staff_offline_last_sent")
        
        # Send alert
        send_response = self.session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-send-now")
        assert send_response.status_code == 200
        
        # Get updated config
        updated_response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        updated_last_sent = updated_response.json().get("staff_offline_last_sent")
        
        # Verify timestamp was updated
        assert updated_last_sent is not None, "staff_offline_last_sent should be set"
        if initial_last_sent:
            assert updated_last_sent != initial_last_sent, "staff_offline_last_sent should be updated"
    
    def test_staff_offline_config_requires_auth(self):
        """Test that staff offline endpoints require authentication"""
        # Create new session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        # Test config endpoint
        response = unauth_session.get(f"{BASE_URL}/api/scheduled-reports/config")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Test save config endpoint
        response = unauth_session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-config", json={
            "enabled": True,
            "alert_hour": 11,
            "alert_minute": 0
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Test send now endpoint
        response = unauth_session.post(f"{BASE_URL}/api/scheduled-reports/staff-offline-send-now")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
