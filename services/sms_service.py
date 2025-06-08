# File: services/sms_service.py
import requests
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.api_key = os.getenv("AFRICASTALKING_API_KEY")
        self.username = os.getenv("AFRICASTALKING_USERNAME", "sandbox")
        self.base_url = "https://api.africastalking.com/version1/messaging"
        
    async def send_sms(self, phone_numbers: List[str], message: str) -> Dict:
        """Send SMS using Africa's Talking API"""
        if not self.api_key:
            logger.error("SMS API key not configured")
            return {"success": False, "error": "SMS service not configured"}
        
        headers = {
            "apiKey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        data = {
            "username": self.username,
            "to": ",".join(phone_numbers),
            "message": message
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, data=data)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"SMS sent successfully: {result}")
            return {"success": True, "result": result}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {"success": False, "error": str(e)}

class TwilioSMSService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
    async def send_sms(self, phone_numbers: List[str], message: str) -> Dict:
        """Send SMS using Twilio API"""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.error("Twilio credentials not configured")
            return {"success": False, "error": "Twilio service not configured"}
        
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            results = []
            for phone_number in phone_numbers:
                message_instance = client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=phone_number
                )
                results.append({"to": phone_number, "sid": message_instance.sid})
            
            logger.info(f"SMS sent successfully via Twilio: {results}")
            return {"success": True, "results": results}
            
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {str(e)}")
            return {"success": False, "error": str(e)}
