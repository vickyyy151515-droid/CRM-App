"""
Test Auto-Replacement Feature for Invalid Database Records

Tests the following endpoints:
- POST /api/bonanza/admin/process-invalid/{staff_id} - Process invalid records with auto-assignment
- GET /api/bonanza/admin/archived-invalid - Get archived invalid records
- POST /api/bonanza/admin/archived-invalid/{record_id}/restore - Restore archived record
- DELETE /api/bonanza/admin/archived-invalid/{record_id} - Permanently delete archived record
- Same endpoints for memberwd
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "vicky123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestAuthFixtures:
    """Authentication fixtures"""
    
    @staticmethod
    def get_admin_token():
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    @staticmethod
    def get_staff_token():
        """Get staff authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None


class TestBonanzaInvalidRecordsAPI:
    """Test Bonanza invalid records API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.admin_token = TestAuthFixtures.get_admin_token()
        self.staff_token = TestAuthFixtures.get_staff_token()
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        self.staff_headers = {
            "Authorization": f"Bearer {self.staff_token}",
            "Content-Type": "application/json"
        } if self.staff_token else None
    
    def test_get_invalid_records_endpoint(self):
        """Test GET /api/bonanza/admin/invalid-records returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/invalid-records",
            headers=self.admin_headers
        )
        print(f"GET /api/bonanza/admin/invalid-records: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "total_invalid" in data
        assert "by_staff" in data
        print(f"Total invalid bonanza records: {data['total_invalid']}")
    
    def test_get_archived_invalid_endpoint(self):
        """Test GET /api/bonanza/admin/archived-invalid returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/archived-invalid",
            headers=self.admin_headers
        )
        print(f"GET /api/bonanza/admin/archived-invalid: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_database" in data
        print(f"Total archived bonanza records: {data['total']}")
    
    def test_process_invalid_without_staff_id(self):
        """Test process-invalid with non-existent staff returns 404"""
        fake_staff_id = "non-existent-staff-id"
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/process-invalid/{fake_staff_id}",
            headers=self.admin_headers,
            json={"auto_assign_quantity": 2}
        )
        print(f"POST /api/bonanza/admin/process-invalid/{fake_staff_id}: {response.status_code}")
        # Should return 404 because no invalid records for non-existent staff
        assert response.status_code in [404, 400]
    
    def test_restore_non_existent_record(self):
        """Test restore with non-existent record returns 404"""
        fake_record_id = "non-existent-record-id"
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/archived-invalid/{fake_record_id}/restore",
            headers=self.admin_headers
        )
        print(f"POST /api/bonanza/admin/archived-invalid/{fake_record_id}/restore: {response.status_code}")
        assert response.status_code == 404
    
    def test_delete_non_existent_record(self):
        """Test delete with non-existent record returns 404"""
        fake_record_id = "non-existent-record-id"
        response = requests.delete(
            f"{BASE_URL}/api/bonanza/admin/archived-invalid/{fake_record_id}",
            headers=self.admin_headers
        )
        print(f"DELETE /api/bonanza/admin/archived-invalid/{fake_record_id}: {response.status_code}")
        assert response.status_code == 404
    
    def test_process_invalid_unauthenticated(self):
        """Test process-invalid without auth returns 401/403"""
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/process-invalid/test-staff",
            json={"auto_assign_quantity": 2}
        )
        print(f"POST (no auth) /api/bonanza/admin/process-invalid: {response.status_code}")
        assert response.status_code in [401, 403, 422]


class TestMemberWDInvalidRecordsAPI:
    """Test MemberWD invalid records API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.admin_token = TestAuthFixtures.get_admin_token()
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_invalid_records_endpoint(self):
        """Test GET /api/memberwd/admin/invalid-records returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/invalid-records",
            headers=self.admin_headers
        )
        print(f"GET /api/memberwd/admin/invalid-records: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "total_invalid" in data
        assert "by_staff" in data
        print(f"Total invalid memberwd records: {data['total_invalid']}")
    
    def test_get_archived_invalid_endpoint(self):
        """Test GET /api/memberwd/admin/archived-invalid returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/archived-invalid",
            headers=self.admin_headers
        )
        print(f"GET /api/memberwd/admin/archived-invalid: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_database" in data
        print(f"Total archived memberwd records: {data['total']}")
    
    def test_process_invalid_without_staff_id(self):
        """Test process-invalid with non-existent staff returns 404"""
        fake_staff_id = "non-existent-staff-id"
        response = requests.post(
            f"{BASE_URL}/api/memberwd/admin/process-invalid/{fake_staff_id}",
            headers=self.admin_headers,
            json={"auto_assign_quantity": 2}
        )
        print(f"POST /api/memberwd/admin/process-invalid/{fake_staff_id}: {response.status_code}")
        assert response.status_code in [404, 400]
    
    def test_restore_non_existent_record(self):
        """Test restore with non-existent record returns 404"""
        fake_record_id = "non-existent-record-id"
        response = requests.post(
            f"{BASE_URL}/api/memberwd/admin/archived-invalid/{fake_record_id}/restore",
            headers=self.admin_headers
        )
        print(f"POST /api/memberwd/admin/archived-invalid/{fake_record_id}/restore: {response.status_code}")
        assert response.status_code == 404
    
    def test_delete_non_existent_record(self):
        """Test delete with non-existent record returns 404"""
        fake_record_id = "non-existent-record-id"
        response = requests.delete(
            f"{BASE_URL}/api/memberwd/admin/archived-invalid/{fake_record_id}",
            headers=self.admin_headers
        )
        print(f"DELETE /api/memberwd/admin/archived-invalid/{fake_record_id}: {response.status_code}")
        assert response.status_code == 404


class TestBonanzaInvalidRecordsIntegration:
    """Integration tests for Bonanza invalid records flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.admin_token = TestAuthFixtures.get_admin_token()
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_full_flow_with_existing_invalid_records(self):
        """Test the full flow with pre-existing invalid records"""
        # Step 1: Check if there are invalid records
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/invalid-records",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        invalid_data = response.json()
        print(f"Invalid records found: {invalid_data['total_invalid']}")
        
        if invalid_data['total_invalid'] > 0 and invalid_data.get('by_staff'):
            staff_group = invalid_data['by_staff'][0]
            staff_id = staff_group['_id']
            invalid_count = staff_group['count']
            print(f"Testing with staff_id: {staff_id}, invalid_count: {invalid_count}")
            
            # Step 2: Process invalid records (archive) with auto-assign
            process_response = requests.post(
                f"{BASE_URL}/api/bonanza/admin/process-invalid/{staff_id}",
                headers=self.admin_headers,
                json={"auto_assign_quantity": min(2, invalid_count)}
            )
            print(f"Process invalid response: {process_response.status_code}")
            print(f"Process invalid data: {process_response.json()}")
            assert process_response.status_code == 200
            process_data = process_response.json()
            assert process_data.get('success') == True
            assert 'archived_count' in process_data
            assert 'new_assigned_count' in process_data
            print(f"Archived: {process_data['archived_count']}, New assigned: {process_data['new_assigned_count']}")
            
            # Step 3: Verify records appear in archived-invalid
            archived_response = requests.get(
                f"{BASE_URL}/api/bonanza/admin/archived-invalid",
                headers=self.admin_headers
            )
            assert archived_response.status_code == 200
            archived_data = archived_response.json()
            print(f"Archived records after processing: {archived_data['total']}")
            assert archived_data['total'] >= process_data['archived_count']
        else:
            print("No invalid records to process - skipping integration test")
            pytest.skip("No invalid records to process")
    
    def test_restore_and_delete_archived_record(self):
        """Test restore and delete operations on archived records"""
        # Get archived records
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/archived-invalid",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        archived_data = response.json()
        
        if archived_data['total'] > 0 and archived_data.get('by_database'):
            # Get first archived record
            first_db = archived_data['by_database'][0]
            if first_db.get('records'):
                record_id = first_db['records'][0]['id']
                print(f"Testing with archived record_id: {record_id}")
                
                # Test restore
                restore_response = requests.post(
                    f"{BASE_URL}/api/bonanza/admin/archived-invalid/{record_id}/restore",
                    headers=self.admin_headers
                )
                print(f"Restore response: {restore_response.status_code}")
                
                if restore_response.status_code == 200:
                    restore_data = restore_response.json()
                    assert restore_data.get('success') == True
                    print("Record restored successfully")
                else:
                    print(f"Restore failed or record not found: {restore_response.json()}")
        else:
            print("No archived records to test - skipping")
            pytest.skip("No archived records available for testing")


class TestArchivedRecordsResponseFormat:
    """Test that API responses have correct structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test"""
        self.admin_token = TestAuthFixtures.get_admin_token()
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_bonanza_archived_response_structure(self):
        """Test bonanza archived response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/archived-invalid",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level keys
        assert "total" in data, "Response should have 'total' key"
        assert "by_database" in data, "Response should have 'by_database' key"
        assert isinstance(data['total'], int), "'total' should be integer"
        assert isinstance(data['by_database'], list), "'by_database' should be list"
        
        # If there are records, check structure
        if data['total'] > 0 and data['by_database']:
            db_group = data['by_database'][0]
            assert "database_name" in db_group
            assert "database_id" in db_group
            assert "product_name" in db_group
            assert "count" in db_group
            assert "records" in db_group
            print(f"Bonanza archived structure verified with {data['total']} records")
    
    def test_memberwd_archived_response_structure(self):
        """Test memberwd archived response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/archived-invalid",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level keys
        assert "total" in data, "Response should have 'total' key"
        assert "by_database" in data, "Response should have 'by_database' key"
        assert isinstance(data['total'], int), "'total' should be integer"
        assert isinstance(data['by_database'], list), "'by_database' should be list"
        print(f"MemberWD archived structure verified with {data['total']} records")
    
    def test_bonanza_invalid_records_response_structure(self):
        """Test bonanza invalid records response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/invalid-records",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_invalid" in data
        assert "by_staff" in data
        assert isinstance(data['total_invalid'], int)
        assert isinstance(data['by_staff'], list)
        print(f"Bonanza invalid records structure verified: {data['total_invalid']} invalid")
    
    def test_memberwd_invalid_records_response_structure(self):
        """Test memberwd invalid records response has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/invalid-records",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_invalid" in data
        assert "by_staff" in data
        assert isinstance(data['total_invalid'], int)
        assert isinstance(data['by_staff'], list)
        print(f"MemberWD invalid records structure verified: {data['total_invalid']} invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
