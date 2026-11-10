"""Kılavuz sayfası üretici: studio_ui/guides.py → docs/kilavuz/index.html (+ img/).

  python packaging/build_guide.py <ekran_goruntuleri_klasoru> [--fragment cikti.html]
Uygulamayla birlikte gelen tam HTML ve (isteğe bağlı) yayın için gövde parçası üretir.
"""
from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio_ui import guides  # noqa: E402
from studio_ui.version import APP_VERSION  # noqa: E402

SHOT = {"home": "01_home", "encode": "02_encode", "decode": "03_decode", "analysis": "04_analysis", "vault": "05_vault",
        "bridge": "06_bridge", "security": "07_security_lab", "toolbox": "08_toolbox", "kvkk": "09_kvkk",
        "tengwar": "10_tengwar", "alphabet": "11_alphabet", "history": "12_history", "badges": "13_badges", "passwords": "14_passwords", "start": "90_guide_toolbox"}

E = html.escape

CSS = """
/* Düzen: solda yapışkan bölüm listesi, sağda tek sütun okuma alanı; telefonda liste üstte yatay kayar. */
:root {
  --bg: #f5f3ee; --panel: #ffffff; --ink: #18202b; --muted: #5b6878; --line: #dcd7cc;
  --accent: #a96a12; --accent-soft: #f3e3c6; --cyan: #0f7d8c;
  --display: "Space Grotesk", "Segoe UI", system-ui, sans-serif;
  --body: "Inter", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", Consolas, ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #070c13; --panel: #0f1a27; --ink: #e9f0f7; --muted: #8a9db1; --line: #22364b;
  --accent: #f4b65e; --accent-soft: #2a2213; --cyan: #62d9e8; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #070c13; --panel: #0f1a27; --ink: #e9f0f7; --muted: #8a9db1; --line: #22364b;
  --accent: #f4b65e; --accent-soft: #2a2213; --cyan: #62d9e8; color-scheme: dark }
* { box-sizing: border-box }
body { background: var(--bg); color: var(--ink); font: 16px/1.6 var(--body); margin: 0 }
.wrap { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 48px; max-width: 1240px; margin: 0 auto;
  padding-block: 40px 80px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)) }
nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; display: flex; flex-direction: column; gap: 2px }
nav.toc .brand { font: 700 13px/1.3 var(--mono); letter-spacing: .12em; color: var(--accent); margin-bottom: 14px }
nav.toc a { color: var(--muted); text-decoration: none; padding: 6px 10px; border-radius: 6px; font-size: 14px; display: flex; gap: 10px }
nav.toc a span { font: 12px/1.9 var(--mono); color: var(--line) }
nav.toc a:hover, nav.toc a:focus-visible { background: var(--accent-soft); color: var(--ink); outline: none }
main { min-width: 0 }
header.hero { display: flex; gap: 24px; align-items: center; padding-bottom: 32px; border-bottom: 1px solid var(--line); margin-bottom: 8px; flex-wrap: wrap }
header.hero img { width: 88px; height: 88px; border-radius: 20px }
header.hero .eyebrow { font: 700 12px var(--mono); letter-spacing: .14em; color: var(--accent) }
header.hero h1 { font: 700 clamp(30px, 4vw, 44px)/1.1 var(--display); margin: 6px 0 8px; text-wrap: balance }
header.hero p { margin: 0; color: var(--muted); max-width: 62ch }
.legend { display: flex; gap: 10px; align-items: center; margin-top: 14px; font-size: 14px; color: var(--muted); flex-wrap: wrap }
.i { display: inline-grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid var(--cyan);
  color: var(--cyan); font: 700 13px var(--display); flex: none }
video { width: 100%; border-radius: 12px; border: 1px solid var(--line); background: #000; margin-top: 28px; display: block }
section.ch { padding-top: 56px; scroll-margin-top: 16px }
.ch-head { display: flex; gap: 14px; align-items: baseline }
.ch-num { font: 700 14px var(--mono); color: var(--accent) }
.ch h2 { font: 700 30px/1.15 var(--display); margin: 0; text-wrap: balance }
.ch .summary { font-size: 17px; max-width: 65ch; margin: 12px 0 20px }
.shot { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; margin: 8px 0 24px; background: var(--panel) }
.shot img { display: block; width: 100%; height: auto }
h3 { font: 700 12px var(--mono); letter-spacing: .14em; color: var(--muted); margin: 26px 0 10px }
ol.steps { list-style: none; counter-reset: s; padding: 0; margin: 0; display: grid; gap: 10px; max-width: 70ch }
ol.steps li { counter-increment: s; display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 4px }
ol.steps li::before { content: counter(s, decimal-leading-zero); font: 700 13px/1.9 var(--mono); color: var(--accent) }
ul.tips { padding: 0; margin: 0; list-style: none; display: grid; gap: 8px; max-width: 70ch }
ul.tips li { padding: 10px 14px; background: var(--accent-soft); border-radius: 8px; font-size: 15px }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; min-width: 0 }
.card .t { display: flex; gap: 10px; align-items: center; font: 700 12px var(--mono); letter-spacing: .08em; color: var(--ink) }
.card p { margin: 8px 0 0; color: var(--muted); font-size: 14.5px }
.card ol { margin: 8px 0 0; padding-left: 20px; color: var(--muted); font-size: 14px }
kbd { font: 600 13px var(--mono); border: 1px solid var(--line); border-bottom-width: 2px; border-radius: 5px; padding: 0 5px; background: var(--panel) }
footer { margin-top: 72px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; display: flex;
  justify-content: space-between; gap: 16px; flex-wrap: wrap; align-items: center }
footer img { height: 34px }
@media (max-width: 860px) {
  .wrap { grid-template-columns: minmax(0, 1fr); gap: 16px; padding-block: 20px 60px }
  nav.toc { position: static; flex-direction: row; overflow-x: auto; padding-bottom: 6px; border-bottom: 1px solid var(--line) }
  nav.toc .brand { display: none } nav.toc a { white-space: nowrap }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto } }
html { scroll-behavior: smooth }
"""


def kbd(text: str) -> str:
    import re
    t = E(text)
    return re.sub(r"\b((?:Ctrl|Alt|Shift)\+[A-Za-z0-9…]+(?:\+[A-Za-z0-9…]+)*|F1)\b", r"<kbd>\1</kbd>", t)


def body(img_prefix: str, video: str | None) -> str:
    toc = "".join(f'<a href="#{c["key"]}"><span>{i:02d}</span>{E(c["title"])}</a>' for i, c in enumerate(guides.CHAPTERS, 1))
    parts = []
    for i, c in enumerate(guides.CHAPTERS, 1):
        shot = SHOT.get(c["key"])
        img = (f'<figure class="shot"><img src="{img_prefix}{shot}.jpg" alt="{E(c["title"])} ekranı" loading="lazy" '
               f'width="1600" height="900"></figure>') if shot else ""
        steps = "".join(f"<li><span>{kbd(s)}</span></li>" for s in c["steps"])
        tips = "".join(f"<li>{kbd(s)}</li>" for s in c["tips"])
        cards = "".join(
            f'<div class="card"><div class="t"><span class="i" aria-hidden="true">i</span>{E(t)}</div><p>{kbd(s["text"])}</p>'
            + (f'<ol>{"".join(f"<li>{kbd(x)}</li>" for x in s["steps"])}</ol>' if s.get("steps") else "") + "</div>"
            for t, s in c["sections"].items())
        parts.append(f"""<section class="ch" id="{c['key']}">
<div class="ch-head"><span class="ch-num">{i:02d}</span><h2>{E(c['title'])}</h2></div>
<p class="summary">{kbd(c['summary'])}</p>{img}
{f'<h3>NASIL KULLANILIR</h3><ol class="steps">{steps}</ol>' if steps else ''}
{f'<h3>İPUÇLARI</h3><ul class="tips">{tips}</ul>' if tips else ''}
{f'<h3>BU EKRANDAKİ KARTLAR · ⓘ</h3><div class="cards">{cards}</div>' if cards else ''}
</section>""")
    vid = (f'<video controls preload="metadata" poster="{img_prefix}01_home.jpg" src="{video}">'
           f"</video>") if video else ""
    return f"""<div class="wrap">
<nav class="toc" aria-label="Bölümler"><div class="brand">ELFCAESAR · KILAVUZ</div>{toc}</nav>
<main>
<header class="hero"><img src="{img_prefix}logo.png" alt="ElfCaesar logosu">
<div><div class="eyebrow">KULLANIM KILAVUZU · SÜRÜM {APP_VERSION}</div><h1>ElfCaesar Studio, bölüm bölüm</h1>
<p>Şifreleme, uçtan uca şifreli mesaj, dijital imza ve KVKK kişisel veri koruması — tek çevrimdışı uygulamada.
Her bölümde ne işe yaradığı, adım adım nasıl kullanıldığı ve ekrandaki her kartın anlamı.</p>
<div class="legend"><span class="i" aria-hidden="true">i</span> Uygulamada bu işareti gördüğün her yerde, o kısmın kılavuzu bir tık uzakta. <kbd>F1</kbd> her zaman açar.</div>
</div></header>{vid}
{''.join(parts)}
<footer><span>ElfCaesar Studio {APP_VERSION} · Bir Dante eseri · Uygulama çevrimdışıdır; bu kılavuz da internet gerektirmez.</span>
<img src="{img_prefix}dante.png" alt="Dante imzası"></footer>
</main></div>"""


FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&'
         'family=JetBrains+Mono:wght@600;700&family=Space+Grotesk:wght@600;700&display=swap">')


def build(shots: Path, out_dir: Path, video: str | None = None, fragment: Path | None = None):
    img = out_dir / "img"
    img.mkdir(parents=True, exist_ok=True)
    for name in set(SHOT.values()):
        shutil.copy(shots / f"{name}.jpg", img / f"{name}.jpg")
    shutil.copy(ROOT / "assets" / "logo_128.png", img / "logo.png")
    shutil.copy(ROOT / "assets" / "dante_sig_180.png", img / "dante.png")
    page = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>ElfCaesar Studio Kılavuzu</title><style>{CSS}</style></head><body>{body("img/", video)}</body></html>')
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    if fragment:
        fragment.write_text(f'<title>ElfCaesar Studio Kılavuzu</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                            f'{FONTS}\n<style>{CSS}</style>\n{body("img/", video)}', encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    frag = Path(args[args.index("--fragment") + 1]) if "--fragment" in args else None
    vid = args[args.index("--video") + 1] if "--video" in args else None
    build(Path(args[0]), ROOT / "docs" / "kilavuz", None, None)
    if frag:
        build(Path(args[0]), frag.parent, vid, frag)
