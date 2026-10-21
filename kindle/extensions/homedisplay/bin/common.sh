#!/bin/sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
. "$DIR/config.sh"
# KUAL betikleri kısıtlı bir PATH ile çalıştırabiliyor; eips /usr/sbin altında
PATH="$PATH:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
PIDFILE=/tmp/homedisplay.pid
IMG=/tmp/homedisplay.png
# Log USB belleğe yazılır: Mac'ten Kindle/extensions/homedisplay/homedisplay.log olarak okunabilir
LOG="$DIR/homedisplay.log"

log() {
    # 100 KB'ı geçerse son kısmı tut
    if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 102400 ]; then
        tail -n 200 "$LOG" > "$LOG.old" && mv "$LOG.old" "$LOG"
    fi
    echo "$(date '+%F %T') $*" >> "$LOG"
}

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

# HTTPS için bin/xh (pascalw/kindle-dash paketindeki modern HTTP istemcisi), yoksa wget/curl
download() {
    url="$1"; out="$2"
    case "$url" in
        https://*)
            if [ -x "$DIR/bin/xh" ]; then
                "$DIR/bin/xh" -d -q -o "$out" get "$url" 2>> "$LOG"
                rc=$?
                [ $rc -ne 0 ] && log "xh hata kodu $rc (saat yanlışsa HTTPS kurulamaz: $(date))"
                return $rc
            fi
            log "UYARI: bin/xh yok, HTTPS büyük olasılıkla başarısız olacak"
            ;;
    esac
    wget -q -T 30 -O "$out" "$url" 2>/dev/null || curl -s -m 30 -o "$out" "$url"
}

battery() { lipc-get-prop com.lab126.powerd battLevel 2>/dev/null || gasgauge-info -c 2>/dev/null | tr -dc 0-9; }

# $1 = 1 ise tam yenileme
refresh() {
    full="$1"
    command -v eips >/dev/null 2>&1 || log "UYARI: eips bulunamadı (PATH=$PATH)"
    if ! wifi_on; then
        log "wifi bağlanamadı"
        eips 1 38 "Wi-Fi yok" >/dev/null 2>&1
        return 1
    fi
    if download "$IMAGE_URL" "$IMG.tmp" && [ -s "$IMG.tmp" ]; then
        if [ "$full" != 1 ] && [ -f "$IMG" ] && \
           [ "$(md5sum < "$IMG.tmp")" = "$(md5sum < "$IMG")" ]; then
            rm -f "$IMG.tmp"
            log "görüntü değişmemiş"
            [ "$WIFI_OFF_BETWEEN" = 1 ] && wifi_off
            return 0
        fi
        mv "$IMG.tmp" "$IMG"
        if [ "$full" = 1 ]; then
            eips -c >/dev/null 2>&1
            eips -f -g "$IMG" >> "$LOG" 2>&1
        else
            eips -g "$IMG" >> "$LOG" 2>&1
        fi
        log "görüntü güncellendi ($(wc -c < "$IMG") bayt)"
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
