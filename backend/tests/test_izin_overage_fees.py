"""
Test Izin Overage Fees Feature
Tests the new feature: staff daily izin limit of 30 minutes with $5/minute fee for overage

Features tested:
1. Backend API returns izin_limit_minutes, total_izin_overage_minutes, izin_overage_records
2. Izin overage calculation: >30 min daily total triggers fee
3. Izin under 30 minutes should NOT generate overage fee
4. Fee rate is $5/minute with decimal precision
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test credentials
ADMIN_EMAIL = "vicky@crm.com"
ADMIN_PASSWORD = "admin123"

# Test data constants
IZIN_LIMIT_MINUTES = 30
FEE_PER_MINUTE = 5
TEST_STAFF_ID = f"TEST_izin_staff_{uuid.uuid4().hex[:8]}"
TEST_DATE_OVER_LIMIT = "2026-02-17"  # Date with >30 min izin
TEST_DATE_UNDER_LIMIT = "2026-02-16"  # Date with <30 min izin


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Session with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def db_client():
    """MongoDB client"""
    from pymongo import MongoClient
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def setup_test_data(db_client):
    """
    Create test izin records:
    - One date with >30 min total (triggers overage fee)
    - One date with <30 min total (no fee)
    """
    now = datetime.now().isoformat()
    
    # Create test staff user if not exists
    existing_staff = db_client.users.find_one({'id': TEST_STAFF_ID})
    if not existing_staff:
        db_client.users.insert_one({
            'id': TEST_STAFF_ID,
            'name': 'Test Izin Staff',
            'email': f'{TEST_STAFF_ID}@test.com',
            'role': 'staff',
            'created_at': now
        })
    
    # Clear any existing test izin records for our test dates
    db_client.izin_records.delete_many({
        'staff_id': TEST_STAFF_ID,
        'date': {'$in': [TEST_DATE_OVER_LIMIT, TEST_DATE_UNDER_LIMIT]}
    })
    
    # Create izin records for over-limit date (total = 45.5 minutes > 30)
    # This should generate: overage = 45.5 - 30 = 15.5 min, fee = 15.5 * $5 = $77.50
    over_limit_records = [
        {
            'id': str(uuid.uuid4()),
            'staff_id': TEST_STAFF_ID,
            'staff_name': 'Test Izin Staff',
            'date': TEST_DATE_OVER_LIMIT,
            'start_time': '10:00:00',
            'end_time': '10:20:00',
            'duration_minutes': 20.0,  # 20 minutes
            'created_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'staff_id': TEST_STAFF_ID,
            'staff_name': 'Test Izin Staff',
            'date': TEST_DATE_OVER_LIMIT,
            'start_time': '14:00:00',
            'end_time': '14:25:30',
            'duration_minutes': 25.5,  # 25.5 minutes (includes seconds precision)
            'created_at': now
        }
    ]
    db_client.izin_records.insert_many(over_limit_records)
    
    # Create izin records for under-limit date (total = 25 minutes < 30)
    # This should NOT generate any overage fee
    under_limit_records = [
        {
            'id': str(uuid.uuid4()),
            'staff_id': TEST_STAFF_ID,
            'staff_name': 'Test Izin Staff',
            'date': TEST_DATE_UNDER_LIMIT,
            'start_time': '11:00:00',
            'end_time': '11:15:00',
            'duration_minutes': 15.0,  # 15 minutes
            'created_at': now
        },
        {
            'id': str(uuid.uuid4()),
            'staff_id': TEST_STAFF_ID,
            'staff_name': 'Test Izin Staff',
            'date': TEST_DATE_UNDER_LIMIT,
            'start_time': '15:00:00',
            'end_time': '15:10:00',
            'duration_minutes': 10.0,  # 10 minutes
            'created_at': now
        }
    ]
    db_client.izin_records.insert_many(under_limit_records)
    
    yield
    
    # Cleanup test data after all tests
    db_client.izin_records.delete_many({'staff_id': TEST_STAFF_ID})
    db_client.users.delete_one({'id': TEST_STAFF_ID})


class TestIzinOverageFeeAPI:
    """Test GET /api/attendance/admin/fees/summary for izin overage fields"""
    
    def test_api_returns_izin_limit_minutes(self, admin_client):
        """Verify API response includes izin_limit_minutes field"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200, f"API call failed: {response.text}"
        
        data = response.json()
        assert 'izin_limit_minutes' in data, "Response missing izin_limit_minutes field"
        assert data['izin_limit_minutes'] == 30, f"Expected izin_limit=30, got {data['izin_limit_minutes']}"
        print(f"✓ izin_limit_minutes = {data['izin_limit_minutes']}")
    
    def test_api_returns_total_izin_overage_minutes(self, admin_client):
        """Verify API response includes total_izin_overage_minutes field"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        assert 'total_izin_overage_minutes' in data, "Response missing total_izin_overage_minutes field"
        assert isinstance(data['total_izin_overage_minutes'], (int, float)), "total_izin_overage_minutes should be numeric"
        print(f"✓ total_izin_overage_minutes = {data['total_izin_overage_minutes']}")
    
    def test_staff_fees_include_izin_overage_records(self, admin_client):
        """Verify staff_fees entries include izin_overage_records array"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        # Find our test staff
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None, f"Test staff {TEST_STAFF_ID} not found in staff_fees"
        assert 'izin_overage_records' in test_staff, "Staff fee entry missing izin_overage_records field"
        assert isinstance(test_staff['izin_overage_records'], list), "izin_overage_records should be a list"
        print(f"✓ Found {len(test_staff['izin_overage_records'])} izin_overage_records for test staff")


class TestIzinOverageCalculation:
    """Test izin overage fee calculation logic"""
    
    def test_overage_calculated_for_over_30_minutes(self, admin_client):
        """
        Test: Staff with >30 min daily izin should have overage fee
        Setup: TEST_DATE_OVER_LIMIT has 20 + 25.5 = 45.5 min total
        Expected: overage = 45.5 - 30 = 15.5 min, fee = 15.5 * 5 = $77.50
        """
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        # Find our test staff
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None, f"Test staff {TEST_STAFF_ID} not found"
        
        # Check izin overage records
        overage_records = test_staff.get('izin_overage_records', [])
        assert len(overage_records) >= 1, "Expected at least 1 izin overage record"
        
        # Find record for our over-limit date
        over_limit_record = None
        for rec in overage_records:
            if rec.get('date') == TEST_DATE_OVER_LIMIT:
                over_limit_record = rec
                break
        
        assert over_limit_record is not None, f"Expected overage record for {TEST_DATE_OVER_LIMIT}"
        
        # Verify calculation
        expected_total = 45.5
        expected_overage = 15.5
        expected_fee = 77.50
        
        actual_total = over_limit_record.get('total_izin_minutes', 0)
        actual_overage = over_limit_record.get('overage_minutes', 0)
        actual_fee = over_limit_record.get('fee', 0)
        
        # Use approximate comparison for floats
        assert abs(actual_total - expected_total) < 0.01, f"Expected total {expected_total}, got {actual_total}"
        assert abs(actual_overage - expected_overage) < 0.01, f"Expected overage {expected_overage}, got {actual_overage}"
        assert abs(actual_fee - expected_fee) < 0.01, f"Expected fee ${expected_fee}, got ${actual_fee}"
        
        print(f"✓ Over-limit calculation correct: {actual_total} min total, {actual_overage} min overage, ${actual_fee} fee")
    
    def test_no_overage_for_under_30_minutes(self, admin_client):
        """
        Test: Staff with <30 min daily izin should NOT have overage fee
        Setup: TEST_DATE_UNDER_LIMIT has 15 + 10 = 25 min total (< 30 min limit)
        Expected: No overage record for this date
        """
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        # Find our test staff
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        # Test staff should exist (has overage from another date)
        assert test_staff is not None, f"Test staff {TEST_STAFF_ID} not found"
        
        # Check that under-limit date does NOT appear in overage records
        overage_records = test_staff.get('izin_overage_records', [])
        under_limit_record = None
        for rec in overage_records:
            if rec.get('date') == TEST_DATE_UNDER_LIMIT:
                under_limit_record = rec
                break
        
        assert under_limit_record is None, f"Under-limit date {TEST_DATE_UNDER_LIMIT} should NOT have overage record"
        print(f"✓ Under-limit date correctly excluded from overage (25 min < 30 min limit)")
    
    def test_fee_is_5_dollars_per_minute(self, admin_client):
        """Verify fee rate is $5 per minute of overage"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check fee_per_minute in API response
        assert data.get('fee_per_minute') == 5, f"Expected fee_per_minute=5, got {data.get('fee_per_minute')}"
        
        # Verify by checking a specific overage record
        staff_fees = data.get('staff_fees', [])
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        if test_staff and test_staff.get('izin_overage_records'):
            for rec in test_staff['izin_overage_records']:
                if rec.get('date') == TEST_DATE_OVER_LIMIT:
                    overage = rec.get('overage_minutes', 0)
                    fee = rec.get('fee', 0)
                    expected_fee = overage * 5
                    assert abs(fee - expected_fee) < 0.01, f"Fee calculation error: {overage} min * $5 = ${expected_fee}, got ${fee}"
                    print(f"✓ Fee rate verified: {overage} min * $5/min = ${fee}")
    
    def test_decimal_precision_for_seconds(self, admin_client):
        """
        Verify duration_minutes float handles seconds precision
        Our test data has 25.5 minutes = 25 min 30 sec
        """
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        if test_staff:
            for rec in test_staff.get('izin_overage_records', []):
                if rec.get('date') == TEST_DATE_OVER_LIMIT:
                    total = rec.get('total_izin_minutes', 0)
                    # Should be 45.5 (20 + 25.5) - includes decimal
                    assert isinstance(total, float), "total_izin_minutes should be float for decimal precision"
                    assert total == 45.5 or abs(total - 45.5) < 0.01, f"Expected 45.5, got {total}"
                    print(f"✓ Decimal precision preserved: {total} minutes")


class TestIzinOverageStaffFeeStructure:
    """Test the structure of staff fee entries with izin overage"""
    
    def test_staff_fee_has_total_izin_overage_minutes(self, admin_client):
        """Staff fee entry should have total_izin_overage_minutes field"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None
        assert 'total_izin_overage_minutes' in test_staff, "Staff fee missing total_izin_overage_minutes"
        assert test_staff['total_izin_overage_minutes'] >= 15.5, f"Expected >= 15.5, got {test_staff['total_izin_overage_minutes']}"
        print(f"✓ total_izin_overage_minutes = {test_staff['total_izin_overage_minutes']}")
    
    def test_staff_fee_has_izin_overage_days(self, admin_client):
        """Staff fee entry should have izin_overage_days count"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None
        assert 'izin_overage_days' in test_staff, "Staff fee missing izin_overage_days"
        assert test_staff['izin_overage_days'] >= 1, f"Expected >= 1 overage days, got {test_staff['izin_overage_days']}"
        print(f"✓ izin_overage_days = {test_staff['izin_overage_days']}")
    
    def test_izin_overage_record_structure(self, admin_client):
        """Verify structure of individual izin overage records"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None
        overage_records = test_staff.get('izin_overage_records', [])
        assert len(overage_records) > 0
        
        rec = overage_records[0]
        required_fields = ['date', 'total_izin_minutes', 'overage_minutes', 'fee']
        
        for field in required_fields:
            assert field in rec, f"Overage record missing field: {field}"
        
        print(f"✓ Overage record has all required fields: {required_fields}")
        print(f"  Sample record: date={rec['date']}, total={rec['total_izin_minutes']}min, overage={rec['overage_minutes']}min, fee=${rec['fee']}")
    
    def test_izin_overage_fee_included_in_total_fee(self, admin_client):
        """Izin overage fee should be included in staff total_fee"""
        response = admin_client.get(f"{BASE_URL}/api/attendance/admin/fees/summary?year=2026&month=2")
        assert response.status_code == 200
        
        data = response.json()
        staff_fees = data.get('staff_fees', [])
        
        test_staff = None
        for sf in staff_fees:
            if sf.get('staff_id') == TEST_STAFF_ID:
                test_staff = sf
                break
        
        assert test_staff is not None
        
        # Calculate expected izin overage fee from records
        overage_fee_total = sum(r.get('fee', 0) for r in test_staff.get('izin_overage_records', []))
        
        # Total fee should include at least the izin overage fees
        total_fee = test_staff.get('total_fee', 0)
        assert total_fee >= overage_fee_total, f"total_fee ({total_fee}) should include izin overage fees ({overage_fee_total})"
        
        print(f"✓ Izin overage fee (${overage_fee_total}) included in total_fee (${total_fee})")


class TestCleanup:
    """Cleanup verification (fixture handles actual cleanup)"""
    
    def test_verify_test_data_created(self, admin_client, db_client):
        """Verify test data was created and will be cleaned up"""
        # Check test izin records exist
        count = db_client.izin_records.count_documents({'staff_id': TEST_STAFF_ID})
        print(f"✓ Test izin records created: {count} records for staff {TEST_STAFF_ID}")
        assert count > 0, "Test izin records should exist"
