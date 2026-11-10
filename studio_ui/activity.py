"""Oturum içi işlem geçmişi modeli.

Gizlilik: Yalnızca işlem adı, kategori, sonuç ve zaman tutulur. Metin içeriği,
parola, anahtar veya dosya içeriği asla kaydedilmez. Geçmiş diske yazılmaz.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable

CATEGORIES = {
    "codec": "Kodlama",
    "analysis": "Analiz",
    "vault": "Kasa",
    "identity": "Kimlik",
    "file": "Dosya",
    "system": "Sistem",
}
LEVELS = ("success", "info", "warning", "error")


@dataclass(frozen=True)
class Activity:
    timestamp: float
    category: str
    level: str
    title: str
    detail: str = ""

    @property
    def clock(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    @property
    def category_label(self) -> str:
        return CATEGORIES.get(self.category, self.category.title())


@dataclass
class ActivityLog:
    limit: int = 500
    _items: list[Activity] = field(default_factory=list)

    def add(self, category: str, level: str, title: str, detail: str = "",
            timestamp: float | None = None) -> Activity:
        if category not in CATEGORIES:
            category = "system"
        if level not in LEVELS:
            level = "info"
        item = Activity(time.time() if timestamp is None else timestamp,
                        category, level, title.strip()[:120], detail.strip()[:200])
        self._items.append(item)
        if len(self._items) > self.limit:
            del self._items[: len(self._items) - self.limit]
        return item

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def items(self) -> list[Activity]:
        return list(self._items)

    def recent(self, n: int = 5) -> list[Activity]:
        return list(reversed(self._items[-n:])) if n > 0 else []

    def filtered(self, category: str | None = None, query: str = "") -> list[Activity]:
        q = query.strip().casefold()
        out = []
        for item in reversed(self._items):
            if category and category != "all" and item.category != category:
                continue
            if q and q not in f"{item.title} {item.detail} {item.category_label}".casefold():
                continue
            out.append(item)
        return out

    def per_minute(self, minutes: int = 30, now: float | None = None) -> list[int]:
        """Son ``minutes`` dakikadaki işlem sayıları; en eski önce, en yeni sonda."""
        now = time.time() if now is None else now
        buckets = [0] * minutes
        for item in self._items:
            age = int((now - item.timestamp) // 60)
            if 0 <= age < minutes:
                buckets[minutes - 1 - age] += 1
        return buckets

    def by_category(self) -> dict[str, int]:
        counts = {key: 0 for key in CATEGORIES}
        for item in self._items:
            counts[item.category] = counts.get(item.category, 0) + 1
        return counts

    def success_rate(self) -> float | None:
        judged = [i for i in self._items if i.level in ("success", "error")]
        if not judged:
            return None
        return sum(1 for i in judged if i.level == "success") / len(judged)

    def export_lines(self, items: Iterable[Activity] | None = None) -> str:
        rows = items if items is not None else self._items
        return "\n".join(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(i.timestamp))}\t"
                         f"{i.category_label}\t{i.level.upper()}\t{i.title}\t{i.detail}" for i in rows)
