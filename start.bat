@echo off
echo ========================================
echo   Research Sensei - Starting...
echo ========================================
echo.

echo [1/2] Starting backend on port 18765...
start "Backend" cmd /k "cd /d %~dp0 && python -m backend.web"

timeout /t 2 /nobreak >nul

echo [2/2] Starting frontend on port 13000...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   Backend:  http://127.0.0.1:18765
echo   Frontend: http://localhost:13000
echo ========================================
echo.
echo Press any key to exit this window...
pause >nul
