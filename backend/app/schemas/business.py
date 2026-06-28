"""Pydantic schemas for business logic APIs"""
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid


# ============================================================================
# CUSTOMER SCHEMAS
# ============================================================================

class CustomerCreate(BaseModel):
    """Schema for creating a new customer"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class CustomerUpdate(BaseModel):
    """Schema for updating a customer"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)


class CustomerResponse(BaseModel):
    """Schema for customer response"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str
    date_of_birth: Optional[datetime] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    preferred_language: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_visit: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# CARD SCHEMAS (Extended)
# ============================================================================

class CardCreate(BaseModel):
    """Schema for creating a new card"""
    card_uid: str = Field(..., min_length=1, max_length=255, description="RFID card UID or QR code")
    owner: str = Field(..., min_length=1, max_length=100, description="Card owner name")
    card_type: str = Field(default="REGULAR", description="Card type: REGULAR, VIP, STAFF, TEST")
    initial_balance: Decimal = Field(default=0.00, ge=0, description="Initial card balance")
    customer_id: Optional[uuid.UUID] = None
    location_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=500)

    @validator('card_type')
    def validate_card_type(cls, v):
        valid_types = ['REGULAR', 'VIP', 'STAFF', 'TEST']
        if v not in valid_types:
            raise ValueError(f'Card type must be one of {valid_types}')
        return v


class CardUpdate(BaseModel):
    """Schema for updating a card"""
    owner: Optional[str] = Field(None, min_length=1, max_length=100)
    card_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

    @validator('card_type')
    def validate_card_type(cls, v):
        if v is None:
            return v
        valid_types = ['REGULAR', 'VIP', 'STAFF', 'TEST']
        if v not in valid_types:
            raise ValueError(f'Card type must be one of {valid_types}')
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        valid_statuses = ['ACTIVE', 'INACTIVE', 'LOST', 'STOLEN', 'DAMAGED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class CardResponse(BaseModel):
    """Schema for card response"""
    id: uuid.UUID
    card_uid: str
    owner: str
    card_type: str
    status: str
    balance: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_transaction_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CardBalanceResponse(BaseModel):
    """Schema for card balance response"""
    card_uid: str
    balance: Decimal
    status: str
    card_type: str
    owner: str


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionCreate(BaseModel):
    """Schema for creating a transaction"""
    card_uid: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0, description="Transaction amount (positive)")
    transaction_type: str = Field(..., description="Transaction type: ADD, DEDUCT, REFUND")
    payment_method: Optional[str] = Field(None, description="Payment method: CASH, CARD, TRANSFER")
    notes: Optional[str] = Field(None, max_length=500)

    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        valid_types = ['ADD', 'DEDUCT', 'REFUND']
        if v not in valid_types:
            raise ValueError(f'Transaction type must be one of {valid_types}')
        return v


class TransactionResponse(BaseModel):
    """Schema for transaction response"""
    id: uuid.UUID
    card_uid: str
    amount: Decimal
    transaction_type: str
    payment_method: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# BALANCE MANAGEMENT SCHEMAS
# ============================================================================

class BalanceOperation(BaseModel):
    """Schema for balance operations"""
    amount: Decimal = Field(..., gt=0, description="Amount to add or deduct")
    notes: Optional[str] = Field(None, max_length=500)


class BalanceAddResponse(BaseModel):
    """Schema for balance add response"""
    success: bool
    message: str
    card_uid: str
    old_balance: Decimal
    new_balance: Decimal
    transaction_id: Optional[uuid.UUID] = None


class BalanceChargeResponse(BaseModel):
    """Schema for balance charge response"""
    success: bool
    message: str
    card_uid: str
    old_balance: Decimal
    new_balance: Decimal
    amount_charged: Decimal
    transaction_id: Optional[uuid.UUID] = None


# ============================================================================
# LOCATION SCHEMAS
# ============================================================================

class LocationCreate(BaseModel):
    """Schema for creating a location"""
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: str = Field(default='UTC')
    currency: str = Field(default='EGP')
    manager_id: Optional[uuid.UUID] = None
    manager_name: Optional[str] = Field(None, max_length=100)
    opens_at: Optional[str] = Field(None, description="HH:MM format")
    closes_at: Optional[str] = Field(None, description="HH:MM format")
    notes: Optional[str] = Field(None, max_length=500)


class LocationUpdate(BaseModel):
    """Schema for updating a location"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None
    manager_name: Optional[str] = Field(None, max_length=100)
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        valid_statuses = ['ACTIVE', 'CLOSED', 'MAINTENANCE', 'TEMPORARILY_CLOSED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class LocationResponse(BaseModel):
    """Schema for location response"""
    id: uuid.UUID
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    timezone: str
    currency: str
    status: str
    manager_id: Optional[uuid.UUID] = None
    manager_name: Optional[str] = None
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    opened_at: Optional[datetime] = None
    full_address: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# MACHINE SCHEMAS
# ============================================================================

class MachineCreate(BaseModel):
    """Schema for creating a machine"""
    location_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)
    machine_type: str = Field(default='GAME', description="GAME, KIOSK, ATTRACTION, VENDING, TOKEN_MACHINE")
    cost_per_play: Decimal = Field(default=0.00, ge=0)
    currency: str = Field(default='EGP')
    ip_address: Optional[str] = Field(None, max_length=50)
    mac_address: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)

    @validator('machine_type')
    def validate_machine_type(cls, v):
        valid_types = ['GAME', 'KIOSK', 'ATTRACTION', 'VENDING', 'TOKEN_MACHINE']
        if v not in valid_types:
            raise ValueError(f'Machine type must be one of {valid_types}')
        return v


class MachineUpdate(BaseModel):
    """Schema for updating a machine"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = None
    cost_per_play: Optional[Decimal] = Field(None, ge=0)
    ip_address: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        valid_statuses = ['ONLINE', 'OFFLINE', 'MAINTENANCE', 'OUT_OF_ORDER', 'RETIRED']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v


class MachineResponse(BaseModel):
    """Schema for machine response"""
    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    code: Optional[str] = None
    serial_number: Optional[str] = None
    machine_type: str
    status: str
    cost_per_play: Decimal
    currency: str
    revenue_total: Decimal
    revenue_today: Decimal
    total_plays: str
    plays_today: str
    last_played: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    next_maintenance: Optional[datetime] = None
    maintenance_notes: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    installed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class DashboardStatsResponse(BaseModel):
    """Schema for dashboard statistics"""
    revenue_today: Decimal
    revenue_week: Decimal
    revenue_month: Decimal
    revenue_total: Decimal
    cards_active: int
    cards_inactive: int
    cards_total: int
    transactions_today: int
    transactions_week: int
    transactions_month: int
    machines_online: int
    machines_offline: int
    machines_total: int
    customers_total: int


class DashboardCardsResponse(BaseModel):
    """Schema for dashboard cards overview"""
    cards: List[CardResponse]
    total: int
    active: int
    inactive: int


class DashboardRevenueResponse(BaseModel):
    """Schema for dashboard revenue breakdown"""
    by_day: List[dict]
    by_machine: List[dict]
    by_location: List[dict]
    top_cards: List[dict]


# ============================================================================
# LIST FILTER SCHEMAS
# ============================================================================

class CardListFilter(BaseModel):
    """Schema for filtering card list"""
    status: Optional[str] = None
    card_type: Optional[str] = None
    search: Optional[str] = Field(None, description="Search by card UID or owner")
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class TransactionListFilter(BaseModel):
    """Schema for filtering transaction list"""
    card_uid: Optional[str] = None
    transaction_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MachineListFilter(BaseModel):
    """Schema for filtering machine list"""
    location_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    machine_type: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class LocationListFilter(BaseModel):
    """Schema for filtering location list"""
    status: Optional[str] = None
    search: Optional[str] = Field(None, description="Search by name or city")
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)