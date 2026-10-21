# Home Display — Kindle 4 (firmware 4.1.1) · Erenköy / Kadıköy

Kindle 4'ü (klavyesiz "Kindle 4 NT") duvara asılabilir bir ev panosuna çevirir.
**Tamamen ücretsizdir:** Raspberry Pi, sunucu, abonelik ya da API anahtarı gerekmez.

```
 GitHub Actions (ücretsiz)              GitHub (ücretsiz barındırma)        Kindle 4
 günde 6 kez: verileri topla,   ──▶   "display" dalı: display.png  ──▶   saatte bir kontrol et,
 600×800 PNG çiz                                                          değiştiyse ekrana bas
```

Görüntüyü GitHub Actions üretir; herkese açık depolarda Actions sınırsız ve ücretsizdir.
Güncelleme saatleri (Türkiye saati): **06:07, 09:07, 12:07, 15:07, 18:07, 21:07**.
GitHub yoğun saatlerde birkaç dakika geciktirebilir.

Kindle PNG'yi `raw.githubusercontent.com` adresinden indirir. Kindle 4'ün kendi `wget`'i
modern HTTPS'e bağlanamaz; bu yüzden pakete [kindle-dash](https://github.com/pascalw/kindle-dash)
projesinin K4 için derlenmiş `xh` istemcisi eklenmiştir.

![örnek](docs/preview.png)

## Ekranda neler var

| Bölüm | İçerik | Kaynak (hepsi ücretsiz, anahtarsız) |
|---|---|---|
| Başlık | Gün, tarih, gün doğumu/batımı, ay evresi | Open-Meteo + yerel hesap |
| Hava | Erenköy'de anlık durum, hissedilen, nem, rüzgar (poyraz/lodos…), UV, 4 günlük tahmin | [Open-Meteo](https://open-meteo.com) |
| Kutucuklar | Hava kalitesi, Caddebostan açığında deniz suyu, dolar/euro, gram altın | Open-Meteo, [truncgil finans](https://finans.truncgil.com) |
| **Mevsiminde** | Büyük harflerle ay adı; altında o ayın 6 meyvesi, 6 sebzesi ve 6 İstanbul balığı, her biri **ikonuyla** ve adıyla. Av yasağı (15 Nisan – 31 Ağustos) geri sayımı | `server/local_data.py`, `server/icons.py` |
| Semt | Bugün/yarın kurulan pazarlar (Erenköy Pazarı Perşembe…), Erenköy'e en yakın 2 nöbetçi eczane, sıradaki resmi tatil | Kadıköy Belediyesi listesi, nobetcieczane.org, [Nager.Date](https://date.nager.at) |

Saat, yapılacaklar, takvim, deprem ve ezan bilgisi **yoktur**.

### İkonlar

Meyve ve sebzelerin bir kısmı Google'ın açık lisanslı (OFL) tek renkli
[Noto Emoji](https://fonts.google.com/noto/specimen/Noto+Emoji) fontundan çizilir.
Fontta karşılığı olmayanlar (nar, ayva, incir, dut, pırasa, enginar, bamya, kereviz…) ve
**her balık türü** (hamsi, lüfer, palamut, kalkan, barbunya…) `server/icons.py` içinde aynı
çizgi stilinde ayrı ayrı çizilmiştir. Hepsi e-ink'te net görünecek şekilde siyah çizgi ve gri dolgudur.

---

## 1. Bulut tarafı (bir kez)

1. GitHub'da depo → **Actions** sekmesi. "I understand my workflows, go ahead and enable them" çıkarsa onaylayın.
2. **render** iş akışı → **Run workflow**. Bir dakika içinde `display` dalı güncellenir.
3. Tarayıcıda açıp panoyu görün:
   `https://raw.githubusercontent.com/melihgucer-art/home_display/display/display.png`

Ayarlar `server/config.toml` dosyasında (konum, kutucuklar, yatay kullanım için `rotate = 90`).
Mevsim listeleri ve pazarlar `server/local_data.py` dosyasında; GitHub uygulamasından
telefonla düzenleyebilirsiniz. Değişiklik kaydedilince pano hemen yeniden üretilir.

> GitHub, depoda 60 gün hiç etkinlik olmazsa zamanlanmış işleri durdurabilir. Olursa Actions
> sekmesinden **render** iş akışını yeniden etkinleştirin.

---

## 2. Kindle 4'ü hazırla (firmware 4.1.1)

Önce sürümü doğrulayın: **Menu → Settings → Menu → Device Info**.
Gerekli dosyalar MobileRead'deki NiLuJe dizinindedir:
**https://www.mobileread.com/forums/showthread.php?t=225030** (Kindle 4 / "K4" bölümü).

### 2.1 Jailbreak

1. **Kindle 4 jailbreak** paketini (`kindle-k4-jailbreak-*.zip`) indirip açın.
2. Kindle'ı USB ile bağlayın. Paketteki `data.tar.gz`, `ENABLE_DIAGS` dosyasını ve
   `diagnostic_logs` klasörünü Kindle'ın kök dizinine kopyalayın.
3. **Menu → Settings → Menu → Restart**.
4. Diagnostics menüsünde: **D) Exit, Reboot or Disable Diags → R) Reboot System → Q**.
5. Açılışta jailbreak mesajı görünür. Kökteki dosyalar kendiliğinden silinir.

### 2.2 MKK, sertifika güncellemesi ve KUAL

> KUAL'ın eski geliştirici sertifikasının süresi **17 Nisan 2025'te doldu**. Sertifika güncellemesi
> yapılmazsa KUAL "not signed by an authorized developer" ya da "permissions have expired" hatası verir.

Gerekenlerin hepsi depo → **Releases → "Kindle eklentisi"** → **`kindle-kurulum.zip`** içinde numaralı
klasörler halinde duruyor (bkz. `OKU-BENI.txt`). Her adımda dosyayı Kindle'a kopyalayın, ⏏ ile çıkarın,
sonra Kindle'da işlemi yapın:

1. `1-MKK/Update_mkk-20141129-k4-ALL_install.bin` → Kindle köküne → **Menu → Settings → Menu → Update Your Kindle**.
2. `2-Sertifika/Update_mkk-20250419-k4-ALL_keystore-install.bin` → Kindle köküne → **Update Your Kindle**.
3. `3-KUAL/KUAL-KDK-1.0.azw2` → Kindle'daki `documents/` klasörüne. Kütüphanede "Kindle Launcher" olarak görünür.
4. (Önerilir) `5-Guncelleme-Engeli/update.bin.tmp.partial` klasörü → Kindle köküne. Amazon'un otomatik
   güncellemesi jailbreak'i silmesin diye.

Dosyaların kaynağı NiLuJe'nin MobileRead paylaşımlarıdır
([anlık görüntüler](https://www.mobileread.com/forums/showthread.php?t=225030),
[2025 sertifikası](https://www.mobileread.com/forums/showpost.php?p=4506164&postcount=1295)).
Paket her oluşturulduğunda MKK'nın MD5'i doğrulanır.

### 2.3 Home Display eklentisi

1. `kindle-kurulum.zip` içindeki `4-HomeDisplay` klasörünü açın (ya da yalnızca eklenti için
   `homedisplay-kindle.zip`'i kullanın; ikisinde de `xh` hazır gelir).
2. İçindeki `extensions` klasörünü Kindle'ın köküne kopyalayın.
   Sonuç: `extensions/homedisplay/config.xml` ve `extensions/homedisplay/bin/xh`.
3. Kindle'da Wi-Fi'ye bağlanın. **Kindle'ın saati doğru olmalı**, yoksa HTTPS bağlantısı kurulamaz.
4. KUAL → **Home Display → Tek seferlik yenile** ile görüntünün geldiğini kontrol edin.
5. **Home Display → Başlat**.

Kindle saatte bir yeni görüntü olup olmadığına bakar. Görüntü değişmediyse ekrana dokunmaz;
gece 00–05 arası hiç kontrol etmez.

**Çıkış:** Home tuşuna basın. Tepki vermezse güç düğmesini ~20 sn basılı tutun; cihaz yeniden başlar
ve normal haline döner.

### Kindle ayarları: `extensions/homedisplay/config.sh`

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `IMAGE_URL` | raw.githubusercontent… | Görüntünün adresi |
| `REFRESH_SECONDS` | 3600 | Kontrol aralığı |
| `FULL_REFRESH_EVERY` | 3 | Kaç güncellemede bir tam yenileme (gölgeyi temizler) |
| `WAIT_MODE` | `sleep` | `sleep`: cihaz uyanık kalır (şarja takılı kullanım). `suspend`: RTC ile uyur (deneysel) |
| `NIGHT_HOURS` | `0-5` | Bu saatlerde kontrol yapılmaz |
| `WIFI_OFF_BETWEEN` | 0 | 1 yapılırsa Wi-Fi kontroller arasında kapanır (pil tasarrufu) |
| `LOW_BATTERY` | 15 | Pil bu yüzdenin altına inince köşede uyarı çıkar |

**Pil:** Duvarda kalıcı kullanım için USB şarja takılı tutun. Şarjsız kullanacaksanız
`WIFI_OFF_BETWEEN=1` yapın.

---

## 3. Sorun giderme

- **Log:** Kindle'da `/tmp/homedisplay.log`.
- **"Sunucuya ulasilamadi":** Kindle saati yanlışsa HTTPS başarısız olur. `bin/xh` dosyasının yerinde
  olduğunu kontrol edin.
- **Altta "Alınamadı: …":** O veri kaynağı o an yanıt vermemiş demektir, pano yine çizilir.
  Ayrıntı için Actions → render → son çalıştırmanın loguna bakın.

## Testler

`python -m pytest` (gereksinimler: `server/requirements.txt`, `tests/requirements.txt`). Testler ağa çıkmaz,
bütün kaynaklar sahte yanıtlarla denenir. Her push'ta GitHub Actions'ta da çalışır (**test** iş akışı).

- **Kaynak hataları:** her kaynak için bağlantı hatası, zaman aşımı, HTTP 500/429, geçersiz JSON
  (ör. Cloudflare sayfası), boş ya da `null` yanıt. Pano her durumda çizilir ve diğer kaynaklar etkilenmez.
- **Hiçbir kaynağa ulaşılamazsa** yeni görüntü yayımlanmaz, Kindle son iyi panoyu göstermeye devam eder.
- **Bozuk veri:** eksik alanlar, `null` değerler, kısa ya da uzun tahmin listeleri, bilinmeyen hava kodları, uç sıcaklık ve rüzgar değerleri.
- **Uzun ve kısa metinler:** çok uzun ya da boş eczane, tatil, pazar, ürün ve konum adları.
  Hiçbir metin ekran kenarına taşmaz.
- **Tarihler:** her ay, haftanın her günü, yılbaşı, 29 Şubat, av yasağı sınırları, bilinen ay evreleri.
- **İkonlar:** her ürünün kendi ikonu olduğu, ikonların kesilmediği, balık türlerinin birbirinden ayırt edildiği.
- **Kindle betikleri:** sahte `eips`/`lipc`/`xh` ile dash ve busybox'ta. Kapsanan durumlar: indirme hatası
  (eski görüntü korunur), boş dosya, değişmeyen görüntü (yeniden çizilmez), Wi-Fi yok, düşük pil, gece saatleri.
- **İş akışları:** zamanlamanın Türkiye saatiyle günde 6 kez olduğu.

## Dosya yapısı

```
server/
  home_display.py      veri toplama + pano çizimi
  icons.py             meyve/sebze/balık ikonları
  local_data.py        aylık mevsim listeleri, Kadıköy semt pazarları, ay evresi
  config.toml          ayarlar (herkese açık, gizli bilgi yazmayın)
  fonts/               Noto Emoji (OFL lisansı)
.github/workflows/
  render.yml           günde 6 kez panoyu üretip display dalına yazar
  kindle-package.yml   Kindle eklentisini xh ile paketleyip Releases'e koyar
  test.yml             her push'ta testleri çalıştırır
kindle/extensions/homedisplay/   KUAL eklentisi
tests/                 test paketi
```
