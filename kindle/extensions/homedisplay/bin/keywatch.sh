#!/bin/sh
# Home tuşuna basılınca Home Display'i durdurur ve normal Kindle arayüzüne döner.
# Kindle 4 Home tuşu = 102 (KEY_HOME)
. "$(dirname "$0")/common.sh"
echo $$ > /tmp/homedisplay-key.pid
trap '' HUP
if ! have waitforkey; then
    log "UYARI: waitforkey yok; Home tuşuyla çıkılamaz (güç düğmesini 30 sn basılı tutun)"
    exit 0
fi
log "Home tuşu dinleniyor"
while true; do
    key="$(waitforkey 2>/dev/null | awk '{print $1}')"
    if [ "$key" = "102" ]; then
        exec "$DIR/bin/stop.sh"
    fi
done
