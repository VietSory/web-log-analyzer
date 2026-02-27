from __future__ import annotations

from email.message import EmailMessage
from html import escape
import logging
import smtplib
import ssl
from typing import Any

from config import get_settings


logger = logging.getLogger(__name__)


class MailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_warning_message(
        self,
        *,
        server_name: str,
        server_id: str,
        log_content: str,
        anomaly_details: list[dict[str, Any]] | None = None,
        recipient_email: str | None = None,
    ) -> EmailMessage:
        recipient = recipient_email or self.settings.alert_email
        sender = self.settings.from_email or self.settings.smtp_user
        if not recipient:
            raise ValueError("Alert recipient is not configured")
        if not sender:
            raise ValueError("Mail sender is not configured")

        message = EmailMessage()
        message["Subject"] = f"Web Log Analyzer alert: {server_name}"
        message["From"] = sender
        message["To"] = recipient

        findings = anomaly_details or []
        text_lines = [
            "Security warning detected.",
            f"Server: {server_name}",
            f"Server ID: {server_id}",
            "",
            "Log content:",
            log_content,
        ]
        for finding in findings:
            text_lines.extend(
                [
                    "",
                    f"Severity: {finding.get('severity', 'unknown')}",
                    f"IP: {finding.get('ip', 'unknown')}",
                    f"Details: {finding.get('details', finding.get('title', ''))}",
                ]
            )
        message.set_content("\n".join(text_lines))

        finding_rows = "".join(
            "<tr>"
            f"<td>{escape(str(finding.get('severity', 'unknown')))}</td>"
            f"<td>{escape(str(finding.get('ip', 'unknown')))}</td>"
            f"<td>{escape(str(finding.get('details', finding.get('title', ''))))}</td>"
            "</tr>"
            for finding in findings
        )
        message.add_alternative(
            "<html><body>"
            "<h2>Security warning detected</h2>"
            f"<p><strong>Server:</strong> {escape(server_name)}</p>"
            f"<p><strong>Server ID:</strong> {escape(server_id)}</p>"
            "<h3>Log content</h3>"
            f"<pre>{escape(log_content)}</pre>"
            "<h3>Findings</h3>"
            "<table><thead><tr><th>Severity</th><th>IP</th><th>Details</th></tr></thead>"
            f"<tbody>{finding_rows}</tbody></table>"
            "</body></html>",
            subtype="html",
        )
        return message

    def send_warning_alert(
        self,
        server_name: str,
        server_id: str,
        log_content: str,
        anomaly_details: list[dict[str, Any]] | None = None,
        recipient_email: str | None = None,
    ) -> bool:
        if not self.settings.mail_enabled:
            return False

        try:
            message = self.build_warning_message(
                server_name=server_name,
                server_id=server_id,
                log_content=log_content,
                anomaly_details=anomaly_details,
                recipient_email=recipient_email,
            )
            context = ssl.create_default_context()
            with smtplib.SMTP(
                self.settings.smtp_server,
                self.settings.smtp_port,
                timeout=10,
            ) as server:
                server.starttls(context=context)
                server.login(
                    self.settings.smtp_user,
                    self.settings.smtp_password.get_secret_value(),
                )
                server.send_message(message)
        except (OSError, smtplib.SMTPException, ValueError):
            logger.exception("warning alert delivery failed")
            return False

        return True


mail_service = MailService()
