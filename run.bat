@echo off
cd /d "%~dp0"
py -3 gui.py
if errorlevel 1 (
  echo.
  echo Uygulama baslatilamadi. README.md dosyasindaki Python kurulumunu kontrol edin.
  pause
)
