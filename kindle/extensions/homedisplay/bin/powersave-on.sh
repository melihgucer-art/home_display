#!/bin/sh
# Pil tasarrufunu açar: Kindle kontroller arasında uyku moduna geçer.
. "$(dirname "$0")/common.sh"
touch "$POWERSAVE_FLAG"
log "pil tasarrufu açıldı"
eips 1 38 "Pil tasarrufu acik (Baslat'a basin)" >/dev/null 2>&1
