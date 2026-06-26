#!/bin/bash

# Arcade Card System - Local + Cloudflare Tunnel Setup
# This script sets up everything to run locally with public HTTPS access

set -e  # Exit on any error

echo "=== Arcade Card System Setup ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/stark/arcade-card-system"
VENV_DIR="$PROJECT_DIR/venv"
DB_NAME="arcade_cards"
DB_USER="arcade_user"
DB_PASSWORD="arcade_secure_$(date +%s | md5sum | head -c 10)"
API_PORT=8000

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL not found. Installing...${NC}"
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

# Check cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${YELLOW}cloudflared not found. Installing...${NC}"
    curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/bin/cloudflared && chmod +x ~/bin/cloudflared
    export PATH="$HOME/bin:$PATH"
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"
echo ""

# Step 2: Setup PostgreSQL
echo -e "${YELLOW}[2/7] Setting up PostgreSQL...${NC}"

# Start PostgreSQL if not running
if ! systemctl is-active --quiet postgresql; then
    sudo systemctl start postgresql
fi

# Create database and user
sudo -u postgres psql << EOF
SELECT 'CREATE DATABASE $DB_NAME' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
EOF

echo -e "${GREEN}✓ Database '$DB_NAME' created${NC}"
echo -e "${GREEN}✓ User '$DB_USER' created${NC}"
echo -e "${GREEN}⚠️  Save this password: $DB_PASSWORD${NC}"
echo ""

# Step 3: Create Python virtual environment
echo -e "${YELLOW}[3/7] Setting up Python environment...${NC}"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies
pip install --upgrade pip

cat > "$PROJECT_DIR/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
gunicorn==21.2.0
slowapi==0.1.9
EOF

pip install -r "$PROJECT_DIR/requirements.txt"
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 4: Create backend structure
echo -e "${YELLOW}[4/7] Creating FastAPI backend...${NC}"

mkdir -p "$PROJECT_DIR/backend"

# Create database.py
cat > "$PROJECT_DIR/backend/database.py" << EOF
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

# Create models.py
cat > "$PROJECT_DIR/backend/models.py" << 'EOF'
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, unique=True, index=True)
    owner = Column(String, default="Guest")
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    card_uid = Column(String, ForeignKey("cards.uid"))
    amount = Column(Float)
    transaction_type = Column(String)
    created_at = Column(DateTime, server_default=func.now())
EOF

# Create schemas.py
cat > "$PROJECT_DIR/backend/schemas.py" << 'EOF'
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CardBase(BaseModel):
    uid: str = Field(..., description="Card UID")
    owner: str = Field(default="Guest", description="Card owner name")
    balance: float = Field(default=0.0, ge=0, description="Card balance")

class Card(CardBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CardCreate(CardBase):
    pass

class TransactionBase(BaseModel):
    card_uid: str = Field(..., description="Card UID")
    amount: float = Field(..., gt=0, description="Transaction amount")
    transaction_type: str = Field(..., pattern="^(add|deduct)$", description="Type: add or deduct")

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
EOF

# Create crud.py
cat > "$PROJECT_DIR/backend/crud.py" << 'EOF'
from sqlalchemy.orm import Session
from sqlalchemy import or_
import models
import schemas

def get_card(db: Session, uid: str):
    return db.query(models.Card).filter(models.Card.uid == uid).first()

def get_cards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Card).offset(skip).limit(limit).all()

def create_card(db: Session, card: schemas.CardCreate):
    db_card = models.Card(**card.model_dump())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def get_or_create_card(db: Session, uid: str, owner: str = "Guest"):
    card = get_card(db, uid)
    if not card:
        card = create_card(db, schemas.CardCreate(uid=uid, owner=owner))
    return card

def update_balance(db: Session, uid: str, amount: float, transaction_type: str):
    card = get_card(db, uid)
    if not card:
        raise ValueError("Card not found")

    if transaction_type == 'add':
        card.balance += amount
    else:
        if card.balance < amount:
            raise ValueError("Insufficient balance")
        card.balance -= amount

    transaction = models.Transaction(
        card_uid=uid,
        amount=amount,
        transaction_type=transaction_type
    )
    db.add(transaction)
    db.commit()
    db.refresh(card)
    return card

def get_transactions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()

def get_card_transactions(db: Session, uid: str, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction).filter(models.Transaction.card_uid == uid).order_by(models.Transaction.created_at.desc()).offset(skip).limit(limit).all()
EOF

# Create main.py
cat > "$PROJECT_DIR/backend/main.py" << 'EOF'
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import database
import models
import schemas
import crud

# Initialize database
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Arcade Card System API",
    description="Card management and transaction tracking for arcade kiosks",
    version="1.0.0"
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware (allow all for development - restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static dashboard
app.mount("/static", StaticFiles(directory="../dashboard"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    """Serve the dashboard"""
    return FileResponse("../dashboard/index.html")

@app.get("/health")
@limiter.limit("100/minute")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "arcade-card-system"}

# Card endpoints
@app.post("/api/cards/", response_model=schemas.Card, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_card(card: schemas.CardCreate, db: Session = Depends(database.get_db)):
    """Create a new card"""
    db_card = crud.get_card(db, uid=card.uid)
    if db_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card with this UID already exists"
        )
    return crud.create_card(db=db, card=card)

@app.get("/api/cards/", response_model=list[schemas.Card])
@limiter.limit("100/minute")
async def read_cards(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """Get all cards"""
    cards = crud.get_cards(db, skip=skip, limit=limit)
    return cards

@app.get("/api/cards/{uid}", response_model=schemas.Card)
@limiter.limit("100/minute")
async def read_card(uid: str, db: Session = Depends(database.get_db)):
    """Get a specific card by UID"""
    db_card = crud.get_card(db, uid=uid)
    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return db_card

@app.get("/api/cards/{uid}/balance")
@limiter.limit("100/minute")
async def read_card_balance(uid: str, db: Session = Depends(database.get_db)):
    """Get card balance (for ESP32 quick check)"""
    db_card = crud.get_card(db, uid=uid)
    if not db_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found"
        )
    return {"uid": uid, "balance": db_card.balance}

# Transaction endpoints
@app.post("/api/transactions/", response_model=schemas.Transaction, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_transaction(transaction: schemas.TransactionBase, db: Session = Depends(database.get_db)):
    """Create a transaction (add or deduct credits)"""
    try:
        result = crud.update_balance(
            db,
            transaction.card_uid,
            transaction.amount,
            transaction.transaction_type
        )
        # Get the transaction that was just created
        tx = db.query(models.Transaction).filter(
            models.Transaction.card_uid == transaction.card_uid
        ).order_by(models.Transaction.created_at.desc()).first()
        return tx
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/api/transactions/", response_model=list[schemas.Transaction])
@limiter.limit("100/minute")
async def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """Get all transactions"""
    transactions = crud.get_transactions(db, skip=skip, limit=limit)
    return transactions

@app.get("/api/cards/{uid}/transactions", response_model=list[schemas.Transaction])
@limiter.limit("100/minute")
async def read_card_transactions(uid: str, skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """Get transactions for a specific card"""
    transactions = crud.get_card_transactions(db, uid=uid, skip=skip, limit=limit)
    return transactions

# Stats endpoint
@app.get("/api/stats")
@limiter.limit("100/minute")
async def get_stats(db: Session = Depends(database.get_db)):
    """Get system statistics"""
    total_cards = db.query(models.Card).count()
    total_balance = sum(card.balance for card in db.query(models.Card).all())
    total_transactions = db.query(models.Transaction).count()

    return {
        "total_cards": total_cards,
        "total_balance": round(total_balance, 2),
        "total_transactions": total_transactions
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

echo -e "${GREEN}✓ Backend created${NC}"
echo ""

# Step 5: Create dashboard
echo -e "${YELLOW}[5/7] Creating dashboard...${NC}"

mkdir -p "$PROJECT_DIR/dashboard"

cat > "$PROJECT_DIR/dashboard/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arcade Card System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 48px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .card-list {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .card-list h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
        }
        .card-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #eee;
            transition: background 0.3s;
        }
        .card-item:hover {
            background: #f8f9fa;
        }
        .card-item:last-child {
            border-bottom: none;
        }
        .card-info h4 {
            color: #333;
            font-size: 18px;
            margin-bottom: 5px;
        }
        .card-info p {
            color: #666;
            font-size: 14px;
            font-family: monospace;
        }
        .card-balance {
            font-size: 28px;
            font-weight: bold;
            color: #28a745;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .refresh-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            color: #666;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="refresh-indicator">Auto-refresh: every 5s</div>

    <div class="container">
        <div class="header">
            <h1>🎮 Arcade Card System</h1>
            <p>Real-time card management dashboard</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Cards</h3>
                <div class="value" id="total-cards">-</div>
            </div>
            <div class="stat-card">
                <h3>Total Balance</h3>
                <div class="value" id="total-balance">$-</div>
            </div>
            <div class="stat-card">
                <h3>Total Transactions</h3>
                <div class="value" id="total-transactions">-</div>
            </div>
        </div>

        <div class="card-list">
            <h2>All Cards</h2>
            <div id="cards-container" class="loading">Loading cards...</div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin + '/api';

        async function fetchStats() {
            try {
                const [statsRes, cardsRes] = await Promise.all([
                    fetch(`${API_BASE}/stats`),
                    fetch(`${API_BASE}/cards/`)
                ]);

                const stats = await statsRes.json();
                const cards = await cardsRes.json();

                // Update stats
                document.getElementById('total-cards').textContent = stats.total_cards || 0;
                document.getElementById('total-balance').textContent = '$' + (stats.total_balance || 0).toFixed(2);
                document.getElementById('total-transactions').textContent = stats.total_transactions || 0;

                // Render cards
                const container = document.getElementById('cards-container');
                if (!cards || cards.length === 0) {
                    container.innerHTML = '<p style="text-align: center; padding: 40px; color: #666;">No cards registered yet.<br>Use the ESP32 or simulator to add cards.</p>';
                } else {
                    container.innerHTML = cards.map(card => `
                        <div class="card-item">
                            <div class="card-info">
                                <h4>${card.owner}</h4>
                                <p>UID: ${card.uid}</p>
                            </div>
                            <div class="card-balance">$${card.balance.toFixed(2)}</div>
                        </div>
                    `).join('');
                }

                // Hide error if it exists
                const errorEl = document.getElementById('error-message');
                if (errorEl) errorEl.remove();

            } catch (error) {
                console.error('Error fetching data:', error);

                // Show error message
                const container = document.getElementById('cards-container');
                if (!document.getElementById('error-message')) {
                    const errorDiv = document.createElement('div');
                    errorDiv.id = 'error-message';
                    errorDiv.className = 'error';
                    errorDiv.innerHTML = `
                        <strong>Connection Error:</strong> Can't reach the API server.<br>
                        <small>Make sure the FastAPI server is running on port 8000</small>
                    `;
                    container.innerHTML = '';
                    container.appendChild(errorDiv);
                }
            }
        }

        // Load data immediately
        fetchStats();

        // Auto-refresh every 5 seconds
        setInterval(fetchStats, 5000);
    </script>
</body>
</html>
EOF

echo -e "${GREEN}✓ Dashboard created${NC}"
echo ""

# Step 6: Create systemd services
echo -e "${YELLOW}[6/7] Creating systemd services...${NC}"

# Create FastAPI service
sudo tee /etc/systemd/system/arcade-api.service > /dev/null << EOF
[Unit]
Description=Arcade Card System API
After=network.target postgresql.service

[Service]
Type=simple
User=stark
WorkingDirectory=$PROJECT_DIR/backend
Environment="PATH=$VENV_DIR/bin"
Environment="DB_NAME=$DB_NAME"
Environment="DB_USER=$DB_USER"
Environment="DB_PASSWORD=$DB_PASSWORD"
ExecStart=$VENV_DIR/bin/uvicorn main:app --host 0.0.0.0 --port $API_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create Cloudflare Tunnel service
sudo tee /etc/systemd/system/arcade-tunnel.service > /dev/null << EOF
[Unit]
Description=Arcade Card System Cloudflare Tunnel
After=network.target arcade-api.service

[Service]
Type=simple
User=stark
ExecStart=/home/stark/bin/cloudflared tunnel --url http://localhost:$API_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and reload
sudo systemctl daemon-reload
sudo systemctl enable arcade-api
sudo systemctl enable arcade-tunnel

echo -e "${GREEN}✓ Systemd services created${NC}"
echo ""

# Step 7: Start services
echo -e "${YELLOW}[7/7] Starting services...${NC}"

# Start FastAPI
sudo systemctl start arcade-api
sleep 3

# Check if FastAPI is running
if systemctl is-active --quiet arcade-api; then
    echo -e "${GREEN}✓ FastAPI started on port $API_PORT${NC}"
else
    echo -e "${RED}✗ FastAPI failed to start${NC}"
    echo "Check logs: sudo journalctl -u arcade-api.service -n 50"
    exit 1
fi

# Start Cloudflare Tunnel
sudo systemctl start arcade-tunnel
sleep 10

# Check if tunnel is running
if systemctl is-active --quiet arcade-tunnel; then
    echo -e "${GREEN}✓ Cloudflare Tunnel started${NC}"

    # Try to get tunnel URL
    echo ""
    echo -e "${YELLOW}Waiting for tunnel URL...${NC}"
    sleep 5

    TUNNEL_URL=$(sudo journalctl -u arcade-tunnel.service -n 100 --no-pager | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)

    if [ -n "$TUNNEL_URL" ]; then
        echo ""
        echo -e "${GREEN}═════════════════════════════════════════════${NC}"
        echo -e "${GREEN}🎉 SETUP COMPLETE!${NC}"
        echo -e "${GREEN}═════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}🌐 Public URL:${NC} $TUNNEL_URL"
        echo -e "${YELLOW}🏠 Local URL:${NC} http://localhost:$API_PORT"
        echo ""
        echo -e "${YELLOW}📊 Dashboard:${NC} $TUNNEL_URL/"
        echo -e "${YELLOW}📝 API Docs:${NC} $TUNNEL_URL/docs"
        echo ""
        echo -e "${YELLOW}🔐 Database:${NC}"
        echo -e "  Name: $DB_NAME"
        echo -e "  User: $DB_USER"
        echo -e "  Password: $DB_PASSWORD"
        echo ""
        echo -e "${YELLOW}📱 ESP32 Configuration:${NC}"
        echo -e "  Server: $TUNNEL_URL"
        echo -e "  Endpoint: /api/transactions/"
        echo ""
        echo -e "${YELLOW}🔧 Service Management:${NC}"
        echo -e "  Restart API: sudo systemctl restart arcade-api"
        echo -e "  Restart Tunnel: sudo systemctl restart arcade-tunnel"
        echo -e "  View API logs: sudo journalctl -u arcade-api.service -f"
        echo -e "  View tunnel logs: sudo journalctl -u arcade-tunnel.service -f"
        echo ""
        echo -e "${YELLOW}💾 Passwords saved to:${NC} $PROJECT_DIR/.env"
        echo -e "${GREEN}═════════════════════════════════════════════${NC}"
    else
        echo ""
        echo -e "${YELLOW}⚠️  Tunnel started, but URL not found yet${NC}"
        echo -e "${YELLOW}Run this to get URL:${NC}"
        echo -e "sudo journalctl -u arcade-tunnel.service -n 100 | grep trycloudflare"
    fi
else
    echo -e "${RED}✗ Cloudflare Tunnel failed to start${NC}"
    echo "Check logs: sudo journalctl -u arcade-tunnel.service -n 50"
fi

# Save credentials to .env
cat > "$PROJECT_DIR/.env" << EOF
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
API_PORT=$API_PORT
EOF

chmod 600 "$PROJECT_DIR/.env"

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"