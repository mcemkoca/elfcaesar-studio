"""Sızıntı Merkezi — site veri ihlalleri kataloğu (Have I Been Pwned).

• Uygulamayla birlikte gelen katalog çevrim dışı çalışır (studio_ui/data/hibp_breaches.json.gz).
• İsteğe bağlı güncelleme TÜM kataloğu indirir; hangi sitelerde hesabın olduğu hiçbir yere gönderilmez.
• Eşleştirme: kaydın alan adı ↔ ihlalin alan adı (kayıt edilebilir alan adı düzeyinde).
  İhlal, parolanın son değiştiği tarihten SONRA kamuya duyurulduysa (veya olduysa) ve sızan veriler arasında
  parolalar varsa, parola "değiştirilmeli" sayılır. Parola duyurudan sonra değiştirildiyse güvende sayılır.
Veri: Have I Been Pwned — Creative Commons Attribution 4.0 (atıf zorunlu, arayüzde gösterilir).
"""
from __future__ import annotations

import datetime as _dt
import gzip
import json
import time
from pathlib import Path

from .pwvault import registrable_domain

API_URL = "https://haveibeenpwned.com/api/v3/breaches"
USER_AGENT = "ElfCaesarStudio (offline password manager; https://github.com/mcemkoca/elfcaesar-studio)"
ATTRIBUTION = "Veri: Have I Been Pwned (haveibeenpwned.com) · CC BY 4.0"
BUNDLED_NAME = "hibp_breaches.json.gz"
LOCAL_NAME = "hibp_breaches.json.gz"


def _ts(date_str: str) -> float:
    try:
        d = _dt.datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=_dt.timezone.utc)
        return d.timestamp()
    except (TypeError, ValueError):
        return 0.0


def compact(raw: list) -> dict:
    items = []
    for b in raw:
        dom = (b.get("Domain") or "").strip().lower()
        if not dom or b.get("IsFabricated") or b.get("IsSpamList"):
            continue
        items.append({"n": b.get("Name", ""), "t": b.get("Title", ""), "d": dom,
                      "bd": (b.get("BreachDate") or "")[:10], "ad": (b.get("AddedDate") or "")[:10],
                      "c": int(b.get("PwnCount") or 0), "pw": "Passwords" in (b.get("DataClasses") or []),
                      "v": bool(b.get("IsVerified")), "cl": [c for c in (b.get("DataClasses") or [])][:8]})
    latest = max((i["ad"] for i in items), default="")
    return {"format": "ELFBREACH1", "source": API_URL, "latest": latest, "fetched": time.strftime("%Y-%m-%d"),
            "items": items}


def _read(path: Path) -> dict | None:
    try:
        data = json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
        return data if data.get("format") == "ELFBREACH1" else None
    except (OSError, ValueError):
        return None


def _paths():
    from .runtime import local_data_dir, resource_dir
    bundled = [resource_dir() / "studio_ui" / "data" / BUNDLED_NAME, Path(__file__).resolve().parent / "data" / BUNDLED_NAME]
    return local_data_dir() / LOCAL_NAME, bundled


class Catalog:
    def __init__(self, data: dict | None = None):
        self.data = data or {"items": [], "latest": "", "fetched": ""}
        self.by_domain: dict[str, list] = {}
        for it in self.data["items"]:
            self.by_domain.setdefault(registrable_domain(it["d"]) or it["d"], []).append(it)

    @classmethod
    def load(cls) -> "Catalog":
        local, bundled = _paths()
        best = None
        for p in [local] + bundled:
            if p.exists():
                d = _read(p)
                if d and (best is None or d.get("latest", "") > best.get("latest", "")):
                    best = d
        return cls(best)

    @property
    def size(self) -> int:
        return len(self.data["items"])

    @property
    def latest(self) -> str:
        return self.data.get("latest", "")

    def for_domain(self, domain: str) -> list:
        return list(self.by_domain.get(registrable_domain(domain) or domain, []))

    def status(self, entry) -> dict | None:
        """Kayıt için ihlal durumu. None: bilinen ihlal yok."""
        hits = self.for_domain(entry.domain) if entry.domain else []
        if not hits:
            return None
        changed = entry.changed or entry.created or 0
        open_, safe = [], []
        for b in sorted(hits, key=lambda x: x["ad"], reverse=True):
            when = max(_ts(b["bd"]), _ts(b["ad"]))
            # parola duyurudan sonra değiştiyse güvende; ihlal parolaları içermiyorsa bilgi amaçlı
            (safe if changed > when or not b["pw"] else open_).append(b)
        acked = set(getattr(entry, "breach_ack", []) or [])
        open_ = [b for b in open_ if b["n"] not in acked]
        return {"open": open_, "safe": safe, "all": hits}


def refresh(fetch=None) -> dict:
    """Kataloğu çevrim içi yeniler (kullanıcı onayıyla çağrılır). fetch(url)->bytes test için verilebilir."""
    if fetch is None:
        import urllib.request

        def fetch(url):
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310
                return r.read()
    cat = compact(json.loads(fetch(API_URL).decode("utf-8")))
    if not cat["items"]:
        raise ValueError("Boş katalog")
    local, _ = _paths()
    tmp = local.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(json.dumps(cat, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
    tmp.replace(local)
    return cat


def fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} milyon".replace(".", ",")
    if n >= 1_000:
        return f"{n / 1_000:.0f} bin"
    return str(n)


def fmt_date(s: str) -> str:
    try:
        return _dt.datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return s or "?"
