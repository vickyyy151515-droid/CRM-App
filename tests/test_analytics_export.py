"""
Test suite for Advanced Analytics and Export Center features
Tests:
- Analytics endpoints (staff-performance, business)
- Export endpoints (customer-records, omset, staff-report, reserved-members, bonanza-records, memberwd-records)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Get headers with admin auth token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


class TestAnalyticsEndpoints:
    """Test Analytics API endpoints"""
    
    def test_staff_performance_default(self, admin_headers):
        """Test GET /api/analytics/staff-performance with default params"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "period" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "summary" in data
        assert "staff_metrics" in data
        assert "daily_chart" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_records" in summary
        assert "records_in_period" in summary
        assert "whatsapp_ada" in summary
        assert "whatsapp_tidak" in summary
        assert "whatsapp_ceklis1" in summary
        assert "whatsapp_rate" in summary
        assert "respond_ya" in summary
        assert "respond_rate" in summary
        
        print(f"Staff Performance - Total records: {summary['total_records']}, WA Rate: {summary['whatsapp_rate']}%")
    
    def test_staff_performance_period_today(self, admin_headers):
        """Test staff performance with period=today"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance?period=today", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "today"
        print(f"Today's records in period: {data['summary']['records_in_period']}")
    
    def test_staff_performance_period_week(self, admin_headers):
        """Test staff performance with period=week"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance?period=week", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"
        print(f"Week's records in period: {data['summary']['records_in_period']}")
    
    def test_staff_performance_period_quarter(self, admin_headers):
        """Test staff performance with period=quarter"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance?period=quarter", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "quarter"
    
    def test_staff_performance_period_year(self, admin_headers):
        """Test staff performance with period=year"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance?period=year", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "year"
    
    def test_staff_performance_requires_admin(self):
        """Test that staff performance endpoint requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/staff-performance")
        assert response.status_code in [401, 403]
    
    def test_business_analytics_default(self, admin_headers):
        """Test GET /api/analytics/business with default params"""
        response = requests.get(f"{BASE_URL}/api/analytics/business", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "period" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "summary" in data
        assert "omset_chart" in data
        assert "product_omset" in data
        assert "database_utilization" in data
        
        # Verify summary structure
        summary = data["summary"]
        assert "total_omset" in summary
        assert "total_records" in summary
        assert "ndp_count" in summary
        assert "rdp_count" in summary
        assert "ndp_omset" in summary
        assert "rdp_omset" in summary
        
        print(f"Business Analytics - Total OMSET: {summary['total_omset']}, NDP: {summary['ndp_count']}, RDP: {summary['rdp_count']}")
    
    def test_business_analytics_period_month(self, admin_headers):
        """Test business analytics with period=month"""
        response = requests.get(f"{BASE_URL}/api/analytics/business?period=month", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "month"
    
    def test_business_analytics_requires_admin(self):
        """Test that business analytics endpoint requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/business")
        assert response.status_code in [401, 403]
    
    def test_database_utilization_structure(self, admin_headers):
        """Test database utilization data structure"""
        response = requests.get(f"{BASE_URL}/api/analytics/business", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        db_util = data.get("database_utilization", [])
        
        if len(db_util) > 0:
            db = db_util[0]
            assert "database_id" in db
            assert "database_name" in db
            assert "product_name" in db
            assert "total_records" in db
            assert "assigned" in db
            assert "available" in db
            assert "utilization_rate" in db
            print(f"First DB: {db['database_name']} - Utilization: {db['utilization_rate']}%")


class TestExportEndpoints:
    """Test Export API endpoints"""
    
    def test_export_customer_records_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/customer-records with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/customer-records?format=xlsx&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        assert "spreadsheet" in response.headers.get("content-type", "") or response.headers.get("content-type", "").startswith("application/")
        print(f"Customer records export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_customer_records_csv(self, admin_headers, admin_token):
        """Test GET /api/export/customer-records with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/customer-records?format=csv&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Customer records export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_customer_records_requires_admin(self):
        """Test that customer records export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/customer-records")
        assert response.status_code in [401, 403]
    
    def test_export_omset_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/omset with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/omset?format=xlsx&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"OMSET export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_omset_csv(self, admin_headers, admin_token):
        """Test GET /api/export/omset with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/omset?format=csv&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"OMSET export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_omset_requires_admin(self):
        """Test that OMSET export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/omset")
        assert response.status_code in [401, 403]
    
    def test_export_staff_report_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/staff-report with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/staff-report?format=xlsx&period=month&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Staff report export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_staff_report_csv(self, admin_headers, admin_token):
        """Test GET /api/export/staff-report with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/staff-report?format=csv&period=week&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Staff report export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_staff_report_requires_admin(self):
        """Test that staff report export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/staff-report")
        assert response.status_code in [401, 403]
    
    def test_export_reserved_members_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/reserved-members with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/reserved-members?format=xlsx&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Reserved members export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_reserved_members_csv(self, admin_headers, admin_token):
        """Test GET /api/export/reserved-members with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/reserved-members?format=csv&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Reserved members export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_reserved_members_requires_admin(self):
        """Test that reserved members export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/reserved-members")
        assert response.status_code in [401, 403]
    
    def test_export_bonanza_records_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/bonanza-records with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/bonanza-records?format=xlsx&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Bonanza records export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_bonanza_records_csv(self, admin_headers, admin_token):
        """Test GET /api/export/bonanza-records with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/bonanza-records?format=csv&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"Bonanza records export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_bonanza_records_requires_admin(self):
        """Test that bonanza records export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/bonanza-records")
        assert response.status_code in [401, 403]
    
    def test_export_memberwd_records_xlsx(self, admin_headers, admin_token):
        """Test GET /api/export/memberwd-records with xlsx format"""
        response = requests.get(
            f"{BASE_URL}/api/export/memberwd-records?format=xlsx&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"MemberWD records export (xlsx) - Content-Length: {response.headers.get('content-length', 'N/A')}")
    
    def test_export_memberwd_records_csv(self, admin_headers, admin_token):
        """Test GET /api/export/memberwd-records with csv format"""
        response = requests.get(
            f"{BASE_URL}/api/export/memberwd-records?format=csv&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print(f"MemberWD records export (csv) - Content-Type: {response.headers.get('content-type', 'N/A')}")
    
    def test_export_memberwd_records_requires_admin(self):
        """Test that memberwd records export requires admin auth"""
        response = requests.get(f"{BASE_URL}/api/export/memberwd-records")
        assert response.status_code in [401, 403]


class TestExportFilters:
    """Test Export endpoints with various filters"""
    
    def test_export_customer_records_with_status_filter(self, admin_headers, admin_token):
        """Test customer records export with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/export/customer-records?format=csv&status=assigned&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print("Customer records export with status=assigned - OK")
    
    def test_export_omset_with_date_filter(self, admin_headers, admin_token):
        """Test OMSET export with date filters"""
        response = requests.get(
            f"{BASE_URL}/api/export/omset?format=csv&start_date=2024-01-01&end_date=2025-12-31&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print("OMSET export with date filters - OK")
    
    def test_export_reserved_members_with_status_filter(self, admin_headers, admin_token):
        """Test reserved members export with status filter"""
        response = requests.get(
            f"{BASE_URL}/api/export/reserved-members?format=csv&status=approved&token={admin_token}",
            headers=admin_headers
        )
        assert response.status_code == 200
        print("Reserved members export with status=approved - OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
