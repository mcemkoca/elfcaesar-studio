# Güvenilir kod imzalama sertifikası · başvuru rehberi

**Neden gerekli?** Şu anki “Dante” sertifikası öz-imzalıdır; Windows SmartScreen başka bilgisayarlarda “bilinmeyen yayımcı” uyarısı gösterir.
Microsoft'un güvendiği bir sertifika ile imzalanan kurulumlar bu uyarıyı (itibar oluştukça) göstermez.

## Seçenekler (Kasım 2026)
| Seçenek | Kime | Fiyat | Yayımcı adı | Not |
|---|---|---|---|---|
| **Certum Open Source Code Signing** (önerilen) | Açık kaynak projesi olan birey | 69 € (sertifika + kriptografik kart + okuyucu) | “Open Source Developer, <gerçek ad soyad>” | Proje herkese açık olmalı ve seninle ilişkisi görünmeli |
| Certum / Sectigo **OV** Code Signing | Şirket (Dante bir marka/şirket olarak kayıtlıysa) | Yaklaşık 200–400 €/yıl | Şirket unvanı | Ticari ürün için ideal; vergi levhası / ticaret sicili gerekir |
| Azure Artifact Signing | ABD / Kanada'daki bireyler, AB / İngiltere / ABD / Kanada'daki şirketler | ≈ 9,99 $/ay | Doğrulanan ad | Türkiye'deki bireyler şu an uygun değil |

**Önemli:** Sertifikada takma ad (“Dante”) değil, kimlik doğrulamasından geçen **gerçek ad** veya **şirket unvanı** yazar.
“Yayımcı: Dante” görünmesi isteniyorsa Dante adıyla bir şirket/marka tescili ve OV sertifikası gerekir.

## Certum Open Source başvuru adımları
1. Kaynak kodu herkese açık bir depoya koy (ör. GitHub `dante/elfcaesar-studio`), `LICENSE.txt` (MIT) ve README'de adınla projeyle ilişkini göster.
2. shop.certum.eu → Open Source Code Signing (set) siparişi.
3. Kimlik doğrulama (otomatik e-kimlik, fotoğraf veya noter) + adına düzenlenmiş bir fatura (elektrik/su/telefon) + proje adresi.
4. Kart gelince proCertum CardManager ile sertifikayı karta etkinleştir.
5. İmzalama (Windows SDK signtool karttaki anahtarı kullanır):
   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -CertThumbprint <sertifika parmak izi> -ReleaseKey C:\yol\dante_release_ed25519.pem
   ```
   `build.ps1` zaman damgası (RFC 3161) ekler; sertifika süresi dolsa da imza geçerli kalır.

## Bu arada
- Dante Ed25519 sürüm anahtarı ve uygulama içi bütünlük denetimi, sertifikadan bağımsız olarak çalışmaya devam eder.
- Yeni sertifikaya geçince eski öz-imzalı “Dante Root CA”yı kimseye kurdurma.
