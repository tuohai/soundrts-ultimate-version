@echo off
REM Version-agnostic release packaging for the cx_Freeze build.
REM
REM Input : %TEMP%\soundrts-<VERSION>-windows        (produced by _build_cxfreeze.cmd)
REM Output: %TEMP%\soundrts-<VERSION>-ultimate.version-windows.zip
REM
REM The zip lives in %TEMP% -- NOT in the repo's artifacts/ folder.
REM The version is read from soundrts/version.py, so this script never
REM needs renaming when the version is bumped.
REM
REM Usage:  _package_release.cmd
REM
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [package] FATAL: .venv\Scripts\python.exe not found
    exit /b 1
)
echo [package] packaging release into %TEMP%
".venv\Scripts\python.exe" _package_release.py
exit /b %ERRORLEVEL%
