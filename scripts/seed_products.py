import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def seed_products():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    products = [
        {'id': 'prod-liga2000', 'name': 'LIGA2000', 'created_at': '2025-01-01T00:00:00+00:00'},
        {'id': 'prod-istana2000', 'name': 'ISTANA2000', 'created_at': '2025-01-01T00:00:00+00:00'},
        {'id': 'prod-pucuk33', 'name': 'PUCUK33', 'created_at': '2025-01-01T00:00:00+00:00'}
    ]
    
    for product in products:
        existing = await db.products.find_one({'name': product['name']})
        if not existing:
            await db.products.insert_one(product)
            print(f"Created product: {product['name']}")
        else:
            print(f"Product already exists: {product['name']}")
    
    client.close()

if __name__ == '__main__':
    asyncio.run(seed_products())
