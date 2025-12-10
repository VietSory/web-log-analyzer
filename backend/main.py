from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routers import scan
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        scan.load_models()
        print("[INFO] Models loaded successfully via Router.")
    except Exception as e:
        print(f"[ERROR] Failed to load models: {e}")
    
    yield # Server chạy

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(scan.router , tags=["Scan"])
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)