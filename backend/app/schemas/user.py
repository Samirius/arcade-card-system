"""User input schemas"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="Password must be 8-72 characters")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    role: Optional[str] = "STAFF"


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    status: Optional[str] = None
    notes: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: Optional[int]
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    status: str
    created_at: Optional[str]

    class Config:
        from_attributes = True