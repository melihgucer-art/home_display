"""Mevsim ürünleri için tek renkli (e-ink uyumlu) ikonlar.

Noto Emoji'de karşılığı olan ürünler o fonttan çizilir (fonts/NotoEmoji.ttf, OFL lisansı).
Karşılığı olmayan meyve/sebzeler ve tüm balık türleri burada vektörel olarak çizilir.
Çizimler 100x100'lük bir birim kutuda tanımlanır, 4 kat büyük çizilip küçültülür (kenar yumuşatma).
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent / "fonts"
SS = 4  # süper örnekleme katsayısı

EMOJI = {
    "Portakal": "🍊", "Limon": "🍋", "Kivi": "🥝", "Elma": "🍎", "Armut": "🍐",
    "Çilek": "🍓", "Kiraz": "🍒", "Şeftali": "🍑", "Karpuz": "🍉", "Kavun": "🍈",
    "Üzüm": "🍇", "Kestane": "🌰", "Havuç": "🥕", "Brokoli": "🥦", "Marul": "🥬",
    "Bezelye": "🫛", "Salatalık": "🥒", "Domates": "🍅", "Biber": "🫑", "Patlıcan": "🍆",
    "Mısır": "🌽", "Barbunya": "🫘",
}

W = 255      # beyaz
LIGHT = 215
MID = 165
DARK = 95
INK = 0


class Pen:
    """100x100 birim koordinatlarla çizim."""

    def __init__(self, px: int):
        self.k = px * SS / 100
        self.img = Image.new("L", (px * SS, px * SS), 255)
        self.d = ImageDraw.Draw(self.img)
        self.lw = max(1, round(6.5 * self.k))

    def p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def box(self, x0, y0, x1, y1):
        return [x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k]

    def ellipse(self, x0, y0, x1, y1, fill=W, outline=INK, width=None):
        self.d.ellipse(self.box(x0, y0, x1, y1), fill=fill, outline=outline,
                       width=self.lw if width is None else round(width * self.k))

    def circle(self, cx, cy, r, **kw):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, **kw)

    def poly(self, pts, fill=W, outline=INK, width=None):
        pts = self.p(pts)
        self.d.polygon(pts, fill=fill)
        if outline is not None:
            self.d.line(pts + [pts[0]], fill=outline, width=self.lw if width is None else round(width * self.k),
                        joint="curve")
            r = (self.lw if width is None else width * self.k) / 2
            for x, y in pts:  # köşeleri yuvarla
                self.d.ellipse([x - r, y - r, x + r, y + r], fill=outline)

    def line(self, pts, fill=INK, width=None):
        w = self.lw if width is None else max(1, round(width * self.k))
        pts = self.p(pts)
        self.d.line(pts, fill=fill, width=w, joint="curve")
        r = w / 2
        for x, y in (pts[0], pts[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def arc(self, x0, y0, x1, y1, start, end, width=None, fill=INK):
        self.d.arc(self.box(x0, y0, x1, y1), start, end, fill=fill,
                   width=self.lw if width is None else round(width * self.k))

    def blob(self, ellipses, fill=W):
        """Birden çok elipsin birleşimi: önce hepsinin dış çizgisi, sonra içleri."""
        for e in ellipses:
            self.ellipse(*e, fill=INK, outline=INK)
        inset = self.lw / self.k
        for x0, y0, x1, y1 in ellipses:
            self.ellipse(x0 + inset, y0 + inset, x1 - inset, y1 - inset, fill=fill, outline=None, width=0)

    def leaf(self, x0, y0, x1, y1, bulge=0.35, fill=MID, vein=True):
        """(x0,y0)'dan (x1,y1)'e uzanan yaprak."""
        dx, dy = x1 - x0, y1 - y0
        nx, ny = -dy * bulge, dx * bulge
        pts = []
        for i in range(13):
            t = i / 12
            s = math.sin(math.pi * t)
            pts.append((x0 + dx * t + nx * s, y0 + dy * t + ny * s))
        for i in range(11, 0, -1):
            t = i / 12
            s = math.sin(math.pi * t)
            pts.append((x0 + dx * t - nx * s, y0 + dy * t - ny * s))
        self.poly(pts, fill=fill)
        if vein:
            self.line([(x0 + dx * 0.12, y0 + dy * 0.12), (x0 + dx * 0.85, y0 + dy * 0.85)],
                      fill=INK, width=3)

    def done(self, px: int, rotate: float = 0) -> Image.Image:
        img = self.img
        if rotate:
            img = img.rotate(rotate, resample=Image.BICUBIC, fillcolor=255)
        return img.resize((px, px), Image.LANCZOS)


# ------------------------------------------------------------------ meyveler

def nar(p: Pen):
    p.poly([(36, 26), (38, 10), (44, 19), (50, 8), (56, 19), (62, 10), (64, 26)], fill=MID)
    p.circle(50, 58, 36, fill=MID)
    p.arc(26, 34, 74, 82, 200, 250, width=5, fill=W)
    p.circle(44, 52, 5, fill=W, width=0, outline=None)


def ayva(p: Pen):
    p.line([(50, 24), (53, 9)], width=6)
    p.leaf(54, 14, 80, 6, fill=MID)
    p.blob([(20, 42, 80, 94), (30, 20, 70, 62), (14, 52, 50, 88), (52, 50, 86, 88)], fill=LIGHT)
    p.circle(42, 52, 3, fill=W, outline=None, width=0)


def incir(p: Pen):
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        x = 50 + 40 * math.sin(t) * math.sin(t / 2) ** 1.3
        y = 54 - 40 * math.cos(t)
        pts.append((x, y))
    p.poly(pts, fill=DARK)
    p.line([(50, 14), (53, 4)], width=6)
    p.arc(34, 46, 66, 86, 130, 200, width=5, fill=W)
    p.line([(46, 88), (54, 88)], width=4, fill=W)


def _cluster(p: Pen, cx, cy, rx, ry, r, fill):
    pts = []
    y = cy - ry + r
    row = 0
    while y <= cy + ry - r * 0.6:
        half = rx * math.sqrt(max(0.0, 1 - ((y - cy) / ry) ** 2))
        x = cx - half + r + (r if row % 2 else 0)
        while x <= cx + half - r * 0.6:
            pts.append((x, y))
            x += 2 * r
        y += r * 1.7
        row += 1
    for x, y in pts:
        p.circle(x, y, r + 1, fill=INK, outline=None, width=0)
    for x, y in pts:
        p.circle(x, y, r - 1.6, fill=fill, outline=None, width=0)
        p.circle(x - r * 0.3, y - r * 0.3, r * 0.25, fill=W, outline=None, width=0)


def dut(p: Pen):
    p.line([(50, 22), (56, 6)], width=6)
    _cluster(p, 50, 58, 22, 36, 7.5, fill=DARK)


def bogurtlen(p: Pen):
    p.leaf(50, 24, 24, 8, fill=MID)
    p.leaf(50, 24, 78, 10, fill=MID)
    _cluster(p, 50, 60, 32, 32, 8, fill=50)


def kayisi(p: Pen):
    p.leaf(52, 20, 78, 8, fill=MID)
    p.circle(48, 58, 34, fill=LIGHT)
    p.arc(32, 26, 84, 92, 190, 260, width=5)
    p.circle(36, 48, 4, fill=W, outline=None, width=0)


def erik(p: Pen):
    p.line([(48, 22), (44, 8)], width=6)
    p.ellipse(22, 20, 78, 94, fill=DARK)
    p.arc(30, 30, 70, 86, 200, 250, width=5, fill=W)
    p.arc(46, 22, 96, 92, 175, 205, width=4, fill=INK)


def can_erik(p: Pen):
    p.line([(36, 34), (46, 14), (62, 30)], width=5)
    p.ellipse(10, 34, 54, 80, fill=LIGHT)
    p.ellipse(44, 30, 90, 78, fill=MID)
    p.circle(24, 48, 4, fill=W, outline=None, width=0)
    p.circle(58, 44, 4, fill=W, outline=None, width=0)


def yenidunya(p: Pen):
    p.leaf(56, 40, 92, 8, bulge=0.25, fill=MID)
    for x0, y0 in ((8, 44), (34, 30), (36, 56)):
        p.ellipse(x0, y0, x0 + 34, y0 + 40, fill=LIGHT)
        p.circle(x0 + 17, y0 + 38, 3, fill=INK, outline=None, width=0)


def trabzon_hurmasi(p: Pen):
    p.ellipse(10, 32, 90, 92, fill=MID)
    p.arc(20, 42, 80, 86, 200, 250, width=5, fill=W)
    p.poly([(50, 28), (30, 30), (44, 38), (40, 48), (50, 40), (60, 48), (56, 38), (70, 30)], fill=DARK)
    p.line([(50, 32), (50, 16)], width=6)


def greyfurt(p: Pen):
    p.circle(50, 50, 42, fill=LIGHT)
    p.circle(50, 50, 32, fill=W, width=4)
    for i in range(8):
        a = i * math.pi / 4
        p.line([(50, 50), (50 + 30 * math.cos(a), 50 + 30 * math.sin(a))], width=4)
    for i in range(8):
        a = (i + 0.5) * math.pi / 4
        p.circle(50 + 18 * math.cos(a), 50 + 18 * math.sin(a), 5, fill=MID, outline=None, width=0)


def mandalina(p: Pen):
    p.leaf(54, 22, 80, 10, fill=MID)
    p.ellipse(12, 26, 88, 88, fill=LIGHT)
    p.ellipse(40, 22, 60, 32, fill=MID, width=4)
    for x, y in ((30, 50), (44, 64), (60, 52), (68, 68), (34, 72), (52, 78), (72, 44)):
        p.circle(x, y, 2, fill=INK, outline=None, width=0)


def visne(p: Pen):
    p.line([(30, 56), (52, 10), (72, 52)], width=5)
    p.leaf(52, 12, 80, 4, fill=MID)
    p.circle(30, 68, 20, fill=50)
    p.circle(72, 64, 20, fill=50)
    p.circle(24, 62, 4, fill=W, outline=None, width=0)
    p.circle(66, 58, 4, fill=W, outline=None, width=0)


def nektarin(p: Pen):
    p.leaf(50, 20, 22, 8, fill=MID)
    p.circle(50, 58, 34, fill=DARK)
    p.arc(30, 34, 70, 82, 200, 250, width=5, fill=W)


# ------------------------------------------------------------------ sebzeler

def lahana(p: Pen):
    # dış yapraklar
    p.leaf(50, 92, 4, 40, bulge=0.45, fill=MID)
    p.leaf(50, 92, 96, 40, bulge=0.45, fill=MID)
    # baş
    p.circle(50, 46, 34, fill=LIGHT)
    p.arc(22, 18, 70, 70, 120, 300, width=5)
    p.arc(34, 22, 86, 74, 250, 60, width=5)
    p.line([(50, 80), (50, 46), (40, 26)], width=3)
    p.line([(50, 62), (34, 48)], width=3)
    p.line([(50, 58), (68, 44)], width=3)


def pirasa(p: Pen):
    # dik çizilip döndürülür
    p.leaf(48, 44, 26, 6, bulge=0.12, fill=MID, vein=False)
    p.leaf(52, 44, 74, 6, bulge=0.12, fill=MID, vein=False)
    p.leaf(50, 44, 50, 2, bulge=0.12, fill=DARK, vein=False)
    p.poly([(41, 42), (59, 42), (59, 84), (41, 84)], fill=W)
    p.line([(41, 54), (59, 54)], width=3)
    for x in (42, 48, 54, 60):
        p.line([(50, 86), (x - 1, 95)], width=3)


def karnabahar(p: Pen):
    p.leaf(48, 90, 6, 52, bulge=0.3, fill=MID)
    p.leaf(52, 90, 94, 52, bulge=0.3, fill=MID)
    p.blob([(18, 22, 50, 54), (34, 12, 66, 44), (50, 22, 82, 54), (24, 38, 56, 70), (44, 38, 76, 70)])
    for x, y in ((34, 38), (50, 28), (66, 38), (40, 54), (60, 54)):
        p.arc(x - 8, y - 8, x + 8, y + 8, 180, 330, width=3)


def ispanak(p: Pen):
    p.leaf(50, 94, 14, 28, bulge=0.33, fill=MID)
    p.leaf(50, 94, 86, 28, bulge=0.33, fill=MID)
    p.leaf(50, 94, 50, 6, bulge=0.33, fill=DARK)


def kereviz(p: Pen):
    for x1 in (22, 50, 78):
        p.line([(50, 58), (x1, 26)], width=8)
        p.line([(50, 58), (x1, 26)], width=3, fill=LIGHT)
        for dx in (-9, 0, 9):
            p.leaf(x1, 28, x1 + dx, 10, bulge=0.45, fill=MID, vein=False)
    p.ellipse(24, 52, 76, 94, fill=LIGHT)
    for x in (38, 50, 62):
        p.line([(x, 92), (x + (x - 50) * 0.4, 99)], width=3)
    p.arc(32, 60, 68, 88, 200, 240, width=4)


def turp(p: Pen):
    p.leaf(48, 40, 22, 6, fill=MID)
    p.leaf(52, 40, 78, 6, fill=MID)
    p.line([(50, 84), (52, 99)], width=4)
    p.circle(50, 62, 24, fill=DARK)
    p.circle(42, 54, 4, fill=W, outline=None, width=0)


def pancar(p: Pen):
    p.leaf(46, 36, 16, 2, bulge=0.3, fill=MID)
    p.leaf(54, 36, 84, 2, bulge=0.3, fill=MID)
    p.line([(50, 86), (60, 99)], width=4)
    pts = []
    for i in range(40):
        t = 2 * math.pi * i / 40
        x = 50 + 30 * math.sin(t)
        y = 60 - 26 * math.cos(t) + (8 if math.cos(t) < 0 else 0) * (-math.cos(t))
        pts.append((x, y))
    p.poly(pts, fill=40)
    p.arc(30, 44, 70, 84, 200, 240, width=4, fill=W)


def enginar(p: Pen):
    p.poly([(44, 82), (56, 82), (54, 98), (46, 98)], fill=MID)
    p.ellipse(22, 14, 78, 88, fill=LIGHT)
    for y, half in ((30, 16), (46, 24), (62, 24), (76, 16)):
        n = 3 if half > 18 else 2
        step = 2 * half / n
        for i in range(n):
            x0 = 50 - half + i * step
            p.line([(x0, y - 8), (x0 + step / 2, y + 4), (x0 + step, y - 8)], width=4)


def roka(p: Pen):
    p.line([(50, 98), (50, 10)], width=5)
    for y, s in ((22, 12), (40, 18), (60, 22), (78, 16)):
        p.ellipse(50 - s - 14, y - 9, 50 - 4, y + 9, fill=MID)
        p.ellipse(54, y - 9, 54 + s + 10, y + 9, fill=MID)
    p.ellipse(40, 2, 60, 24, fill=MID)
    p.line([(50, 98), (50, 10)], width=4)


def taze_sogan(p: Pen):
    for x in (34, 50, 66):
        p.line([(x, 66), (x + (x - 50) * 0.6, 6)], width=9)
        p.line([(x, 66), (x + (x - 50) * 0.6, 6)], width=3, fill=MID)
    for x in (34, 50, 66):
        p.ellipse(x - 10, 62, x + 10, 86, fill=W)
        for dx in (-5, 0, 5):
            p.line([(x, 86), (x + dx, 96)], width=3)


def bakla(p: Pen):
    p.poly([(10, 70), (20, 52), (48, 34), (78, 22), (92, 26), (86, 40), (60, 60), (28, 78), (14, 80)], fill=MID)
    for cx, cy in ((30, 62), (50, 49), (70, 37)):
        p.ellipse(cx - 9, cy - 7, cx + 9, cy + 7, fill=LIGHT, width=4)
    p.line([(92, 26), (98, 16)], width=5)


def semizotu(p: Pen):
    p.line([(50, 98), (50, 50), (28, 24)], width=5)
    p.line([(50, 64), (76, 36)], width=5)
    p.line([(50, 50), (58, 14)], width=5)
    for x, y in ((28, 20), (20, 32), (36, 34), (76, 30), (86, 42), (66, 44), (58, 10), (46, 20), (68, 20),
                 (38, 70), (62, 78)):
        p.ellipse(x - 8, y - 6, x + 8, y + 6, fill=MID, width=4)


def kabak(p: Pen):
    # dik çizilip döndürülür
    p.ellipse(32, 18, 68, 96, fill=MID)
    p.poly([(42, 22), (58, 22), (56, 6), (44, 6)], fill=DARK)
    for x in (42, 50, 58):
        p.line([(x, 34), (x, 86)], width=3, fill=LIGHT)


def taze_fasulye(p: Pen):
    for off in (-16, 0, 16):
        pts = [(36 + off, 94), (28 + off, 62), (36 + off, 28), (54 + off, 6)]
        p.line(pts, width=13)
        p.line(pts, width=5, fill=MID)


def bamya(p: Pen):
    for cx, ang in ((36, -12), (64, 12)):
        tip = (cx + ang * 1.2, 96)
        p.poly([(cx - 12, 28), (cx + 12, 28), tip], fill=MID)
        p.line([(cx, 30), tip], width=3)
        p.poly([(cx - 10, 30), (cx + 10, 30), (cx + 6, 14), (cx - 6, 14)], fill=DARK)
        p.line([(cx, 14), (cx - ang * 0.3, 4)], width=5)


def balkabagi(p: Pen):
    p.poly([(46, 26), (54, 26), (56, 8), (46, 10)], fill=DARK)
    p.ellipse(6, 26, 50, 90, fill=LIGHT)
    p.ellipse(50, 26, 94, 90, fill=LIGHT)
    p.ellipse(28, 24, 72, 92, fill=LIGHT)


CUSTOM = {
    "Nar": nar, "Ayva": ayva, "İncir": incir, "Dut": dut, "Böğürtlen": bogurtlen,
    "Kayısı": kayisi, "Erik": erik, "Can erik": can_erik, "Yenidünya": yenidunya,
    "Trabzon hurması": trabzon_hurmasi, "Greyfurt": greyfurt, "Mandalina": mandalina,
    "Vişne": visne, "Nektarin": nektarin,
    "Lahana": lahana, "Pırasa": (pirasa, -40), "Karnabahar": karnabahar, "Ispanak": ispanak,
    "Kereviz": kereviz, "Turp": turp, "Pancar": pancar, "Enginar": enginar, "Roka": roka,
    "Taze soğan": taze_sogan, "Bakla": bakla, "Semizotu": semizotu, "Kabak": (kabak, -50),
    "Taze fasulye": taze_fasulye, "Bamya": bamya, "Balkabağı": balkabagi,
}


# ------------------------------------------------------------------ balıklar

# Tür -> gövde ve desen özellikleri
FISH = {
    #            yükseklik, uzunluk, sırt rengi, desen
    "Hamsi":     dict(h=15, L=78, back=MID, pattern="stripe", snout=6),
    "İstavrit":  dict(h=22, L=74, back=MID, pattern="scutes", eye=7),
    "Mezgit":    dict(h=22, L=76, back=LIGHT, pattern="barbel", dorsal=3),
    "Kalkan":    dict(flat=True),
    "Levrek":    dict(h=26, L=74, back=MID, pattern="spiny"),
    "Kefal":     dict(h=24, L=74, back=MID, pattern="lines", blunt=True),
    "Zargana":   dict(h=8, L=74, back=MID, pattern="needle"),
    "Barbunya":  dict(h=24, L=70, back=DARK, pattern="whiskers", blunt=True),
    "Tekir":     dict(h=24, L=70, back=MID, pattern="whiskers_striped", blunt=True),
    "İzmarit":   dict(h=26, L=70, back=LIGHT, pattern="spot"),
    "Çipura":    dict(h=36, L=68, back=LIGHT, pattern="band"),
    "Kolyoz":    dict(h=20, L=76, back=MID, pattern="waves_spots", finlets=True),
    "Uskumru":   dict(h=20, L=76, back=MID, pattern="waves", finlets=True),
    "Sardalya":  dict(h=18, L=74, back=MID, pattern="dots"),
    "Çinekop":   dict(h=22, L=72, back=MID, pattern="jaw"),
    "Sarıkanat": dict(h=24, L=74, back=MID, pattern="jaw"),
    "Lüfer":     dict(h=26, L=76, back=DARK, pattern="jaw"),
    "Palamut":   dict(h=26, L=76, back=MID, pattern="oblique", finlets=True),
    "Torik":     dict(h=28, L=78, back=DARK, pattern="oblique", finlets=True),
}


def _thickness(t: float, h: float, blunt: bool) -> float:
    base = (4 * t * (1 - t)) ** (0.45 if blunt else 0.6)
    return h * base * (1 - 0.55 * t) + 2.2 * t


def fish(p: Pen, spec: dict):
    if spec.get("flat"):
        _flatfish(p)
        return
    h, L = spec["h"], spec["L"]
    x0 = (100 - L - 16) / 2 + (6 if spec.get("pattern") == "needle" else 0)
    cy = 50
    blunt = spec.get("blunt", False)
    xe = x0 + L
    pe = _thickness(0.97, h, blunt)

    # yüzgeçler (gövdenin arkasında)
    dorsal = spec.get("dorsal", 1)
    if spec.get("pattern") == "spiny":
        ds = x0 + L * 0.32
        p.poly([(ds, cy - _thickness(0.32, h, blunt) + 2), (ds + 4, cy - h - 10), (ds + 9, cy - h - 4),
                (ds + 13, cy - h - 9), (ds + 17, cy - h - 3), (ds + 20, cy - _thickness(0.52, h, blunt) + 2)],
               fill=MID, width=4)
        ds2 = x0 + L * 0.6
        p.poly([(ds2, cy - _thickness(0.6, h, blunt) + 2), (ds2 + 6, cy - h * 0.9 - 6),
                (ds2 + 16, cy - _thickness(0.8, h, blunt) + 1)], fill=MID, width=4)
    else:
        for i in range(dorsal):
            a = 0.3 + i * (0.5 / dorsal) if dorsal > 1 else 0.38
            b = a + (0.42 / dorsal if dorsal > 1 else 0.24)
            xa, xb = x0 + L * a, x0 + L * b
            top = cy - _thickness((a + b) / 2, h, blunt) - max(6, h * 0.45)
            p.poly([(xa, cy - _thickness(a, h, blunt) + 2), (xa + (xb - xa) * 0.35, top),
                    (xb, cy - _thickness(b, h, blunt) + 2)], fill=MID, width=4)
    # anal yüzgeç
    aa, ab = 0.62, 0.8
    p.poly([(x0 + L * aa, cy + _thickness(aa, h, blunt) - 2),
            (x0 + L * (aa + 0.06), cy + _thickness(aa, h, blunt) + max(5, h * 0.35)),
            (x0 + L * ab, cy + _thickness(ab, h, blunt) - 2)], fill=MID, width=4)
    # kuyruk
    fork = max(10, h * 0.85)
    p.poly([(xe - 2, cy - pe), (xe + 16, cy - fork), (xe + 9, cy), (xe + 16, cy + fork), (xe - 2, cy + pe)],
           fill=MID)

    # gövde
    top, bot = [], []
    for i in range(41):
        t = i / 40
        th = _thickness(t, h, blunt)
        x = x0 + L * t
        top.append((x, cy - th))
        bot.append((x, cy + th * (0.92 if not spec.get("flatbelly") else 0.7)))
    body = top + bot[::-1]
    p.poly(body, fill=W)
    # sırt rengi: üst yarı
    back = spec.get("back", MID)
    if back != W:
        upper = [(x, y + p.lw / p.k * 0.8) for x, y in top[2:-2]]
        mid = [(x, cy - _thickness((x - x0) / L, h, blunt) * 0.05) for x, _ in top[2:-2]][::-1]
        p.poly(upper + mid, fill=back, outline=None)

    pat = spec.get("pattern", "")
    lw3 = 3
    if pat == "stripe":
        p.line([(x0 + L * 0.2, cy + 1), (x0 + L * 0.92, cy + 1)], width=lw3, fill=W)
    elif pat == "scutes":
        pts = []
        for i in range(12):
            t = 0.25 + i * 0.06
            pts.append((x0 + L * t, cy + (2 if i % 2 else -2) + 3 - 6 * t))
        p.line(pts, width=3)
    elif pat == "barbel":
        p.line([(x0 + 8, cy + h * 0.5), (x0 + 9, cy + h * 0.5 + 6)], width=3)
    elif pat == "lines":
        for dy in (-0.45, 0.0, 0.4):
            p.line([(x0 + L * 0.3, cy + h * dy), (x0 + L * 0.85, cy + h * dy * 0.5)], width=2.5)
    elif pat == "needle":
        p.line([(x0 + 2, cy), (x0 - 16, cy + 1)], width=4)
    elif pat in ("whiskers", "whiskers_striped"):
        p.line([(x0 + 6, cy + h * 0.55), (x0 + 3, cy + h * 0.55 + 9)], width=3)
        p.line([(x0 + 10, cy + h * 0.6), (x0 + 8, cy + h * 0.6 + 9)], width=3)
        if pat == "whiskers_striped":
            p.line([(x0 + L * 0.3, cy - h * 0.15), (x0 + L * 0.88, cy - 1)], width=3, fill=DARK)
            p.line([(x0 + L * 0.3, cy + h * 0.2), (x0 + L * 0.88, cy + 2)], width=3, fill=DARK)
    elif pat == "spot":
        p.circle(x0 + L * 0.72, cy - 1, 5, fill=INK, outline=None, width=0)
    elif pat == "band":
        p.arc(x0 + 2, cy - h * 1.1, x0 + 26, cy + h * 0.2, 260, 330, width=5)
        p.circle(x0 + L * 0.26, cy - h * 0.1, 4, fill=DARK, outline=None, width=0)
        for dy in (-0.35, 0.0, 0.35):
            p.line([(x0 + L * 0.35, cy + h * dy), (x0 + L * 0.85, cy + h * dy * 0.4)], width=2, fill=MID)
    elif pat in ("waves", "waves_spots"):
        for i in range(5):
            xs = x0 + L * (0.3 + i * 0.12)
            ytop = cy - _thickness((xs - x0) / L, h, blunt) + 3
            p.line([(xs, ytop), (xs + 3, ytop + 4), (xs - 1, ytop + 8), (xs + 2, cy - 2)], width=3, fill=INK)
        if pat == "waves_spots":
            for i in range(5):
                p.circle(x0 + L * (0.32 + i * 0.11), cy + h * 0.35, 1.8, fill=INK, outline=None, width=0)
    elif pat == "dots":
        for i in range(5):
            p.circle(x0 + L * (0.32 + i * 0.1), cy - h * 0.15, 2.4, fill=INK, outline=None, width=0)
    elif pat == "jaw":
        p.line([(x0 + 1, cy + 2), (x0 + 13, cy + 5)], width=3)
    elif pat == "oblique":
        for i in range(5):
            xs = x0 + L * (0.3 + i * 0.12)
            p.line([(xs, cy - _thickness((xs - x0) / L, h, blunt) + 3), (xs + 10, cy - 2)], width=3, fill=INK)

    if spec.get("finlets"):
        for i in range(3):
            xf = x0 + L * (0.84 + i * 0.045)
            th = _thickness((xf - x0) / L, h, blunt)
            p.poly([(xf, cy - th), (xf + 2, cy - th - 4), (xf + 3.5, cy - th)], fill=INK, width=2)
            p.poly([(xf, cy + th), (xf + 2, cy + th + 4), (xf + 3.5, cy + th)], fill=INK, width=2)

    # solungaç ve göz
    gx = x0 + L * 0.2
    p.arc(gx - 10, cy - h * 0.7, gx + 2, cy + h * 0.7, 300, 60, width=3.5)
    eye_r = spec.get("eye", max(3.2, h * 0.17))
    p.circle(x0 + L * 0.09 + 2, cy - h * 0.2, eye_r, fill=W, width=3)
    p.circle(x0 + L * 0.09 + 2, cy - h * 0.2, eye_r * 0.45, fill=INK, outline=None, width=0)


def _flatfish(p: Pen):
    """Kalkan: yassı, yuvarlak gövde, yüzgeç saçağı, benekler."""
    p.poly([(80, 50), (96, 36), (93, 50), (96, 64)], fill=MID)
    p.ellipse(4, 14, 86, 86, fill=MID, width=4)
    p.ellipse(10, 20, 80, 80, fill=LIGHT)
    for x, y in ((36, 40), (52, 34), (60, 52), (44, 58), (30, 60), (64, 68), (56, 26)):
        p.circle(x, y, 3.5, fill=DARK, outline=None, width=0)
    p.circle(24, 36, 4, fill=W, width=3)
    p.circle(30, 28, 4, fill=W, width=3)
    p.arc(10, 40, 34, 64, 130, 230, width=4)


def render_icon(name: str, kind: str, px: int) -> Image.Image:
    """Ürün ikonunu px x px gri tonlu görüntü olarak döndürür."""
    if kind == "balik":
        pen = Pen(px)
        fish(pen, FISH.get(name, dict(h=22, L=74, back=MID)))
        return pen.done(px)
    if name in CUSTOM:
        fn = CUSTOM[name]
        rot = 0
        if isinstance(fn, tuple):
            fn, rot = fn
        pen = Pen(px)
        fn(pen)
        return pen.done(px, rotate=rot)
    img = Image.new("L", (px * SS, px * SS), 255)
    ch = EMOJI.get(name, "🌿" if kind == "sebze" else "🍏")
    f = ImageFont.truetype(str(FONT_DIR / "NotoEmoji.ttf"), int(px * SS * 0.86))
    try:
        f.set_variation_by_axes([600])
    except Exception:  # noqa: BLE001
        pass
    ImageDraw.Draw(img).text((px * SS / 2, px * SS / 2), ch, font=f, fill=0, anchor="mm")
    return img.resize((px, px), Image.LANCZOS)
