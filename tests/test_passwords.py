"""6.10.0 Parola Kasası: kasa, içe aktarma, denetim, domino, oltalama, Shamir miras, baskı parolası, paylaşım."""
import time

import pytest

from elfcaesar.secure import SecureFormatError
from studio_ui import autotype, pwaudit, shamir
from studio_ui.pwvault import Entry, PasswordVault, parse_csv, parse_share, registrable_domain, share_payload

M = "kartal-gümüş-orman-ışık-2026"


def test_domains():
    assert registrable_domain("https://www.garantibbva.com.tr/giris") == "garantibbva.com.tr"
    assert registrable_domain("accounts.google.com") == "google.com"
    assert registrable_domain("http://login.e-devlet.gov.tr") == "e-devlet.gov.tr"


def test_vault_roundtrip_and_lock(tmp_path):
    v = PasswordVault(tmp_path / "k.elfvault")
    v.create(M)
    v.add(Entry("Gmail", "ali@gmail.com", "Gizli-Parola-123", "https://mail.google.com"))
    v.save()
    raw = (tmp_path / "k.elfvault").read_bytes()
    assert b"Gizli-Parola" not in raw and b"gmail" not in raw
    w = PasswordVault(tmp_path / "k.elfvault")
    with pytest.raises(SecureFormatError):
        w.unlock("yanlis-parola-uzun")
    assert w.unlock(M) and w.entries[0].username == "ali@gmail.com" and not w.decoy
    w.lock()
    assert not w.is_open and w.entries == []


def test_history_and_search(tmp_path):
    v = PasswordVault(tmp_path / "k.elfvault")
    v.create(M)
    e = v.add(Entry("Trendyol", "ayse", "eski-parola-1", "trendyol.com"))
    e.set_password("yeni-parola-2")
    assert e.history[0]["password"] == "eski-parola-1"
    v.add(Entry("Türk Telekom", "ayse", "x", "turktelekom.com.tr"))
    assert [x.title for x in v.search("trend")] == ["Trendyol"]
    assert v.suggest("tr") == ["Trendyol", "trendyol.com"] or "Trendyol" in v.suggest("tr")
    assert v.for_window("Trendyol – Giriş Yap - Google Chrome")[0].title == "Trendyol"


CHROME = "name,url,username,password,note\nGmail,https://accounts.google.com/,ali@gmail.com,Parola123!,\n" \
         "Trendyol,https://www.trendyol.com/giris,ali@gmail.com,Parola123!,\nBoş,https://x.com,,,\n"
FIREFOX = 'url,username,password,httpRealm,formActionOrigin,guid,timeCreated,timeLastUsed,timePasswordChanged\n' \
          '"https://www.sahibinden.com","ali","S4hib!nden2019",,"https://secure.sahibinden.com","{1}","1","1","1546300800000"\n'
BITWARDEN = "folder,favorite,type,name,notes,fields,reprompt,login_uri,login_username,login_password,login_totp\n" \
            ",,login,Hepsiburada,,,0,https://hepsiburada.com,ali,HB-uzun-parola-99,\n"


def test_import_formats(tmp_path):
    assert parse_csv(CHROME)[1].startswith("Chrome")
    assert parse_csv(FIREFOX)[1] == "Firefox"
    assert parse_csv(BITWARDEN)[1] == "Bitwarden"
    v = PasswordVault(tmp_path / "k.elfvault")
    v.create(M)
    r = v.import_csv(CHROME)
    assert r["added"] == 2 and r["skipped"] == 1
    assert v.import_csv(CHROME)["added"] == 0  # tekrar içe aktarma çoğaltmaz
    r = v.import_csv(FIREFOX)
    assert r["added"] == 1 and v.search("sahibinden")[0].changed == 1546300800
    v.import_csv(BITWARDEN)
    assert len(v.entries) == 4


def test_audit_and_domino(tmp_path):
    now = time.time()
    es = [Entry("Gmail", "ali@gmail.com", "Parola123!", "https://gmail.com"),
          Entry("Trendyol", "ali@gmail.com", "Parola123!", "https://trendyol.com"),
          Entry("Banka", "12345", "Kx9#mQ2v!Lp7@zR4", "https://garantibbva.com.tr"),
          Entry("Forum", "ali", "galatasaray1905", "http://forum.example.com"),
          Entry("Netflix", "ali@gmail.com", "Ormanda-Yuruyen-Kartal-88", "https://netflix.com")]
    es[2].changed = now - 2 * 365 * 86400
    a = pwaudit.audit(es, now)
    r = a["entries"]
    assert "reused" in r[es[0].id]["issues"] and "leaked" in r[es[3].id]["issues"]
    assert "old" in r[es[2].id]["issues"] and "insecure_url" in r[es[3].id]["issues"]
    assert not r[es[4].id]["issues"] and 0 <= a["score"] < 100
    d = pwaudit.domino(es)
    top = d[0]
    assert top["entry"].title == "Gmail" and {e.title for e in top["fallen"]} >= {"Trendyol", "Netflix"}


def test_lookalike():
    known = {"garantibbva.com.tr", "paypal.com", "trendyol.com"}
    assert pwaudit.lookalike("https://paypa1.com/login", known)["real"] == "paypal.com"
    assert pwaudit.lookalike("garantibbva-guvenlik.com", known)["real"] == "garantibbva.com.tr"
    assert pwaudit.lookalike("trendyol.com.giris-yap.xyz", known)["real"] == "trendyol.com"
    assert pwaudit.lookalike("https://www.trendyol.com/sepet", known) is None
    assert pwaudit.lookalike("wikipedia.org", known) is None


def test_hibp_kanonymity():
    pre, suf = pwaudit.hibp_prefix("password")
    assert pre == "5BAA6" and len(suf) == 35
    assert pwaudit.hibp_count("password", lambda p: f"0000:1\n{suf}:9659365") == 9659365


def test_shamir():
    secret = bytes(range(32))
    parts = shamir.split_text(secret, 3, 5)
    assert len(parts) == 5
    assert shamir.combine_text(parts[1:4]) == secret
    assert shamir.combine_text([parts[0], parts[4], parts[2]]) == secret
    with pytest.raises(ValueError):
        shamir.combine_text(parts[:2])
    bad = parts[0][:-3] + ("AAA" if not parts[0].endswith("AAA") else "BBB")
    with pytest.raises(ValueError):
        shamir.decode_share(bad)
    two = [shamir.split(secret, 3, 5)[i] for i in (0, 1)]
    assert shamir.combine(two) != secret  # eşik altı bilgi vermez


def test_miras_recovery(tmp_path):
    v = PasswordVault(tmp_path / "k.elfvault")
    v.create(M)
    v.add(Entry("Banka", "ali", "Cok-Gizli-Banka-Parolasi"))
    parts = v.setup_miras(2, 3, ["Annem", "Kardeşim", "Avukat"])
    assert v.miras_path.exists()
    v.add(Entry("Yeni", "x", "sonradan-eklenen"))
    v.save()  # miras kasası güncel kalır
    got = PasswordVault.recover_miras(v.miras_path, [parts[2], parts[0]])
    assert {e.title for e in got} == {"Banka", "Yeni"}


def test_duress(tmp_path):
    real, fake = tmp_path / "k.elfvault", tmp_path / "yedek.elfvault"
    v = PasswordVault(real)
    v.create(M)
    v.add(Entry("Banka", "ali", "gercek"))
    v.save()
    d = PasswordVault(fake)
    d.create("baskı-altında-açılan-2026")
    d.add(Entry("Forum", "ali", "onemsiz"))
    d.save()
    w = PasswordVault(real)
    assert w.unlock("baskı-altında-açılan-2026", decoy_path=fake) and w.decoy and w.entries[0].title == "Forum"
    w2 = PasswordVault(real)
    assert w2.unlock(M, decoy_path=fake) and not w2.decoy and w2.entries[0].title == "Banka"


def test_share_payload():
    e = Entry("Wi-Fi", "", "ev-agi-parolasi", notes="5 GHz")
    got, note = parse_share(share_payload(e, "misafirler için"))
    assert got.password == "ev-agi-parolasi" and note == "misafirler için"
    assert parse_share("merhaba") is None


def test_autotype_sequence():
    e = Entry("x", "ali", "p@ss")
    assert autotype.sequence(e) == [("text", "ali"), ("key", autotype.VK_TAB), ("text", "p@ss")]
    assert autotype.sequence(e, "pass", submit=True) == [("text", "p@ss"), ("key", autotype.VK_RETURN)]


def test_window_title_strips_browser_and_email_domino():
    v = PasswordVault.__new__(PasswordVault)
    v.entries = [Entry("Gmail", "a@gmail.com", "p1", "https://accounts.google.com"), Entry("Trendyol", "a@gmail.com", "p2", "https://trendyol.com"),
                 Entry("Netflix", "a@gmail.com", "Bahar2024!", "https://netflix.com"), Entry("Spotify", "a@gmail.com", "Bahar2025!", "spotify.com")]
    assert [e.title for e in v.for_window("Trendyol – Giriş Yap - Google Chrome")] == ["Trendyol"]
    d = pwaudit.domino(v.entries)
    assert d[0]["entry"].title == "Gmail" and len(d[0]["fallen"]) == 3
    a = pwaudit.audit(v.entries)["entries"]
    assert "similar" in a[v.entries[2].id]["issues"]


def test_backups_and_restore(tmp_path):
    v = PasswordVault(tmp_path / "k.elfvault")
    v.create(M)
    v.add(Entry("A", "a", "pa"))
    v.save()
    v.add(Entry("B", "b", "pb"))
    v.save()  # 5 dk içinde ikinci yedek oluşmaz
    assert len(v.list_backups()) == 1
    v._backup(min_gap=0)
    assert len(v.list_backups()) == 2
    oldest = v.list_backups()[-1]
    assert v.restore_backup(oldest, M) == 0  # ilk yedek: kasa oluşturulduğu an (boş)
    with pytest.raises(SecureFormatError):
        v.restore_backup(oldest, "baska-parola-uzun")


def test_cloud_folder_merge(tmp_path):
    """İki bilgisayar aynı OneDrive dosyasını kullanıyor: değişiklikler kaybolmadan birleşir."""
    p = tmp_path / "OneDrive" / "k.elfvault"
    a = PasswordVault(p)
    a.create(M)
    shared = a.add(Entry("Gmail", "ali", "eski"))
    gone = a.add(Entry("Silinecek", "x", "y"))
    a.save()
    b = PasswordVault(p)
    b.unlock(M)
    # PC-B: yeni kayıt + Gmail parolası değişir + bir kayıt siler
    b.add(Entry("Netflix", "ali", "n1"))
    b.get(shared.id).set_password("yeni-B")
    b.remove(gone.id)
    time.sleep(0.01)
    b.save()
    # PC-A (eski görünümle): kendi yeni kaydını ekleyip kaydeder → B'nin değişiklikleri ezilmez
    a.add(Entry("Spotify", "ali", "s1"))
    a.save()
    assert a.last_merge["added"] == 1 and a.last_merge["updated"] == 1 and a.last_merge["removed"] == 1
    c = PasswordVault(p)
    c.unlock(M)
    titles = {e.title for e in c.entries}
    assert titles == {"Gmail", "Netflix", "Spotify"}
    assert c.search("gmail")[0].password == "yeni-B"


def test_conflict_copy_merge(tmp_path):
    p = tmp_path / "k.elfvault"
    a = PasswordVault(p)
    a.create(M)
    a.add(Entry("A", "a", "1"))
    a.save()
    other = PasswordVault(tmp_path / "k-DESKTOP-2.elfvault")
    other.create(M)
    other.add(Entry("B", "b", "2"))
    other.save()
    assert [x.name for x in a.conflict_files()] == ["k-DESKTOP-2.elfvault"]
    r = a.merge_file(a.conflict_files()[0])
    assert r["added"] == 1 and {e.title for e in a.entries} == {"A", "B"}
