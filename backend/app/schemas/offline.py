"""Offline token schemas for API validation"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class OfflineTokenIssueRequest(BaseModel):
    """Schema for issuing offline token"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    device_id: Optional[str] = Field(None, min_length=1, max_length=255)
    ttl_hours: int = Field(4, ge=1, le=24, description="Time to live in hours")

    class Config:
        json_schema_extra = {
            "example": {
                "card_uid": "CARD-12345678",
                "device_id": "DEVICE-001",
                "ttl_hours": 4
            }
        }


class OfflineTokenResponse(BaseModel):
    """Schema for issued offline token"""
    success: bool
    token: str
    token_id: str
    card_uid: str
    balance: float
    expires_at: str
    device_id: Optional[str]
    ttl_hours: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_id": "550e8400-e29b-41d4-a716-446655440000",
                "card_uid": "CARD-12345678",
                "balance": 150.00,
                "expires_at": "2026-06-26T16:00:00Z",
                "device_id": "DEVICE-001",
                "ttl_hours": 4
            }
        }


class OfflineTokenValidationResponse(BaseModel):
    """Schema for token validation result"""
    valid: bool
    reason: Optional[str]
    token_id: Optional[str]
    card_uid: Optional[str]
    balance: Optional[Decimal]
    expires_at: Optional[str]
    payload: Optional[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "token_id": "550e8400-e29b-41d4-a716-446655440000",
                "card_uid": "CARD-12345678",
                "balance": 150.00,
                "expires_at": "2026-06-26T16:00:00Z",
                "payload": {
                    "card_uid": "CARD-12345678",
                    "balance": 15000,
                    "issued_at": "2026-06-26T12:00:00Z"
                }
            }
        }


class OfflineTransactionQueueRequest(BaseModel):
    """Schema for queuing offline transaction"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, description="Amount to deduct")
    transaction_type: str = Field(..., description="DEDUCT or REFUND")
    device_id: str = Field(..., min_length=1, max_length=255)
    offline_token_id: str = Field(..., min_length=1, max_length=255)
    machine_id: Optional[str] = Field(None, max_length=255)
    location_id: Optional[str] = Field(None, max_length=255)
    device_timestamp: Optional[datetime] = None
    device_signature: Optional[str] = Field(None, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "card_uid": "CARD-12345678",
                "amount": 5.00,
                "transaction_type": "DEDUCT",
                "device_id": "DEVICE-001",
                "offline_token_id": "550e8400-e29b-41d4-a716-446655440000",
                "machine_id": "MACHINE-001",
                "location_id": "ZONE-A",
                "device_timestamp": "2026-06-26T13:00:00Z",
                "device_signature": "abc123"
            }
        }


class OfflineSyncResult(BaseModel):
    """Schema for offline sync processing result"""
    total: int
    synced: int
    rejected: int
    failed: int
    details: List[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "synced": 8,
                "rejected": 1,
                "failed": 1,
                "details": [
                    {
                        "tx_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "SYNCED",
                        "ledger_entry_id": "660e8400-e29b-41d4-a716-446655440000"
                    },
                    {
                        "tx_id": "550e8400-e29b-41d4-a716-446655440001",
                        "status": "REJECTED",
                        "reason": "Insufficient balance"
                    }
                ]
            }
        }


class DeviceQueueStatusResponse(BaseModel):
    """Schema for device queue status"""
    device_id: str
    queue: Dict[str, int]
    active_tokens: int
    tokens: List[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "DEVICE-001",
                "queue": {
                    "pending": 5,
                    "synced": 100,
                    "rejected": 2,
                    "total": 107
                },
                "active_tokens": 3,
                "tokens": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "card_uid": "CARD-12345678",
                        "balance": 15000,
                        "expires_at": "2026-06-26T16:00:00Z"
                    }
                ]
            }
        }