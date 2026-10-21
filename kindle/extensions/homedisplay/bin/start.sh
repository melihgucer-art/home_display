#!/bin/sh
# Döngüyü arka planda başlatıp hemen çıkar. Kindle arayüzünü döngünün kendisi durdurur:
# arayüz (ve onunla KUAL) kapanınca bu betik de sonlanabileceği için durdurmayı burada yapmıyoruz.
. "$(dirname "$0")/common.sh"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    log "zaten çalışıyor"
    exit 0
fi
log "başlatılıyor (saat: $(date))"
bg "$DIR/bin/keywatch.sh"
bg "$DIR/bin/loop.sh" --takeover
# Arka plan süreçleri kendilerini ayırana kadar bekle; KUAL betik bitince süreç grubunu kapatabilir
sleep 3
log "arka plan süreçleri başlatıldı"
exit 0
