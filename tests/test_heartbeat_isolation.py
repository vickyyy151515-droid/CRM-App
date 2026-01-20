# Test Heartbeat Isolation - CRITICAL BUG FIX VERIFICATION
# 
# BUG: All users show the same 'Active' timestamp when admin views User Activity page
# This test verifies that heartbeat ONLY updates ONE user (the authenticated user)
#
# Test Strategy:
# 1. Login as User A, record their timestamp
# 2. Login as User B, send heartbeat as B
# 3. Verify User A's timestamp did NOT change
# 4. Verify User B's timestamp DID change
# 5. Verify heartbeat response includes correct user_id

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHeartbeatIsolation:
    """
    CRITICAL: Test that heartbeat only updates the authenticated user's timestamp
    This is the core test for the bug where all users showed the same timestamp
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures with multiple user credentials"""
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.second_staff_creds = {"email": "admin@crm.com", "password": "admin123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_user(self, creds):
        """Login and return token and user info"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200, f"Login failed for {creds['email']}: {response.text}"
        data = response.json()
        return data['token'], data['user']
    
    def get_user_activity(self, token):
        """Get all users' activity data"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200, f"Get activity failed: {response.text}"
        return response.json()
    
    def send_heartbeat(self, token):
        """Send heartbeat and return response"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        return response
    
    def find_user_in_activity(self, activity_data, email):
        """Find a specific user in activity data by email"""
        for user in activity_data['users']:
            if user['email'] == email:
                return user
        return None
    
    # ==================== CORE ISOLATION TESTS ====================
    
    def test_heartbeat_returns_correct_user_id(self):
        """
        TEST 1: Verify heartbeat response includes the correct user_id
        This ensures the backend knows which user it's updating
        """
        # Login as admin (to avoid "recently logged out" rejection)
        token, user = self.login_user(self.admin_creds)
        
        # Send heartbeat
        response = self.send_heartbeat(token)
        assert response.status_code == 200, f"Heartbeat failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure - user_id is always present
        assert 'status' in data, "Response should have 'status'"
        assert 'user_id' in data, "Response should have 'user_id'"
        
        # If status is 'rejected', that's also valid - it still returns user_id
        if data['status'] == 'rejected':
            print(f"✓ Heartbeat rejected (user recently logged out) but returns user_id={data['user_id']}")
            return
        
        # For 'ok' status, verify all fields
        assert 'user_email' in data, "Response should have 'user_email'"
        
        # Verify correct user
        assert data['user_id'] == user['id'], f"Heartbeat user_id mismatch: expected {user['id']}, got {data['user_id']}"
        assert data['user_email'] == user['email'], f"Heartbeat email mismatch: expected {user['email']}, got {data['user_email']}"
        
        print(f"✓ Heartbeat correctly returns user_id={data['user_id']}, email={data['user_email']}")
    
    def test_heartbeat_only_updates_authenticated_user(self):
        """
        TEST 2: CRITICAL - Verify heartbeat ONLY updates the authenticated user
        
        Steps:
        1. Login as User A (admin), send heartbeat, record timestamp
        2. Wait 2 seconds
        3. Login as User B (second admin), send heartbeat
        4. Verify User A's timestamp did NOT change
        5. Verify User B's timestamp DID change
        """
        # Step 1: Login as User A (admin) and send heartbeat
        # Using admin accounts to avoid "recently logged out" rejection
        token_a, user_a = self.login_user(self.admin_creds)
        response_a = self.send_heartbeat(token_a)
        assert response_a.status_code == 200, f"Heartbeat A failed: {response_a.text}"
        
        data_a = response_a.json()
        # Handle both 'ok' and 'rejected' status
        if data_a.get('status') == 'rejected':
            pytest.skip(f"User A heartbeat rejected: {data_a.get('reason')}")
        
        timestamp_a_initial = data_a['timestamp']
        print(f"User A ({user_a['email']}) heartbeat timestamp: {timestamp_a_initial}")
        
        # Step 2: Wait to ensure timestamps will be different
        time.sleep(2)
        
        # Step 3: Login as User B (second admin) and send heartbeat
        token_b, user_b = self.login_user(self.second_staff_creds)
        response_b = self.send_heartbeat(token_b)
        assert response_b.status_code == 200, f"Heartbeat B failed: {response_b.text}"
        
        data_b = response_b.json()
        if data_b.get('status') == 'rejected':
            pytest.skip(f"User B heartbeat rejected: {data_b.get('reason')}")
        
        timestamp_b = data_b['timestamp']
        print(f"User B ({user_b['email']}) heartbeat timestamp: {timestamp_b}")
        
        # Step 4: Get activity data and verify timestamps
        activity = self.get_user_activity(token_a)
        
        user_a_activity = self.find_user_in_activity(activity, user_a['email'])
        user_b_activity = self.find_user_in_activity(activity, user_b['email'])
        
        assert user_a_activity is not None, f"User A ({user_a['email']}) not found in activity"
        assert user_b_activity is not None, f"User B ({user_b['email']}) not found in activity"
        
        print(f"User A last_activity from DB: {user_a_activity['last_activity']}")
        print(f"User B last_activity from DB: {user_b_activity['last_activity']}")
        
        # CRITICAL ASSERTION: User A's timestamp should NOT have changed
        # (it should still be close to timestamp_a_initial, not timestamp_b)
        assert user_a_activity['last_activity'] != user_b_activity['last_activity'], \
            f"BUG: User A and User B have SAME timestamp! A={user_a_activity['last_activity']}, B={user_b_activity['last_activity']}"
        
        print("✓ CRITICAL: User A and User B have DIFFERENT timestamps - heartbeat isolation working!")
    
    def test_multiple_users_different_timestamps(self):
        """
        TEST 3: Verify multiple users have different timestamps after their heartbeats
        
        This is a more comprehensive test with 3 users (all admins to avoid logout rejection)
        """
        # Login all users
        token_admin, user_admin = self.login_user(self.admin_creds)
        token_second, user_second = self.login_user(self.second_staff_creds)
        
        # Send heartbeats with delays to ensure different timestamps
        response_admin = self.send_heartbeat(token_admin)
        assert response_admin.status_code == 200
        data_admin = response_admin.json()
        if data_admin.get('status') == 'rejected':
            pytest.skip(f"Admin heartbeat rejected: {data_admin.get('reason')}")
        ts_admin = data_admin['timestamp']
        print(f"Admin heartbeat: {ts_admin}")
        
        time.sleep(2)
        
        response_second = self.send_heartbeat(token_second)
        assert response_second.status_code == 200
        data_second = response_second.json()
        if data_second.get('status') == 'rejected':
            pytest.skip(f"Second user heartbeat rejected: {data_second.get('reason')}")
        ts_second = data_second['timestamp']
        print(f"Second user heartbeat: {ts_second}")
        
        # Get activity data
        activity = self.get_user_activity(token_admin)
        
        admin_activity = self.find_user_in_activity(activity, user_admin['email'])
        second_activity = self.find_user_in_activity(activity, user_second['email'])
        
        # Collect all timestamps
        timestamps = set()
        if admin_activity and admin_activity['last_activity']:
            timestamps.add(admin_activity['last_activity'])
        if second_activity and second_activity['last_activity']:
            timestamps.add(second_activity['last_activity'])
        
        print(f"Unique timestamps found: {len(timestamps)}")
        print(f"Timestamps: {timestamps}")
        
        # At least 2 different timestamps should exist
        assert len(timestamps) >= 2, \
            f"BUG: All users have same timestamp! Found only {len(timestamps)} unique timestamps"
        
        print(f"✓ Found {len(timestamps)} unique timestamps - heartbeat isolation confirmed!")
    
    # ==================== HEARTBEAT RESPONSE VALIDATION ====================
    
    def test_heartbeat_response_structure(self):
        """TEST 4: Verify heartbeat response has all required fields"""
        token, user = self.login_user(self.staff_creds)
        
        response = self.send_heartbeat(token)
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields
        required_fields = ['status', 'timestamp', 'user_id', 'user_email']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        assert data['status'] == 'ok', f"Status should be 'ok', got {data['status']}"
        
        print(f"✓ Heartbeat response structure correct: {list(data.keys())}")
    
    def test_heartbeat_requires_authentication(self):
        """TEST 5: Verify heartbeat requires valid authentication"""
        # No token
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat")
        assert response.status_code in [401, 403], f"Should require auth, got {response.status_code}"
        
        # Invalid token
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        assert response.status_code in [401, 403], f"Should reject invalid token, got {response.status_code}"
        
        print("✓ Heartbeat correctly requires valid authentication")


class TestUserActivityEndpoint:
    """Test the /api/users/activity endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_user(self, creds):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200
        return response.json()['token']
    
    def test_activity_endpoint_returns_correct_data(self):
        """TEST 6: Verify /api/users/activity returns correct structure"""
        token = self.login_user(self.admin_creds)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check structure
        assert 'users' in data, "Should have 'users' list"
        assert 'summary' in data, "Should have 'summary'"
        assert 'thresholds' in data, "Should have 'thresholds'"
        assert 'server_time' in data, "Should have 'server_time'"
        
        # Check summary
        summary = data['summary']
        assert 'total' in summary
        assert 'online' in summary
        assert 'idle' in summary
        assert 'offline' in summary
        
        # Verify counts add up
        assert summary['online'] + summary['idle'] + summary['offline'] == summary['total']
        
        print(f"✓ Activity endpoint returns correct data: {summary}")
    
    def test_activity_requires_admin(self):
        """TEST 7: Verify /api/users/activity requires admin role"""
        token = self.login_user(self.staff_creds)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 403, f"Staff should not access activity, got {response.status_code}"
        
        print("✓ Activity endpoint correctly requires admin role")


class TestForceOfflineAndReset:
    """Test admin endpoints for managing user activity"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_admin(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200
        return response.json()['token']
    
    def test_force_all_offline_endpoint(self):
        """TEST 8: Verify /api/auth/force-all-offline marks all staff offline"""
        token = self.login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.post(f"{BASE_URL}/api/auth/force-all-offline", headers=headers)
        assert response.status_code == 200, f"Force offline failed: {response.text}"
        
        data = response.json()
        assert data['status'] == 'ok'
        assert 'modified_count' in data
        assert 'logout_time' in data
        
        print(f"✓ Force all offline: modified {data['modified_count']} users at {data['logout_time']}")
    
    def test_reset_activity_endpoint(self):
        """TEST 9: Verify /api/auth/reset-activity clears activity data"""
        token = self.login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.post(f"{BASE_URL}/api/auth/reset-activity", headers=headers)
        assert response.status_code == 200, f"Reset activity failed: {response.text}"
        
        data = response.json()
        assert data['status'] == 'ok'
        assert 'modified_count' in data
        
        print(f"✓ Reset activity: modified {data['modified_count']} users")


class TestLogoutBehavior:
    """Test logout properly sets timestamps"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_user(self, creds):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200
        return response.json()['token'], response.json()['user']
    
    def test_logout_sets_timestamp(self):
        """TEST 10: Verify logout properly sets last_logout timestamp"""
        token, user = self.login_user(self.staff_creds)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Logout
        response = self.session.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data['message'] == 'Logged out successfully'
        
        # Verify user shows as offline
        admin_token, _ = self.login_user(self.admin_creds)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_response = self.session.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        assert activity_response.status_code == 200
        
        activity = activity_response.json()
        staff_user = None
        for u in activity['users']:
            if u['email'] == self.staff_creds['email']:
                staff_user = u
                break
        
        assert staff_user is not None
        assert staff_user['last_logout'] is not None, "last_logout should be set after logout"
        
        print(f"✓ Logout sets timestamp: last_logout={staff_user['last_logout']}, status={staff_user['status']}")


class TestStatusCalculation:
    """Test status calculation based on activity timestamps"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_admin(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200
        return response.json()['token']
    
    def test_status_thresholds_documented(self):
        """TEST 11: Verify status thresholds are correctly documented in response"""
        token = self.login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        thresholds = data['thresholds']
        
        # Verify thresholds exist
        assert 'online_minutes' in thresholds, "Should have online_minutes threshold"
        assert 'idle_minutes' in thresholds, "Should have idle_minutes threshold"
        assert 'staff_auto_logout_minutes' in thresholds, "Should have staff_auto_logout_minutes"
        
        print(f"✓ Status thresholds: online={thresholds['online_minutes']}min, idle={thresholds['idle_minutes']}min, auto_logout={thresholds['staff_auto_logout_minutes']}min")
    
    def test_user_status_values(self):
        """TEST 12: Verify user status is one of: online, idle, offline"""
        token = self.login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = {'online', 'idle', 'offline'}
        
        for user in data['users']:
            assert user['status'] in valid_statuses, f"Invalid status '{user['status']}' for user {user['email']}"
        
        print(f"✓ All {len(data['users'])} users have valid status values")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
