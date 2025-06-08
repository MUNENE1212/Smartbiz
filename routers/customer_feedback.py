# File: routers/customer_feedback.py
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from models.schemas import CustomerFeedbackCreate, CustomerFeedbackInDB
from models.database import get_database
from routers.auth import get_current_user_from_cookie, get_manager_user_from_cookie
from utils.validators import Validators

router = APIRouter(prefix="/feedback", tags=["customer_feedback"])

@router.post("")
async def create_feedback(
    feedback: CustomerFeedbackCreate,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Create a new customer feedback entry"""
    # Sanitize input
    feedback_dict = Validators.sanitize_input(feedback.dict())
    
    # Validate feedback type (already handled by schema regex, but reinforcing)
    if feedback_dict["feedback_type"] not in ["requirement", "complaint", "recommendation"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    # Prepare feedback document
    feedback_dict["created_at"] = datetime.utcnow()
    feedback_dict["recorded_by"] = current_user["_id"]
    feedback_dict["status"] = "open"

    result = await db.customer_feedback.insert_one(feedback_dict)
    
    # Log the activity (for future auditing)
    await db.activity_logs.insert_one({
        "action": "create_feedback",
        "feedback_id": result.inserted_id,
        "user_id": current_user["_id"],
        "user_name": current_user["full_name"],
        "created_at": datetime.utcnow()
    })

    return {"message": "Feedback recorded successfully", "feedback_id": str(result.inserted_id)}

@router.get("")
async def get_feedbacks(
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Retrieve all customer feedback entries with optional filters"""
    query = {}
    if feedback_type:
        if feedback_type not in ["requirement", "complaint", "recommendation"]:
            raise HTTPException(status_code=400, detail="Invalid feedback type")
        query["feedback_type"] = feedback_type
    if status:
        if status not in ["open", "in_progress", "resolved"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        query["status"] = status

    feedbacks = []
    async for feedback in db.customer_feedback.find(query).sort("created_at", -1):
        feedback["_id"] = str(feedback["_id"])
        feedback["recorded_by"] = str(feedback["recorded_by"])
        feedbacks.append(feedback)

    return feedbacks

@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: str,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Retrieve a specific feedback entry by ID"""
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(status_code=400, detail="Invalid feedback ID")

    feedback = await db.customer_feedback.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback["_id"] = str(feedback["_id"])
    feedback["recorded_by"] = str(feedback["recorded_by"])
    return feedback

@router.put("/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    feedback_update: CustomerFeedbackCreate,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a feedback entry (manager only)"""
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(status_code=400, detail="Invalid feedback ID")

    existing_feedback = await db.customer_feedback.find_one({"_id": ObjectId(feedback_id)})
    if not existing_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Sanitize input
    update_data = Validators.sanitize_input(feedback_update.dict(exclude_unset=True))
    
    # Validate feedback type
    if "feedback_type" in update_data and update_data["feedback_type"] not in ["requirement", "complaint", "recommendation"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    # Allow status update (manager only)
    if "status" in feedback_update.dict(exclude_unset=True):
        if feedback_update.status not in ["open", "in_progress", "resolved"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        update_data["status"] = feedback_update.status

    if not update_data:
        raise HTTPException(status_code=400, detail="No changes provided")

    update_data["updated_at"] = datetime.utcnow()

    result = await db.customer_feedback.update_one(
        {"_id": ObjectId(feedback_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes made")

    # Log the activity
    await db.activity_logs.insert_one({
        "action": "update_feedback",
        "feedback_id": ObjectId(feedback_id),
        "user_id": current_user["_id"],
        "user_name": current_user["full_name"],
        "changes": update_data,
        "created_at": datetime.utcnow()
    })

    return {"message": "Feedback updated successfully"}

@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a feedback entry (manager only)"""
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(status_code=400, detail="Invalid feedback ID")

    feedback = await db.customer_feedback.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    await db.customer_feedback.delete_one({"_id": ObjectId(feedback_id)})

    # Log the activity
    await db.activity_logs.insert_one({
        "action": "delete_feedback",
        "feedback_id": ObjectId(feedback_id),
        "user_id": current_user["_id"],
        "user_name": current_user["full_name"],
        "created_at": datetime.utcnow()
    })

    return {"message": "Feedback deleted successfully"}
