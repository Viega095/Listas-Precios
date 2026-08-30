# Comparador de Listas de Precios

Aplicación para PC que permite comparar listas de precios de hasta 3 proveedores en formatos Excel (.xlsx, .xls), CSV o PDF, detectando automáticamente la opción más económica y generando pedidos de compra listos para enviar.

---

## 📦 Cómo Distribuir la Aplicación al Cliente (Flujo GitHub + .BAT)

Este método es el más cómodo para el cliente:

1. **Vos (Desarrollador)**:
   - Compilás el ejecutable con **`compilar_exe.bat`**.
   - Subís el archivo `ComparadorPrecios.exe` a los **Releases** de tu repositorio de GitHub (ejemplo: `https://github.com/tu-usuario/tu-repo/releases`).

2. **Tu Cliente**:
   - Solo le enviás el archivo **`Lanzador_Cliente.bat`** (ocupa apenas 2 KB).
   - Al hacer doble clic:
     - Se descarga e instala automáticamente el `.exe` desde GitHub.
     - Le crea el acceso directo en el Escritorio.
     - Abre la aplicación de inmediato sin requerir Python ni ninguna instalación manual.

---

## 🚀 Cómo Iniciar en Desarrollo Local

1. **Primera vez / Instalación de librerías**:
   - Al hacer doble clic en **`iniciar_aplicacion.bat`**, el sistema verifica e **instala automáticamente** las librerías necesarias si no están en el equipo.
   - También podés ejecutar **`instalar_dependencias.bat`** manualmente.

2. **Abrir la Aplicación**:
   - Hacé doble clic en **`iniciar_aplicacion.bat`** (o en el acceso directo de tu Escritorio).
   - O hacé doble clic en **`iniciar_silencioso.vbs`** para iniciar sin ventana de consola.

*El navegador web se abrirá automáticamente en `http://127.0.0.1:8000`.*

---

## 📋 Pasos de Uso

1. **Cargar Listas**: Arrastrá hasta 3 listas de precios (o tocá *"Cargar Datos de Ejemplo"* para una demostración instantánea).
2. **Mapeo de Columnas**: El sistema detecta automáticamente las columnas principales (Producto, Precio, etc.).
3. **Configurar Precios**: Ajustá IVA o descuentos si tus listas no tienen precio final.
4. **Revisión de Dudas**: Confirmá o separá coincidencias dudosas si las hubiera.
5. **Resultados y Pedidos**:
   - Visualizá la conclusión recomendada de compra.
   - Descargá la orden de compra lista para cada proveedor con el botón **`📥 Pedido .xlsx`**.
   - Exportá el análisis completo a **Excel**, **CSV** o **PDF**.
