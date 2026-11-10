"""Güvenli imha + KVKK imha tutanağı.

AxCrypt / Eraser benzeri üzerine yazarak silme. KVKK (Kişisel Verilerin Silinmesi, Yok Edilmesi veya
Anonim Hale Getirilmesi Hakkında Yönetmelik) imha işlemlerinin kayıt altına alınmasını ister; burada
her imha için dosya adı, boyut, SHA-256 özeti (içerik değil), yöntem ve zaman tutanağa yazılır.

Dürüst not: SSD'lerde (wear-leveling), bulut eşitlemeli klasörlerde ve gölge kopyalarda üzerine yazma
eski blokların silindiğini garanti etmez. En güvenli yol veriyi baştan şifreli tutmaktır.
"""
from __future__ import annotations

import hashlib
import html
import os
import secrets
import time
from dataclasses import dataclass, asdict
from pathlib import Path

METHODS = {
    "random1": ("Tek geçiş rastgele veri", 1),
    "random3": ("Üç geçiş rastgele veri", 3),
}


@dataclass
class ShredRecord:
    path: str
    name: str
    size: int
    sha256: str
    method: str
    when: float
    ok: bool
    error: str = ""


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def shred_file(path: str | Path, method: str = "random1") -> ShredRecord:
    p = Path(path)
    label, passes = METHODS[method]
    rec = ShredRecord(str(p), p.name, 0, "", method, time.time(), False)
    try:
        if not p.is_file() or p.is_symlink():
            raise FileNotFoundError("Normal dosya değil")
        rec.size = p.stat().st_size
        rec.sha256 = _hash(p)
        with open(p, "r+b", buffering=0) as f:
            for _ in range(passes):
                f.seek(0)
                left = rec.size
                while left > 0:
                    n = min(left, 1 << 20)
                    f.write(secrets.token_bytes(n))
                    left -= n
                f.flush()
                os.fsync(f.fileno())
            f.truncate(0)
        # Dosya adını da iz bırakmayacak şekilde değiştir
        anon = p.with_name(secrets.token_hex(8))
        os.replace(p, anon)
        anon.unlink()
        rec.ok = True
    except Exception as exc:  # noqa: BLE001 — tutanakta hata olarak görünür
        rec.error = str(exc)
    return rec


def shred_many(paths, method="random1", progress=None) -> list[ShredRecord]:
    out = []
    for i, p in enumerate(paths, 1):
        out.append(shred_file(p, method))
        if progress:
            progress(i, len(paths), p)
    return out


def tutanak_html(records: list[ShredRecord], org: str = "", reason: str = "", version: str = "",
                 signature_png_b64: str = "") -> str:
    e = html.escape
    ok = [r for r in records if r.ok]
    rows = "".join(
        f"<tr class='{'ok' if r.ok else 'err'}'><td>{i}</td><td class='w'>{e(r.name)}</td><td>{r.size:,}</td>"
        f"<td class='h'>{r.sha256[:32]}<br>{r.sha256[32:]}</td><td>{e(METHODS[r.method][0])}</td>"
        f"<td>{time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(r.when))}</td>"
        f"<td>{'İmha edildi' if r.ok else 'HATA: ' + e(r.error)}</td></tr>".replace(",", ".")
        for i, r in enumerate(records, 1))
    body = f"""<h1>Kişisel Veri İmha Tutanağı</h1>
<p class="muted">{e(org) + ' · ' if org else ''}Düzenleme: {time.strftime('%d.%m.%Y %H:%M')} · ElfCaesar Studio {e(version)}</p>
<table class="meta"><tr><th>İmha yöntemi</th><td>Silme — dosya içeriğinin rastgele veriyle üzerine yazılması, adının
anonimleştirilmesi ve dosya sisteminden kaldırılması</td></tr>
<tr><th>İmha gerekçesi</th><td>{e(reason) or 'İşleme amacının sona ermesi / periyodik imha'}</td></tr>
<tr><th>Sonuç</th><td>{len(ok)} / {len(records)} dosya imha edildi</td></tr></table>
<h2>İmha edilen kayıtlar</h2>
<table><tr><th>#</th><th>Dosya adı</th><th>Boyut (bayt)</th><th>SHA-256 (imha öncesi)</th><th>Yöntem</th><th>Zaman</th><th>Durum</th></tr>{rows}</table>
<p class="note">SHA-256 özeti, imha edilen içeriğin hangi dosya olduğunu sonradan ispatlamaya yarar; içeriği geri getirmez ve
kişisel veri içermez. SSD, bulut eşitleme ve yedekleme sistemlerinde kopyalar kalabilir; bu sistemlerdeki kopyalar ayrıca imha
edilmelidir. Bu tutanak hukuki görüş değildir; saklama ve imha politikanıza göre en az üç yıl saklanması önerilir.</p>
<div class="sign"><div>İmhayı gerçekleştiren<br><br>Ad Soyad / İmza</div><div>Onaylayan (Veri sorumlusu)<br><br>Ad Soyad / İmza</div></div>"""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sig = f'<img class="sig" src="data:image/png;base64,{signature_png_b64}" alt="Dante">' if signature_png_b64 else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>İmha Tutanağı · {time.strftime('%d.%m.%Y')}</title>
<style>@page {{ size: A4; margin: 14mm; }} body {{ font: 10.5pt/1.45 "Segoe UI", Arial, sans-serif; color:#111; max-width:190mm; margin:0 auto; }}
h1 {{ margin:0; font-size:20pt; }} h2 {{ font-size:12pt; border-bottom:1px solid #aaa; margin-top:20px; }} .muted {{ color:#555; font-size:9.5pt; }}
table {{ width:100%; border-collapse:collapse; font-size:8.5pt; }} th, td {{ border-bottom:1px solid #ddd; padding:4px 6px; text-align:left; vertical-align:top; }}
th {{ background:#f3f3f3; }} table.meta th {{ width:28%; }} td.w {{ word-break:break-word; }} td.h {{ font-family:Consolas,monospace; font-size:7.5pt; }}
tr.err td {{ color:#b00020; }} .note {{ background:#f6f6f6; padding:8px 10px; font-size:8.5pt; }}
.sign {{ display:flex; gap:40px; margin-top:30px; }} .sign div {{ flex:1; border-top:1px solid #333; padding-top:6px; font-size:9pt; height:60px; }}
.foot {{ display:flex; justify-content:space-between; align-items:center; border-top:2px solid #b8862f; margin-top:20px; padding-top:6px; font-size:8pt; color:#555; }}
.sig {{ height:28px; filter:brightness(.45) sepia(1); }}</style></head><body>{body}
<div class="foot"><div>Tutanak özeti (SHA-256): <span style="font-family:Consolas,monospace">{digest}</span><br>ElfCaesar Studio · Güvenli İmha · Bir Dante eseri</div>{sig}</div>
</body></html>"""


def records_json(records) -> list[dict]:
    return [asdict(r) for r in records]
