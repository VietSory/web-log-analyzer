from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analyze, history, stats, upload, auth, servers
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

app.include_router(analyze.router ,prefix="/api", tags=["Analysis"])
app.include_router(history.router ,prefix="/api/history", tags=["History"])
app.include_router(stats.router ,prefix="/api", tags=["Stats"])
app.include_router(auth.router ,prefix="/api", tags=["Auth"])
app.include_router(servers.router ,prefix="/api", tags=["Servers"])
app.include_router(upload.router ,prefix="/api", tags=["Upload"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)