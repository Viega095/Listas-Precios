@echo off
setlocal enabledelayedexpansion
title Comparador de Listas de Precios - Instalador y Lanzador

:: ======================================================================
:: CONFIGURACION DE GITHUB RELEASES
:: ======================================================================
set "GITHUB_EXE_URL=https://github.com/Viega095/Listas-Precios/releases/latest/download/ComparadorPrecios.exe"
set "APP_DIR=%LOCALAPPDATA%\ComparadorPrecios"
set "EXE_PATH=%APP_DIR%\ComparadorPrecios.exe"

if not exist "%APP_DIR%" (
    mkdir "%APP_DIR%"
)

cls
echo ================================================================
echo     Comparador de Listas de Precios - Instalador Automatico
echo ================================================================
echo.

:: 1. Verificar si ya existe el ejecutable o si requiere descarga
if not exist "%EXE_PATH%" (
    echo [1/3] Conectando con GitHub...
    echo [2/3] Descargando la aplicacion y sus componentes...
    echo       Por favor espere unos segundos...
    echo.
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('%GITHUB_EXE_URL%', '%EXE_PATH%')"
    
    if not exist "%EXE_PATH%" (
        echo.
        echo [AVISO] No se pudo descargar desde internet o no hay conexion.
        if exist "%~dp0ComparadorPrecios.exe" (
            set "EXE_PATH=%~dp0ComparadorPrecios.exe"
        ) else if exist "%~dp0dist\ComparadorPrecios.exe" (
            set "EXE_PATH=%~dp0dist\ComparadorPrecios.exe"
        ) else (
            echo [ERROR] No se encontro el archivo ejecutable.
            echo Verifique su conexion a internet o ejecute "iniciar_aplicacion.bat".
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Aplicacion descargada e instalada con exito.
    )
) else (
    echo [1/3] Verificando actualizaciones en GitHub...
    echo [2/3] Aplicacion lista para ejecutar.
)

:: 2. Crear acceso directo en el Escritorio si no existe
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Comparador de Precios.lnk"
if not exist "%SHORTCUT_PATH%" (
    powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%EXE_PATH%';$s.WorkingDirectory='%APP_DIR%';$s.Save()"
    echo [OK] Acceso directo creado en su Escritorio.
)

:: 3. Iniciar la aplicacion
echo.
echo [3/3] Iniciando Comparador de Listas de Precios...
echo       Abriendo navegador web...
start "" "%EXE_PATH%"

:: Esperar 3 segundos y cerrar la ventana del lanzador
timeout /t 3 /nobreak >nul
exit /b 0
