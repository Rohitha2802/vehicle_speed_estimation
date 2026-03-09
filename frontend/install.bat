@echo off
REM Installation script for React frontend
REM This script installs dependencies and starts the development server

echo ========================================
echo Vehicle Monitoring System - React Setup
echo ========================================
echo.

echo Step 1: Installing dependencies...
echo This may take a few minutes...
echo.

cd /d "%~dp0"
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: npm install failed!
    echo Please check your Node.js installation.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo To start the development server, run:
echo   npm run dev
echo.
echo Or double-click: start-dev.bat
echo.
pause
