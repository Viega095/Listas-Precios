import os
import sys
import webbrowser
import threading
import time
import uvicorn

def open_browser():
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n=======================================================")
    print(f" Comparador de Listas de Precios de Proveedores")
    print(f" Servidor iniciado con éxito en: {url}")
    print(f" Abriendo navegador automáticamente...")
    print(f"=======================================================\n")
    webbrowser.open(url)

if __name__ == "__main__":
    # Iniciar hilo para abrir el navegador web automáticamente
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Iniciar servidor FastAPI
    uvicorn.run("app.server:app", host="127.0.0.1", port=8000, log_level="info", reload=False)
