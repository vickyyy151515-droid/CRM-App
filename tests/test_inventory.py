# Office Inventory API Tests
# Tests for inventory management: CRUD operations, assign/return items, history

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestInventoryAuth:
    """Test authentication requirements for inventory endpoints"""
    
    def test_get_inventory_requires_auth(self):
        """GET /api/inventory requires authentication"""
        response = requests.get(f"{BASE_URL}/api/inventory")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_post_inventory_requires_auth(self):
        """POST /api/inventory requires authentication"""
        response = requests.post(f"{BASE_URL}/api/inventory", json={"name": "Test"})
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_inventory_requires_admin_role(self, staff_token):
        """Staff users should not access inventory (admin only)"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"


class TestInventoryList:
    """Test GET /api/inventory endpoint"""
    
    def test_get_inventory_returns_items_and_stats(self, admin_token):
        """GET /api/inventory returns items, categories, and stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response should have 'items'"
        assert "categories" in data, "Response should have 'categories'"
        assert "stats" in data, "Response should have 'stats'"
        
        # Verify stats structure
        stats = data["stats"]
        assert "total" in stats, "Stats should have 'total'"
        assert "assigned" in stats, "Stats should have 'assigned'"
        assert "available" in stats, "Stats should have 'available'"
        
        # Verify items is a list
        assert isinstance(data["items"], list)
    
    def test_filter_by_category(self, admin_token):
        """GET /api/inventory?category=laptop filters by category"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory?category=laptop", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be laptops
        for item in data["items"]:
            assert item["category"] == "laptop", f"Expected laptop, got {item['category']}"
    
    def test_filter_by_status(self, admin_token):
        """GET /api/inventory?status=available filters by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory?status=available", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be available
        for item in data["items"]:
            assert item["status"] == "available", f"Expected available, got {item['status']}"
    
    def test_search_by_name(self, admin_token):
        """GET /api/inventory?search=macbook searches by name"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory?search=macbook", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Items should contain search term in name/description/serial
        for item in data["items"]:
            search_fields = f"{item.get('name', '')} {item.get('description', '')} {item.get('serial_number', '')}".lower()
            assert "macbook" in search_fields, f"Search term not found in item: {item['name']}"


class TestInventoryCRUD:
    """Test CRUD operations for inventory items"""
    
    def test_create_item(self, admin_token):
        """POST /api/inventory creates new item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_Monitor_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "name": unique_name,
            "description": "Test monitor for testing",
            "category": "monitor",
            "serial_number": f"SN-{uuid.uuid4().hex[:8]}",
            "purchase_date": "2024-01-15",
            "purchase_price": 5000000,
            "condition": "good",
            "notes": "Test item"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory", json=payload, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify created item
        assert data["name"] == unique_name
        assert data["category"] == "monitor"
        assert data["status"] == "available"
        assert data["condition"] == "good"
        assert "id" in data
        
        # Store for cleanup
        return data["id"]
    
    def test_get_single_item(self, admin_token, test_item_id):
        """GET /api/inventory/{id} returns item with history"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory/{test_item_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "item" in data
        assert "assignment_history" in data
        assert data["item"]["id"] == test_item_id
    
    def test_get_nonexistent_item(self, admin_token):
        """GET /api/inventory/{id} returns 404 for nonexistent item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/inventory/nonexistent-id-12345", headers=headers)
        
        assert response.status_code == 404
    
    def test_update_item(self, admin_token, test_item_id):
        """PUT /api/inventory/{id} updates item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        update_payload = {
            "name": "Updated Test Item",
            "condition": "fair",
            "notes": "Updated notes"
        }
        
        response = requests.put(f"{BASE_URL}/api/inventory/{test_item_id}", json=update_payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Test Item"
        assert data["condition"] == "fair"
        assert data["notes"] == "Updated notes"
        
        # Verify persistence with GET
        get_response = requests.get(f"{BASE_URL}/api/inventory/{test_item_id}", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["item"]["name"] == "Updated Test Item"
    
    def test_delete_available_item(self, admin_token):
        """DELETE /api/inventory/{id} deletes available item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First create an item to delete
        create_payload = {
            "name": f"TEST_ToDelete_{uuid.uuid4().hex[:8]}",
            "category": "other",
            "condition": "good"
        }
        create_response = requests.post(f"{BASE_URL}/api/inventory", json=create_payload, headers=headers)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]
        
        # Delete the item
        delete_response = requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)
        assert get_response.status_code == 404


class TestInventoryAssignment:
    """Test assign/return functionality"""
    
    def test_assign_item_to_staff(self, admin_token, available_item_id, staff_user_id):
        """POST /api/inventory/{id}/assign assigns item to staff"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "staff_id": staff_user_id,
            "notes": "Assigned for testing"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory/{available_item_id}/assign", json=payload, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "assignment_id" in data
        
        # Verify item is now assigned
        get_response = requests.get(f"{BASE_URL}/api/inventory/{available_item_id}", headers=headers)
        assert get_response.status_code == 200
        item = get_response.json()["item"]
        assert item["status"] == "assigned"
        assert item["assigned_to"] == staff_user_id
    
    def test_cannot_assign_already_assigned_item(self, admin_token, assigned_item_id, staff_user_id):
        """POST /api/inventory/{id}/assign fails for already assigned item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "staff_id": staff_user_id,
            "notes": "Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory/{assigned_item_id}/assign", json=payload, headers=headers)
        
        assert response.status_code == 400
        assert "already assigned" in response.json().get("detail", "").lower()
    
    def test_assign_to_nonexistent_staff(self, admin_token, available_item_id):
        """POST /api/inventory/{id}/assign fails for nonexistent staff"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "staff_id": "nonexistent-staff-id-12345",
            "notes": "Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory/{available_item_id}/assign", json=payload, headers=headers)
        
        assert response.status_code == 404
        assert "staff not found" in response.json().get("detail", "").lower()
    
    def test_return_item(self, admin_token, assigned_item_id):
        """POST /api/inventory/{id}/return returns item from staff"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "condition": "good",
            "notes": "Returned in good condition"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory/{assigned_item_id}/return", json=payload, headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify item is now available
        get_response = requests.get(f"{BASE_URL}/api/inventory/{assigned_item_id}", headers=headers)
        assert get_response.status_code == 200
        item = get_response.json()["item"]
        assert item["status"] == "available"
        assert item["assigned_to"] is None
    
    def test_cannot_return_available_item(self, admin_token, available_item_id):
        """POST /api/inventory/{id}/return fails for available item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        payload = {
            "condition": "good",
            "notes": "Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/inventory/{available_item_id}/return", json=payload, headers=headers)
        
        assert response.status_code == 400
        assert "not currently assigned" in response.json().get("detail", "").lower()
    
    def test_cannot_delete_assigned_item(self, admin_token, assigned_item_id):
        """DELETE /api/inventory/{id} fails for assigned item"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/inventory/{assigned_item_id}", headers=headers)
        
        assert response.status_code == 400
        assert "cannot delete assigned" in response.json().get("detail", "").lower()


class TestInventoryHistory:
    """Test assignment history functionality"""
    
    def test_history_shows_assignments(self, admin_token, item_with_history_id):
        """GET /api/inventory/{id} shows assignment history"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/inventory/{item_with_history_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "assignment_history" in data
        history = data["assignment_history"]
        
        # Should have at least one history record
        assert len(history) >= 1, "Should have assignment history"
        
        # Verify history record structure
        record = history[0]
        assert "staff_name" in record
        assert "assigned_at" in record


# ==================== FIXTURES ====================

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@crm.com",
        "password": "admin123"
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code}")
    return response.json().get("token")

@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "staff@crm.com",
        "password": "staff123"
    })
    if response.status_code != 200:
        pytest.skip(f"Staff login failed: {response.status_code}")
    return response.json().get("token")

@pytest.fixture(scope="module")
def staff_user_id(admin_token):
    """Get staff user ID"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/users", headers=headers)
    if response.status_code != 200:
        pytest.skip("Failed to get users")
    
    users = response.json()
    staff_users = [u for u in users if u.get("role") == "staff"]
    if not staff_users:
        pytest.skip("No staff users found")
    
    return staff_users[0]["id"]

@pytest.fixture(scope="function")
def test_item_id(admin_token):
    """Create a test item and return its ID, cleanup after test"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "name": f"TEST_Item_{uuid.uuid4().hex[:8]}",
        "category": "other",
        "condition": "good"
    }
    
    response = requests.post(f"{BASE_URL}/api/inventory", json=payload, headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Failed to create test item: {response.text}")
    
    item_id = response.json()["id"]
    yield item_id
    
    # Cleanup
    requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)

@pytest.fixture(scope="function")
def available_item_id(admin_token):
    """Create an available test item"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "name": f"TEST_Available_{uuid.uuid4().hex[:8]}",
        "category": "laptop",
        "condition": "good"
    }
    
    response = requests.post(f"{BASE_URL}/api/inventory", json=payload, headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Failed to create available item: {response.text}")
    
    item_id = response.json()["id"]
    yield item_id
    
    # Cleanup - try to return first if assigned, then delete
    requests.post(f"{BASE_URL}/api/inventory/{item_id}/return", json={"condition": "good"}, headers=headers)
    requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)

@pytest.fixture(scope="function")
def assigned_item_id(admin_token, staff_user_id):
    """Create an assigned test item"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create item
    payload = {
        "name": f"TEST_Assigned_{uuid.uuid4().hex[:8]}",
        "category": "phone",
        "condition": "good"
    }
    
    response = requests.post(f"{BASE_URL}/api/inventory", json=payload, headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Failed to create item: {response.text}")
    
    item_id = response.json()["id"]
    
    # Assign to staff
    assign_response = requests.post(
        f"{BASE_URL}/api/inventory/{item_id}/assign",
        json={"staff_id": staff_user_id, "notes": "Test assignment"},
        headers=headers
    )
    if assign_response.status_code != 200:
        requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)
        pytest.skip(f"Failed to assign item: {assign_response.text}")
    
    yield item_id
    
    # Cleanup - return and delete
    requests.post(f"{BASE_URL}/api/inventory/{item_id}/return", json={"condition": "good"}, headers=headers)
    requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)

@pytest.fixture(scope="function")
def item_with_history_id(admin_token, staff_user_id):
    """Create an item with assignment history"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create item
    payload = {
        "name": f"TEST_History_{uuid.uuid4().hex[:8]}",
        "category": "furniture",
        "condition": "good"
    }
    
    response = requests.post(f"{BASE_URL}/api/inventory", json=payload, headers=headers)
    if response.status_code != 200:
        pytest.skip(f"Failed to create item: {response.text}")
    
    item_id = response.json()["id"]
    
    # Assign and return to create history
    requests.post(
        f"{BASE_URL}/api/inventory/{item_id}/assign",
        json={"staff_id": staff_user_id, "notes": "First assignment"},
        headers=headers
    )
    requests.post(
        f"{BASE_URL}/api/inventory/{item_id}/return",
        json={"condition": "good", "notes": "First return"},
        headers=headers
    )
    
    yield item_id
    
    # Cleanup
    requests.delete(f"{BASE_URL}/api/inventory/{item_id}", headers=headers)
