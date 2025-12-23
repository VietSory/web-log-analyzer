#!/usr/bin/env python3
"""
Test script for real-time log analysis API
Demonstrates how to:
1. Create a server
2. Analyze logs in real-time
3. Check server stats
"""

import requests
import json
import time

API_URL = "http://127.0.0.1:8000"

def test_real_time_logging():
    print("=" * 60)
    print("🧪 REAL-TIME LOG ANALYSIS TEST")
    print("=" * 60)
    
    # 1. Create a test user/server (use existing admin)
    user_id = "admin"  # You can replace with actual user_id
    
    # 2. Create a server
    print("\n📌 Step 1: Creating a server...")
    server_payload = {
        "owner_id": user_id,
        "name": "Test Server Real-Time",
        "ipv4": "192.168.1.100"
    }
    server_res = requests.post(f"{API_URL}/api/servers", json=server_payload)
    if server_res.status_code != 200:
        print(f"❌ Failed to create server: {server_res.text}")
        return
    
    server_id = server_res.json()["server_id"]
    print(f"✅ Server created: {server_id}")
    
    # 3. Analyze sample logs in real-time
    print("\n📌 Step 2: Sending real-time logs for analysis...")
    
    sample_logs = [
        {
            "server_id": server_id,
            "log_content": "GET /api/users HTTP/1.1 200 1024",
            "ip": "192.168.1.10",
            "method": "GET",
            "path": "/api/users",
            "status": 200,
            "size": 1024,
            "referrer": "-",
            "user_agent": "Mozilla/5.0",
            "datetime": "2025-12-23 10:30:00"
        },
        {
            "server_id": server_id,
            "log_content": "POST /admin/login HTTP/1.1 401 512",
            "ip": "192.168.1.50",
            "method": "POST",
            "path": "/admin/login",
            "status": 401,
            "size": 512,
            "referrer": "-",
            "user_agent": "curl/7.64.1",
            "datetime": "2025-12-23 10:31:00"
        },
        {
            "server_id": server_id,
            "log_content": "GET /static/style.css HTTP/1.1 200 2048",
            "ip": "192.168.1.11",
            "method": "GET",
            "path": "/static/style.css",
            "status": 200,
            "size": 2048,
            "referrer": "/",
            "user_agent": "Mozilla/5.0",
            "datetime": "2025-12-23 10:32:00"
        }
    ]
    
    for idx, log_data in enumerate(sample_logs, 1):
        print(f"\n  Analyzing log #{idx}...")
        analyze_res = requests.post(
            f"{API_URL}/api/servers/{server_id}/analyze",
            json=log_data
        )
        
        if analyze_res.status_code == 200:
            result = analyze_res.json()
            print(f"  ✅ Status: {result['log_status'].upper()}")
            print(f"  📊 Log ID: {result['log_id'][:12]}...")
            if result['is_anomaly']:
                print(f"  ⚠️ ANOMALIES DETECTED:")
                for anomaly in result['anomalies']:
                    print(f"    - IP: {anomaly['ip']}, Error: {anomaly['reconstruction_error']:.4f}")
            else:
                print(f"  ✅ Safe log")
        else:
            print(f"  ❌ Failed: {analyze_res.text}")
        
        time.sleep(1)  # Simulate real-time intervals
    
    # 4. Fetch server statistics
    print("\n📌 Step 3: Fetching server statistics...")
    stats_res = requests.get(f"{API_URL}/api/servers/{server_id}/stats")
    
    if stats_res.status_code == 200:
        stats = stats_res.json()
        print(f"\n📊 SERVER STATISTICS:")
        print(f"  📈 Total Logs: {stats['total_logs']}")
        print(f"  ⚠️  Warnings: {stats['warning_count']} ({stats['warning_percentage']}%)")
        print(f"  ✅ Safe Logs: {stats['safe_count']} ({stats['safe_percentage']}%)")
        print(f"\n  Status Distribution:")
        for status, count in stats['status_distribution'].items():
            print(f"    - {status.upper()}: {count}")
    else:
        print(f"❌ Failed to fetch stats: {stats_res.text}")
    
    # 5. Fetch all logs
    print("\n📌 Step 4: Fetching all logs...")
    logs_res = requests.get(f"{API_URL}/api/servers/{server_id}/logs")
    
    if logs_res.status_code == 200:
        logs_data = logs_res.json()
        logs = logs_data.get("logs", [])
        print(f"\n📜 ALL LOGS ({len(logs)} total):")
        for idx, log in enumerate(logs, 1):
            status_icon = "⚠️" if log['status'] == 'warning' else "✅"
            print(f"  {idx}. {status_icon} [{log['status'].upper()}] {log['id'][:12]}...")
            print(f"     Content: {log['contents'][:50]}...")
    else:
        print(f"❌ Failed to fetch logs: {logs_res.text}")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETED!")
    print("=" * 60)
    print(f"\n💡 Server ID: {server_id}")
    print("You can now:")
    print("1. Open the frontend and go to Servers page")
    print("2. Click 'Chi tiết' (Details) on this server")
    print("3. See the real-time logs and statistics update every 5 seconds")
    print("=" * 60)

if __name__ == "__main__":
    test_real_time_logging()
