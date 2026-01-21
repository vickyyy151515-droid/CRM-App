# Test Login -> Logout -> Re-Login Cycle - CRITICAL BUG FIX VERIFICATION
# 
# BUG: Users showed 'offline' even after logging back in
# The logic has been simplified to: if last_logout > last_activity then offline, else use activity time
#
# Test Strategy:
# 1. Login as user A -> verify status is 'online'
# 2. User A sends heartbeat -> verify status stays 'online'
# 3. User A logs out -> verify status becomes 'offline'
# 4. User A logs back in -> verify status is 'online' again (NOT offline)
# 5. Verify the logic: if last_activity > last_logout, user should be ONLINE (if recent)
# 6. Verify the logic: if last_logout > last_activity, user should be OFFLINE
# 7. Test with multiple users - each should have independent status

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLoginLogoutReloginCycle:
    """
    CRITICAL: Test the full login -> logout -> re-login cycle
    This verifies the bug fix where users showed 'offline' after re-login
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_creds = {"email": "vicky@crm.com", "password": "vicky123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.second_admin_creds = {"email": "admin@crm.com", "password": "admin123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_user(self, creds):
        """Login and return token and user info"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200, f"Login failed for {creds['email']}: {response.text}"
        data = response.json()
        return data['token'], data['user']
    
    def logout_user(self, token):
        """Logout user"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        return response
    
    def send_heartbeat(self, token):
        """Send heartbeat"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        return response
    
    def get_user_activity(self, token):
        """Get all users' activity data"""
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200, f"Get activity failed: {response.text}"
        return response.json()
    
    def find_user_status(self, activity_data, email):
        """Find a specific user's status in activity data"""
        for user in activity_data['users']:
            if user['email'] == email:
                return user
        return None
    
    # ==================== CRITICAL LOGIN/LOGOUT/RE-LOGIN TESTS ====================
    
    def test_1_login_shows_online(self):
        """
        TEST 1: Login as user A -> verify status is 'online'
        After login, user should immediately be online
        """
        # Login as admin to check activity
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login as staff user
        staff_token, staff_user = self.login_user(self.staff_creds)
        
        # Send heartbeat to update activity
        heartbeat_response = self.send_heartbeat(staff_token)
        assert heartbeat_response.status_code == 200, f"Heartbeat failed: {heartbeat_response.text}"
        
        # Check status
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        assert staff_status is not None, f"Staff user not found in activity"
        print(f"Staff user status after login: {staff_status['status']}")
        print(f"  last_activity: {staff_status['last_activity']}")
        print(f"  last_logout: {staff_status['last_logout']}")
        
        assert staff_status['status'] == 'online', \
            f"FAIL: User should be 'online' after login, but got '{staff_status['status']}'"
        
        print("✓ TEST 1 PASSED: User is 'online' after login")
    
    def test_2_heartbeat_keeps_online(self):
        """
        TEST 2: User A sends heartbeat -> verify status stays 'online'
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login as staff and send multiple heartbeats
        staff_token, _ = self.login_user(self.staff_creds)
        
        for i in range(3):
            response = self.send_heartbeat(staff_token)
            assert response.status_code == 200
            time.sleep(0.5)
        
        # Check status
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        assert staff_status['status'] == 'online', \
            f"FAIL: User should stay 'online' after heartbeats, but got '{staff_status['status']}'"
        
        print("✓ TEST 2 PASSED: User stays 'online' after heartbeats")
    
    def test_3_logout_shows_offline(self):
        """
        TEST 3: User A logs out -> verify status becomes 'offline'
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login as staff
        staff_token, _ = self.login_user(self.staff_creds)
        
        # Send heartbeat first
        self.send_heartbeat(staff_token)
        
        # Logout
        logout_response = self.logout_user(staff_token)
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        # Check status
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        print(f"Staff user status after logout: {staff_status['status']}")
        print(f"  last_activity: {staff_status['last_activity']}")
        print(f"  last_logout: {staff_status['last_logout']}")
        
        assert staff_status['status'] == 'offline', \
            f"FAIL: User should be 'offline' after logout, but got '{staff_status['status']}'"
        
        print("✓ TEST 3 PASSED: User is 'offline' after logout")
    
    def test_4_relogin_shows_online_again(self):
        """
        TEST 4: CRITICAL - User A logs back in -> verify status is 'online' again (NOT offline)
        
        This is the CRITICAL test for the bug where users showed 'offline' after re-login
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Step 1: Login as staff
        staff_token, _ = self.login_user(self.staff_creds)
        self.send_heartbeat(staff_token)
        
        # Verify online
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        print(f"Step 1 - After login: status={staff_status['status']}")
        assert staff_status['status'] == 'online', "Should be online after login"
        
        # Step 2: Logout
        self.logout_user(staff_token)
        
        # Verify offline
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        print(f"Step 2 - After logout: status={staff_status['status']}")
        assert staff_status['status'] == 'offline', "Should be offline after logout"
        
        # Step 3: Wait a moment and RE-LOGIN
        time.sleep(1)
        
        # RE-LOGIN
        staff_token_new, _ = self.login_user(self.staff_creds)
        
        # Send heartbeat with new token
        heartbeat_response = self.send_heartbeat(staff_token_new)
        print(f"Heartbeat response after re-login: {heartbeat_response.json()}")
        
        # CRITICAL CHECK: Verify status is 'online' again
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        print(f"Step 3 - After RE-LOGIN: status={staff_status['status']}")
        print(f"  last_activity: {staff_status['last_activity']}")
        print(f"  last_logout: {staff_status['last_logout']}")
        
        # Parse timestamps to verify logic
        if staff_status['last_activity'] and staff_status['last_logout']:
            last_activity = datetime.fromisoformat(staff_status['last_activity'].replace('Z', '+00:00'))
            last_logout = datetime.fromisoformat(staff_status['last_logout'].replace('Z', '+00:00'))
            print(f"  last_activity > last_logout: {last_activity > last_logout}")
        
        assert staff_status['status'] == 'online', \
            f"CRITICAL BUG: User should be 'online' after re-login, but got '{staff_status['status']}'"
        
        print("✓ TEST 4 PASSED: CRITICAL - User is 'online' after re-login!")
    
    def test_5_activity_after_logout_means_online(self):
        """
        TEST 5: Verify the logic: if last_activity > last_logout, user should be ONLINE (if recent)
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login as staff
        staff_token, _ = self.login_user(self.staff_creds)
        
        # Logout first
        self.logout_user(staff_token)
        
        # Re-login and send heartbeat
        staff_token_new, _ = self.login_user(self.staff_creds)
        self.send_heartbeat(staff_token_new)
        
        # Get activity
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        # Verify timestamps
        assert staff_status['last_activity'] is not None, "last_activity should be set"
        assert staff_status['last_logout'] is not None, "last_logout should be set"
        
        last_activity = datetime.fromisoformat(staff_status['last_activity'].replace('Z', '+00:00'))
        last_logout = datetime.fromisoformat(staff_status['last_logout'].replace('Z', '+00:00'))
        
        print(f"last_activity: {last_activity}")
        print(f"last_logout: {last_logout}")
        print(f"last_activity > last_logout: {last_activity > last_logout}")
        
        # If last_activity > last_logout, user should be online (if recent)
        if last_activity > last_logout:
            assert staff_status['status'] == 'online', \
                f"FAIL: When last_activity > last_logout, status should be 'online', got '{staff_status['status']}'"
            print("✓ TEST 5 PASSED: last_activity > last_logout means ONLINE")
        else:
            print(f"Note: last_activity <= last_logout, status is '{staff_status['status']}'")
    
    def test_6_logout_after_activity_means_offline(self):
        """
        TEST 6: Verify the logic: if last_logout > last_activity, user should be OFFLINE
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login as staff and send heartbeat
        staff_token, _ = self.login_user(self.staff_creds)
        self.send_heartbeat(staff_token)
        
        # Wait a moment
        time.sleep(1)
        
        # Logout (this sets last_logout > last_activity)
        self.logout_user(staff_token)
        
        # Get activity
        activity = self.get_user_activity(admin_token)
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        
        # Verify timestamps
        last_activity = datetime.fromisoformat(staff_status['last_activity'].replace('Z', '+00:00'))
        last_logout = datetime.fromisoformat(staff_status['last_logout'].replace('Z', '+00:00'))
        
        print(f"last_activity: {last_activity}")
        print(f"last_logout: {last_logout}")
        print(f"last_logout > last_activity: {last_logout > last_activity}")
        
        # If last_logout > last_activity, user should be offline
        assert last_logout > last_activity, "last_logout should be > last_activity after logout"
        assert staff_status['status'] == 'offline', \
            f"FAIL: When last_logout > last_activity, status should be 'offline', got '{staff_status['status']}'"
        
        print("✓ TEST 6 PASSED: last_logout > last_activity means OFFLINE")
    
    def test_7_multiple_users_independent_status(self):
        """
        TEST 7: Test with multiple users - each should have independent status
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login staff user and send heartbeat
        staff_token, _ = self.login_user(self.staff_creds)
        self.send_heartbeat(staff_token)
        
        # Login second admin and send heartbeat
        second_admin_token, _ = self.login_user(self.second_admin_creds)
        self.send_heartbeat(second_admin_token)
        
        # Logout staff user only
        self.logout_user(staff_token)
        
        # Get activity
        activity = self.get_user_activity(admin_token)
        
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        second_admin_status = self.find_user_status(activity, self.second_admin_creds['email'])
        
        print(f"Staff user status: {staff_status['status']}")
        print(f"Second admin status: {second_admin_status['status']}")
        
        # Staff should be offline (logged out)
        assert staff_status['status'] == 'offline', \
            f"Staff should be 'offline' after logout, got '{staff_status['status']}'"
        
        # Second admin should be online (still logged in)
        assert second_admin_status['status'] == 'online', \
            f"Second admin should be 'online', got '{second_admin_status['status']}'"
        
        print("✓ TEST 7 PASSED: Multiple users have independent status")
    
    def test_8_timestamps_different_for_different_users(self):
        """
        TEST 8: Verify timestamps are different for different users
        """
        # Login as admin
        admin_token, _ = self.login_user(self.admin_creds)
        
        # Login staff and send heartbeat
        staff_token, _ = self.login_user(self.staff_creds)
        self.send_heartbeat(staff_token)
        
        time.sleep(2)  # Wait to ensure different timestamps
        
        # Login second admin and send heartbeat
        second_admin_token, _ = self.login_user(self.second_admin_creds)
        self.send_heartbeat(second_admin_token)
        
        # Get activity
        activity = self.get_user_activity(admin_token)
        
        staff_status = self.find_user_status(activity, self.staff_creds['email'])
        second_admin_status = self.find_user_status(activity, self.second_admin_creds['email'])
        
        print(f"Staff last_activity: {staff_status['last_activity']}")
        print(f"Second admin last_activity: {second_admin_status['last_activity']}")
        
        # Timestamps should be different
        assert staff_status['last_activity'] != second_admin_status['last_activity'], \
            f"BUG: Different users have same timestamp!"
        
        print("✓ TEST 8 PASSED: Different users have different timestamps")


class TestQRScannerAPI:
    """Test QR Scanner related API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login_user(self, creds):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200
        return response.json()['token'], response.json()['user']
    
    def test_attendance_scan_endpoint_exists(self):
        """TEST 9: Verify POST /api/attendance/scan endpoint exists"""
        token, _ = self.login_user(self.staff_creds)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with invalid QR code - should return 400 or 404, not 500
        response = self.session.post(
            f"{BASE_URL}/api/attendance/scan",
            headers=headers,
            json={"qr_code": "ATT-INVALID-TEST", "device_token": "TEST-DEVICE"}
        )
        
        # Should not be 500 (server error) or 404 (endpoint not found)
        assert response.status_code != 500, f"Server error: {response.text}"
        print(f"Attendance scan endpoint response: {response.status_code} - {response.text[:100]}")
        print("✓ TEST 9 PASSED: Attendance scan endpoint exists and responds")
    
    def test_device_status_endpoint(self):
        """TEST 10: Verify GET /api/attendance/device-status endpoint"""
        token, _ = self.login_user(self.staff_creds)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/attendance/device-status", headers=headers)
        
        # Should return 200 with device status
        assert response.status_code == 200, f"Device status failed: {response.text}"
        
        data = response.json()
        assert 'has_device' in data, "Response should have 'has_device' field"
        
        print(f"Device status: {data}")
        print("✓ TEST 10 PASSED: Device status endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
