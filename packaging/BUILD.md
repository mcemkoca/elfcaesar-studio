# ElfCaesar Studio · Windows kurulum paketi

## Çıktı
`dist\ElfCaesarStudio-<sürüm>-Setup.exe` — standart Inno Setup sihirbazı (Türkçe / İngilizce).

| Özellik | Ayrıntı |
|---|---|
| Kurulum kipi | Varsayılan **yalnızca geçerli kullanıcı** (yönetici izni yok, `%LOCALAPPDATA%\Programs\ElfCaesar Studio`). İstenirse **tüm kullanıcılar** (`Program Files`, yönetici izni). |
| Sihirbaz sayfaları | Kurulum kipi · Hoş geldiniz · Lisans (MIT) · Önemli bilgiler · Konum · Ek işlemler · Kurulum · Bitti (uygulamayı başlat) |
| Kısayollar | Başlat menüsü: *ElfCaesar Studio* ve *ElfCaesar Mesaj Köprüsü*; isteğe bağlı masaüstü |
| Windows entegrasyonu | Gezgin sağ tık menüsü · `.elfvault .elfcontact .elfid .elmsg .elfdm` ilişkilendirmeleri · Win+R `ElfCaesarStudio` · isteğe bağlı Windows ile başlat |
| Uygulamalar listesi | Ad, sürüm, yayımcı, simge, boyut; *Değiştir/Kaldır* |
| Güncelleme | Aynı AppId ile yeni sürüm üzerine kurulur; açık uygulama algılanır ve kapatılır |
| Kaldırma | Tüm dosya, kısayol ve kayıt defteri girdilerini siler; ayarlar ve kişi defterini silmeyi sorar; `.elfid` / `.elfvault` dosyalarına dokunmaz |
| Uygulama | PyInstaller tek klasör, konsolsuz `ElfCaesarStudio.exe`, Python gerektirmez, sürüm bilgisi ve logo simgesi gömülü |

## Windows'ta derleme
```powershell
winget install Python.Python.3.12
winget install JRSoftware.InnoSetup
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```
İmzalı derleme: `packaging\build.ps1 -CertThumbprint <sertifika parmak izi>` (Windows SDK `signtool` gerekir).

## GitHub Actions
`.github/workflows/windows-installer.yml` — *Actions → Windows kurulum paketi → Run workflow* veya `v*` etiketi;
Setup.exe ve SHA-256 dosyası *artifact* olarak indirilebilir.

## Sessiz kurulum (BT yöneticileri için)
```
ElfCaesarStudio-6.8.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /CURRENTUSER /TASKS="desktopicon,contextmenu,fileassoc"
"%LOCALAPPDATA%\Programs\ElfCaesar Studio\unins000.exe" /VERYSILENT
```

## Sürüm numarası
Tek kaynak `studio_ui/version.py`. Uygulama, exe sürüm bilgisi ve kurulum dosyası adı buradan gelir.

## İmzasız paket uyarısı
Kod imzalama sertifikası olmadan Windows SmartScreen “Windows bilgisayarınızı korudu / Bilinmeyen yayımcı” gösterir
(*Ek bilgi → Yine de çalıştır*). Dağıtımdan önce bir kod imzalama sertifikası (OV/EV) önerilir.
