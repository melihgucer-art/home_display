"""Erenköy / Kadıköy için sabit yerel veriler: mevsim ürünleri ve semt pazarları."""
from __future__ import annotations

import datetime as dt

# Ay -> (meyve, sebze, balık). Balıklar İstanbul (Marmara / Boğaz / Karadeniz) sezonuna göre.
MEVSIM: dict[int, tuple[list[str], list[str], list[str]]] = {
    1: (["Portakal", "Mandalina", "Greyfurt", "Limon", "Kivi", "Elma", "Armut"],
        ["Lahana", "Pırasa", "Karnabahar", "Brokoli", "Ispanak", "Kereviz", "Havuç", "Turp"],
        ["Hamsi", "İstavrit", "Mezgit", "Kalkan", "Levrek", "Kefal"]),
    2: (["Portakal", "Mandalina", "Greyfurt", "Limon", "Kivi", "Elma"],
        ["Lahana", "Pırasa", "Ispanak", "Karnabahar", "Brokoli", "Kereviz", "Havuç", "Roka"],
        ["Hamsi", "Mezgit", "İstavrit", "Kalkan", "Levrek", "Zargana"]),
    3: (["Portakal", "Limon", "Greyfurt", "Kivi", "Elma"],
        ["Ispanak", "Pırasa", "Enginar", "Marul", "Roka", "Taze soğan", "Havuç"],
        ["Mezgit", "Kalkan", "İstavrit", "Zargana", "Levrek", "Kefal"]),
    4: (["Çilek", "Yenidünya", "Limon", "Elma"],
        ["Enginar", "Bakla", "Bezelye", "Marul", "Ispanak", "Taze soğan", "Roka"],
        ["İstavrit", "Kalkan", "Zargana", "Barbunya"]),
    5: (["Çilek", "Yenidünya", "Can erik", "Kiraz"],
        ["Enginar", "Bakla", "Bezelye", "Semizotu", "Kabak", "Salatalık", "Marul"],
        ["İstavrit", "İzmarit", "Barbunya", "Levrek (çiftlik)", "Çipura (çiftlik)"]),
    6: (["Kiraz", "Vişne", "Kayısı", "Şeftali", "Dut", "Karpuz", "Kavun"],
        ["Domates", "Salatalık", "Biber", "Kabak", "Taze fasulye", "Patlıcan", "Semizotu"],
        ["İstavrit", "İzmarit", "Kolyoz", "Sardalya", "Levrek (çiftlik)", "Çipura (çiftlik)"]),
    7: (["Karpuz", "Kavun", "Şeftali", "Kayısı", "Erik", "Vişne", "Böğürtlen"],
        ["Domates", "Biber", "Patlıcan", "Kabak", "Taze fasulye", "Bamya", "Mısır", "Barbunya"],
        ["Sardalya", "Kolyoz", "İstavrit", "İzmarit", "Çinekop"]),
    8: (["Karpuz", "Kavun", "Üzüm", "İncir", "Şeftali", "Nektarin", "Armut"],
        ["Domates", "Biber", "Patlıcan", "Bamya", "Mısır", "Taze fasulye", "Kabak"],
        ["Sardalya", "Kolyoz", "Çinekop", "İstavrit", "Tekir"]),
    9: (["Üzüm", "İncir", "Armut", "Elma", "Ayva", "Nar", "Kavun"],
        ["Domates", "Biber", "Patlıcan", "Bamya", "Mısır", "Lahana", "Kabak"],
        ["Palamut", "Lüfer", "Çinekop", "Sardalya", "Barbunya", "Tekir"]),
    10: (["Nar", "Ayva", "Elma", "Armut", "Üzüm", "Mandalina", "Trabzon hurması"],
         ["Pırasa", "Lahana", "Karnabahar", "Ispanak", "Kereviz", "Balkabağı", "Brokoli", "Havuç"],
         ["Palamut", "Lüfer", "Sarıkanat", "İstavrit", "Barbunya", "Uskumru", "Çipura"]),
    11: (["Mandalina", "Portakal", "Nar", "Ayva", "Trabzon hurması", "Kivi", "Kestane"],
         ["Pırasa", "Lahana", "Karnabahar", "Brokoli", "Ispanak", "Kereviz", "Balkabağı", "Turp"],
         ["Hamsi", "Palamut", "Lüfer", "Torik", "İstavrit", "Levrek", "Kalkan"]),
    12: (["Mandalina", "Portakal", "Greyfurt", "Nar", "Ayva", "Kivi", "Kestane"],
         ["Pırasa", "Lahana", "Karnabahar", "Brokoli", "Ispanak", "Kereviz", "Havuç", "Pancar"],
         ["Hamsi", "Lüfer", "İstavrit", "Mezgit", "Levrek", "Kalkan", "Kefal"]),
}


def balik_notu(today: dt.date) -> str:
    """Denizlerde ticari av yasağı 15 Nisan - 31 Ağustos arasıdır."""
    start, end = dt.date(today.year, 4, 15), dt.date(today.year, 8, 31)
    if start <= today <= end:
        return f"Av yasağı {(end - today).days + 1} gün daha sürüyor, tezgâhta çiftlik balığı çok"
    if dt.date(today.year, 9, 1) <= today <= dt.date(today.year, 9, 14):
        return "Av sezonu açıldı, tezgâhlar taze balıkla doldu"
    if dt.date(today.year, 4, 1) <= today < start:
        return f"Av yasağı {(start - today).days} gün sonra başlıyor"
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
