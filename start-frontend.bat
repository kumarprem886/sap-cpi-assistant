@echo off
echo Starting SAP CPI Assistant Frontend...
cd /d "%~dp0frontend"

:: ── Check Node.js ─────────────────────────────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found.
    echo Install Node.js 20+ from https://nodejs.org/ and make sure it is in PATH.
    pause & exit /b 1
)

:: ── Install dependencies if node_modules missing ──────────────────────────────
if not exist "node_modules" (
    echo Installing Node.js dependencies (first time)...
    npm install
    if %errorlevel% neq 0 (
        echo ERROR: npm install failed.
        pause & exit /b 1
    )
)

echo.
echo Frontend running at http://localhost:5173
echo.

npm run dev
pause
