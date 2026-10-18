"""Reserved test addresses never reach SMTP.

Test accounts and the synthetic signup monitor (scripts/synthetic_signup_check.py)
register @example.com addresses. Sending there earns only a hard bounce, and
enough bounces push real users' verification emails into spam.
"""
import pytest

from services.email_service import is_undeliverable_test_address


@pytest.mark.parametrize("address", [
    "synthetic-monitor-ab12@example.com", "probe@EXAMPLE.org", "a@sub.example.net",
    "x@foo.test", "y@bar.invalid", "z@localhost", "w@thing.example",
])
def test_reserved_test_addresses_are_not_emailed(address):
    assert is_undeliverable_test_address(address)


@pytest.mark.parametrize("address", ["someone@gmail.com", "doctor@example-clinic.com", "a@myexample.com", "b@test.in"])
def test_real_addresses_are_emailed(address):
    assert not is_undeliverable_test_address(address)


def test_the_send_path_skips_a_test_address(monkeypatch):
    import services.email_service as es
    opened = []
    monkeypatch.setattr(es.smtplib, "SMTP", lambda *a, **k: opened.append(a))
    monkeypatch.setattr(es.smtplib, "SMTP_SSL", lambda *a, **k: opened.append(a))
    monkeypatch.setattr(es.settings, "SMTP_USER", "u", raising=False)
    monkeypatch.setattr(es.settings, "SMTP_PASSWORD", "p", raising=False)
    es._send_email_sync("synthetic-monitor-1@example.com", "Verify", "<p>x</p>")
    assert opened == []
