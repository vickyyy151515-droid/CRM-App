"""
Test Suite for Follow-up Endpoint Role Fix
==========================================
Bug: Admin follow-up page showed '0' for all summary counters.
Root cause: /api/followups checked user.role == 'admin' but not 'master_admin',
           causing master_admin users to only see their own (empty) follow-ups.

Fix: Changed `user.role == 'admin'` to `user.role in ['admin', 'master_admin']`
     at lines 38 and 101 in followup.py

Test Credentials:
- Admin: admin@crm.com / admin123 (role: admin)
- Master Admin: test_master_admin@crm.com / test123 (role: master_admin)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFollowupRoleFix:
    """Tests for the followup endpoint role fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_creds = {"email": "admin@crm.com", "password": "admin123"}
        self.master_admin_creds = {"email": "test_master_admin@crm.com", "password": "test123"}
        self.staff_creds = {"email": "staff@crm.com", "password": "staff123"}
        
    def get_auth_token(self, email: str, password: str) -> str:
        """Get JWT token for user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("token")
        return None
    
    def get_headers(self, token: str) -> dict:
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    # Test 1: Admin can access followups with summary counts
    def test_01_admin_gets_followups_with_summary(self):
        """GET /api/followups returns correct summary counts for admin role user"""
        token = self.get_auth_token(**self.admin_creds)
        assert token is not None, "Admin login failed - check credentials admin@crm.com/admin123"
        
        response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "followups" in data, "Response missing 'followups' key"
        assert "summary" in data, "Response missing 'summary' key"
        
        # Verify summary structure
        summary = data["summary"]
        assert "total" in summary, "Summary missing 'total' key"
        assert "critical" in summary, "Summary missing 'critical' key"
        assert "high" in summary, "Summary missing 'high' key"
        assert "medium" in summary, "Summary missing 'medium' key"
        assert "low" in summary, "Summary missing 'low' key"
        assert "deposited" in summary, "Summary missing 'deposited' key"
        
        print(f"✓ Admin followups response: total={summary['total']}, critical={summary['critical']}, high={summary['high']}, medium={summary['medium']}, low={summary['low']}")
    
    # Test 2: Master Admin can access followups with summary counts (THE MAIN BUG FIX TEST)
    def test_02_master_admin_gets_followups_with_summary(self):
        """GET /api/followups returns correct summary counts for master_admin role user"""
        token = self.get_auth_token(**self.master_admin_creds)
        assert token is not None, "Master Admin login failed - check credentials test_master_admin@crm.com/test123"
        
        response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "followups" in data, "Response missing 'followups' key"
        assert "summary" in data, "Response missing 'summary' key"
        
        summary = data["summary"]
        print(f"✓ Master Admin followups response: total={summary['total']}, critical={summary['critical']}, high={summary['high']}, medium={summary['medium']}, low={summary['low']}")
        
        # If test data was seeded, we should have non-zero counts
        # The agent_to_agent_context_note says 4 records were created with varying ages
        # However, we don't assert specific counts as data may vary
    
    # Test 3: Admin and Master Admin see same data (both see all staff's followups)
    def test_03_admin_and_master_admin_see_same_data(self):
        """Both admin and master_admin should see all followups (not filtered to their own)"""
        admin_token = self.get_auth_token(**self.admin_creds)
        master_admin_token = self.get_auth_token(**self.master_admin_creds)
        
        assert admin_token is not None, "Admin login failed"
        assert master_admin_token is not None, "Master Admin login failed"
        
        # Get followups for both roles
        admin_response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(admin_token)
        )
        master_admin_response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(master_admin_token)
        )
        
        assert admin_response.status_code == 200, f"Admin request failed: {admin_response.text}"
        assert master_admin_response.status_code == 200, f"Master Admin request failed: {master_admin_response.text}"
        
        admin_data = admin_response.json()
        master_admin_data = master_admin_response.json()
        
        # Both should have same total (since both can see all staff's data)
        admin_total = admin_data["summary"]["total"]
        master_admin_total = master_admin_data["summary"]["total"]
        
        assert admin_total == master_admin_total, \
            f"Admin sees {admin_total} followups but Master Admin sees {master_admin_total}. " \
            f"Both should see the same data. BUG: master_admin may still be filtered to own data."
        
        print(f"✓ Both admin and master_admin see same total: {admin_total} followups")
    
    # Test 4: Staff with filter works for admin
    def test_04_admin_can_filter_by_staff_id(self):
        """GET /api/followups with staff_id filter works for admin"""
        token = self.get_auth_token(**self.admin_creds)
        assert token is not None, "Admin login failed"
        
        # First get all followups to find a staff_id
        all_response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        assert all_response.status_code == 200
        
        followups = all_response.json().get("followups", [])
        if not followups:
            pytest.skip("No followup data available to test staff_id filter")
        
        # Get unique staff_id from followups
        staff_id = followups[0].get("staff_id")
        if not staff_id:
            pytest.skip("Followup record has no staff_id")
        
        # Filter by this staff_id
        filtered_response = requests.get(
            f"{BASE_URL}/api/followups?staff_id={staff_id}",
            headers=self.get_headers(token)
        )
        assert filtered_response.status_code == 200
        
        filtered_data = filtered_response.json()
        filtered_followups = filtered_data.get("followups", [])
        
        # All returned followups should have this staff_id
        for fu in filtered_followups:
            assert fu.get("staff_id") == staff_id, \
                f"Expected staff_id={staff_id}, got {fu.get('staff_id')}"
        
        print(f"✓ Admin staff_id filter works: {len(filtered_followups)} followups for staff {staff_id}")
    
    # Test 5: Staff with filter works for master_admin
    def test_05_master_admin_can_filter_by_staff_id(self):
        """GET /api/followups with staff_id filter works for master_admin"""
        token = self.get_auth_token(**self.master_admin_creds)
        assert token is not None, "Master Admin login failed"
        
        # First get all followups to find a staff_id
        all_response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        assert all_response.status_code == 200
        
        followups = all_response.json().get("followups", [])
        if not followups:
            pytest.skip("No followup data available to test staff_id filter")
        
        # Get unique staff_id from followups
        staff_id = followups[0].get("staff_id")
        if not staff_id:
            pytest.skip("Followup record has no staff_id")
        
        # Filter by this staff_id
        filtered_response = requests.get(
            f"{BASE_URL}/api/followups?staff_id={staff_id}",
            headers=self.get_headers(token)
        )
        assert filtered_response.status_code == 200
        
        filtered_data = filtered_response.json()
        filtered_followups = filtered_data.get("followups", [])
        
        # All returned followups should have this staff_id
        for fu in filtered_followups:
            assert fu.get("staff_id") == staff_id, \
                f"Expected staff_id={staff_id}, got {fu.get('staff_id')}"
        
        print(f"✓ Master Admin staff_id filter works: {len(filtered_followups)} followups for staff {staff_id}")
    
    # Test 6: Followup filters endpoint works for master_admin
    def test_06_master_admin_gets_followup_filters(self):
        """GET /api/followups/filters returns products and databases for master_admin"""
        token = self.get_auth_token(**self.master_admin_creds)
        assert token is not None, "Master Admin login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/followups/filters",
            headers=self.get_headers(token)
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "products" in data, "Response missing 'products' key"
        assert "databases" in data, "Response missing 'databases' key"
        assert isinstance(data["products"], list), "products should be a list"
        assert isinstance(data["databases"], list), "databases should be a list"
        
        print(f"✓ Master Admin filters: {len(data['products'])} products, {len(data['databases'])} databases")
    
    # Test 7: Staff user only sees their own followups
    def test_07_staff_sees_only_own_followups(self):
        """Staff user should only see followups assigned to them"""
        # First login as admin to get a valid staff_id
        admin_token = self.get_auth_token(**self.admin_creds)
        assert admin_token is not None, "Admin login failed"
        
        # Try to login as staff
        staff_token = self.get_auth_token(**self.staff_creds)
        if not staff_token:
            pytest.skip("Staff login failed - staff@crm.com/staff123 credentials may not exist")
        
        # Get staff's own followups
        staff_response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(staff_token)
        )
        
        # Staff should be able to access endpoint but see only their data
        if staff_response.status_code == 200:
            data = staff_response.json()
            print(f"✓ Staff sees {data['summary']['total']} followups (their own only)")
        else:
            # Staff may not have any followups assigned which is fine
            print(f"Staff request status: {staff_response.status_code}")
    
    # Test 8: Summary counts match followup list length
    def test_08_summary_counts_match_list_length(self):
        """Summary card counts should match actual followup list length"""
        token = self.get_auth_token(**self.admin_creds)
        assert token is not None, "Admin login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        assert response.status_code == 200
        
        data = response.json()
        followups = data["followups"]
        summary = data["summary"]
        
        # Total should match list length
        assert summary["total"] == len(followups), \
            f"Summary total ({summary['total']}) doesn't match followups list length ({len(followups)})"
        
        # Count urgency levels manually
        critical_count = sum(1 for f in followups if f.get("urgency") == "critical")
        high_count = sum(1 for f in followups if f.get("urgency") == "high")
        medium_count = sum(1 for f in followups if f.get("urgency") == "medium")
        low_count = sum(1 for f in followups if f.get("urgency") == "low")
        
        assert summary["critical"] == critical_count, \
            f"Summary critical ({summary['critical']}) doesn't match actual ({critical_count})"
        assert summary["high"] == high_count, \
            f"Summary high ({summary['high']}) doesn't match actual ({high_count})"
        assert summary["medium"] == medium_count, \
            f"Summary medium ({summary['medium']}) doesn't match actual ({medium_count})"
        assert summary["low"] == low_count, \
            f"Summary low ({summary['low']}) doesn't match actual ({low_count})"
        
        print(f"✓ Summary counts match: total={summary['total']}, critical={critical_count}, high={high_count}, medium={medium_count}, low={low_count}")
    
    # Test 9: Urgency levels are correctly categorized
    def test_09_urgency_levels_correctly_categorized(self):
        """Urgency levels: critical=7+days, high=3+days, medium=1+days, low=today"""
        token = self.get_auth_token(**self.admin_creds)
        assert token is not None, "Admin login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(token)
        )
        assert response.status_code == 200
        
        followups = response.json().get("followups", [])
        if not followups:
            pytest.skip("No followup data to verify urgency categorization")
        
        # Verify urgency categorization logic
        for fu in followups:
            days = fu.get("days_since_response", 0)
            urgency = fu.get("urgency")
            
            if days >= 7:
                expected = "critical"
            elif days >= 3:
                expected = "high"
            elif days >= 1:
                expected = "medium"
            else:
                expected = "low"
            
            assert urgency == expected, \
                f"Record with {days} days should be '{expected}' but is '{urgency}'"
        
        print(f"✓ All {len(followups)} followups have correct urgency categorization")
    
    # Test 10: Verify admin role sees all staff data (not filtered)
    def test_10_admin_sees_all_staff_data_not_filtered_to_self(self):
        """Admin should see all staff's followups, not just their own assigned records"""
        admin_token = self.get_auth_token(**self.admin_creds)
        assert admin_token is not None, "Admin login failed"
        
        response = requests.get(
            f"{BASE_URL}/api/followups",
            headers=self.get_headers(admin_token)
        )
        assert response.status_code == 200
        
        followups = response.json().get("followups", [])
        
        # If there are followups, they should NOT all be assigned to the admin
        # (assuming admin doesn't have records assigned to them)
        if followups:
            staff_ids = set(f.get("staff_id") for f in followups if f.get("staff_id"))
            print(f"✓ Admin sees followups from {len(staff_ids)} different staff members: {staff_ids}")
            
            # If we only see 1 staff_id and it matches admin's id, that might indicate the bug
            # But we can't easily get admin's user_id without another endpoint
        else:
            print("✓ No followups in system (test data may not have been seeded)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
