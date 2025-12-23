#!/usr/bin/env python3
"""
Test mail service functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.mail_service import mail_service

def test_mail_service():
    print("=" * 60)
    print("📧 TESTING MAIL SERVICE")
    print("=" * 60)
    
    # Test data
    test_server_name = "Test Web Server"
    test_server_id = "abc123-test-server-id"
    test_log_content = "2025-12-23 15:30:45 ERROR Failed login attempt from 192.168.1.100 user=admin path=/admin/login"
    test_anomalies = [
        {
            "ip": "192.168.1.100",
            "severity": "High",
            "reconstruction_error": 0.0847,
            "details": "Path: /admin/login - Suspicious activity detected"
        }
    ]
    
    print(f"\n📤 Sending test warning email...")
    print(f"   Server: {test_server_name}")
    print(f"   Server ID: {test_server_id}")
    print(f"   Log: {test_log_content[:50]}...")
    
    result = mail_service.send_warning_alert(
        server_name=test_server_name,
        server_id=test_server_id,
        log_content=test_log_content,
        anomaly_details=test_anomalies
    )
    
    if result:
        print("\n✅ Email sent successfully!")
        print(f"   Check inbox at: {os.getenv('ALERT_EMAIL', 'admin@example.com')}")
    else:
        print("\n❌ Failed to send email")
        print("   Check your .env configuration:")
        print("   - MAIL_ENABLED=true")
        print("   - SMTP_USER and SMTP_PASSWORD are correct")
        print("   - ALERT_EMAIL is set")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_mail_service()
