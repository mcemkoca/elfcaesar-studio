# ELFCAESAR STUDIO 6.10.3 — Windows Edition
*Bir Dante eseri.*

[![Testler](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/tests.yml/badge.svg)](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/tests.yml)
[![CodeQL](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/codeql.yml/badge.svg)](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/codeql.yml)
[![Güvenlik taraması](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/security-scan.yml/badge.svg)](https://github.com/mcemkoca/elfcaesar-studio/actions/workflows/security-scan.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/mcemkoca/elfcaesar-studio/badge)](https://scorecard.dev/viewer/?uri=github.com/mcemkoca/elfcaesar-studio)

Çevrimdışı çalışan şifreleme, uçtan uca şifreli mesaj, dijital imza, parola kasası ve KVKK kişisel veri kalkanı.
Hesap yok, sunucu yok; verin bilgisayarından çıkmaz.

- **İndir:** [Son sürüm (Releases)](https://github.com/mcemkoca/elfcaesar-studio/releases/latest)
- **Kılavuz ve tanıtım videosu:** https://mcemkoca.github.io/elfcaesar-studio/kilavuz/
- **Gizlilik politikası ve kullanım koşulları:** https://mcemkoca.github.io/elfcaesar-studio/yasal/
- **Code signing policy:** https://mcemkoca.github.io/elfcaesar-studio/kod-imzalama/
- **Güvenlik açığı bildirimi:** [SECURITY.md](SECURITY.md) · **Beta geri bildirimi:** [Issues → Beta geri bildirimi](https://github.com/mcemkoca/elfcaesar-studio/issues/new?template=beta.yml)

### “Windows bilgisayarınızı korudu” uyarısı
Kurulum dosyası Dante'nin kendi sertifikasıyla imzalıdır; Windows bu sertifikayı henüz tanımadığı için SmartScreen
uyarı gösterebilir. Bu beklenen bir durumdur: **Ek bilgi → Yine de çalıştır**. Açık kaynak kod imzalama sertifikası
başvurusu sürmektedir. Kurmadan önce dosyanın gerçekten bizden geldiğini aşağıdaki gibi doğrulayabilirsin.

### İndirdiğin dosyayı doğrula
Her sürümde `SHA256SUMS.txt` ve Dante sürüm anahtarıyla (Ed25519, parmak izi `B715 8370 19A2 935F`) imzalanmış
`SHA256SUMS.txt.sig` bulunur. Dosyaları aynı klasöre indir ve:

```
pip install cryptography
python verify_release.py SHA256SUMS.txt SHA256SUMS.txt.sig
```
`verify_release.py` depodaki `tools/` klasöründedir. Yalnızca özet için PowerShell: `Get-FileHash .\ElfCaesarStudio-6.10.3-Setup.exe`.
Dosyanın VirusTotal sonucu sürüm notlarındadır.

## Sürüm notları
## 6.10.3 — Firefox ve mağaza paketleri
- `TarayiciEklentisi\ElfCaesar-Firefox-6.10.3.xpi`: Firefox → about:debugging → Geçici eklenti yükle (imzalı sürüm AMO onayından sonra).
- `TarayiciEklentisi\ElfCaesar-Chrome-WebStore-6.10.3.zip`: Chrome Web Mağazası geliştirici panosuna yüklenecek paket.

## 6.10.2 — Sağlamlaştırma (beta adayı)
- İç güvenlik incelemesi ve düzeltmeleri: `docs/GUVENLIK_INCELEMESI.md`. Kod imzalama başvuru rehberi: `docs/KOD_IMZALAMA.md`.
- Parola Kasası otomatik yedekleri, bulut klasörü senkronu ve çakışma birleştirme; Windows Pano Geçmişi koruması.
- SADE / TAM arayüz modu, HATA BİLDİR, gizlilik politikası ve kullanım koşulları (taslak).

## 6.10.1 — Tarayıcı eklentisi
- `TarayiciEklentisi` klasörü: chrome://extensions → Geliştirici modu → Paketlenmemiş öğe yükle. Eklenti simgesi → EŞLEŞTİR → uygulamada kodu onayla.
- Giriş formlarında ElfCaesar düğmesi; yalnızca adres çubuğundaki alan adıyla birebir eşleşen kayıt doldurulur; taklit sitede kırmızı uyarı.

## 6.10.0 — Parola Kasası
- Parolalar tek ana parolayla AES-256-GCM kasasında; tarayıcılardan CSV ile içe aktarma, otomatik tamamlamalı arama, Ctrl+Alt+P Hızlı Doldur.
- Parola Denetimi, Domino Analizi, Oltalama Kalkanı, Dijital Miras (Shamir), Baskı Parolası, kişiye şifreli parola gönderimi.

## 6.9.3 — Rozetler ve parıltı
- 15 Elf dilinde adlandırılmış rozet, Rozet Vitrini ve kazanma kutlaması (Kontrol Merkezi > ROZET VİTRİNİ).
- 3B düğmeler, akıcı sayfa geçişleri ve parlayan kart kenarları. Hareketi azaltmak için `ELFCAESAR_REDUCED_MOTION=1`.

## 6.9.2 — Kılavuz
- Her bölüm ve kart başlığında **ⓘ** düğmesi; **F1** her yerde kılavuzu açar (arama, bölüm listesi, önceki/sonraki).
- Resimli tam kılavuz uygulamayla gelir: Kılavuz penceresi > RESİMLİ KILAVUZ veya Başlat menüsü > *ElfCaesar Studio Kılavuzu*.
- Türkçe seslendirmeli tanıtım videosu (`ElfCaesar_Studio_6.9.2_Tanitim.mp4`) ve altyazısı.

## 6.9.1 — Araç Kutusu ve Dante imzası
- **Klasör kasası:** klasörü alt klasörleri ve dosya adlarıyla tek `.elfvault` dosyasına şifreler; Gezgin'de klasöre sağ tık → *ElfCaesar ile klasörü kilitle*.
- **Anahtar dosyası (ikinci faktör):** kasa parola + belirli bir dosya olmadan açılmaz; 512 bit anahtar üretici.
- **Dijital imza:** dosyaya sağ tık → *ElfCaesar ile imzala* (`.elfsig`); `.elfsig` çift tık → imza doğrulama, rehberdeki doğrulanmış kişilere “GÜVENİLİR”.
- **KVKK maskeli kopya** ve **güvenli imha + KVKK imha tutanağı**.
- **Kurulum bütünlüğü:** 996 dosya Dante sürüm anahtarıyla (Ed25519, parmak izi `B715 8370 19A2 935F`) imzalı manifeste göre doğrulanır; `ElfCaesarStudio.exe` ve Setup Authenticode imzalı (yayımcı: Dante).

## 6.9.0 — KVKK Kalkanı (Kurumsal · Beta)
- Klasör taraması: TXT, CSV, JSON, XML, HTML, EML, DOCX, XLSX, PPTX, ODT/ODS içinde T.C. kimlik, IBAN, kart, telefon, e-posta, parola ifadesi.
- Bulunan değerler gösterilmez/kaydedilmez; yalnızca tür ve adet. Risk: yüksek / orta / düşük.
- KASAYA AL: seçili dosyalar tek parolayla AES-256-GCM; şifreli kopya doğrulanır; orijinali silmek için ayrıca sorulur.
- Yazdırılabilir Kişisel Veri Envanteri raporu (SHA-256 özeti, Dante imzası). Hukuki görüş değildir.

## 6.8.3 — Ekran kalkanı ve kâğıt yedek
- Ekran görüntüsü kalkanı (Güvenlik Merkezi > Korumalar): KAPALI / HASSAS PENCERELER / TÜM UYGULAMA.
- Kurtarma kitapçığı (Güvenli Kasa > KURTARMA KİTAPÇIĞI): QR + numaralı satırlar; parola yazılmaz. KİTAPÇIKTAN GERİ YÜKLE ile geri gelir.


## 6.8.2 — Parola zekâsı
- **Çevrimdışı sızıntı veritabanı:** 10.000 küresel yaygın parola (SecLists, MIT) + Türkiye'ye özgü tabanlar (takımlar, şehirler, isimler, sevgi sözcükleri, klavye dizileri). İnternete bağlanılmaz.
- **Akıllı eşleştirme:** `Galatasaray1905`, `G@l@t@s@r@y`, `P@ssw0rd`, `Zeynep1990`, `parolaparola` gibi türevler yakalanır ve gerçekçi tahmin süresiyle puanlanır.
- **Sızmış parola engeli:** Yeni kasa parolası listedeki bir parola veya basit türeviyse kabul edilmez (NIST SP 800-63B).
- **Saldırgan donanımı:** Ev PC · Oyun PC · Bulut (8× H100) · Saldırı çiftliği (1.000 GPU); bulut ve çiftlik için tahmini kırma maliyeti.


## 6.8.1 — Kırılma süresi · Dante imzası · Hoş geldin hediyesi
- **Kırılma süresi:** Parola penceresi ve Güvenlik Merkezi > Parola Laboratuvarı, parolanın 5 senaryoda ortalama kırılma süresini gösterir: çevrim içi (hız sınırlı / korumasız), ElfCaesar kasası (scrypt N=2¹⁵ r=8; 1 GPU ≈ 3.500, 1.000 GPU ≈ 3,5 milyon deneme/sn), sızan hızlı özet (MD5/NTLM, ≈100 milyar/sn).
- **Saldırı yöntemleri:** kaba kuvvet, sözlük, hibrit/kural tabanlı, örüntü, sızıntı listesi — parolaya göre risk ve nedeni.
- **Yapımcı imzası — Dante:** açılış, tanıtım, Hakkında, kenar çubuğu, kurulum sihirbazı, Uygulamalar listesi (Yayımcı) ve .exe dosya bilgileri.
- **Hoş geldin hediyesi:** ilk açılışta sinematik tanıtım ve bilgisayarında üretilen “Kurucu Elf” rozeti (Hakkında > TANITIMI İZLE).
- **Profesyonel sürümleme:** SemVer (6.8.1, 6.8.2 …), Windows dosya sürümü 6.8.1.681, uygulama içi Yenilikler penceresi, `CHANGELOG.md`, `ROADMAP.md`.


## Kurulum (son kullanıcı)
1. `ElfCaesarStudio-6.9.1-Setup.exe` dosyasını çalıştır.
2. “Yalnızca geçerli kullanıcı için kurulsun (önerilir)” → yönetici izni gerekmez.
3. Sihirbazı izle; *Ek işlemler* sayfasında masaüstü simgesi, Gezgin sağ tık menüsü ve dosya ilişkilendirmelerini seç.
4. Kaldırmak için: *Ayarlar → Uygulamalar → ElfCaesar Studio → Kaldır*.

Python kurmak gerekmez. Paket imzasızsa SmartScreen uyarısında *Ek bilgi → Yine de çalıştır*.

## 6.8 — Windows kurulum paketi
- Standart Inno Setup sihirbazı (Türkçe/İngilizce), logodan üretilmiş sihirbaz görselleri (yüksek DPI dahil).
- Kullanıcı başına (yöneticisiz) veya tüm kullanıcılar için kurulum; 64 bit, Windows 10+.
- Başlat menüsü ve masaüstü kısayolları, *Mesaj Köprüsü* kısayolu, Win+R ile başlatma.
- Gezgin sağ tık menüsü, `.elfvault .elfcontact .elfid .elmsg .elfdm` dosya ilişkilendirmeleri, isteğe bağlı Windows ile başlat.
- Tek örnek: sağ tık / çift tık işlemleri açık pencereye gider (yerel, belirteçli bağlantı).
- Yüksek DPI farkındalığı, görev çubuğu kimliği, kurulum programının tanıdığı uygulama mutex'i.
- Çökme günlüğü (`%LOCALAPPDATA%\ElfCaesar\logs`, içerik içermez) ve kullanıcıya bildirim.
- Kaldırırken ayarlar/kişi defteri için soru; kimlik ve kasa dosyalarına dokunulmaz.
- Derleme: `packaging/build.ps1`, GitHub Actions iş akışı, isteğe bağlı kod imzalama. Ayrıntılar: `packaging/BUILD.md`.
- Geliştirici (Python ile) kurulum betikleri `tools/dev/` klasörüne taşındı; `run.bat` kaynak koddan çalıştırır.

## 6.7 — WhatsApp / Telegram için şifreli mesaj köprüsü
6.6 temel alındı. Şifreleme, kimlik ve mesajlaşma **motorları değişmedi**; yeni katman motorların ürettiği paketleri sohbet kanallarında taşır.

**Önemli:** WhatsApp ve Telegram kendi sağ tık menülerine üçüncü taraf öğe eklenmesine izin vermez. ElfCaesar bu yüzden her uygulamada seçili metin üzerinde çalışan **genel kısayollar**, **pano radarı** ve dosyalar için **Windows Gezgini sağ tık menüsü** kullanır.

### Yeni özellikler
1. **ELF1 sohbet zırhı** — Şifreli paket tek satırlık `🔐ELF1:…` bloğuna dönüşür. Kayıpsız kompakt kodlama sayesinde imzalı kısa mesaj ~%45 daha kısa. WhatsApp biçimlendirme işaretlerinden (`_ * ~`) etkilenmez, satır kırılmasına dayanıklıdır, sağlama ile eksik kopyalamayı yakalar.
2. **Yerinde şifreleme — Ctrl+Alt+E** — WhatsApp/Telegram'da yazdığın metni seç, kısayola bas: metin seçili alıcıya şifrelenip yerine yapıştırılır.
3. **Yerinde çözme — Ctrl+Alt+D** — Gelen şifreli mesajı seç, kısayola bas: mühürlü balonda açılır.
4. **Pano radarı** — Şifreli mesaj veya kişi kartı kopyaladığında bildirim ve tek tıkla ÇÖZ.
5. **Mühürlü mesaj balonu ve güven rozetleri** — DOĞRULANMIŞ KİŞİ · DEFTERDE/DOĞRULANMAMIŞ · İMZALI/BİLİNMEYEN · İMZASIZ · PAROLALI.
6. **Okuduktan sonra yok et** — Çözülen mesaj 30/60/120 sn sonra kapanır; metin hiçbir yere kaydedilmez.
7. **Kişi defteri** — Yalnızca açık anahtarlar (`%APPDATA%\ElfCaesar\contacts.json`); özel anahtar asla yazılmaz.
8. **Güvenlik kelimeleri** — Parmak izinden 6 Türkçe kelime; telefonda sesli karşılaştırıp kişiyi “doğrulandı” işaretle.
9. **Kişi kartını sohbetle paylaş** — `🔐ELF1:K:` bloğu; karşı taraf kopyalar, radar deftere eklemeyi önerir.
10. **Grup mesajı** — Birden çok alıcı seç; tek blok, her alıcı yalnızca kendi kopyasını açar.
11. **Otomatik parçalama** — Uzun mesajlar Telegram (4096) sınırına göre numaralı parçalara bölünür; parçalar farklı zamanlarda kopyalansa da birleştirilir.
12. **Ortak parolalı sohbet mesajı** — Kimliği olmayan biriyle AES-256-GCM parolalı mesaj.
13. **Kimlik oturumu** — `.elfid` bir kez açılır; özel anahtar yalnızca bellekte; kilit/panik/kapanışta kapanır.
14. **Mini köprü penceresi — Ctrl+Alt+B** — Sohbet uygulamasının yanında her zaman üstte duran küçük yazma/çözme penceresi; **Yanıtla** ile gönderen otomatik seçilir.
15. **Windows Gezgini sağ tık menüsü** — Dosyalarda “ElfCaesar ile şifrele”, `.elfvault` dosyalarında “çöz”, `.elfcontact` dosyalarında “kişi defterine ekle” (yalnızca geçerli kullanıcı, yönetici gerekmez; Mesaj Köprüsü > Entegrasyonlar'dan aç/kapat).
16. **Güvenlik seviyesi entegrasyonu** — Doğrulanmamış kişiler ve imzasız mesajlar öneri olarak görünür.

### Kısa kullanım
1. Her iki taraf: Güvenli Kasa > YENİ KİMLİK, sonra Mesaj Köprüsü > KİMLİĞİ AÇ.
2. KARTIMI SOHBETTE PAYLAŞ → WhatsApp'a yapıştır. Karşı taraf kopyalar → radar → deftere ekle.
3. Telefonda 6 güvenlik kelimesini karşılaştır → SESLİ DOĞRULA.
4. Mesajı yaz, seç, **Ctrl+Alt+E**, Enter. Karşı taraf mesajı seçer, **Ctrl+Alt+D**.

### Sınırlar
- Genel kısayollar ve Gezgin menüsü yalnızca Windows'ta; diğer sistemlerde kopyala → PANODAN ÇÖZ kullanılır.
- Kısayollar seçimi almak için panoyu kullanır; o anki pano içeriğinin üzerine yazılır.
- Sohbet uygulaması kimin kime, ne zaman mesaj attığını (meta veri) yine görür; yalnızca içerik korunur.
- Windows cihazında henüz test edilmedi.

## 6.6 — Güvenlik zekâsı ve marka kimliği
6.5 temel alındı. Şifreleme (`secure`), kimlik/mesajlaşma (`identity`) ve ELFC2 (`engine`) motorlarında **hiçbir değişiklik yapılmadı**.

### Logo
- `assets/` klasörü: tam logo (48–256 px), küçük boyutlar için yazısız amblem (16–64 px), çok boyutlu `elfcaesar.ico`.
- Kullanıldığı yerler: pencere/görev çubuğu ikonu, açılış ekranı, kenar çubuğu markası (tıklayınca Hakkında), Kontrol Merkezi başlığı, animasyonlu çekirdeğin merkezi, güvenlik göstergesi, parola penceresi, gizlilik kilidi, Hakkında penceresi, masaüstü kısayolu ve Inno Setup kurulum ikonu.

### Güvenlik seviyesi (0–100)
- Beş kademe: **Çırak → Muhafız → Şövalye → Kale → Mithril**. Üst çubuktaki rozet ve ana ekran kartı canlı güncellenir.
- Puan; kasa motoru, son kasa parolasının seviyesi, pano koruması, gizlilik kilidi, imzalı gönderim, sabitlenmiş gönderen ve hassas verinin ELFC2 ile kodlanıp kodlanmadığından hesaplanır. İçerik puana girmez, kaydedilmez.

### Öneri seviyeleri
- **KRİTİK · YÜKSEK · ORTA · DÜŞÜK · BİLGİ** önceliğiyle sıralı öneriler; her biri kazandıracağı puanı ve tek tıklık eylemi (ETKİNLEŞTİR, KASAYA GİT, LABORATUVAR…) gösterir.

### Parola kalkan seviyesi
- Yeni parola penceresi: canlı 5 kademeli ölçer (**Kâğıt Kalkan → Tahta Kalkan → Demir Kalkan → Çelik Kale → Mithril Zırh**), bit tahmini, ipuçları, eşleşme göstergesi, parola üretici. Zayıf parolada ek onay istenir.
- Parola Laboratuvarı: Güvenlik Merkezi'nde parolayı kaydetmeden deneme alanı.

### Korumalar
- **Pano koruması:** Parola ve kasa içeriği kopyalanınca pano 15/30/60 sn sonra temizlenir (pano değişmediyse).
- **Gizlilik kilidi:** 2/5/10 dk hareketsizlikte ekran gizlenir, kasa SONUÇ alanındaki açık metin silinir. (Hesap parolası olmayan bir gizlilik perdesidir.)
- **Panik modu (Ctrl+Shift+L):** Tüm editörleri, analiz sonuçlarını, kimlik kartlarını ve panoyu temizler, ekranı gizler. Diskteki dosyalara dokunmaz.
- **Hassas veri uyarısı:** ELFC2 kodlamasından önce e-posta, IBAN, Luhn doğrulamalı kart numarası, algoritmayla doğrulanan T.C. kimlik numarası, telefon ve “şifre:” ifadelerini yakalar; metni Güvenli Kasa'ya taşımayı önerir.
- Ayarlar `%APPDATA%\ElfCaesar\settings.json` dosyasında tutulur; yalnızca açık/kapalı ve süre değerleri içerir.

## 6.5 — Advanced Visual Design
6.4 temel alındı. Şifreleme (`secure`), kimlik/mesajlaşma (`identity`) ve ELFC2 (`engine`) motorlarında **hiçbir değişiklik yapılmadı**; dosyalar bayt düzeyinde 6.4 ile aynıdır. Yeni kod yalnızca `gui.py` ve yeni `studio_ui/` arayüz paketindedir.

- **Animasyonlu kripto çekirdeği:** Kontrol Merkezi'nde dönen halkalar, yörünge düğümleri, tarama çizgisi ve nabız halkası. Yalnızca ana ekran görünürken çalışır; başka sekmede durur.
- **Sistem aktivite paneli:** Son 30 dakikanın dakika bazlı işlem grafiği (üzerine gelince değer), kategori çubukları ve son işlemler listesi. Durum kartları kasa motorunu, sürükle-bırakı ve oturum başarı oranını gerçek değerlerle gösterir.
- **İkon ve buton sistemi:** Platformdan bağımsız vektör ikon seti; yuvarlatılmış, klavyeyle kullanılabilir butonlar (primary · accent · secondary · ghost · danger, md/sm). Dar alanda araç çubukları otomatik olarak ikon moduna geçer, ipuçları açılır.
- **Sekmeli çalışma alanları:** Açılan sayfalar sekme olarak kalır; editör içerikleri ve kaydırma konumu korunur. Ctrl+1…8 sayfa, Ctrl+Tab sekme geçişi, Ctrl+W veya orta tık sekme kapatır.
- **Sürükle-bırak:** Metin dosyaları editörlere, belgeler Dosya Kasası alanına bırakılabilir (`.elfvault` → çözme, diğerleri → şifreleme). `tkinterdnd2` kurulu değilse alanlar tıklanınca dosya seçtirir.
- **Görsel kimlik kartları:** Kimlik oluşturma, kişi kartı doğrulama ve imzalı mesaj açma sonrası parmak izinden üretilen simetrik mühür, rol etiketi ve gruplanmış parmak izi. Mühür yalnızca görsel tanıma içindir; doğrulama tam parmak izi karşılaştırmasıyla yapılır.
- **Bildirim ve işlem geçmişi:** Sağ altta kayan bildirimler, zil rozeti, İşlem Geçmişi sayfası (kategori filtresi, arama, dışa aktarma, temizleme). Yalnızca işlem adı/kategori/sonuç tutulur; içerik, parola ve anahtar kaydedilmez, diske yazılmaz.
- **Sindarin / Tengwar ekranı:** Dil → mod → yazı kavram haritası, seçilebilir mod kartları, 4 seri × 6 derece témar referans tablosu, yol haritası. Glif üretimi ve çeviri hâlâ yoktur.
- **Ek iyileştirmeler:** Editörlerde satır numaraları, kaydırma çubuğu, kes/geri al/yinele, imleç konumu ve seçim sayacı; sayaçlar artık programatik değişikliklerde de güncellenir. Özel kaydırma seçici (fare, sürükleme, ok tuşları). Analizde Türkçe benzerlik puanı, puan haritası, sıralama ve en olası adayı aktarma. Alfabe sayfasında harf kutuları ve kaydırma önizlemesi. 1120 px altında kompakt kenar çubuğu.

## Çalıştırma
Windows üzerinde Python 3.11+ ve Tcl/Tk gerekir:
`py -3 -m pip install -r requirements.txt`
Sürükle-bırak için (isteğe bağlı): `py -3 -m pip install -r requirements-optional.txt`
Ardından `run.bat` ile başlatılabilir.

## Test
`py -3 -m pytest -q` — motor ve arayüz modeli testleri.
Pencere açan arayüz testleri isteğe bağlıdır: `set ELFCAESAR_GUI_TESTS=1` ardından `py -3 -m pytest -q`.

## Güvenlik notu
ELFC2 kodlama/obfuscation işlemidir, şifreleme değildir. Gerçek gizlilik için Güvenli Kasa'nın AES-GCM tabanlı işlevlerini kullanın. Analiz puanı yalnızca bir sıralama ipucudur. Bu uygulama bağımsız güvenlik denetiminden geçmemiştir.

## Önceki sürümler
- 6.4: Editör araçları, sayaçlar, analiz filtresi ve kaydırma çubukları, kasa hızlı gezinme.
- 6.3 ve öncesi: Duyarlı yerleşim, obsidyen/amber/camgöbeği kimlik, ELFC2 kodlaması, AES-256-GCM kasa, X25519/Ed25519 kimlikler.
