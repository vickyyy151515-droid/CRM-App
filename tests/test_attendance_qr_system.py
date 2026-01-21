# Attendance QR System Tests - Iteration 29
# Tests for QR Code based attendance with device registration
# Key features:
# - 1 Staff = 1 Phone (device registration required)
# - 1 QR Code = 1 Use (single-use QR codes)
# - Shift hours 11:00 AM - 23:00 PM with lateness tracking

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAttendanceAuth:
    """Test authentication requirements for attendance endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def test_check_today_requires_auth(self):
        """check-today endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/attendance/check-today")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_generate_qr_requires_auth(self):
        """generate-qr endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/attendance/generate-qr")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_device_status_requires_auth(self):
        """device-status endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/attendance/device-status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_register_device_requires_auth(self):
        """register-device endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/attendance/register-device", json={
            "device_id": "test-device",
            "device_name": "Test Device"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
    def test_scan_requires_auth(self):
        """scan endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/attendance/scan", json={
            "qr_code": "test-qr",
            "device_id": "test-device"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"


class TestStaffAttendanceEndpoints:
    """Test staff attendance endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.staff_token = None
        
    def get_staff_token(self):
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
        
    def test_check_today_returns_checked_in_status(self):
        """check-today returns checked_in boolean"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/check-today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "checked_in" in data, "Response should contain 'checked_in' field"
        assert isinstance(data["checked_in"], bool), "checked_in should be boolean"
        
    def test_device_status_returns_has_device(self):
        """device-status returns has_device boolean"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/device-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "has_device" in data, "Response should contain 'has_device' field"
        assert isinstance(data["has_device"], bool), "has_device should be boolean"
        
    def test_generate_qr_returns_qr_code_or_already_checked_in(self):
        """generate-qr returns QR code or already_checked_in status"""
        token = self.get_staff_token()
        response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        if data.get("already_checked_in"):
            assert "check_in_time" in data, "Should have check_in_time if already checked in"
            assert "message" in data, "Should have message if already checked in"
        else:
            assert "qr_code" in data, "Response should contain 'qr_code' field"
            assert data["qr_code"].startswith("ATT-"), "QR code should start with 'ATT-'"
            assert "expires_in_seconds" in data, "Response should contain 'expires_in_seconds'"
            assert data["expires_in_seconds"] == 60, "QR should expire in 60 seconds"
            assert "staff_name" in data, "Response should contain 'staff_name'"
            
    def test_qr_code_format_is_unique(self):
        """QR code format includes staff ID and timestamp for uniqueness"""
        token = self.get_staff_token()
        response = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if not data.get("already_checked_in"):
            qr_code = data["qr_code"]
            # Format: ATT-{staff_id}-{random_token}-{timestamp}
            parts = qr_code.split("-")
            assert len(parts) >= 4, f"QR code should have at least 4 parts: {qr_code}"
            assert parts[0] == "ATT", "QR code should start with ATT"


class TestDeviceRegistration:
    """Test device registration functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.staff_token = None
        self.admin_token = None
        
    def get_staff_token(self):
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
        
    def test_register_device_prevents_duplicate(self):
        """Staff can only register one device - duplicate registration fails"""
        token = self.get_staff_token()
        
        # Check if device already registered
        status_resp = self.session.get(
            f"{BASE_URL}/api/attendance/device-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if status_resp.status_code == 200 and status_resp.json().get("has_device"):
            # Try to register another device - should fail
            response = self.session.post(
                f"{BASE_URL}/api/attendance/register-device",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "device_id": f"TEST-NEW-{uuid.uuid4().hex[:8]}",
                    "device_name": "New Test Device"
                }
            )
            assert response.status_code == 400, f"Expected 400 for duplicate device, got {response.status_code}"
            assert "already have a registered device" in response.json().get("detail", "").lower()
        else:
            pytest.skip("Staff has no device registered - cannot test duplicate prevention")
            
    def test_device_status_shows_registered_device_info(self):
        """device-status shows device_name and registered_at when device exists"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/device-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_device"):
            assert "device_name" in data, "Should have device_name when device registered"
            assert "registered_at" in data, "Should have registered_at when device registered"


class TestQRScanning:
    """Test QR code scanning functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.staff_token = None
        
    def get_staff_token(self):
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
        
    def test_scan_invalid_qr_returns_400(self):
        """Scanning invalid QR code returns 400"""
        token = self.get_staff_token()
        
        # Get registered device ID first
        status_resp = self.session.get(
            f"{BASE_URL}/api/attendance/device-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if status_resp.status_code == 200 and status_resp.json().get("has_device"):
            # Need to get actual device_id from admin endpoint
            admin_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@crm.com",
                "password": "admin123"
            })
            admin_token = admin_resp.json().get("token")
            
            devices_resp = self.session.get(
                f"{BASE_URL}/api/attendance/admin/devices",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            devices = devices_resp.json().get("devices", [])
            staff_device = next((d for d in devices if d.get("staff_id") == "staff-user-1"), None)
            
            if staff_device:
                response = self.session.post(
                    f"{BASE_URL}/api/attendance/scan",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "qr_code": "INVALID-QR-CODE",
                        "device_id": staff_device["device_id"]
                    }
                )
                assert response.status_code == 400, f"Expected 400, got {response.status_code}"
                assert "invalid" in response.json().get("detail", "").lower()
            else:
                pytest.skip("Could not find staff device")
        else:
            pytest.skip("Staff has no registered device")
            
    def test_scan_with_wrong_device_returns_403(self):
        """Scanning with unregistered device returns 403"""
        token = self.get_staff_token()
        
        # Generate QR code
        qr_resp = self.session.post(
            f"{BASE_URL}/api/attendance/generate-qr",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if qr_resp.status_code == 200:
            data = qr_resp.json()
            if not data.get("already_checked_in"):
                # Try to scan with wrong device
                response = self.session.post(
                    f"{BASE_URL}/api/attendance/scan",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "qr_code": data["qr_code"],
                        "device_id": f"WRONG-DEVICE-{uuid.uuid4().hex[:8]}"
                    }
                )
                assert response.status_code == 403, f"Expected 403, got {response.status_code}"
                assert "not registered" in response.json().get("detail", "").lower()
            else:
                pytest.skip("Already checked in today")
        else:
            pytest.skip("Could not generate QR code")


class TestAdminAttendanceEndpoints:
    """Test admin attendance management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.staff_token = None
        
    def get_admin_token(self):
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
        
    def get_staff_token(self):
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
        
    def test_admin_today_requires_admin_role(self):
        """admin/today endpoint requires admin role"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"
        
    def test_admin_today_returns_summary(self):
        """admin/today returns attendance summary with correct structure"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check required fields
        assert "date" in data, "Response should contain 'date'"
        assert "summary" in data, "Response should contain 'summary'"
        assert "records" in data, "Response should contain 'records'"
        assert "not_checked_in" in data, "Response should contain 'not_checked_in'"
        
        # Check summary structure
        summary = data["summary"]
        assert "total_staff" in summary, "Summary should have total_staff"
        assert "checked_in" in summary, "Summary should have checked_in"
        assert "not_checked_in" in summary, "Summary should have not_checked_in"
        assert "on_time" in summary, "Summary should have on_time"
        assert "late" in summary, "Summary should have late"
        
        # Validate counts are consistent
        assert summary["checked_in"] + summary["not_checked_in"] == summary["total_staff"]
        assert summary["on_time"] + summary["late"] == summary["checked_in"]
        
    def test_admin_devices_returns_device_list(self):
        """admin/devices returns list of registered devices"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "devices" in data, "Response should contain 'devices'"
        assert isinstance(data["devices"], list), "devices should be a list"
        
        # Check device structure if any exist
        if len(data["devices"]) > 0:
            device = data["devices"][0]
            assert "staff_id" in device, "Device should have staff_id"
            assert "staff_name" in device, "Device should have staff_name"
            assert "device_id" in device, "Device should have device_id"
            assert "device_name" in device, "Device should have device_name"
            assert "registered_at" in device, "Device should have registered_at"
            
    def test_admin_records_returns_history(self):
        """admin/records returns attendance history"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/records",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "start_date" in data, "Response should contain 'start_date'"
        assert "end_date" in data, "Response should contain 'end_date'"
        assert "total_records" in data, "Response should contain 'total_records'"
        assert "records" in data, "Response should contain 'records'"
        assert isinstance(data["records"], list), "records should be a list"
        
    def test_admin_records_with_date_filter(self):
        """admin/records accepts date range filter"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/records?start_date=2026-01-01&end_date=2026-01-31",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["start_date"] == "2026-01-01", "start_date should match filter"
        assert data["end_date"] == "2026-01-31", "end_date should match filter"
        
    def test_admin_export_returns_records(self):
        """admin/export returns exportable attendance data"""
        token = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/export?start_date=2026-01-01&end_date=2026-01-31",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "records" in data, "Response should contain 'records'"
        assert isinstance(data["records"], list), "records should be a list"
        
    def test_admin_devices_requires_admin_role(self):
        """admin/devices endpoint requires admin role"""
        token = self.get_staff_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"


class TestDeleteDevice:
    """Test device deletion by admin"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
        
    def test_delete_nonexistent_device_returns_404(self):
        """Deleting non-existent device returns 404"""
        token = self.get_admin_token()
        response = self.session.delete(
            f"{BASE_URL}/api/attendance/admin/device/nonexistent-staff-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
    def test_delete_device_requires_admin(self):
        """Delete device endpoint requires admin role"""
        # Login as staff
        staff_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        staff_token = staff_resp.json().get("token")
        
        response = self.session.delete(
            f"{BASE_URL}/api/attendance/admin/device/staff-user-1",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for staff, got {response.status_code}"


class TestMasterAdminAccess:
    """Test master_admin role access to attendance endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_master_admin_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Master admin login failed")
        
    def test_master_admin_can_access_admin_today(self):
        """master_admin can access admin/today endpoint"""
        token = self.get_master_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_master_admin_can_access_admin_devices(self):
        """master_admin can access admin/devices endpoint"""
        token = self.get_master_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/attendance/admin/devices",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
