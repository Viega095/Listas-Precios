# Comparador de Listas de Precios (Web App)

Aplicación Web moderna que permite comparar listas de precios de hasta 3 proveedores en formatos Excel (.xlsx, .xls), CSV o PDF, detectando automáticamente la opción más económica y generando órdenes de compra listas para enviar.

---

## 🚀 Despliegue en Vercel (1 Clic)

Este proyecto está 100% preparado y configurado para desplegarse como aplicación web en **Vercel** usando Serverless Functions de Python:

1. Entrá a [Vercel](https://vercel.com) e iniciá sesión con tu cuenta de GitHub.
2. Hacé clic en **"Add New..."** -> **"Project"**.
3. Importá el repositorio: **`Viega095/Listas-Precios`**.
4. Dejá la configuración por defecto y hacé clic en **"Deploy"**.
5. ¡Listo! Vercel te dará un enlace público (ej. `https://listas-precios.vercel.app`) que podés compartir directamente con tu cliente para que lo use desde cualquier dispositivo sin instalar nada.

---

## 🛠️ Estructura del Proyecto Web

- **`api/index.py`**: Punto de entrada Serverless para Vercel.
- **`app/`**: Motor de procesamiento en Python FastAPI (Normalización, Matching Fuzzy, Cálculo de Ahorros, Exportaciones Excel/PDF).
- **`static/`**: Interfaz de usuario web interactiva (Tailwind CSS, Lucide Icons, JavaScript vanilla).
- **`vercel.json`**: Configuración de rutas y builds para Vercel.
- **`requirements.txt`**: Dependencias de Python.

---

## 💻 Ejecución Local (Opcional)

Si querés probar la aplicación localmente en tu computadora:

```bash
pip install -r requirements.txt
python main.py
```
Y abrís tu navegador en `http://127.0.0.1:8000`.
