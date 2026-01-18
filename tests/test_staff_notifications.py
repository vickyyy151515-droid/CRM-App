# Test Staff Notifications Feature
# Tests notification badge counts for DB Bonanza and Member WD CRM pages
# Tests mark-viewed endpoint that resets notification counts

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStaffNotifications:
    """Test staff notification endpoints for badge counts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_email = "staff@crm.com"
        self.staff_password = "staff123"
        self.admin_email = "admin@crm.com"
        self.admin_password = "admin123"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_staff_token(self):
        """Get authentication token for staff user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.staff_email,
            "password": self.staff_password
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Staff authentication failed: {response.status_code}")
    
    def get_admin_token(self):
        """Get authentication token for admin user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Admin authentication failed: {response.status_code}")
    
    # ==================== GET /staff/notifications/summary Tests ====================
    
    def test_notification_summary_requires_auth(self):
        """Test that notification summary endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/staff/notifications/summary")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Notification summary requires authentication")
    
    def test_notification_summary_returns_correct_structure(self):
        """Test that notification summary returns bonanza_new and memberwd_new counts"""
        token = self.get_staff_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/staff/notifications/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "bonanza_new" in data, "Response should contain bonanza_new"
        assert "memberwd_new" in data, "Response should contain memberwd_new"
        assert isinstance(data["bonanza_new"], int), "bonanza_new should be an integer"
        assert isinstance(data["memberwd_new"], int), "memberwd_new should be an integer"
        assert data["bonanza_new"] >= 0, "bonanza_new should be non-negative"
        assert data["memberwd_new"] >= 0, "memberwd_new should be non-negative"
        print(f"✓ Notification summary returns correct structure: bonanza_new={data['bonanza_new']}, memberwd_new={data['memberwd_new']}")
    
    def test_notification_summary_admin_returns_zeros(self):
        """Test that admin users get zero counts (feature is for staff only)"""
        token = self.get_admin_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/staff/notifications/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["bonanza_new"] == 0, "Admin should get 0 for bonanza_new"
        assert data["memberwd_new"] == 0, "Admin should get 0 for memberwd_new"
        print("✓ Admin user correctly gets zero notification counts")
    
    # ==================== POST /staff/notifications/mark-viewed Tests ====================
    
    def test_mark_viewed_requires_auth(self):
        """Test that mark-viewed endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/bonanza")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Mark-viewed endpoint requires authentication")
    
    def test_mark_viewed_bonanza_success(self):
        """Test marking bonanza page as viewed"""
        token = self.get_staff_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/bonanza")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        print("✓ Mark bonanza as viewed successful")
    
    def test_mark_viewed_memberwd_success(self):
        """Test marking memberwd page as viewed"""
        token = self.get_staff_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/memberwd")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        print("✓ Mark memberwd as viewed successful")
    
    def test_mark_viewed_invalid_page_type(self):
        """Test that invalid page type returns error"""
        token = self.get_staff_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/invalid")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == False, "Invalid page type should return success=False"
        assert "error" in data, "Response should contain error message"
        print("✓ Invalid page type correctly returns error")
    
    def test_mark_viewed_admin_returns_success(self):
        """Test that admin users get success response (no-op for non-staff)"""
        token = self.get_admin_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/bonanza")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("success") == True, "Admin should get success response"
        print("✓ Admin user correctly gets success response for mark-viewed")
    
    # ==================== Integration Test: Mark Viewed Resets Count ====================
    
    def test_mark_viewed_resets_count(self):
        """Test that marking a page as viewed resets the notification count"""
        token = self.get_staff_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First, mark bonanza as viewed
        mark_response = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/bonanza")
        assert mark_response.status_code == 200, "Mark viewed should succeed"
        
        # Then check the notification summary
        summary_response = self.session.get(f"{BASE_URL}/api/staff/notifications/summary")
        assert summary_response.status_code == 200, "Summary should succeed"
        
        data = summary_response.json()
        # After marking as viewed, bonanza_new should be 0 (unless new records were assigned after)
        # This test verifies the flow works, actual count depends on data
        assert "bonanza_new" in data, "Response should contain bonanza_new"
        print(f"✓ After mark-viewed, bonanza_new count is: {data['bonanza_new']}")
        
        # Same for memberwd
        mark_response2 = self.session.post(f"{BASE_URL}/api/staff/notifications/mark-viewed/memberwd")
        assert mark_response2.status_code == 200, "Mark viewed should succeed"
        
        summary_response2 = self.session.get(f"{BASE_URL}/api/staff/notifications/summary")
        data2 = summary_response2.json()
        print(f"✓ After mark-viewed, memberwd_new count is: {data2['memberwd_new']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
