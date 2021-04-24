@echo off
REM Get our local path before delayed expansion - allows ! in path
set "thisDir=%~dp0"

setlocal enableDelayedExpansion
REM Setup initial vars
set "script_name="
set /a tried=0
set "toask=yes"
set "pause_on_error=yes"
set "py2v="
set "py2path="
set "py3v="
set "py3path="
set "pypath="

REM use_py3:
REM   TRUE  = Use if found, use py2 otherwise
REM   FALSE = Use py2
REM   FORCE = Use py3
set "use_py3=TRUE"

REM Get the system32 (or equivalent) path
call :getsyspath "syspath"

goto checkscript

:checkscript
REM Check for our script first
set "looking_for=!script_name!"
if "!script_name!" == "" (
    set "looking_for=%~n0.py or %~n0.command"
    set "script_name=%~n0.py"
    if not exist "!thisDir!\!script_name!" (
        set "script_name=%~n0.command"
    )
)
if not exist "!thisDir!\!script_name!" (
    echo Could not find !looking_for!.
    echo Please make sure to run this script from the same directory
    echo as !looking_for!.
    echo.
    echo Press [enter] to quit.
    pause > nul
    exit /b
)
goto checkpy

:getsyspath <variable_name>
REM Helper method to return the "proper" path to cmd.exe, reg.exe, and where.exe by walking the ComSpec var
REM Prep the LF variable to use the "line feed" approach
(SET LF=^
%=this line is empty=%
)
REM Strip double semi-colons
call :undouble "ComSpec" "%ComSpec%" ";"
set "testpath=%ComSpec:;=!LF!%"
REM Let's walk each path and test if cmd.exe, reg.exe, and where.exe exist there
set /a found=0
for /f "tokens=* delims=" %%i in ("!testpath!") do (
    REM Only continue if we haven't found it yet
    if NOT "%%i" == "" (
        if !found! lss 1 (
            set "temppath=%%i"
            REM Remove "cmd.exe" from the end if it exists
            if /i "!temppath:~-7!" == "cmd.exe" (
                set "temppath=!temppath:~0,-7!"
            )
            REM Pad the end with a backslash if needed
            if NOT "!temppath:~-1!" == "\" (
                set "temppath=!temppath!\"
            )
            REM Let's see if cmd, reg, and where exist there - and set it if so
            if EXIST "!temppath!cmd.exe" (
                if EXIST "!temppath!reg.exe" (
                    if EXIST "!temppath!where.exe" (
                        set /a found=1
                        set "ComSpec=!temppath!cmd.exe"
                        set "%~1=!temppath!"
                    )
                )
            )
        )
    )
)
goto :EOF

:updatepath
set "spath="
set "upath="
for /f "USEBACKQ tokens=2* delims= " %%i in (`!syspath!reg.exe query "HKCU\Environment" /v "Path" 2^> nul`) do ( if not "%%j" == "" set "upath=%%j" )
for /f "USEBACKQ tokens=2* delims= " %%i in (`!syspath!reg.exe query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v "Path" 2^> nul`) do ( if not "%%j" == "" set "spath=%%j" )
if not "%spath%" == "" (
    REM We got something in the system path
    set "PATH=%spath%"
    if not "!upath!" == "" (
        REM We also have something in the user path
        set "PATH=%PATH%;%upath%"
    )
) else if not "%upath%" == "" (
    set "PATH=%upath%"
)
REM Remove double semicolons from the adjusted PATH
call :undouble "PATH" "%PATH%" ";"
goto :EOF

:undouble <string_name> <string_value> <character>
REM Helper function to strip doubles of a single character out of a string recursively
set "string_value=%~2"
set "check=!string_value:%~3%~3=%~3!"
if not "!check!" == "!string_value!" (
    set "%~1=!check!"
    call :undouble "%~1" "!check!" "%~3"
)
goto :EOF

:checkpy
call :updatepath
for /f "USEBACKQ tokens=*" %%x in (`!syspath!where.exe python 2^> nul`) do ( call :checkpyversion "%%x" "py2v" "py2path" "py3v" "py3path" )
for /f "USEBACKQ tokens=*" %%x in (`!syspath!where.exe python3 2^> nul`) do ( call :checkpyversion "%%x" "py2v" "py2path" "py3v" "py3path" )
for /f "USEBACKQ tokens=*" %%x in (`!syspath!where.exe py 2^> nul`) do ( call :checkpylauncher "%%x" "py2v" "py2path" "py3v" "py3path" )
set "targetpy=3"
if /i "!use_py3!" == "FALSE" (
    set "targetpy=2"
    set "pypath=!py2path!"
) else if /i "!use_py3!" == "FORCE" (
    set "pypath=!py3path!"
) else if /i "!use_py3!" == "TRUE" (
    set "pypath=!py3path!"
    if "!pypath!" == "" set "pypath=!py2path!"
)
if not "!pypath!" == "" (
    goto runscript
)
if !tried! lss 1 (
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
    echo.
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
goto runscript

:checkpylauncher <path> <py2v> <py2path> <py3v> <py3path>
REM Attempt to check the latest python 2 and 3 versions via the py launcher
for /f "USEBACKQ tokens=*" %%x in (`%~1 -2 -c "import sys; print(sys.executable)" 2^> nul`) do ( call :checkpyversion "%%x" "%~2" "%~3" "%~4" "%~5" )
for /f "USEBACKQ tokens=*" %%x in (`%~1 -3 -c "import sys; print(sys.executable)" 2^> nul`) do ( call :checkpyversion "%%x" "%~2" "%~3" "%~4" "%~5" )
goto :EOF

:checkpyversion <path> <py2v> <py2path> <py3v> <py3path>
set "version="&for /f "tokens=2* USEBACKQ delims= " %%a in (`"%~1" -V 2^>^&1`) do (
    REM Ensure we have a version number
    call :isnumber "%%a"
    if not "!errorlevel!" == "0" goto :EOF
    set "version=%%a"
)
if not defined version goto :EOF
if "!version:~0,1!" == "2" (
    REM Python 2
    call :comparepyversion "!version!" "!%~2!"
    if "!errorlevel!" == "1" (
        set "%~2=!version!"
        set "%~3=%~1"
    )
) else (
    REM Python 3
    call :comparepyversion "!version!" "!%~4!"
    if "!errorlevel!" == "1" (
        set "%~4=!version!"
        set "%~5=%~1"
    )
)
goto :EOF

:isnumber <check_value>
set "var="&for /f "delims=0123456789." %%i in ("%~1") do set var=%%i
if defined var (exit /b 1)
exit /b 0

:comparepyversion <version1> <version2> <return>
REM Exits with status 0 if equal, 1 if v1 gtr v2, 2 if v1 lss v2
for /f "tokens=1,2,3 delims=." %%a in ("%~1") do (
    set a1=%%a
    set a2=%%b
    set a3=%%c
)
for /f "tokens=1,2,3 delims=." %%a in ("%~2") do (
    set b1=%%a
    set b2=%%b
    set b3=%%c
)
if not defined a1 set a1=0
if not defined a2 set a2=0
if not defined a3 set a3=0
if not defined b1 set b1=0
if not defined b2 set b2=0
if not defined b3 set b3=0
if %a1% gtr %b1% exit /b 1
if %a1% lss %b1% exit /b 2
if %a2% gtr %b2% exit /b 1
if %a2% lss %b2% exit /b 2
if %a3% gtr %b3% exit /b 1
if %a3% lss %b3% exit /b 2
exit /b 0

:askinstall
cls
echo   ###              ###
echo  # Python Not Found #
echo ###              ###
echo.
echo Python !targetpy! was not found on the system or in the PATH var.
echo.
set /p "menu=Would you like to install it now? [y/n]: "
if /i "!menu!"=="y" (
    REM We got the OK - install it
    goto installpy
) else if "!menu!"=="n" (
    REM No OK here...
    set /a tried=!tried!+1
    goto checkpy
)
REM Incorrect answer - go back
goto askinstall

:installpy
REM This will attempt to download and install python
REM First we get the html for the python downloads page for Windows
set /a tried=!tried!+1
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
for /f "tokens=9 delims=< " %%x in ('findstr /i /c:"Latest Python !targetpy! Release" pyurl.txt') do ( set "release=%%x" )
popd

echo Found Python !release! -  Downloading...
REM Let's delete our txt file now - we no longer need it
del "%TEMP%\pyurl.txt"

REM At this point - we should have the version number.
REM We can build the url like so: "https://www.python.org/ftp/python/[version]/python-[version]-amd64.exe"
set "url=https://www.python.org/ftp/python/!release!/python-!release!-amd64.exe"
set "pytype=exe"
if "!targetpy!" == "2" (
    set "url=https://www.python.org/ftp/python/!release!/python-!release!.amd64.msi"
    set "pytype=msi"
)
REM Now we download it with our slick powershell command
powershell -command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (new-object System.Net.WebClient).DownloadFile('!url!','%TEMP%\pyinstall.!pytype!')"
REM If it doesn't exist - we bail
if not exist "%TEMP%\pyinstall.!pytype!" (
    goto checkpy
)
REM It should exist at this point - let's run it to install silently
echo Installing...
pushd "%TEMP%"
if /i "!pytype!" == "exe" (
    echo pyinstall.exe /quiet PrependPath=1 Include_test=0 Shortcuts=0 Include_launcher=0
    pyinstall.exe /quiet PrependPath=1 Include_test=0 Shortcuts=0 Include_launcher=0
) else (
    set "foldername=!release:.=!"
    echo msiexec /i pyinstall.msi /qb ADDLOCAL=ALL TARGETDIR="%LocalAppData%\Programs\Python\Python!foldername:~0,2!"
    msiexec /i pyinstall.msi /qb ADDLOCAL=ALL TARGETDIR="%LocalAppData%\Programs\Python\Python!foldername:~0,2!"
)
popd
echo Installer finished with %ERRORLEVEL% status.
REM Now we should be able to delete the installer and check for py again
del "%TEMP%\pyinstall.!pytype!"
REM If it worked, then we should have python in our PATH
REM this does not get updated right away though - let's try
REM manually updating the local PATH var
call :updatepath
goto checkpy
exit /b

:runscript
REM Python found
cls
set "args=%*"
set "args=!args:"=!"
if "!args!"=="" (
    "!pypath!" "!thisDir!!script_name!"
) else (
    "!pypath!" "!thisDir!!script_name!" %*
)
if /i "!pause_on_error!" == "yes" (
    if not "%ERRORLEVEL%" == "0" (
        echo.
        echo Script exited with error code: %ERRORLEVEL%
        echo.
        echo Press [enter] to exit...
        pause > nul
    )
)
goto :EOF
