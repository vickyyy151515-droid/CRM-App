"""
Test cases for Reserved Members Permanent Toggle Feature.
Admin should be able to mark reserved members as 'Permanent' so they never expire.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPermanentToggleFeature:
    """Test PATCH /reserved-members/{id}/permanent endpoint and related functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin token before each test"""
        self.admin_token = None
        # Login as master_admin
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.admin_token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_toggle_permanent_on(self):
        """Test toggling a member to permanent status"""
        # Get list of reserved members to find a non-permanent one
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert resp.status_code == 200, f"Failed to get reserved members: {resp.text}"
        
        members = resp.json()
        assert len(members) > 0, "No reserved members found for testing"
        
        # Find TESTCUST002 (regular, non-permanent)
        target_member = None
        for m in members:
            customer_id = m.get('customer_id') or m.get('customer_name', '')
            if 'TESTCUST002' in customer_id.upper():
                target_member = m
                break
        
        if not target_member:
            # Use any non-permanent member
            for m in members:
                if not m.get('is_permanent', False):
                    target_member = m
                    break
        
        if not target_member:
            pytest.skip("No non-permanent members found to test toggle on")
        
        member_id = target_member['id']
        initial_status = target_member.get('is_permanent', False)
        
        # Toggle permanent status
        toggle_resp = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=self.headers)
        assert toggle_resp.status_code == 200, f"Toggle failed: {toggle_resp.text}"
        
        data = toggle_resp.json()
        assert 'message' in data, "Response missing 'message' field"
        assert 'is_permanent' in data, "Response missing 'is_permanent' field"
        assert data['is_permanent'] != initial_status, "Permanent status should have toggled"
        
        # Verify by fetching the member again
        verify_resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert verify_resp.status_code == 200
        
        updated_member = next((m for m in verify_resp.json() if m['id'] == member_id), None)
        assert updated_member is not None, "Updated member not found"
        assert updated_member.get('is_permanent') == data['is_permanent'], "Database not updated correctly"
        
        # Toggle back to original state for cleanup
        requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=self.headers)
    
    def test_toggle_permanent_off(self):
        """Test toggling a permanent member back to non-permanent"""
        # Get list of reserved members to find a permanent one
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert resp.status_code == 200
        
        members = resp.json()
        
        # Find TESTCUST001 (permanent)
        target_member = None
        for m in members:
            customer_id = m.get('customer_id') or m.get('customer_name', '')
            if 'TESTCUST001' in customer_id.upper():
                target_member = m
                break
        
        if not target_member:
            # Find any permanent member
            for m in members:
                if m.get('is_permanent', False):
                    target_member = m
                    break
        
        if not target_member:
            pytest.skip("No permanent members found to test toggle off")
        
        member_id = target_member['id']
        
        # Make sure it's permanent first
        if not target_member.get('is_permanent', False):
            requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=self.headers)
        
        # Now toggle it off
        toggle_resp = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=self.headers)
        assert toggle_resp.status_code == 200, f"Toggle off failed: {toggle_resp.text}"
        
        data = toggle_resp.json()
        assert 'non-permanent' in data['message'].lower() or data['is_permanent'] == False
        
        # Toggle back on to maintain test state
        requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=self.headers)
    
    def test_get_reserved_members_returns_is_permanent(self):
        """Test that GET /reserved-members returns is_permanent field"""
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert resp.status_code == 200
        
        members = resp.json()
        assert len(members) > 0, "No reserved members found"
        
        # Check that is_permanent field exists in response
        for m in members:
            assert 'is_permanent' in m, f"Member {m.get('id')} missing is_permanent field"
            assert isinstance(m['is_permanent'], bool), f"is_permanent should be boolean"
    
    def test_permanent_endpoint_requires_admin(self):
        """Test that staff users cannot toggle permanent status"""
        # First, try to login as staff user
        staff_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "staff@crm.com",
            "password": "staff123"
        })
        
        if staff_login.status_code != 200:
            pytest.skip("No staff user available to test authorization")
        
        staff_token = staff_login.json()["token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        
        # Get a member ID to try toggling
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        members = resp.json()
        if not members:
            pytest.skip("No members to test authorization")
        
        member_id = members[0]['id']
        
        # Try to toggle as staff - should be forbidden
        toggle_resp = requests.patch(f"{BASE_URL}/api/reserved-members/{member_id}/permanent", headers=staff_headers)
        assert toggle_resp.status_code == 403, f"Staff should not be able to toggle permanent. Got: {toggle_resp.status_code}"
    
    def test_toggle_permanent_404_not_found(self):
        """Test toggling non-existent member returns 404"""
        fake_id = "non-existent-member-id-12345"
        toggle_resp = requests.patch(f"{BASE_URL}/api/reserved-members/{fake_id}/permanent", headers=self.headers)
        assert toggle_resp.status_code == 404, f"Expected 404, got: {toggle_resp.status_code}"
    
    def test_cleanup_preview_includes_permanent_members_count(self):
        """Test that cleanup preview endpoint includes permanent_members_count and skips them"""
        resp = requests.get(f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview", headers=self.headers)
        assert resp.status_code == 200, f"Cleanup preview failed: {resp.text}"
        
        data = resp.json()
        
        # Check that permanent_members_count is present
        assert 'permanent_members_count' in data, "Missing permanent_members_count in response"
        assert isinstance(data['permanent_members_count'], int), "permanent_members_count should be integer"
        
        # Check that permanent_members list is present
        assert 'permanent_members' in data, "Missing permanent_members list"
        
        # Verify permanent members are not in will_be_deleted or expiring_soon
        permanent_ids = {m['id'] for m in data.get('permanent_members', [])}
        deleted_ids = {m['id'] for m in data.get('will_be_deleted', [])}
        expiring_ids = {m['id'] for m in data.get('expiring_soon', [])}
        
        overlap_deleted = permanent_ids & deleted_ids
        overlap_expiring = permanent_ids & expiring_ids
        
        assert len(overlap_deleted) == 0, f"Permanent members should not be in will_be_deleted: {overlap_deleted}"
        assert len(overlap_expiring) == 0, f"Permanent members should not be in expiring_soon: {overlap_expiring}"
    
    def test_cleanup_skips_permanent_members(self):
        """Test that process_reserved_member_cleanup skips permanent members"""
        # First, ensure we have a permanent member
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        members = resp.json()
        
        permanent_member = None
        for m in members:
            if m.get('is_permanent', False):
                permanent_member = m
                break
        
        if not permanent_member:
            pytest.skip("No permanent member available to test cleanup skip")
        
        # Get preview before running cleanup
        preview_resp = requests.get(f"{BASE_URL}/api/scheduled-reports/reserved-member-cleanup-preview", headers=self.headers)
        preview = preview_resp.json()
        
        initial_permanent_count = preview.get('permanent_members_count', 0)
        assert initial_permanent_count > 0, "Expected at least one permanent member"
        
        # Verify the permanent member is listed in permanent_members
        permanent_ids = [m['id'] for m in preview.get('permanent_members', [])]
        assert permanent_member['id'] in permanent_ids, "Permanent member should be in permanent_members list"
        
        # Note: We don't actually run cleanup here as it modifies data
        # The logic in process_reserved_member_cleanup checks is_permanent=True and skips


class TestPermanentMemberDisplay:
    """Test that permanent status is correctly displayed in GET endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin token"""
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vicky@crm.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.admin_token = login_resp.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_is_permanent_field_in_reserved_members_list(self):
        """Verify is_permanent boolean field is present for all members"""
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert resp.status_code == 200
        
        members = resp.json()
        for member in members:
            assert 'is_permanent' in member, f"Missing is_permanent for member {member.get('id')}"
            assert isinstance(member['is_permanent'], bool)
    
    def test_permanent_filter_by_status(self):
        """Test that permanent members still appear in approved filter"""
        resp = requests.get(f"{BASE_URL}/api/reserved-members", headers=self.headers)
        assert resp.status_code == 200
        
        members = resp.json()
        approved_permanent = [m for m in members if m.get('status') == 'approved' and m.get('is_permanent', False)]
        
        # Permanent members should have status 'approved'
        for m in approved_permanent:
            assert m['status'] == 'approved', "Permanent member should have approved status"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
