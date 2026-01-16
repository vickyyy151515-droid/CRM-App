"""
Test At-Risk Customer Enhancement and Toggle Button Functionality
- Tests phone_number field in retention alerts API
- Tests WhatsApp status toggle (Ada/Ceklis1/Tidak)
- Tests Respond status toggle (Ya/Tidak)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRetentionAlerts:
    """Test At-Risk Customer alerts endpoint with phone_number field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@crm.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.admin_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_retention_alerts_returns_phone_number_field(self):
        """Verify /retention/alerts returns phone_number field in response"""
        response = requests.get(f"{BASE_URL}/api/retention/alerts", headers=self.headers)
        assert response.status_code == 200, f"API call failed: {response.text}"
        
        data = response.json()
        assert "summary" in data
        assert "alerts" in data
        
        # Check that alerts have phone_number field
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            assert "phone_number" in alert, "phone_number field missing from alert"
            assert "customer_id" in alert, "customer_id field missing from alert"
            assert "customer_name" in alert, "customer_name field missing from alert"
            print(f"Alert has phone_number: '{alert['phone_number']}' (empty is expected if no matching customer_records)")
    
    def test_retention_alerts_summary_structure(self):
        """Verify summary structure in alerts response"""
        response = requests.get(f"{BASE_URL}/api/retention/alerts", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        assert "total" in summary
        assert summary["total"] == summary["critical"] + summary["high"] + summary["medium"]


class TestWhatsAppStatusToggle:
    """Test WhatsApp status toggle functionality (Ada/Ceklis1/Tidak)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get staff token and find a test record"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.staff_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.staff_token}"}
        
        # Get a batch with records
        batches_response = requests.get(f"{BASE_URL}/api/my-request-batches", headers=self.headers)
        assert batches_response.status_code == 200
        batches = batches_response.json()
        
        # Find a batch with records
        self.test_record_id = None
        for batch in batches:
            if batch.get("record_count", 0) > 0:
                records_response = requests.get(
                    f"{BASE_URL}/api/my-assigned-records-by-batch",
                    params={"request_id": batch["id"]},
                    headers=self.headers
                )
                if records_response.status_code == 200:
                    records = records_response.json()
                    if len(records) > 0:
                        self.test_record_id = records[0]["id"]
                        self.test_batch_id = batch["id"]
                        break
        
        assert self.test_record_id is not None, "No test record found"
    
    def test_whatsapp_status_toggle_on(self):
        """Test setting WhatsApp status to 'ada'"""
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/whatsapp-status",
            json={"whatsapp_status": "ada"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to set status: {response.text}"
        
        # Verify status was set
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record is not None
        assert record["whatsapp_status"] == "ada"
    
    def test_whatsapp_status_toggle_off(self):
        """Test toggling WhatsApp status OFF (set to null)"""
        # First set to 'ada'
        requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/whatsapp-status",
            json={"whatsapp_status": "ada"},
            headers=self.headers
        )
        
        # Then toggle off (set to null)
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/whatsapp-status",
            json={"whatsapp_status": None},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to toggle off: {response.text}"
        
        # Verify status was cleared
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record is not None
        assert record["whatsapp_status"] is None
    
    def test_whatsapp_status_ceklis1(self):
        """Test setting WhatsApp status to 'ceklis1'"""
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/whatsapp-status",
            json={"whatsapp_status": "ceklis1"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record["whatsapp_status"] == "ceklis1"
    
    def test_whatsapp_status_tidak(self):
        """Test setting WhatsApp status to 'tidak'"""
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/whatsapp-status",
            json={"whatsapp_status": "tidak"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record["whatsapp_status"] == "tidak"


class TestRespondStatusToggle:
    """Test Respond status toggle functionality (Ya/Tidak)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get staff token and find a test record"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        assert response.status_code == 200
        self.staff_token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.staff_token}"}
        
        # Get a batch with records
        batches_response = requests.get(f"{BASE_URL}/api/my-request-batches", headers=self.headers)
        batches = batches_response.json()
        
        self.test_record_id = None
        for batch in batches:
            if batch.get("record_count", 0) > 0:
                records_response = requests.get(
                    f"{BASE_URL}/api/my-assigned-records-by-batch",
                    params={"request_id": batch["id"]},
                    headers=self.headers
                )
                if records_response.status_code == 200:
                    records = records_response.json()
                    if len(records) > 0:
                        self.test_record_id = records[0]["id"]
                        self.test_batch_id = batch["id"]
                        break
        
        assert self.test_record_id is not None
    
    def test_respond_status_toggle_on_ya(self):
        """Test setting Respond status to 'ya'"""
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/respond-status",
            json={"respond_status": "ya"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record["respond_status"] == "ya"
    
    def test_respond_status_toggle_off(self):
        """Test toggling Respond status OFF (set to null)"""
        # First set to 'ya'
        requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/respond-status",
            json={"respond_status": "ya"},
            headers=self.headers
        )
        
        # Then toggle off
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/respond-status",
            json={"respond_status": None},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record["respond_status"] is None
    
    def test_respond_status_tidak(self):
        """Test setting Respond status to 'tidak'"""
        response = requests.patch(
            f"{BASE_URL}/api/customer-records/{self.test_record_id}/respond-status",
            json={"respond_status": "tidak"},
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Verify
        records_response = requests.get(
            f"{BASE_URL}/api/my-assigned-records-by-batch",
            params={"request_id": self.test_batch_id},
            headers=self.headers
        )
        records = records_response.json()
        record = next((r for r in records if r["id"] == self.test_record_id), None)
        assert record["respond_status"] == "tidak"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
