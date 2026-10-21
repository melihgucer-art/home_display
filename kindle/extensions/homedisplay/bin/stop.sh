#!/bin/sh
. "$(dirname "$0")/common.sh"
for f in "$PIDFILE" /tmp/homedisplay-key.pid; do
    [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null
    rm -f "$f"
done
[ -w "$RTC_DEV/wakealarm" ] && echo 0 > "$RTC_DEV/wakealarm"
log "durduruldu"
lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
eips -c >/dev/null 2>&1
/etc/init.d/framework start >/dev/null 2>&1 &
