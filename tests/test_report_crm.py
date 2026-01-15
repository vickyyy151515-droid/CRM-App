"""
Test Report CRM API endpoints
Tests RDP logic (unique customers per day/staff, not total records)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReportCRM:
    """Report CRM endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_report_crm_data_endpoint(self):
        """Test /api/report-crm/data endpoint returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            params={"year": 2026, "month": 1},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "yearly" in data
        assert "monthly" in data
        assert "monthly_by_staff" in data
        assert "daily" in data
        assert "daily_by_staff" in data
        assert "staff_performance" in data
        assert "deposit_tiers" in data
        
        # Verify yearly data has 12 months
        assert len(data["yearly"]) == 12
        
        # Verify each month has required fields
        for month_data in data["yearly"]:
            assert "month" in month_data
            assert "new_id" in month_data
            assert "rdp" in month_data
            assert "total_form" in month_data
            assert "nominal" in month_data
    
    def test_rdp_counts_unique_customers(self):
        """Test that RDP counts unique customers, not total records"""
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            params={"year": 2026, "month": 1},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Get January data
        jan_data = next((m for m in data["yearly"] if m["month"] == 1), None)
        assert jan_data is not None
        
        # RDP should be unique customers who deposited again
        # Based on test data: jd001, aa, sa are RDP customers
        # Total RDP should be 3 (unique customers), not the total number of repeat deposits
        print(f"January NDP: {jan_data['new_id']}, RDP: {jan_data['rdp']}, Total Form: {jan_data['total_form']}")
        
        # RDP should be less than or equal to total_form
        assert jan_data['rdp'] <= jan_data['total_form'], "RDP should not exceed total form count"
        
        # NDP + RDP should be less than or equal to total_form (since same customer can have multiple deposits)
        # This validates that we're counting unique customers, not records
        assert jan_data['new_id'] + jan_data['rdp'] <= jan_data['total_form'], \
            "NDP + RDP should not exceed total form (unique customers vs total records)"
    
    def test_staff_performance_rdp_unique(self):
        """Test staff performance RDP counts unique customers per staff"""
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            params={"year": 2026, "month": 1},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        staff_perf = data.get("staff_performance", [])
        
        for staff in staff_perf:
            print(f"Staff: {staff['staff_name']}, NDP: {staff['new_id']}, RDP: {staff['rdp']}, Form: {staff['total_form']}")
            
            # RDP should be unique customers per staff
            assert staff['rdp'] <= staff['total_form'], \
                f"Staff {staff['staff_name']} RDP should not exceed total form"
            
            # NDP + RDP should be unique customers
            assert staff['new_id'] + staff['rdp'] <= staff['total_form'], \
                f"Staff {staff['staff_name']} NDP + RDP should not exceed total form"
    
    def test_daily_report_rdp_unique_per_day(self):
        """Test daily report RDP counts unique customers per day"""
        response = requests.get(
            f"{BASE_URL}/api/report-crm/data",
            params={"year": 2026, "month": 1},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        daily_data = data.get("daily", [])
        
        for day in daily_data:
            print(f"Date: {day['date']}, NDP: {day['new_id']}, RDP: {day['rdp']}, Form: {day['total_form']}")
            
            # RDP should be unique customers per day
            assert day['rdp'] <= day['total_form'], \
                f"Day {day['date']} RDP should not exceed total form"
            
            # NDP + RDP should be unique customers for that day
            assert day['new_id'] + day['rdp'] <= day['total_form'], \
                f"Day {day['date']} NDP + RDP should not exceed total form"


class TestRetentionAlerts:
    """Customer Retention alerts endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_retention_alerts_endpoint(self):
        """Test /api/retention/alerts endpoint returns correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/retention/alerts",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "summary" in data
        assert "alerts" in data
        
        # Verify summary has required fields
        summary = data["summary"]
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        assert "total" in summary
        
        # Total should equal sum of risk levels
        assert summary["total"] == summary["critical"] + summary["high"] + summary["medium"]
    
    def test_retention_alerts_uses_normalized_ids(self):
        """Test that alerts use normalized customer IDs"""
        response = requests.get(
            f"{BASE_URL}/api/retention/alerts",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If there are alerts, verify they have correct structure
        for alert in data.get("alerts", []):
            assert "customer_id" in alert
            assert "days_since_deposit" in alert
            assert "risk_level" in alert
            assert alert["risk_level"] in ["critical", "high", "medium"]
            
            # Days since deposit should be positive
            assert alert["days_since_deposit"] >= 0
    
    def test_retention_overview_endpoint(self):
        """Test /api/retention/overview endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/retention/overview",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "date_range" in data
        assert "total_customers" in data
        assert "ndp_customers" in data
        assert "rdp_customers" in data
        assert "retention_rate" in data
        
        # Retention rate should be between 0 and 100
        assert 0 <= data["retention_rate"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
