"""Authenticated file/message encryption for ElfCaesar Studio.
Uses AES-256-GCM with scrypt-derived keys. ELFC2 is intentionally separate.
"""
from __future__ import annotations
import base64, json, os, secrets, string
from pathlib import Path
from typing import Any

FORMAT = "ELFVAULT1"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**15, 8, 1
MAX_PASSWORD_BYTES = 1024

class SecureFormatError(ValueError): pass
class SecureDependencyError(RuntimeError): pass

def _crypto():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
        from cryptography.hazmat.primitives import hashes
        return AESGCM, Scrypt, hashes
    except ImportError as exc:
        raise SecureDependencyError("Güvenli kasa için cryptography paketi gerekli. requirements.txt içinden kurun.") from exc

def _derive(password: str, salt: bytes, Scrypt, hashes) -> bytes:
    if not isinstance(password, str) or len(password.encode('utf-8')) < 12:
        raise ValueError("Parola en az 12 UTF-8 bayt olmalı; uzun bir parola cümlesi tercih edin.")
    if len(password.encode('utf-8')) > MAX_PASSWORD_BYTES:
        raise ValueError("Parola çok uzun.")
    return Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(password.encode('utf-8'))

def seal_bytes(data: bytes, password: str, *, kind: str = "file", filename: str = "", content_type: str = "application/octet-stream") -> bytes:
    AESGCM, Scrypt, hashes = _crypto()
    if not isinstance(data, bytes): raise TypeError("data bytes olmalı")
    if kind not in {"file", "message", "bundle", "identity"}: raise ValueError("Geçersiz içerik türü")
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _derive(password, salt, Scrypt, hashes)
    header = {"format": FORMAT, "kdf": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
              "cipher": "AES-256-GCM", "kind": kind, "filename": Path(filename).name,
              "content_type": content_type, "salt": base64.b64encode(salt).decode(),
              "nonce": base64.b64encode(nonce).decode()}
    aad = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    ciphertext = AESGCM(key).encrypt(nonce, data, aad)
    envelope = {"header": header, "ciphertext": base64.b64encode(ciphertext).decode()}
    return (FORMAT + "\n" + json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))).encode("utf-8")

def open_bytes(blob: bytes, password: str) -> tuple[bytes, dict[str, Any]]:
    AESGCM, Scrypt, hashes = _crypto()
    try:
        text = blob.decode("utf-8")
        magic, raw = text.split("\n", 1)
        env = json.loads(raw); h = env["header"]
        if magic != FORMAT or h.get("format") != FORMAT: raise ValueError
        if (h.get("cipher"), h.get("kdf"), h.get("n"), h.get("r"), h.get("p")) != ("AES-256-GCM", "scrypt", SCRYPT_N, SCRYPT_R, SCRYPT_P): raise ValueError
        salt, nonce = base64.b64decode(h["salt"], validate=True), base64.b64decode(h["nonce"], validate=True)
        ciphertext = base64.b64decode(env["ciphertext"], validate=True)
        if len(salt) != 16 or len(nonce) != 12 or len(ciphertext) < 16: raise ValueError
    except Exception as exc:
        raise SecureFormatError("Dosya bozuk veya desteklenmeyen ELF Vault biçiminde.") from exc
    key = _derive(password, salt, Scrypt, hashes)
    aad = json.dumps(h, sort_keys=True, separators=(",", ":")).encode()
    try: clear = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except Exception as exc: raise SecureFormatError("Parola yanlış veya dosya değiştirilmiş. Kimlik doğrulama başarısız.") from exc
    return clear, h

def encrypt_file(source: str | Path, destination: str | Path, password: str) -> Path:
    src, dst = Path(source), Path(destination)
    raw = src.read_bytes()
    sealed = seal_bytes(raw, password, kind="file", filename=src.name)
    _atomic_write(dst, sealed)
    return dst

def decrypt_file(source: str | Path, destination: str | Path, password: str) -> Path:
    src, dst = Path(source), Path(destination)
    clear, header = open_bytes(src.read_bytes(), password)
    if header.get("kind") != "file": raise SecureFormatError("Bu paket dosya kasası değil.")
    _atomic_write(dst, clear)
    return dst

def encrypt_message(message: str, password: str) -> str:
    return seal_bytes(message.encode("utf-8"), password, kind="message", content_type="text/plain; charset=utf-8").decode("utf-8")

def decrypt_message(payload: str, password: str) -> str:
    clear, h = open_bytes(payload.encode("utf-8"), password)
    if h.get("kind") != "message": raise SecureFormatError("Bu paket mesaj değil; dosya/kasa paketi.")
    try: return clear.decode("utf-8")
    except UnicodeDecodeError as exc: raise SecureFormatError("Mesaj UTF-8 değil.") from exc

def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    try:
        with open(tmp, "xb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try: tmp.unlink(missing_ok=True)
        except OSError: pass

def generate_passphrase(words: int = 5) -> str:
    # Local generator: cryptographically random word-like tokens, no downloaded dictionary.
    if not 4 <= words <= 10: raise ValueError("Kelime sayısı 4–10 arasında olmalı")
    alphabet = string.ascii_lowercase + string.digits
    return "-".join(''.join(secrets.choice(alphabet) for _ in range(5)) for _ in range(words))
