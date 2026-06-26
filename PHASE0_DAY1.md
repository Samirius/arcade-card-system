# Quick Start Guide - Phase 0 Setup

## 🎯 Day 1: Environment Setup (3-5 hours)

### Step 1: Clean Up Current Project
```bash
cd ~/arcade-card-system

# Stop services
sudo systemctl stop arcade-api arcade-tunnel

# Backup current work (just in case)
cp -r ~/arcade-card-system ~/arcade-card-system-backup-$(date +%Y%m%d)

# Remove insecure files
rm -rf backend/  # Remove old insecure backend
rm -f dashboard/index.html  # Remove old dashboard
```

### Step 2: Create New Project Structure
```bash
# Create new directory structure
mkdir -p backend/{app/{models,schemas,crud,api/{v1/endpoints},services,utils},tests,alembic/versions}
mkdir -p frontend/src/{components,pages,services,utils}
mkdir -p docs scripts esp32-firmware/src

# Initialize git if not already
cd ~/arcade-card-system
git init

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/
.env
*.db
*.sqlite
node_modules/
.DS_Store
.vscode/
EOF

git add .gitignore
git commit -m "chore: add .gitignore"
```

### Step 3: Set Up Python Environment
```bash
cd ~/arcade-card-system

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install core dependencies
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pyotp==2.9.0

# Utilities
python-dotenv==1.0.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1
EOF

pip install -r requirements.txt

# Install dev dependencies
cat > requirements-dev.txt << 'EOF'
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.6.0
httpx==0.25.2
EOF

pip install -r requirements-dev.txt
```

### Step 4: Configure PostgreSQL
```bash
# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
DROP DATABASE IF EXISTS arcade_management;
DROP USER IF EXISTS arcade_user;

CREATE USER arcade_user WITH PASSWORD 'secure_password_here_change_me';
CREATE DATABASE arcade_management OWNER arcade_user;
GRANT ALL PRIVILEGES ON DATABASE arcade_management TO arcade_user;

\c arcade_management
GRANT ALL ON SCHEMA public TO arcade_user;
EOF

# Test connection
PGPASSWORD=secure_password_here_change_me psql -h localhost -U arcade_user -d arcade_management -c "SELECT current_database(), current_user;"
```

### Step 5: Create Environment Configuration
```bash
# Create .env file
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://arcade_user:secure_password_here_change_me@localhost/5432/arcade_management

# Security
SECRET_KEY=change-this-to-a-secure-random-key-at-least-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
APP_NAME=Arcade Management System
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=development

# Security
BCRYPT_ROUNDS=12
MFA_ISSUER=Arcade Management
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Hosting
HOST=0.0.0.0
PORT=8000
EOF

chmod 600 .env
```

### Step 6: Create Database Schema
```bash
# Apply schema from DATABASE_SCHEMA.md
sudo -u postgres psql -d arcade_management << 'EOF'
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enums
CREATE TYPE user_role AS ENUM ('CUSTOMER', 'STAFF', 'SUPERVISOR', 'REGIONAL_MGR', 'OPERATIONS', 'ADMIN', 'OWNER');
CREATE TYPE user_status AS ENUM ('ACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION', 'DELETED');
CREATE TYPE card_type AS ENUM ('REGULAR', 'VIP', 'STAFF', 'MANAGEMENT');
CREATE TYPE card_status AS ENUM ('ACTIVE', 'BLOCKED', 'LOST', 'STOLEN', 'EXPIRED', 'DELETED');
CREATE TYPE transaction_type AS ENUM ('ADD', 'DEDUCT', 'REFUND', 'TRANSFER', 'ADJUSTMENT', 'REVERSAL');
CREATE TYPE payment_method AS ENUM ('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'DIGITAL_WALLET', 'TRANSFER', 'VOUCHER', 'INTERNAL');

-- Create core tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role user_role NOT NULL DEFAULT 'CUSTOMER',
    status user_status DEFAULT 'PENDING_VERIFICATION',
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    last_login TIMESTAMP,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255),
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    card_uid VARCHAR(255) UNIQUE NOT NULL,
    card_type card_type DEFAULT 'REGULAR',
    status card_status DEFAULT 'ACTIVE',
    balance DECIMAL(10,2) DEFAULT 0.00 CHECK (balance >= 0),
    last_used TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    card_id UUID REFERENCES cards(id) NOT NULL,
    transaction_type transaction_type NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    balance_before DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    payment_method payment_method DEFAULT 'INTERNAL',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_cards_uid ON cards(card_uid);
CREATE INDEX idx_cards_customer ON cards(customer_id);
CREATE INDEX idx_transactions_card ON transactions(card_id);
CREATE INDEX idx_transactions_date ON transactions(created_at);

-- Insert test admin user
INSERT INTO users (email, password_hash, first_name, last_name, role, status)
VALUES (
    'admin@arcade.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYqAqG8kOq.y',
    'Admin',
    'User',
    'ADMIN',
    'ACTIVE'
);
-- Password: admin123 (change immediately!)
EOF
```

### Step 7: Create Base Application
```bash
# Create app/__init__.py
cat > backend/app/__init__.py << 'EOF'
"""Arcade Management System Backend"""
__version__ = "1.0.0"
EOF

# Create config.py
cat > backend/app/config.py << 'EOF'
"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Application
    app_name: str = "Arcade Management System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Security
    bcrypt_rounds: int = 12
    mfa_issuer: str = "Arcade Management"
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    
    # Hosting
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
EOF

# Create database.py
cat > backend/app/database.py << 'EOF'
"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

# Create main.py
cat > backend/app/main.py << 'EOF'
"""FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Secure arcade card management system",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],  # Local only for MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
EOF

# Create tests
cat > backend/tests/test_main.py << 'EOF'
"""Test basic application"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "running"

def test_health_check():
    """Test health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
EOF

# Create pytest.ini
cat > backend/pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html
EOF
```

### Step 8: Test Everything
```bash
cd ~/arcade-card-system/backend

# Activate virtual environment
source venv/bin/activate

# Run tests
pytest tests/ -v

# Start application (in another terminal)
python -m uvicorn app.main:app --reload

# Test in browser
# Visit: http://localhost:8000/docs
```

### Step 9: Verify Security
```bash
# Test database connection
psql -h localhost -U arcade_user -d arcade_management -c "\dt"

# Verify admin user exists
psql -h localhost -U arcade_user -d arcade_management -c "SELECT email, role, status FROM users;"

# Verify indexes
psql -h localhost -U arcade_user -d arcade_management -c "\di"
```

### Step 10: Commit Progress
```bash
cd ~/arcade-card-system

git add .
git commit -m "feat: complete Phase 0 environment setup

- Set up project structure
- Configure PostgreSQL database
- Create FastAPI base application
- Add test infrastructure
- Configure security settings
- Add documentation
"
```

---

## ✅ Day 1 Checklist

- [ ] Current insecure code cleaned up
- [ ] Project structure created
- [ ] Virtual environment set up
- [ ] Dependencies installed
- [ ] PostgreSQL configured
- [ ] Database schema created
- [ ] Base FastAPI app running
- [ ] Tests passing
- [ ] Documentation created
- [ ] Progress committed to git

---

## 🚀 Next Steps

**Day 2:** Security Foundation
- Implement password hashing
- Create JWT system
- Set up MFA library
- Create audit logging

**Say "Start Day 2" when you're ready!**

---

**Need help with Day 1?** Just ask! 👍