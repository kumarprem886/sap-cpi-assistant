@echo off
echo Starting SAP CPI Assistant Backend...
cd /d "%~dp0backend"

:: ── Detect Python ─────────────────────────────────────────────────────────────
where py >nul 2>&1
if %errorlevel% equ 0 ( set PYCMD=py & goto :py_found )
where python >nul 2>&1
if %errorlevel% equ 0 ( set PYCMD=python & goto :py_found )
echo ERROR: Python not found. Install from https://python.org/downloads/
pause & exit /b 1
:py_found

:: ── Create .env from template if missing ─────────────────────────────────────
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo Created .env from .env.example — edit it to set your AI provider key.
    ) else (
        echo ERROR: .env not found. Create backend\.env with your AI provider settings.
        echo See README.md for examples.
        pause & exit /b 1
    )
)

:: ── Install dependencies if needed ───────────────────────────────────────────
%PYCMD% -m pip install -r requirements.txt -q --disable-pip-version-check

echo.
echo Backend running at http://localhost:8000
echo API Docs at        http://localhost:8000/docs
echo.

%PYCMD% -m uvicorn main:app --reload --port 8000
pause
