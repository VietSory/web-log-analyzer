import os
import shutil
import pandas as pd 
from fastapi import APIRouter, UploadFile, File, HTTPException
from core.parser import parse_log_file
from core.ml_engine import LogAnomalyDetector

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Khởi tạo AI
ai_engine = LogAnomalyDetector(model_dir="models")
def startup_load_model():
    ai_engine.load_resources()
startup_load_model()

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename is None:
        raise HTTPException(status_code=400, detail="No file uploaded")
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": file.filename}

@router.post("/api/scan/{filename}")
def scan_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path): raise HTTPException(status_code=404, detail="Not found")
    
    df = parse_log_file(file_path)
    if df.empty: return {"threat_count": 0, "threats": []}
    
    threats = ai_engine.detect_anomalies(df)
    return {"threat_count": len(threats), "threats": threats}

@router.get("/api/stats/{filename}")
def get_stats(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path): raise HTTPException(status_code=404, detail="File not found")
        
    df = parse_log_file(file_path) 
    if df.empty: return {"error": "No data parsed"}
    
    # 1. Tính Metrics
    total_req = len(df)
    unique_ips = int(df['ip'].nunique()) if 'ip' in df.columns else 0
    avg_size = round(float(df['size'].mean()) / 1024, 2) if 'size' in df.columns else 0
    
    error_5xx = df[df['status'] >= 500].shape[0] if 'status' in df.columns else 0
    error_rate = round((error_5xx / total_req) * 100, 2) if total_req > 0 else 0
    
    # 2. Status Distribution (Top 5)
    status_counts = {}
    if 'status' in df.columns:
        s_counts = df['status'].value_counts().head(5)
        status_counts = {str(k): int(v) for k, v in s_counts.items()}

    # 3. Traffic Over Time (FIX LỖI PYLANCE)
    chart_data = {}
    if 'datetime' in df.columns:
        df_time = df.dropna(subset=['datetime'])
        if not df_time.empty:
            # Group theo giờ
            traffic = df_time.resample('H', on='datetime').size()
            ts_list = traffic.index.tolist()
            cnt_list = traffic.values.tolist()
            for ts, count in zip(ts_list, cnt_list):
                if count > 0:
                    time_str = ts.strftime('%Y-%m-%d %H:%M')
                    chart_data[time_str] = int(count)

    return {
        "total_requests": total_req,
        "unique_ips": unique_ips,
        "avg_body_size": avg_size,
        "error_rate": error_rate,
        "status_distribution": status_counts,
        "traffic_chart": chart_data
    }
    
@router.get("/api/logs/{filename}")
def get_logs(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path): 
        raise HTTPException(status_code=404, detail="File not found")
    df = parse_log_file(file_path)
    if df.empty: 
        return []
    if 'datetime' in df.columns:
        df['datetime'] = df['datetime'].astype(str)
    return df.head(10000).to_dict(orient="records")