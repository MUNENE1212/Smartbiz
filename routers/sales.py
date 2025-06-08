from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict
from bson import ObjectId
from datetime import datetime

from models.schemas import SaleCreate, SaleInDB
from models.database import get_database
from routers.auth import get_current_user_from_cookie
from utils.validators import Validators

router = APIRouter(prefix="/sales", tags=["sales"])

@router.get("/items-for-sale")
async def get_items_for_sale(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    items = []
    async for item in db.items.find({"current_stock": {"$gt": 0}}):
        items.append({
            "id": str(item["_id"]),
            "name": item["name"],
            "selling_price": item["selling_price"]
        })
    return items

@router.post("")
async def create_sale(
    sale: SaleCreate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Validate MPESA reference if payment method is MPESA
    if sale.payment_method == "mpesa" and sale.mpesa_reference:
        if not Validators.validate_mpesa_reference(sale.mpesa_reference):
            raise HTTPException(status_code=400, detail="Invalid MPESA reference format")

    # Validate and update stock for each item
    total_amount = 0
    sale_items = []
    for item in sale.items:
        if not ObjectId.is_valid(item["item_id"]):
            raise HTTPException(status_code=400, detail=f"Invalid item ID: {item['item_id']}")

        db_item = await db.items.find_one({"_id": ObjectId(item["item_id"])})
        if not db_item:
            raise HTTPException(status_code=404, detail=f"Item not found: {item['item_id']}")
        
        if db_item["current_stock"] < item["quantity"]:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {db_item['name']}")

        # Validate unit price matches current selling price
        if item["unit_price"] != db_item["selling_price"]:
            raise HTTPException(status_code=400, detail=f"Price mismatch for {db_item['name']}")

        total_price = item["quantity"] * item["unit_price"]
        total_amount += total_price
        
        sale_items.append({
            "item_id": ObjectId(item["item_id"]),
            "item_name": db_item["name"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "total_price": total_price
        })

    # Calculate discounts and final amount
    discount_amount = total_amount * (sale.discount_percentage / 100)
    final_amount = total_amount - discount_amount

    # Only managers can apply discounts
    if sale.discount_percentage > 0 and current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Only managers can apply discounts")

    # Update stock levels
    for item in sale_items:
        await db.items.update_one(
            {"_id": item["item_id"]},
            {
                "$inc": {"current_stock": -item["quantity"]},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    # Create sale record
    sale_dict = {
        "items": sale_items,
        "total_amount": total_amount,
        "discount_percentage": sale.discount_percentage,
        "discount_amount": discount_amount,
        "final_amount": final_amount,
        "payment_method": sale.payment_method,
        "mpesa_reference": sale.mpesa_reference,
        "customer_name": sale.customer_name,
        "created_at": datetime.utcnow(),
        "processed_by": current_user["_id"]
    }

    result = await db.sales.insert_one(sale_dict)
    
    # Calculate change (if cash payment)
    change = None
    if sale.payment_method == "cash" and "amount_paid" in sale.dict():
        amount_paid = sale.dict().get("amount_paid", final_amount)
        if amount_paid < final_amount:
            raise HTTPException(status_code=400, detail="Amount paid is less than final amount")
        change = amount_paid - final_amount

    return {
        "message": "Sale recorded successfully",
        "sale_id": str(result.inserted_id),
        "change": change if change is not None else None
    }

@router.get("/{sale_id}")
async def get_sale(
    sale_id: str,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not ObjectId.is_valid(sale_id):
        raise HTTPException(status_code=400, detail="Invalid sale ID")

    sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    sale["_id"] = str(sale["_id"])
    sale["processed_by"] = str(sale["processed_by"])
    for item in sale["items"]:
        item["item_id"] = str(item["item_id"])

    return sale

@router.get("/history")
async def get_sales_history(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    sales = []
    async for sale in db.sales.find():
        sale["_id"] = str(sale["_id"])
        sale["processed_by"] = str(sale["processed_by"])
        for item in sale["items"]:
            item["item_id"] = str(item["item_id"])
        sales.append(sale)
    return sales