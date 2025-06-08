# File: services/reporting_service.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class ReportingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_daily_sales_report(self, date: Optional[datetime] = None) -> Dict:
        """Generate daily sales report"""
        if not date:
            date = datetime.utcnow()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        pipeline = [
            {"$match": {"created_at": {"$gte": start_of_day, "$lt": end_of_day}}},
            {"$group": {
                "_id": None,
                "total_sales": {"$sum": "$final_amount"},
                "total_transactions": {"$sum": 1},
                "cash_sales": {"$sum": {"$cond": [{"$eq": ["$payment_method", "cash"]}, "$final_amount", 0]}},
                "mpesa_sales": {"$sum": {"$cond": [{"$eq": ["$payment_method", "mpesa"]}, "$final_amount", 0]}},
                "total_discount": {"$sum": "$discount_amount"},
                "total_items_sold": {"$sum": {"$sum": "$items.quantity"}}
            }}
        ]
        
        result = await self.db.sales.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "date": start_of_day,
                "total_sales": 0,
                "total_transactions": 0,
                "cash_sales": 0,
                "mpesa_sales": 0,
                "total_discount": 0,
                "total_items_sold": 0,
                "top_selling_items": []
            }
        
        report = result[0]
        report["date"] = start_of_day
        del report["_id"]
        
        # Get top selling items for the day
        top_items_pipeline = [
            {"$match": {"created_at": {"$gte": start_of_day, "$lt": end_of_day}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.item_id",
                "item_name": {"$first": "$items.item_name"},
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": "$items.total_price"}
            }},
            {"$sort": {"total_quantity": -1}},
            {"$limit": 5}
        ]
        
        top_items = await self.db.sales.aggregate(top_items_pipeline).to_list(5)
        report["top_selling_items"] = [
            {**item, "_id": str(item["_id"])} for item in top_items
        ]
        
        return report
    
    async def get_weekly_sales_report(self, start_date: Optional[datetime] = None) -> Dict:
        """Generate weekly sales report"""
        if not start_date:
            today = datetime.utcnow()
            start_date = today - timedelta(days=today.weekday())  # Start of current week
        
        start_of_week = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)
        
        daily_reports = []
        total_weekly_sales = 0
        
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            daily_report = await self.get_daily_sales_report(day)
            daily_reports.append(daily_report)
            total_weekly_sales += daily_report["total_sales"]
        
        return {
            "week_start": start_of_week,
            "week_end": end_of_week,
            "daily_reports": daily_reports,
            "total_weekly_sales": total_weekly_sales,
            "average_daily_sales": total_weekly_sales / 7 if total_weekly_sales > 0 else 0
        }
    
    async def get_operator_performance(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get operator performance report"""
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$lookup": {
                "from": "users",
                "localField": "processed_by",
                "foreignField": "_id",
                "as": "operator"
            }},
            {"$unwind": "$operator"},
            {"$group": {
                "_id": "$processed_by",
                "operator_name": {"$first": "$operator.full_name"},
                "total_sales": {"$sum": "$final_amount"},
                "total_transactions": {"$sum": 1},
                "average_transaction": {"$avg": "$final_amount"},
                "total_items_sold": {"$sum": {"$sum": "$items.quantity"}}
            }},
            {"$sort": {"total_sales": -1}}
        ]
        
        operators = await self.db.sales.aggregate(pipeline).to_list(None)
        
        for operator in operators:
            operator["operator_id"] = str(operator["_id"])
            operator["period_start"] = start_date
            operator["period_end"] = end_date
            del operator["_id"]
        
        return operators
    
    async def get_inventory_report(self) -> Dict:
        """Generate inventory status report"""
        pipeline = [
            {"$group": {
                "_id": None,
                "total_items": {"$sum": 1},
                "total_stock_value": {"$sum": {"$multiply": ["$current_stock", "$selling_price"]}},
                "low_stock_items": {"$sum": {"$cond": [{"$lte": ["$current_stock", "$alert_threshold"]}, 1, 0]}},
                "out_of_stock_items": {"$sum": {"$cond": [{"$eq": ["$current_stock", 0]}, 1, 0]}}
            }}
        ]
        
        result = await self.db.items.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "total_items": 0,
                "total_stock_value": 0,
                "low_stock_items": 0,
                "out_of_stock_items": 0,
                "category_breakdown": []
            }
        
        report = result[0]
        del report["_id"]
        
        # Get category breakdown
        category_pipeline = [
            {"$group": {
                "_id": "$category",
                "item_count": {"$sum": 1},
                "total_stock": {"$sum": "$current_stock"},
                "category_value": {"$sum": {"$multiply": ["$current_stock", "$selling_price"]}}
            }},
            {"$sort": {"category_value": -1}}
        ]
        
        categories = await self.db.items.aggregate(category_pipeline).to_list(None)
        report["category_breakdown"] = categories
        
        return report
    
    async def get_expense_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate expense report for a given period"""
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": "$category",
                "total_amount": {"$sum": "$amount"},
                "expense_count": {"$sum": 1}
            }},
            {"$sort": {"total_amount": -1}}
        ]
        
        expenses = await self.db.expenses.aggregate(pipeline).to_list(None)
        
        total_expenses = sum(expense["total_amount"] for expense in expenses)
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_expenses": total_expenses,
            "category_breakdown": [
                {
                    "category": expense["_id"],
                    "total_amount": expense["total_amount"],
                    "expense_count": expense["expense_count"]
                } for expense in expenses
            ]
        }
    
    async def get_customer_feedback_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate customer feedback report for a given period"""
        pipeline = [
            {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": "$feedback_type",
                "count": {"$sum": 1},
                "details": {"$push": {
                    "description": "$description",
                    "customer_name": "$customer_name",
                    "status": "$status",
                    "created_at": "$created_at"
                }}
            }},
            {"$sort": {"count": -1}}
        ]
        
        feedback = await self.db.customer_feedback.aggregate(pipeline).to_list(None)
        
        total_feedback = sum(item["count"] for item in feedback)
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_feedback": total_feedback,
            "feedback_breakdown": [
                {
                    "type": item["_id"],
                    "count": item["count"],
                    "details": item["details"]
                } for item in feedback
            ]
        }
