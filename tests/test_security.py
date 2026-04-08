"""Unit tests for security helpers."""

import pytest

from security import oauth_email_allowed


@pytest.fixture(autouse=True)
def clear_k_service(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)


def test_oauth_allowlist_exact_match():
    assert oauth_email_allowed("A@Example.com", "a@example.com,other@test.org") is True
    assert oauth_email_allowed("evil@test.org", "a@example.com") is False


def test_oauth_production_requires_allowlist(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "svc")
    assert oauth_email_allowed("any@gmail.com", "") is False
    assert oauth_email_allowed("me@ok.com", "me@ok.com") is True


def test_oauth_dev_allows_any_when_allowlist_empty(monkeypatch):
    assert oauth_email_allowed("any@gmail.com", "") is True
