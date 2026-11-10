# Güvenlik politikası · Security policy

## Açık bildirme (lütfen herkese açık issue açmayın)
Bir güvenlik açığı bulduysanız **GitHub → Security → Report a vulnerability** ile özel olarak bildirin.
Gizli bildirim yalnızca bakımcıya görünür.

If you found a vulnerability, please report it privately via **Security → Report a vulnerability**.
English reports are welcome.

## Ne bekleyebilirsiniz
- 7 gün içinde ilk yanıt; 30 gün içinde düzeltme veya yol haritası.
- Düzeltme yayımlandıktan sonra açığı ortak olarak duyururuz ve isteğinize göre `docs/TESEKKURLER.md` listesine adınızı ekleriz.
- Şu an ücretli ödül programı yoktur; teşekkür listesi ve sürüm notlarında anılma vardır.

## Kapsam
- Şifreleme, kimlik ve imza motoru (`elfcaesar/`), parola kasası, klasör kasası
- Tarayıcı eklentisi ve yerel yardımcı (native messaging), yerel IPC
- Kurulum ve güncelleme bütünlüğü (Authenticode, Ed25519 imzalı MANIFEST)

Kapsam dışı: kullanıcının kendi bilgisayarının ele geçirilmiş olması, sosyal mühendislik, fiziksel erişim.

## Desteklenen sürümler
Yalnızca son sürüm (şu an 6.10.x) güvenlik düzeltmesi alır.

## Sürüm doğrulama
Her sürümün `SHA256SUMS.txt` dosyası Dante sürüm anahtarıyla (Ed25519, parmak izi `B715 8370 19A2 935F`) imzalanır.
Doğrulama: `python tools/verify_release.py SHA256SUMS.txt SHA256SUMS.txt.sig`
