#!/bin/sh
# Pil tasarrufunu kapatır: Kindle kontroller arasında uyanık bekler.
. "$(dirname "$0")/common.sh"
rm -f "$POWERSAVE_FLAG"
log "pil tasarrufu kapatıldı"
eips 1 38 "Pil tasarrufu kapali" >/dev/null 2>&1
