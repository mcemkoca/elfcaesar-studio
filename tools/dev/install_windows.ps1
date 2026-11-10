$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "ELFCAESAR STUDIO - Windows kurulum denetimi" -ForegroundColor Cyan
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "Python 3 bulunamadi. https://www.python.org/downloads/windows/ adresinden Python 3.11+ kurun; kurulumda Tcl/Tk ve Python Launcher secili olsun." -ForegroundColor Yellow
  Start-Process "https://www.python.org/downloads/windows/"
  exit 1
}
& py -3 -c "import tkinter; print('Tkinter OK')"
if ($LASTEXITCODE -ne 0) { throw "Python Tkinter bileşeni bulunamadı. Python kurulumunu Modify ile onarın." }
Write-Host "Güvenli kasa bağımlılığı kuruluyor..." -ForegroundColor Cyan
& py -3 -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Gerekli paketler kurulamadı. İnternet bağlantısını ve pip kurulumunu kontrol edin." }
Write-Host "İsteğe bağlı sürükle-bırak desteği kuruluyor (tkinterdnd2)..." -ForegroundColor Cyan
& py -3 -m pip install -r (Join-Path $root "requirements-optional.txt")
if ($LASTEXITCODE -ne 0) { Write-Host "Sürükle-bırak paketi kurulamadı; uygulama dosya seçme pencereleriyle normal çalışır." -ForegroundColor Yellow }
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "ElfCaesar Studio.lnk"
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcutPath)
$sc.TargetPath = "$env:WINDIR\System32\cmd.exe"
$sc.Arguments = "/c `"$root\run.bat`""
$sc.WorkingDirectory = $root
$icon = Join-Path $root "assets\elfcaesar.ico"
if (Test-Path $icon) { $sc.IconLocation = "$icon,0" } else { $sc.IconLocation = "$env:SystemRoot\System32\imageres.dll, -102" }
$sc.Save()
Write-Host "Kurulum tamamlandi. Masaustundeki ElfCaesar Studio kisayolunu acin." -ForegroundColor Green
Start-Process "$root\run.bat"
