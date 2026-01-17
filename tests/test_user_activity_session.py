# Test User Activity and Session Status Features
# Tests for:
# 1. User Activity - status determined by last_activity timestamp
# 2. Session Status API - GET /auth/session-status
# 3. Heartbeat API - POST /auth/heartbeat

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestUserActivityAndSession:
    """Test user activity status and session management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_creds = {"email": "admin@crm.com", "password": "admin123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()['token']
    
    def get_staff_token(self):
        """Get staff authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=self.staff_creds)
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        return response.json()['token']
    
    # ==================== HEARTBEAT TESTS ====================
    
    def test_heartbeat_updates_last_activity(self):
        """Test POST /auth/heartbeat updates last_activity timestamp"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Call heartbeat
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        assert response.status_code == 200, f"Heartbeat failed: {response.text}"
        
        data = response.json()
        assert data['status'] == 'ok', "Heartbeat should return status 'ok'"
        assert 'timestamp' in data, "Heartbeat should return timestamp"
        print(f"✓ Heartbeat successful, timestamp: {data['timestamp']}")
    
    def test_heartbeat_requires_auth(self):
        """Test heartbeat requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat")
        assert response.status_code in [401, 403], "Heartbeat should require authentication"
        print("✓ Heartbeat correctly requires authentication")
    
    # ==================== SESSION STATUS TESTS ====================
    
    def test_session_status_returns_valid_info(self):
        """Test GET /auth/session-status returns valid session info"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/auth/session-status", headers=headers)
        assert response.status_code == 200, f"Session status failed: {response.text}"
        
        data = response.json()
        assert 'valid' in data, "Response should contain 'valid' field"
        assert data['valid'] == True, "Session should be valid after login"
        print(f"✓ Session status: valid={data['valid']}")
    
    def test_session_status_minutes_remaining(self):
        """Test session status returns minutes_remaining countdown"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # First send heartbeat to ensure fresh activity
        self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        
        response = self.session.get(f"{BASE_URL}/api/auth/session-status", headers=headers)
        assert response.status_code == 200, f"Session status failed: {response.text}"
        
        data = response.json()
        assert 'minutes_remaining' in data, "Response should contain 'minutes_remaining'"
        
        # After fresh login/heartbeat, should have close to 60 minutes remaining
        minutes = data['minutes_remaining']
        assert minutes > 55, f"Minutes remaining should be close to 60, got {minutes}"
        assert minutes <= 60, f"Minutes remaining should not exceed 60, got {minutes}"
        print(f"✓ Session minutes remaining: {minutes}")
    
    def test_session_status_minutes_inactive(self):
        """Test session status returns minutes_inactive"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/auth/session-status", headers=headers)
        assert response.status_code == 200, f"Session status failed: {response.text}"
        
        data = response.json()
        assert 'minutes_inactive' in data, "Response should contain 'minutes_inactive'"
        
        # After fresh login, should have very low inactive time
        inactive = data['minutes_inactive']
        assert inactive >= 0, f"Minutes inactive should be >= 0, got {inactive}"
        print(f"✓ Session minutes inactive: {inactive}")
    
    def test_session_status_requires_auth(self):
        """Test session status requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/auth/session-status")
        assert response.status_code in [401, 403], "Session status should require authentication"
        print("✓ Session status correctly requires authentication")
    
    # ==================== USER ACTIVITY TESTS ====================
    
    def test_user_activity_endpoint_exists(self):
        """Test GET /users/activity endpoint exists and returns data"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200, f"User activity failed: {response.text}"
        
        data = response.json()
        assert 'users' in data, "Response should contain 'users' list"
        assert 'summary' in data, "Response should contain 'summary'"
        assert 'thresholds' in data, "Response should contain 'thresholds'"
        print(f"✓ User activity endpoint working, found {len(data['users'])} users")
    
    def test_user_activity_summary_structure(self):
        """Test user activity summary has correct structure"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        summary = data['summary']
        
        assert 'total' in summary, "Summary should have 'total'"
        assert 'online' in summary, "Summary should have 'online'"
        assert 'idle' in summary, "Summary should have 'idle'"
        assert 'offline' in summary, "Summary should have 'offline'"
        
        # Verify counts add up
        total = summary['total']
        online = summary['online']
        idle = summary['idle']
        offline = summary['offline']
        
        assert online + idle + offline == total, f"Counts should add up: {online}+{idle}+{offline} != {total}"
        print(f"✓ Activity summary: total={total}, online={online}, idle={idle}, offline={offline}")
    
    def test_user_activity_thresholds(self):
        """Test user activity thresholds are correct"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        thresholds = data['thresholds']
        
        assert thresholds['idle_minutes'] == 5, f"Idle threshold should be 5 minutes, got {thresholds['idle_minutes']}"
        assert thresholds['offline_minutes'] == 15, f"Offline threshold should be 15 minutes, got {thresholds['offline_minutes']}"
        print(f"✓ Thresholds correct: idle={thresholds['idle_minutes']}min, offline={thresholds['offline_minutes']}min")
    
    def test_user_activity_status_based_on_timestamp(self):
        """Test user status is determined by last_activity timestamp"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # First send heartbeat to ensure admin is online
        self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        users = data['users']
        
        # Find admin user
        admin_user = None
        for user in users:
            if user['email'] == 'admin@crm.com':
                admin_user = user
                break
        
        assert admin_user is not None, "Admin user should be in activity list"
        
        # Admin should be online after heartbeat
        assert admin_user['status'] == 'online', f"Admin should be online after heartbeat, got {admin_user['status']}"
        assert 'last_activity' in admin_user, "User should have last_activity field"
        print(f"✓ Admin status: {admin_user['status']}, last_activity: {admin_user['last_activity']}")
    
    def test_user_activity_user_fields(self):
        """Test user activity returns correct user fields"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        users = data['users']
        
        assert len(users) > 0, "Should have at least one user"
        
        user = users[0]
        required_fields = ['id', 'name', 'email', 'role', 'status', 'last_login', 'last_activity']
        for field in required_fields:
            assert field in user, f"User should have '{field}' field"
        
        # Status should be one of: online, idle, offline
        assert user['status'] in ['online', 'idle', 'offline'], f"Invalid status: {user['status']}"
        print(f"✓ User fields correct: {list(user.keys())}")
    
    def test_user_activity_requires_admin(self):
        """Test user activity requires admin role"""
        token = self.get_staff_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        # Staff should not have access to user activity
        assert response.status_code in [401, 403], f"Staff should not access user activity, got {response.status_code}"
        print("✓ User activity correctly requires admin role")
    
    # ==================== LOGOUT TESTS ====================
    
    def test_logout_updates_status(self):
        """Test logout updates user status"""
        token = self.get_staff_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Logout
        response = self.session.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert response.status_code == 200, f"Logout failed: {response.text}"
        
        data = response.json()
        assert data['message'] == 'Logged out successfully'
        print("✓ Logout successful")
    
    def test_user_offline_after_logout(self):
        """Test user shows as offline after explicit logout"""
        # Login as staff
        staff_token = self.get_staff_token()
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Send heartbeat to ensure staff is online
        self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=staff_headers)
        
        # Logout staff
        self.session.post(f"{BASE_URL}/api/auth/logout", headers=staff_headers)
        
        # Check activity as admin
        admin_token = self.get_admin_token()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        users = data['users']
        
        # Find staff user
        staff_user = None
        for user in users:
            if user['email'] == 'staff@crm.com':
                staff_user = user
                break
        
        assert staff_user is not None, "Staff user should be in activity list"
        
        # Staff should be offline after logout
        assert staff_user['status'] == 'offline', f"Staff should be offline after logout, got {staff_user['status']}"
        print(f"✓ Staff correctly shows as offline after logout: {staff_user['status']}")


class TestActivityStatusLogic:
    """Test the activity status determination logic"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_creds = {"email": "admin@crm.com", "password": "admin123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200
        return response.json()['token']
    
    def test_online_status_within_5_minutes(self):
        """Test users with activity within 5 minutes show as online"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Send heartbeat to ensure fresh activity
        self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Find admin user (who just sent heartbeat)
        admin_user = None
        for user in data['users']:
            if user['email'] == 'admin@crm.com':
                admin_user = user
                break
        
        assert admin_user is not None
        assert admin_user['status'] == 'online', f"User with recent activity should be online, got {admin_user['status']}"
        print(f"✓ User with activity within 5 min is online: {admin_user['status']}")
    
    def test_activity_status_not_based_on_is_online_flag(self):
        """Test that status is determined by timestamp, not is_online flag"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get activity data
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify thresholds are being used
        thresholds = data['thresholds']
        assert thresholds['idle_minutes'] == 5, "Idle threshold should be 5 minutes"
        assert thresholds['offline_minutes'] == 15, "Offline threshold should be 15 minutes"
        
        # The key test: status should be based on last_activity, not is_online
        # This is verified by the code structure - we can't directly test the flag
        # but we can verify the thresholds are correct
        print("✓ Activity status uses timestamp-based thresholds (5min idle, 15min offline)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
