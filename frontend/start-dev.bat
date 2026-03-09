@echo off
REM Start development server
REM Make sure you've run install.bat first!

echo ========================================
echo Starting React Development Server...
echo ========================================
echo.
echo The app will open at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd /d "%~dp0"
call npm run dev

pause
