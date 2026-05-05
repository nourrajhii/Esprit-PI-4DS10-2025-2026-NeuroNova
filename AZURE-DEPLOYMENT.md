# EstateMind — Azure Student Deployment Guide

## What you have

| Environment | Command | Works today |
|-------------|---------|-------------|
| **Local** | `start-dev.bat` | ✅ All services on localhost |
| **Azure** | `docker-compose -f docker-compose.azure.yml up -d` | After this guide ↓ |

---

## Cost estimate (Azure Student — $100 credit)

| Resource | Size | Cost/month | Notes |
|----------|------|-----------|-------|
| VM (all backend) | Standard_B2s (2 vCPU, 4GB) | ~$35 | Runs all AI agents |
| Public IP | Static | ~$3 | Fixed address |
| OS Disk | 64GB SSD | ~$5 | Included in VM |
| **Total** | | **~$43/month** | **$100 lasts ~2.5 months** |

> **No Ollama in cloud** → uses Gemini API (already configured, free quota).  
> **No Villa3D SD model** → Tripo API still works, SD generation skipped.  
> **MongoDB Atlas** → stays as-is, no Azure DB needed.

---

## Step 1 — Create the Azure VM

### Option A: Azure Portal (easiest)

1. Go to **portal.azure.com** → click **"Create a resource"**
2. Search **"Virtual machine"** → click **Create**
3. Fill in:
   - **Resource group**: `estatemind-rg` (create new)
   - **VM name**: `estatemind-vm`
   - **Region**: `France Central` or `West Europe` (closest to Tunisia)
   - **Image**: `Ubuntu Server 22.04 LTS`
   - **Size**: Click "See all sizes" → search `B2s` → select **Standard_B2s** (2 vCPU, 4GB RAM)
   - **Authentication**: `SSH public key` → generate new pair → **download the .pem file**
   - **Username**: `azureuser`
4. Click **"Next: Disks"** → keep default (Premium SSD, 64GB)
5. Click **"Next: Networking"** → under **"Public inbound ports"** select **"Allow selected ports"**:
   - ✅ SSH (22)
   - ✅ HTTP (80)
6. Click **"Review + Create"** → **"Create"**

Wait ~2 minutes for deployment to complete.

### Option B: Azure CLI (faster, run from your Windows terminal)

```bash
# Install Azure CLI first: https://docs.microsoft.com/cli/azure/install-azure-cli-windows
az login

# Create everything with one command
az group create --name estatemind-rg --location francecentral

az vm create \
  --resource-group estatemind-rg \
  --name estatemind-vm \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard

# Get your VM's public IP
az vm show --resource-group estatemind-rg --name estatemind-vm \
  --show-details --query publicIps -o tsv
```

---

## Step 2 — Open the required ports

In Azure Portal → your VM → **Networking** → **Add inbound port rule** for each:

| Port | Service | Priority |
|------|---------|----------|
| 22 | SSH | 100 |
| 80 | Nginx (full site) | 110 |
| 3001 | Frontend direct | 120 |
| 4000 | Backend API | 130 |
| 8000 | VIAGRA AI | 140 |
| 8001-8010 | AI agents | 150 |
| 8055 | Dhia agent | 160 |

Or with Azure CLI (batch):
```bash
for port in 3001 4000 8000 8001 8002 8003 8004 8005 8006 8007 8010 8055; do
  az network nsg rule create \
    --resource-group estatemind-rg \
    --nsg-name estatemind-vmNSG \
    --name "allow-$port" \
    --protocol Tcp \
    --priority $((200 + port)) \
    --destination-port-ranges $port \
    --access Allow
done
```

---

## Step 3 — Note your VM's public IP

```bash
# Get it from Azure CLI:
az vm show --resource-group estatemind-rg --name estatemind-vm \
  --show-details --query publicIps -o tsv

# Example output: 20.86.123.45
# Save this — you will need it in Step 5
```

---

## Step 4 — SSH into your VM

```bash
# Windows PowerShell or Git Bash:
ssh -i ~/Downloads/estatemind-vm_key.pem azureuser@YOUR_VM_IP

# If you used az --generate-ssh-keys, the key is usually at:
ssh azureuser@YOUR_VM_IP
# (key was saved automatically to ~/.ssh/)
```

---

## Step 5 — Deploy EstateMind on the VM

Once SSH-ed in, run:

```bash
# Download and run the setup script
curl -fsSL https://raw.githubusercontent.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova/main/deploy-azure.sh | bash
```

The script will:
1. Install Docker + Docker Compose
2. Clone your GitHub repository
3. Prompt you to fill in `.env` with real credentials
4. Build all Docker images (~15-20 min first time)
5. Start all services

### Credentials to fill in `.env` on the VM:

```bash
nano ~/estatemind/.env
```

Copy your values from your local `.env` file. The key ones:

```env
SERVER_HOST=20.86.123.45          # your VM public IP from Step 3

GEMINI_API_KEY=AIzaSy...          # same as local
SERPAPI_KEY=7b257b...             # same as local

MONGODB_URI=mongodb+srv://...     # same as local (Atlas stays in cloud)
SCRAPED_DB_URI=mongodb+srv://...  # same as local

JWT_SECRET=estatemind_jwt_secret_2025_secure
JWT_REFRESH_SECRET=estatemind_refresh_secret_2025_secure

SMTP_USER=aoidiyosri@gmail.com
SMTP_PASS=ogds tffe jdvp hfgp

TWILIO_ACCOUNT_SID=AC4288bc...
TWILIO_AUTH_TOKEN=aa84b7...

STRIPE_SECRET_KEY=sk_test_51...
STRIPE_PUBLISHABLE_KEY=pk_test_51...
STRIPE_WEBHOOK_SECRET=whsec_...

TRIPO_API_KEY=tsk_WLCF37...
```

Save with `Ctrl+O`, `Enter`, `Ctrl+X`.

---

## Step 6 — Start services

```bash
cd ~/estatemind
docker compose -f docker-compose.azure.yml up -d

# Watch logs:
docker compose -f docker-compose.azure.yml logs -f

# Check status:
docker compose -f docker-compose.azure.yml ps
```

---

## Step 7 — Verify everything works

```bash
# Replace with your actual VM IP:
VM_IP=20.86.123.45

curl http://$VM_IP:8000/health          # VIAGRA: all agents ok
curl http://$VM_IP:4000/health          # Backend: Node.js ok
curl http://$VM_IP:3001                 # Frontend: HTML response
curl http://$VM_IP/health/legal         # Legal agent via nginx
```

Open your browser: **http://YOUR_VM_IP:3001**

---

## Useful commands (on the VM)

```bash
cd ~/estatemind

# Restart everything
docker compose -f docker-compose.azure.yml restart

# Stop everything
docker compose -f docker-compose.azure.yml down

# Update to latest code
git pull && docker compose -f docker-compose.azure.yml up -d --build

# View logs for one service
docker logs immo-viagra --tail=50 -f
docker logs immo-backend --tail=50 -f
docker logs immo-nour2-legal --tail=50 -f

# Check memory usage
docker stats --no-stream

# Free disk space
docker system prune -f
```

---

## Local stays exactly the same

Your local setup is completely untouched:
```batch
start-dev.bat        # starts Backend :4000, VIAGRA :8000, Villa3D :8056, Frontend :3000
```

Local uses Ollama + full SD model.  
Azure uses Gemini API + Tripo API.  
Both share the same MongoDB Atlas database.

---

## Keeping costs low

- **Stop the VM when not needed** (saves compute cost, keeps disk):
  ```bash
  az vm deallocate --resource-group estatemind-rg --name estatemind-vm
  # Restart:
  az vm start --resource-group estatemind-rg --name estatemind-vm
  ```
- Azure Student static IP = **free while VM is running**, ~$3/month when deallocated
- The VM auto-stops only if you set a schedule — set one in Portal → VM → **Auto-shutdown**

---

## Summary — What you need to give me

To complete deployment I only need **one thing** from you:

> **Your VM public IP** (from Step 3)

Everything else is already configured in your `.env` locally.
