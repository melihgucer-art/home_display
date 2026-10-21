#!/bin/sh
. "$(dirname "$0")/common.sh"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    exit 0
fi
log "başlatılıyor (saat: $(date))"
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
# Kindle arayüzünü durdur ki ekranın üstüne çizmesin
/etc/init.d/framework stop >/dev/null 2>&1
sleep 2
eips -c >/dev/null 2>&1
eips 1 18 "Home Display basliyor..." >/dev/null 2>&1
eips 1 20 "Cikmak icin Home tusuna basin" >/dev/null 2>&1
nohup "$DIR/bin/keywatch.sh" >/dev/null 2>&1 &
echo $! > /tmp/homedisplay-key.pid
nohup "$DIR/bin/loop.sh" >/dev/null 2>&1 &
