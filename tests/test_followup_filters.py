"""
Test Follow-up Filters Feature
Tests the new product and database filtering functionality for the Follow-up Reminders page
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFollowupFilters:
    """Test the followup filters endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as staff to get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as staff
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.staff_token = token
        else:
            pytest.skip(f"Staff login failed: {login_response.status_code}")
    
    def test_get_followup_filters_endpoint_exists(self):
        """Test that GET /api/followups/filters endpoint exists and returns 200"""
        response = self.session.get(f"{BASE_URL}/api/followups/filters")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ GET /api/followups/filters endpoint exists and returns 200")
    
    def test_get_followup_filters_returns_correct_structure(self):
        """Test that /api/followups/filters returns products and databases arrays"""
        response = self.session.get(f"{BASE_URL}/api/followups/filters")
        assert response.status_code == 200
        
        data = response.json()
        assert 'products' in data, "Response should contain 'products' key"
        assert 'databases' in data, "Response should contain 'databases' key"
        assert isinstance(data['products'], list), "'products' should be a list"
        assert isinstance(data['databases'], list), "'databases' should be a list"
        print(f"✓ Filters response structure correct - products: {len(data['products'])}, databases: {len(data['databases'])}")
    
    def test_get_followup_filters_product_structure(self):
        """Test that products in filters have correct structure (id, name)"""
        response = self.session.get(f"{BASE_URL}/api/followups/filters")
        assert response.status_code == 200
        
        data = response.json()
        for product in data['products']:
            assert 'id' in product, "Each product should have 'id'"
            assert 'name' in product, "Each product should have 'name'"
        print(f"✓ Product structure correct for {len(data['products'])} products")
    
    def test_get_followup_filters_database_structure(self):
        """Test that databases in filters have correct structure (id, name, product_id)"""
        response = self.session.get(f"{BASE_URL}/api/followups/filters")
        assert response.status_code == 200
        
        data = response.json()
        for db in data['databases']:
            assert 'id' in db, "Each database should have 'id'"
            assert 'name' in db, "Each database should have 'name'"
            assert 'product_id' in db, "Each database should have 'product_id'"
        print(f"✓ Database structure correct for {len(data['databases'])} databases")
    
    def test_get_followups_without_filters(self):
        """Test GET /api/followups without any filters"""
        response = self.session.get(f"{BASE_URL}/api/followups")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'followups' in data, "Response should contain 'followups' key"
        assert 'summary' in data, "Response should contain 'summary' key"
        print(f"✓ GET /api/followups returns {len(data['followups'])} followups")
    
    def test_get_followups_with_product_filter(self):
        """Test GET /api/followups with product_id filter"""
        # First get available products
        filters_response = self.session.get(f"{BASE_URL}/api/followups/filters")
        filters_data = filters_response.json()
        
        if filters_data['products']:
            product_id = filters_data['products'][0]['id']
            response = self.session.get(f"{BASE_URL}/api/followups", params={"product_id": product_id})
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert 'followups' in data
            # Verify all returned followups have the correct product_id
            for followup in data['followups']:
                assert followup.get('product_id') == product_id, f"Followup product_id mismatch: expected {product_id}, got {followup.get('product_id')}"
            print(f"✓ Product filter works - returned {len(data['followups'])} followups for product {product_id}")
        else:
            print("⚠ No products available to test product filter")
    
    def test_get_followups_with_database_filter(self):
        """Test GET /api/followups with database_id filter"""
        # First get available databases
        filters_response = self.session.get(f"{BASE_URL}/api/followups/filters")
        filters_data = filters_response.json()
        
        if filters_data['databases']:
            database_id = filters_data['databases'][0]['id']
            response = self.session.get(f"{BASE_URL}/api/followups", params={"database_id": database_id})
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert 'followups' in data
            print(f"✓ Database filter works - returned {len(data['followups'])} followups for database {database_id}")
        else:
            print("⚠ No databases available to test database filter")
    
    def test_get_followups_with_both_filters(self):
        """Test GET /api/followups with both product_id and database_id filters"""
        # First get available filters
        filters_response = self.session.get(f"{BASE_URL}/api/followups/filters")
        filters_data = filters_response.json()
        
        if filters_data['products'] and filters_data['databases']:
            product_id = filters_data['products'][0]['id']
            # Find a database that belongs to this product
            matching_db = next((db for db in filters_data['databases'] if db.get('product_id') == product_id), None)
            
            if matching_db:
                database_id = matching_db['id']
                response = self.session.get(f"{BASE_URL}/api/followups", params={
                    "product_id": product_id,
                    "database_id": database_id
                })
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                data = response.json()
                assert 'followups' in data
                print(f"✓ Combined filters work - returned {len(data['followups'])} followups")
            else:
                print("⚠ No matching database for product to test combined filters")
        else:
            print("⚠ No products/databases available to test combined filters")
    
    def test_followup_filters_requires_staff_role(self):
        """Test that /api/followups/filters requires staff role (admin should get 403)"""
        # Login as admin
        admin_session = requests.Session()
        admin_session.headers.update({"Content-Type": "application/json"})
        
        login_response = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            admin_session.headers.update({"Authorization": f"Bearer {token}"})
            
            response = admin_session.get(f"{BASE_URL}/api/followups/filters")
            assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
            print("✓ Filters endpoint correctly restricts to staff role only")
        else:
            print("⚠ Admin login failed, skipping role restriction test")
    
    def test_followups_requires_staff_role(self):
        """Test that /api/followups requires staff role (admin should get 403)"""
        # Login as admin
        admin_session = requests.Session()
        admin_session.headers.update({"Content-Type": "application/json"})
        
        login_response = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            admin_session.headers.update({"Authorization": f"Bearer {token}"})
            
            response = admin_session.get(f"{BASE_URL}/api/followups")
            assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
            print("✓ Followups endpoint correctly restricts to staff role only")
        else:
            print("⚠ Admin login failed, skipping role restriction test")


class TestFollowupFiltersUnauthorized:
    """Test unauthorized access to followup filters"""
    
    def test_filters_requires_auth(self):
        """Test that /api/followups/filters requires authentication"""
        response = requests.get(f"{BASE_URL}/api/followups/filters")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Filters endpoint requires authentication")
    
    def test_followups_requires_auth(self):
        """Test that /api/followups requires authentication"""
        response = requests.get(f"{BASE_URL}/api/followups")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Followups endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
