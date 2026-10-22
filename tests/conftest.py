"""Ortak test düzeneği: ağ çağrıları sahte yanıtlarla değiştirilir, gerçek ağa çıkılmaz."""
from __future__ import annotations

import copy
import datetime as real_dt
import json
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import home_display as hd  # noqa: E402


def weather_payload(days: int = 4) -> dict:
    base = real_dt.date(2026, 10, 21)
    return {
        "current": {"temperature_2m": 17.4, "apparent_temperature": 16.2, "relative_humidity_2m": 72,
                    "weather_code": 2, "wind_speed_10m": 14.0, "wind_direction_10m": 30, "is_day": 1},
        "daily": {
            "time": [(base + real_dt.timedelta(days=i)).isoformat() for i in range(days)],
            "weather_code": [2, 61, 0, 73][:days] + [3] * max(0, days - 4),
            "temperature_2m_max": [19, 16, 21, 8][:days] + [10] * max(0, days - 4),
            "temperature_2m_min": [12, 11, 13, 2][:days] + [5] * max(0, days - 4),
            "precipitation_probability_max": [10, 80, 0, 60][:days] + [0] * max(0, days - 4),
            "sunrise": [f"{(base + real_dt.timedelta(days=i)).isoformat()}T07:21" for i in range(days)],
            "sunset": [f"{(base + real_dt.timedelta(days=i)).isoformat()}T18:14" for i in range(days)],
            "uv_index_max": [3.4, 2.0, 4.1, 1.0][:days] + [1.0] * max(0, days - 4),
        },
    }


PHARM_HTML = """
<div class="pharmacy-list">
<div class="pharm" role="button" tabindex="0"
     data-pharm-card
     data-eczane-ad="Şaşkınbakkal Eczanesi"
     data-eczane-adres="Erenköy Mah. Ethem Efendi Cad. No:84/A"
     data-eczane-telefon="0 (216) 357 22 52"
     data-eczane-lat="40.9700" data-eczane-lon="29.0800"
     data-eczane-semt="Erenköy" data-eczane-nobetci="1">
<div class="pharm" role="button" tabindex="0"
     data-pharm-card
     data-eczane-ad="Aile Eczanesi"
     data-eczane-adres="Sahrayıcedid Mah. Atatürk Cad. No:46/A"
     data-eczane-telefon="0 (216) 759 55 31"
     data-eczane-lat="40.981181" data-eczane-lon="29.084487"
     data-eczane-semt="Sahrayıcedit" data-eczane-nobetci="1">
<div class="pharm" role="button" tabindex="0"
     data-pharm-card
     data-eczane-ad="Uzak Eczanesi"
     data-eczane-telefon="0 (216) 111 11 11"
     data-eczane-lat="41.05" data-eczane-lon="29.00"
     data-eczane-semt="Moda" data-eczane-nobetci="1">
"""


def default_payloads() -> dict:
    return {
        "api.open-meteo.com": weather_payload(),
        "air-quality-api.open-meteo.com": {"current": {"european_aqi": 70, "pm2_5": 40.0, "pm10": 49.6}},
        "marine-api.open-meteo.com": {"current": {"sea_surface_temperature": 18.3}},
        "finans.truncgil.com": {"USD": {"Satış": "49,6032"}, "EUR": {"Satış": "55,7364"},
                                "gram-altin": {"Satış": "6.593,87"}},
        "date.nager.at": [{"date": "2026-10-29", "localName": "Cumhuriyet Bayramı"},
                          {"date": "2027-01-01", "localName": "Yılbaşı"}],
        "nobetcieczane.org": PHARM_HTML,
    }


class FakeResponse:
    def __init__(self, body, status: int = 200):
        self.status_code = status
        self._body = body
        self.text = body if isinstance(body, str) else json.dumps(body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def json(self):
        if isinstance(self._body, str):
            return json.loads(self._body)  # geçersizse ValueError
        return copy.deepcopy(self._body)


class FakeNet:
    """Ana bilgisayar adına göre yanıt döndüren sahte requests.get."""

    def __init__(self):
        self.payloads = default_payloads()
        self.status: dict[str, int] = {}
        self.raises: dict[str, Exception] = {}
        self.fail_times: dict[str, int] = {}
        self.calls: list[str] = []

    def get(self, url, params=None, headers=None, timeout=None):
        assert timeout, "her istek zaman aşımıyla yapılmalı"
        host = url.split("/")[2]
        self.calls.append(host)
        if host in self.fail_times and self.fail_times[host] > 0:
            self.fail_times[host] -= 1
            raise requests.ConnectionError("geçici kopma")
        if host in self.raises:
            raise self.raises[host]
        if host not in self.payloads:
            raise requests.ConnectionError(f"bilinmeyen sunucu {host}")
        return FakeResponse(self.payloads[host], self.status.get(host, 200))


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    """Testlerde yeniden denemeler beklemeden yapılır."""
    monkeypatch.setattr(hd, "RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(hd.time, "sleep", lambda s: None)


@pytest.fixture
def net(monkeypatch):
    fake = FakeNet()
    monkeypatch.setattr(hd.requests, "get", fake.get)
    return fake


def freeze(monkeypatch, when: real_dt.datetime):
    class FrozenDT(real_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return when.replace(tzinfo=tz) if tz else when

    monkeypatch.setattr(hd.dt, "datetime", FrozenDT)


@pytest.fixture
def frozen(monkeypatch):
    def _f(y, m, d, hh=12, mm=0):
        freeze(monkeypatch, real_dt.datetime(y, m, d, hh, mm))
    _f(2026, 10, 21)
    return _f


@pytest.fixture
def cfg():
    return hd.load_config()
