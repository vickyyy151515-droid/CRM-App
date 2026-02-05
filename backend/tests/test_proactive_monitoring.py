"""
Test Proactive Monitoring Feature
Tests for:
1. POST /api/data-sync/proactive-check - Run proactive health check and notify admins
2. GET /api/data-sync/monitoring-config - Get monitoring configuration
3. PUT /api/data-sync/monitoring-config - Update monitoring configuration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestProactiveMonitoring:
    """Test proactive monitoring endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def test_01_proactive_check_endpoint_exists(self):
        """Test POST /api/data-sync/proactive-check endpoint exists and returns valid response"""
        response = self.session.post(f"{BASE_URL}/api/data-sync/proactive-check")
        assert response.status_code == 200, f"Proactive check failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "health_score" in data, "Response should include health_score"
        assert "issues_found" in data, "Response should include issues_found"
        assert "critical_issues" in data, "Response should include critical_issues"
        assert "medium_issues" in data, "Response should include medium_issues"
        assert "warnings_found" in data, "Response should include warnings_found"
        assert "notifications_sent" in data, "Response should include notifications_sent"
        assert "message" in data, "Response should include message"
        assert "checked_at" in data, "Response should include checked_at"
        
        print(f"✓ Proactive check returned: health_score={data['health_score']}, notifications_sent={data['notifications_sent']}")
        
    def test_02_proactive_check_returns_valid_health_score(self):
        """Test that proactive check returns a valid health score (0-100)"""
        response = self.session.post(f"{BASE_URL}/api/data-sync/proactive-check")
        assert response.status_code == 200
        
        data = response.json()
        health_score = data.get("health_score")
        assert isinstance(health_score, (int, float)), "health_score should be a number"
        assert 0 <= health_score <= 100, f"health_score should be between 0-100, got {health_score}"
        
        print(f"✓ Health score is valid: {health_score}")
        
    def test_03_proactive_check_counts_are_non_negative(self):
        """Test that all issue counts are non-negative integers"""
        response = self.session.post(f"{BASE_URL}/api/data-sync/proactive-check")
        assert response.status_code == 200
        
        data = response.json()
        for field in ["issues_found", "critical_issues", "medium_issues", "warnings_found", "notifications_sent"]:
            value = data.get(field)
            assert isinstance(value, int), f"{field} should be an integer"
            assert value >= 0, f"{field} should be non-negative, got {value}"
            
        print(f"✓ All counts are valid non-negative integers")
        
    def test_04_get_monitoring_config_endpoint_exists(self):
        """Test GET /api/data-sync/monitoring-config endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/monitoring-config")
        assert response.status_code == 200, f"Get monitoring config failed: {response.text}"
        
        data = response.json()
        # Verify response structure - should have default config fields
        assert "enabled" in data, "Response should include enabled field"
        assert "check_interval_hours" in data, "Response should include check_interval_hours"
        assert "notify_on_warning" in data, "Response should include notify_on_warning"
        assert "notify_on_critical" in data, "Response should include notify_on_critical"
        
        print(f"✓ Monitoring config: enabled={data['enabled']}, interval={data['check_interval_hours']}h")
        
    def test_05_get_monitoring_config_returns_valid_types(self):
        """Test that monitoring config returns correct data types"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/monitoring-config")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("enabled"), bool), "enabled should be boolean"
        assert isinstance(data.get("check_interval_hours"), int), "check_interval_hours should be int"
        assert isinstance(data.get("notify_on_warning"), bool), "notify_on_warning should be boolean"
        assert isinstance(data.get("notify_on_critical"), bool), "notify_on_critical should be boolean"
        
        print(f"✓ All config fields have correct types")
        
    def test_06_put_monitoring_config_endpoint_exists(self):
        """Test PUT /api/data-sync/monitoring-config endpoint exists"""
        # First get current config
        get_response = self.session.get(f"{BASE_URL}/api/data-sync/monitoring-config")
        original_config = get_response.json()
        
        # Update config
        response = self.session.put(
            f"{BASE_URL}/api/data-sync/monitoring-config",
            params={
                "enabled": True,
                "check_interval_hours": 12,
                "notify_on_warning": True,
                "notify_on_critical": True
            }
        )
        assert response.status_code == 200, f"Update monitoring config failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should include message"
        assert data.get("enabled") == True, "enabled should be True"
        assert data.get("check_interval_hours") == 12, "check_interval_hours should be 12"
        
        print(f"✓ Monitoring config updated successfully")
        
    def test_07_put_monitoring_config_persists_changes(self):
        """Test that PUT changes are persisted and can be retrieved"""
        # Update config with specific values
        update_response = self.session.put(
            f"{BASE_URL}/api/data-sync/monitoring-config",
            params={
                "enabled": True,
                "check_interval_hours": 8,
                "notify_on_warning": False,
                "notify_on_critical": True
            }
        )
        assert update_response.status_code == 200
        
        # Get config and verify changes persisted
        get_response = self.session.get(f"{BASE_URL}/api/data-sync/monitoring-config")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data.get("enabled") == True, "enabled should be True"
        assert data.get("check_interval_hours") == 8, "check_interval_hours should be 8"
        assert data.get("notify_on_warning") == False, "notify_on_warning should be False"
        assert data.get("notify_on_critical") == True, "notify_on_critical should be True"
        
        print(f"✓ Config changes persisted correctly")
        
    def test_08_proactive_check_logs_activity(self):
        """Test that proactive check logs activity in system_logs"""
        # Run proactive check
        check_response = self.session.post(f"{BASE_URL}/api/data-sync/proactive-check")
        assert check_response.status_code == 200
        
        # Get activity log
        log_response = self.session.get(f"{BASE_URL}/api/data-sync/activity-log?limit=5")
        assert log_response.status_code == 200
        
        logs = log_response.json().get("logs", [])
        # Check if proactive_health_check log exists (only if notifications were sent)
        check_data = check_response.json()
        if check_data.get("notifications_sent", 0) > 0:
            proactive_logs = [l for l in logs if l.get("type") == "proactive_health_check"]
            assert len(proactive_logs) > 0, "Should have proactive_health_check log when notifications sent"
            print(f"✓ Proactive check logged in activity log")
        else:
            print(f"✓ No notifications sent (no critical issues), log may not be created")
            
    def test_09_health_check_endpoint_still_works(self):
        """Test that regular health check endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/health-check")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert "health_score" in data
        assert "status" in data
        assert "issues" in data
        assert "warnings" in data
        assert "stats" in data
        
        print(f"✓ Regular health check works: score={data['health_score']}, status={data['status']}")
        
    def test_10_sync_status_endpoint_still_works(self):
        """Test that sync status endpoint still works"""
        response = self.session.get(f"{BASE_URL}/api/data-sync/sync-status")
        assert response.status_code == 200, f"Sync status failed: {response.text}"
        
        data = response.json()
        assert "overall_status" in data
        assert "synced_features" in data
        assert "total_features" in data
        assert "features" in data
        
        print(f"✓ Sync status works: {data['synced_features']}/{data['total_features']} features synced")


class TestAdminActionsEndpoints:
    """Test admin action endpoints used by AdminActionsPanel component"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "vicky123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def test_11_bonanza_diagnose_product_mismatch_exists(self):
        """Test GET /api/bonanza/admin/diagnose-product-mismatch endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/bonanza/admin/diagnose-product-mismatch")
        assert response.status_code == 200, f"Diagnose product mismatch failed: {response.text}"
        
        data = response.json()
        assert "total_mismatched" in data, "Response should include total_mismatched"
        print(f"✓ Bonanza diagnose product mismatch: {data.get('total_mismatched', 0)} mismatched")
        
    def test_12_bonanza_diagnose_reserved_conflicts_exists(self):
        """Test GET /api/bonanza/admin/diagnose-reserved-conflicts endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/bonanza/admin/diagnose-reserved-conflicts")
        assert response.status_code == 200, f"Diagnose reserved conflicts failed: {response.text}"
        
        data = response.json()
        assert "total_conflicts" in data, "Response should include total_conflicts"
        print(f"✓ Bonanza diagnose reserved conflicts: {data.get('total_conflicts', 0)} conflicts")
        
    def test_13_memberwd_diagnose_product_mismatch_exists(self):
        """Test GET /api/memberwd/admin/diagnose-product-mismatch endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/diagnose-product-mismatch")
        assert response.status_code == 200, f"Diagnose product mismatch failed: {response.text}"
        
        data = response.json()
        assert "total_mismatched" in data, "Response should include total_mismatched"
        print(f"✓ MemberWD diagnose product mismatch: {data.get('total_mismatched', 0)} mismatched")
        
    def test_14_memberwd_diagnose_reserved_conflicts_exists(self):
        """Test GET /api/memberwd/admin/diagnose-reserved-conflicts endpoint exists"""
        response = self.session.get(f"{BASE_URL}/api/memberwd/admin/diagnose-reserved-conflicts")
        assert response.status_code == 200, f"Diagnose reserved conflicts failed: {response.text}"
        
        data = response.json()
        assert "total_conflicts" in data, "Response should include total_conflicts"
        print(f"✓ MemberWD diagnose reserved conflicts: {data.get('total_conflicts', 0)} conflicts")
        
    def test_15_bonanza_repair_product_mismatch_exists(self):
        """Test POST /api/bonanza/admin/repair-product-mismatch endpoint exists"""
        response = self.session.post(f"{BASE_URL}/api/bonanza/admin/repair-product-mismatch")
        assert response.status_code == 200, f"Repair product mismatch failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should include message"
        print(f"✓ Bonanza repair product mismatch: {data.get('message')}")
        
    def test_16_bonanza_fix_reserved_conflicts_exists(self):
        """Test POST /api/bonanza/admin/fix-reserved-conflicts endpoint exists"""
        response = self.session.post(f"{BASE_URL}/api/bonanza/admin/fix-reserved-conflicts")
        assert response.status_code == 200, f"Fix reserved conflicts failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should include message"
        print(f"✓ Bonanza fix reserved conflicts: {data.get('message')}")
        
    def test_17_memberwd_repair_product_mismatch_exists(self):
        """Test POST /api/memberwd/admin/repair-product-mismatch endpoint exists"""
        response = self.session.post(f"{BASE_URL}/api/memberwd/admin/repair-product-mismatch")
        assert response.status_code == 200, f"Repair product mismatch failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should include message"
        print(f"✓ MemberWD repair product mismatch: {data.get('message')}")
        
    def test_18_memberwd_fix_reserved_conflicts_exists(self):
        """Test POST /api/memberwd/admin/fix-reserved-conflicts endpoint exists"""
        response = self.session.post(f"{BASE_URL}/api/memberwd/admin/fix-reserved-conflicts")
        assert response.status_code == 200, f"Fix reserved conflicts failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should include message"
        print(f"✓ MemberWD fix reserved conflicts: {data.get('message')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
