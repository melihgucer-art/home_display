#!/bin/sh
# Amazon sunucularını /etc/hosts ile engeller. Kayıtsız (jailbreak'li) Kindle 4'te Wi-Fi açılınca
# Amazon KUAL'ın geliştirici sertifikasını siliyor; bu engel bunu önler.
# Saat eşitleme sunucuları (kindle-time, ntp) bilerek engellenmez: pano için saatin doğru olması şart.
HOSTS="${HOSTS:-/etc/hosts}"
PATH="$PATH:/usr/sbin:/usr/bin"
MARK="# BEGIN homedisplay_block_amazon"
grep -q "$MARK" "$HOSTS" 2>/dev/null && { eips 1 38 "Amazon zaten engelli" >/dev/null 2>&1; exit 0; }
mntroot rw >/dev/null 2>&1
cat >> "$HOSTS" <<'HOSTS_EOF'
# BEGIN homedisplay_block_amazon
127.0.0.1 amazon.com
127.0.0.1 www.amazon.com
127.0.0.1 kindle.amazon.com
127.0.0.1 cde-g7g.amazon.com
127.0.0.1 det-g7g.amazon.com
127.0.0.1 det-ta-g7g.amazon.com
127.0.0.1 device-messaging-na.amazon.com
127.0.0.1 fints-g7g.amazon.com
127.0.0.1 firs-g7g.amazon.com
127.0.0.1 firs-ta-g7g.amazon.com
127.0.0.1 fras-g7g.amazon.com
127.0.0.1 kdk-ws.amazon.com
127.0.0.1 kindleatt1.amazon.com
127.0.0.1 todo-g7g.amazon.com
127.0.0.1 w.amazon.com
# END homedisplay_block_amazon
HOSTS_EOF
mntroot ro >/dev/null 2>&1
PATH="$PATH:/usr/sbin:/usr/bin"
if grep -q "$MARK" "$HOSTS" 2>/dev/null; then
    eips 1 38 "Amazon engellendi" >/dev/null 2>&1
else
    eips 1 38 "HATA: Amazon engellenemedi" >/dev/null 2>&1
    exit 1
fi
exit 0
