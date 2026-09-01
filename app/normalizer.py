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
    'cachorros': 'cachorro', 'puppy': 'cachorro', 'puppies': 'cachorro', 'pupy': 'cachorro',
    'adultos': 'adulto', 'adult': 'adulto', 'ad': 'adulto', 'seniors': 'senior',
    'junior': 'junior', 'jr': 'junior',
    'medianos': 'mediano', 'medianas': 'mediano', 'medium': 'mediano', 'med': 'mediano',
    'pequenos': 'pequeno', 'pequenas': 'pequeno', 'small': 'pequeno', 'mini': 'pequeno', 'peq': 'pequeno',
    'chicas': 'pequeno', 'chicos': 'pequeno', 'chico': 'pequeno',
    'grandes': 'grande', 'maxi': 'grande', 'large': 'grande', 'gde': 'grande',
    'razas': 'raza', 'breed': 'raza', 'proplan': 'pro plan',
    'litros': 'l', 'litro': 'l', 'lts': 'l', 'lt': 'l',
    'kilos': 'kg', 'kilo': 'kg', 'gr': 'g', 'gramos': 'g', 'gramo': 'g', 'grs': 'g',
    'descremada': 'descremado', 'entera': 'entero',
    'sachet': 'sachet', 'tetra': 'tetra', 'brik': 'tetra', 'tetrabrik': 'tetra',
    'doypack': 'doypack', 'doy': 'doypack', 'lata': 'lata', 'latas': 'lata', 'botella': 'botella',
    'pouch': 'pouch', 'pouches': 'pouch',
    'hipoallergenic': 'hipoalergenico', 'hypoallergenic': 'hipoalergenico', 'hipoalergenico': 'hipoalergenico',
    'gastro': 'gastrointestinal', 'urinary': 'urinario', 'urinaria': 'urinario',
    'comp': 'comprimido', 'comprimidos': 'comprimido', 'pipetas': 'pipeta'
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
    
    # Unificar variantes compuestas de marcas comerciales frecuentes
    text = re.sub(r'\bnext\s*gard\b', 'nexgard', text)
    text = re.sub(r'\bnextgard\b', 'nexgard', text)
    text = re.sub(r'\b9\s*lives\b', '9lives', text)
    text = re.sub(r'\bnine\s*lives\b', '9lives', text)
    text = re.sub(r'\bcat\s*pro\b', 'catpro', text)
    text = re.sub(r'\bdog\s*pro\b', 'dogpro', text)
    text = re.sub(r'\bmichi\s*feliz\b', 'michifeliz', text)
    text = re.sub(r'\btotal\s*balance\b', 'totalbalance', text)
    text = re.sub(r'\bgran\s*campeon\b', 'grancampeon', text)
    text = re.sub(r'\bmaster\s*food\b', 'masterfood', text)
    text = re.sub(r'\bsaladillo\s*pets\b', 'saladillopets', text)
    text = re.sub(r'\bla\s*palmera\b', 'lapalmera', text)
    text = re.sub(r'\banimal\s*pet\b', 'animalpet', text)
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
    'royal b.ch': 'Royal Canin',
    'royal bch': 'Royal Canin',
    'royal club': 'Royal Canin',
    'royl': 'Royal Canin',
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
    'cat pro': 'Catpro',
    'dogpro': 'Dogpro',
    'dog pro': 'Dogpro',
    'eukanuba': 'Eukanuba',
    'eukanuba b.ch': 'Eukanuba',
    'eukanuba bch': 'Eukanuba',
    'pedigree': 'Pedigree',
    'pedigre': 'Pedigree',
    'whiskas': 'Whiskas',
    'excellent': 'Excellent',
    'excelent': 'Excellent',
    'excellent b.ch': 'Excellent',
    'excellent bch': 'Excellent',
    'simparica': 'Simparica',
    'nexgard': 'Nexgard',
    'nextgard': 'Nexgard',
    'next gard': 'Nexgard',
    'next': 'Nexgard',
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
    '9 lives': '9 Lives',
    '9lives': '9 Lives',
    'nine lives': '9 Lives',
    'gati': 'Gati',
    'fawna': 'Fawna',
    'mon ami': 'Mon Ami',
    'infinity': 'Infinity',
    'infity': 'Infinity',
    'hop!': 'Hop!',
    'hop': 'Hop!',
    'catlike': 'Catlike',
    'canactive': 'Canactive',
    'advance': 'Advance',
    'bonzo': 'Bonzo',
    'bonello': 'Bonello',
    'gandum': 'Gandum',
    'michi feliz': 'Michi Feliz',
    'michi': 'Michi Feliz',
    'minino': 'Minino',
    'belcan': 'Belcan',
    'loyal cat': 'Loyal Cat',
    'loyal': 'Loyal Cat',
    'protemix': 'Protemix',
    'gran campeon': 'Gran Campeon',
    'master food': 'Master Food',
    'master': 'Master Food',
    'metrive': 'Metrive',
    'saladillo pets': 'Saladillo Pets',
    'saladillo': 'Saladillo Pets',
    'vitalcrops': 'Vitalcrops',
    'la palmera': 'La Palmera (Forrajería)',
    'palmera': 'La Palmera (Forrajería)',
    'bb iniciador': 'La Palmera (Forrajería)',
    'engorde': 'La Palmera (Forrajería)',
    'ponedora': 'La Palmera (Forrajería)',
    'animal pet': 'Animal Pet',
    'virupack': 'Virupack',
    'viruta': 'Heno y Virutas',
    'virutas': 'Heno y Virutas',
    'heno': 'Heno y Virutas',
    'alfalfa': 'Heno y Virutas',
    'kil': 'Kil (Antiparasitarios)',
    'iams': 'Iams',
    'rodeo': 'Rodeo',
    'total balance': 'Total Balance',
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

def detect_brand_and_category(descripcion: str, explicit_marca: str = "") -> str:
    """Detecta con máxima precisión la marca comercial o clasifica en categoría funcional."""
    if explicit_marca and len(explicit_marca.strip()) > 2 and explicit_marca.lower() not in ('sin marca', 'general', 'otros'):
        clean_m = remove_accents_and_clean(explicit_marca)
        if clean_m in BRAND_CANONICAL_MAP:
            return BRAND_CANONICAL_MAP[clean_m]
        return explicit_marca.strip().title()
        
    desc_lwr = descripcion.lower()
    
    # 1. Chequear marcas comerciales directas en el texto
    for brand_key, canonical_name in BRAND_CANONICAL_MAP.items():
        if re.search(r'\b' + re.escape(brand_key) + r'\b', desc_lwr):
            return canonical_name
            
    # 2. Categorías funcionales de Pet Shop
    if re.search(r'\b(comedero|bebedero|botella|plato|tolva|comelento)\b', desc_lwr):
        return "Accesorios y Comederos"
    if re.search(r'\b(collar|correa|pechera|pretal|bozal|bolso|mochila|transportadora)\b', desc_lwr):
        return "Paseo y Transporte"
    if re.search(r'\b(juguete|pelota|pelotas|chifle|chiche|soga|rascador)\b', desc_lwr):
        return "Juguetes y Rascadores"
    if re.search(r'\b(bandeja|litera|palita|sanitaria|arena|piedra|piedras|silica|silicas)\b', desc_lwr):
        return "Piedras y Bandejas Sanitarias"
    if re.search(r'\b(shampoo|enjuague|jabon|talco|perfume|colonia|limpia patas|quita pelusa|cepillo|peine|cortaunas|repuesto bolsa|bolsa basura|hueso\+\s*bolsa|seda)\b', desc_lwr):
        return "Higiene y Cosmética"
    if re.search(r'\b(snack|snacks|bocadito|bocaditos|dentastix|biscrok|hueso|huesos|huesito|huesitos|oreja|orejas|grisines|palito|palitos|glicines|biscuit)\b', desc_lwr):
        return "Snacks y Golosinas"
    if re.search(r'\b(curabichera|pulguicida|garrapaticida|pipeta|spray|locion|crema|sh2006|sh2007|sh1069|sh1061|shampoo para mascotas)\b', desc_lwr):
        return "Farmacia y Veterinaria"
    if re.search(r'\b(alfalfa|heno|viruta|virutas|virupack)\b', desc_lwr):
        return "Heno y Virutas"
    if re.search(r'\b(bb\s*iniciador|engorde|ponedora|pollito|gallina|la\s*palmera)\b', desc_lwr):
        return "La Palmera (Forrajería)"
        
    words = [w for w in re.findall(r'[A-Za-z0-9]+', descripcion) if len(w) > 2 and w.lower() not in STOP_WORDS]
    if words:
        w0 = words[0].lower()
        if w0 in BRAND_CANONICAL_MAP:
            return BRAND_CANONICAL_MAP[w0]
        if words[0].isalpha() and len(words[0]) >= 4:
            return words[0].title()
            
    return "Artículos Generales"

def normalize_product_record(row_dict: Dict[str, Any], list_index: int, row_number: int) -> Dict[str, Any]:
    codigo = str(row_dict.get('codigo', '') or '').strip()
    codigo_barras = str(row_dict.get('codigo_barras', '') or '').strip()
    sku = str(row_dict.get('sku', '') or '').strip()
    descripcion = str(row_dict.get('descripcion', '') or '').strip()
    explicit_marca = str(row_dict.get('marca', '') or '').strip()
    presentacion = str(row_dict.get('presentacion', '') or '').strip()
    unidad = str(row_dict.get('unidad', '') or '').strip()
    
    # Detección inteligente de Marca y Categoría
    marca = detect_brand_and_category(descripcion, explicit_marca)
    
    precio = parse_price(row_dict.get('precio', ''))
    precio_final = parse_price(row_dict.get('precio_final', ''))
    iva = parse_price(row_dict.get('iva', ''))
    descuento = parse_price(row_dict.get('descuento', ''))
    cantidad = parse_quantity(row_dict.get('cantidad', ''))
    
    # Extraer medida de descripcion y presentacion combinadas
    full_desc = f"{descripcion} {presentacion} {unidad}".strip()
    unit_type, unit_value, cleaned_desc = extract_standard_measure(full_desc)
    
    # Detectar formato comercial
    desc_lwr = descripcion.lower()
    is_pouch = bool(re.search(r'\b(pouch|pouches|sobre|sobres)\b', desc_lwr))
    is_lata = bool(re.search(r'\b(lata|latas|can\b|mousse|pat[eé]|trocitos|souffle|filetes)\b', desc_lwr))
    is_snack = bool(re.search(r'\b(snack|snacks|bocadito|bocaditos|dentastix|biscrok|hueso|huesos|huesito|huesitos|oreja|orejas|palito|palitos|glicines|biscuit)\b', desc_lwr))
    is_pipeta = bool(re.search(r'\b(pipeta|pipetas|spot\s*on)\b', desc_lwr))
    is_talquera = bool(re.search(r'\b(talquera|talco)\b', desc_lwr))
    is_piedra = bool(re.search(r'\b(piedra|piedras|arena|pellet|sanitaria|sanitario|bentonita|absorvente)\b', desc_lwr))
    is_shampoo = bool(re.search(r'\b(shampoo|enjuague|perfume)\b', desc_lwr))
    is_accesorio = bool(re.search(r'\b(comedero|bandeja|palita|peine|collar|pechera|correa|juguete|cepillo|bebedero|litera|bolso|cortauñas|cortaunas)\b', desc_lwr))

    # Generar tokens limpios
    cleaned_text = remove_accents_and_clean(cleaned_desc)
    raw_tokens = [t for t in cleaned_text.split() if t not in STOP_WORDS and len(t) > 1]
    canonical_tokens = [SYNONYM_REPLACEMENTS.get(t, t) for t in raw_tokens]
    flat_tokens = []
    for ct in canonical_tokens:
        for sub_t in ct.split():
            if sub_t not in STOP_WORDS and len(sub_t) > 1:
                flat_tokens.append(sub_t)
                
    tokens = flat_tokens
    tokens_sorted = " ".join(sorted(set(tokens)))
    measure_key = f"{int(unit_value)}{unit_type}" if unit_type and unit_value else ""
    
    clean_barcode = re.sub(r'[^0-9A-Za-z]', '', codigo_barras)
    clean_code = re.sub(r'[^0-9A-Za-z]', '', codigo)
    clean_sku = re.sub(r'[^0-9A-Za-z]', '', sku)
    
    if not clean_barcode:
        if clean_code.isdigit() and 8 <= len(clean_code) <= 14:
            clean_barcode = clean_code
        elif clean_sku.isdigit() and 8 <= len(clean_sku) <= 14:
            clean_barcode = clean_sku
            
    if not clean_code and clean_barcode:
        clean_code = clean_barcode
    
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
        "is_pouch": is_pouch,
        "is_lata": is_lata,
        "is_snack": is_snack,
        "is_pipeta": is_pipeta,
        "is_talquera": is_talquera,
        "is_piedra": is_piedra,
        "is_shampoo": is_shampoo,
        "is_accesorio": is_accesorio,
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
