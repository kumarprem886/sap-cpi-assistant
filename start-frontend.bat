@echo off
title SAP CPI - Frontend
cd /d "%~dp0frontend"

where node >nul 2>&1
if errorlevel 1 echo ERROR: Node.js not found. Get it at https://nodejs.org && pause && exit /b 1

if not exist "node_modules" npm install

echo.
echo Frontend: http://localhost:5173
echo.
npm run dev
pause
