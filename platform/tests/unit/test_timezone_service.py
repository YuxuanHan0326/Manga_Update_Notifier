from __future__ import annotations

from app.services import timezone as tzsvc


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


def test_detect_timezone_from_public_ip_uses_ip_lookup_only(monkeypatch):
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_api_url_template", "https://ip.example/{ip}")
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_self_api_url", "https://self.example/json")
    calls: list[str] = []

    def _fake_get(url: str, timeout: float):
        _ = timeout
        calls.append(url)
        return _FakeResponse({"timezone": "Europe/London"})

    monkeypatch.setattr(tzsvc.httpx, "get", _fake_get)

    out = tzsvc.detect_timezone_from_ip("8.8.8.8")
    assert out == "Europe/London"
    assert calls == ["https://ip.example/8.8.8.8"]


def test_detect_timezone_private_ip_falls_back_to_self_lookup(monkeypatch):
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_api_url_template", "https://ip.example/{ip}")
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_self_api_url", "https://self.example/json")
    calls: list[str] = []

    def _fake_get(url: str, timeout: float):
        _ = timeout
        calls.append(url)
        return _FakeResponse({"timezone": "Europe/London"})

    monkeypatch.setattr(tzsvc.httpx, "get", _fake_get)

    out = tzsvc.detect_timezone_from_ip("192.168.1.8")
    assert out == "Europe/London"
    assert calls == ["https://self.example/json"]


def test_detect_timezone_falls_back_when_public_lookup_fails(monkeypatch):
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_api_url_template", "https://ip.example/{ip}")
    monkeypatch.setattr(tzsvc.settings, "ip_timezone_self_api_url", "https://self.example/json")
    calls: list[str] = []

    def _fake_get(url: str, timeout: float):
        _ = timeout
        calls.append(url)
        if "ip.example" in url:
            raise RuntimeError("simulated upstream failure")
        return _FakeResponse({"timezone": "Europe/London"})

    monkeypatch.setattr(tzsvc.httpx, "get", _fake_get)

    out = tzsvc.detect_timezone_from_ip("8.8.8.8")
    assert out == "Europe/London"
    assert calls == ["https://ip.example/8.8.8.8", "https://self.example/json"]
