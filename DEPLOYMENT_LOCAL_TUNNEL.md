# Local + Cloudflare Tunnel Deployment (BEST OPTION)

## Executive Summary

**This is the best approach** - zero hosting costs, full control, minimal setup.

```
Your Local Machine                     Internet
├── FastAPI (localhost:8000)    ──→   https://*.trycloudflare.com
├── PostgreSQL (localhost:5432)       (ESP32 syncs here)
├── Static Dashboard (localhost:3000)
├── Cloudflare Tunnel
└── Systemd (auto-restart)
```

**Advantages:**
- ✅ **Zero cost** (no hosting fees)
- ✅ **Full control** (root access to everything)
- ✅ **No code changes** (everything works as-is)
- ✅ **Fast performance** (no cloud latency)
- ✅ **Data privacy** (database stays local)
- ✅ **Easy backup** (files on your machine)
- ✅ **Instant updates** (deploy locally = live instantly)

**Trade-offs:**
- ⚠️ Requires machine to be on 24/7
- ⚠️ Dynamic tunnel URL (changes on restart) - can fix with named tunnel
- ⚠️ Depends on home internet connection

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Local Machine                        │
│                   (Ubuntu Linux)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │ PostgreSQL   │  │   Dashboard  │     │
│  │   :8000      │  │   :5432      │  │   :3000      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                    │                                       │
│  ┌─────────────────▼─────────────────┐                    │
│  │        Cloudflare Tunnel          │                    │
│  │  (cloudflared --url localhost:8000)│                   │
│  └───────────────────────────────────┘                    │
│                    │                                       │
│                    └────── HTTPS ──────►                   │
│                  trycloudflare.com                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Your system already has:
- ✅ Python 3.11
- ✅ PostgreSQL (already running)
- ✅ cloudflared installed
- ✅ systemd available

Need to verify:
```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Check cloudflared
which cloudflared

# Check Python
python3 --version
```

---

## Step-by-Step Deployment

### Step 1: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE arcade_cards;
CREATE USER arcade_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE arcade_cards TO arcade_user;
\q

# Verify connection
psql -h localhost -U arcade_user -d arcade_cards
```

### Step 2: Install Python Dependencies

```bash
cd ~/arcade-card-system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (create requirements.txt if needed)
cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
alembic==1.12.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
EOF

pip install -r requirements.txt
```

### Step 3: Create FastAPI Backend (if not exists)

```bash
# Create backend directory structure
mkdir -p backend/{models,schemas,crud}
cd backend

# Create database connection
cat > database.py << 'EOF'
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://arcade_user:secure_password_here@localhost:5432/arcade_cards"

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

# Create models
cat > models.py << 'EOF'
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
    transaction_type = Column(String)  # 'add' or 'deduct'
    created_at = Column(DateTime, server_default=func.now())
EOF

# Create schemas
cat > schemas.py << 'EOF'
from pydantic import BaseModel
from datetime import datetime

class CardBase(BaseModel):
    uid: str
    owner: str = "Guest"
    balance: float = 0.0

class Card(CardBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    card_uid: str
    amount: float
    transaction_type: str  # 'add' or 'deduct'

class Transaction(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
EOF

# Create CRUD operations
cat > crud.py << 'EOF'
from sqlalchemy.orm import Session
import models
import schemas

def get_card(db: Session, uid: str):
    return db.query(models.Card).filter(models.Card.uid == uid).first()

def create_card(db: Session, card: schemas.CardCreate):
    db_card = models.Card(**card.dict())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def update_balance(db: Session, uid: str, amount: float, transaction_type: str):
    card = get_card(db, uid)
    if transaction_type == 'add':
        card.balance += amount
    else:
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
EOF

# Create main FastAPI app
cat > main.py << 'EOF'
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import database
import models
import schemas
import crud

# Create database tables
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Arcade Card System API")

# CORS middleware (allow ESP32 to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Arcade Card System API"}

@app.post("/api/cards/", response_model=schemas.Card)
def create_card(card: schemas.CardBase, db: Session = Depends(database.get_db)):
    db_card = crud.get_card(db, uid=card.uid)
    if db_card:
        raise HTTPException(status_code=400, detail="Card already exists")
    return crud.create_card(db=db, card=card)

@app.get("/api/cards/{uid}", response_model=schemas.Card)
def read_card(uid: str, db: Session = Depends(database.get_db)):
    db_card = crud.get_card(db, uid=uid)
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    return db_card

@app.post("/api/transactions/")
def create_transaction(transaction: schemas.TransactionBase, db: Session = Depends(database.get_db)):
    card = crud.get_card(db, transaction.card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return crud.update_balance(db, transaction.card_uid, transaction.amount, transaction.transaction_type)

@app.get("/api/transactions/")
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    transactions = db.query(models.Transaction).offset(skip).limit(limit).all()
    return transactions
EOF
```

### Step 4: Create Static Dashboard

```bash
cd ~/arcade-card-system

# Create simple dashboard
mkdir -p dashboard
cat > dashboard/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arcade Card System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 40px; }
        .header h1 { color: #333; margin-bottom: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card h3 { color: #666; font-size: 14px; margin-bottom: 10px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .card-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .card-item { display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid #eee; }
        .card-item:last-child { border-bottom: none; }
        .card-info h4 { color: #333; margin-bottom: 5px; }
        .card-info p { color: #666; font-size: 14px; }
        .card-balance { font-size: 24px; font-weight: bold; color: #28a745; }
        .loading { text-align: center; padding: 40px; color: #666; }
    </style>
</head>
<body>
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
                const [cardsRes, transactionsRes] = await Promise.all([
                    fetch(`${API_BASE}/cards/`),
                    fetch(`${API_BASE}/transactions/`)
                ]);

                const cards = await cardsRes.json();
                const transactions = await transactionsRes.json();

                // Update stats
                document.getElementById('total-cards').textContent = cards.length || 0;
                document.getElementById('total-balance').textContent = '$' + (cards.reduce((sum, c) => sum + c.balance, 0).toFixed(2));
                document.getElementById('total-transactions').textContent = transactions.length || 0;

                // Render cards
                const container = document.getElementById('cards-container');
                if (cards.length === 0) {
                    container.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">No cards registered yet</p>';
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
            } catch (error) {
                console.error('Error fetching data:', error);
                document.getElementById('cards-container').innerHTML = '<p style="text-align: center; padding: 20px; color: #dc3545;">Error loading data</p>';
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
```

### Step 5: Create Systemd Service for FastAPI

```bash
# Create systemd service
sudo tee /etc/systemd/system/arcade-api.service > /dev/null << EOF
[Unit]
Description=Arcade Card System API
After=network.target postgresql.service

[Service]
Type=simple
User=stark
WorkingDirectory=/home/stark/arcade-card-system/backend
Environment="PATH=/home/stark/arcade-card-system/venv/bin"
ExecStart=/home/stark/arcade-card-system/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable arcade-api
sudo systemctl start arcade-api

# Check status
sudo systemctl status arcade-api
```

### Step 6: Create Systemd Service for Cloudflare Tunnel

```bash
# Create systemd service for tunnel
sudo tee /etc/systemd/system/arcade-tunnel.service > /dev/null << EOF
[Unit]
Description=Arcade Card System Cloudflare Tunnel
After=network.target arcade-api.service

[Service]
Type=simple
User=stark
ExecStart=/home/stark/bin/cloudflared tunnel --url http://localhost:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable arcade-tunnel
sudo systemctl start arcade-tunnel

# Check status
sudo systemctl status arcade-tunnel
```

### Step 7: Get Tunnel URL

```bash
# Wait for tunnel to start (10 seconds)
sleep 10

# Get tunnel URL from logs
sudo journalctl -u arcade-tunnel.service -n 50 --no-pager | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1
```

### Step 8: Update ESP32 Code

```cpp
// Update ESP32 to use tunnel URL
const char* server = "https://your-tunnel-url.trycloudflare.com";
const char* syncEndpoint = "/api/transactions/";

// Example sync function
void syncTransaction(String uid, float amount, String type) {
  HTTPClient http;
  http.begin(String(server) + syncEndpoint);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"card_uid\":\"" + uid + "\",\"amount\":" + String(amount) + ",\"transaction_type\":\"" + type + "\"}";
  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    Serial.println("Sync successful");
  } else {
    Serial.println("Sync failed: " + String(httpCode));
  }

  http.end();
}
```

---

## Named Tunnel (Stable URL) - Optional

For a permanent URL instead of changing every restart:

### Prerequisites
- Cloudflare account (free)
- Domain name (or use your existing one)

### Setup

```bash
# Login to Cloudflare
cloudflared tunnel login

# Create named tunnel
cloudflared tunnel create arcade-card-system

# Note the tunnel ID from output

# Create configuration file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/stark/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: arcade.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
EOF

# Route DNS (choose one)
cloudflared tunnel route dns arcade-card-system arcade.yourdomain.com

# Update systemd to use named tunnel
sudo tee /etc/systemd/system/arcade-tunnel.service > /dev/null << EOF
[Unit]
Description=Arcade Card System Cloudflare Tunnel
After=network.target arcade-api.service

[Service]
Type=simple
User=stark
ExecStart=/home/stark/bin/cloudflared tunnel --config /home/stark/.cloudflared/config.yml run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Restart
sudo systemctl daemon-reload
sudo systemctl restart arcade-tunnel
```

Now your tunnel URL is always: `https://arcade.yourdomain.com`

---

## Auto-Start on Boot

Everything is already configured to start automatically:

```bash
# Verify services are enabled
sudo systemctl is-enabled arcade-api
sudo systemctl is-enabled arcade-tunnel
sudo systemctl is-enabled postgresql

# Test by rebooting
sudo reboot
```

After reboot, services will start automatically:
1. PostgreSQL starts
2. FastAPI starts (after PostgreSQL is ready)
3. Cloudflare Tunnel starts (after FastAPI is ready)

---

## Backup Strategy

### Automated Backups

```bash
# Create backup script
cat > ~/backup-arcade.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups/arcade-card-system
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -h localhost -U arcade_user arcade_cards > $BACKUP_DIR/database_$DATE.sql

# Backup application files
tar -czf $BACKUP_DIR/app_$DATE.tar.gz ~/arcade-card-system

# Keep only last 7 days
find $BACKUP_DIR -name "database_*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "app_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x ~/backup-arcade.sh

# Add to crontab (daily at 2am)
(crontab -l 2>/dev/null; echo "0 2 * * * ~/backup-arcade.sh") | crontab -
```

### Manual Backup

```bash
# Backup database
pg_dump -h localhost -U arcade_user arcade_cards > backup.sql

# Backup entire project
tar -czf arcade-card-system-backup.tar.gz ~/arcade-card-system

# Restore database
psql -h localhost -U arcade_user arcade_cards < backup.sql
```

---

## Monitoring

### Check Service Status

```bash
# FastAPI status
sudo systemctl status arcade-api

# Tunnel status
sudo systemctl status arcade-tunnel

# PostgreSQL status
sudo systemctl status postgresql

# View tunnel URL
sudo journalctl -u arcade-tunnel.service -n 50 --no-pager | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com'
```

### View Logs

```bash
# FastAPI logs
sudo journalctl -u arcade-api.service -f

# Tunnel logs
sudo journalctl -u arcade-tunnel.service -f

# PostgreSQL logs
sudo journalctl -u postgresql.service -f
```

### Create Monitoring Script

```bash
cat > ~/check-arcade.sh << 'EOF'
#!/bin/bash
echo "=== Arcade Card System Status ==="
echo ""

# Check services
echo "Services:"
systemctl is-active arcade-api && echo "✓ FastAPI: Running" || echo "✗ FastAPI: Down"
systemctl is-active arcade-tunnel && echo "✓ Tunnel: Running" || echo "✗ Tunnel: Down"
systemctl is-active postgresql && echo "✓ PostgreSQL: Running" || echo "✗ PostgreSQL: Down"
echo ""

# Get tunnel URL
echo "Tunnel URL:"
sudo journalctl -u arcade-tunnel.service -n 50 --no-pager | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1
echo ""

# Check API
echo "API Health Check:"
curl -s http://localhost:8000/ | head -20
EOF

chmod +x ~/check-arcade.sh
```

---

## Firewall Configuration

If you have firewall enabled:

```bash
# Allow PostgreSQL (local only)
sudo ufw allow from 127.0.0.1 to any port 5432

# Allow FastAPI (local only - tunnel handles external)
sudo ufw allow from 127.0.0.1 to any port 8000

# Check firewall status
sudo ufw status
```

---

## Performance Tuning

### PostgreSQL Optimization

```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/14/main/postgresql.conf

# Add these optimizations:
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 1310kB
min_wal_size = 1GB
max_wal_size = 4GB

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### FastAPI Optimization

```bash
# Update systemd service to use workers
sudo nano /etc/systemd/system/arcade-api.service

# Change ExecStart to:
ExecStart=/home/stark/arcade-card-system/venv/bin/gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Install gunicorn
source ~/arcade-card-system/venv/bin/activate
pip install gunicorn

# Restart service
sudo systemctl restart arcade-api
```

---

## Security Hardening

### Database Security

```bash
# Create .pgpass file for automated backups
echo "localhost:5432:arcade_cards:arcade_user:secure_password_here" > ~/.pgpass
chmod 600 ~/.pgpass

# Restrict PostgreSQL network access
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Add/ensure these lines:
local   all             all                                     md5
host    arcade_cards    arcade_user      127.0.0.1/32            md5
host    arcade_cards    arcade_user      ::1/128                 md5

# Reload PostgreSQL
sudo systemctl reload postgresql
```

### API Security

```bash
# Update main.py to add rate limiting
# Install dependencies
source ~/arcade-card-system/venv/bin/activate
pip install slowapi

# Add to main.py:
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/transactions/")
@limiter.limit("10/minute")
async def create_transaction(...):
    ...
```

---

## Troubleshooting

### Tunnel URL Not Showing

```bash
# Check if tunnel is running
ps aux | grep cloudflared

# Check logs for errors
sudo journalctl -u arcade-tunnel.service -n 100

# Manually test cloudflared
~/bin/cloudflared tunnel --url http://localhost:8000
```

### API Not Responding

```bash
# Check if FastAPI is running
curl http://localhost:8000/

# Check logs
sudo journalctl -u arcade-api.service -n 50

# Restart service
sudo systemctl restart arcade-api
```

### Database Connection Failed

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U arcade_user -d arcade_cards

# Check PostgreSQL logs
sudo journalctl -u postgresql.service -n 50
```

### ESP32 Can't Connect

```bash
# Verify tunnel is accessible from outside
curl https://your-tunnel-url.trycloudflare.com/

# Check CORS headers
curl -I https://your-tunnel-url.trycloudflare.com/api/cards/

# Test from another network (use phone on mobile data)
```

---

## Summary

**What you get:**
- ✅ Complete Arcade Card System running locally
- ✅ Public HTTPS access via Cloudflare Tunnel
- ✅ Automatic startup on boot
- ✅ Zero hosting costs
- ✅ Full control and data privacy
- ✅ Easy backups
- ✅ Real-time sync with ESP32

**Total Cost:** $0/month
**Setup Time:** ~30 minutes
**Maintenance:** Minimal (automated backups, auto-restart on crash)

**Next Steps:**
1. Follow the deployment steps above
2. Test with simulator.py
3. Update ESP32 firmware
4. Deploy to production
5. Set up monitoring alerts (optional)

---

**Questions?** The system is fully documented and ready to deploy!