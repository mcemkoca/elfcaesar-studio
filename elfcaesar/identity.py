"""Recipient-based encrypted messaging and signed identity cards.

X25519 + HKDF-SHA256 + AES-256-GCM; Ed25519 signatures.
Private identity material is always stored inside the existing password-encrypted vault.
"""
from __future__ import annotations
import base64, hashlib, json, os
from pathlib import Path
from typing import Any

from .secure import seal_bytes, open_bytes, SecureFormatError, _atomic_write

IDENTITY_FORMAT = "ELFIDENTITY1"
CONTACT_FORMAT = "ELFCONTACT1"
MESSAGE_FORMAT = "ELFDM1"

class IdentityError(ValueError):
    pass

def _crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return X25519PrivateKey, X25519PublicKey, Ed25519PrivateKey, Ed25519PublicKey, Encoding, PrivateFormat, PublicFormat, NoEncryption, HKDF, hashes, AESGCM
    except ImportError as exc:
        raise RuntimeError("cryptography paketi gerekli.") from exc

def _b64(b: bytes) -> str: return base64.b64encode(b).decode("ascii")
def _unb64(s: str) -> bytes:
    try: return base64.b64decode(s, validate=True)
    except Exception as exc: raise IdentityError("Anahtar/paket biçimi bozuk.") from exc

def _pubraw(key) -> bytes:
    *_, Encoding, PrivateFormat, PublicFormat, NoEncryption, HKDF, hashes, AESGCM = _crypto()
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)

def _fingerprint(exchange_pub: bytes, sign_pub: bytes) -> str:
    return hashlib.sha256(b"ELFCAESAR-ID-v1\0" + exchange_pub + sign_pub).hexdigest()

def _contact_from_public(name: str, exchange_pub: bytes, sign_pub: bytes) -> dict[str, Any]:
    return {"format": CONTACT_FORMAT, "version": 1, "name": name.strip()[:80] or "ElfCaesar Contact",
            "x25519_public": _b64(exchange_pub), "ed25519_public": _b64(sign_pub),
            "fingerprint": _fingerprint(exchange_pub, sign_pub)}

def create_identity(name: str, password: str, identity_path: str | Path) -> dict[str, Any]:
    (XPriv, XPub, EPriv, EPub, Encoding, PrivateFormat, PublicFormat, NoEncryption, HKDF, hashes, AESGCM) = _crypto()
    xpriv, epriv = XPriv.generate(), EPriv.generate()
    xraw = xpriv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    eraw = epriv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    xpub, epub = _pubraw(xpriv.public_key()), _pubraw(epriv.public_key())
    private = {"format": IDENTITY_FORMAT, "version": 1, "name": name.strip()[:80] or "My identity",
               "x25519_private": _b64(xraw), "ed25519_private": _b64(eraw),
               "contact": _contact_from_public(name, xpub, epub)}
    sealed = seal_bytes(json.dumps(private, separators=(",", ":")).encode(), password,
                        kind="identity", filename=Path(identity_path).name, content_type="application/vnd.elfcaesar.identity")
    _atomic_write(Path(identity_path), sealed)
    return private["contact"]

def load_identity(identity_path: str | Path, password: str) -> dict[str, Any]:
    _, XPub, _, _, Encoding, PrivateFormat, PublicFormat, NoEncryption, _, _, _ = _crypto()
    raw, header = open_bytes(Path(identity_path).read_bytes(), password)
    if header.get("kind") != "identity": raise IdentityError("Bu dosya kimlik kasası değil.")
    try: data = json.loads(raw.decode("utf-8"))
    except Exception as exc: raise IdentityError("Kimlik dosyası bozuk.") from exc
    if data.get("format") != IDENTITY_FORMAT or data.get("version") != 1: raise IdentityError("Desteklenmeyen kimlik sürümü.")
    # Reconstruct and cross-check public keys to detect malformed identity payloads.
    XPriv, _, EPriv, _, *_ = _crypto()
    xp = XPriv.from_private_bytes(_unb64(data["x25519_private"]))
    ep = EPriv.from_private_bytes(_unb64(data["ed25519_private"]))
    contact = _contact_from_public(data.get("name", ""), _pubraw(xp.public_key()), _pubraw(ep.public_key()))
    if contact != data.get("contact"): raise IdentityError("Kimlik anahtarı doğrulaması başarısız.")
    return data

def export_contact(contact: dict[str, Any], path: str | Path) -> None:
    validate_contact(contact)
    _atomic_write(Path(path), json.dumps(contact, ensure_ascii=False, indent=2).encode("utf-8"))

def import_contact(path: str | Path) -> dict[str, Any]:
    try: data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc: raise IdentityError("Kişi kartı okunamadı.") from exc
    return validate_contact(data)

def validate_contact(contact: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contact, dict) or contact.get("format") != CONTACT_FORMAT or contact.get("version") != 1:
        raise IdentityError("Desteklenmeyen kişi kartı.")
    xp, ep = _unb64(contact.get("x25519_public", "")), _unb64(contact.get("ed25519_public", ""))
    if len(xp) != 32 or len(ep) != 32 or _fingerprint(xp, ep) != contact.get("fingerprint"):
        raise IdentityError("Kişi kartı parmak izi geçersiz.")
    return contact

def encrypt_for_contact(message: str, recipient: dict[str, Any], sender_identity: dict[str, Any] | None = None) -> str:
    (XPriv, XPub, EPriv, EPub, Encoding, PrivateFormat, PublicFormat, NoEncryption, HKDF, hashes, AESGCM) = _crypto()
    recipient = validate_contact(recipient)
    rpub = XPub.from_public_bytes(_unb64(recipient["x25519_public"]))
    ephemeral = XPriv.generate(); shared = ephemeral.exchange(rpub)
    salt, nonce = os.urandom(16), os.urandom(12)
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
               info=b"ELFCAESAR-DM-v1\0" + recipient["fingerprint"].encode()).derive(shared)
    header = {"format": MESSAGE_FORMAT, "version": 1, "recipient": recipient["fingerprint"],
              "ephemeral": _b64(_pubraw(ephemeral.public_key())), "salt": _b64(salt), "nonce": _b64(nonce)}
    aad = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    cipher = AESGCM(key).encrypt(nonce, message.encode("utf-8"), aad)
    body = {"header": header, "ciphertext": _b64(cipher)}
    if sender_identity:
        sender_contact = validate_contact(sender_identity["contact"])
        epriv = EPriv.from_private_bytes(_unb64(sender_identity["ed25519_private"]))
        signed = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        body["sender"] = sender_contact
        body["signature"] = _b64(epriv.sign(signed))
    return MESSAGE_FORMAT + "\n" + json.dumps(body, ensure_ascii=False, separators=(",", ":"))

def decrypt_from_contact(payload: str, identity: dict[str, Any], trusted_sender: dict[str, Any] | None = None) -> tuple[str, dict[str, Any] | None]:
    (XPriv, XPub, EPriv, EPub, Encoding, PrivateFormat, PublicFormat, NoEncryption, HKDF, hashes, AESGCM) = _crypto()
    try:
        magic, raw = payload.split("\n", 1); body = json.loads(raw); h = body["header"]
        if magic != MESSAGE_FORMAT or h.get("format") != MESSAGE_FORMAT or h.get("version") != 1: raise ValueError
        salt, nonce = _unb64(h["salt"]), _unb64(h["nonce"])
        eph = XPub.from_public_bytes(_unb64(h["ephemeral"]))
        if len(salt) != 16 or len(nonce) != 12: raise ValueError
    except Exception as exc: raise IdentityError("Şifreli mesaj paketi bozuk veya desteklenmiyor.") from exc
    own = validate_contact(identity["contact"])
    if h.get("recipient") != own["fingerprint"]: raise IdentityError("Bu mesaj farklı bir alıcıya gönderilmiş.")
    xpriv = XPriv.from_private_bytes(_unb64(identity["x25519_private"]))
    shared = xpriv.exchange(eph)
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
               info=b"ELFCAESAR-DM-v1\0" + own["fingerprint"].encode()).derive(shared)
    aad = json.dumps(h, sort_keys=True, separators=(",", ":")).encode()
    try: clear = AESGCM(key).decrypt(nonce, _unb64(body["ciphertext"]), aad).decode("utf-8")
    except Exception as exc: raise IdentityError("Mesaj açılamadı; paket değiştirilmiş veya anahtar uyuşmuyor.") from exc
    sender = body.get("sender")
    if sender or body.get("signature"):
        if not sender or not body.get("signature"): raise IdentityError("İmza alanları eksik.")
        sender = validate_contact(sender)
        if trusted_sender and sender["fingerprint"] != validate_contact(trusted_sender)["fingerprint"]:
            raise IdentityError("Gönderen parmak izi güvenilen kişiyle eşleşmiyor.")
        e_pub = EPub.from_public_bytes(_unb64(sender["ed25519_public"]))
        signed = {"header": body["header"], "ciphertext": body["ciphertext"]}
        try: e_pub.verify(_unb64(body["signature"]), json.dumps(signed, sort_keys=True, separators=(",", ":")).encode())
        except Exception as exc: raise IdentityError("Gönderen imzası geçersiz.") from exc
    return clear, sender
