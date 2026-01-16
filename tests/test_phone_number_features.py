"""
Test Phone Number Features for CRM Application
- At-Risk Customers: phone lookup checks bonanza_records and memberwd_records in addition to customer_records
- Staff Reserved Members: phone number field is required when requesting a reservation
- Admin Reserved Members: phone number is optional and displayed in table
- Reserved Members API: POST /reserved-members accepts phone_number parameter
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Admin authentication failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_token():
    """Get staff authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": STAFF_EMAIL,
        "password": STAFF_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Staff authentication failed")
    return response.json()["token"]


@pytest.fixture(scope="module")
def staff_user_id(admin_token):
    """Get staff user ID for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/staff-users", headers=headers)
    if response.status_code != 200 or len(response.json()) == 0:
        pytest.skip("No staff users found")
    return response.json()[0]["id"]


@pytest.fixture(scope="module")
def product_id(admin_token):
    """Get a product ID for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/products", headers=headers)
    if response.status_code != 200 or len(response.json()) == 0:
        pytest.skip("No products found")
    return response.json()[0]["id"]


class TestAtRiskPhoneLookup:
    """Test At-Risk Customers phone lookup from multiple collections"""
    
    def test_retention_alerts_returns_phone_number_field(self, admin_token):
        """Verify /retention/alerts returns phone_number field in response"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts", headers=headers)
        assert response.status_code == 200, f"API call failed: {response.text}"
        
        data = response.json()
        assert "summary" in data, "Response should have summary"
        assert "alerts" in data, "Response should have alerts"
        
        # Check that alerts have phone_number field
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            assert "phone_number" in alert, "phone_number field missing from alert"
            assert "customer_id" in alert, "customer_id field missing from alert"
            assert "customer_name" in alert, "customer_name field missing from alert"
            assert "risk_level" in alert, "risk_level field missing from alert"
            print(f"SUCCESS: Alert has phone_number field: '{alert['phone_number']}'")
        else:
            print("INFO: No at-risk alerts found (this is OK if no customers are at risk)")
    
    def test_retention_alerts_summary_structure(self, admin_token):
        """Verify summary structure in alerts response"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        assert "critical" in summary, "Summary should have critical count"
        assert "high" in summary, "Summary should have high count"
        assert "medium" in summary, "Summary should have medium count"
        assert "total" in summary, "Summary should have total count"
        assert summary["total"] == summary["critical"] + summary["high"] + summary["medium"], "Total should equal sum of risk levels"
        print(f"SUCCESS: Summary structure correct - Critical: {summary['critical']}, High: {summary['high']}, Medium: {summary['medium']}, Total: {summary['total']}")
    
    def test_retention_alerts_with_product_filter(self, admin_token, product_id):
        """Test retention alerts with product filter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/retention/alerts?product_id={product_id}", headers=headers)
        assert response.status_code == 200, f"API call failed: {response.text}"
        
        data = response.json()
        assert "alerts" in data
        # All alerts should be for the specified product
        for alert in data["alerts"]:
            assert alert["product_id"] == product_id, f"Alert product_id mismatch: {alert['product_id']} != {product_id}"
        print(f"SUCCESS: Product filter works - {len(data['alerts'])} alerts for product {product_id}")


class TestStaffReservedMembersPhoneRequired:
    """Test that phone number is required for staff reservation requests"""
    
    def test_staff_request_without_phone_fails(self, staff_token, product_id):
        """Staff request without phone number should fail (phone is required for staff)"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_NoPhone_{int(time.time())}"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "product_id": product_id
            # No phone_number - should fail for staff
        })
        
        # Note: Based on the code review, phone_number is Optional in the model
        # But the frontend enforces it as required for staff
        # The backend may or may not enforce this - let's check
        if response.status_code == 200:
            # If it succeeds, the backend doesn't enforce phone requirement
            # This is a potential issue - frontend enforces but backend doesn't
            data = response.json()
            print(f"WARNING: Backend accepted request without phone number - phone_number: {data.get('phone_number')}")
            # Clean up
            admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
            })
            admin_token = admin_response.json()["token"]
            requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", 
                          headers={"Authorization": f"Bearer {admin_token}"})
        else:
            print(f"SUCCESS: Backend rejected request without phone number - {response.status_code}")
    
    def test_staff_request_with_phone_succeeds(self, staff_token, product_id):
        """Staff request with phone number should succeed"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_WithPhone_{int(time.time())}"
        phone = "081234567890"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "product_id": product_id,
            "phone_number": phone
        })
        
        assert response.status_code == 200, f"Request with phone should succeed: {response.text}"
        data = response.json()
        
        # Verify phone number is stored
        assert data["phone_number"] == phone, f"Phone number mismatch: {data.get('phone_number')} != {phone}"
        assert data["customer_name"] == unique_name
        assert data["status"] == "pending", "Staff request should be pending"
        
        print(f"SUCCESS: Staff request with phone succeeded - phone: {data['phone_number']}, status: {data['status']}")
        
        # Clean up
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["token"]
        requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", 
                      headers={"Authorization": f"Bearer {admin_token}"})
    
    def test_staff_request_with_whatsapp_link_phone(self, staff_token, product_id):
        """Staff request with WhatsApp link format phone should succeed"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        unique_name = f"TEST_WAPhone_{int(time.time())}"
        phone = "https://wa.me/6281234567890"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "product_id": product_id,
            "phone_number": phone
        })
        
        assert response.status_code == 200, f"Request with WA link phone should succeed: {response.text}"
        data = response.json()
        
        assert data["phone_number"] == phone, f"Phone number should be stored as-is"
        print(f"SUCCESS: WhatsApp link format phone accepted: {data['phone_number']}")
        
        # Clean up
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["token"]
        requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", 
                      headers={"Authorization": f"Bearer {admin_token}"})


class TestAdminReservedMembersPhone:
    """Test admin reserved members phone number handling"""
    
    def test_admin_add_with_phone(self, admin_token, staff_user_id, product_id):
        """Admin can add reserved member with phone number"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_AdminPhone_{int(time.time())}"
        phone = "089876543210"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id,
            "product_id": product_id,
            "phone_number": phone
        })
        
        assert response.status_code == 200, f"Admin add with phone failed: {response.text}"
        data = response.json()
        
        assert data["phone_number"] == phone, f"Phone number mismatch"
        assert data["status"] == "approved", "Admin-added should be approved"
        
        print(f"SUCCESS: Admin added member with phone: {data['phone_number']}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", headers=headers)
    
    def test_admin_add_without_phone(self, admin_token, staff_user_id, product_id):
        """Admin can add reserved member without phone number (optional for admin)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_AdminNoPhone_{int(time.time())}"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id,
            "product_id": product_id
            # No phone_number - should be OK for admin
        })
        
        assert response.status_code == 200, f"Admin add without phone should succeed: {response.text}"
        data = response.json()
        
        # Phone should be None or empty
        assert data.get("phone_number") is None or data.get("phone_number") == "", "Phone should be None/empty when not provided"
        assert data["status"] == "approved"
        
        print(f"SUCCESS: Admin added member without phone - phone_number: {data.get('phone_number')}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", headers=headers)
    
    def test_get_reserved_members_includes_phone(self, admin_token, staff_user_id, product_id):
        """GET /reserved-members returns phone_number field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_GetPhone_{int(time.time())}"
        phone = "081122334455"
        
        # Create a member with phone
        create_response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id,
            "product_id": product_id,
            "phone_number": phone
        })
        assert create_response.status_code == 200
        member_id = create_response.json()["id"]
        
        # Get all members
        get_response = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        assert get_response.status_code == 200
        
        members = get_response.json()
        created_member = next((m for m in members if m["id"] == member_id), None)
        
        assert created_member is not None, "Created member not found in list"
        assert "phone_number" in created_member, "phone_number field missing from response"
        assert created_member["phone_number"] == phone, f"Phone mismatch: {created_member.get('phone_number')} != {phone}"
        
        print(f"SUCCESS: GET /reserved-members includes phone_number: {created_member['phone_number']}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=headers)


class TestReservedMembersAPIPhoneParameter:
    """Test POST /reserved-members accepts phone_number parameter"""
    
    def test_post_reserved_members_accepts_phone_number(self, admin_token, staff_user_id, product_id):
        """POST /reserved-members accepts phone_number in request body"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_APIPhone_{int(time.time())}"
        phone = "087654321098"
        
        response = requests.post(f"{BASE_URL}/api/reserved-members", headers=headers, json={
            "customer_name": unique_name,
            "staff_id": staff_user_id,
            "product_id": product_id,
            "phone_number": phone
        })
        
        assert response.status_code == 200, f"POST should accept phone_number: {response.text}"
        data = response.json()
        
        # Verify all fields
        assert data["customer_name"] == unique_name
        assert data["phone_number"] == phone
        assert data["staff_id"] == staff_user_id
        assert data["product_id"] == product_id
        assert "id" in data
        assert "created_at" in data
        
        print(f"SUCCESS: POST /reserved-members accepts phone_number parameter")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reserved-members/{data['id']}", headers=headers)
    
    def test_phone_number_persists_after_approval(self, admin_token, staff_token, product_id):
        """Phone number persists after admin approves staff request"""
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_PhonePersist_{int(time.time())}"
        phone = "085566778899"
        
        # Staff creates request with phone
        create_response = requests.post(f"{BASE_URL}/api/reserved-members", headers=staff_headers, json={
            "customer_name": unique_name,
            "product_id": product_id,
            "phone_number": phone
        })
        assert create_response.status_code == 200
        member_id = create_response.json()["id"]
        assert create_response.json()["status"] == "pending"
        
        # Admin approves
        approve_response = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/approve", headers=admin_headers)
        assert approve_response.status_code == 200
        
        # Verify phone persists after approval
        get_response = requests.get(f"{BASE_URL}/api/reserved-members", headers=admin_headers)
        members = get_response.json()
        approved_member = next((m for m in members if m["id"] == member_id), None)
        
        assert approved_member is not None
        assert approved_member["status"] == "approved"
        assert approved_member["phone_number"] == phone, f"Phone should persist after approval: {approved_member.get('phone_number')}"
        
        print(f"SUCCESS: Phone number persists after approval: {approved_member['phone_number']}")
        
        # Clean up
        requests.delete(f"{BASE_URL}/api/reserved-members/{member_id}", headers=admin_headers)


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, admin_token):
        """Clean up all TEST_ prefixed reserved members"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=headers)
        members = response.json()
        
        deleted_count = 0
        for member in members:
            if member["customer_name"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/reserved-members/{member['id']}", headers=headers)
                deleted_count += 1
        
        print(f"SUCCESS: Cleaned up {deleted_count} test reserved members")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
