from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional
import os
import jwt  # Explicitly using pyjwt; ensure 'pip install pyjwt' and uninstall conflicting 'jwt'
from passlib.context import CryptContext
from bson import ObjectId

from models.schemas import UserCreate, UserLogin, PasswordChange, UserInDB
from models.database import get_database
from utils.validators import Validators

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load SECRET_KEY from environment variable with fallback
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
if not isinstance(SECRET_KEY, str):
    raise ValueError("SECRET_KEY must be a string; check environment variable JWT_SECRET_KEY")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Bearer token authentication (for API endpoints)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
    return user

# Cookie authentication (for web pages)
async def get_current_user_from_cookie(
    request: Request,
    token: str = Cookie(None),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token found",
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

async def get_manager_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return current_user

async def get_manager_user_from_cookie(current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user["role"] != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return current_user

@router.post("/register")
async def register_user(
    user: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Optional[dict] = Depends(get_current_user_from_cookie, use_cache=False)
):
    # Allow initial manager registration if no managers exist
    if user.role == "manager" and current_user is None:
        manager_count = await db.users.count_documents({"role": "manager", "is_active": True})
        if manager_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manager registration requires authentication"
            )
    elif current_user is None or current_user["role"] != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required for registration"
        )

    # Validate ID number format
    if not Validators.validate_id_number(user.id_number):
        raise HTTPException(status_code=400, detail="Invalid ID number format")
    
    # Validate phone number
    if not Validators.validate_phone_number(user.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"id_number": user.id_number})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this ID number already exists")
    
    # Create new user
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user.initial_password)
    user_dict["first_login"] = True
    user_dict["created_at"] = datetime.utcnow()
    user_dict["created_by"] = current_user["_id"] if current_user else None
    user_dict["is_active"] = True
    
    result = await db.users.insert_one(user_dict)
    return {"message": "User created successfully", "user_id": str(result.inserted_id)}

@router.post("/login")
async def login(user_credentials: UserLogin, db: AsyncIOMotorDatabase = Depends(get_database)):
    user = await db.users.find_one({"id_number": user_credentials.id_number})
    if not user or not verify_password(user_credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID number or password"
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Update last login
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user["role"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        "first_login": user.get("first_login", False),
        "role": user["role"],
        "user_name": user["full_name"]
    }

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user_from_cookie),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    if not verify_password(password_data.current_password, current_user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    new_hashed_password = get_password_hash(password_data.new_password)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"password": new_hashed_password, "first_login": False}}
    )
    return {"message": "Password updated successfully"}

@router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user_from_cookie)):
    return {
        "id_number": current_user["id_number"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "phone_number": current_user["phone_number"],
        "last_login": current_user.get("last_login"),
        "first_login": current_user.get("first_login", False)
    }