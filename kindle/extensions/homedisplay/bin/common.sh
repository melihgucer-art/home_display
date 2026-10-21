#!/bin/sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
. "$DIR/config.sh"
PIDFILE=/tmp/homedisplay.pid
IMG=/tmp/homedisplay.png
LOG=/tmp/homedisplay.log

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

wifi_on() {
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    i=0
    while [ $i -lt 30 ]; do
        [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" = "CONNECTED" ] && return 0
        sleep 1; i=$((i + 1))
    done
    return 1
}

wifi_off() { lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null; }

battery() { lipc-get-prop com.lab126.powerd battLevel 2>/dev/null || gasgauge-info -c 2>/dev/null | tr -dc 0-9; }

# $1 = 1 ise tam yenileme
refresh() {
    full="$1"
    if ! wifi_on; then
        log "wifi bağlanamadı"
        eips 1 38 "Wi-Fi yok" >/dev/null 2>&1
        return 1
    fi
    if wget -q -T 20 -O "$IMG.tmp" "$IMAGE_URL" && [ -s "$IMG.tmp" ]; then
        mv "$IMG.tmp" "$IMG"
        if [ "$full" = 1 ]; then
            eips -c >/dev/null 2>&1
            eips -f -g "$IMG" >/dev/null 2>&1
        else
            eips -g "$IMG" >/dev/null 2>&1
        fi
        log "görüntü güncellendi"
    else
        rm -f "$IMG.tmp"
        log "indirme başarısız: $IMAGE_URL"
        eips 1 38 "Sunucuya ulasilamadi" >/dev/null 2>&1
    fi
    b="$(battery)"
    if [ -n "$b" ] && [ "$b" -lt "$LOW_BATTERY" ] 2>/dev/null; then
        eips 40 38 "Pil %$b" >/dev/null 2>&1
    fi
    [ "$WIFI_OFF_BETWEEN" = 1 ] && wifi_off
    return 0
}

is_night() {
    [ -z "$NIGHT_HOURS" ] && return 1
    h=$(date +%H | sed 's/^0//'); h=${h:-0}
    from=${NIGHT_HOURS%-*}; to=${NIGHT_HOURS#*-}
    if [ "$from" -le "$to" ]; then
        [ "$h" -ge "$from" ] && [ "$h" -le "$to" ]
    else  # gece yarısını aşan aralık, örn. 23-5
        [ "$h" -ge "$from" ] || [ "$h" -le "$to" ]
    fi
}

wait_next() {
    if [ "$WAIT_MODE" = "suspend" ] && [ -w "$RTC_DEV/wakealarm" ]; then
        echo 0 > "$RTC_DEV/wakealarm"
        echo "+$REFRESH_SECONDS" > "$RTC_DEV/wakealarm"
        echo mem > /sys/power/state
        sleep 5   # uyanınca ağ/sürücüler toparlansın
    else
        sleep "$REFRESH_SECONDS"
    fi
}
