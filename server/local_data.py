"""Erenköy / Kadıköy için sabit yerel veriler: mevsim ürünleri ve semt pazarları."""
from __future__ import annotations

import datetime as dt

# Ay -> (meyve, sebze, balık); her kategoride 6 ürün, önem sırasıyla.
# Balıklar İstanbul (Marmara / Boğaz / Karadeniz) sezonuna göre.
MEVSIM: dict[int, tuple[list[str], list[str], list[str]]] = {
    1: (["Portakal", "Mandalina", "Greyfurt", "Limon", "Kivi", "Elma"],
        ["Lahana", "Pırasa", "Karnabahar", "Ispanak", "Kereviz", "Havuç"],
        ["Hamsi", "İstavrit", "Mezgit", "Kalkan", "Levrek", "Kefal"]),
    2: (["Portakal", "Mandalina", "Greyfurt", "Limon", "Kivi", "Armut"],
        ["Pırasa", "Lahana", "Ispanak", "Brokoli", "Kereviz", "Turp"],
        ["Hamsi", "Mezgit", "İstavrit", "Kalkan", "Zargana", "Levrek"]),
    3: (["Portakal", "Limon", "Greyfurt", "Kivi", "Elma", "Çilek"],
        ["Ispanak", "Enginar", "Marul", "Roka", "Taze soğan", "Pırasa"],
        ["Mezgit", "Kalkan", "İstavrit", "Zargana", "Kefal", "Levrek"]),
    4: (["Çilek", "Yenidünya", "Limon", "Portakal", "Elma", "Kivi"],
        ["Enginar", "Bakla", "Bezelye", "Marul", "Taze soğan", "Ispanak"],
        ["İstavrit", "Kalkan", "Zargana", "Barbunya", "Mezgit", "Kefal"]),
    5: (["Çilek", "Yenidünya", "Can erik", "Kiraz", "Dut", "Limon"],
        ["Enginar", "Bakla", "Bezelye", "Semizotu", "Kabak", "Salatalık"],
        ["İstavrit", "İzmarit", "Barbunya", "Kefal", "Çipura", "Levrek"]),
    6: (["Kiraz", "Vişne", "Kayısı", "Şeftali", "Dut", "Karpuz"],
        ["Domates", "Salatalık", "Biber", "Kabak", "Taze fasulye", "Semizotu"],
        ["İstavrit", "İzmarit", "Kolyoz", "Sardalya", "Çipura", "Levrek"]),
    7: (["Karpuz", "Kavun", "Şeftali", "Kayısı", "Erik", "Böğürtlen"],
        ["Domates", "Biber", "Patlıcan", "Bamya", "Mısır", "Barbunya"],
        ["Sardalya", "Kolyoz", "İstavrit", "İzmarit", "Çinekop", "Kefal"]),
    8: (["Karpuz", "Kavun", "Üzüm", "İncir", "Nektarin", "Armut"],
        ["Domates", "Biber", "Patlıcan", "Bamya", "Mısır", "Taze fasulye"],
        ["Sardalya", "Kolyoz", "Çinekop", "İstavrit", "Tekir", "İzmarit"]),
    9: (["Üzüm", "İncir", "Armut", "Elma", "Nar", "Ayva"],
        ["Domates", "Biber", "Patlıcan", "Mısır", "Lahana", "Kabak"],
        ["Palamut", "Lüfer", "Çinekop", "Sardalya", "Barbunya", "Tekir"]),
    10: (["Nar", "Ayva", "Elma", "Armut", "Mandalina", "Trabzon hurması"],
         ["Pırasa", "Lahana", "Karnabahar", "Ispanak", "Kereviz", "Balkabağı"],
         ["Palamut", "Lüfer", "Sarıkanat", "İstavrit", "Barbunya", "Uskumru"]),
    11: (["Mandalina", "Portakal", "Nar", "Ayva", "Trabzon hurması", "Kestane"],
         ["Pırasa", "Lahana", "Karnabahar", "Brokoli", "Ispanak", "Balkabağı"],
         ["Hamsi", "Palamut", "Lüfer", "Torik", "İstavrit", "Kalkan"]),
    12: (["Mandalina", "Portakal", "Greyfurt", "Nar", "Kivi", "Kestane"],
         ["Pırasa", "Lahana", "Karnabahar", "Brokoli", "Kereviz", "Pancar"],
         ["Hamsi", "Lüfer", "İstavrit", "Mezgit", "Levrek", "Kalkan"]),
}


def balik_notu(today: dt.date) -> str:
    """Denizlerde ticari av yasağı 15 Nisan - 31 Ağustos arasıdır."""
    start, end = dt.date(today.year, 4, 15), dt.date(today.year, 8, 31)
    if start <= today <= end:
        return f"Av yasağı: {(end - today).days + 1} gün kaldı"
    if dt.date(today.year, 9, 1) <= today <= dt.date(today.year, 9, 14):
        return "Av sezonu açıldı"
    if dt.date(today.year, 4, 1) <= today < start:
        return f"Av yasağına {(start - today).days} gün"
    return ""


# Kadıköy Belediyesi semt pazarları listesi (Erenköy çevresi öne alınmıştır).
# Hafta günü: 0 = Pazartesi
PAZARLAR: list[tuple[str, list[int], str]] = [
    ("Erenköy Pazarı", [3], "Çobanyıldızı Sk."),
    ("Göztepe Pazarı", [0], "Kültür Sk."),
    ("Organik Halk Pazarı", [2], "Göztepe Özgürlük Parkı"),
    ("Kozyatağı Pazarı", [4], "Cemil Akdoğan Sk."),
    ("Salı Pazarı", [1, 4], "Hasanpaşa"),
    ("Sahrayıcedit Pazarı", [5], "Sahrayıcedit"),
    ("Koşuyolu Pazarı", [6], "Cenap Şahabettin Sk."),
]


def pazarlar(day: dt.date) -> list[str]:
    return [name for name, days, _ in PAZARLAR if day.weekday() in days]


# Nöbetçi eczane listesinde Erenköy'e yakınlık sırası
YAKIN_MAHALLELER = ["Erenköy", "19 Mayıs", "Suadiye", "Göztepe", "Caddebostan",
                    "Kozyatağı", "Sahrayıcedit", "Bostancı", "Merdivenköy", "Feneryolu"]


def ay_evresi(day: dt.date) -> str:
    """Basit ay evresi hesabı (referans yeni ay: 6 Ocak 2000 18:14 UTC)."""
    ref = dt.datetime(2000, 1, 6, 18, 14)
    days = (dt.datetime(day.year, day.month, day.day, 12) - ref).total_seconds() / 86400
    age = days % 29.530588
    names = [(1.85, "Yeni ay"), (5.54, "Hilal"), (9.23, "İlk dördün"), (12.92, "Şişkin ay"),
             (16.61, "Dolunay"), (20.30, "Şişkin ay"), (23.99, "Son dördün"), (27.68, "Hilal"),
             (29.54, "Yeni ay")]
    return next(n for limit, n in names if age < limit)
