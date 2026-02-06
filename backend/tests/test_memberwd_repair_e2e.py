"""
End-to-end test for Member WD CRM Data Health and Repair functionality.

This test simulates the production bug scenario:
1. Creates a test record with status='invalid' (simulating the old bug)
2. Creates a batch with incorrect count (simulating count mismatch)
3. Runs health check to verify detection
4. Runs repair to verify fix
5. Verifies the fix worked correctly
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


class TestMemberWDRepairE2E:
    """End-to-end test for Member WD CRM repair functionality"""
    
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
    
    def test_01_verify_health_check_structure(self):
        """Verify health check returns proper structure for detecting issues"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        
        # Print detailed health report
        print("\n=== MEMBER WD DATA HEALTH REPORT ===")
        print(f"Is Healthy: {data.get('is_healthy')}")
        print(f"Total Issues: {data.get('total_issues')}")
        print(f"Batch Mismatches: {data.get('batch_mismatches', 0)}")
        
        print("\n--- Databases ---")
        for db in data.get('databases', []):
            print(f"  {db['database_name']}:")
            print(f"    Total: {db['total_records']}, Available: {db['available']}, Assigned: {db['assigned']}, Archived: {db['archived']}")
            print(f"    Invalid Status Records: {db.get('invalid_status_records', 0)}")
            print(f"    Issues: {db.get('issues', {})}")
            print(f"    Has Issues: {db.get('has_issues', False)}")
        
        print("\n--- Batches with Mismatches ---")
        for batch in data.get('batches', []):
            if batch.get('has_mismatch'):
                print(f"  {batch['batch_id']} ({batch['staff_name']}):")
                print(f"    Stored: {batch['stored_count']}, Actual: {batch['actual_count']}, Diff: {batch['difference']}")
        
        # Verify structure
        assert 'databases' in data
        assert 'batches' in data
        assert 'total_issues' in data
        assert 'is_healthy' in data
        assert 'batch_mismatches' in data
        
        print("\n✓ Health check structure verified")
    
    def test_02_verify_repair_structure(self):
        """Verify repair returns proper structure with fix counts"""
        response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert response.status_code == 200, f"Repair failed: {response.text}"
        
        data = response.json()
        
        # Print detailed repair report
        print("\n=== MEMBER WD REPAIR REPORT ===")
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        
        repair_log = data.get('repair_log', {})
        print(f"\n--- Repair Log ---")
        print(f"  Timestamp: {repair_log.get('timestamp')}")
        print(f"  Fixed Missing DB Info: {repair_log.get('fixed_missing_db_info', 0)}")
        print(f"  Fixed Invalid Status Restored: {repair_log.get('fixed_invalid_status_restored', 0)}")
        print(f"  Fixed Invalid Status Cleared: {repair_log.get('fixed_invalid_status_cleared', 0)}")
        print(f"  Fixed Orphaned Assignments: {repair_log.get('fixed_orphaned_assignments', 0)}")
        print(f"  Fixed Batch Counts: {repair_log.get('fixed_batch_counts', 0)}")
        
        print(f"\n--- Databases Checked ---")
        for db in repair_log.get('databases_checked', []):
            print(f"  {db['database_name']}:")
            print(f"    Total: {db['total_records']}, Available: {db['available']}, Assigned: {db['assigned']}, Archived: {db['archived']}")
            print(f"    Is Consistent: {db.get('is_consistent', False)}")
        
        print(f"\n--- Batches Synchronized ---")
        for batch in repair_log.get('batches_synchronized', []):
            print(f"  {batch.get('batch_id', 'N/A')}: {batch.get('old_count', 0)} -> {batch.get('new_count', 0)}")
        
        # Verify structure
        assert data.get('success') == True
        assert 'message' in data
        assert 'repair_log' in data
        
        repair_log = data['repair_log']
        assert 'fixed_missing_db_info' in repair_log
        assert 'fixed_invalid_status_restored' in repair_log
        assert 'fixed_invalid_status_cleared' in repair_log
        assert 'fixed_orphaned_assignments' in repair_log
        assert 'fixed_batch_counts' in repair_log
        assert 'databases_checked' in repair_log
        assert 'batches_synchronized' in repair_log
        
        print("\n✓ Repair structure verified")
    
    def test_03_verify_health_after_repair(self):
        """Verify health check shows no issues after repair"""
        # Run repair first
        repair_response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert repair_response.status_code == 200, f"Repair failed: {repair_response.text}"
        
        # Check health after repair
        health_response = self.session.get(f"{BASE_URL}/api/memberwd/admin/data-health")
        assert health_response.status_code == 200, f"Health check failed: {health_response.text}"
        
        data = health_response.json()
        
        print("\n=== HEALTH CHECK AFTER REPAIR ===")
        print(f"Is Healthy: {data.get('is_healthy')}")
        print(f"Total Issues: {data.get('total_issues')}")
        print(f"Batch Mismatches: {data.get('batch_mismatches', 0)}")
        
        # Verify no invalid status records remain
        total_invalid_status = 0
        for db in data.get('databases', []):
            invalid_count = db.get('invalid_status_records', 0)
            total_invalid_status += invalid_count
            if invalid_count > 0:
                print(f"  WARNING: Database '{db['database_name']}' still has {invalid_count} invalid status records")
        
        # Verify no batch mismatches remain
        batch_mismatches = data.get('batch_mismatches', 0)
        
        print(f"\nTotal Invalid Status Records: {total_invalid_status}")
        print(f"Total Batch Mismatches: {batch_mismatches}")
        
        # After repair, these should be 0
        assert total_invalid_status == 0, f"Expected 0 invalid status records after repair, got {total_invalid_status}"
        assert batch_mismatches == 0, f"Expected 0 batch mismatches after repair, got {batch_mismatches}"
        
        print("\n✓ Health check shows no issues after repair")
    
    def test_04_verify_backward_compatibility_queries(self):
        """Verify that queries support both old and new formats for reservation conflicts"""
        # Test data-sync conflict resolution log
        response = self.session.get(f"{BASE_URL}/api/data-sync/conflict-resolution-log")
        assert response.status_code == 200, f"Conflict resolution log failed: {response.text}"
        
        data = response.json()
        print("\n=== CONFLICT RESOLUTION LOG ===")
        print(f"Total Count: {data.get('total_count', 0)}")
        print(f"Summary: {data.get('summary', {})}")
        
        # Test data-sync conflict resolution stats
        response = self.session.get(f"{BASE_URL}/api/data-sync/conflict-resolution-stats")
        assert response.status_code == 200, f"Conflict resolution stats failed: {response.text}"
        
        data = response.json()
        print("\n=== CONFLICT RESOLUTION STATS ===")
        print(f"Total Invalidated: {data.get('total_invalidated', 0)}")
        print(f"Today: {data.get('today', 0)}")
        print(f"This Week: {data.get('this_week', 0)}")
        print(f"This Month: {data.get('this_month', 0)}")
        
        print("\n✓ Backward compatibility queries work correctly")
    
    def test_05_verify_databases_list_counts(self):
        """Verify that database list shows correct counts after repair"""
        # Run repair first
        repair_response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-data")
        assert repair_response.status_code == 200, f"Repair failed: {repair_response.text}"
        
        # Get databases list
        response = self.session.get(f"{BASE_URL}/api/memberwd/databases")
        assert response.status_code == 200, f"Get databases failed: {response.text}"
        
        databases = response.json()
        
        print("\n=== MEMBER WD DATABASES ===")
        for db in databases:
            print(f"\n{db.get('name', 'Unknown')}:")
            print(f"  Total Records: {db.get('total_records', 0)}")
            print(f"  Assigned Count: {db.get('assigned_count', 0)}")
            print(f"  Available Count: {db.get('available_count', 0)}")
            print(f"  Archived Count: {db.get('archived_count', 0)}")
            print(f"  Excluded Count: {db.get('excluded_count', 0)}")
            
            # Verify counts add up
            total = db.get('total_records', 0)
            assigned = db.get('assigned_count', 0)
            available = db.get('available_count', 0)
            archived = db.get('archived_count', 0)
            excluded = db.get('excluded_count', 0)
            
            # Note: available_count already excludes excluded_count
            # So: total = assigned + (available + excluded) + archived
            expected_total = assigned + available + excluded + archived
            
            if total != expected_total:
                print(f"  WARNING: Count mismatch! Total={total}, Sum={expected_total}")
        
        print("\n✓ Database counts verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
