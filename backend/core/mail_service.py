# FILE: backend/core/mail_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

class MailService:
    def __init__(self):
        # Cấu hình SMTP - có thể dùng Gmail, Outlook, hoặc SMTP server riêng
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "your-email@gmail.com")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "your-app-password")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.enabled = os.getenv("MAIL_ENABLED", "false").lower() == "true"
    
    def send_warning_alert(self, server_name, server_id, log_content, anomaly_details=None, recipient_email=None):
        """
        Gửi email cảnh báo khi phát hiện log warning
        
        Args:
            server_name: Tên server
            server_id: ID của server
            log_content: Nội dung log
            anomaly_details: Chi tiết anomaly từ ML engine
            recipient_email: Email người nhận (mặc định từ env)
        """
        if not self.enabled:
            print("📧 Mail service is disabled. Set MAIL_ENABLED=true to enable.")
            return False
        
        # Email người nhận mặc định
        to_email = recipient_email or os.getenv("ALERT_EMAIL", "admin@example.com")
        
        # Tạo nội dung email
        subject = f"⚠️ WARNING ALERT - Server: {server_name}"
        
        # HTML email body
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); 
                              color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; }}
                    .alert-box {{ background: #fff3cd; border-left: 4px solid #ffc107; 
                                  padding: 15px; margin: 15px 0; border-radius: 4px; }}
                    .info-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                    .info-table td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
                    .info-table td:first-child {{ font-weight: bold; width: 150px; }}
                    .log-content {{ background: #2d2d2d; color: #f8f8f2; padding: 15px; 
                                    border-radius: 4px; overflow-x: auto; font-family: 'Courier New', monospace; }}
                    .footer {{ text-align: center; color: #6c757d; margin-top: 20px; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0;">⚠️ Security Warning Alert</h2>
                        <p style="margin: 5px 0 0 0;">Anomaly Detected in Server Logs</p>
                    </div>
                    
                    <div class="content">
                        <div class="alert-box">
                            <strong>🚨 Action Required:</strong> A suspicious log entry has been detected and flagged as a warning.
                        </div>
                        
                        <h3>Server Information</h3>
                        <table class="info-table">
                            <tr>
                                <td>Server Name:</td>
                                <td>{server_name}</td>
                            </tr>
                            <tr>
                                <td>Server ID:</td>
                                <td><code>{server_id}</code></td>
                            </tr>
                            <tr>
                                <td>Detection Time:</td>
                                <td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td>
                            </tr>
                            <tr>
                                <td>Status:</td>
                                <td><span style="color: #dc3545; font-weight: bold;">WARNING</span></td>
                            </tr>
                        </table>
                        
                        <h3>Log Content</h3>
                        <div class="log-content">
                            {log_content}
                        </div>
        """
        
        # Thêm chi tiết anomaly nếu có
        if anomaly_details and len(anomaly_details) > 0:
            html_body += """
                        <h3>Anomaly Details</h3>
                        <table class="info-table">
            """
            for anomaly in anomaly_details:
                html_body += f"""
                            <tr>
                                <td>IP Address:</td>
                                <td>{anomaly.get('ip', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>Severity:</td>
                                <td><span style="color: #dc3545;">{anomaly.get('severity', 'N/A')}</span></td>
                            </tr>
                            <tr>
                                <td>Reconstruction Error:</td>
                                <td>{anomaly.get('reconstruction_error', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>Details:</td>
                                <td>{anomaly.get('details', 'N/A')}</td>
                            </tr>
                """
            html_body += """
                        </table>
            """
        
        html_body += """
                        <div class="footer">
                            <p>This is an automated alert from Web Log Analyzer System</p>
                            <p>Please review the server logs and take appropriate action if necessary.</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Text version (fallback)
        text_body = f"""
⚠️ SECURITY WARNING ALERT

Server: {server_name}
Server ID: {server_id}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Status: WARNING

Log Content:
{log_content}
"""
        
        if anomaly_details:
            text_body += "\n\nAnomaly Details:\n"
            for anomaly in anomaly_details:
                text_body += f"- IP: {anomaly.get('ip', 'N/A')}\n"
                text_body += f"  Severity: {anomaly.get('severity', 'N/A')}\n"
                text_body += f"  Error: {anomaly.get('reconstruction_error', 'N/A')}\n"
        
        text_body += "\n---\nThis is an automated alert from Web Log Analyzer System"
        
        # Tạo message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        
        # Attach parts
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Gửi email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            print(f"✅ Warning email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

# Singleton instance
mail_service = MailService()
