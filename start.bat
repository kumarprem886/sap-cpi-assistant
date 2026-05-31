@echo off
title SAP CPI Assistant
setlocal

echo.
echo  ========================================================
echo    SAP CPI Assistant — Starting up
echo  ========================================================
echo.

:: ── Detect Python (py launcher preferred, fallback to python) ─────────────────
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYCMD=py
    goto :python_ok
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYCMD=python
    goto :python_ok
)
echo  ERROR: Python not found.
echo  Install Python 3.10+ from https://python.org/downloads/
echo  During install: tick "Add Python to PATH"
echo.
pause
exit /b 1
:python_ok
echo  [OK] Python  (%PYCMD%)

:: ── Detect Node.js ────────────────────────────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Node.js not found.
    echo  Install Node.js 20+ from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
echo  [OK] Node.js (node + npm)

:: ── Create .env from template if missing ─────────────────────────────────────
if not exist "%~dp0backend\.env" (
    if exist "%~dp0backend\.env.example" (
        copy /Y "%~dp0backend\.env.example" "%~dp0backend\.env" >nul
        echo  [OK] Created backend\.env from .env.example
        echo.
        echo  NOTE: The app defaults to Ollama (local AI, free).
        echo        To use a cloud AI provider, open backend\.env
        echo        and set your API key. See README.md for options.
        echo.
    )
)

:: ── Install Python dependencies (first time or if requirements changed) ───────
echo  Checking Python dependencies...
%PYCMD% -m pip install -r "%~dp0backend\requirements.txt" -q --disable-pip-version-check
if %errorlevel% neq 0 (
    echo  ERROR: pip install failed. Run manually:
    echo    cd backend
    echo    py -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo  [OK] Python dependencies ready

:: ── Install frontend dependencies if node_modules missing ────────────────────
if not exist "%~dp0frontend\node_modules" (
    echo  Installing Node.js dependencies (first time, takes 1-2 minutes)...
    cd /d "%~dp0frontend"
    npm install
    if %errorlevel% neq 0 (
        echo  ERROR: npm install failed.
        pause
        exit /b 1
    )
    echo  [OK] Node.js dependencies installed
) else (
    echo  [OK] Node.js dependencies ready
)

:: ── Start Backend ─────────────────────────────────────────────────────────────
echo.
echo  Starting Backend  (http://localhost:8000) ...
start "SAP CPI - Backend" cmd /k "cd /d %~dp0backend && %PYCMD% -m uvicorn main:app --reload --port 8000"

:: ── Start Frontend ────────────────────────────────────────────────────────────
echo  Starting Frontend (http://localhost:5173) ...
start "SAP CPI - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: ── Wait then open browser ────────────────────────────────────────────────────
echo.
echo  Waiting for servers to initialise...
timeout /t 6 /nobreak >nul

echo  Opening browser...
start "" "http://localhost:5173"

echo.
echo  ========================================================
echo    SAP CPI Assistant is running!
echo.
echo    App      : http://localhost:5173
echo    API      : http://localhost:8000
echo    API Docs : http://localhost:8000/docs
echo.
echo    Default login:  admin@cpi.local  /  admin123
echo  ========================================================
echo.
echo  Close the two terminal windows to stop the servers.
echo.
