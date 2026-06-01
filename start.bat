@echo off
title SAP CPI Assistant
echo.
echo  ========================================================
echo    SAP CPI Assistant - Starting up...
echo  ========================================================
echo.

:: Check Python
where py >nul 2>&1
if not errorlevel 1 goto :have_py
where python >nul 2>&1
if not errorlevel 1 goto :have_py
echo  ERROR: Python not found. Install from https://python.org
pause & exit /b 1
:have_py

:: Check Node
where node >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)

:: Create .env if missing
if not exist "%~dp0backend\.env" (
    if exist "%~dp0backend\.env.example" (
        copy /Y "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
        echo  Created backend\.env - add your AI API key to use AI features
    )
)

:: Install Python deps only if uvicorn is missing
py -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo  Installing Python packages - this takes a minute on first run...
    py -m pip install -r "%~dp0backend\requirements.txt" -q
    if errorlevel 1 (
        echo  ERROR: pip install failed
        pause & exit /b 1
    )
)
echo  [OK] Backend ready

:: Install Node deps only if missing
if not exist "%~dp0frontend\node_modules" (
    echo  Installing Node packages - this takes a minute on first run...
    cd /d "%~dp0frontend"
    npm install
    cd /d "%~dp0"
    if errorlevel 1 (
        echo  ERROR: npm install failed
        pause & exit /b 1
    )
)
echo  [OK] Frontend ready

:: Start servers
echo.
echo  Starting backend...
start "SAP CPI - Backend" cmd /k "cd /d %~dp0backend && py -m uvicorn main:app --reload --port 8000"

echo  Starting frontend...
start "SAP CPI - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait and open browser
echo.
echo  Waiting for servers (5 sec)...
timeout /t 5 /nobreak >nul

start "" http://localhost:5173

echo.
echo  ========================================================
echo    App:      http://localhost:5173
echo    API:      http://localhost:8000
echo    Login:    admin@cpi.local / admin123
echo  ========================================================
echo.
echo  Close Backend + Frontend windows to stop the app.
pause
