# File: utils/helpers.py
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import calendar

class DateHelper:
    @staticmethod
    def get_week_range(date: Optional[datetime] = None) -> tuple:
        """Get start and end of week for given date"""
        if not date:
            date = datetime.utcnow()
        
        start_of_week = date - timedelta(days=date.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return start_of_week, end_of_week
    
    @staticmethod
    def get_month_range(date: Optional[datetime] = None) -> tuple:
        """Get start and end of month for given date"""
        if not date:
            date = datetime.utcnow()
        
        start_of_month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(date.year, date.month)[1]
        end_of_month = date.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        
        return start_of_month, end_of_month

class ProfitCalculator:
    @staticmethod
    def calculate_item_profit(selling_price: float, buying_price: float, quantity: int) -> Dict:
        """Calculate profit for an item"""
        total_cost = buying_price * quantity
        total_revenue = selling_price * quantity
        profit = total_revenue - total_cost
        profit_margin = (profit / total_revenue) * 100 if total_revenue > 0 else 0
        
        return {
            "total_cost": total_cost,
            "total_revenue": total_revenue,
            "profit": profit,
            "profit_margin": profit_margin
        }
    
    @staticmethod
    def calculate_daily_profit(sales_data: List[Dict], expenses: List[Dict]) -> Dict:
        """Calculate daily profit from sales and expenses"""
        total_revenue = sum(sale.get("final_amount", 0) for sale in sales_data)
        total_expenses = sum(expense.get("amount", 0) for expense in expenses)
        
        # Note: This is a simplified calculation
        # For accurate profit, you'd need cost of goods sold
        gross_profit = total_revenue  # Simplified - needs actual COGS calculation
        net_profit = gross_profit - total_expenses
        
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "profit_margin": (net_profit / total_revenue) * 100 if total_revenue > 0 else 0
        }
