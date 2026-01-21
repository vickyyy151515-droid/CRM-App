"""
User Activity Independence Tests

CRITICAL REQUIREMENT: Admin actions must NEVER affect staff status.
- Heartbeat only updates the authenticated user's own timestamp
- Activity page is READ-ONLY (no writes)
- Staff login/logout/re-login cycle works correctly
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@crm.com", "password": "admin123"}
STAFF_CREDS = {"email": "staff@crm.com", "password": "staff123"}
MASTER_ADMIN_CREDS = {"email": "vicky@crm.com", "password": "vicky123"}


class TestHeartbeatEndpoint:
    """Test POST /api/auth/heartbeat - updates ONLY the authenticated user's last_activity"""
    
    def test_heartbeat_requires_authentication(self):
        """Heartbeat should require valid authentication"""
        response = requests.post(f"{BASE_URL}/api/auth/heartbeat")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Heartbeat requires authentication")
    
    def test_heartbeat_returns_correct_user_id(self):
        """Heartbeat should return the authenticated user's ID"""
        # Login as staff
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        assert login_resp.status_code == 200
        token = login_resp.json()['token']
        user_id = login_resp.json()['user']['id']
        
        # Send heartbeat
        headers = {"Authorization": f"Bearer {token}"}
        heartbeat_resp = requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        assert heartbeat_resp.status_code == 200
        
        data = heartbeat_resp.json()
        assert data.get('user_id') == user_id, f"Expected user_id {user_id}, got {data.get('user_id')}"
        assert 'timestamp' in data
        print(f"✓ Heartbeat returns correct user_id: {user_id}")
    
    def test_heartbeat_response_structure(self):
        """Heartbeat should return status, user_id, and timestamp"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_resp.json()['token']
        
        headers = {"Authorization": f"Bearer {token}"}
        heartbeat_resp = requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        assert heartbeat_resp.status_code == 200
        
        data = heartbeat_resp.json()
        assert 'status' in data
        assert 'user_id' in data
        assert 'timestamp' in data
        print(f"✓ Heartbeat response structure correct: {list(data.keys())}")


class TestUserActivityEndpoint:
    """Test GET /api/users/activity - returns correct status for all users (READ-ONLY)"""
    
    def test_activity_endpoint_requires_admin(self):
        """Activity endpoint should require admin role"""
        # Try without auth
        response = requests.get(f"{BASE_URL}/api/users/activity")
        assert response.status_code in [401, 403]
        
        # Try with staff (should fail)
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        token = login_resp.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 403, f"Staff should not access activity endpoint, got {response.status_code}"
        print("✓ Activity endpoint requires admin role")
    
    def test_activity_endpoint_returns_correct_structure(self):
        """Activity endpoint should return users, summary, thresholds, server_time"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_resp.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/users/activity", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'users' in data
        assert 'summary' in data
        assert 'thresholds' in data
        assert 'server_time' in data
        
        # Check summary structure
        summary = data['summary']
        assert 'total' in summary
        assert 'online' in summary
        assert 'idle' in summary
        assert 'offline' in summary
        print(f"✓ Activity endpoint returns correct structure: summary={summary}")
    
    def test_activity_returns_user_fields(self):
        """Each user in activity list should have required fields"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_resp.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/users/activity", headers=headers)
        data = response.json()
        
        assert len(data['users']) > 0, "Should have at least one user"
        
        user = data['users'][0]
        required_fields = ['id', 'name', 'email', 'role', 'status']
        for field in required_fields:
            assert field in user, f"Missing field: {field}"
        
        # Status should be valid
        assert user['status'] in ['online', 'idle', 'offline'], f"Invalid status: {user['status']}"
        print(f"✓ User fields correct: {list(user.keys())}")
    
    def test_activity_thresholds_documented(self):
        """Activity endpoint should return threshold values"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = login_resp.json()['token']
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/users/activity", headers=headers)
        data = response.json()
        
        thresholds = data['thresholds']
        assert 'online_minutes' in thresholds
        assert 'idle_minutes' in thresholds
        assert 'offline_minutes' in thresholds
        print(f"✓ Thresholds documented: {thresholds}")


class TestLoginLogoutStatusCycle:
    """Test staff login -> status becomes 'online', logout -> 'offline', re-login -> 'online'"""
    
    def test_staff_login_sets_online(self):
        """Staff login should set status to 'online'"""
        # Login as staff
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        assert login_resp.status_code == 200
        staff_token = login_resp.json()['token']
        staff_id = login_resp.json()['user']['id']
        
        # Send heartbeat to ensure activity is updated
        headers = {"Authorization": f"Bearer {staff_token}"}
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=headers)
        
        # Check status via admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data = activity_resp.json()
        
        staff_user = next((u for u in data['users'] if u['id'] == staff_id), None)
        assert staff_user is not None, f"Staff user {staff_id} not found in activity list"
        assert staff_user['status'] == 'online', f"Expected 'online', got '{staff_user['status']}'"
        print(f"✓ Staff login sets status to 'online': {staff_user['name']}")
    
    def test_staff_logout_sets_offline(self):
        """Staff logout should set status to 'offline'"""
        # Login as staff
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        staff_token = login_resp.json()['token']
        staff_id = login_resp.json()['user']['id']
        
        # Logout
        headers = {"Authorization": f"Bearer {staff_token}"}
        logout_resp = requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert logout_resp.status_code == 200
        
        # Check status via admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data = activity_resp.json()
        
        staff_user = next((u for u in data['users'] if u['id'] == staff_id), None)
        assert staff_user is not None
        assert staff_user['status'] == 'offline', f"Expected 'offline' after logout, got '{staff_user['status']}'"
        print(f"✓ Staff logout sets status to 'offline'")
    
    def test_staff_relogin_sets_online_again(self):
        """Staff re-login after logout should set status back to 'online'"""
        # Login as staff
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        staff_token = login_resp.json()['token']
        staff_id = login_resp.json()['user']['id']
        
        # Logout
        headers = {"Authorization": f"Bearer {staff_token}"}
        requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        
        # Re-login
        relogin_resp = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        assert relogin_resp.status_code == 200
        new_token = relogin_resp.json()['token']
        
        # Send heartbeat with new token
        new_headers = {"Authorization": f"Bearer {new_token}"}
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=new_headers)
        
        # Check status via admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data = activity_resp.json()
        
        staff_user = next((u for u in data['users'] if u['id'] == staff_id), None)
        assert staff_user is not None
        assert staff_user['status'] == 'online', f"Expected 'online' after re-login, got '{staff_user['status']}'"
        print(f"✓ Staff re-login sets status back to 'online'")


class TestIndependenceRequirement:
    """
    CRITICAL TEST: Admin viewing activity page does NOT change staff's timestamp
    
    This is the most important test - admin actions must NEVER affect staff status.
    """
    
    def test_admin_viewing_activity_does_not_change_staff_timestamp(self):
        """
        INDEPENDENCE TEST: Admin viewing activity page multiple times should NOT change staff's last_activity
        """
        # Step 1: Login as staff and send heartbeat
        staff_login = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        assert staff_login.status_code == 200
        staff_token = staff_login.json()['token']
        staff_id = staff_login.json()['user']['id']
        
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=staff_headers)
        
        # Step 2: Login as admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Step 3: Get staff's initial last_activity timestamp
        activity_resp1 = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data1 = activity_resp1.json()
        staff_user1 = next((u for u in data1['users'] if u['id'] == staff_id), None)
        initial_timestamp = staff_user1.get('last_activity')
        print(f"Initial staff last_activity: {initial_timestamp}")
        
        # Step 4: Admin views activity page multiple times (simulating page refresh)
        for i in range(5):
            time.sleep(0.5)  # Small delay between requests
            requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        
        # Step 5: Check staff's timestamp again - it should NOT have changed
        activity_resp2 = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data2 = activity_resp2.json()
        staff_user2 = next((u for u in data2['users'] if u['id'] == staff_id), None)
        final_timestamp = staff_user2.get('last_activity')
        print(f"Final staff last_activity: {final_timestamp}")
        
        # CRITICAL ASSERTION: Timestamps must be equal
        assert initial_timestamp == final_timestamp, \
            f"INDEPENDENCE VIOLATION: Staff timestamp changed from {initial_timestamp} to {final_timestamp} when admin viewed activity page!"
        
        print("✓ INDEPENDENCE TEST PASSED: Admin viewing activity page did NOT change staff's timestamp")
    
    def test_admin_heartbeat_does_not_affect_staff(self):
        """Admin sending heartbeat should NOT affect staff's last_activity"""
        # Login as staff and record timestamp
        staff_login = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        staff_token = staff_login.json()['token']
        staff_id = staff_login.json()['user']['id']
        
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=staff_headers)
        
        # Login as admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get staff's initial timestamp
        activity_resp1 = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        staff_user1 = next((u for u in activity_resp1.json()['users'] if u['id'] == staff_id), None)
        initial_timestamp = staff_user1.get('last_activity')
        
        # Admin sends multiple heartbeats
        for i in range(5):
            time.sleep(0.3)
            requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=admin_headers)
        
        # Check staff's timestamp - should NOT have changed
        activity_resp2 = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        staff_user2 = next((u for u in activity_resp2.json()['users'] if u['id'] == staff_id), None)
        final_timestamp = staff_user2.get('last_activity')
        
        assert initial_timestamp == final_timestamp, \
            f"INDEPENDENCE VIOLATION: Staff timestamp changed when admin sent heartbeat!"
        
        print("✓ Admin heartbeat does NOT affect staff's timestamp")
    
    def test_multiple_users_independent_status(self):
        """Each user should have independent status tracking"""
        # Login as staff
        staff_login = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF_CREDS)
        staff_token = staff_login.json()['token']
        staff_id = staff_login.json()['user']['id']
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Login as admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_id = admin_login.json()['user']['id']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Both send heartbeats
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=staff_headers)
        requests.post(f"{BASE_URL}/api/auth/heartbeat", headers=admin_headers)
        
        # Get activity
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        users = activity_resp.json()['users']
        
        staff_user = next((u for u in users if u['id'] == staff_id), None)
        admin_user = next((u for u in users if u['id'] == admin_id), None)
        
        assert staff_user is not None
        assert admin_user is not None
        
        # Both should be online (independent)
        assert staff_user['status'] == 'online', f"Staff should be online, got {staff_user['status']}"
        assert admin_user['status'] == 'online', f"Admin should be online, got {admin_user['status']}"
        
        # Logout staff
        requests.post(f"{BASE_URL}/api/auth/logout", headers=staff_headers)
        
        # Check again - staff should be offline, admin should still be online
        activity_resp2 = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        users2 = activity_resp2.json()['users']
        
        staff_user2 = next((u for u in users2 if u['id'] == staff_id), None)
        admin_user2 = next((u for u in users2 if u['id'] == admin_id), None)
        
        assert staff_user2['status'] == 'offline', f"Staff should be offline after logout, got {staff_user2['status']}"
        assert admin_user2['status'] == 'online', f"Admin should still be online, got {admin_user2['status']}"
        
        print("✓ Multiple users have independent status tracking")


class TestStatusBadgeColors:
    """Test that status values are correct for badge color mapping"""
    
    def test_all_status_values_valid(self):
        """All user status values should be 'online', 'idle', or 'offline'"""
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        users = activity_resp.json()['users']
        
        valid_statuses = {'online', 'idle', 'offline'}
        for user in users:
            assert user['status'] in valid_statuses, \
                f"Invalid status '{user['status']}' for user {user['name']}"
        
        print(f"✓ All {len(users)} users have valid status values")
    
    def test_summary_counts_match_users(self):
        """Summary counts should match actual user statuses"""
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        admin_token = admin_login.json()['token']
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        activity_resp = requests.get(f"{BASE_URL}/api/users/activity", headers=admin_headers)
        data = activity_resp.json()
        
        users = data['users']
        summary = data['summary']
        
        # Count actual statuses
        actual_online = sum(1 for u in users if u['status'] == 'online')
        actual_idle = sum(1 for u in users if u['status'] == 'idle')
        actual_offline = sum(1 for u in users if u['status'] == 'offline')
        
        assert summary['total'] == len(users), f"Total mismatch: {summary['total']} vs {len(users)}"
        assert summary['online'] == actual_online, f"Online mismatch: {summary['online']} vs {actual_online}"
        assert summary['idle'] == actual_idle, f"Idle mismatch: {summary['idle']} vs {actual_idle}"
        assert summary['offline'] == actual_offline, f"Offline mismatch: {summary['offline']} vs {actual_offline}"
        
        print(f"✓ Summary counts match: total={summary['total']}, online={summary['online']}, idle={summary['idle']}, offline={summary['offline']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
