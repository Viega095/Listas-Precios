@echo off
title Comparador de Listas de Precios
echo ================================================================
echo  Iniciando Comparador de Listas de Precios...
echo ================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python en este equipo.
    echo Por favor descargue e instale Python desde https://www.python.org/
    echo Asegurese de marcar la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

:: Verificar si las librerias estan instaladas
python -c "import fastapi, uvicorn, pandas, openpyxl, rapidfuzz, reportlab" >nul 2>&1
if %errorlevel% neq 0 (
    echo [CONFIGURACION INICIAL] Detectando dependencias faltantes...
    echo Instalando librerias necesarias por unica vez, por favor espere...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Hubo un problema al instalar las dependencias con pip.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencias instaladas correctamente.
    echo.
)

:: Ejecutar la aplicacion
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] La aplicacion se cerro.
    pause
)
