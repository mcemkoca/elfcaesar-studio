"""Parola Kasası: kayıtlar, şifreli saklama ve tarayıcı/yönetici içe aktarma.

Kasa dosyası değişmeyen motorla mühürlenir (AES-256-GCM + scrypt, kind="bundle").
Ana parola diske yazılmaz; açık kasa yalnızca bellekte tutulur.
Tarayıcı içe aktarma: tarayıcının kendi "Parolaları dışa aktar" CSV dosyası (Chrome, Edge, Brave, Opera,
Vivaldi, Firefox) ve Bitwarden / KeePass / 1Password / LastPass CSV'leri. Tarayıcının şifreli veritabanı
doğrudan okunmaz: bu, kötü amaçlı yazılımların kullandığı yöntemdir ve modern tarayıcılar engeller.
"""
from __future__ import annotations

import csv
import io
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from elfcaesar.secure import SecureFormatError, _atomic_write, open_bytes, seal_bytes

FORMAT = "ELFPASS1"
CONTENT_TYPE = "application/vnd.elfcaesar.passwords+json"


def default_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) / "ElfCaesar" if base else Path.home() / ".elfcaesar"
    return root / "parola-kasasi.elfvault"


@dataclass
class Entry:
    title: str
    username: str = ""
    password: str = ""
    url: str = ""
    notes: str = ""
    tags: list = field(default_factory=list)
    id: str = field(default_factory=lambda: secrets.token_hex(8))
    created: float = field(default_factory=time.time)
    changed: float = field(default_factory=time.time)  # parolanın son değiştiği an
    used: float = 0.0
    history: list = field(default_factory=list)  # [{"password", "until"}]
    recovery_email: str = ""  # hesabın kurtarma e-postası (domino analizi için)
    source: str = ""
    modified: float = field(default_factory=time.time)  # herhangi bir alanın son değiştiği an (senkron birleştirme)

    @property
    def domain(self) -> str:
        return registrable_domain(self.url) if self.url else ""

    def set_password(self, pw: str):
        if pw != self.password:
            if self.password:
                self.history = ([{"password": self.password, "until": time.time()}] + self.history)[:10]
            self.password = pw
            self.changed = time.time()
            self.modified = self.changed

    def matches(self, q: str) -> bool:
        q = q.casefold().strip()
        return not q or any(q in (v or "").casefold() for v in (self.title, self.username, self.url, self.notes, " ".join(self.tags)))


_TWO_LEVEL = {"com.tr", "org.tr", "net.tr", "gov.tr", "edu.tr", "k12.tr", "bel.tr", "gen.tr", "web.tr", "av.tr",
              "co.uk", "org.uk", "ac.uk", "com.au", "co.jp", "com.br", "co.in", "co.kr", "com.cn", "com.mx", "co.nz"}
# Herkesin alt alan adı açabildiği barındırma servisleri (Public Suffix List "private" bölümünden seçki):
# a.github.io ile b.github.io FARKLI sahiplerdir; aynı alan adı sayılmamalı.
_SHARED_HOSTING = {"github.io", "gitlab.io", "blogspot.com", "wordpress.com", "herokuapp.com", "netlify.app", "vercel.app",
                   "pages.dev", "workers.dev", "web.app", "firebaseapp.com", "appspot.com", "azurewebsites.net",
                   "cloudfront.net", "s3.amazonaws.com", "glitch.me", "repl.co", "replit.app", "onrender.com",
                   "fly.dev", "surge.sh", "neocities.org", "wixsite.com", "weebly.com", "tumblr.com", "myshopify.com",
                   "ngrok.io", "ngrok-free.app", "000webhostapp.com", "blogspot.com.tr", "sites.google.com"}


def host_of(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    try:
        return (urlparse(url).hostname or "").lower().strip(".")
    except ValueError:
        return ""


def registrable_domain(url_or_host: str) -> str:
    host = host_of(url_or_host) if ("/" in url_or_host or ":" in url_or_host or "." in url_or_host) else url_or_host
    host = host.removeprefix("www.")
    parts = host.split(".")
    for n in (3, 2):
        if len(parts) > n and ".".join(parts[-n:]) in _SHARED_HOSTING:
            return ".".join(parts[-(n + 1):])
    if len(parts) >= 3 and ".".join(parts[-2:]) in _TWO_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


class PasswordVault:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()
        self.entries: list[Entry] = []
        self._secret: str | None = None
        self.decoy = False
        self.meta = {"created": time.time()}
        self._disk_sig = None  # açıldığı andaki dosya özeti (başka cihaz değiştirdi mi?)
        self.last_merge = None

    # ------------------------------------------------------------ yaşam döngüsü
    @property
    def is_open(self) -> bool:
        return self._secret is not None

    def exists(self) -> bool:
        return self.path.exists()

    def create(self, master: str):
        self._secret = master
        self.entries = []
        self.save()

    def unlock(self, master: str, decoy_path: Path | None = None) -> bool:
        """Ana parola veya (varsa) baskı parolasıyla açar. Baskı kasası açıldıysa self.decoy=True olur."""
        try:
            self._load(self.path, master)
            self.decoy = False
            return True
        except SecureFormatError:
            if decoy_path and Path(decoy_path).exists():
                main_path = self.path
                try:
                    self.path = Path(decoy_path)
                    self._load(self.path, master)
                    self.decoy = True
                    return True
                except SecureFormatError:
                    self.path = main_path
            raise

    def _load(self, path: Path, master: str):
        clear, header = open_bytes(path.read_bytes(), master)
        if header.get("content_type") != CONTENT_TYPE:
            raise SecureFormatError("Bu dosya parola kasası değil.")
        data = json.loads(clear.decode("utf-8"))
        if data.get("format") != FORMAT:
            raise SecureFormatError("Desteklenmeyen parola kasası sürümü.")
        known = set(Entry.__dataclass_fields__)
        self.entries = [Entry(**{k: v for k, v in e.items() if k in known}) for e in data.get("entries", [])]
        for e in self.entries:
            e.modified = max(e.modified or 0, e.changed or 0)
        self.meta = data.get("meta", {})
        self._secret = master
        self._disk_sig = self._sig(path)

    def lock(self):
        self._secret = None
        self.entries = []
        self.decoy = False

    def to_bytes(self) -> bytes:
        return json.dumps({"format": FORMAT, "meta": self.meta, "entries": [asdict(e) for e in self.entries]},
                          ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def save(self):
        if self._secret is None:
            raise RuntimeError("Kasa kilitli")
        self.last_merge = None
        if self.path.exists() and self._disk_sig is not None and self._sig(self.path) != self._disk_sig:
            self.last_merge = self._merge_disk()  # bulut klasöründe başka cihaz değiştirmiş: kaybetmeden birleştir
        if self.path.exists():
            self._backup()
        data = self.to_bytes()
        sealed = seal_bytes(data, self._secret, kind="bundle", filename=self.path.name, content_type=CONTENT_TYPE)
        _atomic_write(self.path, sealed)
        self._disk_sig = self._sig(self.path)
        miras = self.meta.get("miras")
        if miras and not self.decoy:
            _atomic_write(self.miras_path, seal_bytes(data, miras["key"], kind="bundle", filename=self.miras_path.name,
                                                      content_type=CONTENT_TYPE))

    # ------------------------------------------------------------ yedekler ve senkron
    @staticmethod
    def _sig(path: Path):
        try:
            import hashlib
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError:
            return None

    @property
    def backup_dir(self) -> Path:
        return self.path.parent / "yedekler"

    def _backup(self, keep: int = 20, min_gap: float = 300):
        """Kaydetmeden önce mevcut (şifreli) dosyanın kopyası. 5 dk içinde tek yedek, son 20 yedek tutulur."""
        if self.decoy:
            return
        d = self.backup_dir
        try:
            d.mkdir(parents=True, exist_ok=True)
            olds = self.list_backups()
            if olds and time.time() - olds[0].stat().st_mtime < min_gap:
                return
            target = d / f"{self.path.stem}-{time.strftime('%Y%m%d-%H%M%S')}-{int(time.time() * 1000) % 1000:03d}.elfvault"
            n = 1
            while target.exists():
                target = target.with_name(f"{target.stem}-{n}.elfvault")
                n += 1
            target.write_bytes(self.path.read_bytes())
            for old in self.list_backups()[keep:]:
                old.unlink()
        except OSError:
            pass

    def list_backups(self) -> list[Path]:
        d = self.backup_dir
        if not d.exists():
            return []
        return sorted(d.glob(f"{self.path.stem}-*.elfvault"), key=lambda p: p.stat().st_mtime, reverse=True)

    def restore_backup(self, backup: Path, master: str) -> int:
        """Yedeği açar (parolası farklıysa hata), mevcut kasayı onunla değiştirir. Mevcut sürüm de yedeklenir."""
        tmp = PasswordVault(Path(backup))
        tmp._load(Path(backup), master)
        if self.path.exists():
            self._backup(min_gap=0)
        self.entries, self.meta = tmp.entries, tmp.meta
        self._secret = master
        self._disk_sig = None
        sealed = seal_bytes(self.to_bytes(), master, kind="bundle", filename=self.path.name, content_type=CONTENT_TYPE)
        _atomic_write(self.path, sealed)
        self._disk_sig = self._sig(self.path)
        return len(self.entries)

    def merge_entries(self, other_entries, other_meta=None) -> dict:
        """İki kasa sürümünü kayıt kimliğine göre birleştirir: en son değişen kazanır, silinenler (mezar taşı) silinir."""
        tomb = dict(self.meta.get("deleted", {}))
        for k, v in ((other_meta or {}).get("deleted", {}) or {}).items():
            tomb[k] = max(tomb.get(k, 0), v)
        mine = {e.id: e for e in self.entries}
        added = updated = removed = 0
        for o in other_entries:
            m = mine.get(o.id)
            if m is None:
                mine[o.id] = o
                added += 1
            elif (o.modified or 0) > (m.modified or 0):
                hist = {h["password"]: h for h in (m.history + o.history)}
                if m.password != o.password and m.password:
                    hist.setdefault(m.password, {"password": m.password, "until": time.time()})
                o.history = sorted(hist.values(), key=lambda h: -h.get("until", 0))[:10]
                o.history = [h for h in o.history if h["password"] != o.password]
                mine[o.id] = o
                updated += 1
        for eid, t in tomb.items():
            e = mine.get(eid)
            if e is not None and t >= (e.modified or 0):
                del mine[eid]
                removed += 1
        self.entries = list(mine.values())
        self.meta["deleted"] = {k: v for k, v in tomb.items() if time.time() - v < 400 * 86400}
        return {"added": added, "updated": updated, "removed": removed}

    def _merge_disk(self) -> dict | None:
        try:
            other = PasswordVault(self.path)
            other._load(self.path, self._secret)
        except SecureFormatError:
            # diskteki sürüm başka parolayla: üzerine yazmak yerine çakışma kopyası olarak sakla
            self.path.replace(self.path.with_name(f"{self.path.stem}-cakisma-{time.strftime('%Y%m%d-%H%M%S')}.elfvault"))
            return {"conflict_copy": True}
        return self.merge_entries(other.entries, other.meta)

    def conflict_files(self) -> list[Path]:
        """Bulut eşitleme servislerinin oluşturduğu çakışma kopyaları (ör. 'parola-kasasi-DESKTOP-1.elfvault')."""
        out = []
        for p in self.path.parent.glob(f"{self.path.stem}*.elfvault"):
            if p == self.path or p.name.endswith(".miras.elfvault") or ".yedek." in p.name:
                continue
            out.append(p)
        return sorted(out)

    def merge_file(self, path: Path, master: str | None = None) -> dict:
        other = PasswordVault(Path(path))
        other._load(Path(path), master or self._secret)
        res = self.merge_entries(other.entries, other.meta)
        self.save()
        return res

    # ------------------------------------------------------------ Dijital Miras (Shamir)
    @property
    def miras_path(self) -> Path:
        return self.path.with_name(self.path.stem + ".miras.elfvault")

    def setup_miras(self, k: int, n: int, heirs: list[str] | None = None) -> list[str]:
        """Rastgele 256 bit kurtarma anahtarı üretir, k-of-n parçalara böler, miras kasasını yazar."""
        from . import shamir
        key = secrets.token_bytes(32)
        self.meta["miras"] = {"key": key.hex(), "k": k, "n": n, "date": time.strftime("%d.%m.%Y"),
                              "heirs": (heirs or [])[:n]}
        self.save()
        return shamir.split_text(key, k, n)

    def disable_miras(self):
        self.meta.pop("miras", None)
        self.save()
        try:
            self.miras_path.unlink()
        except OSError:
            pass

    @staticmethod
    def recover_miras(miras_file: Path, share_texts: list[str]) -> list["Entry"]:
        from . import shamir
        key = shamir.combine_text(share_texts)
        tmp = PasswordVault(Path(miras_file))
        tmp._load(Path(miras_file), key.hex())
        entries = tmp.entries
        tmp.lock()
        return entries

    def change_master(self, new_master: str):
        self._secret = new_master
        self.save()

    def check_master(self, master: str) -> bool:
        return self._secret is not None and secrets.compare_digest(master.encode(), self._secret.encode())

    # ------------------------------------------------------------ kayıtlar
    def add(self, entry: Entry) -> Entry:
        self.entries.append(entry)
        return entry

    def get(self, eid: str) -> Entry | None:
        return next((e for e in self.entries if e.id == eid), None)

    def remove(self, eid: str):
        self.entries = [e for e in self.entries if e.id != eid]
        self.meta.setdefault("deleted", {})[eid] = time.time()

    def search(self, q: str) -> list[Entry]:
        return sorted((e for e in self.entries if e.matches(q)), key=lambda e: (-e.used, e.title.casefold()))

    def for_window(self, window_title: str) -> list[Entry]:
        """Ön plandaki pencere başlığına (ör. 'Gmail - Google Chrome') uyan kayıtlar."""
        t = (window_title or "").casefold()
        import re as _re
        t = _re.sub(r"\s[-\u2013\u2014]\s(google chrome|mozilla firefox|microsoft edge|brave|opera|vivaldi|yandex|chromium)\s*$", "", t)
        hits = []
        for e in self.entries:
            d = e.domain
            name = d.split(".")[0] if d else ""
            score = 0
            if d and d in t:
                score = 3
            elif name and len(name) >= 3 and name in t:
                score = 2
            elif e.title and e.title.casefold() in t:
                score = 1
            if score:
                hits.append((score, e))
        return [e for _s, e in sorted(hits, key=lambda x: (-x[0], -x[1].used))]

    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        """Otomatik tamamlama: başlık / alan adı / kullanıcı adı önerileri."""
        p = prefix.casefold().strip()
        if not p:
            return []
        seen, out = set(), []
        for e in sorted(self.entries, key=lambda e: -e.used):
            for v in (e.title, e.domain, e.username):
                if v and v.casefold().startswith(p) and v.casefold() not in seen:
                    seen.add(v.casefold())
                    out.append(v)
        return out[:limit]

    # ------------------------------------------------------------ içe aktarma
    def import_csv(self, text: str) -> dict:
        rows, source = parse_csv(text)
        added = updated = skipped = 0
        index = {(e.domain or e.title.casefold(), e.username.casefold()): e for e in self.entries}
        for r in rows:
            if not r["password"]:
                skipped += 1
                continue
            key = (registrable_domain(r["url"]) if r["url"] else r["title"].casefold(), r["username"].casefold())
            ex = index.get(key)
            if ex:
                if ex.password != r["password"]:
                    ex.set_password(r["password"])
                    updated += 1
                else:
                    skipped += 1
                continue
            e = Entry(title=r["title"] or registrable_domain(r["url"]) or "Kayıt", username=r["username"],
                      password=r["password"], url=r["url"], notes=r["notes"], source=source)
            if r.get("changed"):
                e.changed = r["changed"]
            self.add(e)
            index[key] = e
            added += 1
        return {"source": source, "added": added, "updated": updated, "skipped": skipped, "rows": len(rows)}


# ------------------------------------------------------------------ CSV biçimleri
def _pick(row: dict, *names) -> str:
    low = {k.strip().casefold(): (v or "") for k, v in row.items() if k}
    for n in names:
        if n in low and low[n]:
            return low[n].strip()
    return ""


def parse_csv(text: str) -> tuple[list[dict], str]:
    text = text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text))
    fields = {(f or "").strip().casefold() for f in (reader.fieldnames or [])}
    if "login_password" in fields:
        source = "Bitwarden"
    elif {"httprealm", "formactionorigin"} & fields:
        source = "Firefox"
    elif "login name" in fields or "web site" in fields:
        source = "KeePass"
    elif {"name", "url", "username", "password"} <= fields:
        source = "Chrome / Edge / Brave / Opera"
    elif "extra" in fields and "grouping" in fields:
        source = "LastPass"
    else:
        source = "CSV"
    rows = []
    for row in reader:
        url = _pick(row, "url", "login_uri", "web site", "website", "origin_url")
        title = _pick(row, "name", "title", "account") or registrable_domain(url)
        changed = _pick(row, "timepasswordchanged")
        rows.append({
            "title": title, "url": url,
            "username": _pick(row, "username", "login_username", "login name", "user name", "email"),
            "password": _pick(row, "password", "login_password"),
            "notes": _pick(row, "note", "notes", "comments", "extra"),
            "changed": (int(changed) / 1000 if changed.isdigit() else None),
        })
    if not reader.fieldnames or not any(r["password"] for r in rows) and rows:
        if not reader.fieldnames:
            raise ValueError("CSV başlık satırı bulunamadı.")
    return rows, source


BROWSER_EXPORT_STEPS = {
    "Google Chrome": "chrome://password-manager/settings → Parolaları dışa aktar → Dosyayı indir",
    "Microsoft Edge": "edge://wallet/passwords → ⋯ → Parolaları dışa aktar",
    "Brave": "brave://password-manager/settings → Parolaları dışa aktar",
    "Opera": "opera://password-manager/settings → Parolaları dışa aktar",
    "Mozilla Firefox": "about:logins → ⋯ (sağ üst) → Girişleri dışa aktar…",
    "Bitwarden": "Araçlar → Kasayı dışa aktar → .csv",
    "KeePass": "Dosya → Dışa aktar → KeePass CSV (1.x)",
}


# ------------------------------------------------------------------ kişiye şifreli paylaşım
SHARE_MARK = "ELFPASS-SHARE1"


def share_payload(e: Entry, note: str = "") -> str:
    body = {"title": e.title, "username": e.username, "password": e.password, "url": e.url, "notes": e.notes,
            "note": note[:200], "sent": time.strftime("%d.%m.%Y %H:%M")}
    return SHARE_MARK + "\n" + json.dumps(body, ensure_ascii=False)


def parse_share(text: str) -> tuple[Entry, str] | None:
    if not (text or "").startswith(SHARE_MARK + "\n"):
        return None
    d = json.loads(text.split("\n", 1)[1])
    return Entry(title=d.get("title") or "Paylaşılan kayıt", username=d.get("username", ""), password=d.get("password", ""),
                 url=d.get("url", ""), notes=d.get("notes", ""), source="Paylaşım"), d.get("note", "")
