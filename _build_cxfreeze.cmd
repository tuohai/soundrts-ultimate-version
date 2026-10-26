@echo off
REM Version-agnostic cx_Freeze build wrapper.
REM The release version is NOT hardcoded here: setup.py reads it from
REM soundrts/version.py and derives the output folder
REM   %TEMP%\soundrts-<VERSION>-windows
REM so this script never needs renaming when the version is bumped.
REM
REM Usage:  _build_cxfreeze.cmd
REM Output: %TEMP%\soundrts-<VERSION>-windows  (NOT the repo's build/ dir)

setlocal
echo [wrapper-cx] Loading vcvars64...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 (
    echo [wrapper-cx] FATAL: vcvars64 failed
    exit /b 1
)
echo [wrapper-cx] cl.exe:
where cl.exe
set "SOUNDRTS_SKIP_CYTHON="
set "DISTUTILS_USE_SDK=1"
set "MSSdk=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [wrapper-cx] FATAL: .venv\Scripts\python.exe not found
    exit /b 1
)
echo [wrapper-cx] running cx_Freeze build
".venv\Scripts\python.exe" setup.py build <NUL > "%TEMP%\cx_freeze_build.log" 2>&1
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
    echo [wrapper-cx] FATAL: setup.py build failed. Tail of log:
    powershell -NoProfile -Command "Get-Content '%TEMP%\cx_freeze_build.log' -Tail 80"
)
exit /b %RC%
