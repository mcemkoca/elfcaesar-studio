<#
.SYNOPSIS
  ElfCaesar Studio Windows kurulum paketini üretir (Setup.exe).

.DESCRIPTION
  1) Ayrı bir derleme ortamı (.venv-build) kurar   2) testleri çalıştırır
  3) PyInstaller ile build\dist\ElfCaesarStudio\ klasörünü üretir
  4) Inno Setup ile dist\ElfCaesarStudio-<sürüm>-Setup.exe dosyasını üretir
  5) İsteğe bağlı: kod imzalama ve SHA-256 özeti

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File packaging\build.ps1
  powershell -ExecutionPolicy Bypass -File packaging\build.ps1 -SkipTests -CertThumbprint ABCD...
#>
param(
  [switch]$SkipTests,
  [string]$Python = "py",
  [string]$PythonVersion = "-3.12",
  [string]$CertThumbprint = $env:ELFCAESAR_CERT_THUMBPRINT,
  [string]$ReleaseKey = $env:DANTE_RELEASE_KEY   # dante_release_ed25519.pem (parola: $env:DANTE_KEY_PASS)
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
function Step($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }

Step "Derleme ortamı (.venv-build)"
if (-not (Test-Path ".venv-build\Scripts\python.exe")) { & $Python $PythonVersion -m venv .venv-build }
$Py = Join-Path $Root ".venv-build\Scripts\python.exe"
& $Py -m pip install --upgrade pip | Out-Null
& $Py -m pip install -r requirements.txt -r requirements-optional.txt -r packaging\requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Bağımlılıklar kurulamadı." }

if (-not $SkipTests) {
  Step "Testler"
  & $Py -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw "Testler başarısız; paket üretilmedi." }
}

Step "Sürüm bilgisi"
$Version, $Build = (& $Py packaging\make_version_info.py).Trim().Split(" ")
Write-Host "Sürüm: $Version (yapı $Build) · Yapımcı: Dante"

Step "PyInstaller"
& $Py -m PyInstaller --noconfirm --clean --distpath build\dist --workpath build\work packaging\ElfCaesarStudio.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller başarısız." }

$SignTool = $null
if ($CertThumbprint) {
  $SignTool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
              Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
  if (-not $SignTool) { throw "signtool.exe bulunamadı (Windows SDK gerekli)." }
  Step "Uygulama imzalanıyor"
  & $SignTool sign /sha1 $CertThumbprint /fd sha256 /tr http://timestamp.digicert.com /td sha256 "build\dist\ElfCaesarStudio\ElfCaesarStudio.exe"
}

Step "Tarayıcı eklentisi"
Copy-Item browser-extension -Destination build\dist\ElfCaesarStudio\TarayiciEklentisi -Recurse -Force
Move-Item build\dist\ElfCaesarStudio\TarayiciEklentisi\com.dante.elfcaesar.json build\dist\ElfCaesarStudio\ -Force
& $Py packaging\package_extensions.py build\dist\ElfCaesarStudio\TarayiciEklentisi
Move-Item build\dist\ElfCaesarStudio\TarayiciEklentisi\com.dante.elfcaesar.firefox.json build\dist\ElfCaesarStudio\ -Force

if ($ReleaseKey) {
  Step "Dante sürüm manifesti"
  & $Py packaging\sign_release.py build\dist\ElfCaesarStudio $ReleaseKey
  if ($LASTEXITCODE -ne 0) { throw "Manifest imzalanamadı." }
}

Step "Inno Setup"
$Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6 bulunamadı. Kurmak için: winget install JRSoftware.InnoSetup" }
$IsccArgs = @("/DAppVersion=$Version", "/DAppBuild=$Build", "packaging\ElfCaesarStudio.iss")
if ($SignTool) {
  $IsccArgs = @("/Selfsign=`"$SignTool`" sign /sha1 $CertThumbprint /fd sha256 /tr http://timestamp.digicert.com /td sha256 `$f",
                "/DSignSetup=1") + $IsccArgs
}
& $Iscc @IsccArgs
if ($LASTEXITCODE -ne 0) { throw "Inno Setup derlemesi başarısız." }

$Setup = "dist\ElfCaesarStudio-$Version-Setup.exe"
$Hash = (Get-FileHash $Setup -Algorithm SHA256).Hash.ToLower()
"$Hash  $(Split-Path $Setup -Leaf)" | Set-Content "$Setup.sha256" -Encoding ascii
Step "Hazır"
Write-Host "$Setup`nSHA-256: $Hash" -ForegroundColor Green
