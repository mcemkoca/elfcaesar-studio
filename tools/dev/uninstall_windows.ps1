$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $desktop "ElfCaesar Studio.lnk"
if (Test-Path $link) { Remove-Item $link -Force }
Write-Host "Masaustu kisayolu kaldirildi. Program klasorunu silerek uygulamayi tamamen kaldirabilirsiniz."
# ElfCaesar Gezgin sağ tık menüsü (yalnızca geçerli kullanıcı)
foreach ($k in @("HKCU:\Software\Classes\*\shell\ElfCaesar.Encrypt",
                 "HKCU:\Software\Classes\SystemFileAssociations\.elfvault\shell\ElfCaesar.Decrypt",
                 "HKCU:\Software\Classes\SystemFileAssociations\.elfcontact\shell\ElfCaesar.AddContact")) {
  if (Test-Path -LiteralPath $k) { Remove-Item -LiteralPath $k -Recurse -Force }
}
Write-Host "Sağ tık menüsü öğeleri kaldırıldı (varsa). Kişi defteri ve ayarlar: %APPDATA%\ElfCaesar" -ForegroundColor Cyan
