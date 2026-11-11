"""Gömülü veri ihlali kataloğunu yeniler: Have I Been Pwned /api/v3/breaches → studio_ui/data/hibp_breaches.json.gz

  python packaging/update_breaches.py [indirilmiş_breaches.json]
Veri: Have I Been Pwned (https://haveibeenpwned.com), CC BY 4.0. Yalnızca alan adı olan ihlaller ve eşleştirme için
gereken alanlar tutulur; açıklamalar ve logolar alınmaz.
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio_ui import breaches  # noqa: E402


def main(argv):
    if argv:
        raw = Path(argv[0]).read_bytes()
    else:
        req = urllib.request.Request(breaches.API_URL, headers={"User-Agent": breaches.USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310
            raw = r.read()
    cat = breaches.compact(json.loads(raw.decode("utf-8")))
    out = ROOT / "studio_ui" / "data" / breaches.BUNDLED_NAME
    out.write_bytes(gzip.compress(json.dumps(cat, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))
    print(f"{len(cat['items'])} ihlal · son eklenen {cat['latest']} · {out.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
