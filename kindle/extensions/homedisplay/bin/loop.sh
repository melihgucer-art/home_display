#!/bin/sh
. "$(dirname "$0")/common.sh"
trap '' HUP  # KUAL/arayüz kapanınca gelen kapanma sinyalini yok say
if [ "$1" = "--once" ]; then
    sleep 10  # kütüphane ekranı çizilsin, sonra üstüne çiz
    refresh 1
    exit 0
fi
echo $$ > "$PIDFILE"
log "döngü başladı (pid $$)"
if [ "$1" = "--takeover" ]; then
    sleep 3  # KUAL menüsünün kapanmasını bekle
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
    if powersave_on; then
        echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
    fi
    # Kindle arayüzünü durdur ki ekranın üstüne çizmesin
    /etc/init.d/framework stop >> "$LOG" 2>&1
    log "Kindle arayüzü durduruldu"
    sleep 2
    eips -c >/dev/null 2>&1
    eips 1 18 "Home Display basliyor..." >/dev/null 2>&1
    eips 1 20 "Cikmak icin Home tusuna basin" >/dev/null 2>&1
    eips 1 21 "(olmazsa guc dugmesini 30 sn basili tutun)" >/dev/null 2>&1
fi
n=0
retry=0
while true; do
    if is_night; then
        log "gece modu, atlanıyor"
    else
        full=0
        [ $((n % FULL_REFRESH_EVERY)) -eq 0 ] && full=1
        refresh "$full"
        rc=$?
        n=$((n + 1))
        # Bulut güncellemesi gecikmiş olabilir: görüntü değişmediyse 20 dk sonra tekrar bak (en fazla 2 kez)
        if [ $rc -eq 3 ] && [ -n "$CHECK_TIMES" ] && [ $retry -lt 2 ]; then
            retry=$((retry + 1))
            log "yeni görüntü henüz yok, 20 dk sonra tekrar denenecek ($retry/2)"
            wait_seconds 1200
            continue
        fi
    fi
    retry=0
    wait_next
done
