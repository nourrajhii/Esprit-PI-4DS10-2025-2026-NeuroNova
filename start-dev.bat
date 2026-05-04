@echo off
title EstateMind Dev Launcher
cd /d "%~dp0"

echo ============================================================
echo   EstateMind — Demarrage des services locaux
echo ============================================================
echo.

REM ── VIAGRA Orchestrator (port 8000) ──────────────────────────
echo [1/3] Demarrage VIAGRA Orchestrator (port 8000)...
start "VIAGRA :8000" /min cmd /k "cd /d "%~dp0viagra" && python main.py"

REM ── Villa3D API (port 8056) ───────────────────────────────────
echo [2/3] Demarrage Villa 3D API (port 8056)...
echo      (SD+LoRA charge en arriere-plan — pret dans 2-5 min)
start "Villa3D :8056" /min cmd /k "cd /d "%~dp0travail finale" && python api_service.py"

REM ── Frontend Next.js (port 3000) ─────────────────────────────
echo [3/3] Demarrage Frontend Next.js (port 3000)...
start "Frontend :3000" /min cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================================
echo   Tous les services sont demarres en arriere-plan.
echo   Ouvrez http://localhost:3000 dans votre navigateur.
echo.
echo   Fenetres actives (barre des taches):
echo     VIAGRA :8000    Villa3D :8056    Frontend :3000
echo ============================================================
echo.
timeout /t 8 /nobreak >nul
start http://localhost:3000
