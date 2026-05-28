@echo off
title SAP CPI Assistant

echo.
echo  Starting SAP CPI Assistant...
echo  ================================
echo.

:: ── Start Backend ────────────────────────────────────────────────────────────
echo  [1/2] Starting Backend (FastAPI)...
start "SAP CPI - Backend" cmd /k "cd /d %~dp0backend && py -m uvicorn main:app --reload --port 8000"

:: ── Start Frontend ────────────────────────────────────────────────────────────
echo  [2/2] Starting Frontend (Vite)...
start "SAP CPI - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: ── Wait then open browser ────────────────────────────────────────────────────
echo.
echo  Waiting for servers to start...
timeout /t 6 /nobreak >nul

echo  Opening browser...
start "" "http://localhost:5173/sap-cpi-assistant/"

echo.
echo  Both servers are running.
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173/sap-cpi-assistant/
echo.
echo  Close the two terminal windows to stop the servers.
echo.
