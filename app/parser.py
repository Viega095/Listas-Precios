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
    Extrae texto estructurado y tablas de un PDF usando pypdf con reconstrucción de coordenadas (X, Y)
    para alinear perfectamente tablas con múltiples columnas, pesos y precios.
    """
    from pypdf import PdfReader
    
    reader = PdfReader(io.BytesIO(file_bytes))
    all_lines = []
    
    # 1. Extraer líneas agrupadas por coordenadas visuales Y (mismo renglón horizontal)
    for page_idx, page in enumerate(reader.pages):
        words_with_pos = []
        
        def visitor_body(text, cm, tm, font_dict, font_size):
            if text and text.strip():
                # tm[4] = coordenada X, tm[5] = coordenada Y
                x = tm[4]
                y = tm[5]
                words_with_pos.append((y, x, text))
                
        try:
            page.extract_text(visitor_text=visitor_body)
        except Exception:
            words_with_pos = []
            
        if words_with_pos:
            # Ordenar de arriba hacia abajo (Y descendente) y de izquierda a derecha (X ascendente)
            words_with_pos.sort(key=lambda item: (-item[0], item[1]))
            current_line = []
            current_y = None
            
            for y, x, text in words_with_pos:
                if current_y is None or abs(y - current_y) <= 4:
                    current_line.append((x, text))
                    if current_y is None:
                        current_y = y
                else:
                    current_line.sort(key=lambda it: it[0])
                    line_str = ' '.join(it[1].strip() for it in current_line).strip()
                    if line_str:
                        all_lines.append(line_str)
                    current_line = [(x, text)]
                    current_y = y
                    
            if current_line:
                current_line.sort(key=lambda it: it[0])
                line_str = ' '.join(it[1].strip() for it in current_line).strip()
                if line_str:
                    all_lines.append(line_str)
        else:
            # Fallback a extracción tradicional de texto si no se pudo leer coordenadas
            try:
                txt = page.extract_text(extraction_mode="layout") or page.extract_text()
            except Exception:
                txt = page.extract_text()
            if txt:
                for l in txt.splitlines():
                    ls = l.strip()
                    if ls:
                        all_lines.append(ls)

    if not all_lines:
        raise ValueError("El archivo PDF no contiene texto extraíble o es un documento escaneado sin OCR.")

    IGNORE_KEYWORDS = [
        'pagina', 'página', 'page', 'código descripción', 'codigo descripcion', 
        'lista de precio', 'tarifa', 'cuit', 'xxxxxx', 'total general', 'subtotal'
    ]
    
    parsed_rows = []
    
    for l in all_lines:
        line_clean = l.strip()
        if not line_clean or len(line_clean) < 3:
            continue
            
        line_lower = line_clean.lower()
        if any(line_lower.startswith(k) for k in IGNORE_KEYWORDS):
            continue
        if ('código' in line_lower or 'codigo' in line_lower) and ('descripción' in line_lower or 'descripcion' in line_lower):
            continue
        if re.match(r'^[xX\s\-_=.]+$', line_clean):
            continue
            
        # Tokenizar la fila
        tokens = [t.strip() for t in re.split(r'\s+', line_clean) if t.strip()]
        if len(tokens) < 2:
            continue
            
        # El precio real en dinero es el último token válido de la fila
        last_tok = tokens[-1].replace('$', '').strip()
        price_val = parse_price(last_tok)
        
        # Validar que el precio esté en rango lógico para una unidad de producto (entre $50 y $50.000.000)
        if price_val <= 0 or price_val > 50_000_000:
            if len(tokens) >= 3:
                alt_p = parse_price(tokens[-2].replace('$', '').strip())
                if alt_p > 0 and alt_p < 50_000_000:
                    price_val = alt_p
                    tokens = tokens[:-1]
                else:
                    continue
            else:
                continue
                
        desc_tokens = tokens[:-1]
        if not desc_tokens:
            continue
            
        # Si el último token restante en la descripción es una columna auxiliar de peso/multiplicador (ej: '1', '1.5', '15', '0.085', '0.25')
        if len(desc_tokens) >= 2:
            last_dt = desc_tokens[-1].replace(',', '.')
            try:
                _ = float(last_dt)
                # Es un número suelto de la columna peso -> removerlo de la descripción
                desc_tokens = desc_tokens[:-1]
            except ValueError:
                pass
                
        # Chequear si el primer token es un código de artículo (ej: 3003, SHU008, 1528)
        code = ""
        if len(desc_tokens) >= 2:
            first_t = desc_tokens[0]
            if (first_t.isdigit() and len(first_t) <= 14) or (re.match(r'^[A-Za-z]{1,5}\d{2,8}$', first_t)):
                code = first_t
                desc_tokens = desc_tokens[1:]
                
        desc_str = " ".join(desc_tokens).strip()
        if desc_str and len(desc_str) >= 2 and any(c.isalpha() for c in desc_str):
            parsed_rows.append({
                "Codigo": code,
                "Detalle_Producto": desc_str,
                "Precio": str(price_val)
            })

    if parsed_rows:
        return pd.DataFrame(parsed_rows)
    else:
        return pd.DataFrame({'Detalle_Producto': all_lines, 'Precio': ['0.0'] * len(all_lines)})
