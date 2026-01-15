# Test Role Hierarchy and Page Access Control Feature
# Tests: master_admin role, role hierarchy enforcement, page access control

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_ADMIN_EMAIL = "masteradmin@crm.com"
MASTER_ADMIN_PASSWORD = "master123"
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestAuthLogin:
    """Test login returns blocked_pages in user object"""
    
    def test_master_admin_login_returns_blocked_pages(self):
        """Master admin login should return empty blocked_pages"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_ADMIN_EMAIL,
            "password": MASTER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "blocked_pages" in data["user"]
        assert data["user"]["role"] == "master_admin"
        assert isinstance(data["user"]["blocked_pages"], list)
    
    def test_admin_login_returns_blocked_pages(self):
        """Admin login should return blocked_pages list"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "blocked_pages" in data["user"]
        assert data["user"]["role"] == "admin"
        # Admin should have blocked pages as per context
        assert "bonus" in data["user"]["blocked_pages"]
        assert "products" in data["user"]["blocked_pages"]


class TestRoleHierarchy:
    """Test role hierarchy enforcement - admin cannot edit admin/master_admin"""
    
    @pytest.fixture
    def master_admin_token(self):
        """Get master admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_ADMIN_EMAIL,
            "password": MASTER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Master admin login failed")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture
    def admin_user_id(self, master_admin_token):
        """Get admin user ID"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("email") == ADMIN_EMAIL:
                    return user.get("id")
        pytest.skip("Could not find admin user")
    
    @pytest.fixture
    def master_admin_user_id(self, master_admin_token):
        """Get master admin user ID"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("email") == MASTER_ADMIN_EMAIL:
                    return user.get("id")
        pytest.skip("Could not find master admin user")
    
    @pytest.fixture
    def staff_user_id(self, master_admin_token):
        """Get or create staff user ID"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("role") == "staff":
                    return user.get("id")
        pytest.skip("Could not find staff user")
    
    def test_admin_cannot_edit_admin_user(self, admin_token, admin_user_id):
        """Admin should NOT be able to edit another admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}",
            headers=headers,
            json={"name": "Test Name Change"}
        )
        # Should return 403 Forbidden
        assert response.status_code == 403
        data = response.json()
        assert "permission" in data.get("detail", "").lower() or "don't have" in data.get("detail", "").lower()
    
    def test_admin_cannot_edit_master_admin_user(self, admin_token, master_admin_user_id):
        """Admin should NOT be able to edit master_admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(
            f"{BASE_URL}/api/users/{master_admin_user_id}",
            headers=headers,
            json={"name": "Test Name Change"}
        )
        # Should return 403 Forbidden
        assert response.status_code == 403
    
    def test_admin_can_edit_staff_user(self, admin_token, staff_user_id):
        """Admin SHOULD be able to edit staff user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        # First get current name
        response = requests.get(f"{BASE_URL}/api/users/{staff_user_id}", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get staff user")
        original_name = response.json().get("name")
        
        # Update name
        response = requests.put(
            f"{BASE_URL}/api/users/{staff_user_id}",
            headers=headers,
            json={"name": "TEST_Updated Staff Name"}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/users/{staff_user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json().get("name") == "TEST_Updated Staff Name"
        
        # Restore original name
        requests.put(
            f"{BASE_URL}/api/users/{staff_user_id}",
            headers=headers,
            json={"name": original_name}
        )
    
    def test_master_admin_can_edit_admin_user(self, master_admin_token, admin_user_id):
        """Master admin SHOULD be able to edit admin user"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        # First get current name
        response = requests.get(f"{BASE_URL}/api/users/{admin_user_id}", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get admin user")
        original_name = response.json().get("name")
        
        # Update name
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}",
            headers=headers,
            json={"name": "TEST_Updated Admin Name"}
        )
        assert response.status_code == 200
        
        # Verify update
        response = requests.get(f"{BASE_URL}/api/users/{admin_user_id}", headers=headers)
        assert response.status_code == 200
        assert response.json().get("name") == "TEST_Updated Admin Name"
        
        # Restore original name
        requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}",
            headers=headers,
            json={"name": original_name}
        )
    
    def test_admin_cannot_delete_admin_user(self, admin_token, admin_user_id):
        """Admin should NOT be able to delete another admin user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.delete(
            f"{BASE_URL}/api/users/{admin_user_id}",
            headers=headers
        )
        # Should return 403 Forbidden
        assert response.status_code == 403


class TestPageAccessControl:
    """Test page access control - only master_admin can set page access for admins"""
    
    @pytest.fixture
    def master_admin_token(self):
        """Get master admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_ADMIN_EMAIL,
            "password": MASTER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Master admin login failed")
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture
    def admin_user_id(self, master_admin_token):
        """Get admin user ID"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("email") == ADMIN_EMAIL:
                    return user.get("id")
        pytest.skip("Could not find admin user")
    
    @pytest.fixture
    def staff_user_id(self, master_admin_token):
        """Get staff user ID"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if response.status_code == 200:
            users = response.json()
            for user in users:
                if user.get("role") == "staff":
                    return user.get("id")
        pytest.skip("Could not find staff user")
    
    def test_master_admin_can_set_page_access_for_admin(self, master_admin_token, admin_user_id):
        """Master admin SHOULD be able to set page access for admin users"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # Get current blocked pages
        response = requests.get(f"{BASE_URL}/api/users/{admin_user_id}/page-access", headers=headers)
        assert response.status_code == 200
        original_blocked = response.json().get("blocked_pages", [])
        
        # Set new blocked pages
        new_blocked = ["bonus", "products", "analytics"]
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}/page-access",
            headers=headers,
            json={"blocked_pages": new_blocked}
        )
        assert response.status_code == 200
        assert response.json().get("blocked_pages") == new_blocked
        
        # Verify persistence
        response = requests.get(f"{BASE_URL}/api/users/{admin_user_id}/page-access", headers=headers)
        assert response.status_code == 200
        assert response.json().get("blocked_pages") == new_blocked
        
        # Restore original blocked pages
        requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}/page-access",
            headers=headers,
            json={"blocked_pages": original_blocked}
        )
    
    def test_admin_cannot_set_page_access(self, admin_token, admin_user_id):
        """Admin should NOT be able to set page access (requires master_admin)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(
            f"{BASE_URL}/api/users/{admin_user_id}/page-access",
            headers=headers,
            json={"blocked_pages": ["bonus"]}
        )
        # Should return 403 Forbidden (Master Admin access required)
        assert response.status_code == 403
    
    def test_page_access_only_for_admin_users(self, master_admin_token, staff_user_id):
        """Page access control should only work for admin users, not staff"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        response = requests.put(
            f"{BASE_URL}/api/users/{staff_user_id}/page-access",
            headers=headers,
            json={"blocked_pages": ["bonus"]}
        )
        # Should return 400 Bad Request (only for admin users)
        assert response.status_code == 400
        assert "admin" in response.json().get("detail", "").lower()


class TestRegisterMasterAdmin:
    """Test that master_admin role can be created via register endpoint"""
    
    @pytest.fixture
    def master_admin_token(self):
        """Get master admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MASTER_ADMIN_EMAIL,
            "password": MASTER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Master admin login failed")
    
    def test_can_register_master_admin_role(self, master_admin_token):
        """Should be able to register a user with master_admin role"""
        headers = {"Authorization": f"Bearer {master_admin_token}"}
        
        # Try to create a new master_admin user
        test_email = "TEST_newmasteradmin@crm.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            headers=headers,
            json={
                "email": test_email,
                "password": "test123",
                "name": "TEST New Master Admin",
                "role": "master_admin"
            }
        )
        
        # Should succeed (201 or 200) or fail with email already exists (400)
        if response.status_code == 400 and "already" in response.json().get("detail", "").lower():
            # User already exists from previous test, that's fine
            pass
        else:
            assert response.status_code in [200, 201]
            data = response.json()
            assert data.get("role") == "master_admin"
        
        # Cleanup - delete the test user if created
        users_response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        if users_response.status_code == 200:
            for user in users_response.json():
                if user.get("email") == test_email:
                    requests.delete(f"{BASE_URL}/api/users/{user['id']}", headers=headers)


class TestAuthMe:
    """Test /auth/me endpoint returns blocked_pages"""
    
    def test_auth_me_returns_blocked_pages(self):
        """GET /auth/me should return blocked_pages for admin user"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        
        # Get /auth/me
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "blocked_pages" in data
        assert isinstance(data["blocked_pages"], list)
