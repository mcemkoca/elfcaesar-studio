# Rakip analizi — ElfCaesar Studio 6.9.1 (10.11.2026)

✓ var · ◐ kısmen · — yok

| Özellik | VeraCrypt | Cryptomator | Picocrypt | AxCrypt | Kleopatra/GPG | Mailvelope | KVKK tarayıcıları | **ElfCaesar 6.9.1** |
|---|---|---|---|---|---|---|---|---|
| Dosya şifreleme (AES-256-GCM, bellek-zor KDF) | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| Klasörü tek dosyada kilitleme | ✓ (konteyner) | ✓ (kasa) | ✓ | — | ◐ | — | — | **✓ 6.9.1** |
| Dosya adlarını gizleme | ✓ | ✓ | ✓ | — | — | — | — | **✓ 6.9.1** (klasör kasası) |
| Anahtar dosyası (2. faktör) | ✓ | — | ✓ | — | — | — | — | **✓ 6.9.1** |
| Güvenli silme | — | — | — | ✓ | — | — | — | **✓ 6.9.1** + tutanak |
| Dijital imza / doğrulama | — | — | — | — | ✓ | ✓ | — | **✓ 6.9.1** |
| Kişiye uçtan uca mesaj (açık anahtar) | — | ◐ (Hub) | — | ◐ | ✓ | ✓ | — | ✓ |
| WhatsApp/Telegram'da yerinde şifreleme | — | — | — | — | — | ◐ (webmail) | — | ✓ |
| Güvenlik kelimeleri (Signal tarzı) | — | — | — | — | ◐ | — | — | ✓ |
| Sızmış parola engeli + kırılma süresi | — | — | — | — | — | — | — | ✓ |
| Ekran görüntüsü kalkanı | — | — | — | — | — | — | — | ✓ |
| Kâğıt kurtarma kitapçığı (QR) | — | ◐ (kurtarma anahtarı) | — | — | ◐ (paperkey) | — | — | ✓ |
| KVKK kişisel veri envanteri | — | — | — | — | — | — | ✓ | ✓ |
| KVKK maskeli kopya | — | — | — | — | — | — | ✓ (PDF) | **✓ 6.9.1** (metin) |
| KVKK imha tutanağı | — | — | — | — | — | — | ◐ | **✓ 6.9.1** |
| Kendi kurulumunu imzayla doğrulama | ◐ (PGP imzası, elle) | — | — | — | — | — | — | **✓ 6.9.1** (uygulama içinde) |
| Türkçe arayüz | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Mobil | — | ✓ | — | ✓ | — | — | — | — |
| Bulut eşitleme için dosya bazlı kasa | — | ✓ | — | ✓ | — | — | — | — |
| Reed-Solomon bozulma onarımı | — | — | ✓ | — | — | — | — | — (6.10.4) |
| PDF/OCR tarama | — | — | — | — | — | — | ✓ | — (6.10.3) |
| Gizli birim (inkâr edilebilirlik) | ✓ | — | ✓ | — | — | — | — | — (bilinçli olarak yok) |

## Kalan eksikler ve plan
- 6.9.2: imzalı güncelleme bildirimi, parolasız kişiye dosya gönderme (kişi kartıyla).
- 6.10.3 KVKK Pro: PDF/OCR, VKN/pasaport, beyaz liste, sektör şablonları, saklama takvimi.
- 6.10.4: Reed-Solomon kurtarma bloğu, >1 GB akış şifreleme.
- Mobil ve Cryptomator tarzı canlı sanal sürücü uzun vadede (7.x).

## ElfCaesar'a özgü yeni fikirler (rakiplerde yok)
1. **KVKK zinciri tek uygulamada:** bul → maskele/şifrele → imha et → tutanak (envanter + imha tutanağı aynı SHA-256 imzalı biçimde).
2. **Kurulumun kendi kendini doğrulaması:** kullanıcı tek tıkla "bu kopya Dante'nin yayımladığıyla aynı mı?" görür.
3. **Sohbet uygulamasında yerinde şifreleme + güvenlik kelimeleri + imza** — e-posta dışı kanallar için PGP deneyimi.
