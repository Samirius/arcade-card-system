"""Transaction input schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=-999999.99, lt=999999.99)
    transaction_type: str = Field(..., pattern="^(ADD|DEDUCT|REFUND)$")
    payment_method: Optional[str] = Field(None, pattern="^(CASH|CARD|MOBILE|OTHER)$")
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    id: Optional[int]
    card_uid: str
    amount: Decimal
    transaction_type: str
    payment_method: Optional[str]
    notes: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True