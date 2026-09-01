import io
import re
import csv
import pandas as pd
import openpyxl
from typing import List, Dict, Any, Tuple, Optional

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

def detect_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """
    Intenta mapear automáticamente las columnas del archivo a los campos estándar.
    Retorna un diccionario de campo_estandar -> nombre_columna_original.
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
                # Solo buscar substring si el sinónimo tiene al menos 4 caracteres para evitar falsos positivos
                if len(syn) >= 4 and (syn in clean_col or clean_col in syn):
                    mapping[standard_field] = orig_col
                    used_original_cols.add(orig_col)
                    break
            if mapping[standard_field] is not None:
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
    """Extrae texto estructurado y tablas de un PDF usando pypdf."""
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
    price_pattern = re.compile(r'(\$?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\$?\s*\d+(?:[.,]\d{1,2})?)\s*$')

    for l in all_lines:
        if '\t' in l:
            parts = [p.strip() for p in l.split('\t') if p.strip()]
        elif '|' in l:
            parts = [p.strip() for p in l.split('|') if p.strip()]
        elif ';' in l:
            parts = [p.strip() for p in l.split(';') if p.strip()]
        else:
            # Separar por múltiples espacios
            parts = [p.strip() for p in re.split(r'\s{2,}', l) if p.strip()]
            if len(parts) <= 1:
                # Intentar extraer precio al final de la línea
                match_p = price_pattern.search(l)
                if match_p and match_p.start() > 0:
                    desc_part = l[:match_p.start()].strip()
                    price_part = match_p.group(1).replace('$', '').strip()
                    # Verificar si la descripción empieza con un código alfanumérico
                    match_code = re.match(r'^([A-Za-z0-9_-]{3,15})\s+(.+)$', desc_part)
                    if match_code:
                        parts = [match_code.group(1), match_code.group(2), price_part]
                    else:
                        parts = [desc_part, price_part]
                else:
                    parts = [l]
        if parts:
            parsed_rows.append(parts)
        
    max_cols = max((len(r) for r in parsed_rows), default=1)
    if max_cols > 1:
        if max_cols == 2:
            headers = ["Detalle_Producto", "Precio"]
        elif max_cols == 3:
            headers = ["Codigo", "Detalle_Producto", "Precio"]
        else:
            headers = [f"Columna_{i+1}" for i in range(max_cols)]
            
        if len(parsed_rows[0]) == max_cols and not any(re.search(r'\d', str(x)) for x in parsed_rows[0]):
            headers = parsed_rows[0]
            data_rows = parsed_rows[1:]
        else:
            data_rows = parsed_rows
            
        padded_rows = []
        for r in data_rows:
            padded = r + [''] * (max_cols - len(r))
            padded_rows.append(padded[:max_cols])
            
        return pd.DataFrame(padded_rows, columns=headers)
    else:
        return pd.DataFrame({'Texto': all_lines})
