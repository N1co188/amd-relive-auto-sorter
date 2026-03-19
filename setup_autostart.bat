@echo off
set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "EXE_PATH=%DIST_DIR%\AMD_Clip_Sorter.exe"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\AMD_Clip_Sorter.lnk"

if not exist "%EXE_PATH%" (
    echo WARNING: The executable file was not found!
    echo Please run "build.bat" first to create it.
    pause
    exit /b
)

echo Adding "AMD_Clip_Sorter" to Windows Startup...
echo.

:: Create a temporary VBScript to make a proper Windows Shortcut
set "VBS_SCRIPT=%TEMP%\CreateShortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%SHORTCUT_PATH%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%EXE_PATH%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%DIST_DIR%" >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

cscript /nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo SUCCESS! 
echo "AMD_Clip_Sorter" will now start automatically in the 
echo background (system tray) every time you boot your PC.
echo.
pause