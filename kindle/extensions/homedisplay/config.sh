# Home Display - Kindle tarafı ayarları
# Panonun adresi: GitHub Actions'ın günde 6 kez (06, 09, 12, 15, 18, 21) ürettiği görüntü.
# HTTPS adresleri bin/xh ile indirilir (Kindle'ın kendi wget'i modern HTTPS'i desteklemez).
IMAGE_URL="https://raw.githubusercontent.com/melihgucer-art/home_display/display/display.png"

# Kontrol saatleri: bulut panoyu 06:07, 09:07 ... 21:07'de üretir; Kindle hemen ardından bakar.
# Gece 21:20'den sabah 06:20'ye kadar tek seferde bekler. Boş bırakırsanız REFRESH_SECONDS kullanılır.
CHECK_TIMES="06:20 09:20 12:20 15:20 18:20 21:20"

# CHECK_TIMES boşsa kaç saniyede bir kontrol edilsin. Görüntü değişmediyse ekran yeniden çizilmez.
REFRESH_SECONDS=3600

# Kaç yenilemede bir tam (siyah-beyaz yanıp sönen) yenileme yapılsın - gölgelenmeyi temizler
FULL_REFRESH_EVERY=3

# Pil tasarrufu: KUAL -> Home Display -> "Pil tasarrufunu aç" ile açılır (PIL_TASARRUFU dosyası).
# Açıkken Kindle kontroller arasında uyku moduna geçer (kindle-dash'in K4'te kullandığı yöntem):
# pil haftalarca gider. Uykudayken Home tuşu çalışmaz; çıkmak için güç düğmesini 30 sn basılı tutun.
# Buradan kalıcı açmak için WAIT_MODE="suspend" yazabilirsiniz.
WAIT_MODE="sleep"
RTC_WAKE="/sys/devices/platform/mxc_rtc.0/wakeup_enable"
RTC_DEV="/sys/class/rtc/rtc0"

# Bu saatler arasında ekran yenilenmez (boş bırakırsanız kapalı), örn. 0-6
NIGHT_HOURS="0-5"

# Wi-Fi'yi yenilemeler arasında kapat (pil tasarrufu, sleep modunda da işe yarar)
WIFI_OFF_BETWEEN=0

# Pil bu yüzdenin altına düşünce ekranın köşesine uyarı yaz
LOW_BATTERY=15
