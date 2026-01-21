"""
Test TOTP Attendance System
- Tests all TOTP-based attendance endpoints
- Verifies TOTP setup, verification, and check-in flows
- Tests admin endpoints for attendance management
"""

import pytest
import requests
import os
import pyotp

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MASTER_ADMIN = {"email": "vicky@crm.com", "password": "vicky123"}
STAFF = {"email": "staff@crm.com", "password": "staff123"}


class TestAuth:
    """Helper class for authentication"""
    
    @staticmethod
    def get_token(credentials):
        """Get auth token for user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    @staticmethod
    def get_headers(token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class TestTOTPSetup:
    """Test TOTP setup endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.staff_token:
            pytest.skip("Staff authentication failed")
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
    
    def test_totp_status_requires_auth(self):
        """Test that TOTP status endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/attendance/totp/status")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_totp_status_returns_setup_state(self):
        """Test TOTP status returns is_setup boolean"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.get(f"{BASE_URL}/api/attendance/totp/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "is_setup" in data
        assert isinstance(data["is_setup"], bool)
    
    def test_totp_setup_generates_qr_code(self):
        """Test TOTP setup generates QR code and secret"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "qr_code" in data
        assert "secret" in data
        assert "uri" in data
        assert "message" in data
        
        # Verify QR code is base64 PNG
        assert data["qr_code"].startswith("data:image/png;base64,")
        
        # Verify secret is valid base32
        assert len(data["secret"]) >= 16
        
        # Verify URI format
        assert "otpauth://totp/" in data["uri"]
        assert "CRM%20Attendance" in data["uri"] or "CRM Attendance" in data["uri"]
    
    def test_totp_setup_returns_same_secret_if_exists(self):
        """Test that calling setup again returns same secret"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # First call
        response1 = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        assert response1.status_code == 200
        secret1 = response1.json()["secret"]
        
        # Second call
        response2 = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        assert response2.status_code == 200
        secret2 = response2.json()["secret"]
        
        # Should return same secret
        assert secret1 == secret2


class TestTOTPVerification:
    """Test TOTP verification endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.staff_token:
            pytest.skip("Staff authentication failed")
    
    def test_verify_setup_requires_auth(self):
        """Test that verify-setup endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            json={"code": "123456"}
        )
        assert response.status_code == 401 or response.status_code == 403
    
    def test_verify_setup_rejects_invalid_code(self):
        """Test that invalid TOTP code is rejected"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # First ensure TOTP is set up
        requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        
        # Try with invalid code
        response = requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            headers=headers,
            json={"code": "000000"}
        )
        assert response.status_code == 400
        assert "Invalid code" in response.json().get("detail", "")
    
    def test_verify_setup_accepts_valid_code(self):
        """Test that valid TOTP code is accepted"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # Get the secret
        setup_response = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        assert setup_response.status_code == 200
        secret = setup_response.json()["secret"]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret, interval=30)
        valid_code = totp.now()
        
        # Verify with valid code
        response = requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            headers=headers,
            json={"code": valid_code}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "verified" in data.get("message", "").lower()


class TestTOTPCheckIn:
    """Test TOTP check-in endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.staff_token:
            pytest.skip("Staff authentication failed")
    
    def test_checkin_requires_auth(self):
        """Test that check-in endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/checkin",
            json={"code": "123456"}
        )
        assert response.status_code == 401 or response.status_code == 403
    
    def test_check_today_requires_auth(self):
        """Test that check-today endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/attendance/check-today")
        assert response.status_code == 401 or response.status_code == 403
    
    def test_check_today_returns_status(self):
        """Test check-today returns checked_in status"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.get(f"{BASE_URL}/api/attendance/check-today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "checked_in" in data
        assert isinstance(data["checked_in"], bool)
    
    def test_checkin_rejects_invalid_code(self):
        """Test that invalid TOTP code is rejected for check-in"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # Ensure TOTP is set up and verified first
        setup_response = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        secret = setup_response.json()["secret"]
        
        # Verify setup
        totp = pyotp.TOTP(secret, interval=30)
        valid_code = totp.now()
        requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            headers=headers,
            json={"code": valid_code}
        )
        
        # Try check-in with invalid code
        response = requests.post(
            f"{BASE_URL}/api/attendance/checkin",
            headers=headers,
            json={"code": "000000"}
        )
        # Should be 400 (invalid code) or 400 (already checked in)
        assert response.status_code == 400
    
    def test_checkin_with_valid_code(self):
        """Test check-in with valid TOTP code"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # Get the secret
        setup_response = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        secret = setup_response.json()["secret"]
        
        # Verify setup first
        totp = pyotp.TOTP(secret, interval=30)
        valid_code = totp.now()
        requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            headers=headers,
            json={"code": valid_code}
        )
        
        # Try check-in
        new_code = totp.now()
        response = requests.post(
            f"{BASE_URL}/api/attendance/checkin",
            headers=headers,
            json={"code": new_code}
        )
        
        # Should be 200 (success) or 400 (already checked in today)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") == True
            assert "check_in_time" in data
            assert "is_late" in data
            assert "attendance_status" in data
        else:
            # Already checked in
            assert "already checked in" in response.json().get("detail", "").lower()


class TestAdminAttendanceEndpoints:
    """Test admin attendance management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
    
    def test_admin_today_requires_admin(self):
        """Test that admin/today requires admin role"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/today", headers=headers)
        assert response.status_code == 403
    
    def test_admin_today_returns_summary(self):
        """Test admin/today returns attendance summary"""
        headers = TestAuth.get_headers(self.admin_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/today", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "date" in data
        assert "summary" in data
        assert "records" in data
        assert "not_checked_in" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_staff" in summary
        assert "checked_in" in summary
        assert "not_checked_in" in summary
        assert "on_time" in summary
        assert "late" in summary
    
    def test_admin_totp_status_requires_admin(self):
        """Test that admin/totp-status requires admin role"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/totp-status", headers=headers)
        assert response.status_code == 403
    
    def test_admin_totp_status_returns_staff_list(self):
        """Test admin/totp-status returns staff TOTP status list"""
        headers = TestAuth.get_headers(self.admin_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/totp-status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "staff" in data
        assert isinstance(data["staff"], list)
        
        # If there are staff members, verify structure
        if len(data["staff"]) > 0:
            staff = data["staff"][0]
            assert "staff_id" in staff
            assert "staff_name" in staff
            assert "is_setup" in staff
            assert "is_verified" in staff
    
    def test_admin_records_requires_admin(self):
        """Test that admin/records requires admin role"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/records", headers=headers)
        assert response.status_code == 403
    
    def test_admin_records_returns_history(self):
        """Test admin/records returns attendance history"""
        headers = TestAuth.get_headers(self.admin_token)
        response = requests.get(f"{BASE_URL}/api/attendance/admin/records", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "start_date" in data
        assert "end_date" in data
        assert "total_records" in data
        assert "records" in data
        assert isinstance(data["records"], list)
    
    def test_admin_records_with_date_filter(self):
        """Test admin/records accepts date filters"""
        headers = TestAuth.get_headers(self.admin_token)
        response = requests.get(
            f"{BASE_URL}/api/attendance/admin/records",
            headers=headers,
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["start_date"] == "2026-01-01"
        assert data["end_date"] == "2026-01-31"


class TestAdminTOTPReset:
    """Test admin TOTP reset functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
    
    def test_reset_totp_requires_admin(self):
        """Test that TOTP reset requires admin role"""
        headers = TestAuth.get_headers(self.staff_token)
        response = requests.delete(
            f"{BASE_URL}/api/attendance/admin/totp/some-staff-id",
            headers=headers
        )
        assert response.status_code == 403
    
    def test_reset_totp_nonexistent_returns_404(self):
        """Test that resetting nonexistent TOTP returns 404"""
        headers = TestAuth.get_headers(self.admin_token)
        response = requests.delete(
            f"{BASE_URL}/api/attendance/admin/totp/nonexistent-staff-id-12345",
            headers=headers
        )
        assert response.status_code == 404


class TestTOTPFlow:
    """Test complete TOTP flow: setup -> verify -> check-in"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.staff_token = TestAuth.get_token(STAFF)
        self.admin_token = TestAuth.get_token(MASTER_ADMIN)
        if not self.staff_token:
            pytest.skip("Staff authentication failed")
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
    
    def test_complete_totp_flow(self):
        """Test complete TOTP flow from setup to check-in"""
        headers = TestAuth.get_headers(self.staff_token)
        
        # Step 1: Check initial status
        status_response = requests.get(f"{BASE_URL}/api/attendance/totp/status", headers=headers)
        assert status_response.status_code == 200
        
        # Step 2: Setup TOTP
        setup_response = requests.post(f"{BASE_URL}/api/attendance/totp/setup", headers=headers)
        assert setup_response.status_code == 200
        secret = setup_response.json()["secret"]
        
        # Step 3: Generate valid code
        totp = pyotp.TOTP(secret, interval=30)
        valid_code = totp.now()
        
        # Step 4: Verify setup
        verify_response = requests.post(
            f"{BASE_URL}/api/attendance/totp/verify-setup",
            headers=headers,
            json={"code": valid_code}
        )
        assert verify_response.status_code == 200
        
        # Step 5: Check status again - should be setup
        status_response2 = requests.get(f"{BASE_URL}/api/attendance/totp/status", headers=headers)
        assert status_response2.status_code == 200
        assert status_response2.json()["is_setup"] == True
        
        # Step 6: Try check-in
        new_code = totp.now()
        checkin_response = requests.post(
            f"{BASE_URL}/api/attendance/checkin",
            headers=headers,
            json={"code": new_code}
        )
        # Should be 200 (success) or 400 (already checked in)
        assert checkin_response.status_code in [200, 400]
        
        # Step 7: Check today's attendance
        check_today_response = requests.get(f"{BASE_URL}/api/attendance/check-today", headers=headers)
        assert check_today_response.status_code == 200
        
        print("Complete TOTP flow test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
