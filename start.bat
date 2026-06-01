@echo off
title SAP CPI Assistant
echo.
echo  ========================================================
echo    SAP CPI Assistant
echo  ========================================================
echo.

:: ── Python check ───────────────────────────────────────────────────────────────
where py >nul 2>&1
if not errorlevel 1 (set PYCMD=py) else (
    where python >nul 2>&1
    if not errorlevel 1 (set PYCMD=python) else (
        echo  ERROR: Python not found. Install from https://python.org
        pause & exit /b 1
    )
)
echo  [OK] Python

:: ── Node check ─────────────────────────────────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)
echo  [OK] Node.js

:: ── .env setup ─────────────────────────────────────────────────────────────────
if not exist "%~dp0backend\.env" if exist "%~dp0backend\.env.example" (
    copy /Y "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
    echo  [OK] Created backend\.env
)

:: ── Python packages ────────────────────────────────────────────────────────────
%PYCMD% -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  Installing Python packages (first time only)...
    %PYCMD% -m pip install -r "%~dp0backend\requirements.txt" -q
    if errorlevel 1 (echo  ERROR: pip install failed & pause & exit /b 1)
)
echo  [OK] Backend ready

:: ── Node packages ──────────────────────────────────────────────────────────────
if not exist "%~dp0frontend\node_modules" (
    echo  Installing Node packages (first time only)...
    pushd "%~dp0frontend"
    npm install
    popd
    if errorlevel 1 (echo  ERROR: npm install failed & pause & exit /b 1)
)
echo  [OK] Frontend ready

:: ── Launch servers via helper scripts ──────────────────────────────────────────
:: Using helper .bat files avoids all quoting/cd issues
echo.
echo  Starting Backend  (http://localhost:8000)...
start "SAP CPI Backend"  cmd /k "%~dp0start-backend.bat"

echo  Starting Frontend (http://localhost:5173)...
start "SAP CPI Frontend" cmd /k "%~dp0start-frontend.bat"

:: ── Open browser ───────────────────────────────────────────────────────────────
echo.
echo  Waiting 10 seconds for Vite to compile...
timeout /t 10 /nobreak >nul
start "" http://localhost:5173

echo.
echo  ========================================================
echo    App:    http://localhost:5173
echo    API:    http://localhost:8000/docs
echo    Login:  admin@cpi.local  /  admin123
echo  ========================================================
echo.
echo  Close the Backend and Frontend windows to stop.
pause
