@echo off
title EstateMind Dev Launcher
cd /d "%~dp0"

echo ============================================================
echo   EstateMind — Demarrage des services locaux
echo ============================================================
echo.

REM ── Backend Node.js (port 4000) — Auth, Listings, Stripe ─────
echo [1/4] Demarrage Backend Node.js (port 4000)...
start "Backend :4000" /min cmd /k "cd /d "%~dp0backend" && node src/server.js"

REM ── VIAGRA Orchestrator (port 8000) ──────────────────────────
echo [2/4] Demarrage VIAGRA Orchestrator (port 8000)...
start "VIAGRA :8000" /min cmd /k "cd /d "%~dp0viagra" && python main.py"

REM ── Villa3D API (port 8056) ───────────────────────────────────
echo [3/4] Demarrage Villa 3D API (port 8056)...
echo      (SD+LoRA charge en arriere-plan — pret dans 2-5 min)
start "Villa3D :8056" /min cmd /k "cd /d "%~dp0travail finale" && python api_service.py"

REM ── Frontend Next.js (port 3000) ─────────────────────────────
echo [4/4] Demarrage Frontend Next.js (port 3000)...
start "Frontend :3000" /min cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================================
echo   Tous les services sont demarres en arriere-plan.
echo   Ouvrez http://localhost:3000 dans votre navigateur.
echo.
echo   Fenetres actives (barre des taches):
echo     Backend :4000   VIAGRA :8000   Villa3D :8056   Frontend :3000
echo ============================================================
echo.
timeout /t 10 /nobreak >nul
start http://localhost:3000
