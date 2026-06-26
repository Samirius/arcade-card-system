"""Card input schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class CardCreate(BaseModel):
    """Schema for creating a new card"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    owner: str = Field(..., min_length=1, max_length=100)
    card_type: Optional[str] = Field("REGULAR", pattern="^(REGULAR|VIP|STAFF|TEST)$")
    balance: Decimal = Field(0.00, ge=0, le=999999.99)


class CardUpdate(BaseModel):
    """Schema for updating card"""
    status: Optional[str] = Field(None, pattern="^(ACTIVE|INACTIVE|LOST|STOLEN|DAMAGED)$")
    notes: Optional[str] = None


class CardBalanceUpdate(BaseModel):
    """Schema for updating card balance"""
    amount: Decimal = Field(..., ge=-999999.99, le=999999.99)
    transaction_type: str = Field(..., pattern="^(ADD|DEDUCT|REFUND)$")
    notes: Optional[str] = None


class CardResponse(BaseModel):
    """Schema for card response"""
    id: Optional[int]
    card_uid: str
    owner: str
    card_type: str
    balance: Decimal
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True