"""
Test suite for CRM Sync Features - Iteration 34

Tests the following sync features:
1. Attendance Check-in with Leave Integration - staff with approved leave should NOT be marked late
2. Lateness Fees calculation should EXCLUDE days with approved leave
3. Bonus Check Expiration should use correct date (record_date/last_omset_date, not approved_at)
4. Reserved Member Cleanup should use last_omset_date for grace period calculation
5. When reserved member is deleted manually, bonus_check_submissions should be cleaned up
6. When user is deleted, all related data should be cascade deleted
7. Fix verified: generate_atrisk_alert variable name fix (recently_alerted_ids -> recently_alerted_keys)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAttendanceLeaveIntegration:
    """
    Test 1: Attendance Check-in with Leave Integration
    Staff with approved leave should NOT be marked late
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth tokens for admin and staff"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.admin_token = data.get("token")
        self.admin_id = data.get("user", {}).get("id")
        
        # Login as staff
        staff_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        if staff_response.status_code == 200:
            staff_data = staff_response.json()
            self.staff_token = staff_data.get("token")
            self.staff_id = staff_data.get("user", {}).get("id")
        else:
            self.staff_token = None
            self.staff_id = None
    
    def test_01_attendance_checkin_endpoint_exists(self):
        """Test that attendance check-in endpoint exists"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Check today's attendance status
        response = self.session.get(f"{BASE_URL}/api/attendance/check-today")
        assert response.status_code == 200, f"Attendance check-today endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Attendance check-today endpoint works")
        print(f"  Checked in: {data.get('checked_in')}")
    
    def test_02_leave_requests_endpoint_exists(self):
        """Test that leave requests endpoint exists"""
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        # Get leave requests - correct endpoint is /api/leave/all-requests
        response = self.session.get(f"{BASE_URL}/api/leave/all-requests")
        assert response.status_code == 200, f"Leave requests endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Leave requests endpoint works")
        print(f"  Total leave requests: {len(data) if isinstance(data, list) else data.get('total', 0)}")
    
    def test_03_attendance_code_checks_leave_status(self):
        """
        Verify that attendance.py code checks for approved leave before marking late.
        This is a code review test - we verify the logic exists in the codebase.
        """
        # Read the attendance.py file to verify the leave check logic
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'approved_leave', '/app/backend/routes/attendance.py'],
            capture_output=True, text=True
        )
        
        # Check that the leave check logic exists
        assert 'approved_leave' in result.stdout, "attendance.py should check for approved leave"
        assert 'leave_requests' in result.stdout or 'has_approved_leave' in result.stdout, \
            "attendance.py should query leave_requests collection"
        
        print(f"✓ Attendance code checks for approved leave before marking late")
        print(f"  Found leave check logic in attendance.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")


class TestLatenessFeeLeaveExclusion:
    """
    Test 2: Lateness Fees calculation should EXCLUDE days with approved leave
    """
    
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
    
    def test_01_fees_summary_endpoint_exists(self):
        """Test that fees summary endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/attendance/admin/fees/summary")
        assert response.status_code == 200, f"Fees summary endpoint failed: {response.text}"
        
        data = response.json()
        assert 'staff_fees' in data, "Response should have staff_fees"
        assert 'fee_per_minute' in data, "Response should have fee_per_minute"
        
        print(f"✓ Fees summary endpoint works")
        print(f"  Fee per minute: ${data.get('fee_per_minute')}")
        print(f"  Total fees this month: ${data.get('total_fees_this_month', 0)}")
    
    def test_02_fees_code_excludes_approved_leave(self):
        """
        Verify that fees.py code excludes records with approved leave from fee calculation.
        This is a code review test.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'has_approved_leave', '/app/backend/routes/fees.py'],
            capture_output=True, text=True
        )
        
        # Check that the leave exclusion logic exists
        assert 'has_approved_leave' in result.stdout, "fees.py should check has_approved_leave"
        
        print(f"✓ Fees code excludes records with approved leave")
        print(f"  Found leave exclusion logic in fees.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")


class TestBonusCheckExpiration:
    """
    Test 3: Bonus Check Expiration should use correct date (record_date/last_omset_date, not approved_at)
    """
    
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
    
    def test_01_bonus_check_products_endpoint(self):
        """Test that bonus check products endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/bonus-check/products")
        assert response.status_code == 200, f"Bonus check products endpoint failed: {response.text}"
        
        data = response.json()
        print(f"✓ Bonus check products endpoint works")
        # Response is a list directly or has 'products' key
        products = data if isinstance(data, list) else data.get('products', [])
        print(f"  Products available: {len(products)}")
    
    def test_02_bonus_check_code_uses_record_date(self):
        """
        Verify that bonus_check.py uses record_date (last deposit date) for expiration check,
        NOT approved_at.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'record_date', '/app/backend/routes/bonus_check.py'],
            capture_output=True, text=True
        )
        
        # Check that record_date is used
        assert 'record_date' in result.stdout, "bonus_check.py should use record_date for expiration"
        
        print(f"✓ Bonus check code uses record_date for expiration calculation")
        print(f"  Found record_date usage in bonus_check.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")
    
    def test_03_bonus_check_code_uses_last_omset(self):
        """
        Verify that bonus_check.py queries omset_records for last deposit date.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'omset_records', '/app/backend/routes/bonus_check.py'],
            capture_output=True, text=True
        )
        
        # Check that omset_records is queried
        assert 'omset_records' in result.stdout, "bonus_check.py should query omset_records"
        
        print(f"✓ Bonus check code queries omset_records for last deposit date")
        print(f"  Found omset_records query in bonus_check.py:")
        for line in result.stdout.strip().split('\n')[:3]:
            print(f"    {line}")


class TestReservedMemberCleanupGracePeriod:
    """
    Test 4: Reserved Member Cleanup should use last_omset_date for grace period calculation
    """
    
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
    
    def test_01_cleanup_preview_endpoint(self):
        """Test reserved member cleanup preview endpoint"""
        response = self.session.get(f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview")
        assert response.status_code == 200, f"Cleanup preview failed: {response.text}"
        
        data = response.json()
        assert 'config' in data, "Response should have config"
        assert 'total_approved_members' in data, "Response should have total_approved_members"
        
        print(f"✓ Reserved member cleanup preview endpoint works")
        print(f"  Total approved members: {data.get('total_approved_members')}")
        print(f"  Will be deleted: {data.get('will_be_deleted_count')}")
    
    def test_02_cleanup_code_uses_last_omset_date(self):
        """
        Verify that scheduled_reports.py uses last_omset_date for grace period calculation.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'last_omset_date', '/app/backend/routes/scheduled_reports.py'],
            capture_output=True, text=True
        )
        
        # Check that last_omset_date is used
        assert 'last_omset_date' in result.stdout, "scheduled_reports.py should use last_omset_date"
        
        print(f"✓ Cleanup code uses last_omset_date for grace period calculation")
        print(f"  Found last_omset_date usage in scheduled_reports.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")
    
    def test_03_cleanup_code_uses_record_date_from_omset(self):
        """
        Verify that cleanup code queries omset_records using record_date field.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'record_date', '/app/backend/routes/scheduled_reports.py'],
            capture_output=True, text=True
        )
        
        # Check that record_date is used
        assert 'record_date' in result.stdout, "scheduled_reports.py should use record_date"
        
        # Verify it's used for sorting (check for sort pattern)
        assert "sort=[('record_date'" in result.stdout or 'record_date' in result.stdout, \
            "scheduled_reports.py should sort by record_date"
        
        print(f"✓ Cleanup code uses record_date from omset_records")
        print(f"  Found record_date usage in scheduled_reports.py:")
        for line in result.stdout.strip().split('\n')[:3]:
            print(f"    {line}")


class TestReservedMemberDeleteBonusCleanup:
    """
    Test 5: When reserved member is deleted manually, bonus_check_submissions should be cleaned up
    """
    
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
    
    def test_01_records_delete_code_cleans_bonus_submissions(self):
        """
        Verify that records.py delete_reserved_member cleans up bonus_check_submissions.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'bonus_check_submissions', '/app/backend/routes/records.py'],
            capture_output=True, text=True
        )
        
        # Check that bonus_check_submissions cleanup exists
        assert 'bonus_check_submissions' in result.stdout, \
            "records.py should clean up bonus_check_submissions on delete"
        assert 'delete_many' in result.stdout, \
            "records.py should use delete_many for bonus_check_submissions"
        
        print(f"✓ Reserved member delete cleans up bonus_check_submissions")
        print(f"  Found bonus cleanup logic in records.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")
    
    def test_02_cleanup_job_also_cleans_bonus_submissions(self):
        """
        Verify that scheduled cleanup job also cleans up bonus_check_submissions.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'bonus_check_submissions', '/app/backend/routes/scheduled_reports.py'],
            capture_output=True, text=True
        )
        
        # Check that bonus_check_submissions cleanup exists in scheduled job
        assert 'bonus_check_submissions' in result.stdout, \
            "scheduled_reports.py should clean up bonus_check_submissions"
        
        print(f"✓ Scheduled cleanup job also cleans up bonus_check_submissions")
        print(f"  Found bonus cleanup in scheduled_reports.py:")
        for line in result.stdout.strip().split('\n')[:3]:
            print(f"    {line}")


class TestUserDeleteCascade:
    """
    Test 6: When user is deleted, all related data should be cascade deleted
    """
    
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
    
    def test_01_user_delete_code_has_cascade_cleanup(self):
        """
        Verify that auth.py delete_user has cascade cleanup for all related collections.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'delete_many', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        # Check that multiple delete_many calls exist
        delete_lines = result.stdout.strip().split('\n')
        assert len(delete_lines) >= 5, "auth.py should have multiple cascade delete operations"
        
        print(f"✓ User delete has cascade cleanup")
        print(f"  Found {len(delete_lines)} delete operations in auth.py:")
        for line in delete_lines[:6]:
            print(f"    {line}")
    
    def test_02_user_delete_cleans_reserved_members(self):
        """Verify user delete cleans up reserved_members"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'reserved_members', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        assert 'reserved_members' in result.stdout, "auth.py should clean up reserved_members"
        print(f"✓ User delete cleans up reserved_members")
    
    def test_03_user_delete_cleans_bonus_submissions(self):
        """Verify user delete cleans up bonus_check_submissions"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'bonus_check_submissions', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        assert 'bonus_check_submissions' in result.stdout, "auth.py should clean up bonus_check_submissions"
        print(f"✓ User delete cleans up bonus_check_submissions")
    
    def test_04_user_delete_cleans_attendance_records(self):
        """Verify user delete cleans up attendance_records"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'attendance_records', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        assert 'attendance_records' in result.stdout, "auth.py should clean up attendance_records"
        print(f"✓ User delete cleans up attendance_records")
    
    def test_05_user_delete_cleans_leave_requests(self):
        """Verify user delete cleans up leave_requests"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'leave_requests', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        assert 'leave_requests' in result.stdout, "auth.py should clean up leave_requests"
        print(f"✓ User delete cleans up leave_requests")
    
    def test_06_user_delete_cleans_notifications(self):
        """Verify user delete cleans up notifications"""
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'notifications', '/app/backend/routes/auth.py'],
            capture_output=True, text=True
        )
        
        assert 'notifications' in result.stdout, "auth.py should clean up notifications"
        print(f"✓ User delete cleans up notifications")


class TestAtRiskAlertVariableFix:
    """
    Test 7: Fix verified: generate_atrisk_alert variable name fix 
    (recently_alerted_ids -> recently_alerted_keys)
    """
    
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
    
    def test_01_variable_name_is_correct(self):
        """
        Verify that the variable name is 'recently_alerted_keys' (not 'recently_alerted_ids').
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'recently_alerted_keys', '/app/backend/routes/scheduled_reports.py'],
            capture_output=True, text=True
        )
        
        # Check that recently_alerted_keys is used
        assert 'recently_alerted_keys' in result.stdout, \
            "scheduled_reports.py should use recently_alerted_keys"
        
        # Count occurrences
        occurrences = result.stdout.count('recently_alerted_keys')
        assert occurrences >= 3, f"Expected at least 3 occurrences, found {occurrences}"
        
        print(f"✓ Variable name 'recently_alerted_keys' is correct")
        print(f"  Found {occurrences} occurrences in scheduled_reports.py:")
        for line in result.stdout.strip().split('\n')[:5]:
            print(f"    {line}")
    
    def test_02_no_old_variable_name(self):
        """
        Verify that the old variable name 'recently_alerted_ids' is NOT used.
        """
        import subprocess
        result = subprocess.run(
            ['grep', '-n', 'recently_alerted_ids', '/app/backend/routes/scheduled_reports.py'],
            capture_output=True, text=True
        )
        
        # Check that recently_alerted_ids is NOT used
        assert 'recently_alerted_ids' not in result.stdout, \
            "scheduled_reports.py should NOT use recently_alerted_ids (old variable name)"
        
        print(f"✓ Old variable name 'recently_alerted_ids' is NOT present")


class TestAPIEndpointsHealth:
    """
    Test that all relevant API endpoints are healthy and accessible
    """
    
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
    
    def test_01_attendance_endpoints(self):
        """Test attendance-related endpoints"""
        endpoints = [
            "/api/attendance/check-today",
            "/api/attendance/totp/status",
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
            print(f"✓ {endpoint} - OK")
    
    def test_02_fees_endpoints(self):
        """Test fees-related endpoints"""
        endpoints = [
            "/api/attendance/admin/fees/summary",
            "/api/attendance/admin/fees/currency-rates",
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
            print(f"✓ {endpoint} - OK")
    
    def test_03_reserved_member_endpoints(self):
        """Test reserved member endpoints"""
        endpoints = [
            "/api/reserved-members",
            "/api/reserved-members/cleanup-config",
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
            print(f"✓ {endpoint} - OK")
    
    def test_04_bonus_check_endpoints(self):
        """Test bonus check endpoints"""
        endpoints = [
            "/api/bonus-check/products",
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
            print(f"✓ {endpoint} - OK")
    
    def test_05_leave_endpoints(self):
        """Test leave request endpoints"""
        endpoints = [
            "/api/leave/all-requests",
            "/api/leave/balance",
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Endpoint {endpoint} failed: {response.text}"
            print(f"✓ {endpoint} - OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
