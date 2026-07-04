@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ==========================================================================
REM  AI Agents Backup & Transfer Tool - Windows launcher
REM
REM  Finds Python 3 and, if it is missing, installs it automatically via
REM  winget, then runs backup_transfer_tool.py. Arguments are passed through:
REM      run.bat                     ->  interactive menu
REM      run.bat backup D:\Backups   ->  run a command directly
REM      run.bat list  D:\Backups
REM ==========================================================================

call :detect
if defined PYCMD goto run

echo Python 3 was not found on this computer.
where winget >nul 2>nul
if errorlevel 1 goto manual

echo.
echo Installing Python 3 via winget - this can take a few minutes...
winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
echo.
call :detect
if defined PYCMD goto run

echo Python was installed but is not on PATH in this window yet.
echo Please CLOSE this window and run the launcher again.
echo.
pause
exit /b 1

:manual
echo winget is not available, so Python cannot be installed automatically.
echo Please install Python 3 from:
echo     https://www.python.org/downloads/
echo (Tick "Add python.exe to PATH" during setup, then run this launcher again.)
start "" "https://www.python.org/downloads/"
echo.
pause
exit /b 1

:run
echo Using Python: !PYCMD!
echo.
!PYCMD! "%~dp0backup_transfer_tool.py" %*
echo.
pause
exit /b 0

REM --- subroutine: sets PYCMD to a working Python 3 command, or leaves it empty
:detect
set "PYCMD="
py -3 --version >nul 2>nul
if not errorlevel 1 (
    set "PYCMD=py -3"
    goto :eof
)
python --version >nul 2>nul
if not errorlevel 1 (
    set "PYCMD=python"
)
goto :eof
