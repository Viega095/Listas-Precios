import re
import unicodedata
from typing import Dict, Any, Tuple, Optional

# Mapeos y patrones de unidades
RE_VOLUME = re.compile(
    r'(?P<val>\d+(?:[\.,]\d+)?)\s*(?P<unit>l(?:itro(?:s)?)?|ml|c\.?c\.?|cm3|cl)\b', 
    re.IGNORECASE
)
RE_WEIGHT = re.compile(
    r'(?P<val>\d+(?:[\.,]\d+)?)\s*(?P<unit>k(?:g|ilo(?:s)?)?|g(?:r|ramo(?:s)?)?|mg)\b', 
    re.IGNORECASE
)
RE_PACK = re.compile(
    r'(?:pack\s*x?|caja\s*x?|display\s*x?|x\s*|bulto\s*x?)\s*(?P<val>\d+)\s*(?:un(?:id(?:ades)?)?|u)?\b', 
    re.IGNORECASE
)

# Palabras vacías o de relleno que no aportan distinción
STOP_WORDS = {
    'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'e', 'o', 'u',
    'con', 'sin', 'para', 'en', 'por', 'a', 'al', 'original', 'clasica', 'clasico', 'premium',
    'promo', 'oferta', 'nuevo', 'super', 'pack'
}

def remove_accents_and_clean(text: str) -> str:
    """Remueve acentos, caracteres especiales y convierte a minúsculas."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    text = text.lower().strip()
    # Normalizar acentos
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    # Reemplazar caracteres no alfanuméricos por espacios
    text = re.sub(r'[^a-z0-9\.,]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_price(value: Any) -> float:
    """Convierte cualquier representación de precio a float positivo."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else 0.0
        
    s = str(value).strip()
    # Remover símbolos de moneda y espacios
    s = re.sub(r'[\$\s€£A-Za-z]', '', s)
    if not s:
        return 0.0
        
    # Manejar formatos como 1.234,56 o 1,234.56 o 1234,56 o 1234.56
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # 1.234,56 -> 1234.56
            s = s.replace('.', '').replace(',', '.')
        else:
            # 1,234.56 -> 1234.56
            s = s.replace(',', '')
    elif ',' in s:
        # 1234,56 -> 1234.56
        s = s.replace(',', '.')
        
    try:
        val = float(s)
        return val if val >= 0 else 0.0
    except ValueError:
        return 0.0

def parse_quantity(value: Any) -> float:
    """Convierte cantidad a float positivo, mínimo 1.0."""
    if value is None or str(value).strip() == '':
        return 1.0
    try:
        val = float(str(value).replace(',', '.').strip())
        return val if val > 0 else 1.0
    except (ValueError, TypeError):
        return 1.0

def extract_standard_measure(text: str) -> Tuple[Optional[str], Optional[float], str]:
    """
    Extrae la medida estandarizada (volumen en ml, peso en gramos, pack en unidades).
    Retorna (tipo_unidad, valor_normalizado, texto_sin_medida).
    Ejemplos:
    - "Coca Cola 2,25 l" -> ("ml", 2250.0, "Coca Cola")
    - "Coca-Cola 2250 ml" -> ("ml", 2250.0, "Coca-Cola")
    - "Azucar 1 kg" -> ("g", 1000.0, "Azucar")
    - "Galletitas 250 gr" -> ("g", 250.0, "Galletitas")
    """
    clean_t = text
    
    # 1. Chequear Volumen
    match_vol = RE_VOLUME.search(clean_t)
    if match_vol:
        val_str = match_vol.group('val').replace(',', '.')
        unit_str = match_vol.group('unit').lower()
        try:
            num = float(val_str)
            if unit_str.startswith('l'):
                norm_val = round(num * 1000, 2)  # Convertir litros a ml
            elif unit_str in ('cl',):
                norm_val = round(num * 10, 2)
            else:
                norm_val = round(num, 2) # ml, cc, cm3
                
            remainder = clean_t[:match_vol.start()] + " " + clean_t[match_vol.end():]
            return "ml", norm_val, re.sub(r'\s+', ' ', remainder).strip()
        except ValueError:
            pass

    # 2. Chequear Peso
    match_w = RE_WEIGHT.search(clean_t)
    if match_w:
        val_str = match_w.group('val').replace(',', '.')
        unit_str = match_w.group('unit').lower()
        try:
            num = float(val_str)
            if unit_str.startswith('k'):
                norm_val = round(num * 1000, 2)  # Convertir kg a gramos
            elif unit_str == 'mg':
                norm_val = round(num / 1000, 4)
            else:
                norm_val = round(num, 2) # gramos
                
            remainder = clean_t[:match_w.start()] + " " + clean_t[match_w.end():]
            return "g", norm_val, re.sub(r'\s+', ' ', remainder).strip()
        except ValueError:
            pass
            
    # 3. Chequear Pack / Unidades
    match_pack = RE_PACK.search(clean_t)
    if match_pack:
        val_str = match_pack.group('val')
        try:
            norm_val = float(val_str)
            remainder = clean_t[:match_pack.start()] + " " + clean_t[match_pack.end():]
            return "u", norm_val, re.sub(r'\s+', ' ', remainder).strip()
        except ValueError:
            pass

    return None, None, clean_t

def normalize_product_record(row_dict: Dict[str, Any], list_index: int, row_number: int) -> Dict[str, Any]:
    """
    Normaliza una fila completa de producto para permitir indexación y comparación precisa.
    """
    codigo = str(row_dict.get('codigo', '') or '').strip()
    codigo_barras = str(row_dict.get('codigo_barras', '') or '').strip()
    sku = str(row_dict.get('sku', '') or '').strip()
    descripcion = str(row_dict.get('descripcion', '') or '').strip()
    marca = str(row_dict.get('marca', '') or '').strip()
    presentacion = str(row_dict.get('presentacion', '') or '').strip()
    unidad = str(row_dict.get('unidad', '') or '').strip()
    
    # Inferir marca si viene vacía a partir del nombre del producto
    if not marca and descripcion:
        words = [w for w in descripcion.split() if len(w) > 2]
        if words:
            if len(words) >= 2 and words[0].lower() in ('royal', 'la', 'los', 'las', 'san', 'pro', 'dog', 'cat', 'coca', 'dr', 'head'):
                marca = f"{words[0]} {words[1]}".title()
            else:
                marca = words[0].title()
    
    # Precios y cantidades
    precio_raw = row_dict.get('precio', '')
    precio_final_raw = row_dict.get('precio_final', '')
    iva_raw = row_dict.get('iva', '')
    descuento_raw = row_dict.get('descuento', '')
    cantidad_raw = row_dict.get('cantidad', '')
    
    precio = parse_price(precio_raw)
    precio_final = parse_price(precio_final_raw)
    iva = parse_price(iva_raw)
    descuento = parse_price(descuento_raw)
    cantidad = parse_quantity(cantidad_raw)
    
    # Extraer medida de descripcion y presentacion combinadas
    full_desc = f"{descripcion} {presentacion} {unidad}".strip()
    unit_type, unit_value, cleaned_desc = extract_standard_measure(full_desc)
    
    # Generar tokens limpios de la descripción
    cleaned_text = remove_accents_and_clean(cleaned_desc)
    tokens = [t for t in cleaned_text.split() if t not in STOP_WORDS and len(t) > 1]
    tokens_sorted = " ".join(sorted(tokens))
    
    # Clave de medida estandarizada (ej: '2250ml', '1000g', '6u' o vacía)
    measure_key = f"{int(unit_value)}{unit_type}" if unit_type and unit_value else ""
    
    # Normalizar códigos de barra numéricos (remover guiones y espacios)
    clean_barcode = re.sub(r'[^0-9A-Za-z]', '', codigo_barras)
    clean_code = re.sub(r'[^0-9A-Za-z]', '', codigo)
    clean_sku = re.sub(r'[^0-9A-Za-z]', '', sku)
    
    # Marca normalizada
    clean_brand = remove_accents_and_clean(marca)

    return {
        "id": f"L{list_index}_R{row_number}",
        "list_index": list_index,
        "row_number": row_number,
        "codigo_orig": codigo,
        "codigo_barras_orig": codigo_barras,
        "sku_orig": sku,
        "descripcion_orig": descripcion,
        "marca_orig": marca,
        "presentacion_orig": presentacion,
        "unidad_orig": unidad,
        "precio_orig": precio,
        "precio_final_orig": precio_final,
        "iva_orig": iva,
        "descuento_orig": descuento,
        "cantidad_orig": cantidad,
        
        # Atributos normalizados para matching
        "clean_barcode": clean_barcode,
        "clean_code": clean_code,
        "clean_sku": clean_sku,
        "clean_brand": clean_brand,
        "measure_key": measure_key,
        "unit_type": unit_type,
        "unit_value": unit_value,
        "tokens": tokens,
        "tokens_sorted": tokens_sorted,
        "normalized_title": f"{' '.join(tokens)} {measure_key}".strip()
    }
