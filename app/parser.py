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
    """Extrae texto estructurado y tablas de un PDF usando pypdf con análisis de patrones de producto y precio."""
    from pypdf import PdfReader
    
    reader = PdfReader(io.BytesIO(file_bytes))
    all_lines = []
    
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            if line_str:
                all_lines.append(line_str)
                
    if not all_lines:
        raise ValueError("El archivo PDF no contiene texto extraíble o es un documento escaneado sin OCR.")
        
    parsed_rows = []
    
    # Patrón de precio en cualquier posición (formato argentino y estándar)
    PRICE_REGEX = re.compile(r'(\$?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})|\$?\s*\d+(?:[.,]\d{1,2})?)')
    IGNORE_KEYWORDS = ['pagina', 'página', 'hoja', 'vigencia', 'lista de precio', 'telefono', 'teléfono', 'cuit', 'total general', 'subtotal']

    for l in all_lines:
        line_clean = l.strip()
        if not line_clean or len(line_clean) < 3:
            continue
            
        line_lower = line_clean.lower()
        if any(line_lower.startswith(k) for k in IGNORE_KEYWORDS) and not re.search(r'\d{3,}', line_clean):
            continue
            
        if re.search(r'^(?:lista\s+de\s+precios?|catalogo|precios\s+vigentes|tarifa\s+de\s+precios)\b', line_lower):
            continue

        # Separar por delimitadores comunes si existen
        if '\t' in line_clean:
            parts = [p.strip() for p in line_clean.split('\t') if p.strip()]
        elif '|' in line_clean:
            parts = [p.strip() for p in line_clean.split('|') if p.strip()]
        elif ';' in line_clean:
            parts = [p.strip() for p in line_clean.split(';') if p.strip()]
        else:
            parts = [p.strip() for p in re.split(r'\s{2,}', line_clean) if p.strip()]
            
        if len(parts) >= 2:
            # Encontrar precio entre las columnas
            price_val = None
            price_idx = -1
            for idx in reversed(range(len(parts))):
                pv = parse_price(parts[idx])
                if pv > 0:
                    price_val = pv
                    price_idx = idx
                    break
                    
            if price_val is not None:
                non_price = [parts[j] for j in range(len(parts)) if j != price_idx]
                code = ""
                desc = ""
                if len(non_price) >= 2 and (non_price[0].isdigit() or re.match(r'^[A-Za-z0-9_-]{2,15}$', non_price[0])):
                    code = non_price[0]
                    desc = " ".join(non_price[1:])
                else:
                    desc = " ".join(non_price)
                    
                if desc and len(desc) >= 2:
                    parsed_rows.append({
                        "Codigo": code,
                        "Detalle_Producto": desc,
                        "Precio": str(price_val)
                    })
                    continue

        # Si vino como una sola línea continua, extraer precio con regex
        matches = list(PRICE_REGEX.finditer(line_clean))
        if matches:
            last_m = matches[-1]
            pv = parse_price(last_m.group(1))
            if pv > 0:
                text_part = (line_clean[:last_m.start()] + " " + line_clean[last_m.end():]).strip()
                code_m = re.match(r'^([A-Za-z0-9_-]{3,15})\s+(.+)$', text_part)
                if code_m and not code_m.group(1).isalpha():
                    code = code_m.group(1)
                    desc = code_m.group(2).strip()
                else:
                    code = ""
                    desc = text_part
                    
                if desc and len(desc) >= 2:
                    parsed_rows.append({
                        "Codigo": code,
                        "Detalle_Producto": desc,
                        "Precio": str(pv)
                    })

    if parsed_rows:
        return pd.DataFrame(parsed_rows)
    else:
        # Fallback estructurado
        return pd.DataFrame({'Detalle_Producto': all_lines, 'Precio': ['0.0'] * len(all_lines)})
