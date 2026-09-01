import re
import unicodedata
from typing import Dict, Any, Tuple, Optional

# Mapeos y patrones de unidades
RE_VOLUME = re.compile(
    r'(?P<val>\d+(?:[\.,]\d+)?)\s*(?P<unit>l(?:itro(?:s)?)?|lts?|ml|c\.?c\.?|cm3|cl)\b', 
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
    'promo', 'oferta', 'nuevo', 'super', 'pack', 'x'
}

# Diccionario de equivalencias y lematización para el mercado argentino y mascotas
SYNONYM_REPLACEMENTS = {
    'gatos': 'gato', 'gatitos': 'gatito', 'kitten': 'gatito', 'kittens': 'gatito',
    'perros': 'perro', 'dog': 'perro', 'dogs': 'perro', 'cat': 'gato', 'cats': 'gato',
    'cachorros': 'cachorro', 'puppy': 'cachorro', 'puppies': 'cachorro',
    'adultos': 'adulto', 'adult': 'adulto', 'seniors': 'senior',
    'medianos': 'mediano', 'medianas': 'mediano', 'medium': 'mediano', 'med': 'mediano',
    'pequenos': 'pequeno', 'pequenas': 'pequeno', 'small': 'pequeno', 'mini': 'pequeno', 'peq': 'pequeno',
    'grandes': 'grande', 'maxi': 'grande', 'large': 'grande', 'gde': 'grande',
    'razas': 'raza', 'breed': 'raza', 'proplan': 'pro plan',
    'litros': 'l', 'litro': 'l', 'lts': 'l', 'lt': 'l',
    'kilos': 'kg', 'kilo': 'kg', 'gr': 'g', 'gramos': 'g', 'gramo': 'g',
    'descremada': 'descremado', 'entera': 'entero',
    'sachet': 'sachet', 'tetra': 'tetra', 'brik': 'tetra', 'tetrabrik': 'tetra',
    'doypack': 'doypack', 'doy': 'doypack', 'lata': 'lata', 'botella': 'botella'
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

KNOWN_BRANDS = [
    # Mascotas
    "Royal Canin", "Purina Pro Plan", "Pro Plan", "Purina Dog Chow", "Dog Chow",
    "Purina Cat Chow", "Cat Chow", "Pedigree", "Whiskas", "Eukanuba", "Excellent",
    "Sieger", "Vitalcan", "Old Prince", "Nutribon", "Fawna", "Gati", "Raza",
    "Infinity", "Voraz", "Mon Ami", "Sabrositos",
    # Lácteos y Bebidas
    "La Serenísima", "La Serenisima", "Sancor", "Ilolay", "Tregar", "Milkaut", "Verónica",
    "Coca-Cola", "Coca Cola", "Sprite", "Fanta", "Pepsi", "Seven Up", "7Up", "Quilmes",
    "Stella Artois", "Heineken", "Brahma", "Corona", "Villavicencio", "Villa del Sur",
    "Levité", "Levite", "Cepita", "Baggio",
    # Almacén
    "Matarazzo", "Lucchetti", "Gallo", "Natura", "Cocinero", "Hellmanns", "Hellmann's",
    "Marolio", "Arcor", "Terrabusi", "Bagley", "San Ignacio", "Molto", "Knorr",
    "La Campagnola", "Canale", "Noel", "Pureza", "Cañuelas", "Favorita",
    # Perfumería y Limpieza
    "Head & Shoulders", "Pantene", "Sedal", "Dove", "Rexona", "Colgate", "Oral-B",
    "Ariel", "Ala", "Skip", "Drive", "Ayudín", "Ayudin", "Magistral", "Cif", "Vivere",
    "Comfort", "Poett", "Glade", "Huggies", "Pampers"
]

BRAND_CANONICAL_MAP = {
    'proplan': 'Purina Pro Plan',
    'pro plan': 'Purina Pro Plan',
    'purina pro plan': 'Purina Pro Plan',
    'dogchow': 'Purina Dog Chow',
    'dog chow': 'Purina Dog Chow',
    'purina dog chow': 'Purina Dog Chow',
    'catchow': 'Purina Cat Chow',
    'cat chow': 'Purina Cat Chow',
    'purina cat chow': 'Purina Cat Chow',
    'royal': 'Royal Canin',
    'royal canin': 'Royal Canin',
    'vital can': 'Vital Can',
    'vitalcan': 'Vital Can',
    'maintenance': 'Maintenance Criadores',
    'maintenance criadores': 'Maintenance Criadores',
    'mantenance': 'Maintenance Criadores',
    'mantenance criadores': 'Maintenance Criadores',
    'old prince': 'Old Prince',
    'kongo': 'Kongo',
    'biopet': 'Biopet',
    'catpro': 'Catpro',
    'dogpro': 'Dogpro',
    'eukanuba': 'Eukanuba',
    'pedigree': 'Pedigree',
    'whiskas': 'Whiskas',
    'excellent': 'Excellent',
    'simparica': 'Simparica',
    'nexgard': 'Nexgard',
    'nextgard': 'Nexgard',
    'bravecto': 'Bravecto',
    'ospret': 'Ospret',
    'osprett': 'Ospret',
    'tiernitos': 'Tiernitos',
    'sabrositos': 'Sabrositos',
    'vagoneta': 'Vagoneta',
    'voraz': 'Voraz',
    'matute': 'Matute',
    'nutribon': 'Nutribon',
    'raza': 'Raza',
    'provet': 'Provet',
    'agility': 'Agility',
    'sieger': 'Sieger',
    'frontline': 'Frontline',
    'coca cola': 'Coca-Cola',
    'coca-cola': 'Coca-Cola',
    'la serenisima': 'La Serenísima',
    'serenisima': 'La Serenísima',
    'la campagnola': 'La Campagnola',
    'campagnola': 'La Campagnola',
    'san ignacio': 'San Ignacio',
    'head and shoulders': 'Head & Shoulders',
    'head & shoulders': 'Head & Shoulders',
    'h&s': 'Head & Shoulders'
}

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
    
    # Inferir marca en cualquier posición del texto
    if not marca and descripcion:
        desc_clean = f" {remove_accents_and_clean(descripcion)} "
        for kb in KNOWN_BRANDS:
            kb_clean = f" {remove_accents_and_clean(kb)} "
            if kb_clean in desc_clean:
                marca = kb
                break
                
        if not marca:
            words = [w for w in descripcion.split() if len(w) > 2]
            if words:
                if len(words) >= 2 and words[0].lower() in ('royal', 'la', 'los', 'las', 'san', 'pro', 'dog', 'cat', 'coca', 'dr', 'head'):
                    marca = f"{words[0]} {words[1]}".title()
                else:
                    marca = words[0].title()

    clean_marca_key = remove_accents_and_clean(marca)
    if clean_marca_key in BRAND_CANONICAL_MAP:
        marca = BRAND_CANONICAL_MAP[clean_marca_key]
    
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
    
    # Generar tokens limpios y lematizados de la descripción
    cleaned_text = remove_accents_and_clean(cleaned_desc)
    raw_tokens = [t for t in cleaned_text.split() if t not in STOP_WORDS and len(t) > 1]
    canonical_tokens = [SYNONYM_REPLACEMENTS.get(t, t) for t in raw_tokens]
    # Si algún reemplazo trajo 2 palabras (ej: 'proplan' -> 'pro plan')
    flat_tokens = []
    for ct in canonical_tokens:
        for sub_t in ct.split():
            if sub_t not in STOP_WORDS and len(sub_t) > 1:
                flat_tokens.append(sub_t)
                
    tokens = flat_tokens
    tokens_sorted = " ".join(sorted(set(tokens)))
    
    # Clave de medida estandarizada (ej: '2250ml', '1000g', '6u' o vacía)
    measure_key = f"{int(unit_value)}{unit_type}" if unit_type and unit_value else ""
    
    # Normalizar códigos de barra numéricos (remover guiones y espacios)
    clean_barcode = re.sub(r'[^0-9A-Za-z]', '', codigo_barras)
    clean_code = re.sub(r'[^0-9A-Za-z]', '', codigo)
    clean_sku = re.sub(r'[^0-9A-Za-z]', '', sku)
    
    # Si no vino código de barras explícito, pero el código o SKU es un EAN estándar (8 a 14 dígitos)
    if not clean_barcode:
        if clean_code.isdigit() and 8 <= len(clean_code) <= 14:
            clean_barcode = clean_code
        elif clean_sku.isdigit() and 8 <= len(clean_sku) <= 14:
            clean_barcode = clean_sku
            
    if not clean_code and clean_barcode:
        clean_code = clean_barcode
    
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
