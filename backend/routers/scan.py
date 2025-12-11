import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
# Import logic từ core
from core.parser import parse_log_file
from core.ml_engine import LogAnomalyDetector

# Khởi tạo Router
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- KHỞI TẠO AI ENGINE ---
# Lưu ý: Chỉ trỏ vào thư mục models, không trỏ file lẻ
# AI Engine sẽ tự tìm: autoencoder_model.keras, scaler.pkl, label_encoders.pkl...
ai_engine = LogAnomalyDetector(model_dir="models")

# --- HÀM STARTUP (QUAN TRỌNG) ---
# Hàm này cần được gọi khi server bắt đầu chạy
# Bạn có thể đặt nó vào sự kiện @app.on_event("startup") trong main.py
def startup_load_model():
    ai_engine.load_resources()

# Load model ngay khi import file này (hoặc tốt hơn là gọi từ main.py)
startup_load_model()

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

@router.post("/api/scan/{filename}") # Nên dùng POST cho tác vụ scan
def scan_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 1. Parse log
    df = parse_log_file(file_path)
    
    if df.empty:
        return {"threat_count": 0, "threats": [], "message": "File empty or invalid format"}

    # 2. Detect anomalies
    threats = ai_engine.detect_anomalies(df)
    
    return {
        "threat_count": len(threats),
        "threats": threats
    }

@router.get("/api/stats/{filename}")
def get_stats(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    df = parse_log_file(file_path) 
    
    if df.empty: 
        return {"error": "No data"}
    
    return {
        "total_requests": len(df),
        "unique_ips": df['ip'].nunique() if 'ip' in df.columns else 0,
    }