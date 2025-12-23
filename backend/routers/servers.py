from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import (
    create_server, 
    get_user_servers, 
    get_server_by_id, 
    delete_server,
    get_server_logs,
    create_log
)
from core.ml_engine import LogAnomalyDetector
from core.mail_service import mail_service
import pandas as pd
import os

router = APIRouter()

class CreateServerRequest(BaseModel):
    owner_id: str
    name: str
    ipv4: Optional[str] = None

class LogAnalyzeRequest(BaseModel):
    server_id: str
    log_content: str
    ip: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status: Optional[int] = None
    size: Optional[int] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    datetime: Optional[str] = None

@router.post("/servers")
def create_server_endpoint(request: CreateServerRequest):
    """Create a new server"""
    try:
        server_id = create_server(request.owner_id, request.name, request.ipv4)
        return {
            "status": "success", 
            "message": "Server created successfully",
            "server_id": server_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create server: {str(e)}")

@router.get("/servers/user/{owner_id}")
def get_user_servers_endpoint(owner_id: str):
    """Get all servers for a specific user"""
    try:
        servers = get_user_servers(owner_id)
        return servers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch servers: {str(e)}")

@router.get("/servers/{server_id}")
def get_server_endpoint(server_id: str):
    """Get server details by ID"""
    try:
        server = get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch server: {str(e)}")

@router.delete("/servers/{server_id}")
def delete_server_endpoint(server_id: str):
    """Delete a server and its associated logs"""
    try:
        success = delete_server(server_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete server")
        return {"status": "success", "message": "Server deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete server: {str(e)}")

@router.get("/servers/{server_id}/logs")
def get_server_logs_endpoint(server_id: str):
    """Get all logs for a specific server"""
    try:
        server = get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        logs = get_server_logs(server_id)
        return {
            "server": server,
            "logs": logs,
            "total_logs": len(logs)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

@router.get("/servers/{server_id}/stats")
def get_server_stats_endpoint(server_id: str):
    """Get statistics for server logs, focusing on warnings"""
    try:
        server = get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        logs = get_server_logs(server_id)
        
        # Calculate statistics - unified status: warning, safe
        total_logs = len(logs)
        warning_logs = [log for log in logs if log.get('status', '').lower() == 'warning']
        safe_logs = [log for log in logs if log.get('status', '').lower() == 'safe']
        
        # Status distribution
        status_counts = {}
        for log in logs:
            status = log.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Warning statistics
        warning_count = len(warning_logs)
        warning_percentage = (warning_count / total_logs * 100) if total_logs > 0 else 0
        safe_percentage = (len(safe_logs) / total_logs * 100) if total_logs > 0 else 0
        
        return {
            "server": server,
            "total_logs": total_logs,
            "warning_count": warning_count,
            "safe_count": len(safe_logs),
            "warning_percentage": round(warning_percentage, 2),
            "safe_percentage": round(safe_percentage, 2),
            "status_distribution": status_counts,
            "warning_logs": warning_logs[:10]  # Latest 10 warnings
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

@router.post("/servers/{server_id}/analyze")
def analyze_log_endpoint(server_id: str, request: LogAnalyzeRequest):
    """Analyze a log entry and save to database with warning/safe status"""
    try:
        server = get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        
        # Initialize ML engine
        model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')
        detector = LogAnomalyDetector(model_dir)
        detector.load_resources()
        
        # Prepare log data for analysis
        log_data = {
            'ip': request.ip or 'unknown',
            'method': request.method or 'GET',
            'path': request.path or '/',
            'status': request.status or 200,
            'size': request.size or 0,
            'referrer': request.referrer or '-',
            'user_agent': request.user_agent or 'unknown',
            'datetime': request.datetime or '',
        }
        
        # Create DataFrame for analysis
        df = pd.DataFrame([log_data])
        
        # Detect anomalies
        anomalies = detector.detect_anomalies(df)
        
        # Determine status: warning if anomaly detected, safe otherwise
        status = 'warning' if anomalies else 'safe'
        
        # Save log to database
        log_id = create_log(server_id, status, request.log_content)
        
        # Send email alert if warning detected
        if status == 'warning':
            try:
                mail_service.send_warning_alert(
                    server_name=server.get('name', 'Unknown Server'),
                    server_id=server_id,
                    log_content=request.log_content,
                    anomaly_details=anomalies
                )
            except Exception as mail_error:
                print(f"⚠️ Failed to send email alert: {mail_error}")
                # Don't fail the request if email fails
        
        return {
            "status": "success",
            "log_id": log_id,
            "log_status": status,
            "is_anomaly": len(anomalies) > 0,
            "anomalies": anomalies,
            "message": f"Log analyzed and saved as '{status}'"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze log: {str(e)}")
