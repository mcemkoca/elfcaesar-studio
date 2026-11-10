"""Sohbet zırhı (ELF1): şifreli paketleri WhatsApp / Telegram / e-posta gibi kanallarda güvenle taşımak için.

Bu modül bir TAŞIMA katmanıdır; şifreleme yapmaz. Kimlik motorunun ürettiği ELFDM1 paketini
kayıpsız ve kompakt bir ikili biçime çevirir, tek satırlık metin olarak zırhlar ve geri açar.
Kriptografik doğrulama yine motor (identity.decrypt_from_contact) tarafından yapılır.

Biçim:  🔐ELF1:<tür>:<base64>:<sağlama>        (parçalı: ELF1:<tür>#<id>.<i>.<n>:<base64>:<sağlama>)
Türler: M = kişiye özel mesaj, G = grup mesajı, P = parolalı mesaj, K = açık kişi kartı.
Alfabe yalnızca A–Z a–z 0–9 + / içerir: WhatsApp'ın _ * ~ ` biçimlendirme işaretlerinden etkilenmez.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import zlib

MAGIC = "ELF1"
BADGE = "🔐"
DM_FORMAT, CONTACT_FORMAT = "ELFDM1", "ELFCONTACT1"
DEFAULT_LIMIT = 3500  # Telegram mesaj sınırı 4096; pay bırakılır
KIND_NAMES = {"M": "Kişiye özel mesaj", "G": "Grup mesajı", "P": "Parolalı mesaj", "K": "Kişi kartı"}

_PATTERN = re.compile(
    r"ELF1:(?P<kind>[MGPK])(?:#(?P<id>[0-9a-f]{4})\.(?P<i>\d{1,2})\.(?P<n>\d{1,2}))?:"
    r"(?P<body>[A-Za-z0-9+/\s]+?):(?P<chk>[0-9a-f]{6})")


class ArmorError(ValueError):
    pass


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii").rstrip("=")


def _b64d(s: str) -> bytes:
    s = re.sub(r"\s+", "", s)
    try:
        return base64.b64decode(s + "=" * (-len(s) % 4), validate=True)
    except Exception as exc:
        raise ArmorError("Zırh verisi bozuk (base64).") from exc


def _chk(kind: str, body: str) -> str:
    return hashlib.sha256(f"{kind}:{body}".encode()).hexdigest()[:6]


def fingerprint_of(x_pub: bytes, ed_pub: bytes) -> str:
    """Kimlik motoruyla aynı parmak izi tanımı (motor doğrulamayı yine kendisi yapar)."""
    return hashlib.sha256(b"ELFCAESAR-ID-v1\0" + x_pub + ed_pub).hexdigest()


def _std_b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _std_unb64(s: str) -> bytes:
    return base64.b64decode(s, validate=True)


# ------------------------------------------------------------------ kompakt ikili kodlama
def pack_dm(payload: str) -> bytes:
    """ELFDM1 metin paketini kompakt ikili biçime çevirir; kayıpsızlık geri açılarak doğrulanır."""
    try:
        magic, raw = payload.split("\n", 1)
        body = json.loads(raw)
        h = body["header"]
        if magic != DM_FORMAT or h.get("format") != DM_FORMAT or h.get("version") != 1:
            raise ValueError
        fp = bytes.fromhex(h["recipient"])
        eph, salt, nonce = _std_unb64(h["ephemeral"]), _std_unb64(h["salt"]), _std_unb64(h["nonce"])
        cipher = _std_unb64(body["ciphertext"])
        if len(fp) != 32 or len(eph) != 32 or len(salt) != 16 or len(nonce) != 12:
            raise ValueError
        signed = "signature" in body
        out = bytearray([1 if signed else 0]) + fp + eph + salt + nonce
        if signed:
            s = body["sender"]
            name = s.get("name", "").encode("utf-8")
            if len(name) > 255 or s.get("format") != CONTACT_FORMAT or s.get("version") != 1:
                raise ValueError
            x, e, sig = _std_unb64(s["x25519_public"]), _std_unb64(s["ed25519_public"]), _std_unb64(body["signature"])
            if len(x) != 32 or len(e) != 32 or len(sig) != 64 or fingerprint_of(x, e) != s.get("fingerprint"):
                raise ValueError
            out += x + e + sig + bytes([len(name)]) + name
        out += cipher
    except Exception as exc:
        raise ArmorError("ELFDM1 paketi zırhlanamadı.") from exc
    packed = bytes(out)
    if json.loads(unpack_dm(packed).split("\n", 1)[1]) != body:  # kayıpsızlık güvencesi
        raise ArmorError("Kompakt kodlama doğrulanamadı.")
    return packed


def unpack_dm(blob: bytes) -> str:
    try:
        flags, pos = blob[0], 1
        fp, eph, salt, nonce = blob[pos:pos + 32], blob[pos + 32:pos + 64], blob[pos + 64:pos + 80], blob[pos + 80:pos + 92]
        pos += 92
        header = {"format": DM_FORMAT, "version": 1, "recipient": fp.hex(), "ephemeral": _std_b64(eph),
                  "salt": _std_b64(salt), "nonce": _std_b64(nonce)}
        body = {"header": header}
        if flags & 1:
            x, e, sig = blob[pos:pos + 32], blob[pos + 32:pos + 64], blob[pos + 64:pos + 128]
            pos += 128
            n = blob[pos]
            name = blob[pos + 1:pos + 1 + n].decode("utf-8")
            pos += 1 + n
            if len(x) != 32 or len(e) != 32 or len(sig) != 64:
                raise ValueError
            body["sender"] = {"format": CONTACT_FORMAT, "version": 1, "name": name, "x25519_public": _std_b64(x),
                              "ed25519_public": _std_b64(e), "fingerprint": fingerprint_of(x, e)}
            body["signature"] = _std_b64(sig)
        cipher = blob[pos:]
        if len(fp) != 32 or len(nonce) != 12 or len(cipher) < 16:
            raise ValueError
        body["ciphertext"] = _std_b64(cipher)
    except Exception as exc:
        raise ArmorError("Zırhlı mesaj eksik veya bozuk.") from exc
    return DM_FORMAT + "\n" + json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def dm_recipient(blob: bytes) -> str:
    return blob[1:33].hex()


def pack_contact(contact: dict) -> bytes:
    x, e = _std_unb64(contact["x25519_public"]), _std_unb64(contact["ed25519_public"])
    if fingerprint_of(x, e) != contact.get("fingerprint"):
        raise ArmorError("Kişi kartı parmak izi tutarsız.")
    name = contact.get("name", "").encode("utf-8")[:255]
    return x + e + bytes([len(name)]) + name


def unpack_contact(blob: bytes) -> dict:
    if len(blob) < 65:
        raise ArmorError("Kişi kartı eksik.")
    x, e, n = blob[:32], blob[32:64], blob[64]
    name = blob[65:65 + n].decode("utf-8", errors="strict")
    return {"format": CONTACT_FORMAT, "version": 1, "name": name, "x25519_public": _std_b64(x),
            "ed25519_public": _std_b64(e), "fingerprint": fingerprint_of(x, e)}


def pack_group(payloads: list[str]) -> bytes:
    if not 1 <= len(payloads) <= 32:
        raise ArmorError("Grup mesajı 1–32 alıcı destekler.")
    out = bytearray([len(payloads)])
    for p in payloads:
        blob = pack_dm(p)
        out += len(blob).to_bytes(2, "big") + blob
    return bytes(out)


def unpack_group(blob: bytes) -> list[bytes]:
    try:
        count, pos, items = blob[0], 1, []
        for _ in range(count):
            n = int.from_bytes(blob[pos:pos + 2], "big")
            items.append(blob[pos + 2:pos + 2 + n])
            pos += 2 + n
        if pos != len(blob):
            raise ValueError
        return items
    except Exception as exc:
        raise ArmorError("Grup mesajı bozuk.") from exc


# ------------------------------------------------------------------ zırh
def armor(kind: str, data: bytes) -> str:
    if kind not in KIND_NAMES:
        raise ArmorError("Bilinmeyen zırh türü.")
    if kind == "P":
        data = zlib.compress(data, 9)
    body = _b64e(data)
    return f"{BADGE}{MAGIC}:{kind}:{body}:{_chk(kind, body)}"


def armor_dm(payload: str) -> str:
    return armor("M", pack_dm(payload))


def armor_group(payloads: list[str]) -> str:
    return armor("G", pack_group(payloads))


def armor_password(payload: str) -> str:
    return armor("P", payload.encode("utf-8"))


def armor_contact(contact: dict) -> str:
    return armor("K", pack_contact(contact))


def split(armored: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """Uzun zırhı sohbet mesajı sınırına göre numaralı parçalara böler."""
    if len(armored) <= limit:
        return [armored]
    m = _PATTERN.search(armored)
    if not m or m.group("id"):
        raise ArmorError("Bölünecek geçerli zırh bulunamadı.")
    kind, body = m.group("kind"), re.sub(r"\s+", "", m.group("body"))
    size = max(200, limit - 40)
    chunks = [body[i:i + size] for i in range(0, len(body), size)]
    if len(chunks) > 99:
        raise ArmorError("Mesaj sohbet için çok uzun; dosya kasasını kullan.")
    mid = secrets.token_hex(2)
    out = []
    for i, c in enumerate(chunks, start=1):
        tag = f"{kind}#{mid}.{i}.{len(chunks)}"
        out.append(f"{BADGE}{MAGIC}:{tag}:{c}:{_chk(tag, c)}")
    return out


class Reassembler:
    """Parçaları (farklı kopyalamalardan gelse bile) birleştirir."""

    def __init__(self):
        self.parts: dict[str, dict[int, str]] = {}
        self.meta: dict[str, tuple[str, int]] = {}

    def feed(self, text: str) -> list[tuple[str, bytes]]:
        complete = []
        for m in _PATTERN.finditer(text or ""):
            kind, body = m.group("kind"), re.sub(r"\s+", "", m.group("body"))
            if m.group("id"):
                tag = f"{kind}#{m.group('id')}.{m.group('i')}.{m.group('n')}"
                if _chk(tag, body) != m.group("chk"):
                    raise ArmorError("Parça sağlaması tutmuyor; mesaj eksik kopyalanmış olabilir.")
                key, i, n = f"{kind}#{m.group('id')}", int(m.group("i")), int(m.group("n"))
                self.parts.setdefault(key, {})[i] = body
                self.meta[key] = (kind, n)
                if len(self.parts[key]) == n:
                    joined = "".join(self.parts[key][k] for k in range(1, n + 1))
                    complete.append((kind, self._decode(kind, joined)))
                    del self.parts[key], self.meta[key]
            else:
                if _chk(kind, body) != m.group("chk"):
                    raise ArmorError("Zırh sağlaması tutmuyor; mesaj eksik veya değiştirilmiş kopyalanmış.")
                complete.append((kind, self._decode(kind, body)))
        return complete

    @staticmethod
    def _decode(kind: str, body: str) -> bytes:
        data = _b64d(body)
        if kind == "P":
            try:
                data = zlib.decompress(data)
            except zlib.error as exc:
                raise ArmorError("Parolalı mesaj zırhı bozuk.") from exc
        return data

    def pending(self) -> list[tuple[str, int, int]]:
        return [(KIND_NAMES[self.meta[k][0]], len(v), self.meta[k][1]) for k, v in self.parts.items()]


def detect(text: str) -> bool:
    return bool(text) and "ELF1:" in text and _PATTERN.search(text) is not None


# ------------------------------------------------------------------ güvenlik kelimeleri
WORDS = """elma armut kiraz üzüm incir nar ayva erik limon portakal ceviz fındık badem zeytin buğday arpa
çınar meşe kavak söğüt çam ladin akasya ıhlamur gül lale nergis papatya menekşe sümbül orkide karanfil
aslan kaplan kurt tilki ayı geyik ceylan tavşan sincap kartal şahin doğan baykuş serçe martı turna
yunus balina ahtapot mercan inci ırmak deniz göl şelale vadi tepe dağ ova orman çöl ada
güneş ay yıldız bulut yağmur kar rüzgar fırtına şimşek gökkuşağı şafak akşam gece sabah bahar yaz
kılıç kalkan zırh miğfer ok yay mızrak bayrak kale kule köprü kapı anahtar kilit fener mum
kitap kalem defter harita pusula saat ayna hazine taç yüzük kolye madalya kupa sandık davul kaval
gemi yelken çapa dümen kanat tüy yuva bal süt ekmek tuz çay kahve şeker baharat demir""".split()
assert len(WORDS) == 128 and len(set(WORDS)) == 128


def safety_words(fingerprint: str, count: int = 6) -> list[str]:
    """Parmak izinden telefonda sesli karşılaştırılabilecek 6 Türkçe kelime (42 bit)."""
    digest = int.from_bytes(hashlib.sha256(b"ELFCAESAR-WORDS-v1\0" + fingerprint.strip().lower().encode()).digest(), "big")
    return [WORDS[(digest >> (7 * i)) & 127] for i in range(count)]
