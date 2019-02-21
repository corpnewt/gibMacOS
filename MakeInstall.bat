:::::::::::::::::::::::::::::::::::::::::
:: Automatically check & get admin rights
:::::::::::::::::::::::::::::::::::::::::
@echo off

:checkPrivileges
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
if '%~1'=='ELEV' (shift & goto main)
ECHO.

setlocal DisableDelayedExpansion
set "batchPath=%~0"
setlocal EnableDelayedExpansion
ECHO Set UAC = CreateObject^("Shell.Application"^) > "%temp%\OEgetPrivileges.vbs"
ECHO UAC.ShellExecute "!batchPath!", "ELEV", "", "runas", 1 >> "%temp%\OEgetPrivileges.vbs"
"%temp%\OEgetPrivileges.vbs"
exit /B

:gotPrivileges
::::::::::::::::::::::::::::
::START
::::::::::::::::::::::::::::

@echo off
setlocal enableDelayedExpansion

REM Setup initial vars
set "script_name=%~n0.py"
set "thisDir=%~dp0"

REM Check for our script first
if not exist "!thisDir!\!script_name!" (
    echo Could not find !script_name!.
    echo Please make sure to run this script from the same directory
    echo as !script_name!.
    echo.
    echo Press [enter] to quit.
    pause > nul
    exit /b
)

REM Get python location
FOR /F "tokens=* USEBACKQ" %%F IN (`where python 2^> nul`) DO (
    SET "python=%%F"
)

REM Check for py and give helpful hints!
if /i "!python!"=="" (
    echo Python is not installed or not found in your PATH var.
    echo Please install it from https://www.python.org/downloads/windows/
    echo.
    echo Make sure you check the box labeled:
    echo.
    echo "Add Python X.X to PATH"
    echo.
    echo Where X.X is the py version you're installing.
    echo.
    echo Press [enter] to quit.
    pause > nul
    exit /b
)

REM Python found
if "%*"=="" (
    "!python!" "!thisDir!!script_name!"
) else (
    "!python!" "!thisDir!!script_name!" %*
)
