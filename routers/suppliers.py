from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime

from models.schemas import SupplierCreate, SupplierInDB
from models.database import get_database
from routers.auth import get_current_user_from_cookie, get_manager_user_from_cookie
from utils.validators import Validators

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

@router.post("")
async def create_supplier(
    supplier: SupplierCreate,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not Validators.validate_phone_number(supplier.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    if supplier.email and not Validators.validate_email(supplier.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    existing_supplier = await db.suppliers.find_one({
        "$or": [
            {"custom_id": supplier.custom_id},
            {"phone_number": supplier.phone_number}
        ]
    })
    if existing_supplier:
        raise HTTPException(status_code=400, detail="Supplier with this custom ID or phone number already exists")

    supplier_dict = supplier.dict()
    supplier_dict["created_at"] = datetime.utcnow()
    supplier_dict["created_by"] = str(current_user["_id"])
    supplier_dict["is_active"] = True

    result = await db.suppliers.insert_one(supplier_dict)
    return {"message": "Supplier created successfully", "custom_id": supplier.custom_id}

@router.get("")
async def get_suppliers(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database),
    active_only: bool = Query(True)
):
    query = {"is_active": True} if active_only else {}
    suppliers = []
    async for supplier in db.suppliers.find(query).sort("name", 1):
        supplier["_id"] = str(supplier["_id"])
        supplier["created_by"] = str(supplier["created_by"])
        suppliers.append(supplier)
    
    return suppliers

@router.get("/{custom_id}")
async def get_supplier(
    custom_id: str,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    supplier = await db.suppliers.find_one({"custom_id": custom_id})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier["_id"] = str(supplier["_id"])
    supplier["created_by"] = str(supplier["created_by"])
    return supplier

@router.put("/{custom_id}")
async def update_supplier(
    custom_id: str,
    supplier_update: SupplierCreate,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    existing_supplier = await db.suppliers.find_one({"custom_id": custom_id})
    if not existing_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    if not Validators.validate_phone_number(supplier_update.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")

    if supplier_update.email and not Validators.validate_email(supplier_update.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    duplicate_check = await db.suppliers.find_one({
        "$and": [
            {"custom_id": {"$ne": custom_id}},
            {"$or": [
                {"name": {"$regex": f"^{supplier_update.name}$", "$options": "i"}},
                {"phone_number": supplier_update.phone_number}
            ]}
        ]
    })
    if duplicate_check:
        raise HTTPException(status_code=400, detail="Supplier with this name or phone number already exists")

    update_data = {k: v for k, v in supplier_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    result = await db.suppliers.update_one(
        {"custom_id": custom_id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes made")

    return {"message": "Supplier updated successfully"}

@router.delete("/{custom_id}")
async def deactivate_supplier(
    custom_id: str,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    supplier = await db.suppliers.find_one({"custom_id": custom_id})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    await db.suppliers.update_one(
        {"custom_id": custom_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )

    return {"message": "Supplier deactivated successfully"}