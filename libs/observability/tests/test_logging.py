from __future__ import annotations

import json

import pytest
import structlog

from sa_observability.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    structlog.reset_defaults()


def test_json_logging__adds_context_and_redacts(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(service="offer-service", env="prod")
    get_logger().info("offer_price_updated", offer_id="01J", password="hunter2")

    line = capsys.readouterr().out.strip()
    record = json.loads(line)
    assert record["event"] == "offer_price_updated"
    assert record["service"] == "offer-service"
    assert record["env"] == "prod"
    assert record["level"] == "info"
    assert "timestamp" in record
    assert record["offer_id"] == "01J"
    assert record["password"] == "«redacted»"


def test_dev_logging__is_console_and_hides_secret(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(service="catalog", env="dev")
    get_logger().info("auth_ok", sid="gpkavk4s0aciujg6m698gev040")

    out = capsys.readouterr().out
    assert "gpkavk4s0aciujg6m698gev040" not in out
    assert "«redacted»" in out


def test_no_trace_context_outside_span(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(service="catalog", env="prod")
    get_logger().info("noop")
    record = json.loads(capsys.readouterr().out.strip())
    assert "trace_id" not in record
