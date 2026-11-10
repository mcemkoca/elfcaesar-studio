"""Kâğıt kurtarma kitapçığı: şifreli kimlik kasasının (.elfid) yazdırılabilir yedeği.

.elfid zaten parolayla (AES-256-GCM + scrypt) şifrelidir; kitapçık parolayı İÇERMEZ.
Geri yükleme: QR'daki metni veya satırları uygulamaya yapıştır → .elfid yeniden oluşur.
"""
from __future__ import annotations

import base64
import html
import re
import time
import zlib

MAGIC = "ELFBACKUP1"
LINE = 32


def _crc(s: str) -> str:
    return f"{zlib.crc32(s.encode()) & 0xFFFF:04X}"


def encode_lines(data: bytes) -> list[str]:
    """Base32 satırları: '01 ABCD… · 3F2A' — her satırda elle yazım hatasını yakalayan sağlama."""
    b32 = base64.b32encode(data).decode().rstrip("=")
    out = []
    for i in range(0, len(b32), LINE):
        chunk = b32[i:i + LINE]
        n = i // LINE + 1
        out.append(f"{n:02d} {' '.join(chunk[j:j + 4] for j in range(0, len(chunk), 4))} · {_crc(f'{n}{chunk}')}")
    return out


def qr_payload(data: bytes) -> str:
    """Tek parça (eski biçim, geriye uyumluluk için okunur)."""
    return f"{MAGIC}:" + base64.b64encode(zlib.compress(data, 9)).decode()


QR_PART_CHARS = 380  # parça başına base32 karakter: QR sürüm ~11–12, telefonla rahat okunur


def qr_parts(data: bytes, size: int = QR_PART_CHARS) -> list[str]:
    """Kimliği numaralı, sağlamalı QR parçalarına böler. Yalnızca A–Z 2–7 : / kullanır → QR alfanümerik mod."""
    b32 = base64.b32encode(zlib.compress(data, 9)).decode().rstrip("=")
    n = max(1, -(-len(b32) // size))
    even = -(-len(b32) // n)  # parçalar eşit boyutta
    chunks = [b32[i:i + even] for i in range(0, len(b32), even)]
    n = len(chunks)
    return [f"{MAGIC}:{i}/{n}:{c}:{_crc(f'{i}/{n}{c}')}" for i, c in enumerate(chunks, start=1)]


class BackupError(ValueError):
    pass


def decode_text(text: str) -> bytes:
    """QR metni (ELFBACKUP1:…) veya numaralı base32 satırlarından kimlik baytlarını geri üretir."""
    text = text.strip()
    parts = re.findall(rf"{MAGIC}:(\d+)/(\d+):([A-Z2-7\s]+):([0-9A-F]{{4}})", text.upper())
    if parts:
        got, total = {}, int(parts[0][1])
        for i, n, chunk, crc in parts:
            chunk = re.sub(r"\s+", "", chunk)
            if int(n) != total or _crc(f"{int(i)}/{n}{chunk}") != crc:
                raise BackupError(f"QR parça {i}/{n} bozuk okunmuş; tekrar okut.")
            got[int(i)] = chunk
        missing = [str(i) for i in range(1, total + 1) if i not in got]
        if missing:
            raise BackupError(f"Eksik QR parçası: {', '.join(missing)} / {total}. Tüm parçaları okutup birlikte yapıştır.")
        b32 = "".join(got[i] for i in range(1, total + 1))
        try:
            return zlib.decompress(base64.b32decode(b32 + "=" * (-len(b32) % 8)))
        except Exception as exc:
            raise BackupError("QR parçaları birleştirilemedi.") from exc
    m = re.search(rf"{MAGIC}:([A-Za-z0-9+/=\s]+)", text)
    if m:
        try:
            return zlib.decompress(base64.b64decode(re.sub(r"\s+", "", m.group(1)), validate=True))
        except Exception as exc:
            raise BackupError("QR metni eksik veya bozuk.") from exc
    rows = re.findall(r"^\s*(\d{1,3})\s+([A-Z2-7 ]+?)\s*[·.:-]\s*([0-9A-F]{4})\s*$", text.upper(), re.M)
    if not rows:
        raise BackupError("Kitapçık satırı veya QR metni bulunamadı.")
    chunks = {}
    for n, body, crc in rows:
        chunk = body.replace(" ", "")
        if _crc(f"{int(n)}{chunk}") != crc:
            raise BackupError(f"{int(n)}. satırda yazım hatası var (sağlama tutmuyor).")
        chunks[int(n)] = chunk
    if sorted(chunks) != list(range(1, len(chunks) + 1)):
        raise BackupError("Eksik satır var: " + ", ".join(str(i) for i in range(1, max(chunks) + 1) if i not in chunks))
    b32 = "".join(chunks[i] for i in sorted(chunks))
    try:
        return base64.b32decode(b32 + "=" * (-len(b32) % 8))
    except Exception as exc:
        raise BackupError("Satırlar çözülemedi.") from exc


def looks_like_identity(data: bytes) -> bool:
    return data.startswith(b"ELFVAULT1\n") and b'"kind":"identity"' in data.replace(b" ", b"")


def qr_svg(text: str, scale: int = 4) -> str:
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    m = qr.get_matrix()
    n = len(m)
    rects = "".join(f'<rect x="{x}" y="{y}" width="1" height="1"/>' for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n * scale}" height="{n * scale}" '
            f'shape-rendering="crispEdges"><rect width="{n}" height="{n}" fill="#fff"/><g fill="#000">{rects}</g></svg>')


def make_html(identity_bytes: bytes, contact: dict, words: list[str], contact_armor: str, version: str, signature_png_b64: str = "") -> str:
    e = html.escape
    lines = encode_lines(identity_bytes)
    parts = qr_parts(identity_bytes)
    fp = contact["fingerprint"].upper()
    fp_fmt = " ".join(fp[i:i + 4] for i in range(0, len(fp), 4))
    sig = f'<img class="sig" src="data:image/png;base64,{signature_png_b64}" alt="Dante">' if signature_png_b64 else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>ElfCaesar Kurtarma Kitapçığı — {e(contact['name'])}</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font: 11pt/1.45 "Segoe UI", Arial, sans-serif; color: #111; max-width: 182mm; margin: 0 auto; }}
h1 {{ font-size: 20pt; margin: 0; }} h2 {{ font-size: 12pt; margin: 18px 0 6px; border-bottom: 1px solid #999; }}
.top {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom: 3px solid #b8862f; padding-bottom: 8px; }}
.muted {{ color:#555; font-size: 9.5pt; }} .warn {{ background:#fff4e0; border-left: 4px solid #b8862f; padding: 8px 10px; }}
.grid {{ display:flex; gap: 18px; align-items:flex-start; }} .mono {{ font-family: Consolas, "Courier New", monospace; }}
.lines {{ font-size: 10pt; line-height: 1.5; }} .lines div {{ break-inside: avoid; white-space: nowrap; }}
.words span {{ display:inline-block; border:1px solid #333; border-radius:4px; padding:3px 8px; margin:2px; font-weight:600; }}
.sig {{ height: 34px; filter: brightness(.45) sepia(1); }} .box {{ border:1px dashed #666; height: 26px; margin: 4px 0 10px; }}
.page {{ page-break-before: always; }} .qrs {{ display:flex; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }}
figure {{ margin: 0; text-align: center; }} figcaption {{ font-size: 8.5pt; color: #555; }}
</style></head><body>
<div class="top"><div><h1>Kurtarma Kitapçığı</h1><div class="muted">ElfCaesar Studio {e(version)} · {time.strftime('%d.%m.%Y %H:%M')}</div></div>
<div style="text-align:right"><div class="muted">Bir Dante eseri</div>{sig}</div></div>
<p class="warn"><b>Bu sayfa senin özel kimliğinin şifreli kopyasıdır.</b> Kimlik parolası bu kitapçıkta YOKTUR; parola olmadan
yedek açılamaz. Yine de bir kasa veya kilitli çekmecede, bilgisayarından ayrı bir yerde sakla. Fotoğrafını bulut hizmetlerine yükleme.</p>
<h2>Kimlik</h2>
<p><b>Ad:</b> {e(contact['name'])}<br><b>Parmak izi:</b> <span class="mono">{fp_fmt}</span></p>
<p class="words"><b>Güvenlik kelimeleri:</b><br>{''.join(f'<span>{e(w)}</span>' for w in words)}</p>
<h2>1 · Hızlı geri yükleme (QR)</h2>
<div class="qrs">{''.join(f'<figure>{qr_svg(p, 3)}<figcaption>Parça {i}/{len(parts)}</figcaption></figure>' for i, p in enumerate(parts, start=1))}</div>
<div><ol><li>Telefonunun kamerasıyla QR parçalarını sırayla okut; metinleri bir notta alt alta topla.</li>
<li>Metni bilgisayarına aktar (kendine e-posta yerine kablo, Bluetooth veya yerel ağ önerilir).</li>
<li>ElfCaesar Studio → Güvenli Kasa → <b>KİTAPÇIKTAN GERİ YÜKLE</b> → yapıştır → kaydet.</li>
<li>Kimlik parolanla açılıp açılmadığını kontrol et.</li></ol>
<p class="muted">Her parça ELFBACKUP1:1/{len(parts)}: gibi başlar ve kendi sağlamasını taşır; sıra önemli değildir.</p></div>
<h2>Parola ipucu (isteğe bağlı — parolanın kendisini yazma)</h2><div class="box"></div>
<h2>Açık kişi kartın (paylaşılabilir)</h2>
<div class="grid"><div>{qr_svg(contact_armor, 3)}</div><div class="muted">Bu QR yalnızca AÇIK anahtarlarını içerir; başkalarıyla
paylaşabilirsin. Karşı taraf okutup ElfCaesar'da “PANODAN KART EKLE” ile defterine ekler, sonra güvenlik kelimelerini karşılaştırırsınız.</div></div>
<div class="page"></div>
<h2>2 · Elle geri yükleme (QR okunamazsa)</h2>
<p class="muted">Satırları numaralarıyla birlikte ElfCaesar'daki geri yükleme alanına yaz. Her satırın sonundaki 4 karakterlik sağlama,
yazım hatasını satır numarasıyla gösterir. Toplam {len(lines)} satır.</p>
<div class="lines mono">{''.join(f'<div>{e(l)}</div>' for l in lines)}</div>
<p class="muted" style="margin-top:18px">Kitapçık bilgisayarında oluşturuldu; hiçbir sunucuya gönderilmedi. ElfCaesar Studio · Dante</p>
</body></html>"""
