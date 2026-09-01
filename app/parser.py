import io
import re
import csv
import pandas as pd
import openpyxl
from typing import List, Dict, Any, Tuple, Optional
from app.normalizer import parse_price

# Diccionario de alias exactos y patrones para detección automática de columnas
COLUMN_SYNONYMS = {
    "codigo_barras": [
        "codigo_barras", "cod_barras", "código_barras", "código_de_barras", "barcode", 
        "ean", "ean13", "ean-13", "ean_13", "gtin", "upc", "cod_barra", "codigo_ean", 
        "cod_ean", "codigo_de_barra", "codigo_barra", "cod_bar", "cod_ean13"
    ],
    "sku": [
        "sku", "sku_interno", "part_number", "nro_parte", "num_parte"
    ],
    "codigo": [
        "codigo", "cod", "code", "código", "ref", "referencia", "art", "articulo", "artículo", 
        "id", "item", "código_art", "cod_art", "cod_prod", "codigo_producto", "id_articulo"
    ],
    "descripcion": [
        "descripcion", "descripción", "detalle", "producto", "nombre", "articulo", "artículo",
        "descripcion_producto", "desc", "detalle_producto", "denominacion", "denominación",
        "nombre_producto", "item_description", "description", "title"
    ],
    "marca": [
        "marca", "brand", "fabricante", "proveedor_marca", "linea", "línea", "laboratorio"
    ],
    "presentacion": [
        "presentacion", "presentación", "medida", "tamaño", "tamano", "envase", "formato",
        "contenido", "peso", "volumen", "pack", "present"
    ],
    "iva": [
        "iva", "porc_iva", "alicuota_iva", "tasa_iva", "tax", "%_iva", "%iva", "alicuota"
    ],
    "descuento": [
        "descuento", "descuento_porc", "dto", "desc_porc", "bonificacion", "bonif", "rebaja", "discount", "%_dto", "%dto"
    ],
    "precio_final": [
        "precio_final", "precio_con_iva", "precio_total", "p_final", "precio_venta", "precio_c_iva", "precio_final_iva_inc"
    ],
    "precio": [
        "precio", "precio_unitario", "precio_unit", "costo", "importe", "valor", "unit_price", 
        "precio_lista", "p_lista", "precio_s_iva", "precio_sin_iva", "precio_neto", "neto", "costo_unitario", "price"
    ],
    "unidad": [
        "unidad", "unidades", "unidad_medida", "tipo_unidad", "u_m", "um", "unit"
    ],
    "cantidad": [
        "cantidad", "cant", "cant_pedida", "unidades_compra", "cantidad_a_comprar"
    ]
}

def clean_column_name(col: str) -> str:
    """Limpia y normaliza el nombre de una columna para emparejamiento."""
    if not isinstance(col, str):
        col = str(col)
    col = col.strip().lower()
    col = re.sub(r'[\s_\-\.\/\\]+', '_', col)
    col = re.sub(r'[áàäâ]', 'a', col)
    col = re.sub(r'[éèëê]', 'e', col)
    col = re.sub(r'[íìïî]', 'i', col)
    col = re.sub(r'[óòöô]', 'o', col)
    col = re.sub(r'[úùüû]', 'u', col)
    col = re.sub(r'[ñ]', 'n', col)
    col = re.sub(r'[^a-z0-9_%]', '', col)
    return col

def detect_column_mapping(columns: List[str], df: Optional[pd.DataFrame] = None) -> Dict[str, Optional[str]]:
    """
    Intenta mapear automáticamente las columnas del archivo a los campos estándar.
    Utiliza sinónimos y, si se provee el DataFrame, realiza auto-inferencia analizando el contenido real.
    """
    mapping: Dict[str, Optional[str]] = {
        "codigo": None,
        "codigo_barras": None,
        "sku": None,
        "descripcion": None,
        "marca": None,
        "presentacion": None,
        "unidad": None,
        "cantidad": None,
        "precio": None,
        "precio_final": None,
        "iva": None,
        "descuento": None
    }
    
    cleaned_cols = [(clean_column_name(col), col) for col in columns]
    used_original_cols = set()

    # 1. Primera pasada: coincidencia exacta con sinónimos
    for standard_field, synonyms in COLUMN_SYNONYMS.items():
        for clean_col, orig_col in cleaned_cols:
            if orig_col in used_original_cols:
                continue
            if clean_col in synonyms:
                mapping[standard_field] = orig_col
                used_original_cols.add(orig_col)
                break

    # 2. Segunda pasada: coincidencia por palabras clave seguras (longitud >= 4 caracteres)
    for standard_field, synonyms in COLUMN_SYNONYMS.items():
        if mapping[standard_field] is not None:
            continue
        for clean_col, orig_col in cleaned_cols:
            if orig_col in used_original_cols:
                continue
            for syn in synonyms:
                if len(syn) >= 4 and (syn in clean_col or clean_col in syn):
                    mapping[standard_field] = orig_col
                    used_original_cols.add(orig_col)
                    break
            if mapping[standard_field] is not None:
                break

    # 3. Tercera pasada: Auto-detección inteligente por inspección de contenido
    if df is not None and len(df) > 0:
        # 3.1. Si falta precio: encontrar la columna con más valores monetarios/numéricos
        if mapping["precio"] is None and mapping["precio_final"] is None:
            best_price_col = None
            best_price_count = 0
            for col in columns:
                if col in used_original_cols and col == mapping.get("descripcion"):
                    continue
                sample_vals = df[col].dropna().astype(str).tolist()[:50]
                valid_p = sum(1 for v in sample_vals if parse_price(v) > 0)
                if valid_p > best_price_count and valid_p >= max(1, int(len(sample_vals) * 0.2)):
                    best_price_count = valid_p
                    best_price_col = col
                    
            if best_price_col:
                mapping["precio"] = best_price_col
                used_original_cols.add(best_price_col)

        # 3.2. Si falta descripción: encontrar la columna con texto descriptivo más representativo
        if mapping["descripcion"] is None:
            best_desc_col = None
            best_desc_len = 0
            for col in columns:
                if col in used_original_cols and col == mapping.get("precio"):
                    continue
                sample_vals = df[col].dropna().astype(str).tolist()[:50]
                has_letters = any(re.search(r'[A-Za-z]', v) for v in sample_vals)
                avg_len = sum(len(v.strip()) for v in sample_vals) / max(1, len(sample_vals))
                if has_letters and avg_len > best_desc_len:
                    best_desc_len = avg_len
                    best_desc_col = col
                    
            if best_desc_col:
                mapping["descripcion"] = best_desc_col
                used_original_cols.add(best_desc_col)

        # 3.3. Si falta código: detectar columna con códigos alfanuméricos cortos o EAN
        if mapping["codigo"] is None and mapping["codigo_barras"] is None:
            for col in columns:
                if col in used_original_cols:
                    continue
                sample_vals = df[col].dropna().astype(str).tolist()[:50]
                if sample_vals and all(len(v.strip()) <= 20 for v in sample_vals if v.strip()):
                    if any(len(v.strip()) >= 3 for v in sample_vals):
                        mapping["codigo"] = col
                        used_original_cols.add(col)
                        break

    return mapping

def detect_csv_dialect_and_encoding(file_bytes: bytes) -> Tuple[str, str, str]:
    """Detecta encoding y delimitador de un archivo CSV."""
    encodings = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']
    sample = file_bytes[:10240]
    
    detected_encoding = 'utf-8'
    for enc in encodings:
        try:
            sample.decode(enc)
            detected_encoding = enc
            break
        except UnicodeDecodeError:
            continue
            
    text = sample.decode(detected_encoding, errors='ignore')
    
    # Detectar delimitador contando ocurrencias
    delimiters = [',', ';', '\t', '|']
    delimiter_counts = {d: text.count(d) for d in delimiters}
    detected_delimiter = max(delimiter_counts, key=delimiter_counts.get)
    if delimiter_counts[detected_delimiter] == 0:
        detected_delimiter = ','
        
    return detected_encoding, detected_delimiter, text

def parse_file_to_dataframe(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, List[str], List[Dict[str, Any]]]:
    """
    Lee cualquier archivo soportado (XLSX, XLS, CSV, PDF) y retorna:
    - DataFrame con 100% de las filas
    - Lista de columnas originales
    - Lista de advertencias o errores encontrados
    """
    warnings_list = []
    filename_lower = filename.lower()
    
    try:
        if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xlsm'):
            df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl', dtype=str)
        elif filename_lower.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd', dtype=str)
        elif filename_lower.endswith('.csv') or filename_lower.endswith('.txt'):
            encoding, delimiter, _ = detect_csv_dialect_and_encoding(file_bytes)
            df = pd.read_csv(
                io.BytesIO(file_bytes), 
                encoding=encoding, 
                delimiter=delimiter, 
                dtype=str, 
                on_bad_lines='skip',
                skip_blank_lines=False
            )
        elif filename_lower.endswith('.pdf'):
            df = parse_pdf_to_dataframe(file_bytes)
        else:
            raise ValueError(f"Formato de archivo no soportado: {filename}")
            
        df = df.fillna('')
        
        initial_len = len(df)
        df_clean = df[~df.apply(lambda row: row.astype(str).str.strip().eq('').all(), axis=1)].copy()
        empty_rows_count = initial_len - len(df_clean)
        
        if empty_rows_count > 0:
            warnings_list.append({
                "tipo": "filas_vacias",
                "mensaje": f"Se detectaron {empty_rows_count} fila(s) vacías de un total de {initial_len} filas."
            })
            
        df_clean.columns = [str(c).strip() for c in df_clean.columns]
        columns = list(df_clean.columns)
        
        return df_clean, columns, warnings_list
        
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo {filename}: {str(e)}")

def parse_pdf_to_dataframe(file_bytes: bytes) -> pd.DataFrame:
    """
    Extrae tablas y texto estructurado de un archivo PDF usando motores de alta fidelidad:
    1. pdfplumber: Extracción precisa de tablas estructuradas preservando 100% de los nombres.
    2. pymupdf: Detección de bloques de texto y tablas por coordenadas visuales.
    3. Segmentación continua por patrones de precio para PDFs que emiten texto en flujo único.
    """
    rows = []
    
    # ESTRATEGIA 1: pdfplumber para tablas tabulares (detecta tablas como la de Lista 2)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for r in table:
                            if not r:
                                continue
                            cells = [str(c).strip() for c in r if c is not None and str(c).strip()]
                            if len(cells) < 2:
                                continue
                            joined = ' '.join(cells).lower()
                            if ('código' in joined or 'codigo' in joined) and ('precio' in joined or 'venta' in joined):
                                continue
                            if 'página' in joined or 'pagina' in joined or 'page' in joined:
                                continue
                                
                            # Si tiene 3 columnas (Descripción, Peso, Precio)
                            if len(cells) == 3:
                                desc_raw = cells[0].strip()
                                p_raw = cells[2].strip()
                                p_val = parse_price(p_raw)
                                if p_val < 50: # Si la columna 2 era el precio
                                    p_val2 = parse_price(cells[1].strip())
                                    if p_val2 >= 50:
                                        p_val = p_val2
                                        
                                if p_val >= 50 and p_val < 50_000_000 and len(desc_raw) >= 2:
                                    code = ""
                                    code_m = re.match(r'^([A-Za-z0-9_-]{2,15})\s+(.+)$', desc_raw)
                                    if code_m and not code_m.group(1).isalpha():
                                        code = code_m.group(1)
                                        desc_clean = code_m.group(2).strip()
                                    else:
                                        desc_clean = desc_raw
                                        
                                    if any(c.isalpha() for c in desc_clean):
                                        rows.append({
                                            'Codigo': code,
                                            'Detalle_Producto': desc_clean,
                                            'Precio': str(p_val)
                                        })
                                continue
                                
                            # Si tiene 2 columnas (Descripción, Precio) o más de 3
                            price_val = None
                            price_idx = -1
                            for idx in reversed(range(len(cells))):
                                pv = parse_price(cells[idx])
                                if pv >= 50 and pv < 50_000_000:
                                    price_val = pv
                                    price_idx = idx
                                    break
                                    
                            if price_val is not None:
                                non_price = [cells[j] for j in range(len(cells)) if j != price_idx]
                                if not non_price:
                                    continue
                                    
                                desc_full = " ".join(non_price).strip()
                                code = ""
                                code_m = re.match(r'^([A-Za-z0-9_-]{2,15})\s+(.+)$', desc_full)
                                if code_m and not code_m.group(1).isalpha():
                                    code = code_m.group(1)
                                    desc_clean = code_m.group(2).strip()
                                else:
                                    desc_clean = desc_full
                                    
                                if desc_clean and any(c.isalpha() for c in desc_clean):
                                    rows.append({
                                        'Codigo': code,
                                        'Detalle_Producto': desc_clean,
                                        'Precio': str(price_val)
                                    })
    except Exception:
        pass
        
    if rows and len(rows) >= 3:
        return pd.DataFrame(rows)
        
    # ESTRATEGIA 2: PyMuPDF (pymupdf) para extracción de bloques y tablas visuales
    try:
        import pymupdf
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            try:
                tabs = page.find_tables()
                if tabs and len(tabs.tables) > 0:
                    for tab in tabs:
                        df_tab = tab.extract()
                        for r in df_tab:
                            if not r:
                                continue
                            cells = [str(c).strip() for c in r if c is not None and str(c).strip()]
                            if len(cells) < 2:
                                continue
                            joined = ' '.join(cells).lower()
                            if ('código' in joined or 'codigo' in joined) and ('precio' in joined or 'venta' in joined):
                                continue
                                
                            if len(cells) == 3:
                                desc_raw = cells[0].strip()
                                p_val = parse_price(cells[2].strip())
                                if p_val < 50:
                                    p_val = parse_price(cells[1].strip())
                                if p_val >= 50 and p_val < 50_000_000 and len(desc_raw) >= 2:
                                    code = ""
                                    code_m = re.match(r'^([A-Za-z0-9_-]{2,15})\s+(.+)$', desc_raw)
                                    if code_m and not code_m.group(1).isalpha():
                                        code = code_m.group(1)
                                        desc_clean = code_m.group(2).strip()
                                    else:
                                        desc_clean = desc_raw
                                    if any(c.isalpha() for c in desc_clean):
                                        rows.append({
                                            'Codigo': code,
                                            'Detalle_Producto': desc_clean,
                                            'Precio': str(p_val)
                                        })
                                continue
                                
                            price_val = None
                            price_idx = -1
                            for idx in reversed(range(len(cells))):
                                pv = parse_price(cells[idx])
                                if pv >= 50 and pv < 50_000_000:
                                    price_val = pv
                                    price_idx = idx
                                    break
                            if price_val is not None:
                                non_price = [cells[j] for j in range(len(cells)) if j != price_idx]
                                if not non_price:
                                    continue
                                desc_full = " ".join(non_price).strip()
                                code = ""
                                code_m = re.match(r'^([A-Za-z0-9_-]{2,15})\s+(.+)$', desc_full)
                                if code_m and not code_m.group(1).isalpha():
                                    code = code_m.group(1)
                                    desc_clean = code_m.group(2).strip()
                                else:
                                    desc_clean = desc_full
                                if desc_clean and any(c.isalpha() for c in desc_clean):
                                    rows.append({
                                        'Codigo': code,
                                        'Detalle_Producto': desc_clean,
                                        'Precio': str(price_val)
                                    })
            except Exception:
                pass
                
            if not rows:
                txt = page.get_text("text")
                if txt:
                    for l in txt.splitlines():
                        line_clean = l.strip()
                        if not line_clean or len(line_clean) < 3:
                            continue
                        tokens = [t.strip() for t in re.split(r'\s+', line_clean) if t.strip()]
                        if len(tokens) >= 2:
                            pv = parse_price(tokens[-1])
                            if pv >= 50 and pv < 50_000_000:
                                non_price = tokens[:-1]
                                code = ""
                                if len(non_price) >= 2 and (non_price[0].isdigit() or re.match(r'^[A-Za-z]{1,5}\d{2,8}$', non_price[0])):
                                    code = non_price[0]
                                    desc = ' '.join(non_price[1:])
                                else:
                                    desc = ' '.join(non_price)
                                if desc and any(c.isalpha() for c in desc):
                                    rows.append({
                                        'Codigo': code,
                                        'Detalle_Producto': desc,
                                        'Precio': str(pv)
                                    })
    except Exception:
        pass

    if rows and len(rows) >= 3:
        return pd.DataFrame(rows)

    # ESTRATEGIA 3: Fallback con segmentación continua de flujo
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text += "\n" + t
                
        if full_text:
            price_pattern = re.compile(r'(?:(?<=\s)|^)(\$?\s*\d{3,7}\.\d{2}|\$?\s*\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\$?\s*\d{4,7})(?=\s+[A-Za-z0-9]|\s*$)')
            for chunk in full_text.splitlines():
                chunk_clean = chunk.strip()
                if not chunk_clean:
                    continue
                matches = list(price_pattern.finditer(chunk_clean))
                if matches:
                    last_pos = 0
                    for m in matches:
                        p_val = parse_price(m.group(1))
                        desc_seg = chunk_clean[last_pos:m.start()].strip()
                        last_pos = m.end()
                        if desc_seg and p_val >= 50 and p_val < 50_000_000:
                            toks = [tk.strip() for tk in re.split(r'\s+', desc_seg) if tk.strip()]
                            code = ""
                            if len(toks) >= 2 and (toks[0].isdigit() or re.match(r'^[A-Za-z]{1,5}\d{2,8}$', toks[0])):
                                code = toks[0]
                                desc_seg = " ".join(toks[1:])
                            if desc_seg and any(c.isalpha() for c in desc_seg):
                                rows.append({
                                    'Codigo': code,
                                    'Detalle_Producto': desc_seg,
                                    'Precio': str(p_val)
                                })
    except Exception:
        pass

    if rows:
        return pd.DataFrame(rows)
    else:
        raise ValueError("El archivo PDF no contiene texto o tablas extraíbles.")
