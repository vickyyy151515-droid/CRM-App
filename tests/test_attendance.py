# Attendance System Tests
# Tests for Device-Registered QR Code Attendance System
# - Staff must scan unique QR with registered phone for first login of day
# - QR expires in 1 minute
# - One device per staff account

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAttendanceSystem:
    """Test suite for Attendance System APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.staff_token = None
        self.admin_token = None
        self.test_device_token = f"TEST-DEV-{uuid.uuid4().hex[:8]}"
        
    def get_staff_token(self):
        """Login as staff and get token"""
        if self.staff_token:
            return self.staff_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        if response.status_code == 200:
            self.staff_token = response.json().get("token")
            return self.staff_token
        pytest.skip("Staff login failed")
        
    def get_admin_token(self):
        """Login as admin and get token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("token")
            return self.admin_token
        pytest.skip("Admin login failed")
    
    # ==================== AUTH TESTS ====================
    
    def test_check_today_requires_auth(self):
        """Test that check-today endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/attendance/check-today")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_generate_qr_requires_auth(self):
        """Test that generate-qr endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/attendance/generate-qr")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_device_status_requires_auth(self):
        """Test that device-status endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/attendance/device-status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_register_device_requires_auth(self):
        """Test that register-device endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/attendance/register-device", json={
            "device_token": "test-token",
            "device_name": "Test Device"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    # ==================== STAFF ENDPOINTS ====================
    
    def test_check_today_attendance(self):
        """Test checking today's attendance status"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/check-today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "checked_in" in data, "Response should contain 'checked_in' field"
        assert "date" in data, "Response should contain 'date' field"
        
    def test_device_status(self):
        """Test getting device registration status"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/device-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "has_device" in data, "Response should contain 'has_device' field"
        
    def test_register_device(self):
        """Test registering a new device"""
        token = self.get_staff_token()
        response = self.session.post(
            f"{BASE_URL}/api/attendance/register-device",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_token": self.test_device_token,
                "device_name": "Test Mobile Device"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") in ["registered", "updated"], f"Expected status 'registered' or 'updated', got {data}"
        
    def test_generate_qr_code(self):
        """Test generating QR code for attendance"""
        token = self.get_staff_token()
        response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Either already checked in or got a new QR code
        if data.get("already_checked_in"):
            assert "check_in_time" in data, "Should have check_in_time if already checked in"
        else:
            assert "qr_code" in data, "Response should contain 'qr_code' field"
            assert data["qr_code"].startswith("ATT-"), "QR code should start with 'ATT-'"
            assert "expires_at" in data, "Response should contain 'expires_at' field"
            assert "expires_in_seconds" in data, "Response should contain 'expires_in_seconds' field"
            
    def test_my_attendance_records(self):
        """Test getting user's attendance records"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/my-records",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "month" in data, "Response should contain 'month' field"
        assert "records" in data, "Response should contain 'records' field"
        assert "summary" in data, "Response should contain 'summary' field"
        assert isinstance(data["records"], list), "Records should be a list"
        
    # ==================== SCAN ENDPOINT TESTS ====================
    
    def test_scan_invalid_qr_code(self):
        """Test scanning with invalid QR code"""
        response = self.session.post(
            f"{BASE_URL}/api/attendance/scan",
            json={
                "qr_code": "INVALID-QR-CODE",
                "device_token": self.test_device_token
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
    def test_scan_with_unregistered_device(self):
        """Test scanning with unregistered device token"""
        # First generate a valid QR code
        token = self.get_staff_token()
        qr_response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if qr_response.status_code == 200:
            data = qr_response.json()
            if not data.get("already_checked_in") and "qr_code" in data:
                # Try to scan with unregistered device
                scan_response = self.session.post(
                    f"{BASE_URL}/api/attendance/scan",
                    json={
                        "qr_code": data["qr_code"],
                        "device_token": f"UNREGISTERED-{uuid.uuid4().hex[:8]}"
                    }
                )
                # Should fail with 403 (device not registered)
                assert scan_response.status_code == 403, f"Expected 403, got {scan_response.status_code}: {scan_response.text}"
            else:
                pytest.skip("Already checked in today, cannot test scan")
        else:
            pytest.skip("Could not generate QR code")
            
    def test_scan_with_registered_device(self):
        """Test scanning with registered device - full flow"""
        token = self.get_staff_token()
        
        # First register the device
        reg_response = self.session.post(
            f"{BASE_URL}/api/attendance/register-device",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_token": self.test_device_token,
                "device_name": "Test Mobile Device"
            }
        )
        assert reg_response.status_code == 200, f"Device registration failed: {reg_response.text}"
        
        # Generate QR code
        qr_response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert qr_response.status_code == 200, f"QR generation failed: {qr_response.text}"
        
        data = qr_response.json()
        if data.get("already_checked_in"):
            # Already checked in, verify the response
            assert "check_in_time" in data
            print(f"Staff already checked in at {data.get('check_in_time')}")
        else:
            # Try to scan with registered device
            qr_code = data["qr_code"]
            scan_response = self.session.post(
                f"{BASE_URL}/api/attendance/scan",
                json={
                    "qr_code": qr_code,
                    "device_token": self.test_device_token
                }
            )
            # Should succeed or indicate already checked in
            assert scan_response.status_code == 200, f"Scan failed: {scan_response.text}"
            scan_data = scan_response.json()
            assert scan_data.get("status") in ["success", "already_checked_in"], f"Unexpected status: {scan_data}"
            
    # ==================== ADMIN ENDPOINTS ====================
    
    def test_admin_today_attendance_requires_admin(self):
        """Test that admin/today endpoint requires admin role"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"
        
    def test_admin_today_attendance(self):
        """Test getting today's attendance summary as admin"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "date" in data, "Response should contain 'date' field"
        assert "staff" in data, "Response should contain 'staff' field"
        assert "summary" in data, "Response should contain 'summary' field"
        assert isinstance(data["staff"], list), "Staff should be a list"
        
    def test_admin_attendance_records(self):
        """Test getting attendance records as admin"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/records",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "date_range" in data, "Response should contain 'date_range' field"
        assert "records" in data, "Response should contain 'records' field"
        assert "summary" in data, "Response should contain 'summary' field"
        
    def test_admin_registered_devices(self):
        """Test getting registered devices as admin"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "devices" in data, "Response should contain 'devices' field"
        assert "total" in data, "Response should contain 'total' field"
        assert isinstance(data["devices"], list), "Devices should be a list"
        
    def test_admin_export_attendance(self):
        """Test exporting attendance records as admin"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/export",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "data" in data, "Response should contain 'data' field"
        assert "date_range" in data, "Response should contain 'date_range' field"
        assert "total_records" in data, "Response should contain 'total_records' field"


class TestQRCodeExpiry:
    """Test QR code expiry functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_staff_token(self):
        """Login as staff and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Staff login failed")
        
    def test_qr_code_has_expiry_info(self):
        """Test that generated QR code includes expiry information"""
        token = self.get_staff_token()
        response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("already_checked_in"):
            assert "expires_at" in data, "QR code should have expiry timestamp"
            assert "expires_in_seconds" in data, "QR code should have expiry seconds"
            # Default expiry is 60 seconds
            assert data["expires_in_seconds"] == 60, f"Expected 60 seconds expiry, got {data['expires_in_seconds']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
