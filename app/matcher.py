import uuid
from typing import List, Dict, Any, Tuple, Optional, Set
from rapidfuzz import fuzz

class ProductMatcher:
    def __init__(self, lists_products: List[List[Dict[str, Any]]]):
        """
        lists_products: Lista de listas de productos normalizados (hasta 3 listas: L1, L2, L3)
        """
        self.lists_products = lists_products
        self.num_lists = len(lists_products)
        
    def _pick_one_per_list(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Selecciona como máximo un item por cada lista de procedencia."""
        chosen = []
        seen_lists = set()
        for it in items:
            if it['list_index'] not in seen_lists:
                chosen.append(it)
                seen_lists.add(it['list_index'])
        return chosen

    def match_all(self, similarity_threshold: float = 85.0, doubtful_threshold: float = 70.0) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Ejecuta el matching completo de todos los productos de todas las listas.
        Garantiza que el 100% de los productos de entrada se preserven.
        """
        groups: List[Dict[str, Any]] = []
        assigned_ids: Set[str] = set()
        
        barcode_map: Dict[str, List[Dict[str, Any]]] = {}
        code_map: Dict[str, List[Dict[str, Any]]] = {}
        token_map: Dict[str, List[Dict[str, Any]]] = {}
        
        all_items: List[Dict[str, Any]] = []
        for l_idx, p_list in enumerate(self.lists_products):
            for item in p_list:
                all_items.append(item)
                bc = item['clean_barcode'] or item['clean_sku']
                if bc and len(bc) >= 5:
                    barcode_map.setdefault(bc, []).append(item)
                c = item['clean_code']
                if c and len(c) >= 2:
                    code_map.setdefault(c, []).append(item)
                tk = item['tokens_sorted']
                if tk:
                    token_map.setdefault(tk, []).append(item)

        # 1. Matching por Código de Barras / SKU (Prioridad 1)
        for bc, items in barcode_map.items():
            while True:
                unassigned = [it for it in items if it['id'] not in assigned_ids]
                candidate_group = self._pick_one_per_list(unassigned)
                if len(candidate_group) > 1:
                    group = self._create_group_from_items(candidate_group, match_method="codigo_barras", confidence=100.0)
                    groups.append(group)
                    for it in candidate_group:
                        assigned_ids.add(it['id'])
                else:
                    break

        # 2. Matching por Código Interno de Producto (Prioridad 2)
        for code, items in code_map.items():
            while True:
                unassigned = [it for it in items if it['id'] not in assigned_ids]
                candidate_group = self._pick_one_per_list(unassigned)
                if len(candidate_group) > 1:
                    is_valid = True
                    if len(code) <= 2:
                        t0 = candidate_group[0]['tokens_sorted']
                        if not all(fuzz.token_set_ratio(t0, it['tokens_sorted']) >= 60 for it in candidate_group[1:]):
                            is_valid = False
                    if is_valid:
                        group = self._create_group_from_items(candidate_group, match_method="codigo_interno", confidence=95.0)
                        groups.append(group)
                        for it in candidate_group:
                            assigned_ids.add(it['id'])
                    else:
                        break
                else:
                    break

        # 3. Matching por Descripción Normalizada Exacta + Medida
        for item in all_items:
            if item['id'] in assigned_ids:
                continue
            
            cand_items = [item]
            item_desc = item['normalized_title']
            if not item_desc:
                continue
                
            for other_item in all_items:
                if other_item['id'] in assigned_ids or other_item['list_index'] == item['list_index']:
                    continue
                if any(it['list_index'] == other_item['list_index'] for it in cand_items):
                    continue
                    
                other_desc = other_item['normalized_title']
                if not other_desc:
                    continue
                    
                if item['tokens_sorted'] == other_item['tokens_sorted'] and item['measure_key'] == other_item['measure_key']:
                    cand_items.append(other_item)
                    
            if len(cand_items) > 1:
                group = self._create_group_from_items(cand_items, match_method="descripcion_exacta", confidence=92.0)
                groups.append(group)
                for it in cand_items:
                    assigned_ids.add(it['id'])

        # 4. Matching Difuso (Fuzzy Matching)
        for item in all_items:
            if item['id'] in assigned_ids:
                continue
                
            best_candidates = [item]
            
            for other_l_idx in range(self.num_lists):
                if other_l_idx == item['list_index']:
                    continue
                    
                best_match = None
                best_score = 0.0
                
                for other_item in self.lists_products[other_l_idx]:
                    if other_item['id'] in assigned_ids:
                        continue
                    if any(it['id'] == other_item['id'] or it['list_index'] == other_item['list_index'] for it in best_candidates):
                        continue
                        
                    if item['measure_key'] and other_item['measure_key'] and item['measure_key'] != other_item['measure_key']:
                        continue
                    if item['unit_type'] and other_item['unit_type'] and item['unit_type'] != other_item['unit_type']:
                        continue

                    if item['clean_brand'] and other_item['clean_brand'] and len(item['clean_brand']) > 2 and len(other_item['clean_brand']) > 2:
                        if item['clean_brand'] != other_item['clean_brand'] and fuzz.ratio(item['clean_brand'], other_item['clean_brand']) < 80:
                            continue

                    score1 = fuzz.token_sort_ratio(item['normalized_title'], other_item['normalized_title'])
                    score2 = fuzz.token_set_ratio(item['normalized_title'], other_item['normalized_title'])
                    score = (score1 * 0.6) + (score2 * 0.4)
                    
                    if score > best_score:
                        best_score = score
                        best_match = other_item
                        
                if best_match and best_score >= doubtful_threshold:
                    best_candidates.append(best_match)
                    
            if len(best_candidates) > 1:
                avg_score = sum(best_score for _ in best_candidates[1:]) / len(best_candidates[1:])
                method = "fuzzy_alta_certeza" if avg_score >= similarity_threshold else "fuzzy_dudoso"
                group = self._create_group_from_items(best_candidates, match_method=method, confidence=round(avg_score, 1))
                groups.append(group)
                for it in best_candidates:
                    assigned_ids.add(it['id'])

        # 5. Los productos restantes no tuvieron coincidencia -> Se registran como EXCLUSIVOS (100% de los datos preservados)
        for item in all_items:
            if item['id'] not in assigned_ids:
                group = self._create_group_from_items([item], match_method="sin_coincidencia", confidence=0.0)
                groups.append(group)
                assigned_ids.add(item['id'])

        # Validar rigurosamente que NINGÚN producto fue omitido o recortado
        total_items_input = sum(len(p_list) for p_list in self.lists_products)
        total_items_grouped = sum(len([it for it in [g.get('item_l1'), g.get('item_l2'), g.get('item_l3')] if it is not None]) for g in groups)
        
        assert total_items_input == total_items_grouped, f"Error crítico: Se perdieron productos. Entrada={total_items_input}, Agrupados={total_items_grouped}"

        stats = self._calculate_match_stats(groups)
        return groups, stats

    def _create_group_from_items(self, items: List[Dict[str, Any]], match_method: str, confidence: float) -> Dict[str, Any]:
        """Crea un grupo unificado a partir de items coincidentes."""
        group_id = f"GRP_{uuid.uuid4().hex[:8]}"
        
        item_l1 = next((it for it in items if it['list_index'] == 0), None)
        item_l2 = next((it for it in items if it['list_index'] == 1), None)
        item_l3 = next((it for it in items if it['list_index'] == 2), None)
        
        present_count = sum(1 for it in [item_l1, item_l2, item_l3] if it is not None)
        
        if match_method == "fuzzy_dudoso":
            match_status = "dudoso"
        elif present_count == 3:
            match_status = "en_3_listas"
        elif present_count == 2:
            match_status = "en_2_listas"
        else:
            match_status = "exclusivo"

        first_item = items[0]
        # Elegir la descripción original más completa y legible
        descs = [it['descripcion_orig'] for it in items if it.get('descripcion_orig') and len(it['descripcion_orig'].strip()) > 3]
        canonical_desc = max(descs, key=len) if descs else (first_item['descripcion_orig'] or first_item['normalized_title'])
        
        canonical_code = next((it['codigo_barras_orig'] or it['codigo_orig'] or it['sku_orig'] for it in items if (it.get('codigo_barras_orig') or it.get('codigo_orig') or it.get('sku_orig'))), "")
        canonical_brand = next((it['marca_orig'] for it in items if it.get('marca_orig')), "")
        canonical_presentacion = next((it['presentacion_orig'] for it in items if it.get('presentacion_orig')), "")

        return {
            "group_id": group_id,
            "producto": canonical_desc,
            "codigo": canonical_code,
            "marca": canonical_brand,
            "presentacion": canonical_presentacion,
            "item_l1": item_l1,
            "item_l2": item_l2,
            "item_l3": item_l3,
            "present_count": present_count,
            "match_method": match_method,
            "confidence": confidence,
            "match_status": match_status,
            "manual_override": False
        }

    def _calculate_match_stats(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula el resumen cuantitativo de coincidencias."""
        en_3 = sum(1 for g in groups if g['present_count'] == 3 and g['match_status'] != 'dudoso')
        en_2 = sum(1 for g in groups if g['present_count'] == 2 and g['match_status'] != 'dudoso')
        excl_l1 = sum(1 for g in groups if g['present_count'] == 1 and g['item_l1'] is not None)
        excl_l2 = sum(1 for g in groups if g['present_count'] == 1 and g['item_l2'] is not None)
        excl_l3 = sum(1 for g in groups if g['present_count'] == 1 and g['item_l3'] is not None)
        dudosos = sum(1 for g in groups if g['match_status'] == 'dudoso')
        
        return {
            "total_grupos": len(groups),
            "en_3_listas": en_3,
            "en_2_listas": en_2,
            "exclusivos_l1": excl_l1,
            "exclusivos_l2": excl_l2,
            "exclusivos_l3": excl_l3,
            "total_exclusivos": excl_l1 + excl_l2 + excl_l3,
            "dudosos": dudosos,
            "comparables": en_3 + en_2
        }
