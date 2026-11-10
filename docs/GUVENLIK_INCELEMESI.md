# ElfCaesar Studio 6.10.2 · İç güvenlik incelemesi

**Kapsam:** Parola Kasası (`pwvault.py`, `pwaudit.py`, `shamir.py`), tarayıcı köprüsü (`browser_bridge.py`, `native_host.py`,
`runtime.InstanceServer`), Hızlı Doldur (`autotype.py`), pano (`clipguard.py`), tarayıcı eklentisi (`browser-extension/`).
Şifreleme motorları (`elfcaesar/`) değiştirilmedi ve bu incelemenin dışındadır.

**Önemli:** Bu bir *iç* incelemedir (geliştirme sırasında yapıldı). Bağımsız bir güvenlik firmasının denetiminin yerine geçmez;
geniş dağıtımdan önce dış denetim önerilir.

## Tehdit modeli
| Saldırgan | Hedef | Kapsam |
|---|---|---|
| Kötü niyetli web sitesi | Kasadaki parolaları almak | Kapsamda |
| Taklit (oltalama) sitesi | Kullanıcının parolasını girdirmek | Kapsamda |
| Ağdaki saldırgan (aynı Wi-Fi) | http sayfaya sahte form ekleyip otomatik doldurmayı tetiklemek | Kapsamda |
| Bilgisayarı ele geçirilen kullanıcı / zorla açtırma | Kasayı görmek | Kısmen (Baskı Parolası) |
| Aynı kullanıcı hesabında çalışan kötü amaçlı yazılım | Her şey | **Kapsam dışı** — bu durumda hiçbir parola yöneticisi tam koruma sağlayamaz |

## Bulgular ve düzeltmeler (6.10.2)
| # | Bulgu | Önem | Durum |
|---|---|---|---|
| 1 | Hızlı Doldur, hedef pencere öne gelmezse tuşları o an öndeki pencereye yazabiliyordu (gerçek bilgisayarda gözlendi) | Yüksek | **Düzeltildi**: pencere doğrulanmadan tek tuş gönderilmez; yazarken odak değişirse durur |
| 2 | Paylaşımlı barındırma alan adları (github.io, herokuapp.com, vercel.app…) tek alan adı sayılıyordu: `saldirgan.github.io` sayfası `ayse.github.io` kaydını alabilirdi | Yüksek | **Düzeltildi**: 30 yaygın paylaşımlı son ek ayrı sahip sayılır |
| 3 | https kaydı, aynı sitenin http sürümüne de dolduruluyordu (ağ saldırganı sahte form ekleyebilir) | Orta | **Düzeltildi**: https kaydı şifresiz sayfaya verilmez |
| 4 | Yerel yardımcı eşleştirme kodunu iletmiyordu; eklenti ile uygulamada farklı kod görünebiliyordu | Orta | **Düzeltildi** ve uçtan uca testle doğrulandı |
| 5 | Eşleştirme isteği tekrar tekrar gönderilip kullanıcı onay penceresiyle bıktırılabilirdi | Düşük | **Düzeltildi**: tek bekleyen istek, reddedilince 30 sn kilit |
| 6 | Eklenti simgesi `web_accessible_resources` ile açıktı; siteler eklentinin kurulu olduğunu algılayabilirdi | Düşük | **Düzeltildi**: simge betiğe gömüldü |
| 7 | Eklenti menüsü sentetik (betikle üretilmiş) tıklamalara da tepki verebilirdi | Düşük | **Düzeltildi**: yalnızca `isTrusted` kullanıcı tıklaması |
| 8 | Kopyalanan parolalar Windows Pano Geçmişi'ne (Win+V) ve bulut panosuna düşebiliyordu | Orta | **Düzeltildi**: Windows'ta geçmiş/bulut/izleyici dışlama biçimleriyle yazılır |
| 9 | Güvenlik puanı yeni kurulumda 100 (Mithril) gösteriyordu | Düşük | **Düzeltildi**: kimlik, parola kasası, kasa sağlığı puana katıldı |

## Bilinen ve kabul edilen riskler
- Ana parola, kasa açıkken bellekte tutulur (Python dizesi; tam silinemez). Kilit, panik ve otomatik kilit kasayı kapatır.
- Aynı Windows kullanıcısında çalışan kötü amaçlı yazılım `instance.json` belirtecini, eklentinin eşleşme anahtarını ve tuş vuruşlarını okuyabilir. Bu, tüm parola yöneticileri için geçerlidir.
- Baskı Parolası'nın sahte kasası bilgisayarda ayrı bir dosyadır; bilgisayarı inceleyen biri varlığını görebilir.
- Domino ve oltalama tespiti sezgiseldir; her taklit alan adını yakalaması garanti değildir.
- Eklenti, Web Mağazası dışından yüklendiği için tarayıcı “geliştirici modu” uyarısı gösterebilir.

## Doğrulama
- Birim testleri: `tests/test_browser_bridge.py`, `tests/test_passwords.py` (eşleştirme, birebir alan adı, paylaşımlı barındırma, sürüm düşürme, oltalama, kilitli kasa, Shamir, baskı parolası).
- Uçtan uca: `tools/e2e/` — gerçek Chromium + eklenti + yerel yardımcı + uygulama: https doldurur, http'ye vermez, taklit sitede uyarır.
- Gerçek Windows: Hızlı Doldur, başka uygulama öndeyken bile yalnızca hedef pencereye yazdı (Türkçe karakterler ve € dahil).

## Öneri
Geniş dağıtımdan önce: Parola Kasası + tarayıcı köprüsü için bağımsız denetim (ör. Cure53, Trail of Bits, yerel bir sızma testi firması) ve
herkese açık bir güvenlik bildirim adresi (`security.txt`, sorumlu ifşa politikası).
