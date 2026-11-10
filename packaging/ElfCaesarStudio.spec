# -*- mode: python ; coding: utf-8 -*-
# PyInstaller tanımı · tek klasör (onedir), konsolsuz Windows uygulaması.
# Çalıştırma:  pyinstaller --noconfirm --clean packaging/ElfCaesarStudio.spec
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = [(str(ROOT / "assets"), "assets"), (str(ROOT / "docs" / "kilavuz"), "docs/kilavuz"), (str(ROOT / "docs" / "yasal"), "docs/yasal"), (str(ROOT / "studio_ui" / "data"), "studio_ui/data"),
         (str(ROOT / "LICENSE.txt"), "."), (str(ROOT / "THIRD_PARTY_NOTICES.txt"), ".")]

a = Analysis(
    [str(ROOT / "gui.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["tkinterdnd2"],  # isteğe bağlı sürükle-bırak; kendi PyInstaller kancası tkdnd'yi ekler
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "PIL", "numpy", "unittest", "pydoc_data", "test", "lib2to3"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ElfCaesarStudio",
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "elfcaesar.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
    upx=False,
)
# Tarayıcı yardımcısı (native messaging host): konsollu küçük exe, tarayıcı gizli başlatır
h = Analysis([str(ROOT / "native_host.py")], pathex=[str(ROOT)], binaries=[], datas=[], hiddenimports=[], hookspath=[],
             runtime_hooks=[], excludes=["tkinter", "_tkinter", "cryptography", "pytest", "PIL", "numpy", "unittest", "test"],
             noarchive=False, optimize=1)
hpyz = PYZ(h.pure)
hexe = EXE(hpyz, h.scripts, [], exclude_binaries=True, name="ElfCaesarNativeHost", console=True,
           icon=str(ROOT / "assets" / "elfcaesar.ico"), version=str(ROOT / "build" / "version_info.txt"), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, hexe, h.binaries, h.datas, strip=False, upx=False, name="ElfCaesarStudio")
