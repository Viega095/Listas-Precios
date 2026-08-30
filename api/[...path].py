import sys
import os

# Asegurar que el directorio raíz del proyecto esté en el path de Python
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.server import app

# Exportar como app y handler para máxima compatibilidad con Vercel
handler = app
