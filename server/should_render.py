#!/usr/bin/env python3
"""Zamanlanmış çalışmada panonun yeniden çizilmesi gerekiyor mu?

GitHub zamanlanmış görevleri saatlerce geciktirebiliyor ya da atlayabiliyor. Bu yüzden görev her saat
çalışır ve yalnızca son güncellemeden bu yana yeni bir güncelleme saati (Türkiye saatiyle 06, 09, 12,
15, 18, 21) geçtiyse çizer. Böylece pano günde 6 kez değişir, kaçan bir çalışma bir sonraki saatte telafi edilir.

Kullanım: python3 should_render.py <son-güncelleme-ISO-zamanı|boş>   -> "yes" ya da "no" yazar
"""
from __future__ import annotations

import datetime as dt
import sys
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")
SLOT_HOURS = (6, 9, 12, 15, 18, 21)


def latest_slot(now: dt.datetime) -> dt.datetime:
    """now anına kadar geçmiş en son güncelleme saati (Türkiye saatiyle)."""
    local = now.astimezone(TZ)
    for days_back in range(0, 2):
        day = (local - dt.timedelta(days=days_back)).date()
        for hour in sorted(SLOT_HOURS, reverse=True):
            slot = dt.datetime(day.year, day.month, day.day, hour, tzinfo=TZ)
            if slot <= local:
                return slot
    raise AssertionError("ulaşılamaz")


def should_render(last_update: str | None, now: dt.datetime) -> bool:
    if not last_update or not last_update.strip():
        return True
    try:
        last = dt.datetime.fromisoformat(last_update.strip().replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.timezone.utc)
    return last < latest_slot(now)


def main(argv: list[str]) -> int:
    last = argv[1] if len(argv) > 1 else ""
    print("yes" if should_render(last, dt.datetime.now(dt.timezone.utc)) else "no")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
