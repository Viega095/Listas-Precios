import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.server import generate_in_memory_demo_datasets, clean_json_data

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.post("/")
@app.get("/load_demo")
@app.post("/load_demo")
@app.get("/api/load_demo")
@app.post("/api/load_demo")
async def load_demo_handler():
    results = generate_in_memory_demo_datasets()
    return clean_json_data({"success": True, "files": results})

handler = app
