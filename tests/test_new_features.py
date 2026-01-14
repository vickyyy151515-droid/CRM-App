"""
Test suite for CRM Enhancement Features:
1. Edit Product for DB Bonanza and Member WD CRM databases
2. Bulk operations (approve/reject requests, delete records)
3. Notification system endpoints
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://crm-dashboard-149.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STAFF_EMAIL,
        "password": STAFF_PASSWORD
    })
    assert response.status_code == 200, f"Staff login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_user_id(staff_token):
    """Get staff user ID"""
    response = requests.get(f"{BASE_URL}/api/auth/me", headers={
        "Authorization": f"Bearer {staff_token}"
    })
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="module")
def test_product(admin_token):
    """Create a test product for testing"""
    product_name = f"TEST_Product_{uuid.uuid4().hex[:8]}"
    response = requests.post(f"{BASE_URL}/api/products", 
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": product_name}
    )
    assert response.status_code == 200, f"Failed to create product: {response.text}"
    product = response.json()
    yield product
    # Cleanup - delete product
    requests.delete(f"{BASE_URL}/api/products/{product['id']}", 
        headers={"Authorization": f"Bearer {admin_token}"})


@pytest.fixture(scope="module")
def second_test_product(admin_token):
    """Create a second test product for edit product tests"""
    product_name = f"TEST_Product2_{uuid.uuid4().hex[:8]}"
    response = requests.post(f"{BASE_URL}/api/products", 
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": product_name}
    )
    assert response.status_code == 200, f"Failed to create second product: {response.text}"
    product = response.json()
    yield product
    # Cleanup
    requests.delete(f"{BASE_URL}/api/products/{product['id']}", 
        headers={"Authorization": f"Bearer {admin_token}"})


class TestNotificationEndpoints:
    """Test notification system endpoints"""
    
    def test_get_notifications_admin(self, admin_token):
        """GET /api/notifications - Admin can get notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        assert isinstance(data["unread_count"], int)
        print(f"✓ Admin has {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_get_notifications_staff(self, staff_token):
        """GET /api/notifications - Staff can get notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {staff_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        print(f"✓ Staff has {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_get_notifications_with_limit(self, admin_token):
        """GET /api/notifications?limit=5 - Limit parameter works"""
        response = requests.get(f"{BASE_URL}/api/notifications?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) <= 5
        print(f"✓ Limit parameter works, got {len(data['notifications'])} notifications")
    
    def test_get_notifications_unread_only(self, admin_token):
        """GET /api/notifications?unread_only=true - Filter unread works"""
        response = requests.get(f"{BASE_URL}/api/notifications?unread_only=true",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        data = response.json()
        # All returned notifications should be unread
        for notif in data["notifications"]:
            assert notif.get("read") == False
        print(f"✓ Unread filter works, got {len(data['notifications'])} unread notifications")
    
    def test_mark_all_notifications_read(self, admin_token):
        """PATCH /api/notifications/read-all - Mark all as read"""
        response = requests.patch(f"{BASE_URL}/api/notifications/read-all",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Mark all read: {data['message']}")
    
    def test_mark_notification_read_not_found(self, admin_token):
        """PATCH /api/notifications/{id}/read - Returns 404 for non-existent"""
        fake_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/notifications/{fake_id}/read",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent notification")
    
    def test_delete_notification_not_found(self, admin_token):
        """DELETE /api/notifications/{id} - Returns 404 for non-existent"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(f"{BASE_URL}/api/notifications/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent notification delete")


class TestEditProductBonanza:
    """Test Edit Product feature for DB Bonanza"""
    
    def test_edit_product_requires_admin(self, staff_token, test_product):
        """PATCH /api/bonanza/databases/{id}/product - Requires admin"""
        fake_db_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/bonanza/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"product_id": test_product["id"]})
        assert response.status_code == 403
        print("✓ Edit product requires admin access")
    
    def test_edit_product_invalid_product(self, admin_token):
        """PATCH /api/bonanza/databases/{id}/product - Invalid product returns 404"""
        fake_db_id = str(uuid.uuid4())
        fake_product_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/bonanza/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"product_id": fake_product_id})
        assert response.status_code == 404
        assert "Product not found" in response.json().get("detail", "")
        print("✓ Invalid product returns 404")
    
    def test_edit_product_invalid_database(self, admin_token, test_product):
        """PATCH /api/bonanza/databases/{id}/product - Invalid database returns 404"""
        fake_db_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/bonanza/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"product_id": test_product["id"]})
        assert response.status_code == 404
        assert "Database not found" in response.json().get("detail", "")
        print("✓ Invalid database returns 404")


class TestEditProductMemberWD:
    """Test Edit Product feature for Member WD CRM"""
    
    def test_edit_product_requires_admin(self, staff_token, test_product):
        """PATCH /api/memberwd/databases/{id}/product - Requires admin"""
        fake_db_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/memberwd/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"product_id": test_product["id"]})
        assert response.status_code == 403
        print("✓ Edit product requires admin access")
    
    def test_edit_product_invalid_product(self, admin_token):
        """PATCH /api/memberwd/databases/{id}/product - Invalid product returns 404"""
        fake_db_id = str(uuid.uuid4())
        fake_product_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/memberwd/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"product_id": fake_product_id})
        assert response.status_code == 404
        assert "Product not found" in response.json().get("detail", "")
        print("✓ Invalid product returns 404")
    
    def test_edit_product_invalid_database(self, admin_token, test_product):
        """PATCH /api/memberwd/databases/{id}/product - Invalid database returns 404"""
        fake_db_id = str(uuid.uuid4())
        response = requests.patch(f"{BASE_URL}/api/memberwd/databases/{fake_db_id}/product",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"product_id": test_product["id"]})
        assert response.status_code == 404
        assert "Database not found" in response.json().get("detail", "")
        print("✓ Invalid database returns 404")


class TestBulkRequestOperations:
    """Test bulk approve/reject for download requests"""
    
    def test_bulk_requests_requires_admin(self, staff_token):
        """POST /api/bulk/requests - Requires admin"""
        response = requests.post(f"{BASE_URL}/api/bulk/requests",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"request_ids": [], "action": "approve"})
        assert response.status_code == 403
        print("✓ Bulk requests requires admin access")
    
    def test_bulk_requests_invalid_action(self, admin_token):
        """POST /api/bulk/requests - Invalid action returns 400"""
        response = requests.post(f"{BASE_URL}/api/bulk/requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"request_ids": [], "action": "invalid"})
        assert response.status_code == 400
        assert "approve" in response.json().get("detail", "").lower() or "reject" in response.json().get("detail", "").lower()
        print("✓ Invalid action returns 400")
    
    def test_bulk_approve_empty_list(self, admin_token):
        """POST /api/bulk/requests - Empty list returns success with 0 processed"""
        response = requests.post(f"{BASE_URL}/api/bulk/requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"request_ids": [], "action": "approve"})
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 0
        print("✓ Empty list returns success with 0 processed")
    
    def test_bulk_reject_empty_list(self, admin_token):
        """POST /api/bulk/requests - Empty reject list returns success"""
        response = requests.post(f"{BASE_URL}/api/bulk/requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"request_ids": [], "action": "reject"})
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 0
        print("✓ Empty reject list returns success with 0 processed")
    
    def test_bulk_approve_nonexistent_requests(self, admin_token):
        """POST /api/bulk/requests - Non-existent requests return errors"""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = requests.post(f"{BASE_URL}/api/bulk/requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"request_ids": fake_ids, "action": "approve"})
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 0
        assert len(data["errors"]) == 2
        print(f"✓ Non-existent requests return errors: {data['errors']}")


class TestBulkDeleteRecords:
    """Test bulk delete records for Bonanza and MemberWD"""
    
    def test_bulk_delete_bonanza_requires_admin(self, staff_token):
        """DELETE /api/bulk/bonanza-records - Requires admin"""
        response = requests.delete(f"{BASE_URL}/api/bulk/bonanza-records",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"record_ids": []})
        assert response.status_code == 403
        print("✓ Bulk delete bonanza requires admin access")
    
    def test_bulk_delete_memberwd_requires_admin(self, staff_token):
        """DELETE /api/bulk/memberwd-records - Requires admin"""
        response = requests.delete(f"{BASE_URL}/api/bulk/memberwd-records",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"record_ids": []})
        assert response.status_code == 403
        print("✓ Bulk delete memberwd requires admin access")
    
    def test_bulk_delete_bonanza_empty_list(self, admin_token):
        """DELETE /api/bulk/bonanza-records - Empty list returns 0 deleted"""
        response = requests.delete(f"{BASE_URL}/api/bulk/bonanza-records",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"record_ids": []})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        print("✓ Empty bonanza delete returns 0 deleted")
    
    def test_bulk_delete_memberwd_empty_list(self, admin_token):
        """DELETE /api/bulk/memberwd-records - Empty list returns 0 deleted"""
        response = requests.delete(f"{BASE_URL}/api/bulk/memberwd-records",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"record_ids": []})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        print("✓ Empty memberwd delete returns 0 deleted")
    
    def test_bulk_delete_bonanza_nonexistent(self, admin_token):
        """DELETE /api/bulk/bonanza-records - Non-existent IDs return 0 deleted"""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = requests.delete(f"{BASE_URL}/api/bulk/bonanza-records",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"record_ids": fake_ids})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        print("✓ Non-existent bonanza IDs return 0 deleted")
    
    def test_bulk_delete_memberwd_nonexistent(self, admin_token):
        """DELETE /api/bulk/memberwd-records - Non-existent IDs return 0 deleted"""
        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        response = requests.delete(f"{BASE_URL}/api/bulk/memberwd-records",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"record_ids": fake_ids})
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 0
        print("✓ Non-existent memberwd IDs return 0 deleted")


class TestExistingEndpointsStillWork:
    """Verify existing endpoints still work after new features"""
    
    def test_get_products(self, admin_token):
        """GET /api/products - Still works"""
        response = requests.get(f"{BASE_URL}/api/products",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ GET /api/products works, found {len(response.json())} products")
    
    def test_get_bonanza_databases(self, admin_token):
        """GET /api/bonanza/databases - Still works"""
        response = requests.get(f"{BASE_URL}/api/bonanza/databases",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ GET /api/bonanza/databases works, found {len(response.json())} databases")
    
    def test_get_memberwd_databases(self, admin_token):
        """GET /api/memberwd/databases - Still works"""
        response = requests.get(f"{BASE_URL}/api/memberwd/databases",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ GET /api/memberwd/databases works, found {len(response.json())} databases")
    
    def test_get_download_requests(self, admin_token):
        """GET /api/download-requests - Still works"""
        response = requests.get(f"{BASE_URL}/api/download-requests",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ GET /api/download-requests works, found {len(response.json())} requests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
