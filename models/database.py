# File: models/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os

class Database:
    client: Optional[AsyncIOMotorClient] = None
    database_name: str = os.getenv("MONGODB_DB_NAME", "smartbiz")

db = Database()

async def get_database() -> AsyncIOMotorClient:
    if db.client is None:
        raise ValueError("Database client is not initialized. Call connect_to_mongo first.")
    return db.client[db.database_name]

async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
    
async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
