"""KVKK Kalkanı: bilgisayardaki dosyalarda kişisel veri envanteri.

Gizlilik: bulunan DEĞERLER asla saklanmaz, gösterilmez veya rapora yazılmaz; yalnızca dosya başına
tür ve adet tutulur. Tarama tamamen yereldir. Bu araç hukuki danışmanlık değildir.
"""
from __future__ import annotations

import html
import os
import re
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .security import scan_sensitive

TEXT_EXT = {".txt", ".csv", ".tsv", ".md", ".json", ".xml", ".log", ".html", ".htm", ".eml", ".ini", ".yaml",
            ".yml", ".sql", ".rtf", ".vcf"}
ZIP_XML_EXT = {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"}
SKIP_DIRS = {"node_modules", "__pycache__", "$recycle.bin", "system volume information", "windows", "program files",
             "program files (x86)", "programdata", "appdata", ".git", ".svn", "venv", ".venv", "site-packages"}
MAX_BYTES = 20 * 1024 * 1024
WEIGHTS = {"tckn": 10, "card": 10, "iban": 8, "secret": 8, "phone": 3, "email": 1}
LABELS = {"tckn": "T.C. kimlik", "card": "Kart no", "iban": "IBAN", "secret": "Parola/PIN", "phone": "Telefon", "email": "E-posta"}
KVKK_CATEGORY = {"tckn": "Kimlik", "card": "Finans", "iban": "Finans", "secret": "İşlem güvenliği",
                 "phone": "İletişim", "email": "İletişim"}


@dataclass
class FileFinding:
    path: str
    size: int
    mtime: float
    counts: dict
    score: int
    level: str  # high / medium / low

    @property
    def summary(self) -> str:
        return ", ".join(f"{LABELS[k]} {v}" for k, v in sorted(self.counts.items(), key=lambda kv: -WEIGHTS[kv[0]]))


@dataclass
class ScanResult:
    roots: list
    started: float = field(default_factory=time.time)
    finished: float | None = None
    files_seen: int = 0
    files_scanned: int = 0
    files_skipped: int = 0
    bytes_scanned: int = 0
    errors: int = 0
    findings: list = field(default_factory=list)
    cancelled: bool = False

    def totals(self) -> dict:
        out = {k: 0 for k in WEIGHTS}
        for f in self.findings:
            for k, v in f.counts.items():
                out[k] += v
        return out

    def by_level(self) -> dict:
        out = {"high": 0, "medium": 0, "low": 0}
        for f in self.findings:
            out[f.level] += 1
        return out


def human_size(n: int) -> str:
    return f"{n} B" if n < 1024 else (f"{n / 1024:.0f} KB" if n < 1024 ** 2 else f"{n / 1024 ** 2:.1f} MB")


def display_path(path: str, roots) -> str:
    """Taranan köke göre kısa yol: ornek_sirket/IK/personel.txt"""
    p = Path(path)
    for r in roots:
        try:
            return str(Path(Path(r).name) / p.relative_to(Path(r)))
        except ValueError:
            continue
    return str(p)


def risk_level(score: int) -> str:
    return "high" if score >= 10 else ("medium" if score >= 3 else "low")


def _strip_xml(data: bytes) -> str:
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(text)


def extract_text(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        raw = path.read_bytes()[:MAX_BYTES]
        for enc in ("utf-8", "cp1254", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        return _strip_xml(text.encode()) if ext in {".html", ".htm", ".xml"} else text
    if ext in ZIP_XML_EXT:
        parts = []
        with zipfile.ZipFile(path) as z:
            total = 0
            for info in z.infolist():
                name = info.filename.lower()
                if not name.endswith(".xml") or info.file_size > MAX_BYTES:
                    continue
                if not (name.startswith(("word/document", "word/header", "word/footer", "xl/sharedstrings", "xl/worksheets/",
                                         "ppt/slides/slide")) or name == "content.xml"):
                    continue
                total += info.file_size
                if total > MAX_BYTES:
                    break
                parts.append(_strip_xml(z.read(info)))
        return "\n".join(parts)
    return None


def scan_file(path: Path) -> FileFinding | None:
    text = extract_text(path)
    if not text:
        return None
    found = scan_sensitive(text)
    if not found:
        return None
    counts = {f["kind"]: f["count"] for f in found}
    score = sum(WEIGHTS[k] * min(v, 5) for k, v in counts.items())
    st = path.stat()
    return FileFinding(str(path), st.st_size, st.st_mtime, counts, score, risk_level(score))


def iter_files(roots):
    for root in roots:
        root = Path(root)
        if root.is_file():
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                yield Path(dirpath) / name


def scan(roots, cancel: threading.Event | None = None, progress=None) -> ScanResult:
    result = ScanResult(roots=[str(r) for r in roots])
    for path in iter_files(roots):
        if cancel is not None and cancel.is_set():
            result.cancelled = True
            break
        result.files_seen += 1
        ext = path.suffix.lower()
        if ext not in TEXT_EXT and ext not in ZIP_XML_EXT:
            result.files_skipped += 1
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                result.files_skipped += 1
                continue
            finding = scan_file(path)
            result.files_scanned += 1
            result.bytes_scanned += path.stat().st_size
            if finding:
                result.findings.append(finding)
        except (OSError, zipfile.BadZipFile, RuntimeError):
            result.errors += 1
        if progress and result.files_seen % 25 == 0:
            progress(result, str(path))
    result.findings.sort(key=lambda f: (-f.score, f.path))
    result.finished = time.time()
    if progress:
        progress(result, "")
    return result


def report_html(result: ScanResult, org: str = "", version: str = "", signature_png_b64: str = "") -> str:
    import hashlib
    e = html.escape
    totals, levels = result.totals(), result.by_level()
    dur = (result.finished or time.time()) - result.started
    rows = "".join(
        f"<tr class='{f.level}'><td class='path'>{e(display_path(f.path, result.roots))}</td><td class='types'>{e(f.summary)}</td><td>{ {'high': 'Yüksek', 'medium': 'Orta', 'low': 'Düşük'}[f.level]}</td>"
        f"<td>{human_size(f.size)}</td><td>{time.strftime('%d.%m.%Y', time.localtime(f.mtime))}</td></tr>"
        for f in result.findings)
    cats = "".join(f"<tr><td>{LABELS[k]}</td><td>{KVKK_CATEGORY[k]}</td><td>{v}</td></tr>" for k, v in totals.items() if v)
    body = f"""<h1>Kişisel Veri Envanteri</h1>
<p class="muted">{e(org) + ' · ' if org else ''}Oluşturma: {time.strftime('%d.%m.%Y %H:%M')} · ElfCaesar Studio {e(version)} · KVKK Kalkanı</p>
<div class="tiles"><div><b>{result.files_scanned:,}</b><span>taranan dosya</span></div><div><b>{len(result.findings):,}</b><span>kişisel veri içeren</span></div>
<div class="h"><b>{levels['high']}</b><span>yüksek riskli</span></div><div><b>{levels['medium']}</b><span>orta riskli</span></div>
<div><b>{dur:.0f} sn</b><span>süre</span></div></div>
<h2>Taranan konumlar</h2><ul>{''.join(f'<li>{e(r)}</li>' for r in result.roots)}</ul>
<p class="muted">{result.files_seen:,} dosya görüldü · {result.files_skipped:,} desteklenmeyen/büyük dosya atlandı · {result.errors} okuma hatası
{' · TARAMA YARIDA KESİLDİ' if result.cancelled else ''}</p>
<h2>Veri kategorileri (adet)</h2><table><tr><th>Veri türü</th><th>Kategori</th><th>Bulunan</th></tr>{cats or '<tr><td colspan=3>Bulunmadı</td></tr>'}</table>
<h2>Dosyalar</h2><table><tr><th>Dosya</th><th>İçerdiği veri türleri</th><th>Risk</th><th>Boyut</th><th>Değişiklik</th></tr>{rows or '<tr><td colspan=5>Kişisel veri içeren dosya bulunmadı.</td></tr>'}</table>
<h2>Önerilen teknik tedbirler</h2><ol>
<li>Yüksek riskli dosyaları şifreleyin (ElfCaesar → KVKK Kalkanı → KASAYA AL) veya erişimi kısıtlı bir konuma taşıyın.</li>
<li>İşleme amacı sona eren kişisel verileri imha politikanıza göre silin, yok edin veya anonim hâle getirin.</li>
<li>Parola/PIN içeren düz metin dosyalarını kaldırın; parolaları parola yöneticisinde tutun.</li>
<li>Bu taramayı düzenli aralıklarla tekrarlayın ve raporları saklayın.</li></ol>
<p class="note">Bu rapor bulunan değerleri içermez; yalnızca dosya konumu, veri türü ve adet içerir. Otomatik tespit hatalı sonuç
verebilir (örn. tesadüfen geçerli sayı dizileri). Bu rapor hukuki görüş değildir; KVKK uyumu için hukuk danışmanınıza başvurun.</p>"""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sig = f'<img class="sig" src="data:image/png;base64,{signature_png_b64}" alt="Dante">' if signature_png_b64 else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Kişisel Veri Envanteri · {time.strftime('%d.%m.%Y')}</title>
<style>@page {{ size: A4; margin: 14mm; }} body {{ font: 10.5pt/1.45 "Segoe UI", Arial, sans-serif; color:#111; max-width: 190mm; margin: 0 auto; }}
h1 {{ margin: 0; font-size: 20pt; }} h2 {{ font-size: 12pt; border-bottom: 1px solid #aaa; margin-top: 20px; }}
.muted {{ color:#555; font-size: 9.5pt; }} table {{ width:100%; border-collapse: collapse; font-size: 9pt; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 4px 6px; text-align:left; vertical-align: top; white-space: nowrap; }}
td.path, td.types {{ white-space: normal; word-break: break-word; }}
th {{ background:#f3f3f3; }} tr.high td:nth-child(3) {{ color:#b00020; font-weight:700; }} tr.medium td:nth-child(3) {{ color:#a15c00; }}
.tiles {{ display:flex; gap:10px; margin: 14px 0; }} .tiles div {{ flex:1; border:1px solid #ccc; border-radius:6px; padding:8px; }}
.tiles b {{ display:block; font-size: 16pt; }} .tiles span {{ color:#555; font-size: 8.5pt; }} .tiles .h b {{ color:#b00020; }}
.note {{ background:#f6f6f6; padding: 8px 10px; font-size: 8.5pt; }} .foot {{ display:flex; justify-content:space-between; align-items:center;
border-top: 2px solid #b8862f; margin-top: 20px; padding-top: 6px; font-size: 8pt; color:#555; }} .sig {{ height: 28px; filter: brightness(.45) sepia(1); }}
</style></head><body>{body}
<div class="foot"><div>Rapor özeti (SHA-256): <span style="font-family:Consolas,monospace">{digest}</span><br>ElfCaesar Studio · KVKK Kalkanı · Bir Dante eseri</div>{sig}</div>
</body></html>"""
