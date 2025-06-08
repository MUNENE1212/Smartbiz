from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
import logging
from bson import ObjectId

from models.schemas import ItemCreate, ItemUpdate, ItemSupplierPriceBase, ItemSupplierPrice
from models.database import get_database
from routers.auth import get_current_user_from_cookie, get_manager_user_from_cookie

router = APIRouter(prefix="/inventory", tags=["inventory"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_objectid(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, ObjectId):
                item[key] = str(value)
            elif isinstance(value, dict):
                item[key] = convert_objectid(value)
            elif isinstance(value, list):
                item[key] = [convert_objectid(v) if isinstance(v, (dict, ObjectId)) else v for v in value]
    return item

@router.post("/items")
async def create_item(
    item: ItemCreate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        existing_item = await db.items.find_one({"custom_id": item.custom_id})
        if existing_item:
            raise HTTPException(status_code=400, detail="Item with this custom ID already exists")
        
        item_dict = item.dict(exclude_unset=True)
        item_dict["current_stock"] = item_dict.get("current_stock", 0)  # Use provided value or 0
        item_dict["created_at"] = datetime.utcnow()
        item_dict["created_by"] = str(current_user["_id"])
        item_dict.setdefault("supplier_prices", [])  # Initialize as empty list for multiple suppliers
        
        result = await db.items.insert_one(item_dict)
        return {"message": "Item created successfully", "custom_id": item.custom_id}
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/items/{custom_id}")
async def update_item(
    custom_id: str,
    item_update: ItemUpdate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        existing_item = await db.items.find_one({"custom_id": custom_id})
        if not existing_item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        update_data = {k: v for k, v in item_update.dict(exclude_unset=True).items() if v is not None}
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            update_data.setdefault("supplier_prices", existing_item.get("supplier_prices", []))
            
            result = await db.items.update_one(
                {"custom_id": custom_id},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=400, detail="No changes made")
        
        return {"message": "Item updated successfully"}
    except Exception as e:
        logger.error(f"Error updating item {custom_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/items")
async def get_items(
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        query = {}
        
        if category:
            query["category"] = {"$regex": category, "$options": "i"}
        
        if low_stock_only:
            query["$expr"] = {"$lte": ["$current_stock", "$alert_threshold"]}
        
        items = []
        async for item in db.items.find(query).sort("name", 1):
            item = convert_objectid(item)
            item["created_by"] = str(item["created_by"])
            item["is_low_stock"] = item["current_stock"] <= item["alert_threshold"]
            item["is_out_of_stock"] = item["current_stock"] == 0
            
            if item.get("supplier_prices") and len(item["supplier_prices"]) > 0:
                # Keep all supplier prices, no need to pick the latest for display
                pass
            else:
                item["latest_buying_price"] = item.get("buying_price")
                item["latest_supplier_name"] = None
            
            items.append(item)
        
        return items
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/items/{custom_id}")
async def get_item(
    custom_id: str,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        item = await db.items.find_one({"custom_id": custom_id})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item = convert_objectid(item)
        item["created_by"] = str(item["created_by"])
        item["is_low_stock"] = item["current_stock"] <= item["alert_threshold"]
        item["is_out_of_stock"] = item["current_stock"] == 0
        
        if item.get("supplier_prices") and len(item["supplier_prices"]) > 0:
            pass  # Return all supplier prices
        else:
            item["latest_buying_price"] = item.get("buying_price")
            item["latest_supplier_name"] = None
        
        return item
    except Exception as e:
        logger.error(f"Error fetching item {custom_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/items/{custom_id}/supplier-price")
async def add_supplier_price(
    custom_id: str,
    supplier_price: ItemSupplierPriceBase,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        item = await db.items.find_one({"custom_id": custom_id})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        supplier = await db.suppliers.find_one({"custom_id": supplier_price.supplier_id})
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Add new supplier price without removing existing ones
        supplier_price_dict = supplier_price.dict()
        supplier_price_dict["supplier_name"] = supplier["name"]
        supplier_price_dict["last_updated"] = datetime.utcnow()
        
        await db.items.update_one(
            {"custom_id": custom_id},
            {"$push": {"supplier_prices": supplier_price_dict}}
        )
        
        return {"message": "Supplier price added successfully"}
    except Exception as e:
        logger.error(f"Error adding supplier price for {custom_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/items/{custom_id}/stock-adjustment")
async def adjust_stock(
    custom_id: str,
    adjustment: dict,  # {"type": "increase|decrease", "quantity": int, "reason": str}
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        item = await db.items.find_one({"custom_id": custom_id})
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        adjustment_type = adjustment.get("type")
        quantity = int(adjustment.get("quantity", 0))
        reason = adjustment.get("reason", "Manual adjustment")
        
        if adjustment_type not in ["increase", "decrease"]:
            raise HTTPException(status_code=400, detail="Invalid adjustment type")
        
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        current_stock = item["current_stock"]
        if adjustment_type == "increase":
            new_stock = current_stock + quantity
        else:
            new_stock = max(0, current_stock - quantity)
        
        await db.items.update_one(
            {"custom_id": custom_id},
            {"$set": {"current_stock": new_stock, "updated_at": datetime.utcnow()}}
        )
        
        await db.stock_adjustments.insert_one({
            "item_id": custom_id,
            "item_name": item["name"],
            "adjustment_type": adjustment_type,
            "quantity": quantity,
            "previous_stock": current_stock,
            "new_stock": new_stock,
            "reason": reason,
            "adjusted_by": str(current_user["_id"]),
            "created_at": datetime.utcnow()
        })
        
        return {
            "message": "Stock adjusted successfully",
            "previous_stock": current_stock,
            "new_stock": new_stock
        }
    except Exception as e:
        logger.error(f"Error adjusting stock for {custom_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/categories")
async def get_categories(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    try:
        pipeline = [
            {"$group": {"_id": "$category", "item_count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        categories = []
        async for category in db.items.aggregate(pipeline):
            categories.append({
                "name": category["_id"],
                "item_count": category["item_count"]
            })
        
        return categories
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")