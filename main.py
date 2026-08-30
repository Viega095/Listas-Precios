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
    """Espera activamente a que el servidor FastAPI esté 100% levantado antes de abrir el navegador."""
    import urllib.request
    heartbeat_url = "http://127.0.0.1:8000/api/heartbeat"
    app_url = "http://127.0.0.1:8000"
    
    for _ in range(120): # Intentar hasta 60 segundos
        try:
            req = urllib.request.Request(heartbeat_url, data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    time.sleep(0.3)
                    webbrowser.open(app_url)
                    return
        except Exception:
            time.sleep(0.5)
            
    # Si tardó más del tiempo esperado, intentar abrir de todas formas
    webbrowser.open(app_url)

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
