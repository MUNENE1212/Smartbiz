# File: services/alert_service.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from .sms_service import SMSService, TwilioSMSService
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class AlertService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sms_service = SMSService()  # Default to Africa's Talking
        # self.sms_service = TwilioSMSService()  # Uncomment to use Twilio
        
    async def check_low_stock_alerts(self) -> List[dict]:
        """Check for items with low stock and return alert data"""
        low_stock_items = []
        
        async for item in self.db.items.find({"$expr": {"$lte": ["$current_stock", "$alert_threshold"]}}):
            low_stock_items.append({
                "item_id": str(item["_id"]),
                "name": item["name"],
                "current_stock": item["current_stock"],
                "alert_threshold": item["alert_threshold"],
                "category": item["category"]
            })
        
        return low_stock_items
    
    async def send_low_stock_alerts(self) -> dict:
        """Send SMS alerts to managers for low stock items"""
        low_stock_items = await self.check_low_stock_alerts()
        
        if not low_stock_items:
            return {"success": True, "message": "No low stock alerts"}
        
        # Get all manager phone numbers
        managers = []
        async for manager in self.db.users.find({"role": "manager", "is_active": True}):
            managers.append(manager["phone_number"])
        
        if not managers:
            return {"success": False, "error": "No active managers found"}
        
        # Prepare alert message
        item_list = []
        for item in low_stock_items:
            item_list.append(f"• {item['name']}: {item['current_stock']} left (Alert: {item['alert_threshold']})")
        
        message = f"🚨 LOW STOCK ALERT - SmartBiz Manager\n\n" \
                 f"The following items need restocking:\n\n" \
                 f"{'\\n'.join(item_list[:5])}" \
                 f"{'\\n...and ' + str(len(item_list) - 5) + ' more items' if len(item_list) > 5 else ''}\n\n" \
                 f"Please restock soon to avoid stockouts.\n" \
                 f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Send SMS
        result = await self.sms_service.send_sms(managers, message)
        
        # Log the alert
        await self.db.alert_logs.insert_one({
            "type": "low_stock",
            "items": low_stock_items,
            "recipients": managers,
            "message": message,
            "sms_result": result,
            "created_at": datetime.utcnow()
        })
        
        return result