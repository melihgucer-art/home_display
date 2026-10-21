# Home Display — Kindle 4 (firmware 4.1.1)

Kindle 4'ü (klavyesiz, dokunmatiksiz "Kindle 4 NT") duvara asılabilir bir ev panosuna çevirir.

```
┌──────────────┐    HTTP (yerel ağ)    ┌──────────────────────────┐
│  Kindle 4    │ ───── display.png ──▶ │ Sunucu (PC / Raspberry Pi│
│  wget + eips │ ◀──────────────────── │ / NAS / Docker)          │
└──────────────┘    her 5 dakikada     └──────────────────────────┘
```

Görüntüyü sunucu üretir (600×800, 16 gri ton PNG). Kindle sadece bu dosyayı indirip
`eips` ile ekrana basar. Kindle'ın eski tarayıcısı ve TLS desteği hiç devreye girmez.

**Ekranda neler var** (her biri `config.toml` dosyasından açılıp kapatılabilir):

- Gün, tarih, saat (Türkçe)
- Hava durumu: şu anki durum ve 4 günlük tahmin ([Open-Meteo](https://open-meteo.com), API anahtarı gerekmez)
- Döviz: USD/TRY, EUR/TRY (ECB / frankfurter.app)
- Home Assistant sensörleri (sıcaklık, nem vb.)
- Takvim: Google/iCloud/Outlook takviminin gizli ICS adresi
- Yapılacaklar listesi (`server/todo.txt`)

![örnek](docs/preview.png)

---

## 1. Sunucuyu kur

Sunucu, evde sürekli açık duran herhangi bir makinede çalışabilir.

### Docker ile

```sh
cp server/config.example.toml server/config.toml   # ayarları düzenleyin
cp server/todo.example.txt server/todo.txt
docker compose up -d --build
```

### Docker olmadan (Raspberry Pi vb.)

```sh
cd server
pip install -r requirements.txt          # Pillow, requests
cp config.example.toml config.toml
python3 home_display.py serve
```

Sürekli çalışsın diye `server/home-display.service` dosyasını `/etc/systemd/system/` altına
kopyalayın (yolları kendinize göre düzeltin), sonra `sudo systemctl enable --now home-display` çalıştırın.

Tarayıcıdan `http://<sunucu-ip>:8080/display.png` adresini açın; panoyu görüyorsanız sunucu tarafı hazır.
Bilgisayarda çalışırken önizleme almak için `python3 home_display.py render onizleme.png` de kullanılabilir.

> Sunucuya sabit bir IP verin (modem arayüzünden DHCP rezervasyonu), yoksa Kindle bir gün onu bulamaz.

---

## 2. Kindle 4'ü hazırla (firmware 4.1.1)

Önce sürümü doğrulayın: **Menu → Settings → Menu → Device Info**. 4.1.1 değilse aşağıdaki
dosyaların o sürüme uygun olanlarını seçin.

Bütün dosyalar MobileRead forumunda NiLuJe'nin dizinindedir:
**https://www.mobileread.com/forums/showthread.php?t=225030** (Kindle 4 / "K4" bölümü).

### 2.1 Jailbreak

1. MobileRead'den **Kindle 4 jailbreak** paketini (`kindle-k4-jailbreak-*.zip`) indirip açın.
2. Kindle'ı USB ile bilgisayara bağlayın. Paketteki `data.tar.gz`, `ENABLE_DIAGS` dosyasını
   ve `diagnostic_logs` klasörünü Kindle'ın kök dizinine kopyalayın.
3. Kindle'ı yeniden başlatın: **Menu → Settings → Menu → Restart**.
4. Diagnostics menüsü açılır: **D) Exit, Reboot or Disable Diags → R) Reboot System → Q** (ileri tuşuyla onaylayın).
5. Cihaz açılınca ekranda jailbreak mesajını görürsünüz. Kökteki dosyalar kendiliğinden silinir.

### 2.2 MKK + KUAL

Kindle 4'te KUAL bir "Kindlet" olduğundan önce Kindlet anahtarı gerekir:

1. **MKK (MobileRead Kindlet Kit)** paketinden K4 için olan `Update_mkk-*-k4-*.bin` dosyasını
   Kindle'ın köküne kopyalayın → **Menu → Settings → Menu → Update Your Kindle**.
2. **KUAL** paketindeki `KUAL-KDK-1.0.azw2` dosyasını Kindle'daki `documents/` klasörüne kopyalayın.
   Kütüphanede "Kindle Launcher" olarak görünür.

### 2.3 (İsteğe bağlı) USBNetwork

SSH ile bağlanıp log okumak isterseniz K4 için `Update_usbnetwork-*-k4-*.bin` kurun. Zorunlu değil.

### 2.4 Home Display eklentisi

1. Bu depodaki `kindle/extensions/homedisplay` klasörünü Kindle'daki `extensions/` klasörüne kopyalayın
   (KUAL kurulduysa bu klasör vardır; yoksa oluşturun). Sonuç: `extensions/homedisplay/config.xml`.
2. `extensions/homedisplay/config.sh` dosyasını açıp **`IMAGE_URL`** satırına sunucu adresinizi yazın.
3. Kindle'da Wi-Fi'ye bağlanın.
4. KUAL'ı açın → **Home Display → Tek seferlik yenile** ile görüntünün geldiğini kontrol edin.
5. **Home Display → Başlat**.

Başlattığınızda Kindle arayüzü durdurulur (çizdiğimiz görüntünün üstüne yazmasın diye) ve pano
`REFRESH_SECONDS` aralıklarla yenilenir.

**Çıkış:** Home tuşuna basın, normal Kindle arayüzü geri gelir. Tepki vermezse güç düğmesini
~20 sn basılı tutup bırakın; cihaz yeniden başlar ve normal haline döner (eklenti açılışta
kendiliğinden çalışmaz).

---

## 3. Ayarlar

### Sunucu: `server/config.toml`

| Bölüm | Ne işe yarar |
|---|---|
| `[display]` | Boyut, `rotate = 90` ile yatay kullanım, saat dilimi, alt köşedeki başlık |
| `[weather]` | Enlem/boylam ve şehir adı. Koordinatı Google Maps'te sağ tıklayarak alabilirsiniz |
| `[currency]` | Gösterilecek kurlar |
| `[home_assistant]` | URL, uzun ömürlü erişim jetonu, `[etiket, entity_id]` listesi |
| `[calendar]` | Bir veya birden çok gizli ICS adresi |
| `[todo]` | `todo.txt` içindeki her satır bir madde; dosyayı düzenleyince bir sonraki yenilemede görünür |

Sunucu `config.toml` dosyasını her istekte yeniden okur, yani yeniden başlatmanız gerekmez.
Bir veri kaynağına ulaşılamazsa o bölüm atlanır ve hata alt satırda kısaca yazar. Ekran yine de güncellenir.

### Kindle: `extensions/homedisplay/config.sh`

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `IMAGE_URL` | — | Sunucudaki `display.png` adresi (**HTTP**) |
| `REFRESH_SECONDS` | 300 | Yenileme aralığı |
| `FULL_REFRESH_EVERY` | 6 | Kaç yenilemede bir ekran tam yenilenir (gölgeyi temizler) |
| `WAIT_MODE` | `sleep` | `sleep`: cihaz uyanık kalır (şarja takılı kullanım). `suspend`: RTC alarmıyla uyur (deneysel) |
| `NIGHT_HOURS` | `1-6` | Bu saatlerde yenileme yapılmaz (`23-5` gibi gece yarısını aşan aralık da olur) |
| `WIFI_OFF_BETWEEN` | 0 | 1 yapılırsa Wi-Fi yenilemeler arasında kapatılır |
| `LOW_BATTERY` | 15 | Pil bu yüzdenin altına inince köşede uyarı gösterilir |

**Pil:** `sleep` modunda Kindle 4 şarjsız birkaç gün dayanır. Duvarda kalıcı kullanım için USB
şarja takılı tutmanız önerilir. Şarjsız kullanacaksanız `WIFI_OFF_BETWEEN=1` ve
`REFRESH_SECONDS=900` iyi bir başlangıç olur.

---

## 4. Sorun giderme

- **Log:** Kindle'da `/tmp/homedisplay.log` (USBNetwork ile `ssh root@192.168.15.244`).
- **"Sunucuya ulasilamadi"**: Kindle'ın tarayıcısında `IMAGE_URL` adresini açmayı deneyin.
  Aynı ağda mı? Sunucunun güvenlik duvarı 8080 portuna izin veriyor mu?
- **HTTPS adres verdim, çalışmıyor**: Kindle 4'ün `wget`'i güncel TLS'i desteklemez, yerel HTTP kullanın.
- **Gri tonlar bozuk / görüntü kaymış**: PNG 600×800 ve 8-bit gri olmalı; sunucu bunu otomatik üretir.
  `rotate` kullanıyorsanız çıktı yine 600×800'dür.
- **`suspend` modunda uyanmıyor**: `RTC_DEV` değerini `/sys/class/rtc/rtc0` yapın ya da `sleep` moduna dönün.

## Dosya yapısı

```
server/
  home_display.py         görüntü üretici + HTTP sunucu
  config.example.toml     örnek ayarlar (config.toml olarak kopyalayın)
  todo.example.txt
  Dockerfile, home-display.service
docker-compose.yml
kindle/extensions/homedisplay/   KUAL eklentisi (Kindle'daki extensions/ içine)
  config.sh               Kindle tarafı ayarlar
  bin/start.sh stop.sh once.sh loop.sh common.sh keywatch.sh
```
