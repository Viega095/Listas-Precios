import os
import random
import pandas as pd

def generate_test_datasets():
    os.makedirs("datos_prueba", exist_ok=True)
    print("Generando catálogos de prueba realistas y comparables...")

    # Categorías y productos base con precios de referencia realistas
    articulos_base = [
        ("Gaseosa Cola", ["2,25 l", "2250 ml", "2.25L", "1,5 l", "500 ml", "354 ml"], "Coca-Cola", 2800.0, "Bebidas"),
        ("Gaseosa Lima Limon", ["2,25 l", "2250 ml", "1,5 l", "500 ml"], "Sprite", 2700.0, "Bebidas"),
        ("Cerveza Rubia", ["1 l", "1000 cc", "473 ml", "710 ml", "Pack x6"], "Quilmes", 2200.0, "Bebidas"),
        ("Leche Entera", ["1 l", "1000 ml", "Sachet 1L", "Tetra 1L"], "La Serenísima", 1400.0, "Lácteos"),
        ("Leche Descremada", ["1 l", "1000 ml", "Tetra 1L"], "Sancor", 1350.0, "Lácteos"),
        ("Yogur Bebible Frutilla", ["1 kg", "1000 g", "1000 gr", "180 g"], "La Serenísima", 2100.0, "Lácteos"),
        ("Dulce de Leche Clasico", ["400 g", "400 gr", "1 kg", "1000 g"], "San Ignacio", 2500.0, "Lácteos"),
        ("Aceite Girasol", ["900 ml", "1,5 l", "1500 ml", "3 l"], "Natura", 2400.0, "Almacén"),
        ("Aceite Mezcla", ["900 ml", "1,5 l", "1500 ml"], "Cocinero", 1900.0, "Almacén"),
        ("Arroz Largo Fino", ["1 kg", "1000 g", "1000 gr", "500 g"], "Gallo", 1800.0, "Almacén"),
        ("Fideos Guiseros", ["500 g", "500 gr", "1 kg"], "Matarazzo", 1300.0, "Almacén"),
        ("Fideos Tallarines", ["500 g", "500 gr"], "Lucchetti", 1250.0, "Almacén"),
        ("Pure de Tomate", ["520 g", "520 gr", "Tetra 520g"], "Marolio", 850.0, "Almacén"),
        ("Mayonesa Clasica", ["475 g", "500 g", "950 g", "1 kg"], "Hellmanns", 2600.0, "Almacén"),
        ("Galletitas Dulces", ["120 g", "160 g", "Pack x3", "300 g"], "Arcor", 1100.0, "Galletitas"),
        ("Galletitas de Agua", ["100 g", "300 g", "Pack x3 300g"], "Terrabusi", 950.0, "Galletitas"),
        ("Shampoo Anticaspa", ["400 ml", "200 ml", "750 ml"], "Head & Shoulders", 4500.0, "Perfumería"),
        ("Acondicionador Brillo", ["400 ml", "200 ml"], "Pantene", 4300.0, "Perfumería"),
        ("Desodorante Aerosol", ["150 ml", "150 cc", "Pack x2"], "Rexona", 2800.0, "Perfumería"),
        ("Crema Dental Triple Accion", ["70 g", "90 g", "140 g"], "Colgate", 1900.0, "Perfumería")
    ]

    total_pool = []
    ean_base = 779100000000
    
    # Generar 4.000 productos con precios realistas y coherentes
    for i in range(4000):
        art_nombre, pres_list, default_brand, base_price, cat = articulos_base[i % len(articulos_base)]
        pres = pres_list[(i // len(articulos_base)) % len(pres_list)]
        
        # Ajustar precio base según la presentación (ej: 2.25L vs 500ml)
        mult = 1.0
        if "2,25" in pres or "2250" in pres or "2.25" in pres: mult = 1.8
        elif "1,5" in pres or "1500" in pres: mult = 1.3
        elif "500" in pres or "473" in pres: mult = 0.6
        elif "354" in pres or "200" in pres: mult = 0.45
        elif "Pack x6" in pres: mult = 5.2
        elif "Pack x3" in pres or "Pack x2" in pres: mult = 2.7
        elif "1 kg" in pres or "1000" in pres or "1 l" in pres: mult = 1.0
        elif "900" in pres or "950" in pres: mult = 0.9
        
        p_ref = round(base_price * mult, 2)
        ean = str(ean_base + i + 1)
        sku = f"SKU-{10000 + i}"
        cod_interno = f"ART{i+1:05d}"
        
        total_pool.append({
            "id": i,
            "ean": ean,
            "sku": sku,
            "cod_interno": cod_interno,
            "nombre": art_nombre,
            "marca": default_brand,
            "pres": pres,
            "precio_base": p_ref,
            "categoria": cat
        })

    print(f"Total productos en el catálogo universo: {len(total_pool)}")

    # -------------------------------------------------------------
    # Lista 1: Proveedor 1 - Distribuidora Norte (Excel XLSX - 3.500 productos)
    # -------------------------------------------------------------
    rows_l1 = []
    subset_1 = total_pool[:3500]
    for p in subset_1:
        desc_var = f"{p['nombre']} {p['marca']} {p['pres']}"
        precio_prov1 = round(p['precio_base'] * random.uniform(0.95, 1.12), 2)
        rows_l1.append({
            "COD_ART": p['cod_interno'],
            "EAN13": p['ean'],
            "DETALLE_PRODUCTO": desc_var,
            "MARCA": p['marca'],
            "PRESENTACION": p['pres'],
            "PRECIO_NETO": precio_prov1,
            "ALICUOTA_IVA": 21.0
        })

    df1 = pd.DataFrame(rows_l1)
    file_l1 = "datos_prueba/Proveedor_1_Distribuidora_Norte.xlsx"
    df1.to_excel(file_l1, index=False)
    print(f"Guardado {file_l1} con {len(df1)} filas.")

    # -------------------------------------------------------------
    # Lista 2: Proveedor 2 - Mayorista Central (CSV ';' - 3.300 productos)
    # -------------------------------------------------------------
    rows_l2 = []
    subset_2 = total_pool[300:3600] # Cruza fuertemente con Lista 1 (300 a 3500) y tiene exclusivos
    for p in subset_2:
        pres_alt = p['pres']
        if "2,25 l" in pres_alt: pres_alt = "2250 ml"
        elif "1,5 l" in pres_alt: pres_alt = "1500 ml"
        elif "1 kg" in pres_alt: pres_alt = "1000 gr"
        elif "1 l" in pres_alt: pres_alt = "1000 cc"

        desc_var = f"{p['marca']} {p['nombre']} {pres_alt}".upper()
        precio_prov2 = round(p['precio_base'] * random.uniform(0.90, 1.15), 2)
        
        rows_l2.append({
            "Codigo_Barras": p['ean'],
            "SKU_Interno": p['sku'],
            "Descripcion": desc_var,
            "Fabricante": p['marca'],
            "Contenido": pres_alt,
            "Precio_Lista": precio_prov2,
            "Descuento_Porc": random.choice([0.0, 5.0, 10.0])
        })

    df2 = pd.DataFrame(rows_l2)
    file_l2 = "datos_prueba/Proveedor_2_Mayorista_Central.csv"
    df2.to_csv(file_l2, sep=';', index=False, encoding='utf-8-sig')
    print(f"Guardado {file_l2} con {len(df2)} filas.")

    # -------------------------------------------------------------
    # Lista 3: Proveedor 3 - Supercenter Nacional (Excel XLSX - 3.200 productos)
    # -------------------------------------------------------------
    rows_l3 = []
    subset_3 = total_pool[600:3800] # Cruza con Lista 1 y Lista 2 y tiene exclusivos
    for p in subset_3:
        desc_var = f"{p['nombre']} {p['pres']} - {p['marca']}"
        precio_prov3 = round(p['precio_base'] * random.uniform(0.92, 1.18), 2)
        
        rows_l3.append({
            "ID_ARTICULO": f"SUP-{p['id']}",
            "CODIGO_BARRA": p['ean'],
            "PRODUCTO": desc_var,
            "MARCA": p['marca'],
            "UNIDAD_MEDIDA": "UN",
            "PRECIO_FINAL_IVA_INC": precio_prov3
        })

    df3 = pd.DataFrame(rows_l3)
    file_l3 = "datos_prueba/Proveedor_3_Supercenter_Nacional.xlsx"
    df3.to_excel(file_l3, index=False)
    print(f"Guardado {file_l3} con {len(df3)} filas.")

    print("\n¡Catálogos de prueba regenerados con total realismo y coherencia!")

if __name__ == "__main__":
    generate_test_datasets()
