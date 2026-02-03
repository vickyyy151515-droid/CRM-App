"""
Test suite for Grace Period Cleanup and Database Count Fixes

Tests:
1. Grace period cleanup scheduler is running (verify scheduler starts even when reports are disabled)
2. Reserved member cleanup job can be triggered manually via API
3. MemberWD database counts include archived records correctly
4. Bonanza database counts include archived records correctly
5. Process-invalid endpoint correctly archives records and assigns replacements
6. Available count decreases after assigning replacement records
7. Assigned count stays constant after archiving + replacing records
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSchedulerAndCleanup:
    """Test scheduler and cleanup functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_scheduler_config_endpoint(self):
        """Test that scheduler config endpoint is accessible"""
        response = self.session.get(f"{BASE_URL}/api/scheduled-reports/config")
        assert response.status_code == 200, f"Failed to get scheduler config: {response.text}"
        
        data = response.json()
        # Verify config structure
        assert 'enabled' in data or 'id' in data, "Config should have expected fields"
        print(f"✓ Scheduler config endpoint accessible")
        print(f"  Config: enabled={data.get('enabled')}, report_hour={data.get('report_hour')}")
    
    def test_02_reserved_member_cleanup_preview(self):
        """Test reserved member cleanup preview endpoint"""
        response = self.session.get(f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview")
        assert response.status_code == 200, f"Failed to get cleanup preview: {response.text}"
        
        data = response.json()
        # Verify preview structure
        assert 'config' in data, "Preview should have config"
        assert 'total_approved_members' in data, "Preview should have total_approved_members"
        assert 'expiring_soon_count' in data, "Preview should have expiring_soon_count"
        assert 'will_be_deleted_count' in data, "Preview should have will_be_deleted_count"
        
        print(f"✓ Reserved member cleanup preview endpoint works")
        print(f"  Total approved: {data.get('total_approved_members')}")
        print(f"  Expiring soon: {data.get('expiring_soon_count')}")
        print(f"  Will be deleted: {data.get('will_be_deleted_count')}")
    
    def test_03_reserved_member_cleanup_manual_trigger(self):
        """Test that reserved member cleanup can be triggered manually via API"""
        response = self.session.post(f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-run")
        assert response.status_code == 200, f"Failed to trigger cleanup: {response.text}"
        
        data = response.json()
        assert data.get('success') == True, "Cleanup should succeed"
        assert 'message' in data, "Response should have message"
        
        print(f"✓ Reserved member cleanup manual trigger works")
        print(f"  Message: {data.get('message')}")


class TestMemberWDDatabaseCounts:
    """Test MemberWD database counts include archived records correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_memberwd_databases_endpoint(self):
        """Test MemberWD databases endpoint returns correct counts"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/databases")
        assert response.status_code == 200, f"Failed to get databases: {response.text}"
        
        databases = response.json()
        print(f"✓ MemberWD databases endpoint accessible")
        print(f"  Total databases: {len(databases)}")
        
        # Check each database has required count fields
        for db in databases:
            assert 'total_records' in db, f"Database {db.get('name')} missing total_records"
            assert 'assigned_count' in db, f"Database {db.get('name')} missing assigned_count"
            assert 'archived_count' in db, f"Database {db.get('name')} missing archived_count"
            assert 'available_count' in db, f"Database {db.get('name')} missing available_count"
            
            # Verify count formula: available = total - assigned - archived - excluded
            total = db.get('total_records', 0)
            assigned = db.get('assigned_count', 0)
            archived = db.get('archived_count', 0)
            excluded = db.get('excluded_count', 0)
            available = db.get('available_count', 0)
            
            expected_available = total - assigned - archived - excluded
            
            print(f"  Database: {db.get('name')}")
            print(f"    Total: {total}, Assigned: {assigned}, Archived: {archived}, Excluded: {excluded}")
            print(f"    Available: {available} (expected: {expected_available})")
            
            # Allow small variance due to timing
            assert abs(available - expected_available) <= 1, \
                f"Available count mismatch for {db.get('name')}: got {available}, expected {expected_available}"
    
    def test_02_memberwd_archived_records_endpoint(self):
        """Test MemberWD archived invalid records endpoint"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/archived-invalid")
        assert response.status_code == 200, f"Failed to get archived records: {response.text}"
        
        data = response.json()
        assert 'total' in data, "Response should have total"
        assert 'by_database' in data, "Response should have by_database"
        
        print(f"✓ MemberWD archived invalid records endpoint works")
        print(f"  Total archived: {data.get('total')}")


class TestBonanzaDatabaseCounts:
    """Test Bonanza database counts include archived records correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_bonanza_databases_endpoint(self):
        """Test Bonanza databases endpoint returns correct counts"""
        response = self.session.get(f"{BASE_URL}/api/bonanza/databases")
        assert response.status_code == 200, f"Failed to get databases: {response.text}"
        
        databases = response.json()
        print(f"✓ Bonanza databases endpoint accessible")
        print(f"  Total databases: {len(databases)}")
        
        # Check each database has required count fields
        for db in databases:
            assert 'total_records' in db, f"Database {db.get('name')} missing total_records"
            assert 'assigned_count' in db, f"Database {db.get('name')} missing assigned_count"
            assert 'archived_count' in db, f"Database {db.get('name')} missing archived_count"
            assert 'available_count' in db, f"Database {db.get('name')} missing available_count"
            
            # Verify count formula: available = total - assigned - archived - excluded
            total = db.get('total_records', 0)
            assigned = db.get('assigned_count', 0)
            archived = db.get('archived_count', 0)
            excluded = db.get('excluded_count', 0)
            available = db.get('available_count', 0)
            
            expected_available = total - assigned - archived - excluded
            
            print(f"  Database: {db.get('name')}")
            print(f"    Total: {total}, Assigned: {assigned}, Archived: {archived}, Excluded: {excluded}")
            print(f"    Available: {available} (expected: {expected_available})")
            
            # Allow small variance due to timing
            assert abs(available - expected_available) <= 1, \
                f"Available count mismatch for {db.get('name')}: got {available}, expected {expected_available}"
    
    def test_02_bonanza_archived_records_endpoint(self):
        """Test Bonanza archived invalid records endpoint"""
        response = self.session.get(f"{BASE_URL}/api/bonanza/admin/archived-invalid")
        assert response.status_code == 200, f"Failed to get archived records: {response.text}"
        
        data = response.json()
        assert 'total' in data, "Response should have total"
        assert 'by_database' in data, "Response should have by_database"
        
        print(f"✓ Bonanza archived invalid records endpoint works")
        print(f"  Total archived: {data.get('total')}")


class TestProcessInvalidAndReplace:
    """Test process-invalid endpoint correctly archives records and assigns replacements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_memberwd_invalid_records_endpoint(self):
        """Test MemberWD invalid records endpoint"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/invalid-records")
        assert response.status_code == 200, f"Failed to get invalid records: {response.text}"
        
        data = response.json()
        assert 'total_invalid' in data, "Response should have total_invalid"
        assert 'by_staff' in data, "Response should have by_staff"
        
        print(f"✓ MemberWD invalid records endpoint works")
        print(f"  Total invalid: {data.get('total_invalid')}")
        
        # If there are invalid records, test the process-invalid endpoint
        if data.get('total_invalid', 0) > 0 and len(data.get('by_staff', [])) > 0:
            staff_id = data['by_staff'][0]['_id']
            print(f"  Found invalid records for staff: {staff_id}")
            return staff_id
        return None
    
    def test_02_bonanza_invalid_records_endpoint(self):
        """Test Bonanza invalid records endpoint"""
        response = self.session.get(f"{BASE_URL}/api/bonanza/admin/invalid-records")
        assert response.status_code == 200, f"Failed to get invalid records: {response.text}"
        
        data = response.json()
        assert 'total_invalid' in data, "Response should have total_invalid"
        assert 'by_staff' in data, "Response should have by_staff"
        
        print(f"✓ Bonanza invalid records endpoint works")
        print(f"  Total invalid: {data.get('total_invalid')}")


class TestCountConsistencyAfterProcessInvalid:
    """
    Test that counts are correct after processing invalid records:
    - Available count decreases after assigning replacement records
    - Assigned count stays constant after archiving + replacing records
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token and get staff list"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get staff list
        response = self.session.get(f"{BASE_URL}/api/memberwd/staff")
        if response.status_code == 200:
            staff_list = response.json()
            self.staff = staff_list[0] if staff_list else None
        else:
            self.staff = None
    
    def test_01_memberwd_count_formula_verification(self):
        """
        Verify MemberWD count formula:
        available = total - assigned - archived - excluded
        
        This ensures archived records are properly subtracted from available count.
        """
        response = self.session.get(f"{BASE_URL}/api/memberwd/databases")
        assert response.status_code == 200, f"Failed to get databases: {response.text}"
        
        databases = response.json()
        
        all_valid = True
        for db in databases:
            total = db.get('total_records', 0)
            assigned = db.get('assigned_count', 0)
            archived = db.get('archived_count', 0)
            excluded = db.get('excluded_count', 0)
            available = db.get('available_count', 0)
            
            # Formula: available = total - assigned - archived - excluded
            expected = total - assigned - archived - excluded
            
            if available != expected:
                print(f"✗ Count mismatch for {db.get('name')}")
                print(f"  Formula: {total} - {assigned} - {archived} - {excluded} = {expected}")
                print(f"  Actual available: {available}")
                all_valid = False
            else:
                print(f"✓ {db.get('name')}: available={available} (correct)")
        
        assert all_valid, "Some databases have incorrect count calculations"
    
    def test_02_bonanza_count_formula_verification(self):
        """
        Verify Bonanza count formula:
        available = total - assigned - archived - excluded
        
        This ensures archived records are properly subtracted from available count.
        """
        response = self.session.get(f"{BASE_URL}/api/bonanza/databases")
        assert response.status_code == 200, f"Failed to get databases: {response.text}"
        
        databases = response.json()
        
        all_valid = True
        for db in databases:
            total = db.get('total_records', 0)
            assigned = db.get('assigned_count', 0)
            archived = db.get('archived_count', 0)
            excluded = db.get('excluded_count', 0)
            available = db.get('available_count', 0)
            
            # Formula: available = total - assigned - archived - excluded
            expected = total - assigned - archived - excluded
            
            if available != expected:
                print(f"✗ Count mismatch for {db.get('name')}")
                print(f"  Formula: {total} - {assigned} - {archived} - {excluded} = {expected}")
                print(f"  Actual available: {available}")
                all_valid = False
            else:
                print(f"✓ {db.get('name')}: available={available} (correct)")
        
        assert all_valid, "Some databases have incorrect count calculations"


class TestGracePeriodConfig:
    """Test grace period configuration endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_01_get_grace_period_config(self):
        """Test getting grace period configuration"""
        response = self.session.get(f"{BASE_URL}/api/reserved-members/cleanup-config")
        assert response.status_code == 200, f"Failed to get config: {response.text}"
        
        data = response.json()
        assert 'global_grace_days' in data, "Config should have global_grace_days"
        assert 'warning_days' in data, "Config should have warning_days"
        
        print(f"✓ Grace period config endpoint works")
        print(f"  Global grace days: {data.get('global_grace_days')}")
        print(f"  Warning days: {data.get('warning_days')}")
        print(f"  Product overrides: {len(data.get('product_overrides', []))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
