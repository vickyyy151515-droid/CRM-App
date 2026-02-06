"""
MongoDB Index Creation Script
Creates indexes for optimal query performance on CRM collections.

Run this script to create indexes:
    python create_indexes.py

Indexes are designed based on common query patterns:
- staff_id: Most queries filter by staff
- status: Filter by record status (available, assigned, invalid)
- record_date: Date-based filtering for reports
- product_id: Product filtering
- database_id: Database association
- customer_id_normalized: Customer lookup and deduplication
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os


async def create_indexes():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    print(f"Connecting to: {mongo_url}")
    print(f"Database: {db_name}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Define indexes for each collection
    indexes_config = {
        # ==================== OMSET RECORDS ====================
        'omset_records': [
            # Most common query: by staff and date
            {'keys': [('staff_id', 1), ('record_date', -1)], 'name': 'staff_date_idx'},
            # Product filtering
            {'keys': [('product_id', 1), ('record_date', -1)], 'name': 'product_date_idx'},
            # Customer lookup for NDP/RDP calculation
            {'keys': [('customer_id_normalized', 1), ('staff_id', 1)], 'name': 'customer_staff_idx'},
            # Date range queries
            {'keys': [('record_date', -1)], 'name': 'date_idx'},
        ],
        
        # ==================== CUSTOMER RECORDS (Normal DB) ====================
        'customer_records': [
            # Staff assignment queries
            {'keys': [('staff_id', 1), ('status', 1)], 'name': 'staff_status_idx'},
            # Database filtering
            {'keys': [('database_id', 1), ('status', 1)], 'name': 'database_status_idx'},
            # Customer reservation lookup
            {'keys': [('customer_id_normalized', 1), ('product_id', 1)], 'name': 'customer_product_idx'},
            # Status filtering
            {'keys': [('status', 1)], 'name': 'status_idx'},
        ],
        
        # ==================== BONANZA RECORDS ====================
        'bonanza_records': [
            # Staff assignment queries
            {'keys': [('staff_id', 1), ('status', 1)], 'name': 'staff_status_idx'},
            # Database filtering
            {'keys': [('database_id', 1), ('status', 1)], 'name': 'database_status_idx'},
            # Customer reservation lookup
            {'keys': [('customer_id_normalized', 1), ('product_id', 1)], 'name': 'customer_product_idx'},
            # Status filtering
            {'keys': [('status', 1)], 'name': 'status_idx'},
        ],
        
        # ==================== MEMBER WD RECORDS ====================
        'memberwd_records': [
            # Staff assignment queries
            {'keys': [('staff_id', 1), ('status', 1)], 'name': 'staff_status_idx'},
            # Batch filtering
            {'keys': [('batch_id', 1), ('status', 1)], 'name': 'batch_status_idx'},
            # Database filtering
            {'keys': [('database_id', 1), ('status', 1)], 'name': 'database_status_idx'},
            # Customer reservation lookup
            {'keys': [('customer_id_normalized', 1), ('product_id', 1)], 'name': 'customer_product_idx'},
            # Status filtering
            {'keys': [('status', 1)], 'name': 'status_idx'},
        ],
        
        # ==================== USERS ====================
        'users': [
            # Email lookup for login
            {'keys': [('email', 1)], 'name': 'email_idx', 'unique': True},
            # Role filtering
            {'keys': [('role', 1), ('status', 1)], 'name': 'role_status_idx'},
        ],
        
        # ==================== DATABASES ====================
        'databases': [
            # Product filtering
            {'keys': [('product_id', 1)], 'name': 'product_idx'},
        ],
        
        'bonanza_databases': [
            # Product filtering
            {'keys': [('product_id', 1)], 'name': 'product_idx'},
        ],
        
        'memberwd_databases': [
            # Product filtering
            {'keys': [('product_id', 1)], 'name': 'product_idx'},
        ],
        
        # ==================== DAILY SUMMARIES ====================
        'daily_summaries': [
            # Date lookup
            {'keys': [('date', -1)], 'name': 'date_idx', 'unique': True},
        ],
        
        # ==================== NOTIFICATIONS ====================
        'notifications': [
            # User notifications lookup
            {'keys': [('user_id', 1), ('read', 1), ('created_at', -1)], 'name': 'user_read_date_idx'},
        ],
        
        # ==================== ATTENDANCE ====================
        'attendance_records': [
            # Staff attendance lookup
            {'keys': [('staff_id', 1), ('date', -1)], 'name': 'staff_date_idx'},
            # Date range queries
            {'keys': [('date', -1)], 'name': 'date_idx'},
        ],
        
        # ==================== DOWNLOAD REQUESTS ====================
        'download_requests': [
            # Staff requests lookup
            {'keys': [('staff_id', 1), ('status', 1), ('created_at', -1)], 'name': 'staff_status_date_idx'},
            # Status filtering
            {'keys': [('status', 1), ('created_at', -1)], 'name': 'status_date_idx'},
        ],
    }
    
    print("\n=== CREATING INDEXES ===\n")
    
    total_created = 0
    total_skipped = 0
    
    for collection_name, indexes in indexes_config.items():
        collection = db[collection_name]
        existing_indexes = await collection.index_information()
        existing_names = set(existing_indexes.keys())
        
        print(f"{collection_name}:")
        
        for idx_config in indexes:
            idx_name = idx_config['name']
            
            if idx_name in existing_names:
                print(f"  ⏭️  {idx_name} (already exists)")
                total_skipped += 1
                continue
            
            try:
                # Build index options
                options = {'name': idx_name}
                if idx_config.get('unique'):
                    options['unique'] = True
                
                await collection.create_index(idx_config['keys'], **options)
                print(f"  ✅ {idx_name} created")
                total_created += 1
            except Exception as e:
                print(f"  ❌ {idx_name} failed: {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Indexes created: {total_created}")
    print(f"Indexes skipped (already exist): {total_skipped}")
    
    # Verify indexes were created
    print(f"\n=== VERIFICATION ===")
    for collection_name in indexes_config.keys():
        indexes = await db[collection_name].index_information()
        idx_count = len([k for k in indexes.keys() if k != '_id_'])
        print(f"  {collection_name}: {idx_count} custom indexes")
    
    client.close()
    print("\n✅ Index creation complete!")


if __name__ == "__main__":
    asyncio.run(create_indexes())
