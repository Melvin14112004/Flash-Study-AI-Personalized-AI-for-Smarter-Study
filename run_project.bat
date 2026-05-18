@echo off
rem Change directory to the script's location
cd /d "%~dp0"

echo Current directory is:
echo %cd%
echo.
pause

rem === 1. ACTIVATE VIRTUAL ENVIRONMENT ===
echo Activating venv...
call "venv\Scripts\activate.bat"
echo.

rem === 2. START BACKEND (FLASK) ===
echo Starting backend...
start "Backend" cmd /k "cd /d \"%~dp0backend\" && python app.py"
echo.

rem === 3. START FRONTEND (NPM/DEV) ===
echo Starting frontend...
start "Frontend" cmd /k "cd /d \"%~dp0frontend\" && npm run dev"
echo.

rem === 4. WAIT & OPEN BROWSER ===
echo Waiting 10 seconds for servers...
timeout /t 10 /nobreak >nul

echo Opening browser...
start "" "http://localhost:5173"

echo.
echo Launch complete.
pause