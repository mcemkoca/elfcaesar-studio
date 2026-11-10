"""Kılavuz içeriği: her sayfanın bölümü var, kart başlıkları gerçek kartlarla eşleşiyor."""
import re
from pathlib import Path

from studio_ui import guides

ROOT = Path(__file__).resolve().parent.parent


def _pages():
    src = (ROOT / "gui.py").read_text(encoding="utf-8")
    return re.findall(r'^    \("(\w+)", "\w+", "', src, re.M)


def _card_titles():
    titles = set()
    for f in [ROOT / "gui.py", *(ROOT / "studio_ui").glob("*.py")]:
        titles |= set(re.findall(r'(?:self\._card|self\._add_identity_card)\([^,\n]+, "([^"]+)"', f.read_text(encoding="utf-8")))
    return titles


def test_every_page_has_chapter():
    pages = _pages()
    assert len(pages) >= 11
    for p in pages:
        c = guides.chapter(p)
        assert c and c["summary"] and c["steps"], p


def test_every_card_has_section():
    titles = _card_titles()
    covered = {t for c in guides.CHAPTERS for t in c["sections"]}
    assert titles - covered == set()


def test_text_and_keys_unique():
    keys = [c["key"] for c in guides.CHAPTERS]
    assert len(keys) == len(set(keys)) and keys[0] == "start"
    for k in keys:
        assert len(guides.as_text(k)) > 80
    assert "F1" in guides.as_text("shortcuts")
