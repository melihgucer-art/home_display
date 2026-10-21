# Home Display - Kindle tarafı ayarları
# Sunucunuzun yerel ağdaki adresi (Kindle 4 eski TLS yüzünden HTTPS yerine HTTP kullanın)
IMAGE_URL="http://192.168.1.10:8080/display.png"

# Kaç saniyede bir yenilensin
REFRESH_SECONDS=300

# Kaç yenilemede bir tam (siyah-beyaz yanıp sönen) yenileme yapılsın - gölgelenmeyi temizler
FULL_REFRESH_EVERY=6

# Bekleme yöntemi:
#   sleep   -> cihaz uyanık kalır (şarja takılı kullanım için önerilir, en güvenilir)
#   suspend -> RTC alarmıyla askıya alır, pil daha uzun gider (deneysel)
WAIT_MODE="sleep"
RTC_DEV="/sys/class/rtc/rtc1"

# Bu saatler arasında ekran yenilenmez (boş bırakırsanız kapalı), örn. 0-6
NIGHT_HOURS="1-6"

# Wi-Fi'yi yenilemeler arasında kapat (pil tasarrufu, sleep modunda da işe yarar)
WIFI_OFF_BETWEEN=0

# Pil bu yüzdenin altına düşünce ekranın köşesine uyarı yaz
LOW_BATTERY=15
