#!/usr/bin/env python3
"""Kindle 4 (600x800, 16 gri ton) için Erenköy / Kadıköy ev panosu PNG'si üretir.

GitHub Actions günde 6 kez çalıştırır:
    python3 home_display.py out.png
"""
from __future__ import annotations

import datetime as dt
import io
import math
import re
import sys
import time
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

import icons
import local_data

BASE_DIR = Path(__file__).resolve().parent
HTTP_TIMEOUT = 15
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) home_display/1.0"}

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
GUN_KISA = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# WMO hava durumu kodları (Open-Meteo)
WMO = {
    0: "Açık", 1: "Çoğunlukla açık", 2: "Parçalı bulutlu", 3: "Kapalı",
    45: "Sisli", 48: "Kırağılı sis", 51: "Hafif çisenti", 53: "Çisenti",
    55: "Yoğun çisenti", 56: "Donan çisenti", 57: "Donan çisenti",
    61: "Hafif yağmur", 63: "Yağmur", 65: "Kuvvetli yağmur",
    66: "Donan yağmur", 67: "Donan yağmur", 71: "Hafif kar", 73: "Kar",
    75: "Yoğun kar", 77: "Kar taneleri", 80: "Sağanak", 81: "Sağanak",
    82: "Şiddetli sağanak", 85: "Kar sağanağı", 86: "Kar sağanağı",
    95: "Gök gürültülü", 96: "Dolulu fırtına", 99: "Dolulu fırtına",
}


def load_config() -> dict:
    with (BASE_DIR / "config.toml").open("rb") as f:
        return tomllib.load(f)


# Geçici hatalarda (bağlantı kopması, zaman aşımı, 429/5xx) bekleyip yeniden denenir
RETRY_DELAYS = (2, 5)


def http_get(url: str, **params) -> requests.Response:
    for attempt, delay in enumerate((*RETRY_DELAYS, None)):
        try:
            r = requests.get(url, params=params or None, headers=UA, timeout=HTTP_TIMEOUT)
            if r.status_code == 429 or r.status_code >= 500:
                r.raise_for_status()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            if delay is None:
                raise
            print(f"[yeniden deneme {attempt + 1}] {url.split('/')[2]}: {e!r}", file=sys.stderr)
            time.sleep(delay)
            continue
        r.raise_for_status()
        return r
    raise AssertionError("ulaşılamaz")


def get_json(url: str, **params) -> dict | list:
    return http_get(url, **params).json()


def tr_number(s: str) -> float:
    """'49,6032' veya '5.712,34' biçimindeki Türkçe sayıları çevirir."""
    s = str(s).strip().replace("%", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def fmt_tr(x: float, digits: int = 2) -> str:
    s = f"{x:,.{digits}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- veri

def num(v) -> float | None:
    """API'den gelen değeri sayıya çevirir; null, boş, bool ya da bozuk değerler için None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        try:
            f = float(v.strip())
        except ValueError:
            return None
        return f if math.isfinite(f) else None
    return None


def _col(daily: dict, key: str, i: int):
    v = daily.get(key)
    return v[i] if isinstance(v, list) and i < len(v) else None


def _hhmm(v) -> str | None:
    m = re.search(r"T(\d{2}:\d{2})", v) if isinstance(v, str) else None
    return m.group(1) if m else None


def parse_weather(raw: dict) -> dict:
    """Open-Meteo yanıtını doğrulayıp sade bir yapıya çevirir. Anlık sıcaklık yoksa hata verir."""
    cur = raw["current"]
    temp = num(cur.get("temperature_2m"))
    if temp is None:
        raise ValueError("anlık sıcaklık yok")
    code = num(cur.get("weather_code"))
    current = {
        "temp": temp,
        "feels": num(cur.get("apparent_temperature")),
        "humidity": num(cur.get("relative_humidity_2m")),
        "code": int(code) if code is not None else None,
        "wind": num(cur.get("wind_speed_10m")),
        "wind_dir": num(cur.get("wind_direction_10m")),
        "night": cur.get("is_day", 1) in (0, "0", False),
    }
    daily = raw.get("daily") if isinstance(raw.get("daily"), dict) else {}
    times = daily.get("time") if isinstance(daily.get("time"), list) else []
    days = []
    for i, t in enumerate(times):
        try:
            day = dt.date.fromisoformat(t)
        except (TypeError, ValueError):
            continue
        dcode = num(_col(daily, "weather_code", i))
        days.append({
            "date": day,
            "code": int(dcode) if dcode is not None else None,
            "tmax": num(_col(daily, "temperature_2m_max", i)),
            "tmin": num(_col(daily, "temperature_2m_min", i)),
            "rain": num(_col(daily, "precipitation_probability_max", i)),
            "uv": num(_col(daily, "uv_index_max", i)),
            "sunrise": _hhmm(_col(daily, "sunrise", i)),
            "sunset": _hhmm(_col(daily, "sunset", i)),
        })
    return {"current": current, "days": days[:4]}


def fetch_weather(loc: dict) -> dict:
    return parse_weather(get_json(
        "https://api.open-meteo.com/v1/forecast",
        latitude=loc["latitude"], longitude=loc["longitude"],
        current="temperature_2m,apparent_temperature,relative_humidity_2m,"
                "weather_code,wind_speed_10m,wind_direction_10m,is_day",
        daily="weather_code,temperature_2m_max,temperature_2m_min,"
              "precipitation_probability_max,sunrise,sunset,uv_index_max",
        timezone="Europe/Istanbul", forecast_days=4,
    ))


def fetch_air(loc: dict) -> dict:
    cur = get_json(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        latitude=loc["latitude"], longitude=loc["longitude"],
        current="european_aqi,pm2_5,pm10", timezone="Europe/Istanbul",
    )["current"]
    aqi = num(cur.get("european_aqi"))
    if aqi is None:
        raise ValueError("hava kalitesi indeksi yok")
    return {"aqi": aqi, "pm2_5": num(cur.get("pm2_5"))}


def fetch_sea(loc: dict) -> float:
    cur = get_json(
        "https://marine-api.open-meteo.com/v1/marine",
        latitude=loc["sea_latitude"], longitude=loc["sea_longitude"],
        current="sea_surface_temperature",
    )["current"]
    t = num(cur.get("sea_surface_temperature"))
    if t is None:
        raise ValueError("deniz suyu sıcaklığı yok")
    return t


def fetch_finance() -> dict[str, float]:
    d = get_json("https://finans.truncgil.com/today.json")
    out = {}
    for key, label in (("USD", "USD"), ("EUR", "EUR"), ("gram-altin", "ALTIN")):
        try:
            out[label] = tr_number(d[key]["Satış"])
        except (KeyError, ValueError, TypeError):
            pass
    if not out:
        raise ValueError("kur/altın verisi yok")
    return out


def fetch_next_holiday(today: dt.date) -> tuple[dt.date, str] | None:
    holidays = get_json("https://date.nager.at/api/v3/NextPublicHolidays/TR")
    if not isinstance(holidays, list):
        raise ValueError("tatil listesi bekleniyordu")
    for h in sorted(holidays, key=lambda h: str(h.get("date", ""))):
        try:
            day = dt.date.fromisoformat(h["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if day >= today:
            name = re.sub(r"\s*\(.*?\)", "", str(h.get("localName") or h.get("name") or "")).strip()
            return day, name or "Resmi tatil"
    return None


def tr_title(text: str) -> str:
    """'MİSAKI MİLLİ CD.' -> 'Misakı Milli Cd.' (Türkçe i/ı kurallarıyla)."""
    low = text.replace("I", "ı").replace("İ", "i").lower()
    return " ".join(w[:1].replace("i", "İ").replace("ı", "I").upper() + w[1:] for w in low.split())


def street_of(address: str) -> str:
    """Adresten cadde/sokak adını çıkarır ve kısaltır: 'Sahrayıcedid Mah. Atatürk Cad. No:46/A' -> 'Atatürk Cd.'"""
    a = re.sub(r"(?i)\bno\s*:.*$", "", address or "")
    a = re.sub(r"(?i)^.*?\bmah(?:allesi|\.)\s*", "", a)
    a = a.lstrip(" ,.").split(",")[0].strip(" .")
    m = re.search(r"(?i)^(.*?\b(?:cad(?:desi)?|cd|sok(?:ağı|ak)?|sk|bulvarı|blv))\.?(?:\s|$)", a)
    if not m:
        return ""
    street = tr_title(m.group(1))
    street = re.sub(r"(?i)\s+(caddesi|cad|cd)$", " Cd.", street)
    street = re.sub(r"(?i)\s+(sokağı|sokak|sok|sk)$", " Sk.", street)
    street = re.sub(r"(?i)\s+(bulvarı|blv)$", " Bulv.", street)
    return street


ARROWS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]  # kuzey yukarıda


def distance_bearing(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, str]:
    dy = (lat - lat0) * 111.0
    dx = (lon - lon0) * 111.0 * math.cos(math.radians(lat0))
    deg = math.degrees(math.atan2(dx, dy)) % 360
    return math.hypot(dx, dy), ARROWS[int((deg + 22.5) % 360 // 45)]


def fmt_distance(km: float) -> str:
    return f"{max(10, round(km * 100) * 10)} m" if km < 1 else f"{fmt_tr(km, 1)} km"


def fetch_pharmacies(loc: dict, limit: int = 2) -> list[dict]:
    """Kadıköy nöbetçi eczaneleri (nobetcieczane.org), evin (Çelebi Sk.) yakınından uzağa sıralı."""
    import html as htmllib
    home = (loc.get("home_latitude", loc["latitude"]), loc.get("home_longitude", loc["longitude"]))
    r = http_get("https://nobetcieczane.org/istanbul/kadikoy")
    cards = re.findall(r"<div class=\"pharm\"[^>]*data-pharm-card(.*?)>", r.text, re.S)
    if not cards:
        # Kadıköy'de her gün nöbetçi eczane vardır; hiç kart yoksa sayfa yapısı değişmiştir
        raise ValueError("eczane kartı bulunamadı (site tasarımı değişmiş olabilir)")
    out = []
    for card in cards:
        attrs = {k: htmllib.unescape(v) for k, v in re.findall(r'data-eczane-([a-z-]+)="([^"]*)"', card)}
        if attrs.get("nobetci") != "1":
            continue
        km = arrow = None
        try:
            km, arrow = distance_bearing(*home, float(attrs["lat"]), float(attrs["lon"]))
        except (KeyError, ValueError):
            pass
        out.append({"ad": attrs.get("ad", ""), "semt": attrs.get("semt", ""),
                    "tel": attrs.get("telefon", ""), "km": km, "yon": arrow,
                    "sokak": street_of(attrs.get("adres", "")),
                    "baslangic": attrs.get("baslangic", "")})
    if not out:
        raise ValueError("nöbetçi işaretli eczane yok")
    out.sort(key=lambda e: e["km"] if e["km"] is not None else 99)
    return out[:limit]


# ---------------------------------------------------------------- çizim yardımcıları

_FONTS: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _FONTS:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for d in (BASE_DIR / "fonts", Path("/usr/share/fonts/truetype/dejavu")):
            if (d / name).exists():
                _FONTS[key] = ImageFont.truetype(str(d / name), size)
                break
        else:
            _FONTS[key] = ImageFont.load_default(size)
    return _FONTS[key]


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split(" "):
        test = f"{cur} {word}".strip()
        if draw.textlength(test, font=f) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def ellipsize(draw, text: str, f, width: int) -> str:
    if draw.textlength(text, font=f) <= width:
        return text
    while text and draw.textlength(text + "…", font=f) > width:
        text = text[:-1]
    return text + "…"


def weather_icon(draw: ImageDraw.ImageDraw, code: int, x: float, y: float, s: float,
                 night: bool = False) -> None:
    lw = max(2, int(s // 25))

    if night and code in (0, 1):
        r = s * 0.28
        cx, cy = x + s / 2, y + s / 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
        draw.ellipse([cx - r * 0.45, cy - r * 1.1, cx + r * 1.35, cy + r * 0.7], fill=255)
        return

    def sun(cx, cy, r):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=lw)
        for i in range(8):
            a = i * math.pi / 4
            draw.line([cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35,
                       cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75], fill=0, width=lw)

    def cloud(cx, cy, w, fill=255):
        parts = [(cx - w * 0.3, cy, w * 0.25), (cx, cy - w * 0.16, w * 0.3), (cx + w * 0.3, cy, w * 0.22)]
        for px, py, r in parts:
            draw.ellipse([px - r, py - r, px + r, py + r], fill=fill, outline=0, width=lw)
        draw.rectangle([cx - w * 0.3, cy - 2, cx + w * 0.3, cy + w * 0.2], fill=fill)
        draw.line([cx - w * 0.3, cy + w * 0.22, cx + w * 0.3, cy + w * 0.22], fill=0, width=lw)
        for px, py, r in parts:
            draw.ellipse([px - r + lw + 1, py - r + lw + 1, px + r - lw - 1, py + r - lw - 1], fill=fill)
        draw.rectangle([cx - w * 0.3 + 2, cy, cx + w * 0.3 - 2, cy + w * 0.2], fill=fill)

    c = s / 2
    if code in (0, 1):
        sun(x + c, y + c, s * 0.25)
    elif code == 2:
        sun(x + c * 1.3, y + c * 0.7, s * 0.18)
        cloud(x + c * 0.9, y + c * 1.15, s * 0.8)
    elif code in (45, 48):
        for i in range(4):
            yy = y + s * (0.3 + i * 0.13)
            draw.line([x + s * 0.15, yy, x + s * 0.85, yy], fill=0, width=lw)
    else:
        cloud(x + c, y + c * 0.85, s * 0.9, fill=255 if code == 3 else 200)
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            for i in range(3):
                xx = x + s * (0.3 + i * 0.2)
                draw.line([xx, y + s * 0.78, xx - s * 0.06, y + s * 0.95], fill=0, width=lw)
        elif code in (71, 73, 75, 77, 85, 86):
            for i in range(3):
                draw.text((x + s * (0.3 + i * 0.2), y + s * 0.86), "*",
                          font=font(max(12, int(s // 5)), True), fill=0, anchor="mm")
        elif code >= 95:
            draw.line([x + s * 0.5, y + s * 0.72, x + s * 0.42, y + s * 0.86,
                       x + s * 0.55, y + s * 0.86, x + s * 0.47, y + s * 0.99], fill=0, width=lw)


def tr_upper(text: str) -> str:
    return text.replace("i", "İ").replace("ı", "I").upper()


def aqi_label(aqi: float) -> str:
    for limit, name in ((20, "Çok iyi"), (40, "İyi"), (60, "Orta"), (80, "Kötü"), (100, "Çok kötü")):
        if aqi <= limit:
            return name
    return "Tehlikeli"


def wind_dir(deg: float) -> str:
    # Rüzgarın geldiği yön, İstanbul'daki yerel adlarıyla
    names = ["Yıldız", "Poyraz", "Gündoğusu", "Keşişleme", "Kıble", "Lodos", "Günbatısı", "Karayel"]
    return names[int((deg + 22.5) % 360 // 45)]


# ---------------------------------------------------------------- pano

def render_report(cfg: dict) -> tuple[Image.Image, list[str]]:
    """Panoyu çizer; görüntüyü ve alınamayan kaynakların listesini döndürür.

    Her veri kaynağı ve her bölüm ayrı korunur: biri bozulsa da pano çizilir,
    sorunlu kaynağın adı en alttaki "Alınamadı" satırına yazılır.
    """
    dcfg, loc = cfg["display"], cfg["location"]
    tz = ZoneInfo(dcfg.get("timezone", "Europe/Istanbul"))
    now = dt.datetime.now(tz)
    today = now.date()
    W, H = dcfg.get("width", 600), dcfg.get("height", 800)
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    M = 20
    CW = W - 2 * M
    errors: list[str] = []

    def fail(name: str, e: Exception) -> None:
        if name not in errors:
            errors.append(name)
        print(f"[uyarı] {name}: {e!r}", file=sys.stderr)

    def safe(name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001 - bir kaynak düşse de pano çizilsin
            fail(name, e)
            return None

    tiles_cfg = cfg.get("tiles", {})
    weather = safe("Hava", fetch_weather, loc)
    air = safe("Hava kalitesi", fetch_air, loc) if tiles_cfg.get("air", True) else None
    sea = safe("Deniz", fetch_sea, loc) if tiles_cfg.get("sea", True) else None
    fin = safe("Piyasa", fetch_finance) if tiles_cfg.get("finance", True) else None
    holiday = safe("Tatil", fetch_next_holiday, today)
    pharmacies = safe("Eczane", fetch_pharmacies, loc) if tiles_cfg.get("pharmacy", True) else None
    days = weather["days"] if weather else []

    def deg(v) -> str:
        return "–" if v is None else f"{round(v)}°"

    # --- başlık
    d.rectangle([0, 0, W, 82], fill=0)
    d.text((M, 8), GUNLER[now.weekday()], font=font(36, True), fill=255)
    d.text((M, 50), f"{now.day} {AYLAR[now.month - 1]} {now.year}", font=font(22), fill=255)
    right_w = W - 2 * M - 230  # sol taraftaki gün adına çarpmasın
    d.text((W - M, 10), ellipsize(d, loc.get("name", ""), font(20, True), right_w), font=font(20, True),
           fill=255, anchor="ra")
    if days and days[0]["sunrise"] and days[0]["sunset"]:
        d.text((W - M, 38), f"Gün doğumu {days[0]['sunrise']} · Batımı {days[0]['sunset']}",
               font=font(16), fill=255, anchor="ra")
    # Panonun çizildiği an: Kindle'daki görüntünün ne kadar taze olduğu anlaşılsın
    d.text((W - M, 58), f"{local_data.ay_evresi(today)} · Güncelleme {now:%H:%M}", font=font(16), fill=255,
           anchor="ra")
    y = 92

    # --- hava durumu
    def draw_weather(y: int) -> int:
        cur = weather["current"]
        weather_icon(d, cur["code"] if cur["code"] is not None else 3, M, y, 92, night=cur["night"])
        d.text((M + 104, y - 6), deg(cur["temp"]), font=font(70, True), fill=0)
        d.text((M + 108, y + 76), ellipsize(d, WMO.get(cur["code"], ""), font(19), 200), font=font(19), fill=0)
        details = []
        if cur["feels"] is not None:
            details.append(f"Hissedilen {deg(cur['feels'])}")
        if cur["humidity"] is not None:
            details.append(f"Nem %{round(cur['humidity'])}")
        if cur["wind"] is not None:
            name = wind_dir(cur["wind_dir"]) + " " if cur["wind_dir"] is not None else "Rüzgar "
            details.append(f"{name}{round(cur['wind'])} km/s")
        if days and days[0]["uv"] is not None:
            details.append(f"UV {round(days[0]['uv'])}")
        for i, line in enumerate(details):
            d.text((W - M, y + i * 24), line, font=font(18), fill=0, anchor="ra")
        y += 106
        if days:
            col = CW / len(days)
            for i, day in enumerate(days):
                cx = M + col * i + col / 2
                label = "Bugün" if day["date"] == today else GUNLER[day["date"].weekday()]
                d.text((cx, y), label, font=font(16, True), fill=0, anchor="ma")
                weather_icon(d, day["code"] if day["code"] is not None else 3, cx - 20, y + 20, 40)
                d.text((cx, y + 64), f"{deg(day['tmax'])} / {deg(day['tmin'])}", font=font(16), fill=0, anchor="ma")
                if day["rain"] is not None:
                    d.text((cx, y + 84), f"Yağış %{round(day['rain'])}", font=font(14), fill=70, anchor="ma")
                if i:
                    d.line([M + col * i, y, M + col * i, y + 100], fill=170, width=1)
            y += 108
        return y

    def guarded(name: str, fn, y: int, fallback_h: int) -> int:
        """Bölümü çizer; çizim sırasında hata olursa bölümün alanını temizleyip devam eder."""
        try:
            return fn(y)
        except Exception as e:  # noqa: BLE001
            d.rectangle([0, y, W, y + fallback_h], fill=255)
            fail(name, e)
            return y + 10

    if weather:
        y = guarded("Hava", draw_weather, y, 214)
    else:
        d.text((M, y), "Hava durumu alınamadı", font=font(20), fill=60)
        y += 36

    # --- kutucuklar
    def draw_tiles(y: int) -> int:
        tiles: list[tuple[str, str, str]] = []
        if air:
            sub = f"PM2.5: {round(air['pm2_5'])}" if air["pm2_5"] is not None else ""
            tiles.append(("Hava kalitesi", aqi_label(air["aqi"]), sub))
        if sea is not None:
            tiles.append(("Deniz suyu", f"{round(sea)}°C", loc.get("sea_name", "")))
        if fin:
            if "USD" in fin:
                tiles.append(("Dolar", f"{fmt_tr(fin['USD'])} ₺", "USD"))
            if "EUR" in fin:
                tiles.append(("Euro", f"{fmt_tr(fin['EUR'])} ₺", "EUR"))
            if "ALTIN" in fin:
                tiles.append(("Gram altın", f"{fmt_tr(fin['ALTIN'], 0)} ₺", "satış"))
        if not tiles:
            return y
        n = len(tiles)
        tw = (CW - (n - 1) * 8) / n
        for i, (label, value, sub) in enumerate(tiles):
            x0 = M + i * (tw + 8)
            d.rounded_rectangle([x0, y, x0 + tw, y + 66], radius=8, outline=0, width=2)
            d.text((x0 + tw / 2, y + 5), ellipsize(d, label, font(14), int(tw - 8)), font=font(14), fill=60, anchor="ma")
            size = 22
            while size > 14 and d.textlength(value, font=font(size, True)) > tw - 8:
                size -= 1
            d.text((x0 + tw / 2, y + 22 + (22 - size) // 2), ellipsize(d, value, font(size, True), int(tw - 8)),
                   font=font(size, True), fill=0, anchor="ma")
            d.text((x0 + tw / 2, y + 48), ellipsize(d, sub, font(13), int(tw - 8)), font=font(13), fill=60, anchor="ma")
        return y + 76

    y = guarded("Kutucuklar", draw_tiles, y, 70)

    # --- mevsiminde: ay adı + ikonlu ürün ızgarası
    d.text((M, y), tr_upper(AYLAR[today.month - 1]), font=font(30, True), fill=0)
    note = local_data.balik_notu(today)
    month_w = int(d.textlength(tr_upper(AYLAR[today.month - 1]), font=font(30, True)))
    d.text((W - M, y + 10), ellipsize(d, "Mevsiminde güzel!" + (f" · {note}" if note else ""), font(18), CW - month_w - 16),
           font=font(18), fill=60, anchor="ra")
    y += 38
    d.line([M, y, W - M, y], fill=0, width=2)
    y += 6
    label_w = 62
    per_row = 6
    cell = (CW - label_w) / per_row
    icon_px = 50
    for label, kind, items in zip(("Meyve", "Sebze", "Balık"), ("meyve", "sebze", "balik"),
                                  local_data.MEVSIM[today.month]):
        d.text((M, y + 32), label, font=font(16, True), fill=0)
        for i, name in enumerate([n for n in items if n][:per_row]):
            cx = M + label_w + cell * i + cell / 2
            try:
                # balıklar yatay olduğu için daha geniş çizilip dikeyde ortalanır
                px = 72 if kind == "balik" else icon_px
                icon = icons.render_icon(name, kind, px)
                if kind == "balik":
                    icon = icon.crop((0, (px - icon_px) // 2, px, (px - icon_px) // 2 + icon_px))
                img.paste(icon, (int(cx - icon.width / 2), int(y + 2)))
            except Exception as e:  # noqa: BLE001
                fail("İkon", e)
            lines = wrap(d, name, font(13), int(cell - 4))
            if len(lines) > 2:
                lines = lines[:2]
                lines[1] += "…"
            for j, line in enumerate(lines):
                d.text((cx, y + icon_px + 6 + j * 15), ellipsize(d, line, font(13), int(cell - 4)),
                       font=font(13), fill=0, anchor="ma")
        y += 84
    y += 2

    # --- semt
    d.line([M, y, W - M, y], fill=0, width=2)
    y += 8
    rows: list[tuple[str, str]] = []
    # Pazarlar gün adıyla yazılır ("Per: Erenköy"): pano gece güncellenmediği için "yarın" yanıltabilir
    pazar = []
    for offset in (0, 1):
        day = today + dt.timedelta(days=offset)
        names = [p.removesuffix(" Pazarı") for p in local_data.pazarlar(day)]
        if names:
            pazar.append(f"{GUN_KISA[day.weekday()]}: " + ", ".join(names))
    if not any("Erenköy" in p for p in pazar):
        pazar.append("Per: Erenköy")
    rows.append(("Pazar", " · ".join(pazar)))
    home_name = loc.get("home_name", "")
    LABEL_W = 96
    text_w = CW - LABEL_W
    for i, e in enumerate(pharmacies or []):
        name = re.sub(r"(?i)\s+eczanes[iİ]$", "", e["ad"]).strip() or "Eczane"
        dist = f"{fmt_distance(e['km'])} {e['yon']}" if e["km"] is not None else ""
        place = e.get("sokak") or e["semt"]
        tel = re.sub(r"^0\s*\((\d{3})\)\s*", r"0\1 ", e["tel"]).strip()
        # Sığmazsa önce sokak adından vazgeçilir; telefon ve uzaklık kalır
        for parts in ([name, dist, place, tel], [name, dist, tel], [name, dist, place], [name, dist]):
            text = " · ".join(p for p in parts if p)
            if d.textlength(text, font=font(16)) <= text_w:
                break
        label = "Eczane" if i == 0 else (f"{home_name}'tan" if home_name and i == 1 else "")
        rows.append((label, text))
    if holiday:
        hday, hname = holiday
        left = (hday - today).days
        when = "bugün" if left == 0 else ("yarın" if left == 1 else f"{left} gün sonra")
        rows.append(("Tatil", f"{hname}, {hday.day} {AYLAR[hday.month - 1]} ({when})"))

    bottom = H - (18 if errors else 6)
    for label, text in rows:
        if y + 20 > bottom:
            break
        if label.endswith("'tan"):  # "Çelebi Sk.'tan": eczane uzaklıklarının referansı
            size = 13
            while size > 10 and d.textlength(label, font=font(size)) > LABEL_W - 4:
                size -= 1
            d.text((M, y + 2), ellipsize(d, label, font(size), LABEL_W - 4), font=font(size), fill=60)
        else:
            d.text((M, y), label, font=font(16, True), fill=0)
        d.text((M + LABEL_W, y), ellipsize(d, text, font(16), CW - LABEL_W), font=font(16), fill=0)
        y += 22

    if errors:
        d.rectangle([0, H - 17, W, H], fill=255)
        d.text((M, H - 16), ellipsize(d, "Alınamadı: " + ", ".join(errors), font(12), CW), font=font(12), fill=80)

    return img.quantize(16, dither=Image.Dither.NONE).convert("L"), errors


def render(cfg: dict) -> Image.Image:
    return render_report(cfg)[0]


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def attempted_sources(cfg: dict) -> set[str]:
    tiles = cfg.get("tiles", {})
    names = {"Hava", "Tatil"}
    for key, name in (("air", "Hava kalitesi"), ("sea", "Deniz"), ("finance", "Piyasa"), ("pharmacy", "Eczane")):
        if tiles.get(key, True):
            names.add(name)
    return names


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "display.png")
    cfg = load_config()
    img, errors = render_report(cfg)
    if attempted_sources(cfg) <= set(errors):
        # Hiçbir kaynağa ulaşılamadı (büyük olasılıkla ağ sorunu): eski, dolu panoyu ezme.
        print("Hiçbir veri kaynağına ulaşılamadı; görüntü yayımlanmıyor.", file=sys.stderr)
        return 2
    out.write_bytes(to_png(img))
    print(f"yazıldı: {out}" + (f" (alınamadı: {', '.join(errors)})" if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
