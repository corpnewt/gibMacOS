@echo off
setlocal enableDelayedExpansion

REM Setup initial vars
set "script_name=%~n0.command"
set "thisDir=%~dp0"
set /a tried=0
set "toask=yes"

goto checkscript

:checkscript
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
goto checkpy

:checkpy
python -V > NUL 2>&1
if not "!errorlevel!" == "0" (
    if %tried% lss 1 (
        if /i "!toask!"=="yes" (
            REM Better ask permission first
            goto askinstall
        ) else (
            goto installpy
        )
    ) else (
        cls
        echo   ###     ###
        echo  # Warning #
        echo ###     ###
        REM Couldn't install for whatever reason - give the error message
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
)
goto runscript

:askinstall
cls
echo   ###              ###
echo  # Python Not Found #
echo ###              ###
echo.
echo Python was not found on the system or in the PATH var.
echo.
set /p "menu=Would you like to install it now? [y/n]: "
if /i "!menu!"=="y" (
    REM We got the OK - install it
    goto installpy
) else if "!menu!"=="n" (
    REM No OK here...
    set /a tried=%tried%+1
    goto checkpy
)
REM Incorrect answer - go back
goto askinstall

:installpy
REM This will attempt to download and install python
REM First we get the html for the python downloads page for Windows
set /a tried=%tried%+1
cls
echo   ###               ###
echo  # Installing Python #
echo ###               ###
echo.
echo Gathering info from https://www.python.org/downloads/windows/...
powershell -command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (new-object System.Net.WebClient).DownloadFile('https://www.python.org/downloads/windows/','%TEMP%\pyurl.txt')"
if not exist "%TEMP%\pyurl.txt" (
    goto checkpy
)

echo Parsing for latest...
pushd "%TEMP%"
:: Version detection code slimmed by LussacZheng (https://github.com/corpnewt/gibMacOS/issues/20)
for /f "tokens=9 delims=< " %%x in ('findstr /i /c:"Latest Python 3 Release" pyurl.txt') do ( set "release=%%x" )
popd

echo Found Python !release! -  Downloading...
REM Let's delete our txt file now - we no longer need it
del "%TEMP%\pyurl.txt"

REM At this point - we should have the version number.
REM We can build the url like so: "https://www.python.org/ftp/python/[version]/python-[version]-amd64.exe"
set "url=https://www.python.org/ftp/python/!release!/python-!release!-amd64.exe"
REM Now we download it with our slick powershell command
powershell -command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (new-object System.Net.WebClient).DownloadFile('!url!','%TEMP%\pyinstall.exe')"
REM If it doesn't exist - we bail
if not exist "%TEMP%\pyinstall.exe" (
    goto checkpy
)
REM It should exist at this point - let's run it to install silently
echo Installing...
echo pyinstall.exe /quiet PrependPath=1 Include_test=0 Shortcuts=0 Include_launcher=0
pushd "%TEMP%"
pyinstall.exe /quiet PrependPath=1 Include_test=0 Shortcuts=0 Include_launcher=0
popd
echo Installer finsihed with %ERRORLEVEL% status.
REM Now we should be able to delete the installer and check for py again
del "%TEMP%\pyinstall.exe"
REM If it worked, then we should have python in our PATH
REM this does not get updated right away though - let's try
REM manually updating the local PATH var
set "spath="
set "upath="
for /f "tokens=2* delims= " %%i in ('reg.exe query "HKCU\Environment" /v "Path" 2^> nul') do (
    if NOT "%%j"=="" (
		set "upath=%%j"
	)
)
for /f "tokens=2* delims= " %%i in ('reg.exe query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v "Path" 2^> nul') do (
    if NOT "%%j"=="" (
		set "spath=%%j"
	)
)
if not "!spath!" == "" (
    REM We got something in the system path
    set "PATH=!spath!"
    if not "!upath!" == "" (
        REM We also have something in the user path
        set "PATH=!PATH!;!upath!"
    )
) else if not "!upath!" == "" (
    set "PATH=!upath!"
)
goto checkpy
exit /b

:runscript
REM Python found
cls
set "args=%*"
set "args=!args:"=!"
if "!args!"=="" (
    python "!thisDir!!script_name!"
) else (
    python "!thisDir!!script_name!" %*
)
goto :EOF
