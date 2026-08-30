import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.parser import parse_file_to_dataframe, detect_column_mapping
from app.normalizer import normalize_product_record
from app.matcher import ProductMatcher
from app.calculator import PriceCalculator
from app.exporter import ResultExporter

import asyncio
import time
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PriceComparator")

app = FastAPI(title="Comparador de Precios de Proveedores", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
@app.post("/api/health")
@app.get("/api/heartbeat")
@app.post("/api/heartbeat")
async def health_check():
    """Endpoint de estado para verificar que el servidor está 100% activo."""
    return {"status": "ok"}

@app.post("/api/shutdown")
async def shutdown():
    """Cierra el servidor de forma segura a petición del usuario."""
    def delayed_exit():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"status": "shutting_down"}

# Estado de la sesión actual en memoria (para uso local monousuario)
CURRENT_SESSION: Dict[str, Any] = {
    "raw_files": {}, # 0, 1, 2 -> {"filename": str, "bytes": bytes, "df": pd.DataFrame, "columns": list, "warnings": list}
    "mappings": {},  # 0, 1, 2 -> mapping dict
    "configs": [
        {"nombre": "Proveedor 1", "iva_incluido": True, "iva_percent": 21.0, "descuento_percent": 0.0, "recargo_percent": 0.0, "bonificacion_percent": 0.0, "modo_precio": "unitario", "unidades_por_bulto": 1.0},
        {"nombre": "Proveedor 2", "iva_incluido": True, "iva_percent": 21.0, "descuento_percent": 0.0, "recargo_percent": 0.0, "bonificacion_percent": 0.0, "modo_precio": "unitario", "unidades_por_bulto": 1.0},
        {"nombre": "Proveedor 3", "iva_incluido": True, "iva_percent": 21.0, "descuento_percent": 0.0, "recargo_percent": 0.0, "bonificacion_percent": 0.0, "modo_precio": "unitario", "unidades_por_bulto": 1.0}
    ],
    "matched_groups": [],
    "match_stats": {},
    "comparison_results": None
}

class ProcessRequest(BaseModel):
    mappings: Dict[str, Dict[str, Optional[str]]]
    configs: List[Dict[str, Any]]
    similarity_threshold: Optional[float] = 85.0

class OverrideMatchRequest(BaseModel):
    group_id: str
    action: str # "confirm", "unlink"

@app.post("/api/upload/{list_idx}")
async def upload_file(list_idx: int, file: UploadFile = File(...)):
    """Carga un archivo para una de las listas (0, 1, o 2), detecta columnas y previsualiza filas."""
    if list_idx not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="Índice de lista inválido (debe ser 0, 1 o 2).")
        
    try:
        content = await file.read()
        filename = file.filename
        
        df, columns, warnings = parse_file_to_dataframe(content, filename)
        
        if df.empty:
            raise HTTPException(status_code=400, detail=f"El archivo {filename} está vacío o no contiene filas de datos válidas.")
            
        detected_map = detect_column_mapping(columns)
        
        CURRENT_SESSION["raw_files"][list_idx] = {
            "filename": filename,
            "bytes": content,
            "df": df,
            "columns": columns,
            "warnings": warnings,
            "total_rows": len(df)
        }
        CURRENT_SESSION["mappings"][list_idx] = detected_map
        
        # Previsualización de las primeras 10 filas
        preview_rows = df.head(10).to_dict(orient="records")
        
        return {
            "success": True,
            "list_idx": list_idx,
            "filename": filename,
            "total_rows": len(df),
            "columns": columns,
            "detected_mapping": detected_map,
            "warnings": warnings,
            "preview_rows": preview_rows
        }
    except Exception as e:
        logger.exception("Error al subir archivo")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/upload/{list_idx}")
async def remove_file(list_idx: int):
    """Elimina una lista cargada."""
    if list_idx in CURRENT_SESSION["raw_files"]:
        del CURRENT_SESSION["raw_files"][list_idx]
    if list_idx in CURRENT_SESSION["mappings"]:
        del CURRENT_SESSION["mappings"][list_idx]
    return {"success": True}

@app.post("/api/process")
async def process_all_lists(req: ProcessRequest):
    """Procesa el 100% de las filas de todas las listas cargadas, normaliza, empareja y calcula totales."""
    raw_files = CURRENT_SESSION.get("raw_files", {})
    if not raw_files:
        raise HTTPException(status_code=400, detail="No se ha cargado ninguna lista de precios.")
        
    CURRENT_SESSION["configs"] = req.configs
    
    # 1. Normalizar 100% de los productos de cada lista cargada
    normalized_lists: List[List[Dict[str, Any]]] = []
    
    active_indices = sorted(list(raw_files.keys()))
    
    for l_idx in range(3):
        if l_idx in raw_files:
            df = raw_files[l_idx]["df"]
            mapping = req.mappings.get(str(l_idx)) or CURRENT_SESSION["mappings"].get(l_idx, {})
            
            p_list = []
            for row_num, (_, row) in enumerate(df.iterrows(), 1):
                # Extraer campos según el mapeo confirmado por el usuario
                row_dict = {}
                for std_field, orig_col in mapping.items():
                    if orig_col and orig_col in row:
                        row_dict[std_field] = row[orig_col]
                    else:
                        row_dict[std_field] = None
                        
                norm_item = normalize_product_record(row_dict, list_index=l_idx, row_number=row_num)
                p_list.append(norm_item)
                
            normalized_lists.append(p_list)
        else:
            normalized_lists.append([])

    # 2. Emparejamiento Multi-Lista Inteligente
    matcher = ProductMatcher(normalized_lists)
    groups, match_stats = matcher.match_all(similarity_threshold=req.similarity_threshold or 85.0)
    
    # 3. Cálculo de Precios y Totales
    calculator = PriceCalculator(req.configs)
    comparison_data = calculator.calculate_all(groups)
    
    CURRENT_SESSION["matched_groups"] = groups
    CURRENT_SESSION["match_stats"] = match_stats
    CURRENT_SESSION["comparison_results"] = comparison_data
    
    return {
        "success": True,
        "stats": match_stats,
        "totals": comparison_data["totals"],
        "rows": comparison_data["rows"],
        "total_items": len(comparison_data["rows"])
    }

@app.post("/api/match/override")
async def override_match(req: OverrideMatchRequest):
    """Permite al usuario confirmar o desvincular un emparejamiento dudoso."""
    groups = CURRENT_SESSION.get("matched_groups", [])
    found = False
    new_groups = []
    matcher = ProductMatcher([])
    
    if req.action == "confirm_all":
        for g in groups:
            if g.get("match_status") == "dudoso":
                g["match_status"] = "en_3_listas" if g["present_count"] == 3 else "en_2_listas"
                g["manual_override"] = True
            new_groups.append(g)
        found = True
    elif req.action == "unlink_all":
        for g in groups:
            if g.get("match_status") == "dudoso":
                items = [it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]
                for it in items:
                    single_g = matcher._create_group_from_items([it], match_method="manual_desvinculado", confidence=0.0)
                    single_g["manual_override"] = True
                    new_groups.append(single_g)
            else:
                new_groups.append(g)
        found = True
    else:
        for g in groups:
            if g["group_id"] == req.group_id:
                found = True
                if req.action == "confirm":
                    g["match_status"] = "en_3_listas" if g["present_count"] == 3 else "en_2_listas"
                    g["manual_override"] = True
                    new_groups.append(g)
                elif req.action == "unlink":
                    # Separar los items en grupos individuales exclusivos
                    items = [it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]
                    for it in items:
                        single_g = matcher._create_group_from_items([it], match_method="manual_desvinculado", confidence=0.0)
                        single_g["manual_override"] = True
                        new_groups.append(single_g)
            else:
                new_groups.append(g)
            
    if not found:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
        
    CURRENT_SESSION["matched_groups"] = new_groups
    match_stats = matcher._calculate_match_stats(new_groups)
    CURRENT_SESSION["match_stats"] = match_stats
    
    # Recalcular precios
    calculator = PriceCalculator(CURRENT_SESSION["configs"])
    comparison_data = calculator.calculate_all(new_groups)
    CURRENT_SESSION["comparison_results"] = comparison_data
    
    return {
        "success": True,
        "stats": match_stats,
        "totals": comparison_data["totals"],
        "rows": comparison_data["rows"]
    }

def get_base_dir() -> str:
    """Retorna el directorio base correcto ya sea en Python puro o dentro del .exe compilado por PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_demo_file(rel_path: str) -> Optional[str]:
    """Busca un archivo de demostración en MEIPASS, directorio actual o carpeta del ejecutable."""
    base_dir = get_base_dir()
    candidates = [
        os.path.join(base_dir, rel_path),
        os.path.join(os.getcwd(), rel_path),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel_path),
        os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)), rel_path)
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

@app.post("/api/load_demo")
async def load_demo():
    """Carga automáticamente las 3 listas de prueba de la carpeta datos_prueba/ de forma asíncrona y segura."""
    global LAST_HEARTBEAT
    LAST_HEARTBEAT = time.time()
    
    demo_specs = [
        (0, os.path.join("datos_prueba", "Proveedor_1_Distribuidora_Norte.xlsx"), "Proveedor 1 (Norte)"),
        (1, os.path.join("datos_prueba", "Proveedor_2_Mayorista_Central.csv"), "Proveedor 2 (Central)"),
        (2, os.path.join("datos_prueba", "Proveedor_3_Supercenter_Nacional.xlsx"), "Proveedor 3 (Supercenter)")
    ]
    
    def process_demo_sync():
        res = []
        for idx, rel_path, default_name in demo_specs:
            real_path = find_demo_file(rel_path)
            if real_path and os.path.exists(real_path):
                with open(real_path, "rb") as f:
                    content = f.read()
                filename = os.path.basename(real_path)
                df, columns, warnings = parse_file_to_dataframe(content, filename)
                detected_map = detect_column_mapping(columns)
                
                CURRENT_SESSION["raw_files"][idx] = {
                    "filename": filename,
                    "bytes": content,
                    "df": df,
                    "columns": columns,
                    "warnings": warnings,
                    "total_rows": len(df)
                }
                CURRENT_SESSION["mappings"][idx] = detected_map
                CURRENT_SESSION["configs"][idx]["nombre"] = default_name
                
                res.append({
                    "list_idx": idx,
                    "filename": filename,
                    "prov_name": default_name,
                    "total_rows": len(df),
                    "columns": columns,
                    "detected_mapping": detected_map,
                    "preview_rows": df.head(10).to_dict(orient="records")
                })
        return res

    try:
        results = await asyncio.to_thread(process_demo_sync)
        LAST_HEARTBEAT = time.time()
        
        if not results:
            raise HTTPException(status_code=404, detail="No se encontraron los archivos de prueba en la instalación.")
            
        return {"success": True, "files": results}
    except Exception as e:
        logger.exception("Error al cargar datos de prueba")
        raise HTTPException(status_code=500, detail=f"Error al cargar archivos de prueba: {str(e)}")

@app.get("/api/export/order/{list_idx}")
async def export_order(list_idx: int):
    """Descarga la Orden de Compra en Excel para un proveedor específico."""
    comp_data = CURRENT_SESSION.get("comparison_results")
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
        
    order_bytes = ResultExporter.export_purchase_order_excel(comp_data, CURRENT_SESSION["configs"], list_idx)
    prov_name = CURRENT_SESSION["configs"][list_idx]["nombre"].replace(" ", "_")
    return Response(
        content=order_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Pedido_{prov_name}.xlsx"}
    )

@app.get("/api/export/excel")
async def export_excel():
    """Descarga los resultados en Excel (.xlsx) con estilos y formato condicional."""
    comp_data = CURRENT_SESSION.get("comparison_results")
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
        
    excel_bytes = ResultExporter.export_to_excel(comp_data, CURRENT_SESSION["configs"])
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Comparacion_Listas_Precios.xlsx"}
    )

@app.get("/api/export/csv")
async def export_csv():
    """Descarga los resultados en CSV."""
    comp_data = CURRENT_SESSION.get("comparison_results")
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
        
    csv_bytes = ResultExporter.export_to_csv(comp_data, CURRENT_SESSION["configs"])
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=Comparacion_Listas_Precios.csv"}
    )

@app.get("/api/export/pdf")
async def export_pdf():
    """Descarga el informe ejecutivo en PDF."""
    comp_data = CURRENT_SESSION.get("comparison_results")
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
        
    pdf_bytes = ResultExporter.export_to_pdf(comp_data, CURRENT_SESSION["configs"])
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Informe_Comparativo_Precios.pdf"}
    )

@app.get("/api/session/save")
async def save_session():
    """Descarga la sesión actual en formato JSON para reabrirla luego."""
    comp_data = CURRENT_SESSION.get("comparison_results")
    session_dict = {
        "configs": CURRENT_SESSION.get("configs", []),
        "mappings": CURRENT_SESSION.get("mappings", {}),
        "comparison_results": comp_data,
        "match_stats": CURRENT_SESSION.get("match_stats", {})
    }
    return Response(
        content=json.dumps(session_dict, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=Sesion_Comparacion.json"}
    )

@app.post("/api/session/load")
async def load_session(file: UploadFile = File(...)):
    """Restaura una sesión guardada previamente."""
    try:
        content = await file.read()
        session_dict = json.loads(content.decode('utf-8'))
        
        CURRENT_SESSION["configs"] = session_dict.get("configs", CURRENT_SESSION["configs"])
        CURRENT_SESSION["mappings"] = session_dict.get("mappings", {})
        CURRENT_SESSION["comparison_results"] = session_dict.get("comparison_results")
        CURRENT_SESSION["match_stats"] = session_dict.get("match_stats", {})
        
        return {
            "success": True,
            "configs": CURRENT_SESSION["configs"],
            "totals": CURRENT_SESSION["comparison_results"]["totals"] if CURRENT_SESSION["comparison_results"] else {},
            "rows": CURRENT_SESSION["comparison_results"]["rows"] if CURRENT_SESSION["comparison_results"] else []
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al cargar sesión: {str(e)}")

# Montar archivos estáticos para la interfaz de usuario
static_dir = os.path.join(get_base_dir(), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Comparador de Listas de Precios</h1><p>Frontend no encontrado en /static/index.html</p>")
