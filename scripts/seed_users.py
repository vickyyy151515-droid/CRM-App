import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def seed_users():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Check if users already exist
    existing_admin = await db.users.find_one({'email': 'admin@crm.com'})
    existing_staff = await db.users.find_one({'email': 'staff@crm.com'})
    
    users_to_create = []
    
    if not existing_admin:
        admin_password = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
        users_to_create.append({
            'id': 'admin-user-1',
            'email': 'admin@crm.com',
            'name': 'Admin User',
            'role': 'admin',
            'password_hash': admin_password,
            'created_at': '2025-01-01T00:00:00+00:00'
        })
    
    if not existing_staff:
        staff_password = bcrypt.hashpw('staff123'.encode(), bcrypt.gensalt()).decode()
        users_to_create.append({
            'id': 'staff-user-1',
            'email': 'staff@crm.com',
            'name': 'Staff User',
            'role': 'staff',
            'password_hash': staff_password,
            'created_at': '2025-01-01T00:00:00+00:00'
        })
    
    if users_to_create:
        await db.users.insert_many(users_to_create)
        print(f"Created {len(users_to_create)} demo users")
    else:
        print("Demo users already exist")
    
    client.close()

if __name__ == '__main__':
    asyncio.run(seed_users())
