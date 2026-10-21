#!/bin/sh
. "$(dirname "$0")/common.sh"
echo $$ > "$PIDFILE"
log "döngü başladı"
n=0
while true; do
    if is_night; then
        log "gece modu, atlanıyor"
    else
        full=0
        [ $((n % FULL_REFRESH_EVERY)) -eq 0 ] && full=1
        refresh "$full"
        n=$((n + 1))
    fi
    wait_next
done
