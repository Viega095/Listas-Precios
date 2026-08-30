import time
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parser import parse_file_to_dataframe, detect_column_mapping
from app.normalizer import normalize_product_record
from app.matcher import ProductMatcher
from app.calculator import PriceCalculator
from app.exporter import ResultExporter

def test_large_scale_comparison():
    print("=== INICIANDO PRUEBA DE ESTRÉS DE COMPARACIÓN CON LISTAS MASIVAS ===")
    
    files_to_load = [
        (0, "datos_prueba/Proveedor_1_Distribuidora_Norte.xlsx", "Proveedor 1 Norte"),
        (1, "datos_prueba/Proveedor_2_Mayorista_Central.csv", "Proveedor 2 Central"),
        (2, "datos_prueba/Proveedor_3_Supercenter_Nacional.xlsx", "Proveedor 3 Supercenter")
    ]
    
    t0 = time.time()
    normalized_lists = []
    total_raw_rows = 0
    configs = []
    
    for idx, path, name in files_to_load:
        with open(path, "rb") as f:
            content = f.read()
        df, cols, warnings = parse_file_to_dataframe(content, os.path.basename(path))
        mapping = detect_column_mapping(cols)
        total_raw_rows += len(df)
        print(f"Lista {idx+1} ({name}): {len(df)} filas leídas y {len(cols)} columnas detectadas.")
        
        p_list = []
        for row_num, (_, row) in enumerate(df.iterrows(), 1):
            row_dict = {std_field: (row[orig_col] if orig_col and orig_col in row else None) for std_field, orig_col in mapping.items()}
            p_list.append(normalize_product_record(row_dict, idx, row_num))
            
        normalized_lists.append(p_list)
        configs.append({
            "nombre": name,
            "iva_incluido": True,
            "iva_percent": 21.0,
            "descuento_percent": 0.0,
            "recargo_percent": 0.0,
            "bonificacion_percent": 0.0,
            "modo_precio": "unitario",
            "unidades_por_bulto": 1.0
        })

    t_parse = time.time()
    print(f"\n[OK] Lectura y normalización de {total_raw_rows} productos completada en {t_parse - t0:.2f} segundos.")
    
    # 2. Matching
    print("Ejecutando matching y agrupamiento multi-lista...")
    matcher = ProductMatcher(normalized_lists)
    groups, match_stats = matcher.match_all()
    t_match = time.time()
    print(f"[OK] Matching completado en {t_match - t_parse:.2f} segundos.")
    print(f"  - Grupos consolidados: {len(groups)}")
    print(f"  - Presentes en las 3 listas: {match_stats['en_3_listas']}")
    print(f"  - Presentes en 2 listas: {match_stats['en_2_listas']}")
    print(f"  - Exclusivos: {match_stats['total_exclusivos']}")
    print(f"  - Dudosos: {match_stats['dudosos']}")
    
    # Verificación estricta de 100% de datos
    total_grouped_items = sum(len([it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]) for g in groups)
    assert total_raw_rows == total_grouped_items, f"ERROR: Filas perdidas. Entrada: {total_raw_rows}, Agrupados: {total_grouped_items}"
    print(f"  --> VERIFICACIÓN DE INTEGRIDAD EXITOSA: 100% de los {total_raw_rows} productos están presentes.")

    # 3. Cálculo de Precios y Totales
    print("\nCalculando comparativas de precios, canasta óptima y métricas de ahorro...")
    calc = PriceCalculator(configs)
    comparison_data = calc.calculate_all(groups)
    t_calc = time.time()
    print(f"[OK] Cálculos finalizados en {t_calc - t_match:.2f} segundos.")
    
    totals = comparison_data["totals"]
    print("\n--- RESULTADOS FINANCIEROS GLOBALES ---")
    print(f"Total compra canasta óptima (todos los productos al más barato): ${totals['total_compra_optima']:,.2f}")
    print(f"Total óptimo productos comparables: ${totals['total_optimo_comparables']:,.2f}")
    for idx, cfg in enumerate(configs):
        tot_c = totals['totales_comparables'].get(idx, 0.0)
        tot_g = totals['totales_generales'].get(idx, 0.0)
        ahorro = totals['ahorros'].get(idx, {})
        cnt_b = totals['conteo_mas_baratos'].get(idx, 0)
        print(f"  - {cfg['nombre']}: Total General=${tot_g:,.2f} | Total Comparables=${tot_c:,.2f} | Ahorro=${ahorro.get('ahorro_dinero', 0):,.2f} ({ahorro.get('ahorro_porcentaje', 0):.2f}%) | Artículos más baratos={cnt_b}")

    # 4. Exportaciones Masivas
    print("\nGenerando exportaciones de prueba para el 100% de los datos...")
    excel_bytes = ResultExporter.export_to_excel(comparison_data, configs)
    print(f"[OK] Excel generado con {len(excel_bytes):,} bytes ({len(groups)} filas).")
    
    csv_bytes = ResultExporter.export_to_csv(comparison_data, configs)
    print(f"[OK] CSV generado con {len(csv_bytes):,} bytes.")

    pdf_bytes = ResultExporter.export_to_pdf(comparison_data, configs)
    print(f"[OK] PDF generado con {len(pdf_bytes):,} bytes.")
    
    print("\n=== TODAS LAS PRUEBAS DE ESTRÉS FINALIZARON CON ÉXITO ===")

if __name__ == "__main__":
    test_large_scale_comparison()
