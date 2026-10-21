#!/bin/sh
# Arayüzü durdurmadan tek seferlik çizim (test için).
# KUAL menüsü kapanıp kütüphane ekranı çizildikten sonra çizer; bir tuşa basınca Kindle ekranı geri gelir.
. "$(dirname "$0")/common.sh"
log "tek seferlik yenileme istendi (saat: $(date))"
( sleep 4; refresh 1 ) > /dev/null 2>&1 &
