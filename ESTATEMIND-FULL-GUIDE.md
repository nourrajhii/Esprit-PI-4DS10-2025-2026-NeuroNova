# EstateMind — Complete Architecture & Deployment Guide

> **Live Azure URL:** http://158.158.44.182:3001  
> **AI Orchestrator:** http://158.158.44.182:8000  
> **Backend API:** http://158.158.44.182:4000  
> **GitHub:** https://github.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [All Services & Ports](#2-all-services--ports)
3. [Local Development](#3-local-development)
4. [Azure Cloud Deployment](#4-azure-cloud-deployment)
5. [Adding HTTPS with a Custom Domain](#5-adding-https-with-a-custom-domain)
6. [Common Operations](#6-common-operations)
7. [Troubleshooting](#7-troubleshooting)
8. [Environment Variables Reference](#8-environment-variables-reference)

---

## 1. System Architecture

```
                         INTERNET
                             │
                    ┌────────▼────────┐
                    │   Azure VM      │
                    │  Spain Central  │
                    │ 158.158.44.182  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Nginx :80      │ ← Entry point
                    │  (reverse proxy)│
                    └────┬───────┬───┘
                         │       │
              ┌──────────▼─┐   ┌─▼──────────────┐
              │ Frontend   │   │  Backend API    │
              │ Next.js    │   │  Node.js        │
              │ :3001      │   │  :4000          │
              └──────┬─────┘   └─┬───────────────┘
                     │           │
                     │    ┌──────▼──────────────┐
                     │    │   MongoDB Atlas      │
                     │    │   (cloud, shared)    │
                     │    └─────────────────────┘
                     │
              ┌──────▼──────────────────────────┐
              │      VIAGRA Orchestrator :8000   │
              │  (AI request router / FastAPI)   │
              └──┬────┬────┬────┬────┬────┬─────┘
                 │    │    │    │    │    │
    ┌────────────┘    │    │    │    │    └────────────┐
    │            ┌────┘    │    │    └────┐            │
    ▼            ▼         ▼    ▼         ▼            ▼
 :8001        :8002     :8003 :8004    :8005-8007   :8010
Recommender   Devis    Legal Forecast  Price/Invest  Lifestyle
  Agent       Agent    Agent  Agent    /Geo Agents    Agent
    │            │        │
    └────────────┴────────┴──── all use: Gemini API (cloud)
                                         MongoDB Atlas
```

### Local vs Cloud Differences

| Component | Local (`start-dev.bat`) | Azure (`docker-compose.azure.yml`) |
|-----------|------------------------|-------------------------------------|
| LLM | Ollama (`llama3.2:3b`) local | Gemini API (cloud) |
| 3D generation | SD+LoRA (GPU, full) | Tripo API only (stub) |
| Frontend URL | http://localhost:3000 | http://158.158.44.182:3001 |
| Orchestrator | http://localhost:8000 | http://158.158.44.182:8000 |
| DB | MongoDB Atlas (shared) | MongoDB Atlas (same) |

---

## 2. All Services & Ports

### Azure (live)

| Service | Container | Port | URL | Notes |
|---------|-----------|------|-----|-------|
| Nginx | `immo-nginx` | **80** | http://158.158.44.182 | Entry point |
| Frontend | `immo-frontend` | **3001** | http://158.158.44.182:3001 | Next.js |
| Backend | `immo-backend` | **4000** | http://158.158.44.182:4000 | Node.js / Auth / Stripe |
| VIAGRA AI | `immo-viagra` | **8000** | http://158.158.44.182:8000 | AI Orchestrator |
| Recommender | `immo-advisor-backend` | 8001 | http://158.158.44.182:8001 | Property advisor |
| Devis | `immo-nour-devis` | 8002 | http://158.158.44.182:8002 | Cost estimator |
| Legal | `immo-nour2-legal` | 8003 | http://158.158.44.182:8003 | Legal AI (Gemini) |
| Forecast | `immo-forecast` | 8004 | http://158.158.44.182:8004 | Price forecasting |
| Price | `immo-price-predictor` | 8005 | http://158.158.44.182:8005 | Price prediction |
| Investment | `immo-investment-scorer` | 8006 | http://158.158.44.182:8006 | Investment score |
| Geo | `immo-geo-advisor` | 8007 | http://158.158.44.182:8007 | Location advisor |
| Lifestyle | `immo-lifestyle-match` | 8010 | http://158.158.44.182:8010 | Lifestyle match |
| Dhia | `immo-dhia` | 8055 | http://158.158.44.182:8055 | Data scraper agent |
| Villa3D | `immo-villa3d` | 8056 | http://158.158.44.182:8056 | 3D stub (Tripo API) |
| Redis | `immo-redis` | - | internal | Cache |
| MySQL | `immo-mysql` | - | internal | Local DB |

### Health Check URLs

```bash
# Full system health
curl http://158.158.44.182:8000/health

# Individual services
curl http://158.158.44.182:4000/health
curl http://158.158.44.182:8056/health
curl http://158.158.44.182/health/legal
curl http://158.158.44.182/health/viagra
```

---

## 3. Local Development

### Requirements
- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.ai/download) installed and running
- Git

### Start everything
```batch
# Double-click or run:
start-dev.bat
```

This starts:
1. **Backend Node.js** → port 4000
2. **VIAGRA Orchestrator** → port 8000
3. **Villa3D (SD+LoRA)** → port 8056
4. **Frontend Next.js** → port 3000

Then open: http://localhost:3000

### Pull Ollama model (first time only)
```bash
ollama pull llama3.2:3b
```

### Start individual agents (if needed)
```bash
# Legal agent inner process
cd nour2/Esprit-PI-4DS10-2025-2026-NeuroNova-AgentLegal
python -m uvicorn app.main:app --host 127.0.0.1 --port 8011

# Devis agent inner process
cd nour/Esprit-PI-4DS10-2025-2026-NeuroNova-Agent_Devis
set PYTHONIOENCODING=utf-8
python -m uvicorn api:app --host 127.0.0.1 --port 8009
```

---

## 4. Azure Cloud Deployment

### VM Details

| Property | Value |
|----------|-------|
| Name | `estatemind-vm` |
| Resource Group | `estatemind-spain-rg` |
| Region | Spain Central |
| Size | Standard_B2als_v2 (2 vCPU, 4GB RAM) |
| OS | Ubuntu 22.04 LTS |
| Public IP | `158.158.44.182` |
| SSH Key | `C:\Users\yosri\.ssh\id_rsa` |
| Monthly Cost | ~$24/month (from $100 student credit) |

### SSH Access
```powershell
# From your Windows machine:
ssh -i C:\Users\yosri\.ssh\id_rsa azureuser@158.158.44.182
```

### Deploying Updates
```bash
# On your local machine — push changes:
git add .
git commit -m "your changes"
git push origin estate-mind/ai-agents:estate-mind/deploy

# On the VM — pull and restart:
cd ~/estatemind
git pull
sudo docker compose -f docker-compose.azure.yml up -d --build
```

### First-time Deployment (on a new VM)
```bash
# SSH into VM then run:
curl -fsSL https://raw.githubusercontent.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova/estate-mind/deploy/deploy-azure.sh | bash
```

### Stop VM to save credits
```powershell
# Stop (saves compute cost, disk persists):
az vm deallocate --resource-group estatemind-spain-rg --name estatemind-vm

# Restart:
az vm start --resource-group estatemind-spain-rg --name estatemind-vm
```

---

## 5. Adding HTTPS with a Custom Domain

### Step 1 — Point your domain to the VM

In your domain registrar DNS settings, add:

| Type | Name | Value |
|------|------|-------|
| `A` | `@` | `158.158.44.182` |
| `A` | `www` | `158.158.44.182` |

Wait 5–60 minutes for DNS to propagate. Test with:
```bash
ping yourdomain.com
# Should resolve to 158.158.44.182
```

### Step 2 — Install Certbot on the VM

```bash
ssh -i C:\Users\yosri\.ssh\id_rsa azureuser@158.158.44.182

# Install certbot
sudo apt-get install -y certbot

# Stop nginx temporarily
sudo docker compose -f ~/estatemind/docker-compose.azure.yml stop nginx

# Get certificate (replace yourdomain.com)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com \
  --email dhia.romdhane@esprit.tn --agree-tos --non-interactive

# Certs saved to /etc/letsencrypt/live/yourdomain.com/
```

### Step 3 — Update nginx config for HTTPS

```bash
# On the VM:
cat > ~/estatemind/nginx.azure.conf << 'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 50M;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://immo-frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://immo-backend:4000/;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }

    location /viagra/ {
        proxy_pass http://immo-viagra:8000/;
        proxy_read_timeout 300s;
    }
}
EOF
```

### Step 4 — Mount certs into nginx container

Update `docker-compose.azure.yml` nginx section:
```yaml
nginx:
  volumes:
    - ./nginx.azure.conf:/etc/nginx/conf.d/default.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
  ports:
    - "80:80"
    - "443:443"
```

### Step 5 — Update .env and rebuild frontend

```bash
# On the VM, edit .env:
nano ~/estatemind/.env

# Change these 3 lines:
SERVER_HOST=yourdomain.com
NEXT_PUBLIC_VIAGRA_URL=https://yourdomain.com:8000
NEXT_PUBLIC_BACKEND_URL=https://yourdomain.com:4000

# Rebuild frontend with new domain baked in:
cd ~/estatemind
sudo docker compose -f docker-compose.azure.yml build frontend
sudo docker compose -f docker-compose.azure.yml up -d
```

### Step 6 — Auto-renew SSL (free, every 90 days)

```bash
# Add cron job for auto-renewal:
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f /home/azureuser/estatemind/docker-compose.azure.yml restart nginx") | crontab -
```

---

## 6. Common Operations

### View logs
```bash
# All services:
sudo docker compose -f ~/estatemind/docker-compose.azure.yml logs -f

# One service:
sudo docker logs immo-viagra --tail=50 -f
sudo docker logs immo-frontend --tail=50 -f
sudo docker logs immo-backend --tail=50 -f
sudo docker logs immo-nour2-legal --tail=50 -f
```

### Restart one service
```bash
sudo docker compose -f ~/estatemind/docker-compose.azure.yml restart viagra
sudo docker compose -f ~/estatemind/docker-compose.azure.yml restart frontend
```

### Check memory usage
```bash
sudo docker stats --no-stream
free -h
```

### Clean up disk space
```bash
sudo docker system prune -f
sudo docker image prune -f
```

### Update all services
```bash
cd ~/estatemind
git pull
sudo docker compose -f docker-compose.azure.yml up -d --build
```

---

## 7. Troubleshooting

### Error: 401 on `/auth/me`
✅ **Normal** — the browser checks if a user is logged in on every page load. When no user is logged in, 401 is the correct response. Once you log in, it disappears.

### Error: `A listener indicated an asynchronous response...`
✅ **Normal** — this comes from a browser extension (ad blocker, React DevTools), not your code. Ignore it.

### Error: 500 on `/api/listings`
Check that the frontend container has MongoDB env vars:
```bash
sudo docker exec immo-frontend env | grep SCRAPED
# Should show: SCRAPED_DB_URI=mongodb+srv://...
```
If missing, restart: `sudo docker compose -f docker-compose.azure.yml up -d frontend`

### Error: Villa3D timeout (port 8056)
The stub is running but SD image generation is disabled in cloud. 3D conversion from uploaded images still works via Tripo API.

### AI agents not responding
```bash
# Check all agent health:
sudo docker exec immo-nginx wget -qO- http://immo-viagra:8000/health

# Restart all agents:
sudo docker compose -f ~/estatemind/docker-compose.azure.yml restart
```

### VM ran out of memory
```bash
free -h  # Check memory
sudo docker stats --no-stream  # Check per-container

# Add swap space (2GB):
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### GEMINI_API_KEY not working
```bash
# Check it's in the .env:
grep GEMINI ~/estatemind/.env

# Test it:
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=YOUR_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Say OK"}]}]}'
```

---

## 8. Environment Variables Reference

### Required on Azure VM (`~/estatemind/.env`)

```env
# ── VM Settings ───────────────────────────────────────────────
SERVER_HOST=158.158.44.182          # or your domain name

# ── AI APIs ───────────────────────────────────────────────────
GEMINI_API_KEY=                     # Google AI Studio: https://aistudio.google.com/app/apikey
SERPAPI_KEY=                        # https://serpapi.com/
TRIPO_API_KEY=                      # https://platform.tripo3d.ai/

# ── MongoDB Atlas ─────────────────────────────────────────────
MONGODB_URI=mongodb+srv://...       # https://cloud.mongodb.com/
SCRAPED_DB_URI=mongodb+srv://...

# ── Frontend (baked at build time) ────────────────────────────
NEXT_PUBLIC_VIAGRA_URL=http://158.158.44.182:8000
NEXT_PUBLIC_BACKEND_URL=http://158.158.44.182:4000
NEXT_PUBLIC_VILLA3D_API_URL=http://158.158.44.182:8056

# ── Backend Auth ──────────────────────────────────────────────
JWT_SECRET=
JWT_REFRESH_SECRET=

# ── Email (Gmail App Password) ────────────────────────────────
SMTP_USER=                          # Your Gmail
SMTP_PASS=                          # https://myaccount.google.com/apppasswords

# ── Stripe ────────────────────────────────────────────────────
STRIPE_SECRET_KEY=                  # https://dashboard.stripe.com/test/apikeys
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# ── Twilio WhatsApp ───────────────────────────────────────────
TWILIO_ACCOUNT_SID=                 # https://console.twilio.com/
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Local only (`.env` at project root)

Same as above, plus:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_HOST=http://localhost:11434
```

---

## GitHub Branches

| Branch | Contents |
|--------|----------|
| `main` | README only |
| `estate-mind/deploy` | **Full platform** (this is what Azure deploys) |
| `estate-mind/ai-agents` | Development branch |
| `AgentLegal` | Legal agent standalone |
| `Agent_Devis` | Devis agent standalone |
| `Front-end-and-back-end-plateform-estatemind` | Original frontend/backend |

**Always push to:** `estate-mind/deploy` for Azure to pick up changes.

---

*Generated by Claude — EstateMind NeuroNova Team — May 2026*
