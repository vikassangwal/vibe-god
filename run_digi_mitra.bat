@echo off
title DIGI MITRA - AI Super-Agent
cd /d "C:\Users\HP\Documents\WifeGod"
set PYTHONIOENCODING=utf-8

echo ========================================================
echo               ?? DIGI MITRA 2.0 - SOVEREIGN AI
echo       Autonomous Super-Agent (Trading + eMitra + Mobile)
echo ========================================================
echo.
echo Starting Control Panel Server...
echo Windows Laptop: http://localhost:8000
echo Mobile Phone: Open laptop IP shown in console below
echo.

start "" http://localhost:8000
python -m uvicorn digi_mitra.web_dashboard.server:app --host 0.0.0.0 --port 8000
pause
