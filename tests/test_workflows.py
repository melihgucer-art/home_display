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


def test_render_runs_six_times_a_day_in_turkey_daytime():
    crons = [c["cron"] for c in load("render.yml")["on"]["schedule"]]
    runs = []
    for c in crons:
        minute, hour, dom, mon, dow = c.split()
        assert (dom, mon, dow) == ("*", "*", "*")
        for h in _expand(hour, 0, 23):
            for m in _expand(minute, 0, 59):
                runs.append((h, m))
    assert len(runs) == 6, runs
    tr = sorted(
        dt.datetime(2026, 10, 21, h, m, tzinfo=dt.timezone.utc).astimezone(ZoneInfo("Europe/Istanbul")).strftime("%H:%M")
        for h, m in runs
    )
    assert tr == ["06:07", "09:07", "12:07", "15:07", "18:07", "21:07"]
    # Kindle'ın gece saatleri (00-05) bulut güncellemeleriyle çakışmamalı
    assert all(not (0 <= int(t[:2]) <= 5) for t in tr)


def test_render_command_matches_cli():
    wf = load("render.yml")
    steps = wf["jobs"]["render"]["steps"]
    run = next(s["run"] for s in steps if s.get("name") == "Görüntüyü üret")
    assert "python3 server/home_display.py out/display.png" in run
    assert wf["permissions"]["contents"] == "write"
    assert "workflow_dispatch" in wf["on"]
    assert 'code" = 2' in run and "skip=1" in run
    publish = next(s for s in steps if s.get("name") == "display dalına yaz")
    assert publish["if"] == "steps.render.outputs.skip != '1'"
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
