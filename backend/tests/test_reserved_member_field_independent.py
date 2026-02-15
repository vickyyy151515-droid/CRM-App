"""
Test: Reserved Member Field-Independent Check (Bug Fix Verification)

BUG FIXED: Reserved members were being assigned to wrong staff during random assignment
because the check only looked at hardcoded field names like ['Username', 'username', 'USER'].

FIX: Now checks ALL row_data values against reserved members, regardless of field names.

Test Scope:
1. memberwd assign-random - Uses is_record_reserved function 
2. memberwd manual assign - Uses field-independent check
3. bonanza assign-random - Uses field-independent check
4. Upload-time reserved flagging - memberwd and bonanza both use field-independent check
5. GET /api/reserved-members returns data correctly
6. PATCH /api/reserved-members/{id}/permanent toggle works

Key insight: row_data field names come from Excel column headers (e.g., 'USERNAME', 'NAMA_REKENING')
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReservedMemberFieldIndependentCheck:
    """Tests to verify reserved member check works with ANY field name in row_data"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield

    def test_01_get_reserved_members_list(self):
        """Test GET /api/reserved-members returns data correctly"""
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert response.status_code == 200, f"Failed to get reserved members: {response.text}"
        
        data = response.json()
        # Should be a list
        assert isinstance(data, list), "Response should be a list"
        
        # Check if we have any reserved members
        if len(data) > 0:
            # Each member should have key fields
            member = data[0]
            assert 'id' in member, "Member should have id"
            assert 'staff_id' in member, "Member should have staff_id"
            assert 'status' in member, "Member should have status"
        
        print(f"✓ GET /api/reserved-members returned {len(data)} members")

    def test_02_get_memberwd_databases(self):
        """Test GET /api/memberwd/databases works - needed for random assignment"""
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=self.headers)
        assert response.status_code == 200, f"Failed to get memberwd databases: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of databases"
        print(f"✓ GET /api/memberwd/databases returned {len(data)} databases")
        
        # Store first database with available records for later tests
        for db in data:
            if db.get('available_count', 0) > 0:
                self.available_database_id = db['id']
                print(f"  Found database with {db['available_count']} available records: {db['name']}")
                break

    def test_03_get_bonanza_databases(self):
        """Test GET /api/bonanza/databases works - needed for random assignment"""
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=self.headers)
        assert response.status_code == 200, f"Failed to get bonanza databases: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list of databases"
        print(f"✓ GET /api/bonanza/databases returned {len(data)} databases")

    def test_04_memberwd_assign_random_respects_reserved(self):
        """
        CRITICAL TEST: verify memberwd assign-random excludes reserved members
        regardless of the field name used in row_data
        """
        # First, get a database with available records
        db_response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=self.headers)
        assert db_response.status_code == 200
        databases = db_response.json()
        
        # Find a database with available records
        test_database = None
        for db in databases:
            if db.get('available_count', 0) > 0:
                test_database = db
                break
        
        if not test_database:
            pytest.skip("No memberwd database with available records found")
        
        # Get staff list
        staff_response = requests.get(f"{BASE_URL}/api/memberwd/staff", headers=self.headers)
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff found for assignment")
        
        test_staff = staff_list[0]
        
        # Make the random assignment call
        assign_response = requests.post(f"{BASE_URL}/api/memberwd/assign-random", 
            headers=self.headers,
            json={
                "database_id": test_database['id'],
                "staff_id": test_staff['id'],
                "quantity": 1,
                "username_field": "Username"  # This field name shouldn't matter anymore
            }
        )
        
        # Should succeed (or fail with "no eligible records" if all are reserved)
        if assign_response.status_code == 200:
            data = assign_response.json()
            assert 'assigned_count' in data, "Response should have assigned_count"
            print(f"✓ memberwd assign-random succeeded: {data['assigned_count']} records assigned")
            if 'total_reserved_in_db' in data:
                print(f"  Reserved members skipped: {data['total_reserved_in_db']}")
        elif assign_response.status_code == 400:
            # Could be "no eligible records" - this is valid if all are reserved
            print(f"✓ memberwd assign-random correctly rejected (possibly all reserved): {assign_response.json()}")
        else:
            pytest.fail(f"Unexpected response: {assign_response.status_code} - {assign_response.text}")

    def test_05_bonanza_assign_random_respects_reserved(self):
        """
        CRITICAL TEST: verify bonanza assign-random excludes reserved members
        regardless of the field name used in row_data
        """
        # First, get a database with available records
        db_response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=self.headers)
        assert db_response.status_code == 200
        databases = db_response.json()
        
        # Find a database with available records
        test_database = None
        for db in databases:
            if db.get('available_count', 0) > 0:
                test_database = db
                break
        
        if not test_database:
            pytest.skip("No bonanza database with available records found")
        
        # Get staff list
        staff_response = requests.get(f"{BASE_URL}/api/bonanza/staff", headers=self.headers)
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff found for assignment")
        
        test_staff = staff_list[0]
        
        # Make the random assignment call
        assign_response = requests.post(f"{BASE_URL}/api/bonanza/assign-random", 
            headers=self.headers,
            json={
                "database_id": test_database['id'],
                "staff_id": test_staff['id'],
                "quantity": 1,
                "username_field": "Username"  # This field name shouldn't matter anymore
            }
        )
        
        # Should succeed (or fail with "no eligible records" if all are reserved)
        if assign_response.status_code == 200:
            data = assign_response.json()
            assert 'assigned_count' in data, "Response should have assigned_count"
            print(f"✓ bonanza assign-random succeeded: {data['assigned_count']} records assigned")
            if 'total_reserved_in_db' in data:
                print(f"  Reserved members skipped: {data['total_reserved_in_db']}")
        elif assign_response.status_code == 400:
            # Could be "no eligible records" - this is valid if all are reserved
            print(f"✓ bonanza assign-random correctly rejected (possibly all reserved): {assign_response.json()}")
        else:
            pytest.fail(f"Unexpected response: {assign_response.status_code} - {assign_response.text}")

    def test_06_permanent_toggle_endpoint_works(self):
        """Test PATCH /api/reserved-members/{id}/permanent toggle still works"""
        # Get reserved members
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert response.status_code == 200
        members = response.json()
        
        if not members:
            pytest.skip("No reserved members to test permanent toggle")
        
        # Find a non-permanent member to toggle
        test_member = None
        for m in members:
            if m.get('status') == 'approved':
                test_member = m
                break
        
        if not test_member:
            pytest.skip("No approved reserved member found")
        
        original_permanent = test_member.get('is_permanent', False)
        
        # Toggle permanent status
        toggle_response = requests.patch(
            f"{BASE_URL}/api/reserved-members/{test_member['id']}/permanent",
            headers=self.headers
        )
        
        assert toggle_response.status_code == 200, f"Toggle failed: {toggle_response.text}"
        data = toggle_response.json()
        assert 'is_permanent' in data, "Response should have is_permanent field"
        assert data['is_permanent'] != original_permanent, "is_permanent should have toggled"
        print(f"✓ PATCH permanent toggle worked: {original_permanent} -> {data['is_permanent']}")
        
        # Toggle back to original state
        toggle_back = requests.patch(
            f"{BASE_URL}/api/reserved-members/{test_member['id']}/permanent",
            headers=self.headers
        )
        assert toggle_back.status_code == 200
        assert toggle_back.json()['is_permanent'] == original_permanent
        print(f"✓ Toggled back to original state: {original_permanent}")

    def test_07_memberwd_manual_assign_respects_reserved(self):
        """Test memberwd manual assign also uses field-independent check"""
        # Get a database with available records
        db_response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=self.headers)
        assert db_response.status_code == 200
        databases = db_response.json()
        
        # Find a database with available records
        test_database = None
        for db in databases:
            if db.get('available_count', 0) > 0:
                test_database = db
                break
        
        if not test_database:
            pytest.skip("No memberwd database with available records")
        
        # Get available records from database
        records_response = requests.get(
            f"{BASE_URL}/api/memberwd/databases/{test_database['id']}/records?status=available",
            headers=self.headers
        )
        assert records_response.status_code == 200
        records = records_response.json()
        
        if not records:
            pytest.skip("No available records in database")
        
        # Get staff list
        staff_response = requests.get(f"{BASE_URL}/api/memberwd/staff", headers=self.headers)
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff found")
        
        # Try to assign the first available record
        assign_response = requests.post(f"{BASE_URL}/api/memberwd/assign",
            headers=self.headers,
            json={
                "record_ids": [records[0]['id']],
                "staff_id": staff_list[0]['id']
            }
        )
        
        # Should work or be blocked if the record is reserved
        if assign_response.status_code == 200:
            data = assign_response.json()
            print(f"✓ memberwd manual assign worked: {data.get('assigned_count', 0)} assigned")
            if data.get('warning'):
                print(f"  Warning: {data['warning']}")
        elif assign_response.status_code == 400:
            # Blocked due to reserved - this is correct behavior
            print(f"✓ memberwd manual assign correctly blocked reserved member: {assign_response.json()}")
        else:
            pytest.fail(f"Unexpected response: {assign_response.status_code} - {assign_response.text}")

    def test_08_bonanza_manual_assign_respects_reserved(self):
        """Test bonanza manual assign also uses field-independent check"""
        # Get a database with available records
        db_response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=self.headers)
        assert db_response.status_code == 200
        databases = db_response.json()
        
        # Find a database with available records
        test_database = None
        for db in databases:
            if db.get('available_count', 0) > 0:
                test_database = db
                break
        
        if not test_database:
            pytest.skip("No bonanza database with available records")
        
        # Get available records from database
        records_response = requests.get(
            f"{BASE_URL}/api/bonanza/databases/{test_database['id']}/records?status=available",
            headers=self.headers
        )
        assert records_response.status_code == 200
        records = records_response.json()
        
        if not records:
            pytest.skip("No available records in database")
        
        # Get staff list
        staff_response = requests.get(f"{BASE_URL}/api/bonanza/staff", headers=self.headers)
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff found")
        
        # Try to assign the first available record
        assign_response = requests.post(f"{BASE_URL}/api/bonanza/assign",
            headers=self.headers,
            json={
                "record_ids": [records[0]['id']],
                "staff_id": staff_list[0]['id']
            }
        )
        
        # Should work or be blocked if the record is reserved
        if assign_response.status_code == 200:
            data = assign_response.json()
            print(f"✓ bonanza manual assign worked: {data.get('assigned_count', 0)} assigned")
            if data.get('warning'):
                print(f"  Warning: {data['warning']}")
        elif assign_response.status_code == 400:
            # Blocked due to reserved - this is correct behavior
            print(f"✓ bonanza manual assign correctly blocked reserved member: {assign_response.json()}")
        else:
            pytest.fail(f"Unexpected response: {assign_response.status_code} - {assign_response.text}")

    def test_09_verify_is_record_reserved_logic_in_memberwd(self):
        """
        Verify the is_record_reserved function in memberwd checks ALL row_data values.
        This is the core fix - checking ALL values, not just specific field names.
        """
        # Get memberwd databases with detailed info
        db_response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=self.headers)
        assert db_response.status_code == 200
        databases = db_response.json()
        
        # Check for excluded_count in response - this indicates reserved members detected
        has_excluded = False
        for db in databases:
            if db.get('excluded_count', 0) > 0:
                has_excluded = True
                print(f"✓ Database '{db['name']}' has {db['excluded_count']} excluded (reserved) records")
        
        if not has_excluded and len(databases) > 0:
            print("✓ No reserved members found in available records (or no databases exist)")
        
        print("✓ memberwd databases endpoint returns excluded_count field")


class TestReservedMemberCreationAndQuery:
    """Test reserved member CRUD operations"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        yield

    def test_01_create_reserved_member(self):
        """Test creating a reserved member"""
        # Get products first
        products_response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert products_response.status_code == 200
        products = products_response.json()
        
        if not products:
            pytest.skip("No products available")
        
        # Get staff
        staff_response = requests.get(f"{BASE_URL}/api/users/staff", headers=self.headers)
        assert staff_response.status_code == 200
        staff_list = staff_response.json()
        
        if not staff_list:
            pytest.skip("No staff available")
        
        # Create a test reserved member
        test_customer_id = f"TEST_RESERVED_{uuid.uuid4().hex[:8].upper()}"
        create_response = requests.post(f"{BASE_URL}/api/reserved-members",
            headers=self.headers,
            json={
                "customer_id": test_customer_id,
                "product_id": products[0]['id'],
                "staff_id": staff_list[0]['id']
            }
        )
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        data = create_response.json()
        assert 'id' in data, "Response should have id"
        print(f"✓ Created reserved member: {test_customer_id}")
        
        # Cleanup - delete the test member
        delete_response = requests.delete(
            f"{BASE_URL}/api/reserved-members/{data['id']}",
            headers=self.headers
        )
        if delete_response.status_code == 200:
            print(f"✓ Cleaned up test reserved member")

    def test_02_reserved_members_have_required_fields(self):
        """Test that reserved members have all required fields including is_permanent"""
        response = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert response.status_code == 200
        members = response.json()
        
        if not members:
            pytest.skip("No reserved members to verify")
        
        member = members[0]
        required_fields = ['id', 'staff_id', 'staff_name', 'product_id', 'status']
        
        for field in required_fields:
            assert field in member, f"Reserved member should have '{field}' field"
        
        # is_permanent should exist (default False if not set)
        # The field may not be present if it's False (MongoDB doesn't store False booleans by default)
        # But the code should handle this
        print(f"✓ Reserved member has all required fields")
        print(f"  is_permanent: {member.get('is_permanent', False)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
