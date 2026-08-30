import os
import sys
import io
import webbrowser
import threading
import time
import uvicorn

# Solución para ejecutables sin ventana de consola (PyInstaller --windowed)
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from app.server import app

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    webbrowser.open(url)

if __name__ == "__main__":
    # Iniciar hilo para abrir el navegador web automáticamente
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Iniciar servidor FastAPI directamente con la instancia importada
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        use_colors=False
    )
