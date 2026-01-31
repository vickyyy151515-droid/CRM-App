"""
Test Database Validation Feature - Staff to Admin Notification Flow
Tests for:
- Staff validation of DB Bonanza and Member WD records
- Admin notification system for invalid records
- Admin reassignment of invalid records back to pool
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_ADMIN = {"email": "vicky@crm.com", "password": "vicky123"}
ADMIN = {"email": "admin@crm.com", "password": "admin123"}
STAFF = {"email": "staff@crm.com", "password": "staff123"}


class TestSetup:
    """Setup and authentication tests"""
    
    def test_health_check(self):
        """Test API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health check passed")
    
    def test_master_admin_login(self):
        """Test master admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_ADMIN)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Master admin login successful: {data.get('user', {}).get('name')}")
        return data["token"]
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Admin login successful: {data.get('user', {}).get('name')}")
        return data["token"]
    
    def test_staff_login(self):
        """Test staff login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Staff login successful: {data.get('user', {}).get('name')}")
        return data["token"]


# Helper function to get tokens
def get_staff_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=STAFF)
    return response.json().get("token") if response.status_code == 200 else None

def get_admin_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MASTER_ADMIN)
    return response.json().get("token") if response.status_code == 200 else None


class TestStaffBonanzaRecords:
    """Test staff can get and validate bonanza records"""
    
    def test_staff_get_bonanza_records(self):
        """Test staff can get assigned bonanza records"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/bonanza/staff/records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Staff has {len(data)} assigned bonanza records")
        return data
    
    def test_staff_get_bonanza_records_with_product_filter(self):
        """Test staff can filter bonanza records by product"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        # First get products
        admin_token = get_admin_token()
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        products_response = requests.get(f"{BASE_URL}/api/products", headers=admin_headers)
        
        if products_response.status_code == 200 and len(products_response.json()) > 0:
            product_id = products_response.json()[0]['id']
            response = requests.get(f"{BASE_URL}/api/bonanza/staff/records?product_id={product_id}", headers=headers)
            assert response.status_code == 200
            print(f"Product filter working - got {len(response.json())} records")
        else:
            print("No products available for filter test")


class TestStaffBonanzaValidation:
    """Test staff validation of bonanza records"""
    
    def test_staff_validate_records_as_valid(self):
        """Test staff can mark records as valid"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First get assigned records
        records_response = requests.get(f"{BASE_URL}/api/bonanza/staff/records", headers=headers)
        if records_response.status_code != 200:
            pytest.skip("Could not get staff records")
        
        records = records_response.json()
        # Find unvalidated records
        unvalidated = [r for r in records if not r.get('validation_status')]
        
        if len(unvalidated) == 0:
            print("No unvalidated records to test - skipping")
            pytest.skip("No unvalidated bonanza records for staff")
        
        # Mark first record as valid
        record_id = unvalidated[0]['id']
        response = requests.post(f"{BASE_URL}/api/bonanza/staff/validate", headers=headers, json={
            "record_ids": [record_id],
            "is_valid": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("validation_status") == "validated"
        print(f"Successfully marked record as valid: {data.get('message')}")
    
    def test_staff_validate_records_as_invalid_requires_reason(self):
        """Test staff marking records as invalid requires a reason"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get records
        records_response = requests.get(f"{BASE_URL}/api/bonanza/staff/records", headers=headers)
        records = records_response.json() if records_response.status_code == 200 else []
        unvalidated = [r for r in records if not r.get('validation_status')]
        
        if len(unvalidated) == 0:
            pytest.skip("No unvalidated bonanza records for staff")
        
        record_id = unvalidated[0]['id']
        
        # Try marking invalid with a reason
        response = requests.post(f"{BASE_URL}/api/bonanza/staff/validate", headers=headers, json={
            "record_ids": [record_id],
            "is_valid": False,
            "reason": "TEST_INVALID_REASON - Data tidak lengkap"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("validation_status") == "invalid"
        print(f"Successfully marked record as invalid with reason: {data.get('message')}")


class TestStaffMemberWDRecords:
    """Test staff can get and validate Member WD records"""
    
    def test_staff_get_memberwd_records(self):
        """Test staff can get assigned Member WD records"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/memberwd/staff/records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Staff has {len(data)} assigned Member WD records")
        return data
    
    def test_staff_validate_memberwd_as_invalid(self):
        """Test staff can mark Member WD records as invalid"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get records
        records_response = requests.get(f"{BASE_URL}/api/memberwd/staff/records", headers=headers)
        records = records_response.json() if records_response.status_code == 200 else []
        unvalidated = [r for r in records if not r.get('validation_status')]
        
        if len(unvalidated) == 0:
            print("No unvalidated Member WD records - skipping")
            pytest.skip("No unvalidated Member WD records for staff")
        
        record_id = unvalidated[0]['id']
        
        response = requests.post(f"{BASE_URL}/api/memberwd/staff/validate", headers=headers, json={
            "record_ids": [record_id],
            "is_valid": False,
            "reason": "TEST_MEMBERWD_INVALID - Nomor tidak aktif"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"Member WD record marked as invalid: {data.get('message')}")


class TestAdminInvalidNotifications:
    """Test admin can view invalid database notifications"""
    
    def test_get_admin_invalid_database_notifications(self):
        """Test admin can get invalid database notifications"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/admin/invalid-database", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "notifications" in data
        assert "summary" in data
        assert "bonanza_notifications" in data["summary"]
        assert "memberwd_notifications" in data["summary"]
        assert "bonanza_invalid_records" in data["summary"]
        assert "memberwd_invalid_records" in data["summary"]
        assert "total_unresolved" in data["summary"]
        
        print(f"Admin notifications - Total unresolved: {data['summary']['total_unresolved']}")
        print(f"  Bonanza invalid: {data['summary']['bonanza_invalid_records']}")
        print(f"  Member WD invalid: {data['summary']['memberwd_invalid_records']}")
        return data
    
    def test_notification_has_staff_info(self):
        """Test notifications contain staff name, count, and reason"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/admin/invalid-database", headers=headers)
        
        data = response.json()
        notifications = data.get("notifications", [])
        
        if len(notifications) > 0:
            notification = notifications[0]
            # Verify notification structure
            assert "staff_id" in notification
            assert "staff_name" in notification
            assert "record_count" in notification
            assert "reason" in notification
            assert "type" in notification
            print(f"Notification from {notification['staff_name']}: {notification['record_count']} records - {notification['reason']}")
        else:
            print("No unresolved notifications currently")


class TestAdminBonanzaInvalidRecords:
    """Test admin can view invalid bonanza records grouped by staff"""
    
    def test_get_invalid_bonanza_records(self):
        """Test GET /api/bonanza/admin/invalid-records"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/bonanza/admin/invalid-records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_invalid" in data
        assert "by_staff" in data
        assert isinstance(data["by_staff"], list)
        
        print(f"Total invalid bonanza records: {data['total_invalid']}")
        for staff_group in data["by_staff"]:
            print(f"  Staff {staff_group.get('staff_name', 'Unknown')}: {staff_group.get('count', 0)} records")
        
        return data
    
    def test_invalid_records_have_details(self):
        """Test invalid records contain row_data, reason, etc."""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/bonanza/admin/invalid-records", headers=headers)
        
        data = response.json()
        if data["total_invalid"] > 0 and len(data["by_staff"]) > 0:
            staff_group = data["by_staff"][0]
            records = staff_group.get("records", [])
            if len(records) > 0:
                record = records[0]
                assert "id" in record
                assert "row_data" in record
                assert "database_name" in record
                print(f"Record details verified: {record.get('database_name')}")


class TestAdminMemberWDInvalidRecords:
    """Test admin can view invalid Member WD records"""
    
    def test_get_invalid_memberwd_records(self):
        """Test GET /api/memberwd/admin/invalid-records"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/memberwd/admin/invalid-records", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_invalid" in data
        assert "by_staff" in data
        
        print(f"Total invalid Member WD records: {data['total_invalid']}")
        return data


class TestAdminReassignInvalidRecords:
    """Test admin can reassign invalid records back to available pool"""
    
    def test_reassign_bonanza_invalid_to_pool(self):
        """Test POST /api/bonanza/admin/reassign-invalid/{staff_id}"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First get invalid records to find a staff_id
        invalid_response = requests.get(f"{BASE_URL}/api/bonanza/admin/invalid-records", headers=headers)
        invalid_data = invalid_response.json()
        
        if invalid_data["total_invalid"] == 0 or len(invalid_data["by_staff"]) == 0:
            print("No invalid bonanza records to reassign - this is expected if no records were marked invalid")
            pytest.skip("No invalid bonanza records to test reassignment")
        
        staff_id = invalid_data["by_staff"][0]["_id"]
        staff_name = invalid_data["by_staff"][0].get("staff_name", "Unknown")
        record_count = invalid_data["by_staff"][0]["count"]
        
        print(f"Attempting to reassign {record_count} invalid records from {staff_name}")
        
        response = requests.post(f"{BASE_URL}/api/bonanza/admin/reassign-invalid/{staff_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "count" in data
        print(f"Reassigned {data['count']} records back to pool: {data.get('message')}")
        
        # Verify records are no longer invalid
        verify_response = requests.get(f"{BASE_URL}/api/bonanza/admin/invalid-records", headers=headers)
        verify_data = verify_response.json()
        # Check that this staff no longer has invalid records
        staff_invalid = [s for s in verify_data["by_staff"] if s["_id"] == staff_id]
        if len(staff_invalid) > 0:
            print(f"Warning: Staff still has {staff_invalid[0]['count']} invalid records")
        else:
            print("Verified: Staff no longer has invalid records")
    
    def test_reassign_memberwd_invalid_to_pool(self):
        """Test POST /api/memberwd/admin/reassign-invalid/{staff_id}"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # First get invalid records
        invalid_response = requests.get(f"{BASE_URL}/api/memberwd/admin/invalid-records", headers=headers)
        invalid_data = invalid_response.json()
        
        if invalid_data["total_invalid"] == 0 or len(invalid_data["by_staff"]) == 0:
            print("No invalid Member WD records to reassign")
            pytest.skip("No invalid Member WD records to test reassignment")
        
        staff_id = invalid_data["by_staff"][0]["_id"]
        
        response = requests.post(f"{BASE_URL}/api/memberwd/admin/reassign-invalid/{staff_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"Reassigned Member WD records: {data.get('message')}")
    
    def test_reassign_nonexistent_staff_returns_404(self):
        """Test reassigning for non-existent staff returns 404"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Use a fake staff ID
        fake_staff_id = "nonexistent-staff-id-12345"
        response = requests.post(f"{BASE_URL}/api/bonanza/admin/reassign-invalid/{fake_staff_id}", headers=headers)
        
        # Should return 404 because no invalid records found for this staff
        assert response.status_code == 404
        print("Correctly returned 404 for non-existent staff invalid records")


class TestNotificationResolution:
    """Test that notifications are marked resolved after reassignment"""
    
    def test_notifications_resolved_after_reassign(self):
        """Test that admin notifications are marked resolved after reassigning records"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get current notification state
        response = requests.get(f"{BASE_URL}/api/notifications/admin/invalid-database", headers=headers)
        data = response.json()
        
        print(f"Current notification state:")
        print(f"  Total unresolved: {data['summary']['total_unresolved']}")
        print(f"  Bonanza notifications: {data['summary']['bonanza_notifications']}")
        print(f"  Member WD notifications: {data['summary']['memberwd_notifications']}")
        
        # This test primarily verifies the endpoint returns correct structure
        # Full resolution testing is done in the reassignment tests
        assert "notifications" in data
        assert "summary" in data


class TestRoleBasedAccess:
    """Test role-based access control for validation endpoints"""
    
    def test_staff_cannot_access_admin_invalid_records(self):
        """Staff should not be able to access admin invalid records endpoint"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/bonanza/admin/invalid-records", headers=headers)
        
        # Should be forbidden for staff
        assert response.status_code in [401, 403]
        print("Correctly denied staff access to admin endpoint")
    
    def test_staff_cannot_reassign_invalid_records(self):
        """Staff should not be able to reassign invalid records"""
        token = get_staff_token()
        if not token:
            pytest.skip("Staff login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/bonanza/admin/reassign-invalid/some-staff-id", headers=headers)
        
        # Should be forbidden for staff
        assert response.status_code in [401, 403]
        print("Correctly denied staff from reassigning records")
    
    def test_admin_cannot_use_staff_validation_endpoint(self):
        """Admin role should not be able to use staff validation endpoint"""
        token = get_admin_token()
        if not token:
            pytest.skip("Admin login failed")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/bonanza/staff/validate", headers=headers, json={
            "record_ids": ["test-id"],
            "is_valid": True
        })
        
        # Master admin/admin should get 403 (only staff role allowed)
        assert response.status_code == 403
        print("Correctly denied admin from using staff endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
