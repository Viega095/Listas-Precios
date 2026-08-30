from typing import List, Dict, Any, Optional, Tuple

class PriceCalculator:
    def __init__(self, list_configs: List[Dict[str, Any]]):
        """
        list_configs: Configuración para cada una de las 3 listas.
        Estructura por lista:
        {
            "nombre": "Proveedor A",
            "iva_incluido": True/False,
            "iva_percent": 21.0,
            "descuento_percent": 0.0,
            "recargo_percent": 0.0,
            "bonificacion_percent": 0.0,
            "modo_precio": "unitario" o "bulto",
            "unidades_por_bulto": 1.0
        }
        """
        self.configs = list_configs

    def compute_effective_unit_price(self, raw_item: Optional[Dict[str, Any]], list_idx: int) -> Optional[float]:
        """Calcula el precio unitario final normalizado según la configuración de la lista."""
        if not raw_item:
            return None
            
        base_price = raw_item.get('precio_orig', 0.0)
        # Si precio es 0 pero precio_final existe, usar precio_final
        if base_price <= 0.0 and raw_item.get('precio_final_orig', 0.0) > 0.0:
            base_price = raw_item['precio_final_orig']
            
        if base_price <= 0.0:
            return None
            
        cfg = self.configs[list_idx] if list_idx < len(self.configs) else {}
        
        # 1. Ajuste por unidades por bulto si la lista viene en caja/bulto
        factor_bulto = float(cfg.get('unidades_por_bulto', 1.0) or 1.0)
        if cfg.get('modo_precio') == 'bulto' and factor_bulto > 1.0:
            price = base_price / factor_bulto
        else:
            price = base_price

        # 2. Descuentos específicos del item o de la lista
        item_dto = raw_item.get('descuento_orig', 0.0)
        general_dto = float(cfg.get('descuento_percent', 0.0) or 0.0)
        total_dto = item_dto if item_dto > 0 else general_dto
        
        if total_dto > 0:
            price = price * (1.0 - (total_dto / 100.0))

        # 3. Bonificaciones y recargos
        bonif = float(cfg.get('bonificacion_percent', 0.0) or 0.0)
        if bonif > 0:
            price = price * (1.0 - (bonif / 100.0))
            
        recargo = float(cfg.get('recargo_percent', 0.0) or 0.0)
        if recargo > 0:
            price = price * (1.0 + (recargo / 100.0))

        # 4. Ajuste de IVA
        iva_incluido = cfg.get('iva_incluido', True)
        iva_percent = float(cfg.get('iva_percent', 21.0) or 21.0)
        
        # Si el item trae su propia alícuota de IVA, usarla
        if raw_item.get('iva_orig', 0.0) > 0:
            iva_percent = raw_item['iva_orig']
            
        if not iva_incluido and iva_percent > 0:
            price = price * (1.0 + (iva_percent / 100.0))
            
        return round(price, 2)

    def calculate_all(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula precios normalizados para cada grupo, comparativas y totales analíticos completos.
        """
        comparison_rows: List[Dict[str, Any]] = []
        
        cheapest_counts = {0: 0, 1: 0, 2: 0, "empate": 0}
        exclusive_counts = {0: 0, 1: 0, 2: 0}
        equal_prices_count = 0
        invalid_prices_count = 0
        
        for g in groups:
            item_l1 = g.get('item_l1')
            item_l2 = g.get('item_l2')
            item_l3 = g.get('item_l3')
            
            p1 = self.compute_effective_unit_price(item_l1, 0)
            p2 = self.compute_effective_unit_price(item_l2, 1)
            p3 = self.compute_effective_unit_price(item_l3, 2)
            
            # Cantidad a comparar: tomar cantidad del item o default 1.0
            qty = 1.0
            for it in [item_l1, item_l2, item_l3]:
                if it and it.get('cantidad_orig', 1.0) > 0:
                    qty = it.get('cantidad_orig', 1.0)
                    break
                    
            valid_prices = [(idx, p) for idx, p in [(0, p1), (1, p2), (2, p3)] if p is not None and p > 0]
            
            row: Dict[str, Any] = {
                "group_id": g['group_id'],
                "producto": g['producto'],
                "codigo": g['codigo'],
                "marca": g['marca'],
                "presentacion": g['presentacion'],
                "cantidad": qty,
                "cantidad_es_default": (qty == 1.0),
                
                # Datos originales y efectivos
                "precio_l1": p1,
                "precio_l2": p2,
                "precio_l3": p3,
                "precio_l1_orig": item_l1['precio_orig'] if item_l1 else None,
                "precio_l2_orig": item_l2['precio_orig'] if item_l2 else None,
                "precio_l3_orig": item_l3['precio_orig'] if item_l3 else None,
                "cod_l1": item_l1['codigo_orig'] if item_l1 else "",
                "cod_l2": item_l2['codigo_orig'] if item_l2 else "",
                "cod_l3": item_l3['codigo_orig'] if item_l3 else "",
                "desc_l1": item_l1['descripcion_orig'] if item_l1 else "",
                "desc_l2": item_l2['descripcion_orig'] if item_l2 else "",
                "desc_l3": item_l3['descripcion_orig'] if item_l3 else "",
                
                "match_status": g['match_status'],
                "match_method": g['match_method'],
                "confidence": g['confidence'],
                "present_count": g['present_count'],
                "es_dudoso": (g['match_status'] == 'dudoso')
            }
            
            if not valid_prices:
                row["proveedor_mas_barato"] = "Sin precio válido"
                row["proveedor_mas_barato_idx"] = None
                row["precio_min"] = None
                row["precio_max"] = None
                row["diferencia_dinero"] = 0.0
                row["diferencia_porcentaje"] = 0.0
                row["explicacion_porcentaje"] = "No hay precios válidos"
                row["estado_precio"] = "Sin precio"
                invalid_prices_count += 1
            elif len(valid_prices) == 1:
                idx, p = valid_prices[0]
                prov_name = self.configs[idx]['nombre'] if idx < len(self.configs) else f"Lista {idx+1}"
                row["proveedor_mas_barato"] = f"Exclusivo {prov_name}"
                row["proveedor_mas_barato_idx"] = idx
                row["precio_min"] = p
                row["precio_max"] = p
                row["diferencia_dinero"] = 0.0
                row["diferencia_porcentaje"] = 0.0
                row["explicacion_porcentaje"] = "Único proveedor disponible"
                row["estado_precio"] = f"Exclusivo {prov_name}"
                exclusive_counts[idx] = exclusive_counts.get(idx, 0) + 1
            else:
                prices_only = [p for _, p in valid_prices]
                min_p = min(prices_only)
                max_p = max(prices_only)
                
                # Proveedor(es) con el precio mínimo
                cheapest_indices = [idx for idx, p in valid_prices if abs(p - min_p) < 0.001]
                
                if len(cheapest_indices) == len(valid_prices) and min_p == max_p:
                    row["proveedor_mas_barato"] = "Mismo precio en todas"
                    row["proveedor_mas_barato_idx"] = -1
                    equal_prices_count += 1
                    row["estado_precio"] = "Precio igual"
                    cheapest_counts["empate"] += 1
                elif len(cheapest_indices) > 1:
                    names = [self.configs[i]['nombre'] for i in cheapest_indices]
                    row["proveedor_mas_barato"] = f"Empate: {' / '.join(names)}"
                    row["proveedor_mas_barato_idx"] = cheapest_indices[0]
                    row["estado_precio"] = "Empate más barato"
                    cheapest_counts["empate"] += 1
                else:
                    best_idx = cheapest_indices[0]
                    prov_name = self.configs[best_idx]['nombre']
                    row["proveedor_mas_barato"] = prov_name
                    row["proveedor_mas_barato_idx"] = best_idx
                    cheapest_counts[best_idx] = cheapest_counts.get(best_idx, 0) + 1
                    row["estado_precio"] = f"Más barato: {prov_name}"

                diff_money = round(max_p - min_p, 2)
                # Fórmula requerida: ((precio más caro - precio más barato) / precio más barato) * 100
                diff_pct = round(((max_p - min_p) / min_p) * 100.0, 2) if min_p > 0 else 0.0
                
                row["precio_min"] = min_p
                row["precio_max"] = max_p
                row["diferencia_dinero"] = diff_money
                row["diferencia_porcentaje"] = diff_pct
                row["explicacion_porcentaje"] = f"Calculado sobre el precio más económico (${min_p:,.2f})"

            comparison_rows.append(row)

        # -------------------------------------------------------------
        # Cálculos de Totales y Análisis Financiero Global
        # -------------------------------------------------------------
        num_lists = len(self.configs)
        
        # 1. Total general de cada lista (sumando todos sus productos)
        totales_generales = {}
        for l_idx in range(num_lists):
            key = f"precio_l{l_idx+1}"
            totales_generales[l_idx] = round(sum(
                (r[key] * r['cantidad']) for r in comparison_rows if r.get(key) is not None
            ), 2)

        # 2. Total de productos comparables (aparecen en al menos 2 listas)
        comparable_rows = [r for r in comparison_rows if len([p for p in [r['precio_l1'], r['precio_l2'], r['precio_l3']] if p is not None]) >= 2]
        
        totales_comparables = {}
        for l_idx in range(num_lists):
            key = f"precio_l{l_idx+1}"
            totales_comparables[l_idx] = round(sum(
                (r[key] * r['cantidad']) for r in comparable_rows if r.get(key) is not None
            ), 2)

        # 3. Total de compra óptima comprando siempre al proveedor más barato (para todos los productos)
        total_compra_optima = round(sum(
            (r['precio_min'] * r['cantidad']) for r in comparison_rows if r.get('precio_min') is not None
        ), 2)
        
        # Total de compra óptima solo para los comparables
        total_optimo_comparables = round(sum(
            (r['precio_min'] * r['cantidad']) for r in comparable_rows if r.get('precio_min') is not None
        ), 2)

        # 4. Ahorro posible frente a cada lista (en valor monetario y porcentual)
        ahorros = {}
        for l_idx in range(num_lists):
            tot_list = totales_comparables.get(l_idx, 0.0)
            ahorro_dinero = round(max(0.0, tot_list - total_optimo_comparables), 2)
            ahorro_pct = round((ahorro_dinero / tot_list) * 100.0, 2) if tot_list > 0 else 0.0
            ahorros[l_idx] = {
                "ahorro_dinero": ahorro_dinero,
                "ahorro_porcentaje": ahorro_pct
            }

        # 5. Diferencia total en dinero entre las tres listas (max total general - min total general)
        valid_totales = [t for t in totales_generales.values() if t > 0]
        diferencia_total_listas = round(max(valid_totales) - min(valid_totales), 2) if valid_totales else 0.0

        # 6. Top 10 productos con mayor diferencia porcentual y en dinero
        top_diferencia_dinero = sorted(
            [r for r in comparable_rows if r.get('diferencia_dinero', 0) > 0],
            key=lambda x: x['diferencia_dinero'],
            reverse=True
        )[:10]

        top_diferencia_porcentaje = sorted(
            [r for r in comparable_rows if r.get('diferencia_porcentaje', 0) > 0],
            key=lambda x: x['diferencia_porcentaje'],
            reverse=True
        )[:10]

        totals_summary = {
            "total_productos_comparados": len(comparison_rows),
            "total_productos_comparables": len(comparable_rows),
            "total_productos_exclusivos": sum(exclusive_counts.values()),
            "total_precios_iguales": equal_prices_count,
            "total_sin_precio_valido": invalid_prices_count,
            "totales_generales": totales_generales,
            "totales_comparables": totales_comparables,
            "total_compra_optima": total_compra_optima,
            "total_optimo_comparables": total_optimo_comparables,
            "ahorros": ahorros,
            "diferencia_total_listas": diferencia_total_listas,
            "conteo_mas_baratos": cheapest_counts,
            "conteo_exclusivos": exclusive_counts,
            "top_diferencia_dinero": top_diferencia_dinero,
            "top_diferencia_porcentaje": top_diferencia_porcentaje
        }

        return {
            "rows": comparison_rows,
            "totals": totals_summary
        }
