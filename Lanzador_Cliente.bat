@echo off
setlocal enabledelayedexpansion
title Comparador de Listas de Precios

set "APP_DIR=%LOCALAPPDATA%\ComparadorPrecios"
set "EXE_PATH=%APP_DIR%\ComparadorPrecios.exe"
set "GITHUB_URL=https://github.com/Viega095/Listas-Precios/releases/latest/download/ComparadorPrecios.exe"

if not exist "%APP_DIR%" mkdir "%APP_DIR%"

:: 1. Si no existe el ejecutable, descargarlo desde GitHub
if not exist "%EXE_PATH%" (
    echo ================================================================
    echo    Comparador de Precios - Descargando aplicacion...
    echo ================================================================
    echo.
    echo Conectando con GitHub y descargando la ultima version...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GITHUB_URL%', '%EXE_PATH%')"
)

:: 2. Crear acceso directo en el Escritorio (compatible con OneDrive y Windows en espanol)
powershell -NoProfile -Command "try { $desktop = [Environment]::GetFolderPath('Desktop'); if ($desktop -and (Test-Path $desktop)) { $lnk = Join-Path $desktop 'Comparador de Precios.lnk'; $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut($lnk); $s.TargetPath = '%EXE_PATH%'; $s.WorkingDirectory = '%APP_DIR%'; $s.Save() } } catch {}"

:: 3. Iniciar la aplicacion
start "" "%EXE_PATH%"
exit /b 0
