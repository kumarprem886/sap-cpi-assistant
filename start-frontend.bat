@echo off
echo Starting SAP CPI Assistant Frontend...
cd /d "%~dp0frontend"

SET NODE_PATH=C:\nodejs
SET PATH=%NODE_PATH%;%PATH%

IF NOT EXIST "%NODE_PATH%\node.exe" (
    echo.
    echo ERROR: Node.js not found at C:\nodejs
    echo Please re-run the Node.js installation.
    echo.
    pause
    exit /b 1
)

IF NOT EXIST "node_modules" (
    echo Installing dependencies...
    "%NODE_PATH%\npm.cmd" install
)

"%NODE_PATH%\npm.cmd" run dev
pause
