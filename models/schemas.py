# File: models/schemas.py
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from pydantic_core import core_schema
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate)
            ])
        ])

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    def __str__(self):
        return str(super())

# User Models
class UserBase(BaseModel):
    id_number: str = Field(..., min_length=6, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., pattern="^(manager|operator)$")
    phone_number: str = Field(..., pattern="^[0-9]{10,15}$")

class UserLogin(BaseModel):
    id_number: str = Field(..., min_length=6, max_length=20)
    password: str = Field(..., min_length=1)

class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password_complexity(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserProfile(BaseModel):
    id_number: str
    full_name: str
    role: str
    phone_number: str
    last_login: Optional[datetime] = None
    first_login: bool = False

class UserCreate(UserBase):
    initial_password: str = Field(..., min_length=8)
    
    @field_validator('initial_password')
    @classmethod
    def validate_password_complexity(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserInDB(UserBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password: str
    first_login: bool = True
    created_at: datetime
    created_by: Optional[PyObjectId] = None
    last_login: Optional[datetime] = None
    is_active: bool = True
    
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    image_url: Optional[str] = None

class ItemSupplierPriceBase(BaseModel):
    supplier_id: str
    buying_price: float = Field(..., gt=0)

class ItemCreate(ItemBase):
    custom_id: str = Field(..., min_length=3, pattern="^[a-zA-Z0-9-]+$")
    current_stock: int = Field(0, ge=0)
    alert_threshold: int = Field(..., ge=0)
    selling_price: float = Field(..., gt=0)
    buying_price: float= Field(None, gt=0)
    supplier_prices: Optional[List[ItemSupplierPriceBase]] = None  # Made optional

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    current_stock: Optional[int] = Field(None, ge=0)
    alert_threshold: Optional[int] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, gt=0)
    buying_price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    image_url: Optional[str] = None
    supplier_prices: Optional[List[ItemSupplierPriceBase]] = None  # Made optional

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True
    )


class ItemSupplierPrice(ItemSupplierPriceBase):
    supplier_name: str
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class SupplierCreate(BaseModel):
    custom_id: str = Field(..., min_length=3, pattern="^[a-zA-Z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, min_length=1, max_length=100)

class ItemInDB(ItemBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
    
    custom_id: str = Field(...)
    current_stock: int
    alert_threshold: int
    selling_price: float
    buying_price: float 
    supplier_prices: List[ItemSupplierPrice] = []
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None
# Supplier Models
class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact_person: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., pattern="^[0-9]{10,15}$")
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    address: Optional[str] = None

class SupplierCreate(SupplierBase):
    custom_id: str = Field(..., min_length=3, pattern="^[a-zA-Z0-9-]+$")

class SupplierInDB(SupplierBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    custom_id: str 
    created_at: datetime
    created_by: PyObjectId
    is_active: bool = True

# Sales Models
class SaleItem(BaseModel):
    item_id: PyObjectId
    item_name: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total_price: float = Field(..., gt=0)

class SaleCreate(BaseModel):
    items: List[Dict] = Field(..., min_length=1)  # Changed from min_items to min_length
    payment_method: str = Field(..., pattern="^(cash|mpesa)$")
    mpesa_reference: Optional[str] = None
    customer_name: Optional[str] = None
    discount_percentage: float = Field(default=0, ge=0, le=100)
    
    @model_validator(mode='after')
    def validate_mpesa_reference(self):
        if self.payment_method == 'mpesa' and not self.mpesa_reference:
            raise ValueError('MPESA reference is required for MPESA payments')
        return self

class SaleInDB(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    items: List[SaleItem]
    total_amount: float
    discount_percentage: float
    discount_amount: float
    final_amount: float
    payment_method: str
    mpesa_reference: Optional[str] = None
    customer_name: Optional[str] = None
    created_at: datetime
    processed_by: PyObjectId

# Expense Models
class ExpenseCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1, max_length=50)

class ExpenseInDB(ExpenseCreate):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    recorded_by: PyObjectId

# Customer Feedback Models
class CustomerFeedbackCreate(BaseModel):
    customer_name: Optional[str] = None
    feedback_type: str = Field(..., pattern="^(requirement|complaint|recommendation)$")
    description: str = Field(..., min_length=1, max_length=500)

class CustomerFeedbackInDB(CustomerFeedbackCreate):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    recorded_by: PyObjectId
    status: str = Field(default="open")  # open, in_progress, resolved

# Report Models
class DailySalesReport(BaseModel):
    date: datetime
    total_sales: float
    total_transactions: int
    cash_sales: float
    mpesa_sales: float
    total_items_sold: int
    top_selling_items: List[Dict]

class WeeklySalesReport(BaseModel):
    week_start: datetime
    week_end: datetime
    daily_reports: List[DailySalesReport]
    total_weekly_sales: float
    average_daily_sales: float

class OperatorPerformance(BaseModel):
    operator_id: PyObjectId
    operator_name: str
    total_sales: float
    total_transactions: int
    period_start: datetime
    period_end: datetime
