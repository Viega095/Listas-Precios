import sys
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.normalizer import normalize_product_record
from app.matcher import ProductMatcher
from app.calculator import PriceCalculator
from app.server import ProcessRequest, clean_json_data, CURRENT_SESSION

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
@app.post("/process")
@app.post("/api/process")
async def process_handler(req: ProcessRequest):
    files_data = req.files_data or {}
    if not files_data:
        for idx, f_info in CURRENT_SESSION.get("raw_files", {}).items():
            files_data[str(idx)] = f_info.get("records", [])
            
    if not files_data or all(len(v) == 0 for v in files_data.values()):
        raise HTTPException(status_code=400, detail="No se ha cargado ninguna lista de precios para procesar.")
        
    CURRENT_SESSION["configs"] = req.configs
    
    normalized_lists: List[List[Dict[str, Any]]] = []
    for l_idx in range(3):
        str_idx = str(l_idx)
        records = files_data.get(str_idx, [])
        if records:
            mapping = req.mappings.get(str_idx, {})
            p_list = []
            for row_num, row_dict in enumerate(records, 1):
                mapped_row = {}
                for std_field, orig_col in mapping.items():
                    if orig_col and orig_col in row_dict:
                        mapped_row[std_field] = row_dict[orig_col]
                    else:
                        mapped_row[std_field] = None
                norm_item = normalize_product_record(mapped_row, list_index=l_idx, row_number=row_num)
                p_list.append(norm_item)
            normalized_lists.append(p_list)
        else:
            normalized_lists.append([])

    matcher = ProductMatcher(normalized_lists)
    groups, match_stats = matcher.match_all(similarity_threshold=req.similarity_threshold or 85.0)
    
    calculator = PriceCalculator(req.configs)
    comparison_data = calculator.calculate_all(groups)
    
    CURRENT_SESSION["matched_groups"] = groups
    CURRENT_SESSION["match_stats"] = match_stats
    CURRENT_SESSION["comparison_results"] = comparison_data
    
    return clean_json_data({
        "success": True,
        "stats": match_stats,
        "totals": comparison_data["totals"],
        "rows": comparison_data["rows"],
        "matched_groups": groups,
        "total_items": len(comparison_data["rows"])
    })

handler = app
