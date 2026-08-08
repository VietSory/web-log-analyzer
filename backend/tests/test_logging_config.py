from pathlib import Path
import json
import logging
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.logging_config import JsonLogFormatter, configure_logging


def test_json_formatter_emits_machine_readable_core_fields():
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request %s",
        args=("complete",),
        exc_info=None,
    )
    record.request_id = "req-123"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "request complete"
    assert payload["request_id"] == "req-123"
    assert payload["timestamp"].endswith("+00:00")


def test_configure_logging_rejects_unknown_level():
    with pytest.raises(ValueError, match="Unsupported log level"):
        configure_logging(level="NOPE", json_output=True)
