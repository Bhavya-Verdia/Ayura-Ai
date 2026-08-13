"""
Transport-level regression tests for outbound email.

Production sent nothing for an unknown period and logged no error at all:
DigitalOcean blocks outbound 25/465/587 on the droplet, and smtplib was given no
timeout, so the background task parked in connect() forever. Registration logged
"Verification email scheduled" and then silence — no success line, no exception.

These cover the two decisions that failure turned on. Nothing here opens a socket.
"""
from unittest.mock import MagicMock, patch

import pytest

from services import email_service as es


@pytest.mark.parametrize("port", sorted(es.IMPLICIT_TLS_PORTS))
def test_implicit_tls_ports_do_not_call_starttls(port, monkeypatch):
    """2465 is 465's alternate and speaks TLS immediately. Choosing the mode on
    `port == 465` alone sent STARTTLS to it, which it will never answer."""
    monkeypatch.setattr(es.settings, "SMTP_PORT", port)
    monkeypatch.setattr(es.settings, "SMTP_USER", "resend")
    monkeypatch.setattr(es.settings, "SMTP_PASSWORD", "key")

    with patch.object(es.smtplib, "SMTP_SSL") as ssl_cls, patch.object(es.smtplib, "SMTP") as plain_cls:
        ssl_cls.return_value.__enter__.return_value = MagicMock()
        es._send_email_sync("someone@example.com", "s", "<p>b</p>")

    assert ssl_cls.called, f"port {port} must use implicit TLS"
    assert not plain_cls.called
    assert ssl_cls.call_args.kwargs["timeout"] == es.SMTP_TIMEOUT_SECONDS


@pytest.mark.parametrize("port", [587, 2587])
def test_submission_ports_negotiate_starttls(port, monkeypatch):
    monkeypatch.setattr(es.settings, "SMTP_PORT", port)
    monkeypatch.setattr(es.settings, "SMTP_USER", "resend")
    monkeypatch.setattr(es.settings, "SMTP_PASSWORD", "key")

    with patch.object(es.smtplib, "SMTP") as plain_cls, patch.object(es.smtplib, "SMTP_SSL") as ssl_cls:
        server = plain_cls.return_value.__enter__.return_value
        es._send_email_sync("someone@example.com", "s", "<p>b</p>")

    assert plain_cls.called and not ssl_cls.called
    server.starttls.assert_called_once()
    assert plain_cls.call_args.kwargs["timeout"] == es.SMTP_TIMEOUT_SECONDS


def test_every_send_path_carries_a_timeout(monkeypatch):
    """A blocked port must surface as a logged failure, not a parked thread."""
    assert es.SMTP_TIMEOUT_SECONDS > 0


def test_a_transport_failure_is_logged_not_swallowed_silently(monkeypatch, caplog):
    monkeypatch.setattr(es.settings, "SMTP_PORT", 2465)
    monkeypatch.setattr(es.settings, "SMTP_USER", "resend")
    monkeypatch.setattr(es.settings, "SMTP_PASSWORD", "key")

    with patch.object(es.smtplib, "SMTP_SSL", side_effect=TimeoutError("timed out")):
        with caplog.at_level("ERROR"):
            es._send_email_sync("someone@example.com", "s", "<p>b</p>")

    logged = " ".join(r.message for r in caplog.records)
    assert "someone@example.com" in logged
    assert "TimeoutError" in logged, "the failure type must reach the log"
    assert "2465" in logged, "the port must reach the log — it was the cause"
