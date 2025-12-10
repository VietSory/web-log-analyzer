import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from core.ml_engine import LogAnomalyDetector

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ai_enginer = LogAnomalyDetector(
    model_path="models/log_anomaly_model.pkl",
    scaler_path="models/log_scaler.pkl"
)

def load_models():
    ai_enginer.load_model()
    
@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename is None :
        raise HTTPException(status_code=400, detail="No file uploaded")
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status" : "success","filename": file.filename}

@router.get("/api/scan/{filename}")
def scan_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    df = parse_log_file(file_path)
    
    threats = ai_engine.detect_anomalies(df)
    
    return {
        "threat_count": len(threats),
        "threats": threats
    }

@app.get("/api/stats/{filename}")
def get_stats(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    df = parse_log_file(file_path) 
    
    if df.empty: return {"error": "No data"}
    
    return {
        "total_requests": len(df),
        "unique_ips": df['ip'].nunique() if 'ip' in df.columns else 0,
    }