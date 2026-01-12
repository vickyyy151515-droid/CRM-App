import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def fix_old_requests():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Find all requests without record_ids field
    old_requests = await db.download_requests.find(
        {'record_ids': {'$exists': False}}
    ).to_list(1000)
    
    print(f"Found {len(old_requests)} old requests to update")
    
    for request in old_requests:
        # Set default values for missing fields
        await db.download_requests.update_one(
            {'id': request['id']},
            {'$set': {
                'record_ids': [],
                'record_count': 0
            }}
        )
        print(f"Updated request {request['id']}")
    
    print("All old requests updated!")
    client.close()

if __name__ == '__main__':
    asyncio.run(fix_old_requests())
