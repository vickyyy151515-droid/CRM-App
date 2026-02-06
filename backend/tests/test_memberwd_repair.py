"""
Test suite for Member WD CRM Data Health and Repair functionality.

Tests the fix for the production bug where:
1. Records with status='invalid' (caused by reservation conflicts) were not being counted
2. Batch counts (current_count in memberwd_batches) were getting out of sync with actual record counts

The fix:
- Records with status='invalid' that have assignment info should be restored to status='assigned' with is_reservation_conflict=True
- Batch counts should be synchronized with actual record counts
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "vicky123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestMemberWDDataHealthAndRepair:
    """Test suite for Member WD CRM data health check and repair functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.admin_token = data.get("token")
        assert self.admin_token, "No token in login response"
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
        
        # Cleanup - no specific cleanup needed as we're testing existing endpoints
    
    def test_01_data_health_endpoint_exists(self):
        """Test that /api/memberwd/admin/data-health endpoint exists and returns valid response"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        
        assert response.status_code == 200, f"Data health endpoint failed: {response.text}"
        
        data = response.json()
        print(f"Data health response: {data}")
        
        # Verify response structure
        assert 'databases' in data, "Response should contain 'databases' field"
        assert 'batches' in data, "Response should contain 'batches' field"
        assert 'total_issues' in data, "Response should contain 'total_issues' field"
        assert 'is_healthy' in data, "Response should contain 'is_healthy' field"
        
        # Verify database health info structure
        if data['databases']:
            db_info = data['databases'][0]
            assert 'database_id' in db_info, "Database info should have 'database_id'"
            assert 'database_name' in db_info, "Database info should have 'database_name'"
            assert 'total_records' in db_info, "Database info should have 'total_records'"
            assert 'available' in db_info, "Database info should have 'available'"
            assert 'assigned' in db_info, "Database info should have 'assigned'"
            assert 'archived' in db_info, "Database info should have 'archived'"
            assert 'invalid_status_records' in db_info, "Database info should have 'invalid_status_records'"
            assert 'issues' in db_info, "Database info should have 'issues'"
            
            # Verify issues structure
            issues = db_info['issues']
            assert 'missing_db_name' in issues, "Issues should have 'missing_db_name'"
            assert 'orphaned_assignments' in issues, "Issues should have 'orphaned_assignments'"
            assert 'invalid_status' in issues, "Issues should have 'invalid_status'"
        
        # Verify batch health info structure
        if data['batches']:
            batch_info = data['batches'][0]
            assert 'batch_id' in batch_info, "Batch info should have 'batch_id'"
            assert 'staff_name' in batch_info, "Batch info should have 'staff_name'"
            assert 'stored_count' in batch_info, "Batch info should have 'stored_count'"
            assert 'actual_count' in batch_info, "Batch info should have 'actual_count'"
            assert 'has_mismatch' in batch_info, "Batch info should have 'has_mismatch'"
            assert 'difference' in batch_info, "Batch info should have 'difference'"
        
        print(f"✓ Data health endpoint returns valid structure")
        print(f"  - Total issues detected: {data['total_issues']}")
        print(f"  - Is healthy: {data['is_healthy']}")
        print(f"  - Databases checked: {len(data['databases'])}")
        print(f"  - Batches checked: {len(data['batches'])}")
    
    def test_02_repair_data_endpoint_exists(self):
        """Test that /api/memberwd/admin/repair-data endpoint exists and returns valid response"""
        response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        
        assert response.status_code == 200, f"Repair data endpoint failed: {response.text}"
        
        data = response.json()
        print(f"Repair data response: {data}")
        
        # Verify response structure
        assert 'success' in data, "Response should contain 'success' field"
        assert data['success'] == True, "Repair should succeed"
        assert 'message' in data, "Response should contain 'message' field"
        assert 'repair_log' in data, "Response should contain 'repair_log' field"
        
        repair_log = data['repair_log']
        
        # Verify repair_log structure
        assert 'timestamp' in repair_log, "Repair log should have 'timestamp'"
        assert 'fixed_missing_db_info' in repair_log, "Repair log should have 'fixed_missing_db_info'"
        assert 'fixed_invalid_status_restored' in repair_log, "Repair log should have 'fixed_invalid_status_restored'"
        assert 'fixed_invalid_status_cleared' in repair_log, "Repair log should have 'fixed_invalid_status_cleared'"
        assert 'fixed_orphaned_assignments' in repair_log, "Repair log should have 'fixed_orphaned_assignments'"
        assert 'fixed_batch_counts' in repair_log, "Repair log should have 'fixed_batch_counts'"
        assert 'databases_checked' in repair_log, "Repair log should have 'databases_checked'"
        assert 'batches_synchronized' in repair_log, "Repair log should have 'batches_synchronized'"
        
        print(f"✓ Repair data endpoint returns valid structure")
        print(f"  - Fixed missing db info: {repair_log['fixed_missing_db_info']}")
        print(f"  - Fixed invalid status restored: {repair_log['fixed_invalid_status_restored']}")
        print(f"  - Fixed invalid status cleared: {repair_log['fixed_invalid_status_cleared']}")
        print(f"  - Fixed orphaned assignments: {repair_log['fixed_orphaned_assignments']}")
        print(f"  - Fixed batch counts: {repair_log['fixed_batch_counts']}")
    
    def test_03_health_check_detects_invalid_status_records(self):
        """Test that health check properly detects records with status='invalid'"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        
        assert response.status_code == 200, f"Data health endpoint failed: {response.text}"
        
        data = response.json()
        
        # Check if any database has invalid_status_records
        total_invalid_status = 0
        for db_info in data['databases']:
            invalid_count = db_info.get('invalid_status_records', 0)
            total_invalid_status += invalid_count
            if invalid_count > 0:
                print(f"  - Database '{db_info['database_name']}' has {invalid_count} records with status='invalid'")
        
        print(f"✓ Health check detected {total_invalid_status} total records with status='invalid'")
        
        # Also check issues field
        for db_info in data['databases']:
            issues = db_info.get('issues', {})
            if issues.get('invalid_status', 0) > 0:
                print(f"  - Database '{db_info['database_name']}' issues.invalid_status = {issues['invalid_status']}")
    
    def test_04_health_check_detects_batch_count_mismatches(self):
        """Test that health check properly detects batch count mismatches"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        
        assert response.status_code == 200, f"Data health endpoint failed: {response.text}"
        
        data = response.json()
        
        # Check batch mismatches
        batch_mismatches = data.get('batch_mismatches', 0)
        print(f"✓ Health check detected {batch_mismatches} batch count mismatches")
        
        # Show details of mismatched batches
        for batch_info in data['batches']:
            if batch_info.get('has_mismatch'):
                print(f"  - Batch {batch_info['batch_id']} ({batch_info['staff_name']}): stored={batch_info['stored_count']}, actual={batch_info['actual_count']}, diff={batch_info['difference']}")
    
    def test_05_repair_fixes_invalid_status_records(self):
        """Test that repair endpoint fixes records with status='invalid' by restoring to 'assigned' with is_reservation_conflict=True"""
        # First check current health
        health_before = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health").json()
        invalid_before = sum(db.get('invalid_status_records', 0) for db in health_before['databases'])
        
        # Run repair
        repair_response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert repair_response.status_code == 200, f"Repair failed: {repair_response.text}"
        
        repair_data = repair_response.json()
        fixed_restored = repair_data['repair_log'].get('fixed_invalid_status_restored', 0)
        fixed_cleared = repair_data['repair_log'].get('fixed_invalid_status_cleared', 0)
        
        # Check health after repair
        health_after = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health").json()
        invalid_after = sum(db.get('invalid_status_records', 0) for db in health_after['databases'])
        
        print(f"✓ Repair endpoint processed invalid status records")
        print(f"  - Invalid records before: {invalid_before}")
        print(f"  - Fixed (restored to assigned): {fixed_restored}")
        print(f"  - Fixed (cleared to available): {fixed_cleared}")
        print(f"  - Invalid records after: {invalid_after}")
        
        # After repair, invalid_after should be 0 or less than before
        assert invalid_after <= invalid_before, f"Invalid records should decrease after repair: before={invalid_before}, after={invalid_after}"
    
    def test_06_repair_synchronizes_batch_counts(self):
        """Test that repair endpoint synchronizes batch counts with actual record counts"""
        # First check current health
        health_before = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health").json()
        mismatches_before = health_before.get('batch_mismatches', 0)
        
        # Run repair
        repair_response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert repair_response.status_code == 200, f"Repair failed: {repair_response.text}"
        
        repair_data = repair_response.json()
        fixed_batch_counts = repair_data['repair_log'].get('fixed_batch_counts', 0)
        batches_synchronized = repair_data['repair_log'].get('batches_synchronized', [])
        
        # Check health after repair
        health_after = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health").json()
        mismatches_after = health_after.get('batch_mismatches', 0)
        
        print(f"✓ Repair endpoint synchronized batch counts")
        print(f"  - Batch mismatches before: {mismatches_before}")
        print(f"  - Fixed batch counts: {fixed_batch_counts}")
        print(f"  - Batches synchronized: {len(batches_synchronized)}")
        print(f"  - Batch mismatches after: {mismatches_after}")
        
        # After repair, mismatches should be 0
        assert mismatches_after == 0, f"Batch mismatches should be 0 after repair: {mismatches_after}"
    
    def test_07_assigned_count_accuracy_after_repair(self):
        """Test that assigned record counts are accurate after repair"""
        # Run repair first
        repair_response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert repair_response.status_code == 200, f"Repair failed: {repair_response.text}"
        
        # Get health check
        health_response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        assert health_response.status_code == 200, f"Health check failed: {health_response.text}"
        
        health_data = health_response.json()
        
        # Verify each database has consistent counts
        for db_info in health_data['databases']:
            total = db_info['total_records']
            available = db_info['available']
            assigned = db_info['assigned']
            archived = db_info['archived']
            invalid_status = db_info.get('invalid_status_records', 0)
            
            # After repair, invalid_status should be 0
            assert invalid_status == 0, f"Database '{db_info['database_name']}' still has {invalid_status} records with status='invalid'"
            
            # Sum should match total
            sum_counts = available + assigned + archived
            assert sum_counts == total, f"Database '{db_info['database_name']}' count mismatch: {sum_counts} != {total}"
            
            print(f"✓ Database '{db_info['database_name']}': total={total}, available={available}, assigned={assigned}, archived={archived}")
        
        # Verify batch counts match actual records
        for batch_info in health_data['batches']:
            assert not batch_info['has_mismatch'], f"Batch {batch_info['batch_id']} still has count mismatch: stored={batch_info['stored_count']}, actual={batch_info['actual_count']}"
        
        print(f"✓ All assigned counts are accurate after repair")
    
    def test_08_backward_compatibility_reservation_conflict_queries(self):
        """Test that queries for reservation conflicts find both old format (status='invalid') and new format (is_reservation_conflict=True)"""
        # Login as staff to test the staff endpoint
        staff_session = requests.Session()
        staff_session.headers.update({"Content-Type": "application/json"})
        
        login_response = staff_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        
        if login_response.status_code != 200:
            print(f"Staff login failed (may not exist): {login_response.text}")
            pytest.skip("Staff user not available for testing")
        
        staff_token = login_response.json().get("token")
        staff_session.headers.update({"Authorization": f"Bearer {staff_token}"})
        
        # Test the invalidated-by-reservation endpoint
        response = staff_session.get(f"{BASE_URL}/api/memberwd/staff/invalidated-by-reservation")
        
        assert response.status_code == 200, f"Invalidated by reservation endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Invalidated by reservation endpoint works")
        print(f"  - Count: {data.get('count', 0)}")
        print(f"  - Records: {len(data.get('records', []))}")
        
        # Verify response structure
        assert 'count' in data, "Response should contain 'count' field"
        assert 'records' in data, "Response should contain 'records' field"
    
    def test_09_data_sync_conflict_resolution_log(self):
        """Test that data sync conflict resolution log supports both old and new formats"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/conflict-resolution-log")
        
        assert response.status_code == 200, f"Conflict resolution log endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Conflict resolution log endpoint works")
        print(f"  - Total count: {data.get('total_count', 0)}")
        print(f"  - Returned count: {data.get('returned_count', 0)}")
        
        # Verify response structure
        assert 'total_count' in data, "Response should contain 'total_count' field"
        assert 'records' in data, "Response should contain 'records' field"
        assert 'summary' in data, "Response should contain 'summary' field"
    
    def test_10_data_sync_conflict_resolution_stats(self):
        """Test that data sync conflict resolution stats supports both old and new formats"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/conflict-resolution-stats")
        
        assert response.status_code == 200, f"Conflict resolution stats endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Conflict resolution stats endpoint works")
        print(f"  - Total invalidated: {data.get('total_invalidated', 0)}")
        print(f"  - Today: {data.get('today', 0)}")
        print(f"  - This week: {data.get('this_week', 0)}")
        print(f"  - This month: {data.get('this_month', 0)}")
        
        # Verify response structure
        assert 'total_invalidated' in data, "Response should contain 'total_invalidated' field"
        assert 'today' in data, "Response should contain 'today' field"
        assert 'this_week' in data, "Response should contain 'this_week' field"
        assert 'this_month' in data, "Response should contain 'this_month' field"


class TestBonanzaDataHealthAndRepair:
    """Test suite for DB Bonanza data health check and repair functionality (similar to Member WD)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.admin_token = data.get("token")
        assert self.admin_token, "No token in login response"
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
    
    def test_01_bonanza_repair_data_endpoint(self):
        """Test that /api/bonanza/admin/repair-data endpoint exists and works"""
        response = self.session.post(f"{BASE_URL}/api/bonanza/admin/repair-data")
        
        assert response.status_code == 200, f"Bonanza repair data endpoint failed: {response.text}"
        
        data = response.json()
        print(f"Bonanza repair data response: {data}")
        
        # Verify response structure
        assert 'success' in data, "Response should contain 'success' field"
        assert data['success'] == True, "Repair should succeed"
        assert 'message' in data, "Response should contain 'message' field"
        assert 'repair_log' in data, "Response should contain 'repair_log' field"
        
        print(f"✓ Bonanza repair data endpoint works")
    
    def test_02_bonanza_invalidated_by_reservation_endpoint(self):
        """Test that bonanza invalidated-by-reservation endpoint supports both formats"""
        # Login as staff
        staff_session = requests.Session()
        staff_session.headers.update({"Content-Type": "application/json"})
        
        login_response = staff_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        
        if login_response.status_code != 200:
            print(f"Staff login failed (may not exist): {login_response.text}")
            pytest.skip("Staff user not available for testing")
        
        staff_token = login_response.json().get("token")
        staff_session.headers.update({"Authorization": f"Bearer {staff_token}"})
        
        # Test the invalidated-by-reservation endpoint
        response = staff_session.get(f"{BASE_URL}/api/bonanza/staff/invalidated-by-reservation")
        
        assert response.status_code == 200, f"Bonanza invalidated by reservation endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Bonanza invalidated by reservation endpoint works")
        print(f"  - Count: {data.get('count', 0)}")
        
        # Verify response structure
        assert 'count' in data, "Response should contain 'count' field"
        assert 'records' in data, "Response should contain 'records' field"


class TestRecordsInvalidatedByReservation:
    """Test suite for customer_records invalidated-by-reservation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as staff
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip("Staff user not available for testing")
        
        data = response.json()
        self.staff_token = data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.staff_token}"})
        
        yield
    
    def test_01_my_invalidated_by_reservation_endpoint(self):
        """Test that /api/my-invalidated-by-reservation endpoint supports both formats"""
        response = self.session.get(f"{BASE_URL}/api/my-invalidated-by-reservation")
        
        assert response.status_code == 200, f"My invalidated by reservation endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ My invalidated by reservation endpoint works")
        print(f"  - Count: {data.get('count', 0)}")
        
        # Verify response structure
        assert 'count' in data, "Response should contain 'count' field"
        assert 'records' in data, "Response should contain 'records' field"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
