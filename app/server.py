import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Body
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.parser import parse_file_to_dataframe, detect_column_mapping
from app.normalizer import normalize_product_record
from app.matcher import ProductMatcher
from app.calculator import PriceCalculator
from app.exporter import ResultExporter

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

def clean_json_data(obj: Any) -> Any:
    """Reemplaza NaN, inf y -inf por None para serialización JSON segura."""
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_json_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_data(v) for v in obj]
    return obj

# Estado de sesión local en memoria (fallback para uso monousuario)
CURRENT_SESSION: Dict[str, Any] = {
    "raw_files": {}, # 0, 1, 2 -> {"filename": str, "records": list, "columns": list, "warnings": list}
    "mappings": {},
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
    files_data: Optional[Dict[str, List[Dict[str, Any]]]] = None

class OverrideMatchRequest(BaseModel):
    group_id: str
    action: str # "confirm", "unlink", "confirm_all", "unlink_all"
    matched_groups: Optional[List[Dict[str, Any]]] = None
    configs: Optional[List[Dict[str, Any]]] = None

@app.get("/api/health")
@app.post("/api/health")
@app.get("/api/heartbeat")
@app.post("/api/heartbeat")
async def health_check():
    """Endpoint de estado para verificar que el servidor está 100% activo."""
    return {"status": "ok"}

@app.post("/api/upload/{list_idx}")
async def upload_file(list_idx: int, file: UploadFile = File(...)):
    """Carga un archivo (.xlsx, .xls, .csv, .pdf), detecta columnas y retorna registros serializados."""
    if list_idx not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="Índice de lista inválido (debe ser 0, 1 o 2).")
        
    try:
        content = await file.read()
        filename = file.filename
        
        df, columns, warnings = parse_file_to_dataframe(content, filename)
        
        if df.empty:
            raise HTTPException(status_code=400, detail=f"El archivo {filename} está vacío o no contiene filas válidas.")
            
        detected_map = detect_column_mapping(columns)
        
        # Limpiar registros para compatibilidad JSON pura
        df_clean = df.fillna("")
        records = df_clean.to_dict(orient="records")
        preview_rows = df_clean.head(10).to_dict(orient="records")
        
        CURRENT_SESSION["raw_files"][list_idx] = {
            "filename": filename,
            "records": records,
            "columns": columns,
            "warnings": warnings,
            "total_rows": len(records)
        }
        CURRENT_SESSION["mappings"][list_idx] = detected_map
        
        return clean_json_data({
            "success": True,
            "list_idx": list_idx,
            "filename": filename,
            "total_rows": len(records),
            "columns": columns,
            "detected_mapping": detected_map,
            "warnings": warnings,
            "preview_rows": preview_rows,
            "raw_records": records
        })
    except Exception as e:
        logger.exception("Error al subir archivo")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/upload/{list_idx}")
async def remove_file(list_idx: int):
    """Elimina una lista cargada de la sesión."""
    if list_idx in CURRENT_SESSION["raw_files"]:
        del CURRENT_SESSION["raw_files"][list_idx]
    if list_idx in CURRENT_SESSION["mappings"]:
        del CURRENT_SESSION["mappings"][list_idx]
    return {"success": True}

def generate_in_memory_demo_datasets() -> List[Dict[str, Any]]:
    """Genera 3 listas de prueba realistas y comparables en memoria al instante."""
    articulos_base = [
        ("Gaseosa Cola", ["2.25L", "1.5L", "500ml", "354ml"], "Coca-Cola", 2800.0, "Bebidas"),
        ("Gaseosa Lima Limón", ["2.25L", "1.5L", "500ml"], "Sprite", 2700.0, "Bebidas"),
        ("Cerveza Rubia", ["1L", "473ml", "Pack x6"], "Quilmes", 2200.0, "Bebidas"),
        ("Leche Entera", ["1L", "Tetra 1L", "Sachet 1L"], "La Serenísima", 1400.0, "Lácteos"),
        ("Leche Descremada", ["1L", "Tetra 1L"], "Sancor", 1350.0, "Lácteos"),
        ("Yogur Frutilla", ["1kg", "180g"], "La Serenísima", 2100.0, "Lácteos"),
        ("Dulce de Leche Clásico", ["400g", "1kg"], "San Ignacio", 2500.0, "Lácteos"),
        ("Aceite Girasol", ["900ml", "1.5L", "3L"], "Natura", 2400.0, "Almacén"),
        ("Aceite Mezcla", ["900ml", "1.5L"], "Cocinero", 1900.0, "Almacén"),
        ("Arroz Largo Fino", ["1kg", "500g"], "Gallo", 1800.0, "Almacén"),
        ("Fideos Guiseros", ["500g", "1kg"], "Matarazzo", 1300.0, "Almacén"),
        ("Fideos Tallarines", ["500g"], "Lucchetti", 1250.0, "Almacén"),
        ("Puré de Tomate", ["520g"], "Marolio", 850.0, "Almacén"),
        ("Mayonesa Clásica", ["475g", "950g"], "Hellmanns", 2600.0, "Almacén"),
        ("Galletitas Dulces", ["120g", "300g"], "Arcor", 1100.0, "Galletitas"),
        ("Galletitas de Agua", ["100g", "Pack x3 300g"], "Terrabusi", 950.0, "Galletitas"),
        ("Shampoo Anticaspa", ["400ml", "200ml"], "Head & Shoulders", 4500.0, "Perfumería"),
        ("Acondicionador Brillo", ["400ml", "200ml"], "Pantene", 4300.0, "Perfumería"),
        ("Desodorante Aerosol", ["150ml", "Pack x2"], "Rexona", 2800.0, "Perfumería"),
        ("Crema Dental Triple Acción", ["70g", "140g"], "Colgate", 1900.0, "Perfumería")
    ]
    
    pool = []
    ean_base = 779100000000
    for i in range(250):
        art, pres_list, brand, base_price, cat = articulos_base[i % len(articulos_base)]
        pres = pres_list[(i // len(articulos_base)) % len(pres_list)]
        mult = 1.8 if "2.25" in pres or "Pack x6" in pres else (1.3 if "1.5" in pres or "Pack x3" in pres else (0.6 if "500" in pres or "200" in pres else 1.0))
        price = round(base_price * mult, 2)
        pool.append({
            "ean": str(ean_base + i + 1),
            "sku": f"SKU-{10000 + i}",
            "codigo": f"ART{i+1:04d}",
            "nombre": f"{art} {brand} {pres}",
            "marca": brand,
            "categoria": cat,
            "precio": price
        })

    # Lista 1: Distribuidora Norte (Excel)
    l1_rows = []
    for item in pool[:220]:
        var = 1.0 + ((hash(item['ean']) % 15) - 7) / 100.0
        p = round(item['precio'] * var, 2)
        l1_rows.append({
            "Código EAN": item['ean'],
            "Descripción del Artículo": item['nombre'],
            "Marca": item['marca'],
            "Precio Unitario": p,
            "Rubro": item['categoria']
        })

    # Lista 2: Mayorista Central (CSV)
    l2_rows = []
    for item in pool[30:250]:
        var = 1.0 + ((hash(item['sku']) % 20) - 10) / 100.0
        p = round(item['precio'] * var, 2)
        l2_rows.append({
            "SKU_PROD": item['sku'],
            "PRODUCTO": f"{item['nombre'].upper()} - PROMO",
            "PRECIO_NETO": p,
            "EAN13": item['ean'],
            "FAMILIA": item['categoria']
        })

    # Lista 3: Supercenter Nacional (Excel)
    l3_rows = []
    for item in pool[10:230]:
        var = 1.0 + ((hash(item['codigo']) % 18) - 8) / 100.0
        p = round(item['precio'] * var, 2)
        l3_rows.append({
            "Cod_Articulo": item['codigo'],
            "Detalle_Producto": item['nombre'],
            "Cod_Barra": item['ean'],
            "Importe_Final": p,
            "Sección": item['categoria']
        })

    demo_data = [
        (0, "Proveedor_1_Distribuidora_Norte.xlsx", "Proveedor 1 (Norte)", l1_rows),
        (1, "Proveedor_2_Mayorista_Central.csv", "Proveedor 2 (Central)", l2_rows),
        (2, "Proveedor_3_Supercenter_Nacional.xlsx", "Proveedor 3 (Supercenter)", l3_rows)
    ]
    
    results = []
    for idx, filename, prov_name, rows in demo_data:
        df = pd.DataFrame(rows)
        cols = list(df.columns)
        detected_map = detect_column_mapping(cols)
        
        CURRENT_SESSION["raw_files"][idx] = {
            "filename": filename,
            "records": rows,
            "columns": cols,
            "warnings": [],
            "total_rows": len(rows)
        }
        CURRENT_SESSION["mappings"][idx] = detected_map
        CURRENT_SESSION["configs"][idx]["nombre"] = prov_name
        
        results.append({
            "list_idx": idx,
            "filename": filename,
            "prov_name": prov_name,
            "total_rows": len(rows),
            "columns": cols,
            "detected_mapping": detected_map,
            "warnings": [],
            "preview_rows": rows[:10],
            "raw_records": rows
        })
    return results

@app.post("/api/load_demo")
async def load_demo():
    """Carga automáticamente las 3 listas de demostración instantáneamente en memoria."""
    try:
        results = generate_in_memory_demo_datasets()
        return clean_json_data({"success": True, "files": results})
    except Exception as e:
        logger.exception("Error al generar datos de prueba")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_all_lists(req: ProcessRequest):
    """Procesa el 100% de las filas de todas las listas, normaliza, empareja y calcula totales."""
    files_data = req.files_data or {}
    
    # Si no se enviaron en el body, usar CURRENT_SESSION
    if not files_data:
        for idx, f_info in CURRENT_SESSION.get("raw_files", {}).items():
            files_data[str(idx)] = f_info.get("records", [])
            
    if not files_data or all(len(v) == 0 for v in files_data.values()):
        raise HTTPException(status_code=400, detail="No se ha cargado ninguna lista de precios para procesar.")
        
    CURRENT_SESSION["configs"] = req.configs
    
    # 1. Normalizar productos
    normalized_lists: List[List[Dict[str, Any]]] = []
    
    for l_idx in range(3):
        str_idx = str(l_idx)
        records = files_data.get(str_idx, [])
        if records:
            mapping = req.mappings.get(str_idx, {})
            p_list = []
            for row_num, row_dict in enumerate(records, 1):
                mapped_row = {}
                for std_field, orig_col in mapping.items():
                    if orig_col and orig_col in row_dict:
                        mapped_row[std_field] = row_dict[orig_col]
                    else:
                        mapped_row[std_field] = None
                norm_item = normalize_product_record(mapped_row, list_index=l_idx, row_number=row_num)
                p_list.append(norm_item)
            normalized_lists.append(p_list)
        else:
            normalized_lists.append([])

    # 2. Emparejamiento
    matcher = ProductMatcher(normalized_lists)
    groups, match_stats = matcher.match_all(similarity_threshold=req.similarity_threshold or 85.0)
    
    # 3. Cálculo de Precios y Totales
    calculator = PriceCalculator(req.configs)
    comparison_data = calculator.calculate_all(groups)
    
    CURRENT_SESSION["matched_groups"] = groups
    CURRENT_SESSION["match_stats"] = match_stats
    CURRENT_SESSION["comparison_results"] = comparison_data
    
    return clean_json_data({
        "success": True,
        "stats": match_stats,
        "totals": comparison_data["totals"],
        "rows": comparison_data["rows"],
        "matched_groups": groups,
        "total_items": len(comparison_data["rows"])
    })

@app.post("/api/match/override")
async def override_match(req: OverrideMatchRequest):
    """Permite al usuario confirmar o desvincular un emparejamiento dudoso."""
    groups = req.matched_groups or CURRENT_SESSION.get("matched_groups", [])
    configs = req.configs or CURRENT_SESSION.get("configs", [])
    
    found = False
    new_groups = []
    matcher = ProductMatcher([])
    
    if req.action == "confirm_all":
        for g in groups:
            if g.get("match_status") == "dudoso":
                g["match_status"] = "en_3_listas" if g.get("present_count") == 3 else "en_2_listas"
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
            if g.get("group_id") == req.group_id:
                found = True
                if req.action == "confirm":
                    g["match_status"] = "en_3_listas" if g.get("present_count") == 3 else "en_2_listas"
                    g["manual_override"] = True
                    new_groups.append(g)
                elif req.action == "unlink":
                    items = [it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]
                    for it in items:
                        single_g = matcher._create_group_from_items([it], match_method="manual_desvinculado", confidence=0.0)
                        single_g["manual_override"] = True
                        new_groups.append(single_g)
            else:
                new_groups.append(g)
            
    if not found:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
        
    match_stats = matcher._calculate_match_stats(new_groups)
    calculator = PriceCalculator(configs)
    comparison_data = calculator.calculate_all(new_groups)
    
    CURRENT_SESSION["matched_groups"] = new_groups
    CURRENT_SESSION["match_stats"] = match_stats
    CURRENT_SESSION["comparison_results"] = comparison_data
    
    return clean_json_data({
        "success": True,
        "stats": match_stats,
        "totals": comparison_data["totals"],
        "rows": comparison_data["rows"],
        "matched_groups": new_groups
    })

# ========================================================
# EXPORTACIONES
# ========================================================
@app.post("/api/export/excel")
@app.get("/api/export/excel")
async def export_excel(payload: Optional[Dict[str, Any]] = None):
    comp_data = payload.get("comparison_results") if payload else CURRENT_SESSION.get("comparison_results")
    configs = payload.get("configs") if payload else CURRENT_SESSION.get("configs", [])
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
    excel_bytes = ResultExporter.export_to_excel(comp_data, configs)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Comparacion_Precios_Proveedores.xlsx"}
    )

@app.post("/api/export/csv")
@app.get("/api/export/csv")
async def export_csv(payload: Optional[Dict[str, Any]] = None):
    comp_data = payload.get("comparison_results") if payload else CURRENT_SESSION.get("comparison_results")
    configs = payload.get("configs") if payload else CURRENT_SESSION.get("configs", [])
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
    csv_bytes = ResultExporter.export_to_csv(comp_data, configs)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=Comparacion_Listas_Precios.csv"}
    )

@app.post("/api/export/pdf")
@app.get("/api/export/pdf")
async def export_pdf(payload: Optional[Dict[str, Any]] = None):
    comp_data = payload.get("comparison_results") if payload else CURRENT_SESSION.get("comparison_results")
    configs = payload.get("configs") if payload else CURRENT_SESSION.get("configs", [])
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
    pdf_bytes = ResultExporter.export_to_pdf(comp_data, configs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Informe_Comparativo_Precios.pdf"}
    )

@app.post("/api/export/order/{list_idx}")
@app.get("/api/export/order/{list_idx}")
async def export_order(list_idx: int, payload: Optional[Dict[str, Any]] = None):
    comp_data = payload.get("comparison_results") if payload else CURRENT_SESSION.get("comparison_results")
    configs = payload.get("configs") if payload else CURRENT_SESSION.get("configs", [])
    if not comp_data:
        raise HTTPException(status_code=400, detail="No hay datos de comparación para exportar.")
    order_bytes = ResultExporter.export_purchase_order_excel(comp_data, configs, list_idx)
    prov_name = configs[list_idx]["nombre"].replace(" ", "_")
    return Response(
        content=order_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Pedido_{prov_name}.xlsx"}
    )

@app.get("/api/session/save")
async def save_session():
    comp_data = CURRENT_SESSION.get("comparison_results")
    session_dict = {
        "configs": CURRENT_SESSION.get("configs", []),
        "mappings": CURRENT_SESSION.get("mappings", {}),
        "comparison_results": comp_data,
        "match_stats": CURRENT_SESSION.get("match_stats", {})
    }
    return Response(
        content=json.dumps(clean_json_data(session_dict), ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=Sesion_Comparacion.json"}
    )

@app.post("/api/session/load")
async def load_session(file: UploadFile = File(...)):
    try:
        content = await file.read()
        session_dict = json.loads(content.decode('utf-8'))
        CURRENT_SESSION["configs"] = session_dict.get("configs", CURRENT_SESSION["configs"])
        CURRENT_SESSION["mappings"] = session_dict.get("mappings", {})
        CURRENT_SESSION["comparison_results"] = session_dict.get("comparison_results")
        CURRENT_SESSION["match_stats"] = session_dict.get("match_stats", {})
        return clean_json_data({
            "success": True,
            "configs": CURRENT_SESSION["configs"],
            "totals": CURRENT_SESSION["comparison_results"]["totals"] if CURRENT_SESSION["comparison_results"] else {},
            "rows": CURRENT_SESSION["comparison_results"]["rows"] if CURRENT_SESSION["comparison_results"] else []
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al cargar sesión: {str(e)}")

# Montar archivos estáticos para la interfaz de usuario
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Comparador de Listas de Precios</h1><p>Web App activa.</p>")
