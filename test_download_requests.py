#!/usr/bin/env python3
"""
Simple test script to verify the download requests endpoints work
"""
import asyncio
import sys
import os
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from routes.deps import set_database
from routes.records import get_download_requests, get_download_requests_stats
from routes.deps import User

async def test_endpoints():
    # Connect to MongoDB
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    database = client.crm_pro
    set_database(database)
    
    # Create a mock admin user
    admin_user = User(
        id="test-admin-id",
        email="admin@test.com", 
        name="Test Admin",
        role="admin",
        is_active=True
    )
    
    # Create a mock staff user
    staff_user = User(
        id="test-staff-id",
        email="staff@test.com",
        name="Test Staff", 
        role="staff",
        is_active=True
    )
    
    print("Testing download requests endpoints...")
    
    try:
        # Test 1: Get all download requests as admin
        print("\n1. Testing get_download_requests as admin...")
        requests = await get_download_requests(user=admin_user)
        print(f"   Found {len(requests)} download requests")
        
        # Test 2: Get download requests as staff (should only see own)
        print("\n2. Testing get_download_requests as staff...")
        staff_requests = await get_download_requests(user=staff_user)
        print(f"   Staff sees {len(staff_requests)} download requests")
        
        # Test 3: Get download requests with filters
        print("\n3. Testing get_download_requests with filters...")
        filtered_requests = await get_download_requests(
            status="approved",
            user=admin_user
        )
        print(f"   Found {len(filtered_requests)} approved requests")
        
        # Test 4: Get download request stats
        print("\n4. Testing get_download_requests_stats...")
        stats = await get_download_requests_stats(user=admin_user)
        print(f"   Stats: {stats['total_requests']} total, {stats['approved']} approved, {stats['pending']} pending")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_endpoints())