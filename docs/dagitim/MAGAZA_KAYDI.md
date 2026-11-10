# Eklenti mağaza kaydı — kopyala/yapıştır metinleri (6.10.3)

Tüm mağazalarda aynı paket: `ElfCaesar-Chrome-WebStore-6.10.3.zip` (Edge ve Opera da bunu kabul eder). Firefox: `ElfCaesar-Firefox-6.10.3.xpi`.
Görseller: `gorseller/` (1280×800 ekran görüntüleri, 440×280 küçük ve 1400×560 büyük tanıtım, 300×300 ve 128×128 logo).

| Mağaza | Ücret | Kayıt adresi | Not |
|---|---|---|---|
| Microsoft Edge Add-ons | Ücretsiz | https://partner.microsoft.com/dashboard/microsoftedge/overview | Microsoft hesabıyla "Edge program" kaydı; inceleme ~7 iş günü |
| Opera Add-ons | Ücretsiz | https://addons.opera.com/developer/ | Opera hesabı; inceleme birkaç gün–birkaç hafta |
| Firefox (AMO) | Ücretsiz | https://addons.mozilla.org/developers/ | Firefox hesabı; "On this site" listelemesi |
| Chrome Web Store | 5 $ tek sefer | https://chrome.google.com/webstore/devconsole | İsteğe bağlı; Edge/Opera paketiyle Chrome kullanıcıları da elle kurabilir |

## Ad
ElfCaesar Parola Köprüsü

## Kısa açıklama (≤132 karakter)
TR: ElfCaesar Studio parola kasasından güvenli otomatik doldurma ve oltalama kalkanı. Parolalar bilgisayarından çıkmaz.
EN: Secure autofill and phishing shield for the offline ElfCaesar Studio password vault. Your passwords never leave your PC.

## Uzun açıklama — TR
ElfCaesar Parola Köprüsü, bilgisayarındaki ücretsiz ve açık kaynak ElfCaesar Studio uygulamasının parola kasasını tarayıcına bağlar.

• Tek tıkla doldurma: giriş formundaki ElfCaesar simgesine tıkla, kaydını seç.
• Birebir alan adı eşleşmesi: parola yalnızca adres çubuğundaki gerçek siteye verilir.
• Oltalama Kalkanı: kayıtlı bir siteyi taklit eden adreste (ör. magaza.com.giris-yap.xyz) hiçbir şey doldurulmaz, kırmızı uyarı çıkar.
• Şifresiz sayfa koruması: https ile kaydedilen parola, aynı sitenin http sürümüne verilmez.
• Bulut yok: eklenti yalnızca bilgisayarındaki uygulamayla konuşur (native messaging). Hesap, sunucu, reklam, izleme yok.

Gerekli: Windows için ElfCaesar Studio 6.10.1 veya üstü (ücretsiz): https://github.com/mcemkoca/elfcaesar-studio/releases/latest
Kaynak kod: https://github.com/mcemkoca/elfcaesar-studio

## Long description — EN
ElfCaesar Password Bridge connects your browser to the password vault of ElfCaesar Studio, a free, open-source and fully offline Windows app.

• One-click fill: click the ElfCaesar icon in a login form and pick your entry.
• Exact domain match: a password is only offered to the real site in the address bar.
• Phishing shield: on look-alike addresses (e.g. shop.com.login-now.xyz) nothing is filled and a red warning appears.
• Downgrade protection: a password saved for https is never filled into the http version of the same site.
• No cloud: the extension only talks to the app on your own computer (native messaging). No account, no server, no ads, no tracking.

Requires ElfCaesar Studio 6.10.1+ for Windows (free): https://github.com/mcemkoca/elfcaesar-studio/releases/latest
Source code: https://github.com/mcemkoca/elfcaesar-studio

## Kategori
Verimlilik / Productivity (Edge: "Productivity"; Firefox: "Privacy & Security")

## Tek amaç (single purpose)
Kullanıcının bilgisayarındaki ElfCaesar Studio parola kasasındaki kayıtları, alan adı doğrulamasından geçen giriş formlarına doldurmak ve taklit sitelere karşı uyarmak.
EN: Fill credentials from the user's local ElfCaesar Studio vault into login forms of the exactly matching site, and warn on look-alike (phishing) sites.

## İzin gerekçeleri
- nativeMessaging: Parolalar yalnızca kullanıcının bilgisayarında, ElfCaesar Studio kasasında durur; eklenti onlara yalnızca yerel yardımcı (com.dante.elfcaesar) üzerinden erişir. İnternete hiçbir istek yapılmaz.
  EN: The vault lives only in the ElfCaesar Studio desktop app; the extension reaches it solely through the local native messaging host. No network requests are made.
- storage: Eşleştirme anahtarını (uygulamanın verdiği rastgele belirteç) saklamak için. Parola veya site geçmişi saklanmaz.
  EN: Stores only the random pairing token issued by the app. No passwords or browsing history are stored.
- İçerik betiği, tüm http/https sayfalarında (host permissions): Giriş formunun hangi sitede açıldığı önceden bilinemediği için parola alanının yanına ElfCaesar simgesini koymak ve taklit site uyarısını göstermek gerekir. Betik yalnızca parola alanı olan sayfalarda görünür; sayfa içeriği okunmaz veya gönderilmez.
  EN: Login forms can appear on any site, so the content script must run on http/https pages to place the ElfCaesar icon next to password fields and show the phishing warning. It does not read or transmit page content.
- Uzaktan kod: Hayır. Tüm kod pakettedir. / Remote code: No.

## Veri kullanımı beyanı (Chrome/Edge formu)
- Toplanan veri: Kimlik doğrulama bilgileri (kullanıcı adı/parola) — yalnızca kullanıcının isteğiyle, yalnızca o sayfanın formuna yazmak için, yerelde. Web geçmişi: yok (açık sekmenin adresi yalnızca anlık alan adı karşılaştırması için yerelde kullanılır, saklanmaz).
- Satılmaz, üçüncü kişilere aktarılmaz, tek amaç dışında kullanılmaz, kredi değerlendirmesi için kullanılmaz. (Üç onay kutusunun üçü de işaretlenir.)
- Gizlilik politikası adresi: https://mcemkoca.github.io/elfcaesar-studio/yasal/#gizlilik

## Destek / web sitesi
- Web sitesi: https://mcemkoca.github.io/elfcaesar-studio/
- Destek: https://github.com/mcemkoca/elfcaesar-studio/issues

## İnceleyici notu (test talimatı)
EN: The extension requires the free ElfCaesar Studio desktop app (Windows). Install from https://github.com/mcemkoca/elfcaesar-studio/releases/latest (during setup keep "Browser extension support" checked), create a password vault, add an entry for https://example.com, then click the extension icon → PAIR and confirm the code in the app. On https://example.com/ any login form shows the ElfCaesar icon in the password field.

## Firefox ek bilgileri
- Eklenti kimliği: elfcaesar@dante.studio · Kaynak kodu istenirse: depo bağlantısı (paket derleme/küçültme içermez, kaynakla birebir aynıdır).
- Lisans: MIT
