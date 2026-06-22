@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" soundrts.py
    goto :done
)

where python >nul 2>&1 && (
    python soundrts.py
    goto :done
)

where py >nul 2>&1 && (
    py -3 soundrts.py
    goto :done
)

echo Python not found. Install Python 3.11 or run: pip install -r requirements.txt
pause
exit /b 1

:done
if errorlevel 1 pause
endlocal
