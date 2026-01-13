"""
Test suite for Product Selection feature in DB Bonanza and Member WD CRM
Tests: Product selection on upload, product filtering on databases and staff records
"""
import pytest
import requests
import os
import time
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@crm.com"
ADMIN_PASSWORD = "admin123"
STAFF_EMAIL = "staff@crm.com"
STAFF_PASSWORD = "staff123"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "admin", "User is not admin"
        print(f"SUCCESS: Admin login - token received, role={data['user']['role']}")
    
    def test_staff_login(self):
        """Test staff login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": STAFF_EMAIL,
            "password": STAFF_PASSWORD
        })
        assert response.status_code == 200, f"Staff login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert data["user"]["role"] == "staff", "User is not staff"
        print(f"SUCCESS: Staff login - token received, role={data['user']['role']}")


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
def test_product(admin_token):
    """Create a test product for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    unique_name = f"TEST_Product_{int(time.time())}"
    
    response = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
        "name": unique_name
    })
    
    if response.status_code == 200:
        product = response.json()
        yield product
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{product['id']}", headers=headers)
    else:
        pytest.skip(f"Failed to create test product: {response.text}")


class TestProductsEndpoint:
    """Test /api/products endpoint"""
    
    def test_get_products_as_admin(self, admin_token):
        """Admin can get list of products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} products")
        if len(data) > 0:
            assert "id" in data[0], "Product should have id"
            assert "name" in data[0], "Product should have name"
            print(f"  First product: {data[0].get('name', 'N/A')}")
    
    def test_get_products_as_staff(self, staff_token):
        """Staff can also get list of products"""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        assert response.status_code == 200, f"Staff should be able to get products: {response.text}"
        print("SUCCESS: Staff can view products list")
    
    def test_create_product(self, admin_token):
        """Admin can create a new product"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_name = f"TEST_CreateProduct_{int(time.time())}"
        
        response = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
            "name": unique_name
        })
        assert response.status_code == 200, f"Failed to create product: {response.text}"
        data = response.json()
        assert data["name"] == unique_name, "Product name mismatch"
        assert "id" in data, "Product should have id"
        print(f"SUCCESS: Created product '{unique_name}' with id={data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{data['id']}", headers=headers)


class TestBonanzaUploadWithProduct:
    """Test DB Bonanza upload with product selection"""
    
    def test_bonanza_upload_requires_product_id(self, admin_token):
        """Bonanza upload should require product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a simple CSV file
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com\nuser2,789012,user2@test.com"
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {'name': 'TEST_NoProduct'}
        
        response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=headers, files=files, data=data)
        # Should fail because product_id is missing
        assert response.status_code == 422, f"Should require product_id, got: {response.status_code}"
        print("SUCCESS: Bonanza upload requires product_id (422 validation error)")
    
    def test_bonanza_upload_with_invalid_product(self, admin_token):
        """Bonanza upload should fail with invalid product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com"
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {'name': 'TEST_InvalidProduct', 'product_id': 'invalid-product-id'}
        
        response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=headers, files=files, data=data)
        assert response.status_code == 404, f"Should fail with invalid product_id, got: {response.status_code}"
        print("SUCCESS: Bonanza upload fails with invalid product_id (404)")
    
    def test_bonanza_upload_with_valid_product(self, admin_token, test_product):
        """Bonanza upload should succeed with valid product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com\nuser2,789012,user2@test.com"
        files = {'file': ('test_bonanza.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_Bonanza_{int(time.time())}', 'product_id': test_product['id']}
        
        response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=headers, files=files, data=data)
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        result = response.json()
        assert result['product_id'] == test_product['id'], "Product ID mismatch"
        assert result['product_name'] == test_product['name'], "Product name mismatch"
        assert result['total_records'] == 2, "Record count mismatch"
        print(f"SUCCESS: Bonanza upload with product '{test_product['name']}' - {result['total_records']} records")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bonanza/databases/{result['id']}", headers=headers)


class TestMemberWDUploadWithProduct:
    """Test Member WD CRM upload with product selection"""
    
    def test_memberwd_upload_requires_product_id(self, admin_token):
        """MemberWD upload should require product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com"
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {'name': 'TEST_NoProduct'}
        
        response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=headers, files=files, data=data)
        assert response.status_code == 422, f"Should require product_id, got: {response.status_code}"
        print("SUCCESS: MemberWD upload requires product_id (422 validation error)")
    
    def test_memberwd_upload_with_invalid_product(self, admin_token):
        """MemberWD upload should fail with invalid product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com"
        files = {'file': ('test.csv', csv_content, 'text/csv')}
        data = {'name': 'TEST_InvalidProduct', 'product_id': 'invalid-product-id'}
        
        response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=headers, files=files, data=data)
        assert response.status_code == 404, f"Should fail with invalid product_id, got: {response.status_code}"
        print("SUCCESS: MemberWD upload fails with invalid product_id (404)")
    
    def test_memberwd_upload_with_valid_product(self, admin_token, test_product):
        """MemberWD upload should succeed with valid product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone,Email\nuser1,123456,user1@test.com\nuser2,789012,user2@test.com\nuser3,345678,user3@test.com"
        files = {'file': ('test_memberwd.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_MemberWD_{int(time.time())}', 'product_id': test_product['id']}
        
        response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=headers, files=files, data=data)
        assert response.status_code == 200, f"Upload failed: {response.text}"
        
        result = response.json()
        assert result['product_id'] == test_product['id'], "Product ID mismatch"
        assert result['product_name'] == test_product['name'], "Product name mismatch"
        assert result['total_records'] == 3, "Record count mismatch"
        print(f"SUCCESS: MemberWD upload with product '{test_product['name']}' - {result['total_records']} records")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/memberwd/databases/{result['id']}", headers=headers)


class TestBonanzaDatabaseFiltering:
    """Test DB Bonanza database filtering by product"""
    
    def test_bonanza_databases_filter_by_product(self, admin_token, test_product):
        """Admin can filter Bonanza databases by product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First upload a database with the test product
        csv_content = "Username,Phone\nfilteruser1,111\nfilteruser2,222"
        files = {'file': ('filter_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_FilterBonanza_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Now filter by product_id
        response = requests.get(f"{BASE_URL}/api/bonanza/databases?product_id={test_product['id']}", headers=headers)
        assert response.status_code == 200, f"Filter failed: {response.text}"
        
        databases = response.json()
        assert isinstance(databases, list), "Response should be a list"
        
        # All returned databases should have the correct product_id
        for db in databases:
            assert db['product_id'] == test_product['id'], f"Database {db['id']} has wrong product_id"
        
        # Our uploaded database should be in the list
        found = any(db['id'] == uploaded_db['id'] for db in databases)
        assert found, "Uploaded database not found in filtered results"
        print(f"SUCCESS: Bonanza databases filtered by product - {len(databases)} databases found")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bonanza/databases/{uploaded_db['id']}", headers=headers)
    
    def test_bonanza_databases_no_filter_returns_all(self, admin_token):
        """Without product_id filter, all databases are returned"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=headers)
        assert response.status_code == 200, f"Failed to get databases: {response.text}"
        
        databases = response.json()
        assert isinstance(databases, list), "Response should be a list"
        print(f"SUCCESS: Bonanza databases without filter - {len(databases)} databases returned")


class TestMemberWDDatabaseFiltering:
    """Test Member WD CRM database filtering by product"""
    
    def test_memberwd_databases_filter_by_product(self, admin_token, test_product):
        """Admin can filter MemberWD databases by product_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First upload a database with the test product
        csv_content = "Username,Phone\nfilteruser1,111\nfilteruser2,222"
        files = {'file': ('filter_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_FilterMemberWD_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Now filter by product_id
        response = requests.get(f"{BASE_URL}/api/memberwd/databases?product_id={test_product['id']}", headers=headers)
        assert response.status_code == 200, f"Filter failed: {response.text}"
        
        databases = response.json()
        assert isinstance(databases, list), "Response should be a list"
        
        # All returned databases should have the correct product_id
        for db in databases:
            assert db['product_id'] == test_product['id'], f"Database {db['id']} has wrong product_id"
        
        # Our uploaded database should be in the list
        found = any(db['id'] == uploaded_db['id'] for db in databases)
        assert found, "Uploaded database not found in filtered results"
        print(f"SUCCESS: MemberWD databases filtered by product - {len(databases)} databases found")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/memberwd/databases/{uploaded_db['id']}", headers=headers)


class TestStaffBonanzaRecordsFiltering:
    """Test Staff Bonanza records filtering by product"""
    
    def test_staff_bonanza_records_filter_by_product(self, admin_token, staff_token, staff_user_id, test_product):
        """Staff can filter their Bonanza records by product_id"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Upload a database with the test product
        csv_content = "Username,Phone\nstaffuser1,111\nstaffuser2,222"
        files = {'file': ('staff_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_StaffBonanza_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=admin_headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Get records from the database
        records_response = requests.get(f"{BASE_URL}/api/bonanza/databases/{uploaded_db['id']}/records", headers=admin_headers)
        assert records_response.status_code == 200, f"Failed to get records: {records_response.text}"
        records = records_response.json()
        
        if len(records) > 0:
            # Assign first record to staff
            record_ids = [records[0]['id']]
            assign_response = requests.post(f"{BASE_URL}/api/bonanza/assign", headers=admin_headers, json={
                "record_ids": record_ids,
                "staff_id": staff_user_id
            })
            assert assign_response.status_code == 200, f"Assignment failed: {assign_response.text}"
            
            # Staff filters their records by product
            filter_response = requests.get(f"{BASE_URL}/api/bonanza/staff/records?product_id={test_product['id']}", headers=staff_headers)
            assert filter_response.status_code == 200, f"Filter failed: {filter_response.text}"
            
            staff_records = filter_response.json()
            assert isinstance(staff_records, list), "Response should be a list"
            
            # All returned records should have the correct product_id
            for record in staff_records:
                assert record['product_id'] == test_product['id'], f"Record has wrong product_id"
            
            print(f"SUCCESS: Staff Bonanza records filtered by product - {len(staff_records)} records found")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bonanza/databases/{uploaded_db['id']}", headers=admin_headers)


class TestStaffMemberWDRecordsFiltering:
    """Test Staff MemberWD records filtering by product"""
    
    def test_staff_memberwd_records_filter_by_product(self, admin_token, staff_token, staff_user_id, test_product):
        """Staff can filter their MemberWD records by product_id"""
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Upload a database with the test product
        csv_content = "Username,Phone\nstaffuser1,111\nstaffuser2,222"
        files = {'file': ('staff_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_StaffMemberWD_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=admin_headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Get records from the database
        records_response = requests.get(f"{BASE_URL}/api/memberwd/databases/{uploaded_db['id']}/records", headers=admin_headers)
        assert records_response.status_code == 200, f"Failed to get records: {records_response.text}"
        records = records_response.json()
        
        if len(records) > 0:
            # Assign first record to staff
            record_ids = [records[0]['id']]
            assign_response = requests.post(f"{BASE_URL}/api/memberwd/assign", headers=admin_headers, json={
                "record_ids": record_ids,
                "staff_id": staff_user_id
            })
            assert assign_response.status_code == 200, f"Assignment failed: {assign_response.text}"
            
            # Staff filters their records by product
            filter_response = requests.get(f"{BASE_URL}/api/memberwd/staff/records?product_id={test_product['id']}", headers=staff_headers)
            assert filter_response.status_code == 200, f"Filter failed: {filter_response.text}"
            
            staff_records = filter_response.json()
            assert isinstance(staff_records, list), "Response should be a list"
            
            # All returned records should have the correct product_id
            for record in staff_records:
                assert record['product_id'] == test_product['id'], f"Record has wrong product_id"
            
            print(f"SUCCESS: Staff MemberWD records filtered by product - {len(staff_records)} records found")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/memberwd/databases/{uploaded_db['id']}", headers=admin_headers)


class TestProductNameInRecords:
    """Test that product_name is correctly stored in records"""
    
    def test_bonanza_records_have_product_name(self, admin_token, test_product):
        """Bonanza records should have product_name field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone\nproductuser1,111"
        files = {'file': ('product_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_ProductName_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/bonanza/upload", headers=headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Get records
        records_response = requests.get(f"{BASE_URL}/api/bonanza/databases/{uploaded_db['id']}/records", headers=headers)
        assert records_response.status_code == 200, f"Failed to get records: {records_response.text}"
        records = records_response.json()
        
        assert len(records) > 0, "No records found"
        for record in records:
            assert 'product_id' in record, "Record should have product_id"
            assert 'product_name' in record, "Record should have product_name"
            assert record['product_id'] == test_product['id'], "Product ID mismatch"
            assert record['product_name'] == test_product['name'], "Product name mismatch"
        
        print(f"SUCCESS: Bonanza records have correct product_name: {test_product['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/bonanza/databases/{uploaded_db['id']}", headers=headers)
    
    def test_memberwd_records_have_product_name(self, admin_token, test_product):
        """MemberWD records should have product_name field"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        csv_content = "Username,Phone\nproductuser1,111"
        files = {'file': ('product_test.csv', csv_content, 'text/csv')}
        data = {'name': f'TEST_ProductName_{int(time.time())}', 'product_id': test_product['id']}
        
        upload_response = requests.post(f"{BASE_URL}/api/memberwd/upload", headers=headers, files=files, data=data)
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        uploaded_db = upload_response.json()
        
        # Get records
        records_response = requests.get(f"{BASE_URL}/api/memberwd/databases/{uploaded_db['id']}/records", headers=headers)
        assert records_response.status_code == 200, f"Failed to get records: {records_response.text}"
        records = records_response.json()
        
        assert len(records) > 0, "No records found"
        for record in records:
            assert 'product_id' in record, "Record should have product_id"
            assert 'product_name' in record, "Record should have product_name"
            assert record['product_id'] == test_product['id'], "Product ID mismatch"
            assert record['product_name'] == test_product['name'], "Product name mismatch"
        
        print(f"SUCCESS: MemberWD records have correct product_name: {test_product['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/memberwd/databases/{uploaded_db['id']}", headers=headers)


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_products(self, admin_token):
        """Clean up all TEST_ prefixed products"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        products = response.json()
        
        deleted_count = 0
        for product in products:
            if product["name"].startswith("TEST_"):
                del_response = requests.delete(f"{BASE_URL}/api/products/{product['id']}", headers=headers)
                if del_response.status_code == 200:
                    deleted_count += 1
        
        print(f"SUCCESS: Cleaned up {deleted_count} test products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
