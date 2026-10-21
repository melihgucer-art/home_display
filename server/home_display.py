#!/usr/bin/env python3
"""Kindle 4 (600x800, 16 gri ton) için ev panosu PNG'si üretir ve HTTP ile sunar.

Kullanım:
    python3 home_display.py serve            # http://<ip>:8080/display.png
    python3 home_display.py render out.png   # tek seferlik çıktı
"""
from __future__ import annotations

import datetime as dt
import io
import re
import sys
import threading
import time
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
HTTP_TIMEOUT = 10

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
    path = BASE_DIR / "config.toml"
    if not path.exists():
        path = BASE_DIR / "config.example.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------- veri

def fetch_weather(cfg: dict) -> dict | None:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": cfg["latitude"],
            "longitude": cfg["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max,sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 4,
        },
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def fetch_currency(cfg: dict) -> dict[str, float]:
    # Frankfurter (ECB) API'si: 1 <sembol> kaç <base> eder
    r = requests.get(
        "https://api.frankfurter.app/latest",
        params={"from": cfg["base"], "to": ",".join(cfg["symbols"])},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    rates = r.json()["rates"]
    return {sym: 1 / rate for sym, rate in rates.items() if rate}


def fetch_home_assistant(cfg: dict) -> list[tuple[str, str]]:
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    out = []
    for label, entity in cfg["sensors"]:
        try:
            r = requests.get(f"{cfg['url'].rstrip('/')}/api/states/{entity}",
                             headers=headers, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            unit = data.get("attributes", {}).get("unit_of_measurement", "")
            out.append((label, f"{data['state']} {unit}".strip()))
        except requests.RequestException:
            out.append((label, "?"))
    return out


def _parse_ics_date(value: str, params: str, tz: ZoneInfo) -> tuple[dt.datetime, bool]:
    if "VALUE=DATE" in params or len(value) == 8:
        d = dt.datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=tz)
        return d, True
    if value.endswith("Z"):
        d = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        return d.astimezone(tz), False
    m = re.search(r"TZID=([^;:]+)", params)
    src_tz = tz
    if m:
        try:
            src_tz = ZoneInfo(m.group(1))
        except Exception:
            pass
    d = dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=src_tz)
    return d.astimezone(tz), False


def fetch_calendar(cfg: dict, tz: ZoneInfo, now: dt.datetime) -> list[tuple[dt.datetime, bool, str]]:
    """Basit ICS okuyucu. Tekrarlayan etkinliklerde (RRULE) yalnızca haftalık/
    günlük/yıllık kuralların ilk uygun tekrarını hesaplar."""
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start_day + dt.timedelta(days=cfg.get("days_ahead", 7))
    events = []
    for url in cfg["ics_urls"]:
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        text = re.sub(r"\r?\n[ \t]", "", r.text)  # satır katlamalarını aç
        for block in text.split("BEGIN:VEVENT")[1:]:
            block = block.split("END:VEVENT")[0]
            fields = {}
            for line in block.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                name, _, params = key.partition(";")
                fields[name] = (value.strip(), params)
            if "DTSTART" not in fields:
                continue
            start, all_day = _parse_ics_date(*fields["DTSTART"], tz)
            summary = fields.get("SUMMARY", ("(adsız)", ""))[0].replace("\\,", ",")
            rrule = fields.get("RRULE", ("", ""))[0]
            step = {"FREQ=DAILY": dt.timedelta(days=1),
                    "FREQ=WEEKLY": dt.timedelta(weeks=1)}
            freq = next((k for k in step if k in rrule), None)
            if freq and start < start_day:
                delta = step[freq]
                n = (start_day - start) // delta + (1 if (start_day - start) % delta else 0)
                start = start + delta * n
            elif "FREQ=YEARLY" in rrule and start < start_day:
                start = start.replace(year=start_day.year)
                if start < start_day:
                    start = start.replace(year=start_day.year + 1)
            if start_day <= start < end:
                events.append((start, all_day, summary))
    events.sort(key=lambda e: e[0])
    return events[: cfg.get("max_events", 6)]


def read_todo(cfg: dict) -> list[str]:
    path = BASE_DIR / cfg["file"]
    if not path.exists():
        return []
    items = [l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return items[: cfg.get("max_items", 5)]


# ---------------------------------------------------------------- çizim

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        for d in (BASE_DIR / "fonts", Path("/usr/share/fonts/truetype/dejavu")):
            if (d / name).exists():
                return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default(size)


def weather_icon(draw: ImageDraw.ImageDraw, code: int, x: int, y: int, s: int) -> None:
    """Kod tabanlı basit vektör simge (x, y sol üst, s boyut)."""
    def sun(cx, cy, r):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=max(2, s // 25))
        for i in range(8):
            import math
            a = i * math.pi / 4
            draw.line([cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35,
                       cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75],
                      fill=0, width=max(2, s // 25))

    def cloud(cx, cy, w, fill=255):
        h = w * 0.45
        parts = [(cx - w * 0.3, cy, w * 0.25), (cx, cy - h * 0.35, w * 0.3), (cx + w * 0.3, cy, w * 0.22)]
        for px, py, r in parts:
            draw.ellipse([px - r, py - r, px + r, py + r], fill=fill, outline=0, width=max(2, s // 25))
        draw.rectangle([cx - w * 0.3, cy - 2, cx + w * 0.3, cy + w * 0.2], fill=fill)
        draw.line([cx - w * 0.3, cy + w * 0.22, cx + w * 0.3, cy + w * 0.22], fill=0, width=max(2, s // 25))
        for px, py, r in parts:  # iç çizgileri ört
            draw.ellipse([px - r + 3, py - r + 3, px + r - 3, py + r - 3], fill=fill)
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
            draw.line([x + s * 0.15, yy, x + s * 0.85, yy], fill=0, width=max(2, s // 20))
    else:
        cloud(x + c, y + c * 0.85, s * 0.9, fill=200 if code >= 3 and code != 3 else 255)
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            for i in range(3):
                xx = x + s * (0.3 + i * 0.2)
                draw.line([xx, y + s * 0.78, xx - s * 0.06, y + s * 0.95], fill=0, width=max(2, s // 25))
        elif code in (71, 73, 75, 77, 85, 86):
            for i in range(3):
                xx = x + s * (0.3 + i * 0.2)
                draw.text((xx, y + s * 0.86), "*", font=font(max(12, s // 5), True), fill=0, anchor="mm")
        elif code >= 95:
            draw.line([x + s * 0.5, y + s * 0.72, x + s * 0.42, y + s * 0.86,
                       x + s * 0.55, y + s * 0.86, x + s * 0.47, y + s * 0.99], fill=0, width=max(2, s // 20))


def section_title(draw, x, y, w, text):
    draw.text((x, y), text.upper(), font=font(20, True), fill=0)
    draw.line([x, y + 28, x + w, y + 28], fill=0, width=2)
    return y + 38


def render(cfg: dict) -> Image.Image:
    dcfg = cfg["display"]
    tz = ZoneInfo(dcfg.get("timezone", "Europe/Istanbul"))
    now = dt.datetime.now(tz)
    W, H = dcfg["width"], dcfg["height"]
    if dcfg.get("rotate", 0) in (90, 270):
        W, H = H, W
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    M = 24
    errors = []

    # Başlık: tarih
    d.rectangle([0, 0, W, 110], fill=0)
    d.text((M, 14), GUNLER[now.weekday()], font=font(44, True), fill=255)
    d.text((M, 66), f"{now.day} {AYLAR[now.month - 1]} {now.year}", font=font(28), fill=255)
    d.text((W - M, 55), now.strftime("%H:%M"), font=font(56, True), fill=255, anchor="rm")
    y = 130

    # Hava durumu
    wcfg = cfg.get("weather", {})
    if wcfg.get("enabled"):
        try:
            w = fetch_weather(wcfg)
            cur, daily = w["current"], w["daily"]
            weather_icon(d, cur["weather_code"], M, y, 130)
            d.text((M + 150, y - 5), f"{round(cur['temperature_2m'])}°", font=font(96, True), fill=0)
            d.text((M + 150, y + 105), WMO.get(cur["weather_code"], ""), font=font(24), fill=0)
            info_x = W - M
            lines = [
                wcfg.get("city", ""),
                f"Hissedilen {round(cur['apparent_temperature'])}°",
                f"Nem %{cur['relative_humidity_2m']}",
                f"Rüzgar {round(cur['wind_speed_10m'])} km/s",
                f"↑{daily['sunrise'][0][-5:]}  ↓{daily['sunset'][0][-5:]}",
            ]
            for i, line in enumerate(lines):
                d.text((info_x, y + 5 + i * 27), line, font=font(22, i == 0), fill=0, anchor="ra")
            y += 155
            # 4 günlük tahmin
            col = (W - 2 * M) / 4
            for i in range(4):
                cx = M + col * i
                day = dt.date.fromisoformat(daily["time"][i])
                label = "Bugün" if i == 0 else GUN_KISA[day.weekday()]
                d.text((cx + col / 2, y), label, font=font(20, True), fill=0, anchor="ma")
                weather_icon(d, daily["weather_code"][i], int(cx + col / 2 - 30), y + 26, 60)
                d.text((cx + col / 2, y + 92),
                       f"{round(daily['temperature_2m_max'][i])}° / {round(daily['temperature_2m_min'][i])}°",
                       font=font(20), fill=0, anchor="ma")
                pp = daily["precipitation_probability_max"][i]
                if pp is not None:
                    d.text((cx + col / 2, y + 116), f"☂ %{pp}", font=font(17), fill=80, anchor="ma")
                if i:
                    d.line([cx, y, cx, y + 136], fill=160, width=1)
            y += 146
        except Exception as e:  # noqa: BLE001 - ekran asla boş kalmasın
            errors.append(f"Hava: {e.__class__.__name__}")

    # Döviz + Home Assistant (yan yana kutucuklar)
    tiles: list[tuple[str, str]] = []
    ccfg = cfg.get("currency", {})
    if ccfg.get("enabled"):
        try:
            for sym, val in fetch_currency(ccfg).items():
                tiles.append((sym, f"{val:.2f} ₺" if ccfg["base"] == "TRY" else f"{val:.4f}"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"Döviz: {e.__class__.__name__}")
    hcfg = cfg.get("home_assistant", {})
    if hcfg.get("enabled") and hcfg.get("token"):
        try:
            tiles.extend(fetch_home_assistant(hcfg))
        except Exception as e:  # noqa: BLE001
            errors.append(f"HA: {e.__class__.__name__}")
    if tiles:
        per_row = min(4, len(tiles))
        tw = (W - 2 * M - (per_row - 1) * 10) / per_row
        for i, (label, value) in enumerate(tiles):
            r, c = divmod(i, per_row)
            x0, y0 = M + c * (tw + 10), y + r * 80
            d.rounded_rectangle([x0, y0, x0 + tw, y0 + 70], radius=8, outline=0, width=2)
            d.text((x0 + tw / 2, y0 + 8), label, font=font(18), fill=60, anchor="ma")
            d.text((x0 + tw / 2, y0 + 32), value, font=font(26, True), fill=0, anchor="ma")
        y += ((len(tiles) - 1) // per_row + 1) * 80 + 10

    # Takvim
    kcfg = cfg.get("calendar", {})
    if kcfg.get("enabled") and kcfg.get("ics_urls"):
        y = section_title(d, M, y, W - 2 * M, "Takvim")
        try:
            events = fetch_calendar(kcfg, tz, now)
            if not events:
                d.text((M, y), "Yaklaşan etkinlik yok", font=font(22), fill=80)
                y += 32
            for start, all_day, summary in events:
                if y > H - 120:
                    break
                if start.date() == now.date():
                    day = "Bugün"
                elif start.date() == now.date() + dt.timedelta(days=1):
                    day = "Yarın"
                else:
                    day = f"{GUN_KISA[start.weekday()]} {start.day}"
                when = day if all_day else f"{day} {start:%H:%M}"
                d.text((M, y), when, font=font(20, True), fill=0)
                d.text((M + 175, y), summary[:32], font=font(20), fill=0)
                y += 29
        except Exception as e:  # noqa: BLE001
            errors.append(f"Takvim: {e.__class__.__name__}")
        y += 4

    # Yapılacaklar
    tcfg = cfg.get("todo", {})
    if tcfg.get("enabled"):
        items = read_todo(tcfg)
        if items and y < H - 110:
            y = section_title(d, M, y, W - 2 * M, "Yapılacaklar")
            for item in items:
                if y > H - 72:
                    break
                d.rectangle([M, y + 4, M + 18, y + 22], outline=0, width=2)
                d.text((M + 30, y), item[:40], font=font(20), fill=0)
                y += 29

    # Alt bilgi
    d.line([M, H - 40, W - M, H - 40], fill=0, width=1)
    footer = "Güncellendi " + now.strftime("%d.%m %H:%M")
    if errors:
        footer += "  ·  " + ", ".join(errors)
    d.text((M, H - 30), footer, font=font(16), fill=60)
    d.text((W - M, H - 30), dcfg.get("title", ""), font=font(16, True), fill=0, anchor="ra")

    rot = dcfg.get("rotate", 0)
    if rot:
        img = img.rotate(-rot if rot == 90 else 90, expand=True)
    # Kindle 4 ekranı 16 gri ton gösterir
    return img.quantize(16, dither=Image.Dither.NONE).convert("L")


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- sunucu

class Cache:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = b""
        self.at = 0.0

    def get(self) -> bytes:
        cfg = load_config()
        with self.lock:
            if time.time() - self.at > cfg["server"].get("cache_seconds", 60) or not self.data:
                self.data = to_png(render(cfg))
                self.at = time.time()
            return self.data


CACHE = Cache()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/display.png"):
            try:
                body = CACHE.get()
            except Exception as e:  # noqa: BLE001
                self.send_error(500, str(e))
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(404)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "serve"
    cfg = load_config()
    if cmd == "render":
        out = Path(argv[2] if len(argv) > 2 else "display.png")
        out.write_bytes(to_png(render(cfg)))
        print(f"yazıldı: {out}")
        return 0
    if cmd == "serve":
        s = cfg["server"]
        srv = ThreadingHTTPServer((s.get("host", "0.0.0.0"), s.get("port", 8080)), Handler)
        print(f"http://{s.get('host')}:{s.get('port')}/display.png")
        srv.serve_forever()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
