#!/bin/sh
# amazon-block.sh'nin eklediği satırları kaldırır.
HOSTS="${HOSTS:-/etc/hosts}"
PATH="$PATH:/usr/sbin:/usr/bin"
grep -q "# BEGIN homedisplay_block_amazon" "$HOSTS" 2>/dev/null || exit 0
mntroot rw >/dev/null 2>&1
awk '/# BEGIN homedisplay_block_amazon/,/# END homedisplay_block_amazon/{next} {print}' "$HOSTS" > "$HOSTS.tmp" \
    && cat "$HOSTS.tmp" > "$HOSTS" && rm -f "$HOSTS.tmp"
mntroot ro >/dev/null 2>&1
eips 1 38 "Amazon engeli kaldirildi" >/dev/null 2>&1
exit 0
