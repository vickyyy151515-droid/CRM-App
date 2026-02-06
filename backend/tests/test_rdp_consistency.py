"""
Test RDP Consistency - Critical Bug Fix Validation

This test validates the fix for the recurring RDP count mismatch bug:
When a single customer makes deposits into two different products 
under the same staff on the same day, the staff's total RDP count 
should increment by one (not two).

The bug was: Customer counted once per-staff but multiple times 
if they deposited into multiple products.
"""
import pytest
import asyncio
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Import the functions to test
import sys
sys.path.insert(0, '/app/backend')
from routes.daily_summary import generate_daily_summary, normalize_customer_id


# Test database setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = 'test_rdp_consistency_db'


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def test_db():
    """Setup test database connection"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Clean up before tests
    await db.omset_records.delete_many({})
    await db.users.delete_many({})
    await db.products.delete_many({})
    await db.daily_summaries.delete_many({})
    
    yield db
    
    # Clean up after tests
    await db.omset_records.delete_many({})
    await db.users.delete_many({})
    await db.products.delete_many({})
    await db.daily_summaries.delete_many({})
    client.close()


@pytest.fixture
async def setup_test_data(test_db):
    """Setup test data: 1 staff, 2 products, 1 customer depositing to both products"""
    db = test_db
    
    # Clean any existing data
    await db.omset_records.delete_many({})
    await db.users.delete_many({})
    await db.products.delete_many({})
    
    # Create test staff
    staff_id = str(uuid.uuid4())
    staff = {
        'id': staff_id,
        'name': 'Test Staff',
        'email': 'teststaff@test.com',
        'role': 'staff',
        'status': 'active'
    }
    await db.users.insert_one(staff)
    
    # Create two products
    product1_id = str(uuid.uuid4())
    product2_id = str(uuid.uuid4())
    
    products = [
        {'id': product1_id, 'name': 'Product Alpha', 'status': 'active'},
        {'id': product2_id, 'name': 'Product Beta', 'status': 'active'}
    ]
    await db.products.insert_many(products)
    
    # Create one customer depositing to BOTH products on the same day
    customer_id = 'CUST-12345'
    customer_id_normalized = normalize_customer_id(customer_id)
    test_date = '2025-01-15'
    
    # First, create a historical record to make this customer an RDP (not NDP)
    historical_record = {
        'id': str(uuid.uuid4()),
        'product_id': product1_id,
        'product_name': 'Product Alpha',
        'staff_id': staff_id,
        'staff_name': 'Test Staff',
        'record_date': '2025-01-10',  # Previous date
        'customer_name': 'Test Customer',
        'customer_id': customer_id,
        'customer_id_normalized': customer_id_normalized,
        'nominal': 1000000,
        'depo_kelipatan': 1.0,
        'depo_total': 1000000,
        'keterangan': None,
        'customer_type': 'NDP',
        'created_at': datetime.now().isoformat()
    }
    await db.omset_records.insert_one(historical_record)
    
    # Record 1: Customer deposits to Product Alpha
    record1 = {
        'id': str(uuid.uuid4()),
        'product_id': product1_id,
        'product_name': 'Product Alpha',
        'staff_id': staff_id,
        'staff_name': 'Test Staff',
        'record_date': test_date,
        'customer_name': 'Test Customer',
        'customer_id': customer_id,
        'customer_id_normalized': customer_id_normalized,
        'nominal': 500000,
        'depo_kelipatan': 1.0,
        'depo_total': 500000,
        'keterangan': None,
        'customer_type': 'RDP',
        'created_at': datetime.now().isoformat()
    }
    
    # Record 2: Same customer deposits to Product Beta (different product!)
    record2 = {
        'id': str(uuid.uuid4()),
        'product_id': product2_id,
        'product_name': 'Product Beta',
        'staff_id': staff_id,
        'staff_name': 'Test Staff',
        'record_date': test_date,
        'customer_name': 'Test Customer',
        'customer_id': customer_id,
        'customer_id_normalized': customer_id_normalized,
        'nominal': 300000,
        'depo_kelipatan': 1.0,
        'depo_total': 300000,
        'keterangan': None,
        'customer_type': 'RDP',  # Also RDP since customer deposited before
        'created_at': datetime.now().isoformat()
    }
    
    await db.omset_records.insert_many([record1, record2])
    
    return {
        'staff_id': staff_id,
        'product1_id': product1_id,
        'product2_id': product2_id,
        'customer_id': customer_id,
        'test_date': test_date
    }


class TestRDPConsistency:
    """Test suite for RDP consistency between staff and product summaries"""
    
    @pytest.mark.asyncio
    async def test_rdp_count_consistency_single_customer_multiple_products(self, test_db, setup_test_data):
        """
        CRITICAL TEST: When 1 customer deposits to 2 products under same staff on same day:
        - Staff RDP count should be 1 (not 2)
        - Sum of product RDPs should also be 1 (not 2)
        - These two values must match
        """
        data = setup_test_data
        
        # Monkey-patch get_db to use test database
        import routes.daily_summary as ds_module
        original_get_db = ds_module.get_db
        ds_module.get_db = lambda: test_db
        
        try:
            # Generate summary for test date
            summary = await generate_daily_summary(data['test_date'])
            
            assert summary is not None, "Summary should not be None"
            
            # Get staff breakdown
            staff_breakdown = summary.get('staff_breakdown', [])
            assert len(staff_breakdown) == 1, "Should have exactly 1 staff"
            
            staff_stats = staff_breakdown[0]
            staff_rdp_count = staff_stats.get('rdp_count', 0)
            
            # Get product breakdown
            product_breakdown = summary.get('product_breakdown', [])
            assert len(product_breakdown) == 2, "Should have exactly 2 products"
            
            # Sum RDP counts from products
            product_rdp_sum = sum(p.get('rdp_count', 0) for p in product_breakdown)
            
            # THE CRITICAL ASSERTION: Staff RDP must equal Product RDP sum
            print(f"\n=== RDP CONSISTENCY TEST RESULTS ===")
            print(f"Staff RDP Count: {staff_rdp_count}")
            print(f"Product RDP Sum: {product_rdp_sum}")
            print(f"Product 1 RDP: {product_breakdown[0].get('rdp_count', 0)}")
            print(f"Product 2 RDP: {product_breakdown[1].get('rdp_count', 0)}")
            print(f"Total RDP (overall): {summary.get('total_rdp', 0)}")
            
            # The fix ensures that when same customer deposits to multiple products,
            # they are only counted as 1 RDP (not once per product)
            assert staff_rdp_count == 1, f"Staff RDP count should be 1, got {staff_rdp_count}"
            
            # Product RDP sum should match staff RDP count
            assert product_rdp_sum == staff_rdp_count, \
                f"Product RDP sum ({product_rdp_sum}) should equal Staff RDP count ({staff_rdp_count})"
            
            print(f"✅ RDP CONSISTENCY TEST PASSED!")
            
        finally:
            # Restore original function
            ds_module.get_db = original_get_db
    
    @pytest.mark.asyncio
    async def test_ndp_count_consistency_new_customer_multiple_products(self, test_db):
        """
        Test NDP consistency: When a NEW customer deposits to 2 products on same day:
        - Staff NDP count should be 1 (not 2)
        - Sum of product NDPs should also be 1 (not 2)
        """
        db = test_db
        
        # Clean existing data
        await db.omset_records.delete_many({})
        
        # Create test data for a brand new customer (first time depositing)
        staff_id = str(uuid.uuid4())
        product1_id = str(uuid.uuid4())
        product2_id = str(uuid.uuid4())
        customer_id = 'NEW-CUST-001'
        customer_id_normalized = normalize_customer_id(customer_id)
        test_date = '2025-01-20'
        
        # Create staff
        await db.users.delete_many({})
        await db.users.insert_one({
            'id': staff_id,
            'name': 'Test Staff NDP',
            'email': 'testndp@test.com',
            'role': 'staff',
            'status': 'active'
        })
        
        # Create products
        await db.products.delete_many({})
        await db.products.insert_many([
            {'id': product1_id, 'name': 'Product NDP 1', 'status': 'active'},
            {'id': product2_id, 'name': 'Product NDP 2', 'status': 'active'}
        ])
        
        # NEW customer deposits to both products on the same day (their first deposits ever)
        records = [
            {
                'id': str(uuid.uuid4()),
                'product_id': product1_id,
                'product_name': 'Product NDP 1',
                'staff_id': staff_id,
                'staff_name': 'Test Staff NDP',
                'record_date': test_date,
                'customer_name': 'New Customer',
                'customer_id': customer_id,
                'customer_id_normalized': customer_id_normalized,
                'nominal': 250000,
                'depo_kelipatan': 1.0,
                'depo_total': 250000,
                'keterangan': None,
                'customer_type': 'NDP',
                'created_at': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'product_id': product2_id,
                'product_name': 'Product NDP 2',
                'staff_id': staff_id,
                'staff_name': 'Test Staff NDP',
                'record_date': test_date,
                'customer_name': 'New Customer',
                'customer_id': customer_id,
                'customer_id_normalized': customer_id_normalized,
                'nominal': 150000,
                'depo_kelipatan': 1.0,
                'depo_total': 150000,
                'keterangan': None,
                'customer_type': 'NDP',
                'created_at': datetime.now().isoformat()
            }
        ]
        await db.omset_records.insert_many(records)
        
        # Monkey-patch get_db
        import routes.daily_summary as ds_module
        original_get_db = ds_module.get_db
        ds_module.get_db = lambda: db
        
        try:
            summary = await generate_daily_summary(test_date)
            
            assert summary is not None
            
            staff_breakdown = summary.get('staff_breakdown', [])
            assert len(staff_breakdown) == 1
            
            staff_ndp_count = staff_breakdown[0].get('ndp_count', 0)
            
            product_breakdown = summary.get('product_breakdown', [])
            product_ndp_sum = sum(p.get('ndp_count', 0) for p in product_breakdown)
            
            print(f"\n=== NDP CONSISTENCY TEST RESULTS ===")
            print(f"Staff NDP Count: {staff_ndp_count}")
            print(f"Product NDP Sum: {product_ndp_sum}")
            
            # New customer should be counted as 1 NDP, not 2
            assert staff_ndp_count == 1, f"Staff NDP count should be 1, got {staff_ndp_count}"
            assert product_ndp_sum == staff_ndp_count, \
                f"Product NDP sum ({product_ndp_sum}) should equal Staff NDP count ({staff_ndp_count})"
            
            print(f"✅ NDP CONSISTENCY TEST PASSED!")
            
        finally:
            ds_module.get_db = original_get_db
    
    @pytest.mark.asyncio
    async def test_multiple_staff_rdp_isolation(self, test_db):
        """
        Test that RDP counting is isolated per staff:
        - Staff A's customer depositing to multiple products counts as 1 RDP for Staff A
        - Staff B's different customer also counts as 1 RDP for Staff B
        - Total should be 2 (one per staff)
        """
        db = test_db
        
        # Clean existing data
        await db.omset_records.delete_many({})
        await db.users.delete_many({})
        await db.products.delete_many({})
        
        # Setup 2 staff, 2 products, 2 customers
        staff_a_id = str(uuid.uuid4())
        staff_b_id = str(uuid.uuid4())
        product1_id = str(uuid.uuid4())
        product2_id = str(uuid.uuid4())
        
        await db.users.insert_many([
            {'id': staff_a_id, 'name': 'Staff A', 'email': 'a@test.com', 'role': 'staff', 'status': 'active'},
            {'id': staff_b_id, 'name': 'Staff B', 'email': 'b@test.com', 'role': 'staff', 'status': 'active'}
        ])
        
        await db.products.insert_many([
            {'id': product1_id, 'name': 'Product 1', 'status': 'active'},
            {'id': product2_id, 'name': 'Product 2', 'status': 'active'}
        ])
        
        test_date = '2025-01-25'
        
        # Historical records to make customers RDP
        historical = [
            {
                'id': str(uuid.uuid4()),
                'product_id': product1_id,
                'product_name': 'Product 1',
                'staff_id': staff_a_id,
                'staff_name': 'Staff A',
                'record_date': '2025-01-01',
                'customer_name': 'Customer A',
                'customer_id': 'CUST-A',
                'customer_id_normalized': 'cust-a',
                'nominal': 100000,
                'depo_kelipatan': 1.0,
                'depo_total': 100000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            },
            {
                'id': str(uuid.uuid4()),
                'product_id': product1_id,
                'product_name': 'Product 1',
                'staff_id': staff_b_id,
                'staff_name': 'Staff B',
                'record_date': '2025-01-01',
                'customer_name': 'Customer B',
                'customer_id': 'CUST-B',
                'customer_id_normalized': 'cust-b',
                'nominal': 100000,
                'depo_kelipatan': 1.0,
                'depo_total': 100000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            }
        ]
        await db.omset_records.insert_many(historical)
        
        # Today's records: Each customer deposits to 2 products
        today_records = [
            # Staff A's customer deposits to Product 1
            {
                'id': str(uuid.uuid4()),
                'product_id': product1_id,
                'product_name': 'Product 1',
                'staff_id': staff_a_id,
                'staff_name': 'Staff A',
                'record_date': test_date,
                'customer_name': 'Customer A',
                'customer_id': 'CUST-A',
                'customer_id_normalized': 'cust-a',
                'nominal': 200000,
                'depo_kelipatan': 1.0,
                'depo_total': 200000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            },
            # Staff A's customer deposits to Product 2
            {
                'id': str(uuid.uuid4()),
                'product_id': product2_id,
                'product_name': 'Product 2',
                'staff_id': staff_a_id,
                'staff_name': 'Staff A',
                'record_date': test_date,
                'customer_name': 'Customer A',
                'customer_id': 'CUST-A',
                'customer_id_normalized': 'cust-a',
                'nominal': 150000,
                'depo_kelipatan': 1.0,
                'depo_total': 150000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            },
            # Staff B's customer deposits to Product 1
            {
                'id': str(uuid.uuid4()),
                'product_id': product1_id,
                'product_name': 'Product 1',
                'staff_id': staff_b_id,
                'staff_name': 'Staff B',
                'record_date': test_date,
                'customer_name': 'Customer B',
                'customer_id': 'CUST-B',
                'customer_id_normalized': 'cust-b',
                'nominal': 300000,
                'depo_kelipatan': 1.0,
                'depo_total': 300000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            },
            # Staff B's customer deposits to Product 2
            {
                'id': str(uuid.uuid4()),
                'product_id': product2_id,
                'product_name': 'Product 2',
                'staff_id': staff_b_id,
                'staff_name': 'Staff B',
                'record_date': test_date,
                'customer_name': 'Customer B',
                'customer_id': 'CUST-B',
                'customer_id_normalized': 'cust-b',
                'nominal': 250000,
                'depo_kelipatan': 1.0,
                'depo_total': 250000,
                'keterangan': None,
                'created_at': datetime.now().isoformat()
            }
        ]
        await db.omset_records.insert_many(today_records)
        
        # Generate summary
        import routes.daily_summary as ds_module
        original_get_db = ds_module.get_db
        ds_module.get_db = lambda: db
        
        try:
            summary = await generate_daily_summary(test_date)
            
            assert summary is not None
            
            staff_breakdown = summary.get('staff_breakdown', [])
            assert len(staff_breakdown) == 2, "Should have 2 staff members"
            
            # Each staff should have 1 RDP (not 2)
            for staff in staff_breakdown:
                assert staff.get('rdp_count', 0) == 1, \
                    f"Staff {staff.get('staff_name')} should have 1 RDP, got {staff.get('rdp_count')}"
            
            # Total staff RDP sum
            staff_rdp_total = sum(s.get('rdp_count', 0) for s in staff_breakdown)
            
            # Product RDP sum
            product_breakdown = summary.get('product_breakdown', [])
            product_rdp_total = sum(p.get('rdp_count', 0) for p in product_breakdown)
            
            print(f"\n=== MULTI-STAFF RDP TEST RESULTS ===")
            print(f"Staff A RDP: {[s.get('rdp_count') for s in staff_breakdown if 'A' in s.get('staff_name', '')][0]}")
            print(f"Staff B RDP: {[s.get('rdp_count') for s in staff_breakdown if 'B' in s.get('staff_name', '')][0]}")
            print(f"Total Staff RDP: {staff_rdp_total}")
            print(f"Total Product RDP: {product_rdp_total}")
            
            assert staff_rdp_total == 2, f"Total staff RDP should be 2, got {staff_rdp_total}"
            assert product_rdp_total == staff_rdp_total, \
                f"Product RDP ({product_rdp_total}) should match Staff RDP ({staff_rdp_total})"
            
            print(f"✅ MULTI-STAFF RDP TEST PASSED!")
            
        finally:
            ds_module.get_db = original_get_db


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
