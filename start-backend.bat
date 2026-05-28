@echo off
echo Starting SAP CPI Assistant Backend...
cd /d "%~dp0backend"

IF NOT EXIST ".env" (
    echo.
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your ANTHROPIC_API_KEY
    echo.
    pause
    exit /b 1
)

set PYTHON=C:\Users\prem.am.kumar\AppData\Local\Python\pythoncore-3.14-64\python.exe
"%PYTHON%" -m uvicorn main:app --reload --port 8080
pause
