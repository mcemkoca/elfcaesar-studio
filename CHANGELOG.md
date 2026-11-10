# Sürüm notları — ElfCaesar Studio

Sürümleme: MAJOR.MINOR.PATCH — PATCH düzeltme ve küçük iyileştirme, MINOR yeni özellik grubu, MAJOR dosya biçimi veya motor değişikliği.

## 6.10.3 — Firefox ve mağaza paketleri (10.11.2026)

- Tarayıcı eklentisinin Firefox sürümü (`ElfCaesar-Firefox-6.10.3.xpi`) ve Mozilla yerel yardımcı kaydı.
- Chrome Web Mağazası'na yüklenmeye hazır paket (`ElfCaesar-Chrome-WebStore-6.10.3.zip`).
- Eklenti `web-ext lint` ile temizlendi (innerHTML kaldırıldı); tarayıcı tanıma Firefox'u da içerir.
- Kılavuz ekran görüntüleri ve tanıtım videosu 6.10.3 arayüzüyle yenilendi; sessiz/altyazılı video ve seslendirme kayıt metni eklendi.

## 6.10.2 — Sağlamlaştırma · beta adayı (10.11.2026)

- Güvenlik puanı düzeltildi: yeni kurulum artık Mithril 100 göstermez; kimlik, parola kasası ve kasa sağlığı puana katıldı.
- İç güvenlik incelemesi: paylaşımlı barındırma alan adları (github.io vb.) ayrıldı, https kaydı http sayfaya verilmez, eşleştirme kodu düzeltildi, eşleştirme isteği sınırlandı.
- Kopyalanan parolalar Windows Pano Geçmişi'ne (Win+V) ve bulut panosuna düşmez.
- Parola Kasası otomatik yedekleri (son 20) ve yedekten geri yükleme.
- Bulut klasörü senkronu: OneDrive / Dropbox / Google Drive'daki kasa iki bilgisayarda değişse de kayıt kayıt birleştirilir; çakışma kopyaları birleştirilir.
- Arayüz modu: SADE (yalnızca güvenlik araçları) / TAM.
- Hakkında → HATA BİLDİR (içerik içermeyen tanı raporu) ve GİZLİLİK (gizlilik politikası ve kullanım koşulları).

## 6.10.1 — Tarayıcı eklentisi (10.11.2026)

- ElfCaesar Parola Köprüsü eklentisi (Chrome, Edge, Brave, Opera, Vivaldi): giriş formlarına ElfCaesar düğmesi ve otomatik doldurma.
- Adres çubuğundaki gerçek alan adı doğrulanır; parola yalnızca birebir eşleşen kayda verilir, taklit sitelerde kırmızı Oltalama Kalkanı uyarısı.
- Güvenli eşleştirme: eklenti ve uygulamada aynı kod; uygulama yalnızca eşleşme anahtarının özetini saklar.
- Yerel tarayıcı yardımcısı (ElfCaesarNativeHost.exe) ve kurulumda otomatik kayıt; parolalar bilgisayardan çıkmaz.
- Hızlı Doldur güvenliği: hedef pencere öne getirilemezse hiçbir tuş gönderilmez, parola pano korumasıyla kopyalanır.
- Tanıtım videosu yenilendi: Parola Kasası, tarayıcı eklentisi ve rozetler eklendi.

## 6.10.0 — Parola Kasası (10.11.2026)

- Parola Kasası: tek ana parolayla AES-256-GCM; kilit, panik ve otomatik kilitte bellekten silinir; parola geçmişi.
- Tarayıcılardan içe aktarma: Chrome, Edge, Brave, Opera, Firefox, Bitwarden, KeePass, LastPass CSV; tekrarları birleştirir, açık CSV'yi imha eder.
- Otomatik tamamlamalı arama ve Hızlı Doldur (Ctrl+Alt+P): pencereyi tanır, kullanıcı adı + Tab + parolayı panosuz yazar.
- Parola Denetimi: sızmış, tekrar eden, birbirine benzeyen, zayıf, eski parolalar ve kasa sağlık puanı; isteğe bağlı k-anonim HIBP kontrolü.
- YENİ · Domino Analizi: bir hesap (özellikle e-posta) düşerse zincirleme hangi hesapların düşeceğini gösterir.
- YENİ · Oltalama Kalkanı: kopyalanan bağlantı kasadaki bir siteyi taklit ediyorsa (paypa1.com, trendyol.com.giris.xyz) uyarır.
- YENİ · Dijital Miras: Shamir'in Gizli Paylaşımı ile k / n parça; yazdırılabilir parça sayfaları, mirastan kurtarma.
- YENİ · Baskı Parolası: zorla açtırılırsan ikinci parola zararsız bir sahte kasa açar.
- YENİ · Kişiye şifreli parola gönderimi: kayıt, yalnızca alıcının açabileceği bir sohbet mesajına dönüşür; alıcı tek tıkla kasasına ekler.

## 6.9.3 — Rozetler ve parıltı (10.11.2026)

- 15 rozet: adları Elf dillerinden — Annon, Tîw, Parf, Draug, Certh, Istar, Galadh, Ithildin, Thoron, Lassë, Elen, Elessar, Tirith, Mithril ve Aran.
- Rozet Vitrini: anlam, nadirlik (yaygın / nadir / destansı / efsanevi), kazanma koşulu ve tarih; Kontrol Merkezi'nde rozet şeridi.
- Yeni rozet kutlaması: alttan kayarak gelen, ışık halkalı kart.
- 3B düğmeler: derinlik kenarı, parlak üst yüz, fareyle kalkma, basınca içeri gömülme, birincil düğmelerde ışık süzülmesi.
- Akıcı geçişler: sayfalar yumuşakça kayarak açılır, başlık belirerek gelir, kart kenarları fareyle parlar.

## 6.9.2 — Kılavuz (10.11.2026)

- Her bölümün ve kartın başlığında ⓘ kılavuz düğmesi: tıklayınca kılavuz doğrudan o kısma gider ve vurgular.
- F1 Kılavuz penceresi: 15 bölüm, adım adım kullanım, ipuçları, kart açıklamaları, arama ve önceki/sonraki gezinme.
- Resimli tam kılavuz: her ekranın görüntüsüyle birlikte uygulamayla gelir, internet gerektirmez (Başlat menüsü > ElfCaesar Studio Kılavuzu).
- Bölüm bölüm Türkçe seslendirmeli tanıtım videosu ve altyazısı.

## 6.9.1 — Araç Kutusu ve Dante imzası (10.11.2026)

- Klasör kasası: bütün bir klasörü alt klasörleri ve dosya adlarıyla birlikte tek .elfvault dosyasına şifreler.
- Anahtar dosyası (ikinci faktör): kasa parola + belirli bir dosya olmadan açılmaz; 512 bit anahtar üretici.
- Dijital imza: dosyaları kimliğinle imzala (.elfsig), karşı taraf kimden geldiğini ve değişmediğini doğrulasın.
- KVKK maskeli kopya: T.C. kimlik, IBAN, kart, telefon, e-posta ve parolaları gizleyerek paylaşılabilir kopya.
- Güvenli imha + KVKK imha tutanağı: üzerine yazarak silme, dosya adı anonimleştirme, yazdırılabilir tutanak.
- Kurulum bütünlüğü: her dosya Dante sürüm anahtarıyla imzalı manifeste göre doğrulanır; kurulum paketi Dante kod imzalı.

## 6.9.0 — KVKK Kalkanı (Kurumsal · Beta) (10.11.2026)

- KVKK Kalkanı: seçilen klasörlerde T.C. kimlik, IBAN, kart, telefon, e-posta ve parola ifadesi içeren dosyaları bulur.
- Desteklenen biçimler: TXT, CSV, JSON, XML, HTML, EML, DOCX, XLSX, PPTX, ODT/ODS (Türkçe eski kodlama dahil).
- Risk sınıflandırması (yüksek / orta / düşük); bulunan değerler asla gösterilmez veya kaydedilmez, yalnızca tür ve adet.
- KASAYA AL: seçili dosyaları tek parolayla AES-256-GCM kasasına alır, şifreli kopyayı doğrular, orijinali silmeyi sorar.
- Yazdırılabilir Kişisel Veri Envanteri raporu: kategoriler, dosyalar, önerilen teknik tedbirler, SHA-256 özeti ve Dante imzası.

## 6.8.3 — Ekran kalkanı ve kâğıt yedek (10.11.2026)

- Ekran görüntüsü kalkanı: parola, mühürlü mesaj ve mini köprü pencereleri ekran görüntüsü/paylaşımında siyah görünür.
- Kurtarma kitapçığı: şifreli kimliğin QR + satır satır yazdırılabilir yedeği; parola kitapçığa yazılmaz.
- Kitapçıktan geri yükleme: QR metni veya elle yazılan satırlar; her satırda yazım hatasını yakalayan sağlama.
- Güvenlik Merkezi'ne yeni öneriler: kâğıt yedek ve ekran kalkanı.

## 6.8.2 — Parola zekâsı (10.11.2026)

- Çevrimdışı yaygın/sızmış parola veritabanı: 10.000 küresel (SecLists, MIT) + Türkiye'ye özgü tabanlar.
- Akıllı eşleştirme: büyük/küçük harf, Türkçe karakter, a→@ dönüşümleri, sondaki yıl/rakam/sembol, tekrar (parolaparola).
- Yeni kasa parolası olarak sızmış parolalar ve basit türevleri kabul edilmez (NIST SP 800-63B).
- Saldırgan donanımı seçimi: ev PC, oyun PC, bulut (8× H100), saldırı çiftliği (1.000 GPU).
- Bulut ve çiftlik için tahmini kırma maliyeti (ABD doları).
- Sızıntı listesi yöntemi artık gerçek liste eşleşmesine göre risk gösterir.

## 6.8.1 — Kırılma süresi · Dante imzası · Hoş geldin tanıtımı (10.11.2026)

- Parola kırılma süresi: 5 saldırı senaryosu (çevrim içi, ElfCaesar kasası 1 / 1.000 GPU, sızan hızlı özet).
- Saldırı yöntemleri analizi: kaba kuvvet, sözlük, hibrit, örüntü, sızıntı listesi — her biri için risk.
- Parola penceresinde canlı kırılma süresi; Parola Laboratuvarı'nda ayrıntılı tablo.
- Yapımcı imzası: Dante — açılış, Hakkında, kenar çubuğu, kurulum sihirbazı ve dosya bilgileri.
- Hoş geldin hediyesi: ilk açılışta sinematik tanıtım ve “Kurucu Elf” rozeti.
- Uygulama içi Yenilikler penceresi ve SemVer sürümleme (MAJOR.MINOR.PATCH).

## 6.8.0 — Windows kurulum paketi (10.11.2026)

- Standart Inno Setup sihirbazı, kullanıcı başına kurulum, Başlat menüsü ve masaüstü kısayolları.
- Gezgin sağ tık menüsü, dosya ilişkilendirmeleri, tek örnek davranışı, çökme günlüğü.

## 6.7.0 — Mesaj Köprüsü (10.11.2026)

- WhatsApp / Telegram için ELF1 sohbet zırhı, yerinde şifreleme (Ctrl+Alt+E) ve çözme (Ctrl+Alt+D).
- Kişi defteri, güvenlik kelimeleri, grup mesajı, okuduktan sonra yok et, pano radarı.

## 6.6.0 — Güvenlik Zekâsı (10.11.2026)

- Güvenlik seviyesi (Çırak → Mithril), öneri seviyeleri, parola kalkan seviyesi, panik modu.

## 6.5.0 — Gelişmiş görsel tasarım (09.11.2026)

- Animasyonlu çekirdek, aktivite grafikleri, sekmeli çalışma alanları, kimlik kartları.
