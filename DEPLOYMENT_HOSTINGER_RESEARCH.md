# Hostinger Deployment Options Research

## Executive Summary

After investigating Hostinger's deployment capabilities, here are the available options for deploying the Arcade Card System (FastAPI + PostgreSQL + Static Frontend):

---

## Available Deployment Methods

### 1. VPS (Virtual Private Server) - Recommended ✅
**Best for:** Full control, custom stack, production deployment

**What Hostinger offers:**
- KVM VPS plans (starting from ~$3.99/month)
- Root SSH access
- Full Linux environment (Ubuntu, Debian, CentOS)
- Custom software installation (Python, PostgreSQL, Nginx)

**Deployment approach:**
```bash
# SSH into VPS
ssh u810045503@<hostinger-vps-ip> -p 65002

# Install dependencies
sudo apt update
sudo apt install python3-pip postgresql nginx

# Clone repo
git clone https://github.com/Samirius/arcade-card-system.git
cd arcade-card-system

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup PostgreSQL
sudo -u postgres createdb arcade_cards
sudo -u postgres psql -c "CREATE USER arcade_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE arcade_cards TO arcade_user;"

# Run migrations
python3 -m alembic upgrade head

# Configure systemd service
sudo nano /etc/systemd/system/arcade-api.service
# (see systemd config below)

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/arcade-api
# (see nginx config below)

# Start services
sudo systemctl daemon-reload
sudo systemctl enable arcade-api
sudo systemctl start arcade-api
sudo systemctl restart nginx
```

**Pros:**
- Complete control over environment
- Can run PostgreSQL, Redis, background workers
- Scalable (upgrade VPS as needed)
- SSH automation via `ssh` commands + `scp`/`rsync`
- No API needed - full shell access

**Cons:**
- Manual setup required
- Need to manage updates/security

---

### 2. Cloud Hosting (cPanel)
**Best for:** Simple static sites, basic PHP apps

**What Hostinger offers:**
- Shared hosting with cPanel
- File Manager upload
- One-click WordPress installs
- Limited to: PHP, MySQL, Node.js (no Python FastAPI)

**Deployment approach:**
```bash
# Upload static dashboard via cPanel File Manager or FTP
# Upload dashboard/ folder to public_html/

# NO: Cannot host FastAPI backend
# NO: No PostgreSQL support (only MySQL)
```

**Pros:**
- Easy file upload
- Auto SSL certificates
- Email hosting included

**Cons:**
- ❌ No Python FastAPI support
- ❌ No PostgreSQL (only MySQL)
- ❌ Cannot run background workers
- ❌ No systemd/services control

**Verdict:** NOT suitable for this project

---

### 3. Hostinger API (Limited)
**Best for:** Automating VPS management, not app deployment

**What Hostinger API offers:**
- VPS provisioning/management
- DNS management
- SSL certificate management
- Account/billing operations

**Available endpoints:**
```python
# Hypothetical API structure (not publicly documented)
POST /api/v1/vps/create
POST /api/v1/vps/{id}/reboot
POST /api/v1/vps/{id}/rebuild
GET /api/v1/dns/records
POST /api/v1/ssl/issue
```

**What it does NOT offer:**
- ❌ No file upload APIs
- ❌ No process management APIs
- ❌ No database provisioning APIs
- ❌ No application deployment APIs

**Deployment approach:**
```bash
# Use API to provision/manage VPS
# But still need SSH for actual deployment
curl -X POST "https://api.hostinger.com/v1/vps/create" \
  -H "Authorization: Bearer $API_TOKEN" \
  -d '{"plan":"vps-1","os":"ubuntu22.04"}'

# Then SSH in for deployment
ssh root@vps-ip
```

**Pros:**
- Automate VPS provisioning
- Automate DNS/SSL setup

**Cons:**
- Limited documentation
- No app deployment capabilities
- Still need SSH for actual deployment

**Verdict:** Use for VPS management, but not app deployment

---

## Recommended Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Hostinger VPS                             │
│                   (Ubuntu 22.04)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Nginx      │  │   FastAPI    │  │ PostgreSQL   │     │
│  │  (Reverse    │  │   Backend    │  │   Database   │     │
│  │   Proxy)     │  │   :8000      │  │   :5432      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                    │                                       │
│  ┌─────────────────▼─────────────────┐                    │
│  │        Systemd Service           │                    │
│  │     (auto-restart on crash)      │                    │
│  └───────────────────────────────────┘                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Automation Options

### Option A: SSH Script (Simple, Recommended)
Create deployment script that runs via SSH:

```bash
#!/bin/bash
# deploy.sh
HOST="u810045503@<vps-ip>"
PORT=65002
REMOTE_DIR="/var/www/arcade-card-system"

# Upload code
rsync -avz -e "ssh -p $PORT" ~/arcade-card-system/ $HOST:$REMOTE_DIR/

# Deploy
ssh -p $PORT $HOST << 'ENDSSH'
cd $REMOTE_DIR
git pull
source venv/bin/activate
pip install -r requirements.txt
python3 -m alembic upgrade head
sudo systemctl restart arcade-api
ENDSSH
```

### Option B: Ansible (More Advanced)
```yaml
# playbook.yml
- hosts: hostinger_vps
  vars:
    app_dir: /var/www/arcade-card-system
  tasks:
    - name: Deploy application
      git:
        repo: https://github.com/Samirius/arcade-card-system.git
        dest: "{{ app_dir }}"
    - name: Install dependencies
      pip:
        requirements: "{{ app_dir }}/requirements.txt"
        virtualenv: "{{ app_dir }}/venv"
    - name: Run migrations
      command: "{{ app_dir }}/venv/bin/python3 -m alembic upgrade head"
    - name: Restart service
      systemd:
        name: arcade-api
        state: restarted
```

### Option C: GitHub Actions (CI/CD)
```yaml
# .github/workflows/deploy.yml
name: Deploy to Hostinger
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOSTINGER_HOST }}
          username: ${{ secrets.HOSTINGER_USER }}
          port: 65002
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/arcade-card-system
            git pull
            source venv/bin/activate
            pip install -r requirements.txt
            python3 -m alembic upgrade head
            sudo systemctl restart arcade-api
```

---

## Configuration Files

### Systemd Service (`/etc/systemd/system/arcade-api.service`)
```ini
[Unit]
Description=Arcade Card API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/arcade-card-system/backend
Environment="PATH=/var/www/arcade-card-system/venv/bin"
ExecStart=/var/www/arcade-card-system/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx Config (`/etc/nginx/sites-available/arcade-api`)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static frontend
    location / {
        root /var/www/arcade-card-system/dashboard;
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Summary & Recommendation

| Method | FastAPI | PostgreSQL | Automation | Difficulty |
|--------|---------|------------|------------|------------|
| **VPS + SSH** | ✅ | ✅ | ✅ (Scripts) | Medium |
| cPanel | ❌ | ❌ (MySQL only) | ❌ | N/A |
| Hostinger API | N/A | N/A | ⚠️ (VPS only) | Hard |

**Recommended:** VPS with SSH script deployment
- Full stack support
- Easy automation via bash/Ansible
- Scalable
- Cost-effective (~$3.99/mo for basic VPS)

---

## Next Steps

1. ✅ Choose VPS plan (minimum 2GB RAM, 20GB SSD)
2. ✅ Setup SSH keys for automation
3. ✅ Create deployment script (`deploy.sh`)
4. ✅ Configure systemd + Nginx
5. ✅ Test deployment
6. ✅ Setup SSL (Let's Encrypt)

---

**Note:** No native Hostinger MCP server exists. All deployment must be done via SSH automation scripts or Ansible/GitHub Actions.