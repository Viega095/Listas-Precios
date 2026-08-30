@echo off
setlocal enabledelayedexpansion
title Comparador de Listas de Precios

set "APP_DIR=%LOCALAPPDATA%\ComparadorPrecios"
set "EXE_PATH=%APP_DIR%\ComparadorPrecios.exe"
set "VERSION_FILE=%APP_DIR%\version.txt"
set "GITHUB_URL=https://github.com/Viega095/Listas-Precios/releases/latest/download/ComparadorPrecios.exe"
set "API_URL=https://api.github.com/repos/Viega095/Listas-Precios/releases/latest"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: 1. Si no existe el ejecutable, descargarlo desde GitHub
if not exist "%EXE_PATH%" (
    echo ================================================================
    echo    Comparador de Precios - Descargando aplicacion...
    echo ================================================================
    echo.
    echo Conectando con GitHub y descargando la ultima version...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GITHUB_URL%', '%EXE_PATH%')"
)

:: 2. Crear acceso directo en el Escritorio si no existe
set "SHORTCUT=%USERPROFILE%\Desktop\Comparador de Precios.lnk"
if not exist "%SHORTCUT%" (
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%APP_DIR%'; $s.Save()"
)

:: 3. Iniciar la aplicacion (el propio .exe muestra su splash screen y abre el navegador)
start "" "%EXE_PATH%"
exit /b 0
