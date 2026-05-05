#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  EstateMind — Azure VM Setup Script
#  Run this ON YOUR AZURE VM after SSH-ing in:
#    chmod +x deploy-azure.sh && ./deploy-azure.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e
echo "=================================================="
echo "  EstateMind — Azure VM Setup"
echo "=================================================="

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/7] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y -q \
    git curl wget unzip \
    ca-certificates gnupg lsb-release \
    htop ncdu

# ── 2. Docker ─────────────────────────────────────────────────────────────────
echo "[2/7] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo bash
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to re-login for group changes."
else
    echo "Docker already installed: $(docker --version)"
fi

# ── 3. Docker Compose v2 ──────────────────────────────────────────────────────
echo "[3/7] Installing Docker Compose v2..."
if ! docker compose version &>/dev/null 2>&1; then
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
    sudo curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    echo "Docker Compose installed: $(docker compose version)"
else
    echo "Docker Compose already installed: $(docker compose version)"
fi

# ── 4. Clone / update project ─────────────────────────────────────────────────
echo "[4/7] Cloning EstateMind from GitHub..."
REPO_URL="https://github.com/nourrajhii/Esprit-PI-4DS10-2025-2026-NeuroNova.git"
APP_DIR="$HOME/estatemind"

if [ -d "$APP_DIR/.git" ]; then
    echo "Repo exists, pulling latest..."
    cd "$APP_DIR"
    git pull origin main || git pull origin master || true
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# ── 5. Environment file ────────────────────────────────────────────────────────
echo "[5/7] Checking .env file..."
if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.azure.example" ]; then
        cp "$APP_DIR/.env.azure.example" "$APP_DIR/.env"
        echo ""
        echo "============================================================"
        echo "  ACTION REQUIRED: Edit .env with your real credentials:"
        echo "    nano $APP_DIR/.env"
        echo ""
        echo "  At minimum, fill in:"
        echo "    SERVER_HOST = your VM public IP"
        echo "    GEMINI_API_KEY = your Gemini API key"
        echo "    MONGODB_URI = your Atlas connection string"
        echo "    JWT_SECRET / JWT_REFRESH_SECRET"
        echo "    SMTP_USER / SMTP_PASS"
        echo "    STRIPE keys"
        echo "    TRIPO_API_KEY"
        echo "============================================================"
        echo ""
        read -p "Press Enter after you have filled in .env to continue..."
    else
        echo "ERROR: .env.azure.example not found. Create .env manually."
        exit 1
    fi
else
    echo ".env already exists, skipping."
fi

# ── 6. Build & start services ─────────────────────────────────────────────────
echo "[6/7] Building Docker images (this takes 10-20 minutes first time)..."
cd "$APP_DIR"

# Pull base images first for better layer caching
docker pull node:20-alpine &
docker pull python:3.11-slim &
docker pull nginx:alpine &
docker pull redis:7-alpine &
docker pull mysql:8.0 &
wait

docker compose -f docker-compose.azure.yml build --parallel
docker compose -f docker-compose.azure.yml up -d

# ── 7. Status ─────────────────────────────────────────────────────────────────
echo "[7/7] Waiting 30s for services to start..."
sleep 30

echo ""
echo "=================================================="
echo "  Service Status:"
echo "=================================================="
docker compose -f docker-compose.azure.yml ps

# Quick health check
VM_IP=$(curl -s https://ipinfo.io/ip 2>/dev/null || echo "YOUR_VM_IP")
echo ""
echo "=================================================="
echo "  Your EstateMind is running at:"
echo ""
echo "  Frontend:   http://${VM_IP}:3001"
echo "  Backend:    http://${VM_IP}:4000"
echo "  VIAGRA AI:  http://${VM_IP}:8000"
echo "  Full site:  http://${VM_IP}:80"
echo ""
echo "  Check health: curl http://${VM_IP}:8000/health"
echo "=================================================="
