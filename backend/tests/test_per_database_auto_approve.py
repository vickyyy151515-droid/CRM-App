"""
Test Per-Database Auto-Approve Feature for Download Requests

Tests cover:
1. Setting auto_approve=false stores False (bool) in MongoDB
2. Setting auto_approve=true stores True (bool) in MongoDB
3. GET /api/databases returns auto_approve field for each database
4. When database auto_approve=false AND global toggle ON, staff POST /api/download-requests returns status=pending
5. When database auto_approve=true AND global toggle ON, staff POST /api/download-requests returns status=approved
6. When global toggle OFF, ALL requests return status=pending regardless of per-database setting
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"

# Test database ID (ted db liga 1.xlsx with 150 records)
TEST_DATABASE_ID = "84c66ca8-c707-45f6-91fa-5c0b176edbb9"


class TestPerDatabaseAutoApprove:
    """Tests for per-database auto-approve feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth tokens"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Get admin token
        admin_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        self.admin_token = admin_login.json().get("token")
        
        # Get staff token
        staff_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert staff_login.status_code == 200, f"Staff login failed: {staff_login.text}"
        self.staff_token = staff_login.json().get("token")
        
        yield
        
        # Cleanup: Reset database to default (None) after tests
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        # Set to None (global default) - first set to True, then toggle twice to get to None
        self.session.put(f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set")
    
    def test_01_set_auto_approve_false_stores_bool_false(self):
        """Test: PUT /api/databases/{id}/auto-approve/set?auto_approve=false stores False (bool) in MongoDB"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Set auto_approve to false
        response = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=false"
        )
        
        assert response.status_code == 200, f"Set auto_approve=false failed: {response.text}"
        data = response.json()
        
        # Verify the response contains auto_approve=False (bool)
        assert 'auto_approve' in data, "Response missing auto_approve field"
        assert data['auto_approve'] is False, f"Expected auto_approve=False, got {data['auto_approve']}"
        assert data['message'] == 'Database set to: Manual Approval'
        
        print("✓ Backend: PUT /api/databases/{id}/auto-approve/set?auto_approve=false stores False (bool)")
    
    def test_02_set_auto_approve_true_stores_bool_true(self):
        """Test: PUT /api/databases/{id}/auto-approve/set?auto_approve=true stores True (bool) in MongoDB"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Set auto_approve to true
        response = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=true"
        )
        
        assert response.status_code == 200, f"Set auto_approve=true failed: {response.text}"
        data = response.json()
        
        # Verify the response contains auto_approve=True (bool)
        assert 'auto_approve' in data, "Response missing auto_approve field"
        assert data['auto_approve'] is True, f"Expected auto_approve=True, got {data['auto_approve']}"
        assert data['message'] == 'Database set to: Auto-Approve'
        
        print("✓ Backend: PUT /api/databases/{id}/auto-approve/set?auto_approve=true stores True (bool)")
    
    def test_03_get_databases_returns_auto_approve_field(self):
        """Test: GET /api/databases returns auto_approve field in response for each database"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # First, set auto_approve to true to ensure we have a value
        set_resp = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=true"
        )
        assert set_resp.status_code == 200
        
        # Get databases list
        response = self.session.get(f"{BASE_URL}/api/databases")
        
        assert response.status_code == 200, f"GET /api/databases failed: {response.text}"
        databases = response.json()
        
        assert len(databases) > 0, "No databases returned"
        
        # Find our test database
        test_db = next((db for db in databases if db['id'] == TEST_DATABASE_ID), None)
        assert test_db is not None, f"Test database {TEST_DATABASE_ID} not found in response"
        
        # Verify auto_approve field exists (can be True, False, or None)
        assert 'auto_approve' in test_db, f"auto_approve field missing from database response: {test_db.keys()}"
        assert test_db['auto_approve'] is True, f"Expected auto_approve=True, got {test_db['auto_approve']}"
        
        print(f"✓ Backend: GET /api/databases returns auto_approve field (value={test_db['auto_approve']})")
    
    def test_04_manual_database_with_global_on_returns_pending(self):
        """Test: When database auto_approve=false AND global toggle ON, staff POST /api/download-requests returns status=pending"""
        # Step 1: As admin, turn ON global auto-approve
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        global_resp = self.session.put(f"{BASE_URL}/api/settings/auto-approve", json={
            "enabled": True,
            "max_records_per_request": None
        })
        assert global_resp.status_code == 200, f"Failed to enable global auto-approve: {global_resp.text}"
        
        # Step 2: Set database to Manual (auto_approve=false)
        set_resp = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=false"
        )
        assert set_resp.status_code == 200, f"Failed to set database to Manual: {set_resp.text}"
        
        # Step 3: As staff, create download request
        self.session.headers.update({"Authorization": f"Bearer {self.staff_token}"})
        
        request_resp = self.session.post(f"{BASE_URL}/api/download-requests", json={
            "database_id": TEST_DATABASE_ID,
            "record_count": 1
        })
        
        assert request_resp.status_code == 200, f"Download request failed: {request_resp.text}"
        request_data = request_resp.json()
        
        # Verify status is PENDING (not auto-approved)
        assert request_data['status'] == 'pending', \
            f"Expected status=pending for Manual database with Global ON, got {request_data['status']}"
        
        print("✓ Backend: Database auto_approve=false AND global ON → status=pending")
    
    def test_05_auto_database_with_global_on_returns_approved(self):
        """Test: When database auto_approve=true AND global toggle ON, staff POST /api/download-requests returns status=approved"""
        # Step 1: As admin, turn ON global auto-approve
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        global_resp = self.session.put(f"{BASE_URL}/api/settings/auto-approve", json={
            "enabled": True,
            "max_records_per_request": None
        })
        assert global_resp.status_code == 200, f"Failed to enable global auto-approve: {global_resp.text}"
        
        # Step 2: Set database to Auto-Approve (auto_approve=true)
        set_resp = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=true"
        )
        assert set_resp.status_code == 200, f"Failed to set database to Auto: {set_resp.text}"
        
        # Step 3: As staff, create download request
        self.session.headers.update({"Authorization": f"Bearer {self.staff_token}"})
        
        request_resp = self.session.post(f"{BASE_URL}/api/download-requests", json={
            "database_id": TEST_DATABASE_ID,
            "record_count": 1
        })
        
        assert request_resp.status_code == 200, f"Download request failed: {request_resp.text}"
        request_data = request_resp.json()
        
        # Verify status is APPROVED (auto-approved)
        assert request_data['status'] == 'approved', \
            f"Expected status=approved for Auto database with Global ON, got {request_data['status']}"
        
        print("✓ Backend: Database auto_approve=true AND global ON → status=approved")
    
    def test_06_global_off_returns_pending_regardless_of_per_database(self):
        """Test: When global toggle OFF, ALL requests return status=pending regardless of per-database setting"""
        # Step 1: As admin, turn OFF global auto-approve
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        global_resp = self.session.put(f"{BASE_URL}/api/settings/auto-approve", json={
            "enabled": False,
            "max_records_per_request": None
        })
        assert global_resp.status_code == 200, f"Failed to disable global auto-approve: {global_resp.text}"
        
        # Step 2: Set database to Auto-Approve (auto_approve=true)
        set_resp = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=true"
        )
        assert set_resp.status_code == 200, f"Failed to set database to Auto: {set_resp.text}"
        
        # Step 3: As staff, create download request
        self.session.headers.update({"Authorization": f"Bearer {self.staff_token}"})
        
        request_resp = self.session.post(f"{BASE_URL}/api/download-requests", json={
            "database_id": TEST_DATABASE_ID,
            "record_count": 1
        })
        
        assert request_resp.status_code == 200, f"Download request failed: {request_resp.text}"
        request_data = request_resp.json()
        
        # Verify status is PENDING (global OFF overrides per-database)
        assert request_data['status'] == 'pending', \
            f"Expected status=pending when Global OFF (even with per-db=Auto), got {request_data['status']}"
        
        print("✓ Backend: Global OFF → status=pending (regardless of per-database setting)")
    
    def test_07_database_none_follows_global_setting(self):
        """Test: When database auto_approve=None (not set), it follows global setting"""
        # Step 1: As admin, turn ON global auto-approve
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        global_resp = self.session.put(f"{BASE_URL}/api/settings/auto-approve", json={
            "enabled": True,
            "max_records_per_request": None
        })
        assert global_resp.status_code == 200
        
        # Step 2: Reset database to None (use global default)
        set_resp = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set"
        )
        # Note: Without auto_approve param, should set to None
        assert set_resp.status_code == 200
        
        # Step 3: As staff, create download request
        self.session.headers.update({"Authorization": f"Bearer {self.staff_token}"})
        
        request_resp = self.session.post(f"{BASE_URL}/api/download-requests", json={
            "database_id": TEST_DATABASE_ID,
            "record_count": 1
        })
        
        assert request_resp.status_code == 200, f"Download request failed: {request_resp.text}"
        request_data = request_resp.json()
        
        # With global ON and per-db None, should be auto-approved
        assert request_data['status'] == 'approved', \
            f"Expected status=approved (per-db=None follows Global=ON), got {request_data['status']}"
        
        print("✓ Backend: Database auto_approve=None follows global setting (Global ON → approved)")
    
    def test_08_verify_auto_approve_persisted_in_mongodb(self):
        """Test: Verify auto_approve value persists correctly after set operations"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Set to false
        resp1 = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=false"
        )
        assert resp1.status_code == 200
        
        # Get database to verify persisted value
        get_resp = self.session.get(f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}")
        assert get_resp.status_code == 200
        db_data = get_resp.json()
        assert db_data.get('auto_approve') is False, f"Persisted value should be False, got {db_data.get('auto_approve')}"
        
        # Set to true
        resp2 = self.session.put(
            f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}/auto-approve/set?auto_approve=true"
        )
        assert resp2.status_code == 200
        
        # Verify again
        get_resp2 = self.session.get(f"{BASE_URL}/api/databases/{TEST_DATABASE_ID}")
        assert get_resp2.status_code == 200
        db_data2 = get_resp2.json()
        assert db_data2.get('auto_approve') is True, f"Persisted value should be True, got {db_data2.get('auto_approve')}"
        
        print("✓ Backend: auto_approve value correctly persisted in MongoDB (verified via GET)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
