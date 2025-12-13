from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import scan 
from database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Server is starting up...")
    init_db() 
    
    yield # Server sẽ chạy và nhận request tại điểm này
    
    # Phần này chạy khi Server TẮT (Shutdown)
    print("🛑 Server is shutting down...")

# Khởi tạo App với tham số lifespan
app = FastAPI(title="Log Analyzer API", lifespan=lifespan)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router , tags=["Log Scan API"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)