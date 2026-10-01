@echo off
setlocal
cd /d "%~dp0"

REM Priority 1: project venv (pygame/wxPython/cx_Freeze installed there)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import pygame" >nul 2>&1
    if not errorlevel 1 (
        ".venv\Scripts\python.exe" soundrts.py %*
        goto :done
    )
    echo [soundrts.bat] .venv exists but pygame missing, trying other pythons...
)

REM Priority 2: python launcher (py -3 picks .venv/.venv, .pyo script-friendly)
where py >nul 2>&1 && (
    py -3 -c "import pygame" >nul 2>&1
    if not errorlevel 1 (
        py -3 soundrts.py %*
        goto :done
    )
)

REM Priority 3: any python on PATH with pygame
where python >nul 2>&1 && (
    for /f "delims=" %%P in ('where python') do (
        "%%~P" -c "import pygame" >nul 2>&1
        if not errorlevel 1 (
            "%%~P" soundrts.py %*
            goto :done
        )
    )
)

echo.
echo [soundrts.bat] Python with pygame not found.
echo   Install Python 3.12 + run: .venv\Scripts\pip.exe install -r requirements.txt
echo   Or use Python launcher: py -3.12 -m pip install pygame-ce wxPython
pause
exit /b 1

:done
if errorlevel 1 pause
endlocal
