"""
Test Grace Period Configuration Feature
========================================
Tests for configurable grace period for reserved member auto-cleanup.

Features tested:
1. GET /api/reserved-members/cleanup-config - returns current configuration with available products
2. PUT /api/reserved-members/cleanup-config - updates grace period settings
3. Validation: grace_days >= 1, warning_days < global_grace_days
4. Validation: product_id exists for product overrides
5. Preview endpoint uses configured grace periods instead of hardcoded 30 days
6. Cleanup logic uses product-specific overrides when available
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestGracePeriodConfigAuth:
    """Test authentication requirements for grace period config endpoints"""
    
    def test_get_config_requires_auth(self):
        """GET cleanup-config requires authentication"""
        response = requests.get(f"{BASE_URL}/api/reserved-members/cleanup-config")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET cleanup-config requires authentication")
    
    def test_put_config_requires_auth(self):
        """PUT cleanup-config requires authentication"""
        response = requests.put(f"{BASE_URL}/api/reserved-members/cleanup-config", json={
            "global_grace_days": 30,
            "warning_days": 7,
            "product_overrides": []
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ PUT cleanup-config requires authentication")
    
    def test_get_config_requires_admin(self):
        """GET cleanup-config requires admin role"""
        # Login as staff
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert login_response.status_code == 200, f"Staff login failed: {login_response.text}"
        staff_token = login_response.json().get('token')
        
        # Try to access config as staff
        response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"
        print("✓ GET cleanup-config requires admin role")
    
    def test_put_config_requires_admin(self):
        """PUT cleanup-config requires admin role"""
        # Login as staff
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert login_response.status_code == 200
        staff_token = login_response.json().get('token')
        
        # Try to update config as staff
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "global_grace_days": 30,
                "warning_days": 7,
                "product_overrides": []
            }
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"
        print("✓ PUT cleanup-config requires admin role")


class TestGetGracePeriodConfig:
    """Test GET /api/reserved-members/cleanup-config endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        self.admin_token = login_response.json().get('token')
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_get_config_returns_correct_structure(self):
        """GET cleanup-config returns expected response structure"""
        response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert response.status_code == 200, f"GET config failed: {response.text}"
        
        data = response.json()
        
        # Check required fields
        assert 'global_grace_days' in data, "Missing global_grace_days"
        assert 'warning_days' in data, "Missing warning_days"
        assert 'product_overrides' in data, "Missing product_overrides"
        assert 'available_products' in data, "Missing available_products"
        
        # Check types
        assert isinstance(data['global_grace_days'], int)
        assert isinstance(data['warning_days'], int)
        assert isinstance(data['product_overrides'], list)
        assert isinstance(data['available_products'], list)
        
        print(f"✓ GET cleanup-config returns correct structure")
        print(f"  - global_grace_days: {data['global_grace_days']}")
        print(f"  - warning_days: {data['warning_days']}")
        print(f"  - product_overrides count: {len(data['product_overrides'])}")
        print(f"  - available_products count: {len(data['available_products'])}")
    
    def test_get_config_returns_available_products(self):
        """GET cleanup-config returns available products for reference"""
        response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        available_products = data.get('available_products', [])
        
        # Each product should have id and name
        if available_products:
            product = available_products[0]
            assert 'id' in product, "Product missing 'id'"
            assert 'name' in product, "Product missing 'name'"
            print(f"✓ Available products have correct structure (id, name)")
            print(f"  - Sample product: {product}")
        else:
            print("✓ No products available (this is OK for empty database)")
    
    def test_get_config_default_values(self):
        """GET cleanup-config returns sensible defaults"""
        response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Default values should be reasonable
        assert data['global_grace_days'] >= 1, "global_grace_days should be at least 1"
        assert data['warning_days'] >= 1, "warning_days should be at least 1"
        assert data['warning_days'] < data['global_grace_days'], "warning_days should be less than global_grace_days"
        
        print(f"✓ Default values are sensible")


class TestUpdateGracePeriodConfig:
    """Test PUT /api/reserved-members/cleanup-config endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get initial config"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json().get('token')
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get initial config to restore later
        config_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        if config_response.status_code == 200:
            self.initial_config = config_response.json()
        else:
            self.initial_config = {
                "global_grace_days": 30,
                "warning_days": 7,
                "product_overrides": []
            }
    
    def test_update_config_success(self):
        """PUT cleanup-config updates configuration successfully"""
        new_config = {
            "global_grace_days": 45,
            "warning_days": 10,
            "product_overrides": []
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=new_config
        )
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        assert data.get('success') == True, "Expected success: true"
        
        # Verify the update by getting config again
        get_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert get_response.status_code == 200
        
        updated_data = get_response.json()
        assert updated_data['global_grace_days'] == 45, f"Expected 45, got {updated_data['global_grace_days']}"
        assert updated_data['warning_days'] == 10, f"Expected 10, got {updated_data['warning_days']}"
        
        print("✓ PUT cleanup-config updates configuration successfully")
        
        # Restore initial config
        requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json={
                "global_grace_days": self.initial_config.get('global_grace_days', 30),
                "warning_days": self.initial_config.get('warning_days', 7),
                "product_overrides": self.initial_config.get('product_overrides', [])
            }
        )
    
    def test_update_config_validates_grace_days_minimum(self):
        """PUT cleanup-config validates grace_days >= 1"""
        invalid_config = {
            "global_grace_days": 0,  # Invalid - must be >= 1
            "warning_days": 7,
            "product_overrides": []
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=invalid_config
        )
        assert response.status_code == 400, f"Expected 400 for invalid grace_days, got {response.status_code}"
        print("✓ Validates grace_days >= 1")
    
    def test_update_config_validates_warning_days_minimum(self):
        """PUT cleanup-config validates warning_days >= 1"""
        invalid_config = {
            "global_grace_days": 30,
            "warning_days": 0,  # Invalid - must be >= 1
            "product_overrides": []
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=invalid_config
        )
        assert response.status_code == 400, f"Expected 400 for invalid warning_days, got {response.status_code}"
        print("✓ Validates warning_days >= 1")
    
    def test_update_config_validates_warning_less_than_grace(self):
        """PUT cleanup-config validates warning_days < global_grace_days"""
        invalid_config = {
            "global_grace_days": 30,
            "warning_days": 30,  # Invalid - must be less than global_grace_days
            "product_overrides": []
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=invalid_config
        )
        assert response.status_code == 400, f"Expected 400 for warning_days >= global_grace_days, got {response.status_code}"
        
        # Also test warning_days > global_grace_days
        invalid_config2 = {
            "global_grace_days": 30,
            "warning_days": 35,  # Invalid - must be less than global_grace_days
            "product_overrides": []
        }
        
        response2 = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=invalid_config2
        )
        assert response2.status_code == 400, f"Expected 400 for warning_days > global_grace_days, got {response2.status_code}"
        
        print("✓ Validates warning_days < global_grace_days")


class TestProductOverrides:
    """Test product-specific grace period overrides"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get products"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json().get('token')
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get available products
        config_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        if config_response.status_code == 200:
            self.available_products = config_response.json().get('available_products', [])
            self.initial_config = config_response.json()
        else:
            self.available_products = []
            self.initial_config = {
                "global_grace_days": 30,
                "warning_days": 7,
                "product_overrides": []
            }
    
    def test_add_product_override(self):
        """Can add product-specific grace period override"""
        if not self.available_products:
            pytest.skip("No products available for testing")
        
        product = self.available_products[0]
        
        config_with_override = {
            "global_grace_days": 30,
            "warning_days": 7,
            "product_overrides": [
                {
                    "product_id": product['id'],
                    "product_name": product['name'],
                    "grace_days": 60
                }
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=config_with_override
        )
        assert response.status_code == 200, f"Failed to add override: {response.text}"
        
        # Verify the override was saved
        get_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert len(data['product_overrides']) == 1, f"Expected 1 override, got {len(data['product_overrides'])}"
        assert data['product_overrides'][0]['product_id'] == product['id']
        assert data['product_overrides'][0]['grace_days'] == 60
        
        print(f"✓ Can add product-specific override: {product['name']} = 60 days")
        
        # Restore initial config
        requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json={
                "global_grace_days": self.initial_config.get('global_grace_days', 30),
                "warning_days": self.initial_config.get('warning_days', 7),
                "product_overrides": self.initial_config.get('product_overrides', [])
            }
        )
    
    def test_product_override_validates_product_exists(self):
        """Product override validates that product_id exists"""
        config_with_invalid_product = {
            "global_grace_days": 30,
            "warning_days": 7,
            "product_overrides": [
                {
                    "product_id": "non_existent_product_id_12345",
                    "product_name": "Non-existent Product",
                    "grace_days": 60
                }
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=config_with_invalid_product
        )
        assert response.status_code == 400, f"Expected 400 for non-existent product, got {response.status_code}"
        print("✓ Validates product_id exists")
    
    def test_product_override_validates_grace_days(self):
        """Product override validates grace_days >= 1"""
        if not self.available_products:
            pytest.skip("No products available for testing")
        
        product = self.available_products[0]
        
        config_with_invalid_override = {
            "global_grace_days": 30,
            "warning_days": 7,
            "product_overrides": [
                {
                    "product_id": product['id'],
                    "product_name": product['name'],
                    "grace_days": 0  # Invalid
                }
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=config_with_invalid_override
        )
        assert response.status_code == 400, f"Expected 400 for invalid override grace_days, got {response.status_code}"
        print("✓ Product override validates grace_days >= 1")
    
    def test_multiple_product_overrides(self):
        """Can add multiple product-specific overrides"""
        if len(self.available_products) < 2:
            pytest.skip("Need at least 2 products for this test")
        
        product1 = self.available_products[0]
        product2 = self.available_products[1]
        
        config_with_overrides = {
            "global_grace_days": 30,
            "warning_days": 7,
            "product_overrides": [
                {
                    "product_id": product1['id'],
                    "product_name": product1['name'],
                    "grace_days": 45
                },
                {
                    "product_id": product2['id'],
                    "product_name": product2['name'],
                    "grace_days": 60
                }
            ]
        }
        
        response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=config_with_overrides
        )
        assert response.status_code == 200, f"Failed to add multiple overrides: {response.text}"
        
        # Verify
        get_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert len(data['product_overrides']) == 2, f"Expected 2 overrides, got {len(data['product_overrides'])}"
        
        print(f"✓ Can add multiple product overrides")
        
        # Restore initial config
        requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json={
                "global_grace_days": self.initial_config.get('global_grace_days', 30),
                "warning_days": self.initial_config.get('warning_days', 7),
                "product_overrides": self.initial_config.get('product_overrides', [])
            }
        )


class TestPreviewUsesConfig:
    """Test that preview endpoint uses configured grace periods"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json().get('token')
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_preview_returns_config_info(self):
        """Preview endpoint returns the config being used"""
        response = requests.get(
            f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview",
            headers=self.headers
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        
        data = response.json()
        
        # Check if config info is included
        assert 'config' in data, "Preview should include config info"
        config = data['config']
        
        assert 'global_grace_days' in config, "Config should include global_grace_days"
        assert 'warning_days' in config, "Config should include warning_days"
        
        print(f"✓ Preview returns config info:")
        print(f"  - global_grace_days: {config.get('global_grace_days')}")
        print(f"  - warning_days: {config.get('warning_days')}")
        print(f"  - product_overrides_count: {config.get('product_overrides_count', 0)}")
    
    def test_preview_member_shows_grace_days(self):
        """Preview member info includes grace_days used"""
        response = requests.get(
            f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check if any members have grace_days info
        all_members = data.get('expiring_soon', []) + data.get('will_be_deleted', [])
        
        if all_members:
            member = all_members[0]
            assert 'grace_days' in member, "Member info should include grace_days"
            print(f"✓ Member info includes grace_days: {member.get('grace_days')}")
        else:
            print("✓ No expiring/to-be-deleted members to verify (this is OK)")


class TestCleanupUsesConfig:
    """Test that cleanup logic uses configured grace periods"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200
        self.admin_token = login_response.json().get('token')
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_cleanup_runs_with_config(self):
        """Cleanup job runs successfully with current config"""
        response = requests.post(
            f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-run",
            headers=self.headers
        )
        assert response.status_code == 200, f"Cleanup failed: {response.text}"
        
        data = response.json()
        assert data.get('success') == True
        
        print("✓ Cleanup runs successfully with current config")
    
    def test_config_change_affects_preview(self):
        """Changing config affects preview results"""
        # Get initial config
        initial_response = requests.get(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers
        )
        assert initial_response.status_code == 200
        initial_config = initial_response.json()
        
        # Get initial preview
        preview1 = requests.get(
            f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview",
            headers=self.headers
        )
        assert preview1.status_code == 200
        preview1_data = preview1.json()
        
        # Change config to shorter grace period
        new_config = {
            "global_grace_days": 15,  # Shorter grace period
            "warning_days": 5,
            "product_overrides": []
        }
        
        update_response = requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json=new_config
        )
        assert update_response.status_code == 200
        
        # Get new preview
        preview2 = requests.get(
            f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview",
            headers=self.headers
        )
        assert preview2.status_code == 200
        preview2_data = preview2.json()
        
        # Verify config in preview changed
        assert preview2_data['config']['global_grace_days'] == 15
        assert preview2_data['config']['warning_days'] == 5
        
        print("✓ Config change affects preview results")
        print(f"  - Before: global_grace_days={preview1_data['config']['global_grace_days']}")
        print(f"  - After: global_grace_days={preview2_data['config']['global_grace_days']}")
        
        # Restore initial config
        requests.put(
            f"{BASE_URL}/api/reserved-members/cleanup-config",
            headers=self.headers,
            json={
                "global_grace_days": initial_config.get('global_grace_days', 30),
                "warning_days": initial_config.get('warning_days', 7),
                "product_overrides": initial_config.get('product_overrides', [])
            }
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
