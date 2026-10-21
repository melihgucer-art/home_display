"""Kindle betikleri: Kindle'a özgü komutlar (eips, lipc, xh…) sahteleriyle değiştirilerek gerçek kabukta çalıştırılır.

Kindle 4 busybox ash kullanır; busybox kuruluysa testler onunla da çalışır (CI'da kurulu).
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "kindle" / "extensions" / "homedisplay"

SHELLS = [["dash"]] + ([["busybox", "sh"]] if shutil.which("busybox") else [])

PNG_A = b"\x89PNG\r\n\x1a\n" + b"A" * 64
PNG_B = b"\x89PNG\r\n\x1a\n" + b"B" * 64


def _exe(path: Path, body: str):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class Kindle:
    """Geçici bir Kindle ortamı: eklenti kopyası + sahte komutlar + çağrı günlüğü."""

    def __init__(self, tmp: Path, shell: list[str]):
        self.shell = shell
        self.ext = tmp / "homedisplay"
        shutil.copytree(EXT, self.ext)
        self.stub = tmp / "stub"
        self.stub.mkdir()
        self.calls = tmp / "calls.log"
        self.calls.touch()
        self.state = tmp / "state"
        self.state.mkdir()
        self.tmpdir = tmp / "tmp"
        self.tmpdir.mkdir()
        # betiklerdeki /tmp yollarını test dizinine yönlendir
        for f in (self.ext / "bin").glob("*.sh"):
            f.write_text(f.read_text().replace("/tmp/", f"{self.tmpdir}/"))
        log = f'echo "$(basename "$0") $*" >> "{self.calls}"\n'
        _exe(self.stub / "eips", log)
        _exe(self.stub / "sleep", log)  # beklemeleri atla
        _exe(self.stub / "lipc-set-prop", log)
        _exe(self.stub / "lipc-get-prop", log + f'''
case "$2" in
  cmState) cat "{self.state}/wifi" 2>/dev/null || echo CONNECTED ;;
  battLevel) cat "{self.state}/batt" 2>/dev/null || echo 80 ;;
esac
''')
        # indirme: state/body içeriğini yazar; state/fail varsa yarım dosya bırakıp hata döner
        dl = log + f'''
out=""
while [ $# -gt 0 ]; do
  case "$1" in -o|-O) out="$2"; shift ;; esac
  shift
done
if [ -f "{self.state}/fail" ]; then echo YARIM > "$out"; exit 1; fi
cat "{self.state}/body" > "$out"
'''
        _exe(self.ext / "bin" / "xh", dl)
        _exe(self.stub / "wget", dl)
        _exe(self.stub / "curl", dl)
        self.set_body(PNG_A)

    def set_body(self, data: bytes):
        (self.state / "body").write_bytes(data)

    def config(self, **kv):
        cfg = self.ext / "config.sh"
        text = cfg.read_text()
        for k, v in kv.items():
            lines = [l for l in text.splitlines() if not l.startswith(f"{k}=")]
            lines.append(f'{k}="{v}"')
            text = "\n".join(lines) + "\n"
        cfg.write_text(text)

    def run(self, snippet: str, hour: str = "12") -> subprocess.CompletedProcess:
        _exe(self.stub / "date", f'case "$1" in +%H) echo {hour} ;; *) /bin/date "$@" ;; esac\n')
        script = self.ext / "bin" / "_test.sh"
        # busybox sleep'i kendi içinden çalıştırır (PATH'e bakmaz); fonksiyon her iki kabukta da önceliklidir
        fake_sleep = f'sleep() {{ echo "sleep $*" >> "{self.calls}"; }}\n'
        script.write_text('#!/bin/sh\n' + fake_sleep + '. "$(dirname "$0")/common.sh"\n' + snippet + "\n")
        env = {"PATH": f"{self.stub}:{os.environ['PATH']}", "HOME": str(self.tmpdir)}
        return subprocess.run(self.shell + [str(script)], capture_output=True, text=True, env=env, timeout=20)

    def log(self) -> list[str]:
        return self.calls.read_text().splitlines()

    def eips(self) -> list[str]:
        return [l for l in self.log() if l.startswith("eips")]

    @property
    def img(self) -> Path:
        return self.tmpdir / "homedisplay.png"

    def reset_log(self):
        self.calls.write_text("")


@pytest.fixture(params=SHELLS, ids=lambda s: " ".join(s))
def kindle(tmp_path, request):
    return Kindle(tmp_path, request.param)


def test_scripts_parse(kindle):
    for f in (kindle.ext / "bin").glob("*.sh"):
        r = subprocess.run(kindle.shell + ["-n", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f.name}: {r.stderr}"
    r = subprocess.run(kindle.shell + ["-n", str(kindle.ext / "config.sh")], capture_output=True, text=True)
    assert r.returncode == 0


def test_first_refresh_draws_full(kindle):
    r = kindle.run("refresh 1")
    assert r.returncode == 0, r.stderr
    assert kindle.img.read_bytes() == PNG_A
    assert any(l.startswith("eips -f -g") for l in kindle.eips())
    assert not (kindle.tmpdir / "homedisplay.png.tmp").exists()


def test_unchanged_image_is_not_redrawn(kindle):
    kindle.run("refresh 1")
    kindle.reset_log()
    kindle.run("refresh 0")
    assert not any("-g" in l for l in kindle.eips()), "aynı görüntü yeniden çizilmemeli"
    assert "değişmemiş" in (kindle.tmpdir / "homedisplay.log").read_text()


def test_changed_image_partial_refresh(kindle):
    kindle.run("refresh 1")
    kindle.set_body(PNG_B)
    kindle.reset_log()
    kindle.run("refresh 0")
    assert any(l.startswith("eips -g") for l in kindle.eips())
    assert kindle.img.read_bytes() == PNG_B


def test_unchanged_image_full_refresh_still_draws(kindle):
    """Tam yenileme turunda görüntü aynı olsa da çizilir (gölgeyi temizlemek için)."""
    kindle.run("refresh 1")
    kindle.reset_log()
    kindle.run("refresh 1")
    assert any(l.startswith("eips -f -g") for l in kindle.eips())


def test_download_failure_keeps_old_image(kindle):
    kindle.run("refresh 1")
    (kindle.state / "fail").touch()
    kindle.reset_log()
    r = kindle.run("refresh 0")
    assert r.returncode == 0
    assert kindle.img.read_bytes() == PNG_A, "eski görüntü korunmalı"
    assert any("Sunucuya ulasilamadi" in l for l in kindle.eips())
    assert not (kindle.tmpdir / "homedisplay.png.tmp").exists()


def test_empty_download_is_failure(kindle):
    kindle.run("refresh 1")
    kindle.set_body(b"")
    kindle.reset_log()
    kindle.run("refresh 0")
    assert kindle.img.read_bytes() == PNG_A
    assert any("Sunucuya ulasilamadi" in l for l in kindle.eips())
    assert not (kindle.tmpdir / "homedisplay.png.tmp").exists()


def test_wifi_never_connects(kindle):
    (kindle.state / "wifi").write_text("NA\n")
    r = kindle.run("refresh 1; echo rc=$?")
    assert "rc=1" in r.stdout
    assert any("Wi-Fi yok" in l for l in kindle.eips())
    assert not any(l.startswith(("xh", "wget")) for l in kindle.log()), "Wi-Fi yokken indirme denenmemeli"
    assert sum(1 for l in kindle.log() if l.startswith("sleep")) == 30  # ~30 sn bekledi


@pytest.mark.parametrize("batt,warn", [("9", True), ("14", True), ("15", False), ("100", False),
                                       ("", False), ("abc", False), ("9%", False)])
def test_battery_warning(kindle, batt, warn):
    (kindle.state / "batt").write_text(batt + "\n")
    r = kindle.run("refresh 1")
    assert r.returncode == 0
    assert any("Pil" in l for l in kindle.eips()) == warn


def test_wifi_off_between(kindle):
    kindle.config(WIFI_OFF_BETWEEN=1)
    kindle.run("refresh 1")
    assert any("wirelessEnable 0" in l for l in kindle.log())


def test_wifi_stays_on_by_default(kindle):
    kindle.run("refresh 1")
    assert not any("wirelessEnable 0" in l for l in kindle.log())


def test_https_uses_xh(kindle):
    kindle.run("refresh 1")
    assert any(l.startswith("xh -d -q -o") and l.endswith("display.png") for l in kindle.log())
    assert not any(l.startswith("wget") for l in kindle.log())


def test_http_uses_wget(kindle):
    kindle.config(IMAGE_URL="http://192.168.1.10:8080/display.png")
    kindle.run("refresh 1")
    assert any(l.startswith("wget") for l in kindle.log())


def test_https_without_xh_warns_and_falls_back(kindle):
    (kindle.ext / "bin" / "xh").unlink()
    kindle.run("refresh 1")
    assert "bin/xh yok" in (kindle.tmpdir / "homedisplay.log").read_text()
    assert any(l.startswith("wget") for l in kindle.log())


@pytest.mark.parametrize("hours,hour,night", [
    ("0-5", "00", True), ("0-5", "05", True), ("0-5", "06", False), ("0-5", "08", False),
    ("0-5", "09", False), ("0-5", "23", False), ("23-5", "23", True), ("23-5", "02", True),
    ("23-5", "06", False), ("23-5", "22", False), ("", "03", False), ("3-3", "03", True),
    ("3-3", "04", False), ("1-6", "07", False),
])
def test_is_night(kindle, hours, hour, night):
    kindle.config(NIGHT_HOURS=hours)
    r = kindle.run("if is_night; then echo GECE; else echo GUNDUZ; fi", hour=hour)
    assert r.stderr == "", r.stderr  # "08"/"09" sekizlik sayı hatası vermemeli
    assert r.stdout.strip() == ("GECE" if night else "GUNDUZ")


def test_loop_full_refresh_cadence(kindle):
    """Döngüde ilk çizim tam, sonra her FULL_REFRESH_EVERY'de bir tam yenileme."""
    kindle.config(FULL_REFRESH_EVERY=3, NIGHT_HOURS="")
    kindle.run('''
n=0
for i in 1 2 3 4 5 6 7; do
    full=0; [ $((n % FULL_REFRESH_EVERY)) -eq 0 ] && full=1
    echo "tur$i full=$full" >> "$LOG"
    n=$((n + 1))
done''')
    text = (kindle.tmpdir / "homedisplay.log").read_text()
    fulls = [l.split()[0] for l in text.splitlines() if "full=1" in l]
    assert fulls == ["tur1", "tur4", "tur7"]


def test_loop_script_logic_matches(kindle):
    loop = (kindle.ext / "bin" / "loop.sh").read_text()
    assert "[ $((n % FULL_REFRESH_EVERY)) -eq 0 ] && full=1" in loop
    assert "is_night" in loop and "wait_next" in loop


def test_wait_next_sleep_mode(kindle):
    kindle.config(REFRESH_SECONDS=3600, WAIT_MODE="sleep")
    kindle.run("wait_next")
    assert "sleep 3600" in kindle.log()


def test_wait_next_suspend_without_rtc_falls_back_to_sleep(kindle):
    kindle.config(WAIT_MODE="suspend", RTC_DEV=str(kindle.tmpdir / "yok"), REFRESH_SECONDS=60)
    kindle.run("wait_next")
    assert "sleep 60" in kindle.log()


def test_start_twice_does_not_spawn_twice(kindle):
    # çalışan bir süreç taklidi: kendi PID'imiz
    pidfile = kindle.tmpdir / "homedisplay.pid"
    pidfile.write_text(str(os.getpid()))
    _exe(kindle.stub / "nohup", f'echo "nohup $*" >> "{kindle.calls}"\n')
    env = {"PATH": f"{kindle.stub}:{os.environ['PATH']}"}
    r = subprocess.run(kindle.shell + [str(kindle.ext / "bin" / "start.sh")], capture_output=True, text=True,
                       env=env, timeout=20)
    assert r.returncode == 0
    assert not any(l.startswith("nohup") for l in kindle.log()), "zaten çalışıyorsa ikinci kez başlamamalı"


def test_stop_cleans_up(kindle):
    (kindle.tmpdir / "homedisplay.pid").write_text("999999")  # olmayan süreç
    (kindle.tmpdir / "homedisplay-key.pid").write_text("999998")
    env = {"PATH": f"{kindle.stub}:{os.environ['PATH']}"}
    r = subprocess.run(kindle.shell + [str(kindle.ext / "bin" / "stop.sh")], capture_output=True, text=True,
                       env=env, timeout=20)
    assert r.returncode == 0, r.stderr
    assert not (kindle.tmpdir / "homedisplay.pid").exists()
    assert not (kindle.tmpdir / "homedisplay-key.pid").exists()
    assert any("preventScreenSaver 0" in l for l in kindle.log())
    assert any("wirelessEnable 1" in l for l in kindle.log())


def test_menu_and_config_xml():
    import json
    import xml.etree.ElementTree as ET
    menu = json.loads((EXT / "menu.json").read_text())
    actions = [i["action"] for i in menu["items"][0]["items"]]
    for a in actions:
        assert (EXT / a).exists(), a
        assert os.access(EXT / a, os.X_OK), f"{a} çalıştırılabilir değil"
    root = ET.parse(EXT / "config.xml").getroot()
    assert root.find("menus/menu").text == "menu.json"


def test_default_config_values():
    text = (EXT / "config.sh").read_text()
    assert 'IMAGE_URL="https://raw.githubusercontent.com/melihgucer-art/home_display/display/display.png"' in text
    assert "REFRESH_SECONDS=3600" in text
