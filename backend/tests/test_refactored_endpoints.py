"""
Tests for P2 Refactored Endpoints - Shared Utility Functions
Verifies that memberwd.py and bonanza.py endpoints using repair_helpers.py
return the same response structure as before refactoring.

Endpoints tested:
- MemberWD: data-health, diagnose-product-mismatch, repair-product-mismatch, 
            diagnose-reserved-conflicts, fix-reserved-conflicts, repair-data
- Bonanza:  data-health, diagnose-product-mismatch, repair-product-mismatch,
            diagnose-reserved-conflicts, fix-reserved-conflicts, repair-data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "vicky123"


class TestRefactoredMemberWDEndpoints:
    """Tests for MemberWD refactored endpoints using shared repair_helpers.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_memberwd_data_health_structure(self):
        """
        GET /api/memberwd/admin/data-health 
        Must return: is_healthy, total_issues, databases array, batches array, batch_mismatches
        """
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/data-health",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "is_healthy" in data, "Missing 'is_healthy' field"
        assert "total_issues" in data, "Missing 'total_issues' field"
        assert "databases" in data, "Missing 'databases' field"
        assert "batches" in data, "Missing 'batches' field"
        assert "batch_mismatches" in data, "Missing 'batch_mismatches' field"
        
        # Type checks
        assert isinstance(data["is_healthy"], bool), "'is_healthy' must be boolean"
        assert isinstance(data["total_issues"], int), "'total_issues' must be integer"
        assert isinstance(data["databases"], list), "'databases' must be array"
        assert isinstance(data["batches"], list), "'batches' must be array"
        assert isinstance(data["batch_mismatches"], int), "'batch_mismatches' must be integer"
        
        # Per-database structure
        if data["databases"]:
            db = data["databases"][0]
            assert "database_id" in db, "Database missing 'database_id'"
            assert "database_name" in db, "Database missing 'database_name'"
            assert "has_issues" in db, "Database missing 'has_issues'"
            assert "total_issues" in db, "Database missing 'total_issues'"
        
        # Per-batch structure (batch mismatch check)
        if data["batches"]:
            batch = data["batches"][0]
            assert "batch_id" in batch, "Batch missing 'batch_id'"
            assert "staff_name" in batch, "Batch missing 'staff_name'"
            assert "has_mismatch" in batch, "Batch missing 'has_mismatch'"
        
        print(f"PASS: data-health returned is_healthy={data['is_healthy']}, "
              f"total_issues={data['total_issues']}, databases={len(data['databases'])}, "
              f"batches={len(data['batches'])}, batch_mismatches={data['batch_mismatches']}")
    
    def test_02_memberwd_diagnose_product_mismatch_structure(self):
        """
        GET /api/memberwd/admin/diagnose-product-mismatch
        Must return: total_mismatched, by_database, would_move, cannot_fix, current_stats
        """
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/diagnose-product-mismatch",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "total_mismatched" in data, "Missing 'total_mismatched' field"
        assert "by_database" in data, "Missing 'by_database' field"
        assert "would_move" in data, "Missing 'would_move' field"
        assert "cannot_fix" in data, "Missing 'cannot_fix' field"
        assert "current_stats" in data, "Missing 'current_stats' field"
        
        # Type checks
        assert isinstance(data["total_mismatched"], int), "'total_mismatched' must be integer"
        assert isinstance(data["by_database"], list), "'by_database' must be array"
        assert isinstance(data["would_move"], list), "'would_move' must be array"
        assert isinstance(data["cannot_fix"], list), "'cannot_fix' must be array"
        assert isinstance(data["current_stats"], list), "'current_stats' must be array"
        
        # Current stats structure
        if data["current_stats"]:
            stat = data["current_stats"][0]
            assert "database_name" in stat, "current_stats missing 'database_name'"
            assert "product_id" in stat or stat.get("product_id") is None, "current_stats check product_id"
            assert "available" in stat, "current_stats missing 'available'"
            assert "assigned" in stat, "current_stats missing 'assigned'"
            assert "total" in stat, "current_stats missing 'total'"
        
        print(f"PASS: diagnose-product-mismatch returned total_mismatched={data['total_mismatched']}, "
              f"by_database={len(data['by_database'])}, would_move={len(data['would_move'])}")
    
    def test_03_memberwd_repair_product_mismatch_structure(self):
        """
        POST /api/memberwd/admin/repair-product-mismatch
        Must return: success, message, repair_log with updated_database_stats
        """
        response = requests.post(
            f"{BASE_URL}/api/memberwd/admin/repair-product-mismatch",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        assert "repair_log" in data, "Missing 'repair_log' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["message"], str), "'message' must be string"
        assert isinstance(data["repair_log"], dict), "'repair_log' must be object"
        
        # repair_log structure
        repair_log = data["repair_log"]
        assert "updated_database_stats" in repair_log, "repair_log missing 'updated_database_stats'"
        assert isinstance(repair_log["updated_database_stats"], list), "'updated_database_stats' must be array"
        
        # updated_database_stats structure
        if repair_log["updated_database_stats"]:
            stat = repair_log["updated_database_stats"][0]
            assert "database_name" in stat, "updated_database_stats missing 'database_name'"
            assert "total" in stat, "updated_database_stats missing 'total'"
            assert "available" in stat, "updated_database_stats missing 'available'"
            assert "assigned" in stat, "updated_database_stats missing 'assigned'"
        
        print(f"PASS: repair-product-mismatch returned success={data['success']}, message='{data['message'][:50]}...'")
    
    def test_04_memberwd_diagnose_reserved_conflicts_structure(self):
        """
        GET /api/memberwd/admin/diagnose-reserved-conflicts
        Must return: total_conflicts, conflicts array, message
        """
        response = requests.get(
            f"{BASE_URL}/api/memberwd/admin/diagnose-reserved-conflicts",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "total_conflicts" in data, "Missing 'total_conflicts' field"
        assert "conflicts" in data, "Missing 'conflicts' field"
        assert "message" in data, "Missing 'message' field"
        
        # Type checks
        assert isinstance(data["total_conflicts"], int), "'total_conflicts' must be integer"
        assert isinstance(data["conflicts"], list), "'conflicts' must be array"
        assert isinstance(data["message"], str), "'message' must be string"
        
        # Conflict structure (if any)
        if data["conflicts"]:
            conflict = data["conflicts"][0]
            assert "record_id" in conflict, "conflict missing 'record_id'"
            assert "customer_id" in conflict, "conflict missing 'customer_id'"
            assert "assigned_to" in conflict, "conflict missing 'assigned_to'"
            assert "reserved_by" in conflict, "conflict missing 'reserved_by'"
        
        print(f"PASS: diagnose-reserved-conflicts returned total_conflicts={data['total_conflicts']}, message='{data['message'][:50]}...'")
    
    def test_05_memberwd_fix_reserved_conflicts_structure(self):
        """
        POST /api/memberwd/admin/fix-reserved-conflicts
        Must return: success, total_fixed, fixed_records, message
        """
        response = requests.post(
            f"{BASE_URL}/api/memberwd/admin/fix-reserved-conflicts",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "total_fixed" in data, "Missing 'total_fixed' field"
        assert "fixed_records" in data, "Missing 'fixed_records' field"
        assert "message" in data, "Missing 'message' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["total_fixed"], int), "'total_fixed' must be integer"
        assert isinstance(data["fixed_records"], list), "'fixed_records' must be array"
        assert isinstance(data["message"], str), "'message' must be string"
        
        # fixed_records structure (if any)
        if data["fixed_records"]:
            record = data["fixed_records"][0]
            assert "record_id" in record, "fixed_record missing 'record_id'"
            assert "customer_id" in record, "fixed_record missing 'customer_id'"
            assert "from_staff" in record, "fixed_record missing 'from_staff'"
            assert "to_staff" in record, "fixed_record missing 'to_staff'"
        
        print(f"PASS: fix-reserved-conflicts returned success={data['success']}, total_fixed={data['total_fixed']}")
    
    def test_06_memberwd_repair_data_structure(self):
        """
        POST /api/memberwd/admin/repair-data
        Must return: success, message, repair_log with fixed_batch_counts and batches_synchronized
        """
        response = requests.post(
            f"{BASE_URL}/api/memberwd/admin/repair-data",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        assert "repair_log" in data, "Missing 'repair_log' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["message"], str), "'message' must be string"
        assert isinstance(data["repair_log"], dict), "'repair_log' must be object"
        
        # repair_log structure (MemberWD specific: includes batch sync)
        repair_log = data["repair_log"]
        assert "fixed_batch_counts" in repair_log, "repair_log missing 'fixed_batch_counts'"
        assert "batches_synchronized" in repair_log, "repair_log missing 'batches_synchronized'"
        assert isinstance(repair_log["fixed_batch_counts"], int), "'fixed_batch_counts' must be integer"
        assert isinstance(repair_log["batches_synchronized"], list), "'batches_synchronized' must be array"
        
        print(f"PASS: repair-data returned success={data['success']}, fixed_batch_counts={repair_log['fixed_batch_counts']}")


class TestRefactoredBonanzaEndpoints:
    """Tests for Bonanza refactored endpoints using shared repair_helpers.py"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_bonanza_data_health_structure(self):
        """
        GET /api/bonanza/admin/data-health
        Must return: is_healthy, total_issues, databases array, issues array
        """
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/data-health",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "is_healthy" in data, "Missing 'is_healthy' field"
        assert "total_issues" in data, "Missing 'total_issues' field"
        assert "databases" in data, "Missing 'databases' field"
        assert "issues" in data, "Missing 'issues' field"
        
        # Type checks
        assert isinstance(data["is_healthy"], bool), "'is_healthy' must be boolean"
        assert isinstance(data["total_issues"], int), "'total_issues' must be integer"
        assert isinstance(data["databases"], list), "'databases' must be array"
        assert isinstance(data["issues"], list), "'issues' must be array"
        
        # Per-database structure
        if data["databases"]:
            db = data["databases"][0]
            assert "database_id" in db, "Database missing 'database_id'"
            assert "database_name" in db, "Database missing 'database_name'"
            assert "has_issues" in db, "Database missing 'has_issues'"
            assert "total_issues" in db, "Database missing 'total_issues'"
        
        print(f"PASS: data-health returned is_healthy={data['is_healthy']}, "
              f"total_issues={data['total_issues']}, databases={len(data['databases'])}")
    
    def test_02_bonanza_diagnose_product_mismatch_structure(self):
        """
        GET /api/bonanza/admin/diagnose-product-mismatch
        Must return: total_mismatched, by_database, would_move, cannot_fix, current_stats
        """
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/diagnose-product-mismatch",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "total_mismatched" in data, "Missing 'total_mismatched' field"
        assert "by_database" in data, "Missing 'by_database' field"
        assert "would_move" in data, "Missing 'would_move' field"
        assert "cannot_fix" in data, "Missing 'cannot_fix' field"
        assert "current_stats" in data, "Missing 'current_stats' field"
        
        # Type checks
        assert isinstance(data["total_mismatched"], int), "'total_mismatched' must be integer"
        assert isinstance(data["by_database"], list), "'by_database' must be array"
        assert isinstance(data["would_move"], list), "'would_move' must be array"
        assert isinstance(data["cannot_fix"], list), "'cannot_fix' must be array"
        assert isinstance(data["current_stats"], list), "'current_stats' must be array"
        
        print(f"PASS: diagnose-product-mismatch returned total_mismatched={data['total_mismatched']}")
    
    def test_03_bonanza_repair_product_mismatch_structure(self):
        """
        POST /api/bonanza/admin/repair-product-mismatch
        Must return: success, message, repair_log with updated_database_stats
        """
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/repair-product-mismatch",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        assert "repair_log" in data, "Missing 'repair_log' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["message"], str), "'message' must be string"
        assert isinstance(data["repair_log"], dict), "'repair_log' must be object"
        
        # repair_log structure
        repair_log = data["repair_log"]
        assert "updated_database_stats" in repair_log, "repair_log missing 'updated_database_stats'"
        assert isinstance(repair_log["updated_database_stats"], list), "'updated_database_stats' must be array"
        
        print(f"PASS: repair-product-mismatch returned success={data['success']}")
    
    def test_04_bonanza_diagnose_reserved_conflicts_structure(self):
        """
        GET /api/bonanza/admin/diagnose-reserved-conflicts
        Must return: total_conflicts, conflicts array, message
        """
        response = requests.get(
            f"{BASE_URL}/api/bonanza/admin/diagnose-reserved-conflicts",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "total_conflicts" in data, "Missing 'total_conflicts' field"
        assert "conflicts" in data, "Missing 'conflicts' field"
        assert "message" in data, "Missing 'message' field"
        
        # Type checks
        assert isinstance(data["total_conflicts"], int), "'total_conflicts' must be integer"
        assert isinstance(data["conflicts"], list), "'conflicts' must be array"
        assert isinstance(data["message"], str), "'message' must be string"
        
        print(f"PASS: diagnose-reserved-conflicts returned total_conflicts={data['total_conflicts']}")
    
    def test_05_bonanza_fix_reserved_conflicts_structure(self):
        """
        POST /api/bonanza/admin/fix-reserved-conflicts
        Must return: success, total_fixed, fixed_records, message
        """
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/fix-reserved-conflicts",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "total_fixed" in data, "Missing 'total_fixed' field"
        assert "fixed_records" in data, "Missing 'fixed_records' field"
        assert "message" in data, "Missing 'message' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["total_fixed"], int), "'total_fixed' must be integer"
        assert isinstance(data["fixed_records"], list), "'fixed_records' must be array"
        assert isinstance(data["message"], str), "'message' must be string"
        
        print(f"PASS: fix-reserved-conflicts returned success={data['success']}, total_fixed={data['total_fixed']}")
    
    def test_06_bonanza_repair_data_structure(self):
        """
        POST /api/bonanza/admin/repair-data
        Must return: success, message, repair_log
        """
        response = requests.post(
            f"{BASE_URL}/api/bonanza/admin/repair-data",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Required fields
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        assert "repair_log" in data, "Missing 'repair_log' field"
        
        # Type checks
        assert data["success"] == True, "'success' must be True"
        assert isinstance(data["message"], str), "'message' must be string"
        assert isinstance(data["repair_log"], dict), "'repair_log' must be object"
        
        # repair_log must have common fields
        repair_log = data["repair_log"]
        assert "timestamp" in repair_log, "repair_log missing 'timestamp'"
        
        print(f"PASS: repair-data returned success={data['success']}, message='{data['message'][:50]}...'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
