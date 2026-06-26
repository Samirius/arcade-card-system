#!/usr/bin/env python3
"""
Arcade Card System - Simulator/Tester

This script simulates the card system without hardware.
Use it to test the logic before uploading to ESP32.
"""

import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class Card:
    uid: str
    balance: float
    owner: str

@dataclass
class Transaction:
    card_uid: str
    type: str  # 'add' or 'deduct'
    amount: float
    timestamp: str
    location: str

class ArcadeCardSystem:
    def __init__(self):
        self.cards: Dict[str, Card] = {}
        self.transactions: List[Transaction] = []
        self.location = "card-kiosk-1"
        self.load_data()

    def load_data(self):
        """Load cards from JSON file"""
        try:
            with open('cards.json', 'r') as f:
                data = json.load(f)
                for uid, card_data in data.items():
                    self.cards[uid] = Card(**card_data)
            print(f"✓ Loaded {len(self.cards)} cards from storage")
        except FileNotFoundError:
            print("✓ No existing cards - starting fresh")

    def save_data(self):
        """Save cards to JSON file"""
        with open('cards.json', 'w') as f:
            data = {uid: asdict(card) for uid, card in self.cards.items()}
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(self.cards)} cards to storage")

    def log_transaction(self, card_uid: str, type: str, amount: float):
        """Log a transaction"""
        transaction = Transaction(
            card_uid=card_uid,
            type=type,
            amount=amount,
            timestamp=datetime.now().isoformat(),
            location=self.location
        )
        self.transactions.append(transaction)
        print(f"📝 Transaction logged: {type} ${amount:.2f} for card {card_uid}")

    def register_card(self, uid: str, owner: str = "Guest") -> Card:
        """Register a new card"""
        if uid in self.cards:
            print(f"⚠️  Card {uid} already exists")
            return self.cards[uid]

        self.cards[uid] = Card(uid=uid, balance=0.0, owner=owner)
        self.save_data()
        print(f"✓ Registered new card: {uid} (Owner: {owner})")
        return self.cards[uid]

    def get_card(self, uid: str) -> Optional[Card]:
        """Get card by UID"""
        return self.cards.get(uid)

    def add_credit(self, uid: str, amount: float) -> bool:
        """Add credit to a card"""
        card = self.get_card(uid)
        if not card:
            print(f"❌ Card {uid} not found")
            return False

        if amount <= 0:
            print(f"❌ Amount must be positive")
            return False

        card.balance += amount
        self.log_transaction(uid, 'add', amount)
        self.save_data()
        print(f"✓ Added ${amount:.2f} to card {uid}")
        print(f"✓ New balance: ${card.balance:.2f}")
        return True

    def deduct_credit(self, uid: str, amount: float) -> bool:
        """Deduct credit from a card"""
        card = self.get_card(uid)
        if not card:
            print(f"❌ Card {uid} not found")
            return False

        if amount <= 0:
            print(f"❌ Amount must be positive")
            return False

        if card.balance < amount:
            print(f"❌ Insufficient balance: ${card.balance:.2f} (need ${amount:.2f})")
            return False

        card.balance -= amount
        self.log_transaction(uid, 'deduct', amount)
        self.save_data()
        print(f"✓ Deducted ${amount:.2f} from card {uid}")
        print(f"✓ Remaining balance: ${card.balance:.2f}")
        return True

    def check_balance(self, uid: str) -> Optional[float]:
        """Check card balance"""
        card = self.get_card(uid)
        if card:
            print(f"💳 Card {uid}")
            print(f"   Owner: {card.owner}")
            print(f"   Balance: ${card.balance:.2f}")
            return card.balance
        else:
            print(f"❌ Card {uid} not found")
            return None

    def list_cards(self):
        """List all registered cards"""
        print(f"\n{'='*50}")
        print(f"REGISTERED CARDS ({len(self.cards)})")
        print(f"{'='*50}")
        for uid, card in self.cards.items():
            print(f"{uid:12} | {card.owner:20} | ${card.balance:7.2f}")
        print(f"{'='*50}\n")

    def list_transactions(self, limit: int = 10):
        """List recent transactions"""
        print(f"\n{'='*60}")
        print(f"RECENT TRANSACTIONS (Last {limit})")
        print(f"{'='*60}")
        for tx in reversed(self.transactions[-limit:]):
            tx_symbol = "➕" if tx.type == 'add' else "➖"
            print(f"{tx.timestamp} | {tx.card_uid} | {tx_symbol} ${tx.amount:.2f} | {tx.location}")
        print(f"{'='*60}\n")

def simulate_rfid_scan():
    """Simulate scanning an RFID card"""
    # Simulate card UIDs (you can use actual card UIDs here)
    test_cards = [
        "A1B2C3D4",
        "11223344",
        "AA55BBCC",
        "00112233"
    ]
    import random
    return random.choice(test_cards)

def main():
    print("🎮 Arcade Card System - Simulator")
    print("="*50)

    system = ArcadeCardSystem()

    while True:
        print("\n📋 Options:")
        print("1. Simulate RFID card scan")
        print("2. Register new card")
        print("3. Add credit to card")
        print("4. Deduct credit from card (arcade test)")
        print("5. Check card balance")
        print("6. List all cards")
        print("7. List recent transactions")
        print("8. Load test data")
        print("0. Exit")

        choice = input("\n➤ Enter choice: ").strip()

        if choice == "1":
            uid = simulate_rfid_scan()
            print(f"\n📡 Card scanned: {uid}")
            system.check_balance(uid)

        elif choice == "2":
            uid = input("Enter card UID: ").strip().upper()
            owner = input("Enter owner name (default: Guest): ").strip() or "Guest"
            system.register_card(uid, owner)

        elif choice == "3":
            uid = input("Enter card UID: ").strip().upper()
            amount = float(input("Enter amount to add ($): "))
            system.add_credit(uid, amount)

        elif choice == "4":
            uid = input("Enter card UID: ").strip().upper()
            amount = float(input("Enter amount to deduct ($): "))
            system.deduct_credit(uid, amount)

        elif choice == "5":
            uid = input("Enter card UID: ").strip().upper()
            system.check_balance(uid)

        elif choice == "6":
            system.list_cards()

        elif choice == "7":
            system.list_transactions()

        elif choice == "8":
            print("\n📦 Loading test data...")
            test_cards = [
                ("A1B2C3D4", "Alice", 25.0),
                ("11223344", "Bob", 15.50),
                ("AA55BBCC", "Charlie", 0.0),
                ("00112233", "Diana", 50.0),
            ]
            for uid, owner, balance in test_cards:
                if uid not in system.cards:
                    system.register_card(uid, owner)
                    if balance > 0:
                        system.add_credit(uid, balance)
            print("✓ Test data loaded!")
            system.list_cards()

        elif choice == "0":
            print("\n👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()