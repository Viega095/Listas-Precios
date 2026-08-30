@echo off
title Compilador de Ejecutable .EXE - Comparador de Precios
echo ================================================================
echo  Compilando aplicacion en un unico archivo .EXE independiente...
echo ================================================================
echo.

python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "ComparadorPrecios" ^
    --add-data "static;static" ^
    --add-data "datos_prueba;datos_prueba" ^
    --hidden-import "uvicorn" ^
    --hidden-import "fastapi" ^
    --hidden-import "pandas" ^
    --hidden-import "openpyxl" ^
    --hidden-import "reportlab" ^
    --hidden-import "pypdf" ^
    --hidden-import "rapidfuzz" ^
    --hidden-import "python_multipart" ^
    main.py

echo.
if %errorlevel% equ 0 (
    echo [EXITO] Compilacion completada con exito.
    echo El ejecutable se encuentra en la carpeta: dist\ComparadorPrecios\ComparadorPrecios.exe
) else (
    echo [ERROR] Ocurrio un problema durante la compilacion.
)
echo.
pause
