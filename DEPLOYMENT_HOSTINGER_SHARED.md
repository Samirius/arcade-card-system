# Hostinger Cloud Shared Hosting Research

## User's Situation: Cloud Shared Hosting (NOT VPS)

This changes everything. Shared hosting has different constraints than VPS.

---

## What Hostinger Cloud Shared Hosting Offers

### Available Technologies
- ✅ **PHP** (primary support)
- ✅ **MySQL** databases
- ✅ **Node.js** (limited)
- ✅ **Python** (via CloudLinux Python Selector)
- ✅ **Static files** (HTML/CSS/JS)
- ✅ **Cron jobs**
- ✅ **Git deployment**
- ❌ **PostgreSQL** (MySQL only)
- ❌ **Systemd services**
- ❌ **Background workers**
- ❌ **Custom server software**

---

## Architecture Challenge

The Arcade Card System uses:
- **FastAPI** (Python async web framework)
- **PostgreSQL** (database)
- **WebSocket support** (real-time sync)

Shared hosting constraints:
- MySQL only (no PostgreSQL)
- No systemd/background workers
- Limited Python (via CGI/FastCGI, not full async)
- No WebSocket support in shared hosting

---

## Solution Options

### Option 1: Hybrid Architecture ⭐ **RECOMMENDED**

```
┌─────────────────────────────────────────────────────────────┐
│                   Hostinger Cloud                           │
│                   (Shared Hosting)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Static     │  │   PHP API    │  │   MySQL DB   │     │
│  │  Dashboard   │  │  (Lightweight)│   (Adapted)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Service                           │
│                   (Supabase/Firebase)                        │
├─────────────────────────────────────────────────────────────┤
│  ✅ PostgreSQL Database                                       │
│  ✅ Real-time WebSocket                                     │
│  ✅ Auth System                                              │
│  ✅ Free Tier Available                                      │
└─────────────────────────────────────────────────────────────┘
```

**Approach:**
1. Deploy static dashboard to Hostinger
2. Use PHP for simple CRUD API endpoints
3. Host PostgreSQL on **Supabase** (free tier, same developer experience)
4. Keep ESP32 syncing via HTTP to PHP API

**Migration needed:**
- FastAPI → PHP/MySQL endpoints
- PostgreSQL → Supabase PostgreSQL
- WebSocket → Supabase Realtime

---

### Option 2: Pure Hostinger (Full Rewrite)

```
┌─────────────────────────────────────────────────────────────┐
│                   Hostinger Cloud                           │
│                   (Shared Hosting)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Static     │  │   PHP API    │  │   MySQL DB   │     │
│  │  Dashboard   │  │  (Endpoints) │   (Full Stack) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │      Cron Job (Transaction Sync)             │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Approach:**
1. Host static frontend on Hostinger
2. Build PHP API endpoints (`/api/transactions`, `/api/cards`, etc.)
3. MySQL database for data storage
4. Cron jobs for background tasks

**Migration needed:**
- FastAPI → PHP
- PostgreSQL → MySQL
- Async → Synchronous
- WebSocket → Polling

---

### Option 3: External Backend Only

```
┌─────────────────────────────────────────────────────────────┐
│                   Hostinger Cloud                           │
│                   (Shared Hosting)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │   Static     │  ← Frontend only                         │
│  │  Dashboard   │                                           │
│  └──────────────┘                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS API calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Backend                          │
│                   (Render/Railway/Free)                     │
├─────────────────────────────────────────────────────────────┤
│  ✅ FastAPI + PostgreSQL                                     │
│  ✅ WebSocket support                                       │
│  ✅ Full async capabilities                                 │
│  ✅ Free tier available                                     │
└─────────────────────────────────────────────────────────────┘
```

**Approach:**
1. Host static HTML dashboard on Hostinger
2. Deploy FastAPI backend to **Render** or **Railway** (free tier)
3. Frontend makes API calls to external backend

**Pros:**
- Keep FastAPI + PostgreSQL
- No code rewrite
- Free tiers available

**Cons:**
- Split infrastructure
- CORS configuration needed
- Two hosting accounts

---

## Detailed Comparison

| Feature | Hybrid (Hostinger+Supabase) | Full PHP Hostinger | External Backend |
|---------|----------------------------|-------------------|------------------|
| **Complexity** | Medium | High | Low |
| **Cost** | Free (Supabase) | Free | Free tiers |
| **Migration** | Moderate | Major | Minimal |
| **Performance** | Good | Fair | Excellent |
| **Real-time** | ✅ (Supabase) | ❌ | ✅ |
| **PostgreSQL** | ✅ | ❌ | ✅ |
| **Single account** | ❌ | ✅ | ❌ |

---

## Recommended Implementation: Hybrid Approach

### Why Hybrid?

1. **Keep some on Hostinger** (what you're paying for)
   - Static dashboard
   - PHP API for ESP32 sync

2. **Offload heavy lifting to Supabase**
   - PostgreSQL database
   - Real-time WebSocket
   - Authentication

3. **Minimal code changes**
   - Frontend: Change API URLs
   - Backend: PHP sync layer to Supabase
   - Database: Same schema, just hosted elsewhere

### Step-by-Step Implementation

**Step 1: Setup Supabase**
```bash
# 1. Create Supabase project (free at supabase.com)
# 2. Get connection string:
#    postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres

# 3. Run migrations via Supabase SQL Editor
#    Paste your PostgreSQL schema
```

**Step 2: Deploy to Hostinger**
```bash
# Upload static files via FTP or Git
git clone https://github.com/Samirius/arcade-card-system.git
# Upload only dashboard/ folder to public_html/

# Create PHP API endpoints
# public_html/api/sync.php - ESP32 sync endpoint
# public_html/api/cards.php - Card management
# public_html/api/transactions.php - Transaction logging
```

**Step 3: Update ESP32 Code**
```cpp
// Change WiFi sync endpoint
const char* server = "your-domain.com/api/sync.php";

// Send data via POST to PHP
// PHP forwards to Supabase via REST API
```

**Step 4: Update Dashboard**
```javascript
// Change API base URL
const API_BASE = 'https://api.supabase.co/v1/project_id';
const API_KEY = 'your-supabase-anon-key';

// Use Supabase JS client for real-time
const { createClient } = supabase
const supabase = createClient(API_BASE, API_KEY);
```

---

## PHP API Example (for ESP32 Sync)

```php
<?php
// public_html/api/sync.php
header('Content-Type: application/json');

// Supabase connection
$sb_url = 'https://api.supabase.co/v1/project_id';
$sb_key = 'your-supabase-service-key';
$connection_string = 'postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres';

// Get POST data from ESP32
$input = json_decode(file_get_contents('php://input'), true);

$card_uid = $input['uid'];
$transaction_type = $input['type']; // 'add' or 'deduct'
$amount = $input['amount'];

// Connect to Supabase via pgsql
$db = pg_connect($connection_string);

if ($transaction_type === 'add') {
    $query = "UPDATE cards SET balance = balance + $1 WHERE uid = $2 RETURNING *";
} else {
    $query = "UPDATE cards SET balance = balance - $1 WHERE uid = $2 RETURNING *";
}

$result = pg_query_params($db, $query, [$amount, $card_uid]);
$card = pg_fetch_assoc($result);

// Log transaction
$log_query = "INSERT INTO transactions (card_uid, amount, type, created_at) VALUES ($1, $2, $3, NOW())";
pg_query_params($db, $log_query, [$card_uid, $amount, $transaction_type]);

echo json_encode(['success' => true, 'balance' => $card['balance']]);
?>
```

---

## Supabase Setup

### Why Supabase?
- ✅ **Free tier** (500MB database, 2GB bandwidth)
- ✅ **PostgreSQL** (same as current)
- ✅ **Real-time WebSocket** (for dashboard sync)
- ✅ **REST API** (auto-generated from tables)
- ✅ **Authentication** (built-in)
- ✅ **Easy migration** (same SQL schema)

### Migration Steps
```sql
-- Run in Supabase SQL Editor
-- Create tables (same schema as current)

CREATE TABLE cards (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(255) UNIQUE NOT NULL,
    owner VARCHAR(255) DEFAULT 'Guest',
    balance DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    card_uid VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'add' or 'deduct'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enable Realtime
ALTER publication supabase_realtime ADD TABLE cards;
ALTER publication supabase_realtime ADD TABLE transactions;

-- Create index for ESP32 sync
CREATE INDEX idx_cards_uid ON cards(uid);
```

---

## Hostinger Deployment (PHP + Static)

### File Structure on Hostinger
```
public_html/
├── index.html           # Dashboard (from dashboard/index.html)
├── css/                 # Dashboard styles
├── js/                  # Dashboard scripts (updated for Supabase)
├── api/
│   ├── sync.php         # ESP32 sync endpoint
│   ├── cards.php        # Card management
│   └── transactions.php # Transaction logging
└── .htaccess            # URL routing
```

### .htaccess Configuration
```apache
<IfModule mod_rewrite.c>
    RewriteEngine On

    # API routing
    RewriteRule ^api/sync$ api/sync.php [L]
    RewriteRule ^api/cards$ api/cards.php [L]
    RewriteRule ^api/transactions$ api/transactions.php [L]

    # SPA fallback
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ index.html [L]
</IfModule>
```

---

## Cost Comparison

| Platform | Cost | What you get |
|----------|------|--------------|
| **Hostinger Cloud** | ~$3-5/mo | Static hosting + PHP + MySQL |
| **Supabase Free** | $0 | 500MB PostgreSQL + Realtime |
| **Total** | **~$3-5/mo** | Full stack deployed |

---

## Next Steps

**If you want to proceed with hybrid approach:**

1. ✅ Create Supabase project
2. ✅ Migrate PostgreSQL schema to Supabase
3. ✅ Update dashboard JS to use Supabase client
4. ✅ Create PHP sync endpoints on Hostinger
5. ✅ Update ESP32 to sync with PHP endpoints
6. ✅ Deploy static dashboard to Hostinger
7. ✅ Test end-to-end

**If you prefer external backend only:**

1. ✅ Deploy FastAPI to Render/Railway (free)
2. ✅ Deploy static dashboard to Hostinger
3. ✅ Configure CORS
4. ✅ Update ESP32 endpoint URLs

---

## Summary

**For Hostinger Cloud shared hosting, you have 3 options:**

1. **Hybrid (Recommended)** - Hostinger for static + PHP, Supabase for DB + real-time
2. **Full PHP** - Complete rewrite to PHP + MySQL (most work)
3. **External Backend** - Keep FastAPI, deploy elsewhere (least work)

**My recommendation: Hybrid approach**
- Leverages your Hostinger plan
- Minimal code changes
- Free Supabase tier
- Best performance

Would you like me to start implementing the hybrid approach?