import sys
import os
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.parser import parse_file_to_dataframe, detect_column_mapping
from app.server import clean_json_data, CURRENT_SESSION

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
@app.post("/{list_idx}")
@app.post("/upload/{list_idx}")
@app.post("/api/upload/{list_idx}")
async def upload_file_handler(list_idx: int = 0, file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename
        
        df, columns, warnings = parse_file_to_dataframe(content, filename)
        if df.empty:
            raise HTTPException(status_code=400, detail=f"El archivo {filename} está vacío o no contiene filas válidas.")
            
        detected_map = detect_column_mapping(columns, df)
        df_clean = df.fillna("")
        records = df_clean.to_dict(orient="records")
        preview_rows = df_clean.head(10).to_dict(orient="records")
        
        CURRENT_SESSION["raw_files"][list_idx] = {
            "filename": filename,
            "records": records,
            "columns": columns,
            "warnings": warnings,
            "total_rows": len(records)
        }
        CURRENT_SESSION["mappings"][list_idx] = detected_map
        
        return clean_json_data({
            "success": True,
            "list_idx": list_idx,
            "filename": filename,
            "total_rows": len(records),
            "columns": columns,
            "detected_mapping": detected_map,
            "warnings": warnings,
            "preview_rows": preview_rows,
            "raw_records": records
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

handler = app
