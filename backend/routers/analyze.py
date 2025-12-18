import os
from fastapi import APIRouter, HTTPException
from core.parser import parse_log_file
from core.ml_engine import LogAnomalyDetector

router = APIRouter()
UPLOAD_DIR = "uploads"

ai_engine = LogAnomalyDetector(model_dir="models")
print("⏳ Loading AI Model for Analyzer...")
try:
    ai_engine.load_resources()
except Exception as e:
    print(f"⚠️ Warning: Could not load AI model: {e}")

@router.post("/scan/{filename}")
def scan_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path): 
        raise HTTPException(status_code=404, detail="File not found")
    df = parse_log_file(file_path)
    if df.empty: 
        return {"threat_count": 0, "threats": []}
    try:
        threats = ai_engine.detect_anomalies(df)
        return {"threat_count": len(threats), "threats": threats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {e}")