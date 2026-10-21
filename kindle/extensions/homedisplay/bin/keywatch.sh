#!/bin/sh
# Home tuşuna basılınca Home Display'i durdurur ve normal Kindle arayüzüne döner.
# Kindle 4 Home tuşu = 102 (KEY_HOME)
DIR="$(dirname "$0")"
command -v waitforkey >/dev/null 2>&1 || exit 0
while true; do
    key="$(waitforkey 2>/dev/null | awk '{print $1}')"
    if [ "$key" = "102" ]; then
        exec "$DIR/stop.sh"
    fi
done
