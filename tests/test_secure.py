import pytest
from elfcaesar.secure import seal_bytes, open_bytes, encrypt_message, decrypt_message, SecureFormatError

PASSWORD = 'KutupYildizi!2026-Mavi'

def test_message_roundtrip():
    msg = 'Merhaba Dünya! Çocuklar 😊\nGizli mesaj.'
    assert decrypt_message(encrypt_message(msg, PASSWORD), PASSWORD) == msg

def test_binary_file_roundtrip():
    data = bytes(range(256)) * 4
    sealed = seal_bytes(data, PASSWORD, kind='file', filename='scan.png', content_type='image/png')
    clear, header = open_bytes(sealed, PASSWORD)
    assert clear == data
    assert header['filename'] == 'scan.png'

def test_wrong_password_rejected():
    sealed = seal_bytes(b'private', PASSWORD)
    with pytest.raises(SecureFormatError): open_bytes(sealed, 'WrongPassword!2026')

def test_tampering_rejected():
    sealed = bytearray(seal_bytes(b'private', PASSWORD))
    sealed[-5] = ord('A') if sealed[-5] != ord('A') else ord('B')
    with pytest.raises((SecureFormatError, ValueError)): open_bytes(bytes(sealed), PASSWORD)

def test_short_password_rejected():
    with pytest.raises(ValueError): seal_bytes(b'x', 'short')

def test_randomized_envelopes():
    a = seal_bytes(b'same', PASSWORD)
    b = seal_bytes(b'same', PASSWORD)
    assert a != b
    assert open_bytes(a, PASSWORD)[0] == b'same'

def test_message_cannot_be_opened_as_file(tmp_path):
    from elfcaesar.secure import decrypt_file
    source = tmp_path / 'message.elmsg'
    source.write_bytes(seal_bytes(b'hello', PASSWORD, kind='message'))
    with pytest.raises(SecureFormatError): decrypt_file(source, tmp_path / 'out.txt', PASSWORD)

def test_identity_recipient_encryption_and_signature(tmp_path):
    from elfcaesar.identity import create_identity, load_identity, encrypt_for_contact, decrypt_from_contact
    a_path, b_path = tmp_path / 'a.elfid', tmp_path / 'b.elfid'
    a_contact = create_identity('Alice', PASSWORD, a_path)
    b_contact = create_identity('Bob', PASSWORD, b_path)
    alice = load_identity(a_path, PASSWORD)
    bob = load_identity(b_path, PASSWORD)
    payload = encrypt_for_contact('Gizli mesaj 🔐', b_contact, alice)
    clear, sender = decrypt_from_contact(payload, bob, a_contact)
    assert clear == 'Gizli mesaj 🔐'
    assert sender['fingerprint'] == a_contact['fingerprint']

def test_identity_wrong_recipient_rejected(tmp_path):
    from elfcaesar.identity import create_identity, load_identity, encrypt_for_contact, decrypt_from_contact, IdentityError
    a_path, b_path, c_path = tmp_path / 'a.elfid', tmp_path / 'b.elfid', tmp_path / 'c.elfid'
    a = create_identity('Alice', PASSWORD, a_path)
    create_identity('Bob', PASSWORD, b_path)
    c = load_identity(create_identity('Carol', PASSWORD, c_path) and c_path, PASSWORD)
    payload = encrypt_for_contact('private', a)
    with pytest.raises(IdentityError): decrypt_from_contact(payload, c)

def test_tampered_signed_message_rejected(tmp_path):
    from elfcaesar.identity import create_identity, load_identity, encrypt_for_contact, decrypt_from_contact, IdentityError
    a_path, b_path = tmp_path / 'a.elfid', tmp_path / 'b.elfid'
    a = load_identity(create_identity('Alice', PASSWORD, a_path) and a_path, PASSWORD)
    b_contact = create_identity('Bob', PASSWORD, b_path)
    b = load_identity(b_path, PASSWORD)
    payload = encrypt_for_contact('private', b_contact, a)
    import json
    magic, raw = payload.split('\n', 1)
    body = json.loads(raw)
    body['ciphertext'] = ('A' if body['ciphertext'][0] != 'A' else 'B') + body['ciphertext'][1:]
    payload = magic + '\n' + json.dumps(body, separators=(',', ':'))
    with pytest.raises(IdentityError): decrypt_from_contact(payload, b)

def test_contact_export_import_roundtrip(tmp_path):
    from elfcaesar.identity import create_identity, export_contact, import_contact
    contact = create_identity('Test', PASSWORD, tmp_path / 'test.elfid')
    path = tmp_path / 'test.elfcontact'
    export_contact(contact, path)
    assert import_contact(path) == contact

def test_signed_message_rejects_wrong_trusted_fingerprint(tmp_path):
    from elfcaesar.identity import create_identity, load_identity, encrypt_for_contact, decrypt_from_contact, IdentityError
    alice_path, bob_path, eve_path = tmp_path / 'alice.elfid', tmp_path / 'bob.elfid', tmp_path / 'eve.elfid'
    alice_contact = create_identity('Alice', PASSWORD, alice_path)
    bob_contact = create_identity('Bob', PASSWORD, bob_path)
    eve_contact = create_identity('Eve', PASSWORD, eve_path)
    alice = load_identity(alice_path, PASSWORD)
    bob = load_identity(bob_path, PASSWORD)
    payload = encrypt_for_contact('hello', bob_contact, alice)
    with pytest.raises(IdentityError): decrypt_from_contact(payload, bob, eve_contact)
