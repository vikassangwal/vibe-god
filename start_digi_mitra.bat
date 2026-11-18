@echo off
title DIGI MITRA 2.0
cd /d C:\Users\HP\Documents\WifeGod
python -m uvicorn digi_mitra.web_dashboard.server:app --host 0.0.0.0 --port 8000
pause
