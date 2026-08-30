import os
import sys
import io
import time
import socket
import threading
import webbrowser
import urllib.request

# Redirección de flujos estándar para ejecutables sin ventana de consola
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

def is_port_in_use(port: int) -> bool:
    """Verifica si el puerto ya está en uso por una instancia previa."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

# Si ya hay una instancia corriendo en el puerto 8000, solo abrir navegador y salir
if is_port_in_use(8000):
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/heartbeat", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            if resp.status == 200:
                webbrowser.open("http://127.0.0.1:8000")
                sys.exit(0)
    except Exception:
        pass

from app.server import app
import uvicorn

splash_root = None

def show_splash():
    """Muestra una mini ventana gráfica moderna mientras arranca el ejecutable."""
    global splash_root
    try:
        import tkinter as tk
        from tkinter import ttk
        
        splash_root = tk.Tk()
        splash_root.title("Comparador de Precios")
        splash_root.geometry("420x170")
        splash_root.resizable(False, False)
        splash_root.configure(bg="#0f172a") # Slate 900
        
        # Centrar en pantalla
        splash_root.update_idletasks()
        w = 420
        h = 170
        x = (splash_root.winfo_screenwidth() // 2) - (w // 2)
        y = (splash_root.winfo_screenheight() // 2) - (h // 2)
        splash_root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Aspecto de Splash Screen sin bordes
        splash_root.overrideredirect(True)
        
        frame = tk.Frame(splash_root, bg="#0f172a", bd=1, relief="solid", highlightbackground="#0284c7", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        
        lbl_title = tk.Label(frame, text="Comparador de Listas de Precios", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_title.pack(pady=(22, 4))
        
        lbl_status = tk.Label(frame, text="Iniciando servidor y preparando aplicación...", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        lbl_status.pack(pady=4)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Splash.Horizontal.TProgressbar", troughcolor='#1e293b', background='#0284c7', bordercolor='#0f172a')
        
        pb = ttk.Progressbar(frame, style="Splash.Horizontal.TProgressbar", mode="indeterminate", length=320)
        pb.pack(pady=(12, 8))
        pb.start(15)
        
        splash_root.mainloop()
    except Exception:
        pass

def close_splash():
    """Cierra la ventana Splash cuando la web está lista."""
    global splash_root
    if splash_root:
        try:
            splash_root.after(0, splash_root.destroy)
        except Exception:
            pass

def server_runner():
    """Ejecuta el servidor FastAPI con Uvicorn."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        use_colors=False
    )

def wait_and_open_browser():
    """Espera a que FastAPI responda 200 OK antes de abrir el navegador y cerrar el splash."""
    heartbeat_url = "http://127.0.0.1:8000/api/heartbeat"
    app_url = "http://127.0.0.1:8000"
    
    for _ in range(120): # hasta 60 segundos
        try:
            req = urllib.request.Request(heartbeat_url, data=b"{}", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    time.sleep(0.4)
                    webbrowser.open(app_url)
                    close_splash()
                    return
        except Exception:
            time.sleep(0.5)
            
    webbrowser.open(app_url)
    close_splash()

if __name__ == "__main__":
    # Iniciar servidor Uvicorn en segundo plano
    threading.Thread(target=server_runner, daemon=True).start()
    
    # Iniciar chequeo de readiness y apertura de navegador en segundo plano
    threading.Thread(target=wait_and_open_browser, daemon=True).start()
    
    # Mostrar la mini interfaz gráfica de inicio en el hilo principal
    show_splash()
