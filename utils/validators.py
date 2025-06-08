# File: utils/validators.py
import re
from typing import Any, Dict, List
from datetime import datetime

class Validators:
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^(\+254|0)[17]\d{8}$'
        
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_id_number(id_number: str) -> bool:
        """Validate ID number (adjust based on your country's format)"""
        # Kenyan ID format: 8 digits
        pattern = r'^\d{8}$'
        
        return bool(re.match(pattern, id_number))
    
    @staticmethod
    def validate_mpesa_reference(reference: str) -> bool:
        """Validate MPESA reference format"""
        # MPESA reference is typically 10 alphanumeric characters
        pattern = r'^[A-Z0-9]{10}$'
        
        return bool(re.match(pattern, reference.upper()))
    
    @staticmethod
    def sanitize_input(data: Any) -> Any:
        """Sanitize input data"""
        if isinstance(data, str):
            return data.strip()
        elif isinstance(data, dict):
            return {k: Validators.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Validators.sanitize_input(item) for item in data]
        return data
