"""Balance operation schemas for API validation"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal


class BalanceOperationRequest(BaseModel):
    """Schema for balance operations (add/deduct)"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, description="Must be positive amount")
    notes: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Flexible context data")

    class Config:
        json_schema_extra = {
            "example": {
                "card_uid": "CARD-12345678",
                "amount": 50.00,
                "notes": "Top-up at counter",
                "metadata": {
                    "location": "Counter 1",
                    "payment_method": "cash"
                }
            }
        }


class BalanceHistoryResponse(BaseModel):
    """Schema for balance operation result"""
    success: bool
    card_uid: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    ledger_entry: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "card_uid": "CARD-12345678",
                "amount": 50.00,
                "balance_before": 100.00,
                "balance_after": 150.00,
                "ledger_entry": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "card_uid": "CARD-12345678",
                    "amount": 50.00,
                    "balance_before": 100.00,
                    "balance_after": 150.00,
                    "operation_type": "ADD",
                    "created_at": "2026-06-26T12:00:00Z"
                }
            }
        }


class BalanceReconciliationResponse(BaseModel):
    """Schema for balance reconciliation result"""
    card_uid: str
    reconciled_balance: float
    current_balance: float
    discrepancy: float
    total_ledger_entries: int
    status: str  # MATCHED, DISCREPANCY
    last_ledger_entry: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "card_uid": "CARD-12345678",
                "reconciled_balance": 150.00,
                "current_balance": 150.00,
                "discrepancy": 0.00,
                "total_ledger_entries": 25,
                "status": "MATCHED"
            }
        }


class BalanceSnapshotResponse(BaseModel):
    """Schema for balance snapshot result"""
    success: bool
    snapshot: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "snapshot": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "card_uid": "CARD-12345678",
                    "balance": 150.00,
                    "snapshot_type": "DAILY",
                    "total_transactions": 5,
                    "total_additions": 200.00,
                    "total_deductions": 50.00,
                    "total_refunds": 0.00,
                    "snapshot_at": "2026-06-26T23:59:59Z"
                }
            }
        }


class TransactionRollbackRequest(BaseModel):
    """Schema for transaction rollback request"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    transaction_id: str = Field(..., description="UUID of transaction to rollback")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for rollback")

    class Config:
        json_schema_extra = {
            "example": {
                "card_uid": "CARD-12345678",
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "reason": "Machine malfunction - customer charged incorrectly"
            }
        }


class BalanceStatisticsResponse(BaseModel):
    """Schema for company balance statistics"""
    total_transactions: int
    unique_cards: int
    total_additions: float
    total_deductions: float
    total_refunds: float
    net_flow: float
    period: Optional[Dict[str, Optional[str]]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "total_transactions": 150,
                "unique_cards": 50,
                "total_additions": 5000.00,
                "total_deductions": 4500.00,
                "total_refunds": 50.00,
                "net_flow": 500.00,
                "period": {
                    "start": "2026-06-01T00:00:00Z",
                    "end": "2026-06-30T23:59:59Z"
                }
            }
        }