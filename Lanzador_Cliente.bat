@echo off
setlocal enabledelayedexpansion
title Comparador de Listas de Precios

:: ======================================================================
:: CONFIGURACION DE GITHUB RELEASES
:: ======================================================================
set "GITHUB_EXE_URL=https://github.com/Viega095/Listas-Precios/releases/latest/download/ComparadorPrecios.exe"
set "APP_DIR=%LOCALAPPDATA%\ComparadorPrecios"
set "EXE_PATH=%APP_DIR%\ComparadorPrecios.exe"

if not exist "%APP_DIR%" (
    mkdir "%APP_DIR%"
)

echo ================================================================
echo   Comparador de Listas de Precios
echo ================================================================
echo.

:: 1. Si no existe el ejecutable, lo descarga de GitHub
if not exist "%EXE_PATH%" (
    echo [INSTALACION INICIAL] Descargando la aplicacion desde GitHub...
    echo Por favor espere unos segundos...
    echo.
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GITHUB_EXE_URL%', '%EXE_PATH%')"
    
    if not exist "%EXE_PATH%" (
        echo [AVISO] No se pudo descargar desde internet o no hay conexion.
        :: Si el archivo ejecutable esta en la misma carpeta local, lo usamos
        if exist "%~dp0ComparadorPrecios.exe" (
            set "EXE_PATH=%~dp0ComparadorPrecios.exe"
        ) else if exist "%~dp0dist\ComparadorPrecios\ComparadorPrecios.exe" (
            set "EXE_PATH=%~dp0dist\ComparadorPrecios\ComparadorPrecios.exe"
        ) else (
            echo [ERROR] No se encontro el archivo de la aplicacion.
            echo Ejecutando version en codigo Python si esta disponible...
            if exist "%~dp0main.py" (
                python "%~dp0main.py"
                exit /b 0
            )
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Aplicacion descargada e instalada correctamente.
    )
)

:: 2. Crear acceso directo en el Escritorio si no existe
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Comparador de Precios.lnk"
if not exist "%SHORTCUT_PATH%" (
    powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%EXE_PATH%';$s.WorkingDirectory='%APP_DIR%';$s.Save()"
)

:: 3. Iniciar la aplicacion
echo Iniciando aplicacion...
start "" "%EXE_PATH%"
exit /b 0
