"""Kişi defteri: yalnızca AÇIK kişi kartlarını (genel anahtarlar) saklar. Özel anahtar asla buraya yazılmaz."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .chatarmor import safety_words, fingerprint_of
from .settings import settings_path

SECRET_FIELDS = ("x25519_private", "ed25519_private")


def book_path() -> Path:
    return settings_path().with_name("contacts.json")


class ContactBook:
    def __init__(self, path: Path | None = None, validator=None):
        self.path = path or book_path()
        self.validator = validator  # identity.validate_contact (motor) — kriptografik denetim
        self.entries: dict[str, dict] = {}
        self.load()

    def load(self):
        self.entries = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for item in raw.get("contacts", []):
                card = item.get("card", {})
                if any(k in card for k in SECRET_FIELDS):
                    continue
                try:
                    self._check(card)
                except Exception:
                    continue
                self.entries[card["fingerprint"]] = {
                    "card": card, "alias": str(item.get("alias") or card.get("name", ""))[:60],
                    "verified": bool(item.get("verified")), "added": float(item.get("added") or time.time()),
                    "last_seen": item.get("last_seen")}
        except (OSError, ValueError, AttributeError):
            pass

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data = {"format": "ELFCONTACTBOOK1", "contacts": list(self.entries.values())}
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    def _check(self, card: dict) -> dict:
        if any(k in card for k in SECRET_FIELDS):
            raise ValueError("Kişi defterine özel anahtar eklenemez.")
        if self.validator:
            return self.validator(card)
        import base64
        x, e = base64.b64decode(card["x25519_public"]), base64.b64decode(card["ed25519_public"])
        if fingerprint_of(x, e) != card.get("fingerprint"):
            raise ValueError("Kişi kartı parmak izi geçersiz.")
        return card

    def add(self, card: dict, alias: str | None = None, verified: bool = False) -> tuple[dict, bool]:
        public = {k: card[k] for k in ("format", "version", "name", "x25519_public", "ed25519_public", "fingerprint") if k in card}
        self._check(public)
        fp = public["fingerprint"]
        is_new = fp not in self.entries
        entry = self.entries.get(fp) or {"card": public, "alias": (alias or public.get("name") or "Kişi")[:60],
                                         "verified": False, "added": time.time(), "last_seen": None}
        if alias:
            entry["alias"] = alias[:60]
        entry["verified"] = entry["verified"] or verified
        self.entries[fp] = entry
        self.save()
        return entry, is_new

    def remove(self, fp: str):
        self.entries.pop(fp, None)
        self.save()

    def set_verified(self, fp: str, value: bool = True):
        if fp in self.entries:
            self.entries[fp]["verified"] = value
            self.save()

    def touch(self, fp: str):
        if fp in self.entries:
            self.entries[fp]["last_seen"] = time.time()
            self.save()

    def get(self, fp: str) -> dict | None:
        return self.entries.get(fp)

    def sorted(self) -> list[dict]:
        return sorted(self.entries.values(), key=lambda e: (not e["verified"], e["alias"].casefold()))

    def words(self, fp: str) -> list[str]:
        return safety_words(fp)

    def stats(self) -> tuple[int, int]:
        return len(self.entries), sum(1 for e in self.entries.values() if e["verified"])
