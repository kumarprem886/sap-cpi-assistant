@echo off
title SAP CPI - Backend
cd /d "%~dp0backend"

where py >nul 2>&1
if not errorlevel 1 goto :run
where python >nul 2>&1
if not errorlevel 1 goto :run
echo ERROR: Python not found. Get it from https://python.org
pause
exit /b 1

:run
if not exist ".env" if exist ".env.example" copy /Y ".env.example" ".env" >nul

echo.
echo Backend: http://localhost:8000
echo Docs:    http://localhost:8000/docs
echo.
py -m uvicorn main:app --port 8000
pause
