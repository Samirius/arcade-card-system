"""Test that Pydantic schemas import correctly"""
import pytest
from decimal import Decimal
from app.schemas.user import UserCreate, UserLogin, UserUpdate
from app.schemas.card import CardCreate, CardUpdate, CardBalanceUpdate
from app.schemas.transaction import TransactionCreate


def test_user_schemas_import():
    """Test that user schemas import correctly"""
    # Test UserCreate
    user = UserCreate(
        email="test@example.com",
        password="Secure123",
        first_name="Test",
        last_name="User",
        phone="+1234567890"
    )
    assert user.email == "test@example.com"
    assert user.password == "Secure123"
    # role is intentionally NOT client-settable (assigned server-side) — must not be a field
    assert "role" not in UserCreate.model_fields


def test_user_validation():
    """Test user input validation"""
    # Email validation
    with pytest.raises(Exception):
        UserCreate(
            email="invalid-email",
            password="Secure123",
            first_name="Test",
            last_name="User",
            phone="+1234567890"
        )
    
    # Password too short
    with pytest.raises(Exception):
        UserCreate(
            email="test@example.com",
            password="short",
            first_name="Test",
            last_name="User",
            phone="+1234567890"
        )


def test_card_schemas_import():
    """Test that card schemas import correctly"""
    card = CardCreate(
        card_uid="card-123",
        owner="John Doe",
        card_type="REGULAR",
        balance=Decimal("100.00")
    )
    assert card.card_uid == "card-123"
    assert card.owner == "John Doe"
    assert card.card_type == "REGULAR"


def test_transaction_schemas_import():
    """Test that transaction schemas import correctly"""
    transaction = TransactionCreate(
        card_uid="card-123",
        amount=Decimal("100.00"),
        transaction_type="ADD",
        payment_method="CASH"
    )
    assert transaction.card_uid == "card-123"
    assert transaction.amount == Decimal("100.00")
    assert transaction.transaction_type == "ADD"


def test_schema_import_from_init():
    """Test that all schemas are importable from app.schemas"""
    from app.schemas import (
        UserCreate, UserLogin, UserUpdate,
        CardCreate, CardUpdate, CardBalanceUpdate,
        TransactionCreate, TransactionCreate as Transaction
    )
    assert UserCreate is not None
    assert CardCreate is not None
    assert TransactionCreate is not None