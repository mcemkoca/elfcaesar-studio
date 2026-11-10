"""ELFC2 codec. This is reversible encoding/obfuscation, NOT secure encryption."""
from __future__ import annotations
import json
from .alphabet import ALPHABET, CHAR_TO_IDX, N

VERSION = "ELFC2"
LETTER_TO_TOKEN = dict(zip(ALPHABET, (
    "el an or ith ar en ae lo na si ta ri ne th ul mo fa ra ie sa do he vi ya we ku pe ze sh"
).split()))
TOKEN_TO_LETTER = {v: k for k, v in LETTER_TO_TOKEN.items()}
SEP, SPACE, NEWLINE, UPPER = "-", "_", "|", "^"

class ElfFormatError(ValueError):
    pass

def _escape(ch: str) -> str:
    return f"~{ord(ch):X}~"

def _lower_char(ch: str) -> str:
    if ch == "I": return "ı"
    if ch == "İ": return "i"
    return ch.lower()

def _upper_char(ch: str) -> str:
    if ch == "ı": return "I"
    if ch == "i": return "İ"
    return ch.upper()

def elf_encode(text: str) -> str:
    """Encode text as unambiguous, delimiter-separated tokens; preserve case and Unicode."""
    out = []
    for ch in text:
        low = _lower_char(ch)
        if low in LETTER_TO_TOKEN and len(low) == 1:
            token = LETTER_TO_TOKEN[low]
            out.append(UPPER + token if ch.isupper() else token)
        elif ch == " ":
            out.append(SPACE)
        elif ch == "\n":
            out.append(NEWLINE)
        else:
            out.append(_escape(ch))
    return SEP.join(out)

def elf_decode(body: str) -> str:
    if body == "":
        return ""
    out = []
    for token in body.split(SEP):
        if token in (SPACE, NEWLINE):
            out.append(" " if token == SPACE else "\n")
        elif token.startswith(UPPER):
            base = token[1:]
            if base not in TOKEN_TO_LETTER:
                raise ElfFormatError(f"Geçersiz büyük harf token'ı: {token!r}")
            out.append(_upper_char(TOKEN_TO_LETTER[base]))
        elif len(token) >= 3 and token.startswith("~") and token.endswith("~"):
            try:
                cp = int(token[1:-1], 16)
                if cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
                    raise ValueError
                out.append(chr(cp))
            except ValueError as exc:
                raise ElfFormatError(f"Bozuk Unicode kaçışı: {token!r}") from exc
        elif token in TOKEN_TO_LETTER:
            out.append(TOKEN_TO_LETTER[token])
        else:
            raise ElfFormatError(f"Geçersiz token: {token!r}")
    return "".join(out)

def caesar_shift(text: str, shift: int) -> str:
    result = []
    for ch in text:
        low = _lower_char(ch)
        if len(low) == 1 and low in CHAR_TO_IDX:
            shifted = ALPHABET[(CHAR_TO_IDX[low] + shift) % N]
            result.append(_upper_char(shifted) if ch.isupper() else shifted)
        else:
            result.append(ch)
    return "".join(result)

def encode(text: str, shift: int = 3) -> str:
    return f"{VERSION}:{elf_encode(caesar_shift(text, shift))}"

def decode(payload: str, shift: int = 3) -> str:
    prefix = VERSION + ":"
    if not payload.startswith(prefix):
        raise ElfFormatError(f"Bu uygulama {VERSION}: formatını bekliyor.")
    return caesar_shift(elf_decode(payload[len(prefix):]), -shift)

def brute_force(payload: str):
    return [(s, decode(payload, s)) for s in range(N)]

def export_json(text: str, shift: int) -> str:
    return json.dumps({
        "format": VERSION, "shift": shift,
        "note": "Kodlama/obfuscation; güvenli şifreleme değildir.",
        "payload": encode(text, shift)
    }, ensure_ascii=False, indent=2)
