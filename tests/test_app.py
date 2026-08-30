import unittest
import os
import io
import json
import pandas as pd
from fastapi.testclient import TestClient

from app.normalizer import extract_standard_measure, remove_accents_and_clean, normalize_product_record, parse_price
from app.parser import detect_column_mapping, parse_file_to_dataframe
from app.matcher import ProductMatcher
from app.calculator import PriceCalculator
from app.exporter import ResultExporter
from app.server import app, CURRENT_SESSION

class TestPriceComparatorComplete(unittest.TestCase):
    
    def setUp(self):
        self.client = TestClient(app)

    def test_unit_normalization(self):
        """Verifica la normalización de volumenes, pesos y packs."""
        unit_type, val, _ = extract_standard_measure("Coca Cola 2,25 l")
        self.assertEqual(unit_type, "ml")
        self.assertEqual(val, 2250.0)

        unit_type, val, _ = extract_standard_measure("Coca-Cola 2250 ml")
        self.assertEqual(unit_type, "ml")
        self.assertEqual(val, 2250.0)

        unit_type, val, _ = extract_standard_measure("Coca 2.25L")
        self.assertEqual(unit_type, "ml")
        self.assertEqual(val, 2250.0)

        unit_type, val, _ = extract_standard_measure("Azúcar Ledesma 1 kg")
        self.assertEqual(unit_type, "g")
        self.assertEqual(val, 1000.0)

        unit_type, val, _ = extract_standard_measure("Azúcar 1000 gr")
        self.assertEqual(unit_type, "g")
        self.assertEqual(val, 1000.0)

        unit_type, val, _ = extract_standard_measure("Cerveza Quilmes Pack x6")
        self.assertEqual(unit_type, "u")
        self.assertEqual(val, 6.0)

    def test_column_autodetection(self):
        """Verifica que detect_column_mapping reconozca nombres variados de columnas."""
        cols = ["COD_ART", "EAN13", "DETALLE_PRODUCTO", "MARCA", "PRECIO_NETO", "ALICUOTA_IVA"]
        mapping = detect_column_mapping(cols)
        
        self.assertEqual(mapping["codigo"], "COD_ART")
        self.assertEqual(mapping["codigo_barras"], "EAN13")
        self.assertEqual(mapping["descripcion"], "DETALLE_PRODUCTO")
        self.assertEqual(mapping["marca"], "MARCA")
        self.assertEqual(mapping["precio"], "PRECIO_NETO")
        self.assertEqual(mapping["iva"], "ALICUOTA_IVA")

    def test_matching_preserves_100_percent_of_rows(self):
        """Verifica que el 100% de las filas de todas las listas se preserven sin recortes."""
        list1 = [
            {"codigo": "A1", "codigo_barras": "7791001", "descripcion": "Coca Cola 2,25 l", "precio": 2500.0},
            {"codigo": "A2", "codigo_barras": "7791002", "descripcion": "Aceite Girasol 1,5 l", "precio": 1800.0},
            {"codigo": "A3", "codigo_barras": "7791003", "descripcion": "Arroz 1 kg", "precio": 1200.0},
        ]
        list2 = [
            {"codigo": "B1", "codigo_barras": "7791001", "descripcion": "Coca-Cola 2250 ml", "precio": 2400.0},
            {"codigo": "B2", "codigo_barras": "7791002", "descripcion": "Aceite 1500 ml", "precio": 1900.0},
            {"codigo": "B4", "codigo_barras": "7791004", "descripcion": "Fideos 500 g (Exclusivo B)", "precio": 900.0},
        ]
        list3 = [
            {"codigo": "C1", "codigo_barras": "7791001", "descripcion": "Coca 2.25L", "precio": 2600.0},
            {"codigo": "C5", "codigo_barras": "7791005", "descripcion": "Galletitas 300 g (Exclusivo C)", "precio": 1100.0},
        ]

        norm1 = [normalize_product_record(r, 0, i+1) for i, r in enumerate(list1)]
        norm2 = [normalize_product_record(r, 1, i+1) for i, r in enumerate(list2)]
        norm3 = [normalize_product_record(r, 2, i+1) for i, r in enumerate(list3)]

        total_input_items = len(norm1) + len(norm2) + len(norm3)
        self.assertEqual(total_input_items, 8)

        matcher = ProductMatcher([norm1, norm2, norm3])
        groups, stats = matcher.match_all()

        total_items_in_groups = sum(len([it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]) for g in groups)
        self.assertEqual(total_input_items, total_items_in_groups)

        self.assertEqual(stats["en_3_listas"], 1)
        self.assertEqual(stats["en_2_listas"], 1)
        self.assertEqual(stats["total_exclusivos"], 3)

    def test_price_calculation_and_percentage_formula(self):
        """Verifica la fórmula ((caro - barato) / barato) * 100 y totales."""
        list1 = [{"codigo": "A1", "descripcion": "Prod 1", "precio": 100.0}]
        list2 = [{"codigo": "A1", "descripcion": "Prod 1", "precio": 150.0}]
        list3 = [{"codigo": "A1", "descripcion": "Prod 1", "precio": 200.0}]

        norm1 = [normalize_product_record(r, 0, 1) for r in list1]
        norm2 = [normalize_product_record(r, 1, 1) for r in list2]
        norm3 = [normalize_product_record(r, 2, 1) for r in list3]

        matcher = ProductMatcher([norm1, norm2, norm3])
        groups, _ = matcher.match_all()

        configs = [
            {"nombre": "Prov 1", "iva_incluido": True, "descuento_percent": 0.0},
            {"nombre": "Prov 2", "iva_incluido": True, "descuento_percent": 0.0},
            {"nombre": "Prov 3", "iva_incluido": True, "descuento_percent": 0.0}
        ]

        calc = PriceCalculator(configs)
        res = calc.calculate_all(groups)
        row = res["rows"][0]

        self.assertEqual(row["precio_min"], 100.0)
        self.assertEqual(row["precio_max"], 200.0)
        self.assertEqual(row["diferencia_dinero"], 100.0)
        self.assertEqual(row["diferencia_porcentaje"], 100.0)
        self.assertEqual(row["proveedor_mas_barato"], "Prov 1")

    def test_export_generation_with_special_characters(self):
        """Verifica que las exportaciones con caracteres especiales (&, <, >) no fallen."""
        list1 = [{"codigo": "A1", "descripcion": "Prod Especial & <Promo> 500ml", "precio": 100.0}]
        norm1 = [normalize_product_record(r, 0, 1) for r in list1]
        matcher = ProductMatcher([norm1, [], []])
        groups, _ = matcher.match_all()
        configs = [
            {"nombre": "Prov 1 & Sons <Norte>", "iva_incluido": True},
            {"nombre": "Prov 2", "iva_incluido": True},
            {"nombre": "Prov 3", "iva_incluido": True}
        ]
        calc = PriceCalculator(configs)
        comp_data = calc.calculate_all(groups)

        excel_bytes = ResultExporter.export_to_excel(comp_data, configs)
        self.assertGreater(len(excel_bytes), 100)

        csv_bytes = ResultExporter.export_to_csv(comp_data, configs)
        self.assertGreater(len(csv_bytes), 10)

        pdf_bytes = ResultExporter.export_to_pdf(comp_data, configs)
        self.assertGreater(len(pdf_bytes), 100)

    def test_server_override_match_confirm_and_unlink(self):
        """Verifica que los endpoints /api/match/override (confirmar y desvincular) funcionen sin NameError."""
        # Configurar un estado inicial en CURRENT_SESSION
        item1 = normalize_product_record({"codigo": "X1", "descripcion": "Coca Cola 2.25L", "precio": 2500.0}, 0, 1)
        item2 = normalize_product_record({"codigo": "X2", "descripcion": "Coca Cola 2.25 Litros", "precio": 2400.0}, 1, 1)
        
        matcher = ProductMatcher([[item1], [item2], []])
        groups, stats = matcher.match_all()
        self.assertEqual(len(groups), 1)
        group_id = groups[0]["group_id"]

        CURRENT_SESSION["matched_groups"] = groups
        CURRENT_SESSION["configs"] = [
            {"nombre": "Prov 1", "iva_incluido": True},
            {"nombre": "Prov 2", "iva_incluido": True},
            {"nombre": "Prov 3", "iva_incluido": True}
        ]

        # 1. Probar Confirmar
        res_confirm = self.client.post("/api/match/override", json={"group_id": group_id, "action": "confirm"})
        self.assertEqual(res_confirm.status_code, 200)
        data_c = res_confirm.json()
        self.assertTrue(data_c["success"])

        # 2. Probar Desvincular (Separar)
        res_unlink = self.client.post("/api/match/override", json={"group_id": group_id, "action": "unlink"})
        self.assertEqual(res_unlink.status_code, 200)
        data_u = res_unlink.json()
        self.assertTrue(data_u["success"])
        # Debe haber separado en 2 grupos exclusivos
        self.assertEqual(len(data_u["rows"]), 2)

        # 3. Probar Confirmar Todos y Separar Todos
        res_all = self.client.post("/api/match/override", json={"group_id": "ALL", "action": "confirm_all"})
        self.assertEqual(res_all.status_code, 200)

        res_unlink_all = self.client.post("/api/match/override", json={"group_id": "ALL", "action": "unlink_all"})
        self.assertEqual(res_unlink_all.status_code, 200)

if __name__ == "__main__":
    unittest.main()
