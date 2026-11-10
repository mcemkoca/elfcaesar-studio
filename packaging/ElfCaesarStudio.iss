; ElfCaesar Studio · Windows kurulum betiği (Inno Setup 6.3+)
; Derleme:  ISCC.exe /DAppVersion=6.10.3 /DAppBuild=6103 packaging\ElfCaesarStudio.iss
; Önce PyInstaller çıktısı hazır olmalı: build\dist\ElfCaesarStudio\ElfCaesarStudio.exe

#ifndef AppVersion
  #define AppVersion "6.10.3"
#endif
#ifndef AppBuild
  #define AppBuild "6103"
#endif
#define AppName "ElfCaesar Studio"
#define AppExe "ElfCaesarStudio.exe"
#define Publisher "Dante"
#define SrcDir "..\build\dist\ElfCaesarStudio"

[Setup]
AppId={{A0B7D184-8B37-4E66-9A13-3EFC4E520026}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppCopyright=© 2026 {#Publisher} · MIT
AppComments=Bir Dante eseri · yerel ve çevrimdışı şifreleme, kimlik ve şifreli mesaj köprüsü
VersionInfoVersion={#AppVersion}.{#AppBuild}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Kurulum
VersionInfoCompany={#Publisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
; Varsayılan: yönetici izni gerektirmeyen kullanıcı kurulumu; istenirse tüm kullanıcılar için kurulabilir
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=ElfCaesarStudio-{#AppVersion}-Setup
SetupIconFile=..\assets\elfcaesar.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=art\wizard-100.bmp,art\wizard-125.bmp,art\wizard-150.bmp,art\wizard-175.bmp,art\wizard-200.bmp
WizardSmallImageFile=art\wizard-small-100.bmp,art\wizard-small-125.bmp,art\wizard-small-150.bmp,art\wizard-small-175.bmp,art\wizard-small-200.bmp
LicenseFile=..\LICENSE.txt
InfoBeforeFile=installer_info_tr.txt
Compression=lzma2/max
LZMAUseSeparateProcess=yes
SolidCompression=yes
; Kurulum/kaldırma sırasında açık uygulamayı algıla ve kapat
AppMutex=ElfCaesarStudio.SingleInstance
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes
ShowLanguageDialog=auto
; Kod imzalama (isteğe bağlı): build.ps1 -CertThumbprint <parmak izi> otomatik olarak /Selfsign=… ve /DSignSetup=1 verir.
#ifdef SignSetup
SignTool=elfsign
#endif

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
turkish.TaskBrowser=Tarayıcı eklentisi yardımcısını kaydet (Chrome, Edge, Brave, Opera, Vivaldi, Firefox)
english.TaskBrowser=Register the browser extension helper (Chrome, Edge, Brave, Opera, Vivaldi, Firefox)
turkish.TaskContext=Windows Gezgini sağ tık menüsüne “ElfCaesar ile şifrele / çöz” ekle
english.TaskContext=Add “Encrypt / Decrypt with ElfCaesar” to the Explorer context menu
turkish.TaskAssoc=.elfvault, .elfcontact, .elfid, .elmsg ve .elfdm dosyalarını ElfCaesar ile aç
english.TaskAssoc=Open .elfvault, .elfcontact, .elfid, .elmsg and .elfdm files with ElfCaesar
turkish.TaskStartup=Windows açılışında arka planda başlat (Mesaj Köprüsü kısayolları için)
english.TaskStartup=Start in the background with Windows (for Message Bridge hotkeys)
turkish.GroupIntegration=Windows entegrasyonu:
english.GroupIntegration=Windows integration:
turkish.BridgeShortcut=ElfCaesar Mesaj Köprüsü
english.BridgeShortcut=ElfCaesar Message Bridge
turkish.AskRemoveData=Ayarlar, kişi defteri ve hata günlükleri de silinsin mi?%n%nKimlik (.elfid) ve kasa (.elfvault) dosyalarınıza dokunulmaz.
english.AskRemoveData=Also remove settings, the contact book and error logs?%n%nYour identity (.elfid) and vault (.elfvault) files are not touched.
turkish.VaultType=ElfCaesar Şifreli Kasa
english.VaultType=ElfCaesar Encrypted Vault
turkish.ContactType=ElfCaesar Kişi Kartı
english.ContactType=ElfCaesar Contact Card
turkish.IdentityType=ElfCaesar Özel Kimlik
english.IdentityType=ElfCaesar Private Identity
turkish.MessageType=ElfCaesar Şifreli Mesaj
english.MessageType=ElfCaesar Encrypted Message

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "contextmenu"; Description: "{cm:TaskContext}"; GroupDescription: "{cm:GroupIntegration}"
Name: "fileassoc"; Description: "{cm:TaskAssoc}"; GroupDescription: "{cm:GroupIntegration}"
Name: "browser"; Description: "{cm:TaskBrowser}"; GroupDescription: "{cm:GroupIntegration}"
Name: "startup"; Description: "{cm:TaskStartup}"; GroupDescription: "{cm:GroupIntegration}"; Flags: unchecked

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Yerel şifreleme ve şifreli mesaj"
Name: "{autoprograms}\{cm:BridgeShortcut}"; Filename: "{app}\{#AppExe}"; Parameters: "--action bridge"
Name: "{autoprograms}\ElfCaesar Studio Kılavuzu"; Filename: "{app}\_internal\docs\kilavuz\index.html"; Comment: "Bölüm bölüm resimli kullanım kılavuzu"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Win+R → ElfCaesarStudio
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExe}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe}"; Flags: uninsdeletekey
; Gezgin sağ tık menüsü (uygulama içindeki anahtarla aynı anahtarlar: Mesaj Köprüsü > Entegrasyonlar)
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Encrypt"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar ile şifrele"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Encrypt"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Encrypt\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action encrypt-file ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar ile çöz"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action decrypt-file ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar kişi defterine ekle"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action add-contact ""%1"""; Tasks: contextmenu
; 6.10.3 Araç Kutusu: klasör kilitle, dosya imzala, imza doğrula
Root: HKCU; Subkey: "Software\Classes\Directory\shell\ElfCaesar.LockFolder"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar ile klasörü kilitle"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\ElfCaesar.LockFolder"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Directory\shell\ElfCaesar.LockFolder\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action lock-folder ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Sign"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar ile imzala"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Sign"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Sign\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action sign-file ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfsig\shell\ElfCaesar.Verify"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar ile imzayı doğrula"; Tasks: contextmenu; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfsig\shell\ElfCaesar.Verify"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#AppExe}"",0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfsig\shell\ElfCaesar.Verify\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action verify-sig ""%1"""; Tasks: contextmenu
Root: HKA; Subkey: "Software\Classes\.elfsig\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Signature"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Signature"; ValueType: string; ValueName: ""; ValueData: "ElfCaesar dijital imza"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Signature\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Signature\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action verify-sig ""%1"""; Tasks: fileassoc
; Uygulama içinden eklenmiş olsa bile kaldırırken temizle
Root: HKCU; Subkey: "Software\Classes\*\shell\ElfCaesar.Encrypt"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt"; Flags: uninsdeletekey dontcreatekey
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact"; Flags: uninsdeletekey dontcreatekey
; Dosya ilişkilendirmeleri
Root: HKA; Subkey: "Software\Classes\.elfvault\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Vault"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Vault"; ValueType: string; ValueName: ""; ValueData: "{cm:VaultType}"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Vault\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Vault\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action decrypt-file ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.elfcontact\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Contact"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Contact"; ValueType: string; ValueName: ""; ValueData: "{cm:ContactType}"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Contact\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Contact\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action add-contact ""%1"""; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.elfid\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Identity"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Identity"; ValueType: string; ValueName: ""; ValueData: "{cm:IdentityType}"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Identity\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Identity\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action bridge"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\.elmsg\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Message"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.elfdm\OpenWithProgids"; ValueType: string; ValueName: "ElfCaesar.Message"; ValueData: ""; Tasks: fileassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Message"; ValueType: string; ValueName: ""; ValueData: "{cm:MessageType}"; Tasks: fileassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Message\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"",0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\ElfCaesar.Message\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" --action open-message ""%1"""; Tasks: fileassoc
; Tarayıcı eklentisi yardımcısı (native messaging)
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.json"; Tasks: browser; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Chromium\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.json"; Tasks: browser; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.json"; Tasks: browser; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.json"; Tasks: browser; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Vivaldi\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.json"; Tasks: browser; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\com.dante.elfcaesar"; ValueType: string; ValueName: ""; ValueData: "{app}\com.dante.elfcaesar.firefox.json"; Tasks: browser; Flags: uninsdeletekey
; Windows ile başlat (arka planda, kısayollar hazır)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ElfCaesar Studio"; ValueData: """{app}\{#AppExe}"" --action background"; Tasks: startup; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "ElfCaesar Studio"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{localappdata}\ElfCaesar\instance.json"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent()) then
  begin
    if MsgBox(CustomMessage('AskRemoveData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\ElfCaesar'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\ElfCaesar'), True, True, True);
    end;
  end;
end;
