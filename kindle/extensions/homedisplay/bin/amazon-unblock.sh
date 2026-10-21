#!/bin/sh
# amazon-block.sh'nin eklediği satırları kaldırır.
HOSTS="${HOSTS:-/etc/hosts}"
grep -q "# BEGIN homedisplay_block_amazon" "$HOSTS" 2>/dev/null || exit 0
command -v mntroot >/dev/null 2>&1 && mntroot rw
awk '/# BEGIN homedisplay_block_amazon/,/# END homedisplay_block_amazon/{next} {print}' "$HOSTS" > "$HOSTS.tmp" \
    && cat "$HOSTS.tmp" > "$HOSTS" && rm -f "$HOSTS.tmp"
command -v mntroot >/dev/null 2>&1 && mntroot ro
eips 1 38 "Amazon engeli kaldirildi" >/dev/null 2>&1
exit 0
