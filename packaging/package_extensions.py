"""Tarayıcı eklentisi paketleri: Chromium (kurulum klasörü + Chrome Web Mağazası zip) ve Firefox (.xpi + klasör).

  python packaging/package_extensions.py <çıktı klasörü>
Chrome Web Mağazası paketi `key` alanı içermez (mağaza kendi kimliğini atar; yayınlandıktan sonra o kimlik
com.dante.elfcaesar.json → allowed_origins'e eklenmelidir).
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "browser-extension"
FIREFOX_ID = "elfcaesar@dante.studio"
FILES = ["background.js", "content.js", "popup.html", "popup.js", "icons"]


def _copy(dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        s = SRC / f
        (shutil.copytree(s, dst / f, dirs_exist_ok=True) if s.is_dir() else shutil.copy2(s, dst / f))


def _zip(folder: Path, out: Path):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(folder).as_posix())


def build(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    man = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    ver = man["version"]
    # Chrome Web Mağazası
    store = out / "_chrome_store"
    _copy(store)
    sm = {k: v for k, v in man.items() if k != "key"}
    (store / "manifest.json").write_text(json.dumps(sm, ensure_ascii=False, indent=2), encoding="utf-8")
    store_zip = out / f"ElfCaesar-Chrome-WebStore-{ver}.zip"
    _zip(store, store_zip)
    shutil.rmtree(store)
    # Firefox (MV3: arka plan betiği, gecko kimliği)
    ff = out / "Firefox"
    _copy(ff)
    fm = {k: v for k, v in man.items() if k != "key"}
    fm["background"] = {"scripts": ["background.js"]}
    fm["browser_specific_settings"] = {"gecko": {"id": FIREFOX_ID, "strict_min_version": "128.0"}}
    (ff / "manifest.json").write_text(json.dumps(fm, ensure_ascii=False, indent=2), encoding="utf-8")
    xpi = out / f"ElfCaesar-Firefox-{ver}.xpi"
    _zip(ff, xpi)
    host = json.loads((SRC / "com.dante.elfcaesar.json").read_text(encoding="utf-8"))
    fh = {k: v for k, v in host.items() if k != "allowed_origins"}
    fh["allowed_extensions"] = [FIREFOX_ID]
    (out / "com.dante.elfcaesar.firefox.json").write_text(json.dumps(fh, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"store": store_zip, "xpi": xpi, "firefox_dir": ff}


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
