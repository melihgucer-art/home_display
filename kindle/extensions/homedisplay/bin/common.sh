#!/bin/sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
. "$DIR/config.sh"
# KUAL betikleri kısıtlı bir PATH ile çalıştırabiliyor; eips /usr/sbin altında
PATH="$PATH:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH
# Kindle saati UTC tutar; gece saatleri ve log için Türkiye saati (UTC+3, yaz saati yok)
TZ="${TZ:-TRT-3}"
export TZ

# Kindle 4'ün eski busybox kabuğu "command -v"yi desteklemeyebilir
have() {
    command -v "$1" >/dev/null 2>&1 || which "$1" >/dev/null 2>&1 || type "$1" >/dev/null 2>&1
}
PIDFILE=/tmp/homedisplay.pid
IMG=/tmp/homedisplay.png
# Log USB belleğe yazılır: Mac'ten Kindle/extensions/homedisplay/homedisplay.log olarak okunabilir
LOG="$DIR/homedisplay.log"

# Arka planda, oturumdan bağımsız çalıştır (Kindle'da nohup her zaman bulunmayabilir)
# İç içe alt kabuk: süreç hemen init'e devredilir, KUAL betiği bitirip süreç grubunu kapatsa da yaşar.
bg() {
    if have setsid; then
        ( setsid "$@" >> "$LOG" 2>&1 < /dev/null & ) &
    elif have nohup; then
        ( nohup "$@" >> "$LOG" 2>&1 < /dev/null & ) &
    else
        ( "$@" >> "$LOG" 2>&1 < /dev/null & ) &
    fi
}

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
    have eips || log "UYARI: eips bulunamadı (PATH=$PATH)"
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
            return 3
        fi
        mv "$IMG.tmp" "$IMG"
        if [ "$full" = 1 ]; then
            eips -c >/dev/null 2>&1
            eips -f -g "$IMG" >> "$LOG" 2>&1
        else
            eips -g "$IMG" >> "$LOG" 2>&1
        fi
        log "görüntü güncellendi ($(wc -c < "$IMG") bayt, eips çıkış kodu $?)"
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

POWERSAVE_FLAG="$DIR/PIL_TASARRUFU"
POWER_STATE="${POWER_STATE:-/sys/power/state}"

powersave_on() { [ "$WAIT_MODE" = "suspend" ] || [ -f "$POWERSAVE_FLAG" ]; }

num() { v=$(echo "$1" | sed 's/^0*//'); echo "${v:-0}"; }

# Bir sonraki kontrol saatine kaç saniye var (CHECK_TIMES boşsa REFRESH_SECONDS)
seconds_until_next() {
    if [ -z "$CHECK_TIMES" ]; then
        echo "$REFRESH_SECONDS"
        return
    fi
    now=$(( $(num "$(date +%H)") * 3600 + $(num "$(date +%M)") * 60 + $(num "$(date +%S)") ))
    best=""
    first=""
    for t in $CHECK_TIMES; do
        target=$(( $(num "${t%%:*}") * 3600 + $(num "${t##*:}") * 60 ))
        if [ -z "$first" ] || [ "$target" -lt "$first" ]; then first=$target; fi
        if [ "$target" -gt $((now + 60)) ]; then
            if [ -z "$best" ] || [ "$target" -lt "$best" ]; then best=$target; fi
        fi
    done
    if [ -n "$best" ]; then echo $((best - now)); else echo $((first + 86400 - now)); fi
}

# Uyku modu: kindle-dash'in Kindle 4'te kullandığı mxc_rtc zamanlayıcısı, yoksa standart RTC alarmı
suspend_for() {
    secs="$1"
    if [ -w "$RTC_WAKE" ]; then
        [ "$(cat "$RTC_WAKE" 2>/dev/null)" = "0" ] && printf '%s' "$secs" > "$RTC_WAKE"
    elif [ -w "$RTC_DEV/wakealarm" ]; then
        echo 0 > "$RTC_DEV/wakealarm"
        echo "+$secs" > "$RTC_DEV/wakealarm"
    else
        return 1
    fi
    echo mem > "$POWER_STATE"
    return 0
}

wait_next() { wait_seconds "$(seconds_until_next)"; }

wait_seconds() {
    secs="$1"
    if powersave_on; then
        log "uykuya geçiliyor, $secs sn sonra uyanılacak"
        sleep 10  # Home tuşuyla çıkmak için kısa bir fırsat
        if suspend_for "$secs"; then
            sleep 5  # uyanınca Wi-Fi ve sürücüler toparlansın
            log "uyandı"
            return 0
        fi
        log "uyku zamanlayıcısı bulunamadı, uyanık bekleniyor"
        secs=$((secs - 10))
    fi
    sleep "$secs"
}
