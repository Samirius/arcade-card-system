"""Company schemas for API validation"""
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CompanyPlan(str, Enum):
    """Company subscription plans"""
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class CompanyStatus(str, Enum):
    """Company status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class BusinessType(str, Enum):
    """Types of arcade businesses"""
    FEC = "FEC"  # Family Entertainment Center
    ARCADE = "ARCADE"
    BOWLING = "BOWLING"
    LASERTAG = "LASERTAG"
    MINIGOLF = "MINIGOLF"
    THEME_PARK = "THEME_PARK"
    MALL_ARCADE = "MALL_ARCADE"
    OTHER = "OTHER"


class CompanyCreate(BaseModel):
    """Schema for creating a new company"""
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly company identifier")
    email: EmailStr
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    business_type: Optional[BusinessType] = BusinessType.FEC
    tax_id: Optional[str] = Field(None, max_length=50)
    plan: Optional[CompanyPlan] = CompanyPlan.STARTER

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Cairo Fun Center",
                "slug": "cairo-fun-center",
                "email": "contact@cairofun.com",
                "phone": "+201234567890",
                "address": "123 Game Street, Cairo",
                "city": "Cairo",
                "country": "Egypt",
                "business_type": "FEC",
                "tax_id": "EG123456789",
                "plan": "STARTER"
            }
        }


class CompanyUpdate(BaseModel):
    """Schema for updating company information"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    business_type: Optional[BusinessType] = None
    tax_id: Optional[str] = Field(None, max_length=50)
    plan: Optional[CompanyPlan] = None
    status: Optional[CompanyStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "phone": "+209876543210",
                "address": "456 New Location, Cairo",
                "plan": "PRO"
            }
        }


class CompanyResponse(BaseModel):
    """Schema for company response"""
    id: str
    name: str
    slug: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    business_type: Optional[str]
    tax_id: Optional[str]
    plan: str
    status: str
    max_venues: int
    max_users: int
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
    deleted_by: Optional[str]

    class Config:
        from_attributes = True


class CompanyStats(BaseModel):
    """Schema for company statistics"""
    company_id: str
    company_name: str
    total_users: int
    total_cards: int
    total_balance: float
    total_transactions_30d: int
    total_volume_30d: float
    plan: str
    max_users: Optional[int]
    usage_percentage: float
    status: str
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "550e8400-e29b-41d4-a716-446655440000",
                "company_name": "Cairo Fun Center",
                "total_users": 5,
                "total_cards": 150,
                "total_balance": 15000.00,
                "total_transactions_30d": 250,
                "total_volume_30d": 5000.00,
                "plan": "STARTER",
                "max_users": 10,
                "usage_percentage": 50.0,
                "status": "ACTIVE",
                "created_at": "2026-06-26T00:00:00Z"
            }
        }


class CompanyListItem(BaseModel):
    """Schema for company list item (simplified)"""
    id: str
    name: str
    slug: str
    email: str
    city: Optional[str]
    country: Optional[str]
    plan: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True