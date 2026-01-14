# Product Management Routes

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime
import uuid
from .deps import User, get_db, get_current_user, get_admin_user, get_jakarta_now

router = APIRouter(tags=["Products"])

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=lambda: get_jakarta_now())

class ProductCreate(BaseModel):
    name: str

@router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, user: User = Depends(get_admin_user)):
    """Create a new product (Admin only)"""
    db = get_db()
    existing = await db.products.find_one({'name': product_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Product with this name already exists")
    
    product = Product(name=product_data.name)
    doc = product.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.products.insert_one(doc)
    return product

@router.get("/products", response_model=List[Product])
async def get_products(user: User = Depends(get_current_user)):
    """Get all products"""
    db = get_db()
    products = await db.products.find({}, {'_id': 0}).sort('name', 1).to_list(1000)
    
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    
    return products

@router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: User = Depends(get_admin_user)):
    """Delete a product (Admin only)"""
    db = get_db()
    product = await db.products.find_one({'id': product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    databases_count = await db.databases.count_documents({'product_id': product_id})
    if databases_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete product with {databases_count} associated databases")
    
    await db.products.delete_one({'id': product_id})
    return {'message': 'Product deleted successfully'}
