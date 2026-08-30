import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

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
@app.get("/health")
@app.post("/health")
@app.get("/api/health")
@app.post("/api/health")
async def health_handler():
    return {"status": "ok"}

handler = app
