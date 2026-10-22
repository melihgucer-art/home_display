"""GitHub Actions iş akışları: zamanlama, komutlar ve yollar."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"


def load(name: str) -> dict:
    data = yaml.safe_load((WF / name).read_text())
    # YAML 1.1'de "on" anahtarı True olarak okunur
    data["on"] = data.pop(True, data.get("on"))
    return data


def _expand(field: str, lo: int, hi: int) -> list[int]:
    out = []
    for part in field.split(","):
        if part == "*":
            out += list(range(lo, hi + 1))
        elif "/" in part:
            base, step = part.split("/")
            start = lo if base == "*" else int(base)
            out += list(range(start, hi + 1, int(step)))
        elif "-" in part:
            a, b = map(int, part.split("-"))
            out += list(range(a, b + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def _simulate_day(run_minutes_utc, start=dt.datetime(2026, 10, 22, 0, 0, tzinfo=dt.timezone.utc), last=None):
    """Verilen UTC dakikalarında çalışan zamanlanmış görevleri canlandırır; çizim zamanlarını döndürür."""
    import sys
    sys.path.insert(0, str(ROOT / "server"))
    import should_render as sr
    renders = []
    for minute in run_minutes_utc:
        now = start + dt.timedelta(minutes=minute)
        if sr.should_render(last, now):
            last = now.isoformat()
            renders.append(now.astimezone(ZoneInfo("Europe/Istanbul")).strftime("%H:%M"))
    return renders


def test_render_cron_is_hourly():
    crons = [c["cron"] for c in load("render.yml")["on"]["schedule"]]
    assert crons == ["7 * * * *"]


def test_hourly_runs_render_six_times_a_day_in_turkey_daytime():
    # 21 Ekim 21:07 TR'de güncellenmiş bir panodan başlayıp bir gün boyunca her saat :07'de çalış
    renders = _simulate_day([60 * h + 7 for h in range(24)], last="2026-10-21T18:07:00+00:00")
    assert renders == ["06:07", "09:07", "12:07", "15:07", "18:07", "21:07"]


def test_late_and_dropped_runs_are_caught_up():
    # 06:07, 07:07 ve 09:07 çalışmaları düştü, 12:07 çalışması 2 saat gecikti
    minutes = [60 * h + 7 for h in range(24) if h not in (3, 4, 6, 9)]
    renders = _simulate_day(minutes, last="2026-10-21T18:07:00+00:00")
    assert renders == ["08:07", "10:07", "13:07", "15:07", "18:07", "21:07"]


def test_no_renders_at_night():
    renders = _simulate_day([60 * h + 7 for h in range(24)], last="2026-10-21T18:07:00+00:00")
    assert not any("00:00" <= r < "06:00" for r in renders)


def test_should_render_edge_inputs():
    import sys
    sys.path.insert(0, str(ROOT / "server"))
    import should_render as sr
    now = dt.datetime(2026, 10, 22, 7, 0, tzinfo=dt.timezone.utc)  # 10:00 TR
    assert sr.should_render(None, now) and sr.should_render("", now) and sr.should_render("bozuk", now)
    assert sr.should_render("2026-10-22T05:59:59Z", now)       # 08:59 TR < 09:00 dilimi
    assert not sr.should_render("2026-10-22T06:00:01Z", now)   # 09:00 TR sonrası
    assert not sr.should_render("2026-10-22T06:30:00", now)     # saat dilimi yoksa UTC kabul
    # gece yarısından sonra: önceki günün 21:00 dilimi geçerli
    midnight = dt.datetime(2026, 10, 22, 0, 30, tzinfo=dt.timezone.utc)  # 03:30 TR
    assert sr.latest_slot(midnight).strftime("%d %H:%M") == "21 21:00"


def test_due_step_guards_every_later_step():
    steps = load("render.yml")["jobs"]["render"]["steps"]
    names = [s.get("name") or s.get("uses") or s.get("run") for s in steps]
    due_idx = next(i for i, s in enumerate(steps) if s.get("id") == "due")
    assert due_idx == 1
    for s in steps[due_idx + 1:]:
        assert "steps.due.outputs.render == 'yes'" in s.get("if", ""), names


def test_render_command_matches_cli():
    wf = load("render.yml")
    steps = wf["jobs"]["render"]["steps"]
    run = next(s["run"] for s in steps if s.get("name") == "Görüntüyü üret")
    assert "python3 server/home_display.py out/display.png" in run
    assert wf["permissions"]["contents"] == "write"
    assert "workflow_dispatch" in wf["on"]
    assert 'code" = 2' in run and "skip=1" in run
    publish = next(s for s in steps if s.get("name") == "display dalına yaz")
    assert publish["if"] == "steps.due.outputs.render == 'yes' && steps.render.outputs.skip != '1'"
    push = publish["run"]
    assert "git add display.png" in push and "push -qf" in push and push.rstrip().endswith("display")


def test_render_has_no_secrets_or_removed_features():
    text = (WF / "render.yml").read_text()
    assert "CALENDAR" not in text and "secrets." not in text


def test_kindle_package_bundles_xh():
    wf = load("kindle-package.yml")
    text = (WF / "kindle-package.yml").read_text()
    assert "pascalw/kindle-dash" in text and "v1.0.0-beta.4" in text
    assert "bin/xh" in text
    assert wf["permissions"]["contents"] == "write"


def test_tests_workflow_runs_pytest_with_busybox():
    wf = load("test.yml")
    text = (WF / "test.yml").read_text()
    assert "pytest" in text and "busybox" in text
    assert "push" in wf["on"]


def test_no_leftover_local_server_files():
    for p in ("docker-compose.yml", "server/Dockerfile", "server/home-display.service", "server/todo.txt",
              ".github/workflows/probe.yml"):
        assert not (ROOT / p).exists(), p
