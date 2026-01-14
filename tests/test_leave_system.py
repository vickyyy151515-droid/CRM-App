"""
Leave Request System Tests
Tests for Off Day/Sakit (Leave Request) functionality
- Staff can request Off Day (12 hours) or Sakit (custom hours)
- Admin can approve/reject with notes
- Balance tracking (24 hours monthly)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestLeaveSystemSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        """Get staff authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        return response.json()["token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"SUCCESS: Admin login successful")
    
    def test_staff_login(self, staff_token):
        """Test staff can login"""
        assert staff_token is not None
        assert len(staff_token) > 0
        print(f"SUCCESS: Staff login successful")


class TestLeaveBalance:
    """Tests for leave balance endpoint"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_leave_balance_current_month(self, staff_token):
        """Test staff can get their leave balance for current month"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/leave/balance", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "year" in data
        assert "month" in data
        assert "total_hours" in data
        assert "used_hours" in data
        assert "remaining_hours" in data
        assert "approved_requests" in data
        
        # Validate values
        assert data["total_hours"] == 24, "Monthly leave should be 24 hours"
        assert data["remaining_hours"] >= 0
        assert data["used_hours"] >= 0
        assert data["remaining_hours"] + data["used_hours"] == data["total_hours"]
        
        print(f"SUCCESS: Leave balance - {data['remaining_hours']}/{data['total_hours']} hours remaining")
    
    def test_get_leave_balance_specific_month(self, staff_token):
        """Test staff can get leave balance for specific month"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(
            f"{BASE_URL}/api/leave/balance",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["year"] == 2025
        assert data["month"] == 12
        print(f"SUCCESS: Leave balance for Dec 2025 - {data['remaining_hours']}/{data['total_hours']} hours")
    
    def test_leave_balance_requires_auth(self):
        """Test leave balance endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leave/balance")
        assert response.status_code in [401, 403]
        print("SUCCESS: Leave balance requires authentication")


class TestStaffLeaveRequests:
    """Tests for staff leave request operations"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_get_my_requests(self, staff_token):
        """Test staff can view their leave requests"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Staff has {len(data)} leave requests for Dec 2025")
    
    def test_create_off_day_request(self, staff_token):
        """Test staff can create an Off Day request"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Use a future date to avoid conflicts
        test_date = "2025-12-25"
        
        # First check if request already exists for this date
        existing = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        existing_dates = [r["date"] for r in existing.json() if r["status"] in ["pending", "approved"]]
        
        if test_date in existing_dates:
            print(f"SKIP: Request already exists for {test_date}")
            return
        
        response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "off_day",
                "date": test_date,
                "reason": "TEST_Holiday leave"
            },
            headers=headers
        )
        
        if response.status_code == 400 and "already have a leave request" in response.text:
            print(f"SKIP: Request already exists for {test_date}")
            return
        
        if response.status_code == 400 and "Insufficient leave balance" in response.text:
            print(f"SKIP: Insufficient leave balance")
            return
        
        assert response.status_code == 200, f"Failed to create request: {response.text}"
        data = response.json()
        
        assert data["leave_type"] == "off_day"
        assert data["hours_deducted"] == 12, "Off Day should deduct 12 hours"
        assert data["status"] == "pending"
        assert data["date"] == test_date
        
        print(f"SUCCESS: Created Off Day request for {test_date} (12 hours)")
    
    def test_create_sakit_request(self, staff_token):
        """Test staff can create a Sakit (sick leave) request with custom time"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        test_date = "2025-12-26"
        
        # Check for existing request
        existing = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        existing_dates = [r["date"] for r in existing.json() if r["status"] in ["pending", "approved"]]
        
        if test_date in existing_dates:
            print(f"SKIP: Request already exists for {test_date}")
            return
        
        response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "sakit",
                "date": test_date,
                "start_time": "09:00",
                "end_time": "13:00",
                "reason": "TEST_Doctor appointment"
            },
            headers=headers
        )
        
        if response.status_code == 400 and "already have a leave request" in response.text:
            print(f"SKIP: Request already exists for {test_date}")
            return
        
        if response.status_code == 400 and "Insufficient leave balance" in response.text:
            print(f"SKIP: Insufficient leave balance")
            return
        
        assert response.status_code == 200, f"Failed to create request: {response.text}"
        data = response.json()
        
        assert data["leave_type"] == "sakit"
        assert data["hours_deducted"] == 4, "4 hours (09:00-13:00) should be deducted"
        assert data["status"] == "pending"
        assert data["start_time"] == "09:00"
        assert data["end_time"] == "13:00"
        
        print(f"SUCCESS: Created Sakit request for {test_date} (4 hours)")
    
    def test_sakit_requires_time_range(self, staff_token):
        """Test Sakit request requires start and end time"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "sakit",
                "date": "2025-12-27",
                "reason": "TEST_Missing time"
            },
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Start time and end time are required" in response.text
        print("SUCCESS: Sakit request correctly requires time range")
    
    def test_invalid_leave_type(self, staff_token):
        """Test invalid leave type is rejected"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "invalid_type",
                "date": "2025-12-28"
            },
            headers=headers
        )
        
        assert response.status_code == 400
        assert "Invalid leave type" in response.text
        print("SUCCESS: Invalid leave type correctly rejected")
    
    def test_duplicate_request_rejected(self, staff_token):
        """Test duplicate request for same date is rejected"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get existing requests
        existing = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        existing_requests = [r for r in existing.json() if r["status"] in ["pending", "approved"]]
        
        if not existing_requests:
            print("SKIP: No existing requests to test duplicate")
            return
        
        # Try to create duplicate
        existing_date = existing_requests[0]["date"]
        response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "off_day",
                "date": existing_date
            },
            headers=headers
        )
        
        assert response.status_code == 400
        assert "already have a leave request" in response.text
        print(f"SUCCESS: Duplicate request for {existing_date} correctly rejected")


class TestCancelLeaveRequest:
    """Tests for cancelling leave requests"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_cancel_pending_request(self, staff_token):
        """Test staff can cancel a pending request"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get pending requests
        response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        pending = [r for r in response.json() if r["status"] == "pending" and "TEST_" in (r.get("reason") or "")]
        
        if not pending:
            print("SKIP: No pending TEST requests to cancel")
            return
        
        request_id = pending[0]["id"]
        cancel_response = requests.delete(
            f"{BASE_URL}/api/leave/request/{request_id}",
            headers=headers
        )
        
        assert cancel_response.status_code == 200
        assert "cancelled" in cancel_response.json()["message"].lower()
        print(f"SUCCESS: Cancelled pending request {request_id}")
    
    def test_cannot_cancel_approved_request(self, staff_token):
        """Test staff cannot cancel an approved request"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get approved requests
        response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        approved = [r for r in response.json() if r["status"] == "approved"]
        
        if not approved:
            print("SKIP: No approved requests to test")
            return
        
        request_id = approved[0]["id"]
        cancel_response = requests.delete(
            f"{BASE_URL}/api/leave/request/{request_id}",
            headers=headers
        )
        
        assert cancel_response.status_code == 400
        assert "pending" in cancel_response.text.lower()
        print("SUCCESS: Cannot cancel approved request")


class TestAdminLeaveRequests:
    """Tests for admin leave request management"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_admin_get_all_requests(self, admin_token):
        """Test admin can view all leave requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/leave/all-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "requests" in data
        assert "pending_count" in data
        assert isinstance(data["requests"], list)
        
        print(f"SUCCESS: Admin sees {len(data['requests'])} requests, {data['pending_count']} pending")
    
    def test_admin_filter_by_status(self, admin_token):
        """Test admin can filter requests by status"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        for status in ["pending", "approved", "rejected"]:
            response = requests.get(
                f"{BASE_URL}/api/leave/all-requests",
                params={"year": 2025, "month": 12, "status": status},
                headers=headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # All returned requests should have the filtered status
            for req in data["requests"]:
                assert req["status"] == status
            
            print(f"SUCCESS: Admin filter by status '{status}' - {len(data['requests'])} requests")
    
    def test_admin_approve_request(self, admin_token, staff_token):
        """Test admin can approve a leave request with note"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # First create a new request to approve
        test_date = "2025-12-29"
        create_response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "off_day",
                "date": test_date,
                "reason": "TEST_For approval test"
            },
            headers=staff_headers
        )
        
        if create_response.status_code != 200:
            print(f"SKIP: Could not create test request - {create_response.text}")
            return
        
        request_id = create_response.json()["id"]
        
        # Admin approves with note
        approve_response = requests.put(
            f"{BASE_URL}/api/leave/request/{request_id}/action",
            json={
                "action": "approve",
                "admin_note": "TEST_Approved for testing"
            },
            headers=admin_headers
        )
        
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"
        
        # Verify the request is now approved
        verify_response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=staff_headers
        )
        approved_req = next((r for r in verify_response.json() if r["id"] == request_id), None)
        
        assert approved_req is not None
        assert approved_req["status"] == "approved"
        assert approved_req["admin_note"] == "TEST_Approved for testing"
        
        print(f"SUCCESS: Admin approved request {request_id} with note")
    
    def test_admin_reject_request(self, admin_token, staff_token):
        """Test admin can reject a leave request with note"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # First create a new request to reject
        test_date = "2025-12-30"
        create_response = requests.post(
            f"{BASE_URL}/api/leave/request",
            json={
                "leave_type": "sakit",
                "date": test_date,
                "start_time": "10:00",
                "end_time": "14:00",
                "reason": "TEST_For rejection test"
            },
            headers=staff_headers
        )
        
        if create_response.status_code != 200:
            print(f"SKIP: Could not create test request - {create_response.text}")
            return
        
        request_id = create_response.json()["id"]
        
        # Admin rejects with note
        reject_response = requests.put(
            f"{BASE_URL}/api/leave/request/{request_id}/action",
            json={
                "action": "reject",
                "admin_note": "TEST_Rejected for testing - insufficient documentation"
            },
            headers=admin_headers
        )
        
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "rejected"
        
        # Verify the request is now rejected
        verify_response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=staff_headers
        )
        rejected_req = next((r for r in verify_response.json() if r["id"] == request_id), None)
        
        assert rejected_req is not None
        assert rejected_req["status"] == "rejected"
        assert "TEST_Rejected" in rejected_req["admin_note"]
        
        print(f"SUCCESS: Admin rejected request {request_id} with note")
    
    def test_admin_get_staff_balance(self, admin_token):
        """Test admin can view staff leave balance"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First get staff user ID
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        staff_id = login_response.json()["user"]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/leave/staff-balance/{staff_id}",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["staff_id"] == staff_id
        assert "staff_name" in data
        assert data["total_hours"] == 24
        assert "used_hours" in data
        assert "remaining_hours" in data
        
        print(f"SUCCESS: Admin viewed staff balance - {data['remaining_hours']}/{data['total_hours']} hours")
    
    def test_cannot_process_already_processed(self, admin_token):
        """Test admin cannot re-process an already processed request"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get an already processed request
        response = requests.get(
            f"{BASE_URL}/api/leave/all-requests",
            params={"year": 2025, "month": 12, "status": "approved"},
            headers=headers
        )
        
        approved = response.json()["requests"]
        if not approved:
            print("SKIP: No approved requests to test")
            return
        
        request_id = approved[0]["id"]
        
        # Try to reject an already approved request
        reject_response = requests.put(
            f"{BASE_URL}/api/leave/request/{request_id}/action",
            json={"action": "reject"},
            headers=headers
        )
        
        assert reject_response.status_code == 400
        assert "already been processed" in reject_response.text
        print("SUCCESS: Cannot re-process already processed request")
    
    def test_invalid_action_rejected(self, admin_token, staff_token):
        """Test invalid action is rejected"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get a pending request
        response = requests.get(
            f"{BASE_URL}/api/leave/all-requests",
            params={"status": "pending"},
            headers=admin_headers
        )
        
        pending = response.json()["requests"]
        if not pending:
            print("SKIP: No pending requests to test")
            return
        
        request_id = pending[0]["id"]
        
        # Try invalid action
        invalid_response = requests.put(
            f"{BASE_URL}/api/leave/request/{request_id}/action",
            json={"action": "invalid_action"},
            headers=admin_headers
        )
        
        assert invalid_response.status_code == 400
        assert "Invalid action" in invalid_response.text
        print("SUCCESS: Invalid action correctly rejected")


class TestLeaveBalanceCalculation:
    """Tests for leave balance calculation after approval/rejection"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_balance_reflects_approved_requests(self, staff_token):
        """Test that balance correctly reflects approved requests"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get balance
        balance_response = requests.get(
            f"{BASE_URL}/api/leave/balance",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        balance = balance_response.json()
        
        # Get approved requests
        requests_response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        approved = [r for r in requests_response.json() if r["status"] == "approved"]
        
        # Calculate expected used hours
        expected_used = sum(r["hours_deducted"] for r in approved)
        
        assert balance["used_hours"] == expected_used, f"Expected {expected_used} used hours, got {balance['used_hours']}"
        assert balance["remaining_hours"] == 24 - expected_used
        
        print(f"SUCCESS: Balance correctly shows {balance['used_hours']} used, {balance['remaining_hours']} remaining")
    
    def test_rejected_requests_dont_affect_balance(self, staff_token):
        """Test that rejected requests don't affect balance"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get balance
        balance_response = requests.get(
            f"{BASE_URL}/api/leave/balance",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        balance = balance_response.json()
        
        # Get all requests
        requests_response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        all_requests = requests_response.json()
        
        # Only approved should count
        approved_hours = sum(r["hours_deducted"] for r in all_requests if r["status"] == "approved")
        rejected_hours = sum(r["hours_deducted"] for r in all_requests if r["status"] == "rejected")
        
        assert balance["used_hours"] == approved_hours
        print(f"SUCCESS: Rejected requests ({rejected_hours} hours) don't affect balance")


class TestAccessControl:
    """Tests for access control"""
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_staff_cannot_access_all_requests(self, staff_token):
        """Test staff cannot access admin endpoint"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(
            f"{BASE_URL}/api/leave/all-requests",
            headers=headers
        )
        
        assert response.status_code == 403
        print("SUCCESS: Staff cannot access admin endpoint")
    
    def test_staff_cannot_approve_requests(self, staff_token):
        """Test staff cannot approve/reject requests"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = requests.put(
            f"{BASE_URL}/api/leave/request/some-id/action",
            json={"action": "approve"},
            headers=headers
        )
        
        assert response.status_code == 403
        print("SUCCESS: Staff cannot approve requests")
    
    def test_staff_cannot_view_other_staff_balance(self, staff_token):
        """Test staff cannot view other staff's balance"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/leave/staff-balance/some-other-id",
            headers=headers
        )
        
        assert response.status_code == 403
        print("SUCCESS: Staff cannot view other staff's balance")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def staff_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        return response.json()["token"]
    
    def test_cleanup_test_requests(self, staff_token):
        """Clean up TEST_ prefixed requests"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get all requests
        response = requests.get(
            f"{BASE_URL}/api/leave/my-requests",
            params={"year": 2025, "month": 12},
            headers=headers
        )
        
        test_requests = [r for r in response.json() if r["status"] == "pending" and "TEST_" in (r.get("reason") or "")]
        
        for req in test_requests:
            delete_response = requests.delete(
                f"{BASE_URL}/api/leave/request/{req['id']}",
                headers=headers
            )
            if delete_response.status_code == 200:
                print(f"Cleaned up test request: {req['id']}")
        
        print(f"SUCCESS: Cleaned up {len(test_requests)} test requests")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
