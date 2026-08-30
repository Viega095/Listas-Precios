import os
import sys
import io
import time
import threading
import webbrowser
import urllib.request

# Redirección de flujos estándar para ejecutables en modo sin consola
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from app.server import app
import uvicorn

def open_browser():
    """Espera activamente a que Uvicorn responda 200 OK antes de abrir el navegador."""
    health_url = "http://127.0.0.1:8000/api/health"
    app_url = "http://127.0.0.1:8000"
    
    for _ in range(120): # Intentar hasta 60 segundos
        try:
            with urllib.request.urlopen(health_url, timeout=1) as resp:
                if resp.status == 200:
                    time.sleep(0.3)
                    webbrowser.open(app_url)
                    return
        except Exception:
            time.sleep(0.5)
            
    webbrowser.open(app_url)

if __name__ == "__main__":
    # Si el servidor ya está ejecutándose en segundo plano, abrir navegador y salir
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=1) as resp:
            if resp.status == 200:
                webbrowser.open("http://127.0.0.1:8000")
                sys.exit(0)
    except Exception:
        pass

    # Iniciar hilo en segundo plano que esperará a que Uvicorn esté listo para abrir la pestaña
    threading.Thread(target=open_browser, daemon=True).start()

    # EJECUTAR UVICORN EN EL HILO PRINCIPAL (Mantiene el servidor activo permanentemente)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        use_colors=False
    )
