"""Pano çiziminin uç durumları: kaynak hataları, bozuk/eksik yanıtlar, uzun/kısa metinler, tarihler."""
from __future__ import annotations

import datetime as real_dt

import pytest
import requests

import home_display as hd
import local_data
from conftest import weather_payload

W, H = 600, 800
M = 20
HOSTS = {
    "Hava": "api.open-meteo.com",
    "Hava kalitesi": "air-quality-api.open-meteo.com",
    "Deniz": "marine-api.open-meteo.com",
    "Piyasa": "finans.truncgil.com",
    "Tatil": "date.nager.at",
    "Eczane": "nobetcieczane.org",
}


def assert_valid(img):
    assert img.size == (W, H)
    assert img.mode == "L"
    assert len(img.getcolors(256)) <= 16, "Kindle 4 en fazla 16 gri ton gösterir"


def assert_margins_clean(img, top=84):
    """Başlık şeridi dışında sol/sağ kenar boşluğuna hiçbir şey taşmamalı."""
    px = img.load()
    for y in range(top, H):
        for x in list(range(0, M - 3)) + list(range(W - M + 3, W)):
            assert px[x, y] > 200, f"kenara taşma: ({x}, {y}) = {px[x, y]}"


def text_of(img) -> int:
    """Görüntüdeki koyu piksel sayısı (boş mu dolu mu kıyası için)."""
    return sum(1 for v in img.get_flattened_data() if v < 128)


# ------------------------------------------------------------------ normal akış

def test_happy_path(net, frozen, cfg):
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_valid(img)
    assert_margins_clean(img)
    assert set(HOSTS.values()) <= set(net.calls)


def test_png_output_roundtrip(net, frozen, cfg, tmp_path):
    out = tmp_path / "display.png"
    assert hd.main(["x", str(out)]) == 0
    from PIL import Image
    im = Image.open(out)
    assert im.size == (W, H) and im.mode == "L"
    assert out.stat().st_size < 200_000


# ------------------------------------------------------------------ kaynak hataları

FAILURES = {
    "bağlantı": lambda n, h: n.raises.__setitem__(h, requests.ConnectionError("yok")),
    "zaman aşımı": lambda n, h: n.raises.__setitem__(h, requests.Timeout("yavaş")),
    "HTTP 500": lambda n, h: n.status.__setitem__(h, 500),
    "HTTP 429": lambda n, h: n.status.__setitem__(h, 429),
    "geçersiz JSON": lambda n, h: n.payloads.__setitem__(h, "<html>Just a moment...</html>"),
    "boş gövde": lambda n, h: n.payloads.__setitem__(h, ""),
    "boş nesne": lambda n, h: n.payloads.__setitem__(h, {}),
    "boş liste": lambda n, h: n.payloads.__setitem__(h, []),
    "null": lambda n, h: n.payloads.__setitem__(h, None),
}


@pytest.mark.parametrize("source", list(HOSTS))
@pytest.mark.parametrize("failure", list(FAILURES))
def test_single_source_failure_never_crashes(net, frozen, cfg, source, failure):
    FAILURES[failure](net, HOSTS[source])
    img, errors = hd.render_report(cfg)
    assert_valid(img)
    assert_margins_clean(img)
    # diğer kaynaklar etkilenmemeli
    assert all(e == source for e in errors), errors


def test_all_sources_down_is_not_published(net, frozen, tmp_path):
    for host in HOSTS.values():
        net.raises[host] = requests.ConnectionError("internet yok")
    out = tmp_path / "display.png"
    assert hd.main(["x", str(out)]) == 2
    assert not out.exists(), "ağ tamamen yokken eski pano ezilmemeli"


def test_partial_outage_is_published(net, frozen, tmp_path):
    for host in list(HOSTS.values())[:-1]:
        net.raises[host] = requests.ConnectionError("internet yok")
    out = tmp_path / "display.png"
    assert hd.main(["x", str(out)]) == 0
    assert out.exists()


def test_all_sources_down(net, frozen, cfg):
    for host in HOSTS.values():
        net.raises[host] = requests.ConnectionError("internet yok")
    img, errors = hd.render_report(cfg)
    assert_valid(img)
    assert_margins_clean(img)
    assert set(errors) == set(HOSTS)
    # yerel bölümler (tarih, mevsim ızgarası, pazar) yine de çizilmeli
    assert text_of(img) > 15_000


def test_error_footer_is_shown_and_fits(net, frozen, cfg):
    for host in HOSTS.values():
        net.status[host] = 503
    img, errors = hd.render_report(cfg)
    assert len(errors) == len(HOSTS)
    strip = img.crop((0, H - 22, W, H))
    assert text_of(strip) > 50, "hata satırı görünmeli"
    assert_margins_clean(img)


# ------------------------------------------------------------------ bozuk / eksik hava verisi

def _weather(net, mutate):
    w = weather_payload()
    mutate(w)
    net.payloads["api.open-meteo.com"] = w


@pytest.mark.parametrize("name,mutate", [
    ("daily eksik", lambda w: w.pop("daily")),
    ("current eksik", lambda w: w.pop("current")),
    ("2 günlük tahmin", lambda w: w.__setitem__("daily", weather_payload(2)["daily"])),
    ("0 günlük tahmin", lambda w: w.__setitem__("daily", weather_payload(0)["daily"])),
    ("7 günlük tahmin", lambda w: w.__setitem__("daily", weather_payload(7)["daily"])),
    ("sıcaklık null", lambda w: w["current"].__setitem__("temperature_2m", None)),
    ("hissedilen null", lambda w: w["current"].__setitem__("apparent_temperature", None)),
    ("nem null", lambda w: w["current"].__setitem__("relative_humidity_2m", None)),
    ("rüzgar yönü null", lambda w: w["current"].__setitem__("wind_direction_10m", None)),
    ("rüzgar yönü yok", lambda w: w["current"].pop("wind_direction_10m")),
    ("bilinmeyen hava kodu", lambda w: w["current"].__setitem__("weather_code", 999)),
    ("hava kodu null", lambda w: w["current"].__setitem__("weather_code", None)),
    ("is_day yok", lambda w: w["current"].pop("is_day")),
    ("UV null", lambda w: w["daily"].__setitem__("uv_index_max", [None] * 4)),
    ("yağış null", lambda w: w["daily"].__setitem__("precipitation_probability_max", [None] * 4)),
    ("max/min null", lambda w: w["daily"].__setitem__("temperature_2m_max", [None, 1, 2, 3])),
    ("gün doğumu bozuk", lambda w: w["daily"].__setitem__("sunrise", ["?"])),
    ("tarih bozuk", lambda w: w["daily"].__setitem__("time", ["dün", "bugün", "x", "y"])),
    ("liste yerine sayı", lambda w: w["daily"].__setitem__("weather_code", 5)),
])
def test_malformed_weather(net, frozen, cfg, name, mutate):
    _weather(net, mutate)
    img, errors = hd.render_report(cfg)
    assert_valid(img)
    assert_margins_clean(img)
    assert set(errors) <= {"Hava"}


@pytest.mark.parametrize("temp", [-25.4, -0.4, 0, 9.5, 45.6, 105])
@pytest.mark.parametrize("wind", [0, 3.3, 130.0])
def test_extreme_weather_values(net, frozen, cfg, temp, wind):
    _weather(net, lambda w: w["current"].update(temperature_2m=temp, apparent_temperature=temp - 12,
                                                  wind_speed_10m=wind, relative_humidity_2m=100))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


@pytest.mark.parametrize("code", sorted(set(hd.WMO) | {0, 1, 2, 3, 45, 48, 999}))
@pytest.mark.parametrize("is_day", [0, 1])
def test_every_weather_code_draws(net, frozen, cfg, code, is_day):
    _weather(net, lambda w: (w["current"].update(weather_code=code, is_day=is_day),
                             w["daily"].__setitem__("weather_code", [code] * 4)))
    img, errors = hd.render_report(cfg)
    assert errors == []


# ------------------------------------------------------------------ diğer kaynakların bozuk değerleri

@pytest.mark.parametrize("air", [
    {"current": {"european_aqi": None, "pm2_5": None}},
    {"current": {"european_aqi": 0, "pm2_5": 0}},
    {"current": {"european_aqi": 500, "pm2_5": 999.9}},
    {"current": {}},
    {"current": None},
])
def test_air_quality_edge(net, frozen, cfg, air):
    net.payloads["air-quality-api.open-meteo.com"] = air
    img, errors = hd.render_report(cfg)
    assert_margins_clean(img)
    assert set(errors) <= {"Hava kalitesi"}


@pytest.mark.parametrize("sea", [None, -1.5, 0, 31.94, "18.3"])
def test_sea_edge(net, frozen, cfg, sea):
    net.payloads["marine-api.open-meteo.com"] = {"current": {"sea_surface_temperature": sea}}
    img, errors = hd.render_report(cfg)
    assert_margins_clean(img)
    assert set(errors) <= {"Deniz"}


@pytest.mark.parametrize("fin", [
    {"USD": {"Satış": "49,60"}},                                     # yalnız dolar
    {"gram-altin": {"Satış": "6.593,87"}},                           # yalnız altın
    {"USD": {"Satış": "abc"}, "EUR": {"Satış": ""}, "gram-altin": {}},  # çöp değerler
    {"USD": {"Satış": "1.234.567,89"}, "EUR": {"Satış": "9.999.999,99"},
     "gram-altin": {"Satış": "123.456.789,00"}},                   # çok büyük sayılar
    {"USD": "49,60"},                                                # beklenmeyen tip
    {},
])
def test_finance_edge(net, frozen, cfg, fin):
    net.payloads["finans.truncgil.com"] = fin
    img, errors = hd.render_report(cfg)
    assert_margins_clean(img)
    assert set(errors) <= {"Piyasa"}


def test_tiles_all_disabled(net, frozen, cfg):
    for k in cfg["tiles"]:
        cfg["tiles"][k] = False
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert "finans.truncgil.com" not in net.calls
    assert "nobetcieczane.org" not in net.calls
    assert_margins_clean(img)


def test_missing_tiles_section(net, frozen, cfg):
    cfg.pop("tiles")
    img, errors = hd.render_report(cfg)
    assert errors == []


# ------------------------------------------------------------------ uzun / kısa metinler

def _pharm(name, semt="Erenköy", tel="0 (216) 357 22 52", lat="40.97", lon="29.08", nobetci="1"):
    return (f'<div class="pharm" data-pharm-card data-eczane-ad="{name}" data-eczane-telefon="{tel}" '
            f'data-eczane-lat="{lat}" data-eczane-lon="{lon}" data-eczane-semt="{semt}" '
            f'data-eczane-nobetci="{nobetci}">')


@pytest.mark.parametrize("html", [
    _pharm("Çok Uzun İsimli Sağlık ve Güzellik Ürünleri Bilimsel Danışmanlık Eczanesi " * 3),
    _pharm("A", semt="Ö" * 120, tel="0" * 80),
    _pharm("TekKelimeAmaÇokÇokÇokÇokÇokÇokÇokÇokÇokÇokUzunBirEczaneAdıDahaDaUzun"),
    _pharm(""),
    _pharm("X", semt="", tel=""),
    _pharm("Kısa", lat="", lon=""),
    _pharm("Kısa", lat="abc", lon="def"),
    _pharm("&amp;&quot;&lt;b&gt;Entity Eczanesi"),
    "",
    "<html>Sayfa tasarımı değişti</html>",
    _pharm("Nöbetçi değil", nobetci="0"),
])
def test_pharmacy_texts(net, frozen, cfg, html):
    net.payloads["nobetcieczane.org"] = html
    img, errors = hd.render_report(cfg)
    assert_valid(img)
    assert_margins_clean(img)
    assert set(errors) <= {"Eczane"}


@pytest.mark.parametrize("name", [
    "Ramazan Bayramı 1. Gün (Tentative Date)",
    "Ç" * 300,
    "Kurban Bayramı Arifesi ve Uzun Bir Açıklama " * 5,
    "",
])
def test_holiday_texts(net, frozen, cfg, name):
    net.payloads["date.nager.at"] = [{"date": "2026-10-29", "localName": name}]
    img, errors = hd.render_report(cfg)
    assert_margins_clean(img)
    assert errors == []


def test_holiday_today_and_tomorrow(net, frozen, cfg):
    for day in ("2026-10-21", "2026-10-22"):
        net.payloads["date.nager.at"] = [{"date": day, "localName": "Test"}]
        _, errors = hd.render_report(cfg)
        assert errors == []


def test_long_location_and_market_names(net, frozen, cfg, monkeypatch):
    cfg["location"]["name"] = "Erenköy Mahallesi · Kadıköy · İstanbul · Türkiye · Anadolu Yakası"
    cfg["location"]["sea_name"] = "Caddebostan Plajı Açıkları Kuzeybatı Bölgesi"
    monkeypatch.setattr(local_data, "PAZARLAR", [
        ("Çok Uzun İsimli Organik Üretici Halk Pazarı Pazarı", [2, 3], "x"),
        ("İkinci Uzun İsimli Mahalle Pazarı", [2, 3], "y"),
        ("Erenköy Pazarı", [3], "z"),
    ])
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


def test_long_product_names(net, frozen, cfg, monkeypatch):
    long = ["Çokuzunbirmeyveadıboşluksuz", "İki kelimeli uzun meyve adı burada", "A", "",
            "Trabzon hurması", "Elma"]
    monkeypatch.setitem(local_data.MEVSIM, 10, (long, long, long))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


def test_fewer_and_more_products(net, frozen, cfg, monkeypatch):
    monkeypatch.setitem(local_data.MEVSIM, 10, (["Nar"], [], ["Hamsi"] * 12))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


# ------------------------------------------------------------------ tarihler

@pytest.mark.parametrize("when", [
    (2026, 1, 1, 0, 0), (2026, 12, 31, 23, 59), (2028, 2, 29, 12, 0), (2026, 4, 14, 12, 0),
    (2026, 4, 15, 12, 0), (2026, 8, 31, 12, 0), (2026, 9, 1, 12, 0), (2026, 9, 14, 12, 0),
    (2026, 9, 15, 12, 0), (2026, 3, 29, 3, 30),  # yaz saati geçişi yok ama gece yarısı sonrası
])
def test_special_dates(net, cfg, monkeypatch, when):
    from conftest import freeze
    freeze(monkeypatch, real_dt.datetime(*when))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_valid(img)
    assert_margins_clean(img)


@pytest.mark.parametrize("month", range(1, 13))
@pytest.mark.parametrize("day", [1, 28])
def test_every_month(net, cfg, monkeypatch, month, day):
    from conftest import freeze
    freeze(monkeypatch, real_dt.datetime(2026, month, day, 9, 7))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


@pytest.mark.parametrize("offset", range(7))
def test_every_weekday(net, cfg, monkeypatch, offset):
    from conftest import freeze
    freeze(monkeypatch, real_dt.datetime(2026, 10, 19, 18, 7) + real_dt.timedelta(days=offset))
    img, errors = hd.render_report(cfg)
    assert errors == []
    assert_margins_clean(img)


def test_layout_fits_vertically_in_worst_case(net, frozen, cfg, monkeypatch):
    """En kalabalık gün: av yasağı notu + hata satırı + iki eczane + tatil + uzun pazar listesi."""
    from conftest import freeze
    freeze(monkeypatch, real_dt.datetime(2026, 4, 9, 12, 0))  # Perşembe, av yasağına 6 gün
    net.status["marine-api.open-meteo.com"] = 500
    img, errors = hd.render_report(cfg)
    assert errors == ["Deniz"]
    # tatil satırı sığmalı (en alttaki bilgi satırı hata satırının üstünde kalmalı)
    footer = img.crop((0, H - 22, W, H))
    above = img.crop((0, H - 50, W, H - 24))
    assert text_of(footer) > 30 and text_of(above) > 30
