#!/bin/sh
# Arayüzü durdurmadan tek seferlik çizim (test için).
# KUAL menüsü kapanıp kütüphane ekranı çizildikten sonra çizer; bir tuşa basınca Kindle ekranı geri gelir.
. "$(dirname "$0")/common.sh"
log "tek seferlik yenileme istendi (saat: $(date))"
# Kütüphane ekranı yavaş çizilebiliyor; üstüne yazılmasın diye 10 sn bekle
bg "$DIR/bin/loop.sh" --once
sleep 2
