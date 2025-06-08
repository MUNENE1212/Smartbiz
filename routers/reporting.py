# File: routers/reporting.py
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from services.reporting_service import ReportingService
from models.database import get_database
from routers.auth import get_current_user_from_cookie, get_manager_user_from_cookie
from utils.helpers import DateHelper

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/sales/daily")
async def get_daily_sales_report(
    date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    reporting_service = ReportingService(db)
    return await reporting_service.get_daily_sales_report(date)

@router.get("/sales/weekly")
async def get_weekly_sales_report(
    start_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    reporting_service = ReportingService(db)
    return await reporting_service.get_weekly_sales_report(start_date)

@router.get("/operator-performance")
async def get_operator_performance(
    start_date: datetime,
    end_date: datetime,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    reporting_service = ReportingService(db)
    return await reporting_service.get_operator_performance(start_date, end_date)

@router.get("/inventory")
async def get_inventory_report(
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    reporting_service = ReportingService(db)
    return await reporting_service.get_inventory_report()

@router.get("/expenses")
async def get_expense_report(
    start_date: datetime,
    end_date: datetime,
    current_user: dict = Depends(get_manager_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    reporting_service = ReportingService(db)
    return await reporting_service.get_expense_report(start_date, end_date)
