"""Yardımcı fonksiyonlar, ayrıştırıcılar, yerel veriler ve ikonlar."""
from __future__ import annotations

import datetime as dt
import math

import pytest
from PIL import Image, ImageDraw

import home_display as hd
import icons
import local_data
from conftest import PHARM_HTML, weather_payload

LOC = {"latitude": 40.9736, "longitude": 29.0770, "sea_latitude": 40.955, "sea_longitude": 29.06}


# ------------------------------------------------------------------ sayı biçimleri

@pytest.mark.parametrize("raw,expected", [
    ("49,6032", 49.6032), ("6.593,87", 6593.87), ("1.234.567,89", 1234567.89),
    ("%0,31", 0.31), ("%-0,01", -0.01), (" 12,5 ", 12.5), ("42", 42.0), ("42.5", 42.5), (7, 7.0),
])
def test_tr_number(raw, expected):
    assert hd.tr_number(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", "abc", "1,2,3", None, "—"])
def test_tr_number_rejects_garbage(raw):
    with pytest.raises((ValueError, TypeError)):
        hd.tr_number(raw)


@pytest.mark.parametrize("x,digits,expected", [
    (49.6032, 2, "49,60"), (6593.87, 0, "6.594"), (1234567.891, 2, "1.234.567,89"),
    (0, 2, "0,00"), (-3.456, 1, "-3,5"), (0.3, 1, "0,3"),
])
def test_fmt_tr(x, digits, expected):
    assert hd.fmt_tr(x, digits) == expected


@pytest.mark.parametrize("raw,expected", [
    (1, 1.0), (2.5, 2.5), ("18.3", 18.3), (" -4 ", -4.0), (None, None), ("", None), ("abc", None),
    (True, None), (False, None), (float("nan"), None), (float("inf"), None), ([1], None), ({}, None),
])
def test_num(raw, expected):
    assert hd.num(raw) == expected


# ------------------------------------------------------------------ hava verisi ayrıştırma

def test_parse_weather_complete():
    w = hd.parse_weather(weather_payload())
    assert w["current"]["temp"] == 17.4
    assert len(w["days"]) == 4
    assert w["days"][0]["sunrise"] == "07:21" and w["days"][0]["sunset"] == "18:14"
    assert w["current"]["night"] is False


def test_parse_weather_caps_at_four_days():
    assert len(hd.parse_weather(weather_payload(7))["days"]) == 4


def test_parse_weather_requires_temperature():
    raw = weather_payload()
    raw["current"]["temperature_2m"] = None
    with pytest.raises(ValueError):
        hd.parse_weather(raw)


def test_parse_weather_skips_bad_days_and_short_columns():
    raw = weather_payload()
    raw["daily"]["time"][1] = "bozuk"
    raw["daily"]["weather_code"] = [1]          # diğer günler için kod yok
    w = hd.parse_weather(raw)
    assert [d["date"].day for d in w["days"]] == [21, 23, 24]
    assert w["days"][0]["code"] == 1 and w["days"][1]["code"] is None


@pytest.mark.parametrize("is_day,night", [(0, True), (1, False), ("0", True), (None, False)])
def test_parse_weather_night_flag(is_day, night):
    raw = weather_payload()
    raw["current"]["is_day"] = is_day
    assert hd.parse_weather(raw)["current"]["night"] is night


# ------------------------------------------------------------------ eczane ayrıştırma

class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def _pharm(monkeypatch, html, **kw):
    monkeypatch.setattr(hd.requests, "get", lambda *a, **k: _Resp(html))
    return hd.fetch_pharmacies(LOC, **kw)


def test_pharmacies_sorted_by_distance_and_limited(monkeypatch):
    out = _pharm(monkeypatch, PHARM_HTML)
    assert [e["ad"] for e in out] == ["Şaşkınbakkal Eczanesi", "Aile Eczanesi"]
    assert out[0]["km"] < out[1]["km"]
    assert len(_pharm(monkeypatch, PHARM_HTML, limit=5)) == 3


def test_pharmacy_distance_is_sane(monkeypatch):
    out = _pharm(monkeypatch, PHARM_HTML, limit=5)
    far = next(e for e in out if e["semt"] == "Moda")
    assert 8 < far["km"] < 12  # Erenköy–Moda kuş uçuşu ~10 km


def test_pharmacy_without_coordinates_goes_last(monkeypatch):
    html = PHARM_HTML + ('<div class="pharm" data-pharm-card data-eczane-ad="Koordinatsız" '
                         'data-eczane-nobetci="1">')
    out = _pharm(monkeypatch, html, limit=5)
    assert out[-1]["ad"] == "Koordinatsız" and out[-1]["km"] is None


def test_pharmacy_entities_decoded(monkeypatch):
    html = '<div class="pharm" data-pharm-card data-eczane-ad="Ali &amp; Veli Eczanesi" data-eczane-nobetci="1">'
    assert _pharm(monkeypatch, html)[0]["ad"] == "Ali & Veli Eczanesi"


def test_pharmacy_not_on_duty_filtered(monkeypatch):
    html = PHARM_HTML.replace('data-eczane-nobetci="1"', 'data-eczane-nobetci="0"', 1)
    assert "Şaşkınbakkal Eczanesi" not in [e["ad"] for e in _pharm(monkeypatch, html, limit=5)]


@pytest.mark.parametrize("html", ["", "<html>yeni tasarım</html>",
                                  '<div class="pharm" data-pharm-card data-eczane-nobetci="0">'])
def test_pharmacy_page_changed_is_reported(monkeypatch, html):
    with pytest.raises(ValueError):
        _pharm(monkeypatch, html)


# ------------------------------------------------------------------ tatil

def _holidays(monkeypatch, payload, today=dt.date(2026, 10, 21)):
    monkeypatch.setattr(hd, "get_json", lambda *a, **k: payload)
    return hd.fetch_next_holiday(today)


def test_holiday_skips_past_and_sorts(monkeypatch):
    payload = [{"date": "2027-01-01", "localName": "Yılbaşı"},
               {"date": "2026-10-01", "localName": "Geçmiş"},
               {"date": "2026-10-29", "localName": "Cumhuriyet Bayramı"}]
    assert _holidays(monkeypatch, payload) == (dt.date(2026, 10, 29), "Cumhuriyet Bayramı")


def test_holiday_strips_parentheses(monkeypatch):
    payload = [{"date": "2027-03-10", "localName": "Ramazan Bayramı 1. Gün (Tentative Date)"}]
    assert _holidays(monkeypatch, payload)[1] == "Ramazan Bayramı 1. Gün"


@pytest.mark.parametrize("payload,expected", [
    ([], None),
    ([{"date": "2026-01-01", "localName": "Geçmiş"}], None),
    ([{"date": "bozuk"}, {"localName": "tarihsiz"}, {"date": "2026-11-01", "localName": None}],
     (dt.date(2026, 11, 1), "Resmi tatil")),
    ([{"date": "2026-11-01", "localName": "", "name": "Holiday"}], (dt.date(2026, 11, 1), "Holiday")),
])
def test_holiday_edge(monkeypatch, payload, expected):
    assert _holidays(monkeypatch, payload) == expected


@pytest.mark.parametrize("payload", [{}, None, "metin"])
def test_holiday_wrong_type_raises(monkeypatch, payload):
    with pytest.raises(ValueError):
        _holidays(monkeypatch, payload)


# ------------------------------------------------------------------ kur

@pytest.mark.parametrize("payload,expected", [
    ({"USD": {"Satış": "49,60"}, "EUR": {"Satış": "55,73"}, "gram-altin": {"Satış": "6.593,87"}},
     {"USD": 49.60, "EUR": 55.73, "ALTIN": 6593.87}),
    ({"USD": {"Satış": "49,60"}, "EUR": {"Alış": "55"}}, {"USD": 49.60}),
])
def test_finance(monkeypatch, payload, expected):
    monkeypatch.setattr(hd, "get_json", lambda *a, **k: payload)
    assert hd.fetch_finance() == pytest.approx(expected)


@pytest.mark.parametrize("payload", [{}, {"USD": {"Satış": "yok"}}, {"USD": None}])
def test_finance_nothing_usable_raises(monkeypatch, payload):
    monkeypatch.setattr(hd, "get_json", lambda *a, **k: payload)
    with pytest.raises(ValueError):
        hd.fetch_finance()


# ------------------------------------------------------------------ metin yardımcıları

@pytest.fixture
def draw():
    return ImageDraw.Draw(Image.new("L", (10, 10)))


@pytest.mark.parametrize("text", ["", "a", "kısa metin", "çok " * 80, "x" * 500, "İĞÜŞÖÇ ığüşöç " * 20])
@pytest.mark.parametrize("width", [1, 30, 300])
def test_ellipsize_always_fits(draw, text, width):
    f = hd.font(16)
    out = hd.ellipsize(draw, text, f, width)
    if draw.textlength(text, font=f) <= width:
        assert out == text
    else:
        assert out.endswith("…")
        assert draw.textlength(out, font=f) <= max(width, draw.textlength("…", font=f))


@pytest.mark.parametrize("text", ["", "tek", "iki kelime", "Trabzon hurması", "a b c d e f g h", "  boşluklu  "])
def test_wrap_keeps_all_words(draw, text):
    lines = hd.wrap(draw, text, hd.font(13), 80)
    assert " ".join(lines).split() == text.split()


def test_tr_upper():
    assert hd.tr_upper("ekim") == "EKİM"
    assert hd.tr_upper("ağustos ılık") == "AĞUSTOS ILIK"
    assert hd.tr_upper("Mevsiminde") == "MEVSİMİNDE"


@pytest.mark.parametrize("deg", [0, 22.4, 22.6, 45, 90, 180, 225, 270, 315, 337.4, 337.6, 359.9, 360, 720, -45])
def test_wind_dir_total(deg):
    assert hd.wind_dir(deg) in {"Yıldız", "Poyraz", "Gündoğusu", "Keşişleme", "Kıble", "Lodos", "Günbatısı", "Karayel"}


def test_wind_dir_known():
    assert hd.wind_dir(0) == "Yıldız"
    assert hd.wind_dir(45) == "Poyraz"
    assert hd.wind_dir(225) == "Lodos"
    assert hd.wind_dir(-45) == "Karayel"


@pytest.mark.parametrize("aqi,label", [(0, "Çok iyi"), (20, "Çok iyi"), (20.1, "İyi"), (60, "Orta"),
                                       (80, "Kötü"), (100, "Çok kötü"), (101, "Tehlikeli"), (999, "Tehlikeli")])
def test_aqi_label(aqi, label):
    assert hd.aqi_label(aqi) == label


# ------------------------------------------------------------------ yerel veri

@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_has_six_unique_products(month):
    for items in local_data.MEVSIM[month]:
        assert len(items) == 6
        assert len(set(items)) == 6, items


def test_every_product_has_its_own_icon():
    """Mevsim listelerindeki her ürünün ya emoji karşılığı ya da özel çizimi olmalı (yedek ikona düşmemeli)."""
    for month, (meyve, sebze, balik) in local_data.MEVSIM.items():
        for name in meyve + sebze:
            assert name in icons.EMOJI or name in icons.CUSTOM, f"{month}. ay: {name} için ikon yok"
        for name in balik:
            assert name in icons.FISH, f"{month}. ay: {name} için balık çizimi yok"


def test_emoji_glyphs_exist_in_font():
    """Fontta olmayan bir emoji boş kutu (tofu) olarak çizilir; her emojinin gerçekten çizildiğini doğrula."""
    from PIL import ImageFont
    f = ImageFont.truetype(str(icons.FONT_DIR / "NotoEmoji.ttf"), 40)
    tofu = f.getmask("\U0010FFFD").getbbox()
    for name, ch in icons.EMOJI.items():
        mask = f.getmask(ch)
        assert mask.getbbox() is not None, name
        assert mask.getbbox() != tofu or bytes(mask) != bytes(f.getmask("\U0010FFFD")), name


@pytest.mark.parametrize("name,kind", [(n, "meyve") for n in icons.CUSTOM] + [(n, "balik") for n in icons.FISH]
                         + [(n, "sebze") for n in icons.EMOJI])
@pytest.mark.parametrize("px", [24, 50, 72])
def test_icon_renders_within_bounds(name, kind, px):
    img = icons.render_icon(name, kind, px)
    assert img.size == (px, px) and img.mode == "L"
    ink = sum(1 for v in img.get_flattened_data() if v < 128)
    assert ink > px * px * 0.04, f"{name} neredeyse boş"
    # ikon kenarlara yapışmamalı / kesilmemeli: en dış 1 piksellik çerçevenin büyük kısmı beyaz olmalı
    edge = [img.getpixel((x, 0)) for x in range(px)] + [img.getpixel((x, px - 1)) for x in range(px)]
    assert sum(1 for v in edge if v < 128) < px * 0.6, f"{name} kenardan taşıyor"


def test_unknown_icon_falls_back():
    assert icons.render_icon("Bilinmeyen meyve", "meyve", 40).size == (40, 40)
    assert icons.render_icon("Bilinmeyen balık", "balik", 40).size == (40, 40)
    assert icons.render_icon("", "sebze", 40).size == (40, 40)


def test_fish_species_look_different():
    imgs = {n: bytes(icons.render_icon(n, "balik", 48).get_flattened_data()) for n in icons.FISH}
    groups: dict[bytes, list[str]] = {}
    for n, b in imgs.items():
        groups.setdefault(b, []).append(n)
    same = [g for g in groups.values() if len(g) > 1]
    # Çinekop/Sarıkanat/Lüfer aynı balığın boyları; geri kalan türler birbirinden ayırt edilebilmeli
    assert all(set(g) <= {"Çinekop", "Sarıkanat", "Lüfer"} for g in same), same


@pytest.mark.parametrize("when,expected", [
    (dt.date(2026, 4, 1), "Av yasağına 14 gün"),
    (dt.date(2026, 4, 14), "Av yasağına 1 gün"),
    (dt.date(2026, 4, 15), "Av yasağı: 139 gün kaldı"),
    (dt.date(2026, 8, 31), "Av yasağı: 1 gün kaldı"),
    (dt.date(2026, 9, 1), "Av sezonu açıldı"),
    (dt.date(2026, 9, 14), "Av sezonu açıldı"),
    (dt.date(2026, 9, 15), ""),
    (dt.date(2026, 3, 31), ""),
    (dt.date(2026, 12, 31), ""),
    (dt.date(2028, 2, 29), ""),
])
def test_balik_notu(when, expected):
    assert local_data.balik_notu(when) == expected


def test_balik_notu_every_day_is_short():
    d = dt.date(2026, 1, 1)
    while d.year == 2026:
        assert len(local_data.balik_notu(d)) <= 26
        d += dt.timedelta(days=1)


@pytest.mark.parametrize("day,expected", [
    (dt.date(2026, 10, 19), ["Göztepe Pazarı"]),
    (dt.date(2026, 10, 20), ["Salı Pazarı"]),
    (dt.date(2026, 10, 21), ["Organik Halk Pazarı"]),
    (dt.date(2026, 10, 22), ["Erenköy Pazarı"]),
    (dt.date(2026, 10, 23), ["Kozyatağı Pazarı", "Salı Pazarı"]),
    (dt.date(2026, 10, 24), ["Sahrayıcedit Pazarı"]),
    (dt.date(2026, 10, 25), ["Koşuyolu Pazarı"]),
])
def test_pazarlar(day, expected):
    assert local_data.pazarlar(day) == expected


@pytest.mark.parametrize("day,expected", [
    # Gerçek ay evreleri (2026): yeni ay 18 Ocak, 10 Ekim; dolunay 3 Ocak, 26 Ekim
    (dt.date(2026, 1, 18), "Yeni ay"), (dt.date(2026, 10, 10), "Yeni ay"),
    (dt.date(2026, 1, 3), "Dolunay"), (dt.date(2026, 10, 26), "Dolunay"),
])
def test_ay_evresi_known_dates(day, expected):
    assert local_data.ay_evresi(day) == expected


def test_ay_evresi_every_day_defined():
    d = dt.date(2026, 1, 1)
    seen = set()
    while d.year < 2028:
        seen.add(local_data.ay_evresi(d))
        d += dt.timedelta(days=1)
    assert seen == {"Yeni ay", "Hilal", "İlk dördün", "Şişkin ay", "Dolunay", "Son dördün"}


def test_config_is_valid():
    cfg = hd.load_config()
    assert cfg["display"]["width"] == 600 and cfg["display"]["height"] == 800
    loc = cfg["location"]
    for k in ("latitude", "longitude", "sea_latitude", "sea_longitude"):
        assert isinstance(loc[k], float)
    assert math.dist((loc["latitude"], loc["longitude"]), (40.97, 29.08)) < 0.05, "konum Erenköy olmalı"
    assert "rotate" not in cfg["display"]


# ------------------------------------------------------------------ eczane konumu (Çelebi Sk.'ya göre)

@pytest.mark.parametrize("address,expected", [
    ("Sahrayıcedid Mah. Atatürk Cad. No:46/A", "Atatürk Cd."),
    ("OSMANAĞA MAH.MİSAKI MİLLİ CD. TALİMHANE SK.NO 5/B KADIKÖY", "Misakı Milli Cd."),
    ("ERENKÖY MAH. KANTARCI RIZA SOK. NO:18/C", "Kantarcı Rıza Sk."),
    ("19 Mayıs Mahallesi, Şemsettin Günaltay Caddesi No:188/B", "Şemsettin Günaltay Cd."),
    ("Koşuyolu Mahallesi, Alidede Sokak No:9/A", "Alidede Sk."),
    ("HASANPAŞA MAH. SÖĞÜTLÜÇEŞME CAD. NO:178/A", "Söğütlüçeşme Cd."),
    ("", ""), ("sadece metin", ""), ("No:5", ""),
])
def test_street_of(address, expected):
    assert hd.street_of(address) == expected


def test_tr_title():
    assert hd.tr_title("MİSAKI MİLLİ İNÖNÜ IŞIK") == "Misakı Milli İnönü Işık"


@pytest.mark.parametrize("dlat,dlon,arrow", [
    (0.01, 0, "↑"), (-0.01, 0, "↓"), (0, 0.01, "→"), (0, -0.01, "←"),
    (0.007, 0.009, "↗"), (-0.007, -0.009, "↙"),
])
def test_distance_bearing_directions(dlat, dlon, arrow):
    km, a = hd.distance_bearing(40.97016, 29.08219, 40.97016 + dlat, 29.08219 + dlon)
    assert a == arrow and km > 0


def test_distance_bearing_known():
    # Çelebi Sk. -> Aile Eczanesi (Sahrayıcedit) ~1,2 km kuzey
    km, a = hd.distance_bearing(40.97016, 29.08219, 40.981181, 29.084487)
    assert 1.1 < km < 1.35 and a == "↑"


@pytest.mark.parametrize("km,text", [(0.0001, "10 m"), (0.183, "180 m"), (0.996, "1000 m"), (1.0, "1,0 km"),
                                     (1.234, "1,2 km"), (12.0, "12,0 km")])
def test_fmt_distance(km, text):
    assert hd.fmt_distance(km) == text


def test_pharmacies_measured_from_home_not_weather_point(monkeypatch):
    loc = dict(LOC, home_latitude=41.05, home_longitude=29.00)  # Moda tarafı
    monkeypatch.setattr(hd.requests, "get", lambda *a, **k: _Resp(PHARM_HTML))
    out = hd.fetch_pharmacies(loc, limit=3)
    assert out[0]["semt"] == "Moda", "en yakın eczane ev konumuna göre seçilmeli"
    assert out[0]["sokak"] == "" and out[1]["sokak"] in ("Ethem Efendi Cd.", "Atatürk Cd.")


def test_config_has_celebi_home():
    loc = hd.load_config()["location"]
    assert loc["home_name"] == "Çelebi Sk."
    assert hd.distance_bearing(loc["home_latitude"], loc["home_longitude"], 40.9736, 29.0770)[0] < 1
