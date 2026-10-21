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


def get_json(url: str, **params) -> dict | list:
    r = requests.get(url, params=params or None, headers=UA, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


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

def fetch_weather(loc: dict) -> dict:
    return get_json(
        "https://api.open-meteo.com/v1/forecast",
        latitude=loc["latitude"], longitude=loc["longitude"],
        current="temperature_2m,apparent_temperature,relative_humidity_2m,"
                "weather_code,wind_speed_10m,wind_direction_10m,is_day",
        daily="weather_code,temperature_2m_max,temperature_2m_min,"
              "precipitation_probability_max,sunrise,sunset,uv_index_max",
        timezone="Europe/Istanbul", forecast_days=4,
    )


def fetch_air(loc: dict) -> dict:
    return get_json(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        latitude=loc["latitude"], longitude=loc["longitude"],
        current="european_aqi,pm2_5,pm10", timezone="Europe/Istanbul",
    )["current"]


def fetch_sea(loc: dict) -> float | None:
    cur = get_json(
        "https://marine-api.open-meteo.com/v1/marine",
        latitude=loc["sea_latitude"], longitude=loc["sea_longitude"],
        current="sea_surface_temperature",
    )["current"]
    return cur.get("sea_surface_temperature")


def fetch_finance() -> dict[str, float]:
    d = get_json("https://finans.truncgil.com/today.json")
    out = {}
    for key, label in (("USD", "USD"), ("EUR", "EUR"), ("gram-altin", "ALTIN")):
        try:
            out[label] = tr_number(d[key]["Satış"])
        except (KeyError, ValueError, TypeError):
            pass
    return out


def fetch_next_holiday(today: dt.date) -> tuple[dt.date, str] | None:
    for h in get_json("https://date.nager.at/api/v3/NextPublicHolidays/TR"):
        day = dt.date.fromisoformat(h["date"])
        if day >= today:
            name = re.sub(r"\s*\(.*?\)", "", h["localName"])
            return day, name
    return None


def fetch_pharmacies(loc: dict, limit: int = 2) -> list[dict]:
    """Kadıköy nöbetçi eczaneleri (nobetcieczane.org), Erenköy'e uzaklığa göre sıralı."""
    import html as htmllib
    r = requests.get("https://nobetcieczane.org/istanbul/kadikoy", headers=UA, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    out = []
    for card in re.findall(r"<div class=\"pharm\"[^>]*data-pharm-card(.*?)>", r.text, re.S):
        attrs = {k: htmllib.unescape(v) for k, v in re.findall(r'data-eczane-([a-z-]+)="([^"]*)"', card)}
        if attrs.get("nobetci") != "1":
            continue
        try:
            lat, lon = float(attrs["lat"]), float(attrs["lon"])
        except (KeyError, ValueError):
            lat = lon = None
        km = None
        if lat is not None:
            dy = (lat - loc["latitude"]) * 111.0
            dx = (lon - loc["longitude"]) * 111.0 * math.cos(math.radians(loc["latitude"]))
            km = math.hypot(dx, dy)
        out.append({"ad": attrs.get("ad", ""), "semt": attrs.get("semt", ""),
                    "tel": attrs.get("telefon", ""), "km": km,
                    "baslangic": attrs.get("baslangic", "")})
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

def render(cfg: dict) -> Image.Image:
    dcfg, loc = cfg["display"], cfg["location"]
    tz = ZoneInfo(dcfg.get("timezone", "Europe/Istanbul"))
    now = dt.datetime.now(tz)
    today = now.date()
    W, H = dcfg["width"], dcfg["height"]
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    M = 20
    CW = W - 2 * M
    errors: list[str] = []

    def safe(name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001 - bir kaynak düşse de pano çizilsin
            errors.append(name)
            print(f"[uyarı] {name}: {e!r}", file=sys.stderr)
            return None

    tiles_cfg = cfg.get("tiles", {})
    weather = safe("Hava", fetch_weather, loc)
    air = safe("Hava kalitesi", fetch_air, loc) if tiles_cfg.get("air", True) else None
    sea = safe("Deniz", fetch_sea, loc) if tiles_cfg.get("sea", True) else None
    fin = safe("Piyasa", fetch_finance) if tiles_cfg.get("finance", True) else None
    holiday = safe("Tatil", fetch_next_holiday, today)
    pharmacies = safe("Eczane", fetch_pharmacies, loc) if tiles_cfg.get("pharmacy", True) else None

    # --- başlık
    d.rectangle([0, 0, W, 82], fill=0)
    d.text((M, 8), GUNLER[now.weekday()], font=font(36, True), fill=255)
    d.text((M, 50), f"{now.day} {AYLAR[now.month - 1]} {now.year}", font=font(22), fill=255)
    d.text((W - M, 10), loc.get("name", ""), font=font(20, True), fill=255, anchor="ra")
    if weather:
        daily = weather["daily"]
        d.text((W - M, 38), f"Gün doğumu {daily['sunrise'][0][-5:]} · Batımı {daily['sunset'][0][-5:]}",
               font=font(16), fill=255, anchor="ra")
    d.text((W - M, 58), local_data.ay_evresi(today), font=font(16), fill=255, anchor="ra")
    y = 92

    # --- hava durumu
    if weather:
        cur, daily = weather["current"], weather["daily"]
        weather_icon(d, cur["weather_code"], M, y, 92, night=not cur.get("is_day", 1))
        d.text((M + 104, y - 6), f"{round(cur['temperature_2m'])}°", font=font(70, True), fill=0)
        d.text((M + 108, y + 76), WMO.get(cur["weather_code"], ""), font=font(19), fill=0)
        details = [
            f"Hissedilen {round(cur['apparent_temperature'])}°",
            f"Nem %{cur['relative_humidity_2m']}",
            f"{wind_dir(cur['wind_direction_10m'])} {round(cur['wind_speed_10m'])} km/s",
            f"UV {round(daily['uv_index_max'][0] or 0)}",
        ]
        for i, line in enumerate(details):
            d.text((W - M, y + i * 24), line, font=font(18), fill=0, anchor="ra")
        y += 106
        col = CW / 4
        for i in range(4):
            cx = M + col * i + col / 2
            day = dt.date.fromisoformat(daily["time"][i])
            d.text((cx, y), "Bugün" if i == 0 else GUNLER[day.weekday()], font=font(16, True), fill=0, anchor="ma")
            weather_icon(d, daily["weather_code"][i], cx - 20, y + 20, 40)
            d.text((cx, y + 64), f"{round(daily['temperature_2m_max'][i])}° / {round(daily['temperature_2m_min'][i])}°",
                   font=font(16), fill=0, anchor="ma")
            pp = daily["precipitation_probability_max"][i]
            if pp is not None:
                d.text((cx, y + 84), f"Yağış %{pp}", font=font(14), fill=70, anchor="ma")
            if i:
                d.line([M + col * i, y, M + col * i, y + 100], fill=170, width=1)
        y += 108
    else:
        d.text((M, y), "Hava durumu alınamadı", font=font(20), fill=60)
        y += 36

    # --- kutucuklar
    tiles: list[tuple[str, str, str]] = []
    if air:
        tiles.append(("Hava kalitesi", aqi_label(air["european_aqi"]), f"PM2.5 {round(air['pm2_5'])} µg/m³"))
    if sea is not None:
        tiles.append(("Deniz suyu", f"{sea:.0f}°C", loc.get("sea_name", "")))
    if fin:
        if "USD" in fin and "EUR" in fin:
            tiles.append(("Dolar / Euro", f"$ {fmt_tr(fin['USD'])}", f"€ {fmt_tr(fin['EUR'])}"))
        if "ALTIN" in fin:
            tiles.append(("Gram altın", f"{fmt_tr(fin['ALTIN'], 0)} ₺", "satış"))
    if tiles:
        n = len(tiles)
        tw = (CW - (n - 1) * 8) / n
        for i, (label, value, sub) in enumerate(tiles):
            x0 = M + i * (tw + 8)
            d.rounded_rectangle([x0, y, x0 + tw, y + 66], radius=8, outline=0, width=2)
            d.text((x0 + tw / 2, y + 5), label, font=font(14), fill=60, anchor="ma")
            d.text((x0 + tw / 2, y + 22), ellipsize(d, value, font(22, True), int(tw - 8)),
                   font=font(22, True), fill=0, anchor="ma")
            d.text((x0 + tw / 2, y + 48), ellipsize(d, sub, font(13), int(tw - 8)), font=font(13), fill=60, anchor="ma")
        y += 76

    # --- mevsiminde: ay adı + ikonlu ürün ızgarası
    d.text((M, y), tr_upper(AYLAR[today.month - 1]), font=font(30, True), fill=0)
    note = local_data.balik_notu(today)
    d.text((W - M, y + 10), "Mevsiminde" + (f" · {note}" if note else ""), font=font(18), fill=60, anchor="ra")
    y += 38
    d.line([M, y, W - M, y], fill=0, width=2)
    y += 6
    label_w = 62
    per_row = 6
    cell = (CW - label_w) / per_row
    icon_px = 50
    for label, kind, items in zip(("Meyve", "Sebze", "Balık"), ("meyve", "sebze", "balik"),
                                  local_data.MEVSIM[today.month]):
        row_h = 86
        d.text((M, y + 32), label, font=font(16, True), fill=0)
        for i, name in enumerate(items[:per_row]):
            cx = M + label_w + cell * i + cell / 2
            # balıklar yatay olduğu için daha geniş çizilip dikeyde ortalanır
            px = 72 if kind == "balik" else icon_px
            icon = icons.render_icon(name, kind, px)
            if kind == "balik":
                icon = icon.crop((0, (px - icon_px) // 2, px, (px - icon_px) // 2 + icon_px))
            img.paste(icon, (int(cx - icon.width / 2), int(y + 2)))
            lines = wrap(d, name, font(13), int(cell - 4))[:2]
            for j, line in enumerate(lines):
                d.text((cx, y + icon_px + 6 + j * 15), line, font=font(13), fill=0, anchor="ma")
        y += row_h
    y += 2

    # --- semt
    d.line([M, y, W - M, y], fill=0, width=2)
    y += 8
    rows: list[tuple[str, str]] = []
    bugun = [p.removesuffix(" Pazarı") for p in local_data.pazarlar(today)]
    yarin = [p.removesuffix(" Pazarı") for p in local_data.pazarlar(today + dt.timedelta(days=1))]
    pazar = []
    if bugun:
        pazar.append("Bugün: " + ", ".join(bugun))
    if yarin:
        pazar.append("Yarın: " + ", ".join(yarin))
    if not any("Erenköy" in p for p in pazar):
        pazar.append(f"Erenköy {(3 - today.weekday()) % 7} gün sonra")
    rows.append(("Pazar", " · ".join(pazar)))
    if pharmacies:
        for i, e in enumerate(pharmacies):
            name = re.sub(r"(?i)\s+eczanes[iİ]$", "", e["ad"]).strip()
            dist = f" {fmt_tr(e['km'], 1)} km" if e["km"] is not None else ""
            tel = re.sub(r"^0\s*\((\d{3})\)\s*", r"0\1 ", e["tel"])
            rows.append(("Eczane" if i == 0 else "", f"{name}, {e['semt']}{dist} · {tel}"))
    if holiday:
        hday, hname = holiday
        left = (hday - today).days
        when = "bugün" if left == 0 else ("yarın" if left == 1 else f"{left} gün sonra")
        rows.append(("Tatil", f"{hname}, {hday.day} {AYLAR[hday.month - 1]} ({when})"))

    bottom = H - (22 if errors else 6)
    for label, text in rows:
        if y + 20 > bottom:
            break
        d.text((M, y), label, font=font(16, True), fill=0)
        d.text((M + 80, y), ellipsize(d, text, font(16), CW - 80), font=font(16), fill=0)
        y += 22

    if errors:
        d.text((M, H - 20), ellipsize(d, "Alınamadı: " + ", ".join(errors), font(13), CW), font=font(13), fill=80)

    rot = dcfg.get("rotate", 0)
    if rot:
        img = img.rotate(-rot, expand=True)
    return img.quantize(16, dither=Image.Dither.NONE).convert("L")


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "display.png")
    out.write_bytes(to_png(render(load_config())))
    print(f"yazıldı: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
