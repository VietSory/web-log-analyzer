from pathlib import Path
import sys

from pydantic import SecretStr

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.mail_service import MailService


def test_warning_email_escapes_attacker_controlled_html(monkeypatch):
    service = MailService()
    service.settings = type(
        "SettingsStub",
        (),
        {
            "alert_email": "alerts@example.com",
            "from_email": "sender@example.com",
            "smtp_user": "sender@example.com",
            "smtp_password": SecretStr("not-used"),
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "mail_enabled": False,
        },
    )()

    message = service.build_warning_message(
        server_name='<img src=x onerror="alert(1)">',
        server_id="server-1",
        log_content="<script>alert(1)</script>",
        anomaly_details=[
            {
                "severity": "high",
                "ip": "192.0.2.1",
                "details": '<svg onload="alert(1)">',
            }
        ],
    )

    html_part = message.get_body(preferencelist=("html",)).get_content()
    assert "<script>alert(1)</script>" not in html_part
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_part
    assert "<img src=x" not in html_part
    assert "&lt;img src=x" in html_part
    assert "<svg onload" not in html_part


def test_disabled_mail_does_not_attempt_network(monkeypatch):
    service = MailService()
    service.settings = type("SettingsStub", (), {"mail_enabled": False})()

    assert service.send_warning_alert("web", "server-1", "log") is False
