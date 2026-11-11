"""Tek sürüm kaynağı: uygulama, PyInstaller sürüm bilgisi ve Inno Setup bu dosyadan beslenir.

Sürümleme: MAJOR.MINOR.PATCH (Semantic Versioning)
  PATCH (6.8.1 → 6.8.2): düzeltme ve küçük iyileştirme
  MINOR (6.8.x → 6.9.0): yeni özellik grubu, geriye dönük uyumlu
  MAJOR (6.x → 7.0.0): dosya biçimi veya motor değişikliği
"""
APP_NAME = "ElfCaesar Studio"
APP_VERSION = "6.11.0"
APP_BUILD = 6110  # Windows dosya sürümünün 4. hanesi: 6.11.0.6110
APP_SHORT_VERSION = APP_VERSION
APP_CODENAME = "Windows Edition"
PUBLISHER = "Dante"
AUTHOR = "Dante"
APP_ID = "{A0B7D184-8B37-4E66-9A13-3EFC4E520026}"
EXE_NAME = "ElfCaesarStudio"
MUTEX_NAME = "ElfCaesarStudio.SingleInstance"
APP_USER_MODEL_ID = "Dante.ElfCaesarStudio"
COPYRIGHT = "© 2026 Dante · ElfCaesar Studio · MIT Lisansı"
