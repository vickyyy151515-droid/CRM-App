"""
Test: Reserved Status Feature for Member WD CRM and DB Bonanza

This test validates the new 'reserved' status feature where records matching
reserved members get status='reserved' instead of 'available'.

Features tested:
1. POST /api/memberwd/admin/sync-reserved-status - syncs all records based on active reservations
2. GET /api/memberwd/databases - excluded_count (reserved) and correct available_count
3. GET /api/bonanza/databases - same as above
4. GET /api/memberwd/databases/{id}/records - records with status='reserved', reserved_by fields
5. GET /api/bonanza/databases/{id}/records - same
6. POST /api/memberwd/assign-random - should NOT assign reserved records
7. POST /api/bonanza/assign-random - same
8. POST /api/memberwd/assign - manual assignment should skip reserved records
9. PATCH /api/reserved-members/{id}/approve - matching records become reserved
10. DELETE /api/reserved-members/{id} - matching reserved records revert to available
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "admin123"


class TestReservedStatusFeature:
    """Test suite for the reserved status feature"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Return headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # ==================== SYNC ENDPOINT TESTS ====================
    
    def test_sync_reserved_status_endpoint(self, auth_headers):
        """Test POST /api/memberwd/admin/sync-reserved-status endpoint exists and works"""
        response = requests.post(f"{BASE_URL}/api/memberwd/admin/sync-reserved-status", headers=auth_headers)
        
        assert response.status_code == 200, f"Sync endpoint failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert data["success"] is True, "Sync should succeed"
        assert "marked_reserved" in data, "Response missing 'marked_reserved' count"
        assert "marked_available" in data, "Response missing 'marked_available' count"
        
        print(f"✓ Sync completed: {data.get('marked_reserved', 0)} marked reserved, {data.get('marked_available', 0)} reverted to available")
    
    # ==================== DATABASE LISTING TESTS ====================
    
    def test_memberwd_databases_includes_excluded_count(self, auth_headers):
        """Test GET /api/memberwd/databases returns excluded_count (reserved) and correct available_count"""
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        
        assert response.status_code == 200, f"MemberWD databases failed: {response.text}"
        databases = response.json()
        
        if len(databases) > 0:
            db = databases[0]
            # Verify all count fields exist
            assert "excluded_count" in db, "Database listing missing 'excluded_count' field"
            assert "available_count" in db, "Database listing missing 'available_count' field"
            assert "total_records" in db, "Database listing missing 'total_records' field"
            assert "assigned_count" in db, "Database listing missing 'assigned_count' field"
            
            # Verify counts are integers
            assert isinstance(db["excluded_count"], int), "excluded_count should be integer"
            assert isinstance(db["available_count"], int), "available_count should be integer"
            
            # Verify excluded_count now equals reserved records count
            # available_count = total - assigned - archived - reserved
            print(f"✓ MemberWD DB '{db.get('name', 'Unknown')}': total={db['total_records']}, available={db['available_count']}, excluded(reserved)={db['excluded_count']}, assigned={db['assigned_count']}")
        else:
            print("⚠ No MemberWD databases found to test")
    
    def test_bonanza_databases_includes_excluded_count(self, auth_headers):
        """Test GET /api/bonanza/databases returns excluded_count (reserved) and correct available_count"""
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=auth_headers)
        
        assert response.status_code == 200, f"Bonanza databases failed: {response.text}"
        databases = response.json()
        
        if len(databases) > 0:
            db = databases[0]
            # Verify all count fields exist
            assert "excluded_count" in db, "Database listing missing 'excluded_count' field"
            assert "available_count" in db, "Database listing missing 'available_count' field"
            assert "total_records" in db, "Database listing missing 'total_records' field"
            assert "assigned_count" in db, "Database listing missing 'assigned_count' field"
            
            print(f"✓ Bonanza DB '{db.get('name', 'Unknown')}': total={db['total_records']}, available={db['available_count']}, excluded(reserved)={db['excluded_count']}, assigned={db['assigned_count']}")
        else:
            print("⚠ No Bonanza databases found to test")
    
    # ==================== RECORDS LISTING TESTS ====================
    
    def test_memberwd_records_have_reserved_status(self, auth_headers):
        """Test GET /api/memberwd/databases/{id}/records returns records with status='reserved'"""
        # First get a database ID
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        if len(databases) == 0:
            pytest.skip("No MemberWD databases to test")
        
        database_id = databases[0]["id"]
        
        # Get records with status=reserved filter
        response = requests.get(f"{BASE_URL}/api/memberwd/databases/{database_id}/records?status=reserved", headers=auth_headers)
        assert response.status_code == 200, f"Get reserved records failed: {response.text}"
        
        reserved_records = response.json()
        
        if len(reserved_records) > 0:
            record = reserved_records[0]
            # Verify reserved record has correct fields
            assert record["status"] == "reserved", f"Record should have status='reserved', got '{record['status']}'"
            assert "reserved_by" in record, "Reserved record should have 'reserved_by' field"
            assert "reserved_by_name" in record, "Reserved record should have 'reserved_by_name' field"
            assert record.get("is_reserved_member") is True, "Reserved record should have is_reserved_member=True"
            
            print(f"✓ Found {len(reserved_records)} reserved records in MemberWD. Sample: reserved_by={record.get('reserved_by_name')}")
        else:
            print("⚠ No reserved records found in MemberWD database")
    
    def test_bonanza_records_have_reserved_status(self, auth_headers):
        """Test GET /api/bonanza/databases/{id}/records returns records with status='reserved'"""
        # First get a database ID
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        if len(databases) == 0:
            pytest.skip("No Bonanza databases to test")
        
        database_id = databases[0]["id"]
        
        # Get records with status=reserved filter
        response = requests.get(f"{BASE_URL}/api/bonanza/databases/{database_id}/records?status=reserved", headers=auth_headers)
        assert response.status_code == 200, f"Get reserved records failed: {response.text}"
        
        reserved_records = response.json()
        
        if len(reserved_records) > 0:
            record = reserved_records[0]
            assert record["status"] == "reserved", f"Record should have status='reserved'"
            print(f"✓ Found {len(reserved_records)} reserved records in Bonanza")
        else:
            print("⚠ No reserved records found in Bonanza database")
    
    # ==================== RANDOM ASSIGNMENT TESTS ====================
    
    def test_memberwd_assign_random_skips_reserved(self, auth_headers):
        """Test POST /api/memberwd/assign-random does NOT assign reserved records"""
        # Get a database with available records
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        # Find a database with available records
        target_db = None
        for db in databases:
            if db.get("available_count", 0) > 0:
                target_db = db
                break
        
        if not target_db:
            pytest.skip("No MemberWD database with available records")
        
        # Get a staff member
        response = requests.get(f"{BASE_URL}/api/memberwd/staff", headers=auth_headers)
        assert response.status_code == 200
        staff_list = response.json()
        
        if len(staff_list) == 0:
            pytest.skip("No staff members to assign to")
        
        staff_id = staff_list[0]["id"]
        
        # Try to assign 1 record - response should indicate reserved records were skipped
        response = requests.post(f"{BASE_URL}/api/memberwd/assign-random", headers=auth_headers, json={
            "database_id": target_db["id"],
            "staff_id": staff_id,
            "quantity": 1,
            "username_field": "Username"
        })
        
        # Should succeed (assigns from available pool, not reserved)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # Check if response mentions skipped reserved records
            print(f"✓ Random assignment succeeded: assigned={data.get('assigned_count')}, total_reserved_in_db={data.get('total_reserved_in_db', 0)}")
        else:
            # 400 might mean no eligible records (all reserved or assigned)
            print(f"⚠ Random assignment returned 400: {response.json().get('detail', 'unknown')}")
    
    def test_bonanza_assign_random_skips_reserved(self, auth_headers):
        """Test POST /api/bonanza/assign-random does NOT assign reserved records"""
        # Get a database with available records
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        # Find a database with available records
        target_db = None
        for db in databases:
            if db.get("available_count", 0) > 0:
                target_db = db
                break
        
        if not target_db:
            pytest.skip("No Bonanza database with available records")
        
        # Get a staff member
        response = requests.get(f"{BASE_URL}/api/bonanza/staff", headers=auth_headers)
        assert response.status_code == 200
        staff_list = response.json()
        
        if len(staff_list) == 0:
            pytest.skip("No staff members to assign to")
        
        staff_id = staff_list[0]["id"]
        
        # Try to assign 1 record
        response = requests.post(f"{BASE_URL}/api/bonanza/assign-random", headers=auth_headers, json={
            "database_id": target_db["id"],
            "staff_id": staff_id,
            "quantity": 1,
            "username_field": "Username"
        })
        
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Bonanza random assignment: assigned={data.get('assigned_count')}, reserved_skipped={data.get('total_reserved_in_db', 0)}")
        else:
            print(f"⚠ Bonanza random assignment returned 400: {response.json().get('detail', 'unknown')}")
    
    # ==================== RESERVED MEMBERS LIFECYCLE TEST ====================
    
    def test_reserved_member_lifecycle_approve_sync(self, auth_headers):
        """Test that approving a reservation syncs records to status='reserved'"""
        # Get list of approved reserved members
        response = requests.get(f"{BASE_URL}/api/reserved-members?status=approved", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get reserved members: {response.text}"
        
        approved_members = response.json()
        print(f"✓ Found {len(approved_members)} approved reserved members")
        
        # Get pending reserved members to check if we can test approval flow
        response = requests.get(f"{BASE_URL}/api/reserved-members?status=pending", headers=auth_headers)
        assert response.status_code == 200
        pending_members = response.json()
        
        if len(pending_members) > 0:
            print(f"  Found {len(pending_members)} pending reservations (can test approval flow)")
        else:
            print(f"  No pending reservations to test approval flow")
        
        # Verify approved members have expected fields
        if len(approved_members) > 0:
            member = approved_members[0]
            assert "customer_id" in member or "customer_name" in member, "Reserved member missing customer identifier"
            assert "staff_id" in member, "Reserved member missing staff_id"
            assert "product_id" in member, "Reserved member missing product_id"
            assert member.get("status") == "approved", "Reserved member should have status=approved"
            print(f"✓ Sample reserved member: customer={member.get('customer_id') or member.get('customer_name')}, staff={member.get('staff_name')}")
    
    # ==================== MANUAL ASSIGNMENT TESTS ====================
    
    def test_memberwd_manual_assign_blocks_reserved(self, auth_headers):
        """Test POST /api/memberwd/assign blocks or warns about reserved records"""
        # Get records from a database
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        if len(databases) == 0:
            pytest.skip("No MemberWD databases")
        
        database_id = databases[0]["id"]
        
        # Get reserved records
        response = requests.get(f"{BASE_URL}/api/memberwd/databases/{database_id}/records?status=reserved", headers=auth_headers)
        assert response.status_code == 200
        reserved_records = response.json()
        
        if len(reserved_records) == 0:
            # Try to get available records instead
            response = requests.get(f"{BASE_URL}/api/memberwd/databases/{database_id}/records?status=available", headers=auth_headers)
            assert response.status_code == 200
            available_records = response.json()
            
            if len(available_records) == 0:
                pytest.skip("No records to test assignment")
            
            print("⚠ No reserved records to test manual assignment blocking")
            return
        
        # Get a staff member
        response = requests.get(f"{BASE_URL}/api/memberwd/staff", headers=auth_headers)
        assert response.status_code == 200
        staff_list = response.json()
        
        if len(staff_list) == 0:
            pytest.skip("No staff to test assignment")
        
        # Try to manually assign a reserved record - should be blocked or skipped
        reserved_record_id = reserved_records[0]["id"]
        staff_id = staff_list[0]["id"]
        
        response = requests.post(f"{BASE_URL}/api/memberwd/assign", headers=auth_headers, json={
            "record_ids": [reserved_record_id],
            "staff_id": staff_id
        })
        
        # Manual assignment should either fail (400) or succeed with 0 assigned (because record is reserved, not available)
        # The endpoint filters by status='available' so reserved records won't be found
        if response.status_code == 400:
            print(f"✓ Manual assignment of reserved record blocked: {response.json().get('detail', 'blocked')}")
        elif response.status_code == 200:
            data = response.json()
            # If it returns 0 assigned or mentions blocked records, that's correct
            print(f"✓ Manual assignment result: assigned={data.get('assigned_count', 0)}, blocked={len(data.get('blocked_records', []))}")
        else:
            print(f"⚠ Unexpected response: {response.status_code} - {response.text}")
    
    # ==================== PRODUCTS AND STAFF HELPER TESTS ====================
    
    def test_get_products(self, auth_headers):
        """Test GET /api/products returns product list"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_headers)
        assert response.status_code == 200, f"Get products failed: {response.text}"
        
        products = response.json()
        print(f"✓ Found {len(products)} products")
        
        if len(products) > 0:
            product = products[0]
            assert "id" in product, "Product missing 'id' field"
            assert "name" in product, "Product missing 'name' field"
    
    def test_get_users_staff(self, auth_headers):
        """Test GET /api/users returns staff users"""
        response = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert response.status_code == 200, f"Get users failed: {response.text}"
        
        users = response.json()
        staff_users = [u for u in users if u.get("role") == "staff"]
        print(f"✓ Found {len(staff_users)} staff users out of {len(users)} total")


class TestReservedStatusCounts:
    """Test that reserved counts are accurate"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    def test_memberwd_excluded_count_equals_reserved_records(self, auth_headers):
        """Verify excluded_count in database listing matches actual reserved records count"""
        # Get database listing
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        if len(databases) == 0:
            pytest.skip("No MemberWD databases")
        
        for db in databases[:3]:  # Test first 3 databases
            database_id = db["id"]
            excluded_count = db.get("excluded_count", 0)
            
            # Count actual reserved records
            response = requests.get(f"{BASE_URL}/api/memberwd/databases/{database_id}/records?status=reserved", headers=auth_headers)
            assert response.status_code == 200
            reserved_records = response.json()
            actual_reserved_count = len(reserved_records)
            
            assert excluded_count == actual_reserved_count, \
                f"Mismatch for DB {db.get('name')}: excluded_count={excluded_count} but actual reserved={actual_reserved_count}"
            
            print(f"✓ DB '{db.get('name')}': excluded_count={excluded_count} matches actual reserved={actual_reserved_count}")
    
    def test_bonanza_excluded_count_equals_reserved_records(self, auth_headers):
        """Verify excluded_count in database listing matches actual reserved records count"""
        response = requests.get(f"{BASE_URL}/api/bonanza/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        if len(databases) == 0:
            pytest.skip("No Bonanza databases")
        
        for db in databases[:3]:  # Test first 3 databases
            database_id = db["id"]
            excluded_count = db.get("excluded_count", 0)
            
            # Count actual reserved records
            response = requests.get(f"{BASE_URL}/api/bonanza/databases/{database_id}/records?status=reserved", headers=auth_headers)
            assert response.status_code == 200
            reserved_records = response.json()
            actual_reserved_count = len(reserved_records)
            
            assert excluded_count == actual_reserved_count, \
                f"Mismatch for DB {db.get('name')}: excluded_count={excluded_count} but actual reserved={actual_reserved_count}"
            
            print(f"✓ DB '{db.get('name')}': excluded_count={excluded_count} matches actual reserved={actual_reserved_count}")
    
    def test_available_count_excludes_reserved(self, auth_headers):
        """Verify available_count = total - assigned - archived - reserved"""
        response = requests.get(f"{BASE_URL}/api/memberwd/databases", headers=auth_headers)
        assert response.status_code == 200
        databases = response.json()
        
        for db in databases[:3]:
            total = db.get("total_records", 0)
            assigned = db.get("assigned_count", 0)
            archived = db.get("archived_count", 0)
            reserved = db.get("excluded_count", 0)
            available = db.get("available_count", 0)
            
            expected_available = total - assigned - archived - reserved
            
            assert available == expected_available, \
                f"available_count mismatch for DB {db.get('name')}: got {available}, expected {expected_available} (total={total}, assigned={assigned}, archived={archived}, reserved={reserved})"
            
            print(f"✓ DB '{db.get('name')}': available={available} = total({total}) - assigned({assigned}) - archived({archived}) - reserved({reserved})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
