"""
Test Pin Batches Feature - P1 CRM Feature
Tests the PATCH /api/my-request-batches/{batch_id}/pin endpoint and GET /api/my-request-batches sorting
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STAFF_EMAIL,
        "password": STAFF_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Staff authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def staff_client(staff_token):
    """Requests session with staff auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {staff_token}"
    })
    return session


@pytest.fixture
def admin_client(admin_token):
    """Requests session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


class TestPinBatchesEndpoint:
    """Test PATCH /api/my-request-batches/{batch_id}/pin endpoint"""
    
    def test_pin_endpoint_requires_auth(self):
        """Test that pin endpoint requires authentication"""
        response = requests.patch(
            f"{BASE_URL}/api/my-request-batches/test-batch-id/pin",
            json={"is_pinned": True}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Pin endpoint requires authentication")
    
    def test_pin_endpoint_staff_only(self, admin_client):
        """Test that pin endpoint is staff-only (admin should get 403)"""
        response = admin_client.patch(
            f"{BASE_URL}/api/my-request-batches/test-batch-id/pin",
            json={"is_pinned": True}
        )
        assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
        print("✓ Pin endpoint is staff-only")
    
    def test_pin_batch_not_found(self, staff_client):
        """Test pinning a non-existent batch returns 404"""
        response = staff_client.patch(
            f"{BASE_URL}/api/my-request-batches/non-existent-batch-id/pin",
            json={"is_pinned": True}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent batch returns 404")


class TestGetMyRequestBatches:
    """Test GET /api/my-request-batches endpoint with is_pinned field and sorting"""
    
    def test_get_batches_requires_auth(self):
        """Test that get batches endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Get batches endpoint requires authentication")
    
    def test_get_batches_staff_only(self, admin_client):
        """Test that get batches endpoint is staff-only"""
        response = admin_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 403, f"Expected 403 for admin, got {response.status_code}"
        print("✓ Get batches endpoint is staff-only")
    
    def test_get_batches_returns_is_pinned_field(self, staff_client):
        """Test that batches include is_pinned field"""
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        batches = response.json()
        print(f"Found {len(batches)} batches")
        
        # Check that all batches have is_pinned field
        for batch in batches:
            assert 'is_pinned' in batch, f"Batch {batch.get('id')} missing is_pinned field"
            assert isinstance(batch['is_pinned'], bool), f"is_pinned should be boolean, got {type(batch['is_pinned'])}"
        
        print("✓ All batches have is_pinned field (boolean)")
    
    def test_batches_sorted_pinned_first(self, staff_client):
        """Test that pinned batches appear first in the list"""
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200
        
        batches = response.json()
        if len(batches) < 2:
            pytest.skip("Need at least 2 batches to test sorting")
        
        # Check sorting: all pinned batches should come before non-pinned
        found_non_pinned = False
        for batch in batches:
            if not batch.get('is_pinned', False):
                found_non_pinned = True
            elif found_non_pinned:
                # Found a pinned batch after a non-pinned one - sorting is wrong
                pytest.fail("Pinned batches should appear before non-pinned batches")
        
        print("✓ Batches are sorted with pinned first")


class TestPinToggleFunctionality:
    """Test the full pin/unpin toggle flow"""
    
    def test_pin_and_unpin_batch(self, staff_client):
        """Test pinning and unpinning a batch"""
        # First get available batches
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200
        
        batches = response.json()
        if not batches:
            pytest.skip("No batches available for staff user to test pin functionality")
        
        # Get first batch
        batch = batches[0]
        batch_id = batch['id']
        original_pin_status = batch.get('is_pinned', False)
        
        print(f"Testing with batch {batch_id}, original pin status: {original_pin_status}")
        
        # Toggle pin status
        new_pin_status = not original_pin_status
        response = staff_client.patch(
            f"{BASE_URL}/api/my-request-batches/{batch_id}/pin",
            json={"is_pinned": new_pin_status}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'message' in data, "Response should contain message"
        assert data.get('is_pinned') == new_pin_status, f"Expected is_pinned={new_pin_status}, got {data.get('is_pinned')}"
        print(f"✓ Pin status toggled to {new_pin_status}")
        
        # Verify by fetching batches again
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200
        
        batches = response.json()
        updated_batch = next((b for b in batches if b['id'] == batch_id), None)
        assert updated_batch is not None, f"Batch {batch_id} not found after update"
        assert updated_batch['is_pinned'] == new_pin_status, f"Pin status not persisted correctly"
        print(f"✓ Pin status persisted correctly")
        
        # Restore original status
        response = staff_client.patch(
            f"{BASE_URL}/api/my-request-batches/{batch_id}/pin",
            json={"is_pinned": original_pin_status}
        )
        assert response.status_code == 200
        print(f"✓ Restored original pin status: {original_pin_status}")


class TestLegacyBatchPinning:
    """Test pinning legacy batches (stored in batch_titles collection)"""
    
    def test_pin_legacy_batch(self, staff_client):
        """Test pinning a legacy batch (batch_id starts with 'legacy_')"""
        # First get batches to find a legacy one
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200
        
        batches = response.json()
        legacy_batch = next((b for b in batches if b['id'].startswith('legacy_')), None)
        
        if not legacy_batch:
            # Create a test for legacy batch format even if none exist
            # The endpoint should handle legacy_ prefix batches via batch_titles collection
            print("No legacy batches found - testing endpoint handles legacy format")
            
            # Test that the endpoint accepts legacy_ prefix (will create entry in batch_titles)
            response = staff_client.patch(
                f"{BASE_URL}/api/my-request-batches/legacy_test-db-id/pin",
                json={"is_pinned": True}
            )
            # Should succeed (upsert behavior)
            assert response.status_code == 200, f"Expected 200 for legacy batch, got {response.status_code}"
            print("✓ Legacy batch pin endpoint works (upsert behavior)")
            
            # Clean up - unpin
            staff_client.patch(
                f"{BASE_URL}/api/my-request-batches/legacy_test-db-id/pin",
                json={"is_pinned": False}
            )
        else:
            batch_id = legacy_batch['id']
            original_status = legacy_batch.get('is_pinned', False)
            
            # Toggle pin
            response = staff_client.patch(
                f"{BASE_URL}/api/my-request-batches/{batch_id}/pin",
                json={"is_pinned": not original_status}
            )
            assert response.status_code == 200
            print(f"✓ Legacy batch {batch_id} pin toggled")
            
            # Restore
            staff_client.patch(
                f"{BASE_URL}/api/my-request-batches/{batch_id}/pin",
                json={"is_pinned": original_status}
            )


class TestBatchResponseStructure:
    """Test the complete response structure of batches"""
    
    def test_batch_has_required_fields(self, staff_client):
        """Test that batch response has all required fields including is_pinned"""
        response = staff_client.get(f"{BASE_URL}/api/my-request-batches")
        assert response.status_code == 200
        
        batches = response.json()
        if not batches:
            pytest.skip("No batches available to test structure")
        
        required_fields = [
            'id', 'database_id', 'database_name', 'product_name',
            'is_pinned', 'record_count', 'ada_count', 'ceklis1_count',
            'tidak_count', 'respond_ya_count', 'respond_tidak_count'
        ]
        
        batch = batches[0]
        for field in required_fields:
            assert field in batch, f"Missing required field: {field}"
        
        print(f"✓ Batch has all required fields: {required_fields}")
        print(f"  Sample batch: id={batch['id']}, is_pinned={batch['is_pinned']}, record_count={batch['record_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
