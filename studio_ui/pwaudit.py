"""Parola Denetimi, Domino (zincirleme ele geçirme) analizi ve oltalama (benzer alan adı) tespiti.

Tamamen çevrimdışı. Sızıntı kontrolü uygulamayla gelen listeyi kullanır; isteğe bağlı çevrim içi kontrol
(Have I Been Pwned, k-anonimlik) yalnızca kullanıcı açıkça isterse ve yalnızca SHA-1 özetinin ilk 5 karakteri gönderilerek yapılır.
"""
from __future__ import annotations

import hashlib
import time
import unicodedata
from collections import defaultdict

from . import leaks
from .pwvault import Entry, registrable_domain
from .security import password_strength

YEAR = 365 * 86400
WEIGHTS = {"leaked": 30, "reused": 22, "weak": 18, "similar": 10, "old": 6, "insecure_url": 6, "empty_user": 0}
LABELS = {"leaked": "Sızıntı listesinde", "reused": "Başka hesapta da kullanılıyor", "weak": "Zayıf",
          "similar": "Diğer parolalara çok benziyor", "old": "1 yıldan eski", "insecure_url": "Şifresiz bağlantı (http)"}
CRITICAL_DOMAINS = ("gmail.com", "google.com", "microsoft.com", "apple.com", "yandex.ru", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com", "yandex.com",
                    "yandex.com.tr", "proton.me", "protonmail.com", "mail.com")


def _skeleton(pw: str) -> str:
    """Benzerlik için iskelet: küçük harf, Türkçe katlama, leet çözümü, rakam/sembol atılır."""
    import re
    s = leaks.fold(pw)
    s = re.sub(r"^[\d\W_]+|[\d\W_]+$", "", s)
    return "".join(c for c in s.translate(leaks._LEET) if c.isalpha())


def audit(entries: list[Entry], now: float | None = None) -> dict:
    now = now or time.time()
    by_pw = defaultdict(list)
    by_skel = defaultdict(list)
    for e in entries:
        if e.password:
            by_pw[e.password].append(e)
            sk = _skeleton(e.password)
            if len(sk) >= 4:
                by_skel[sk].append(e)
    results = {}
    for e in entries:
        issues = []
        st = password_strength(e.password) if e.password else {"level": 0, "leak": None, "name": "Boş"}
        if st.get("leak") or leaks.is_blocked(e.password or ""):
            issues.append("leaked")
        if len(by_pw[e.password]) > 1:
            issues.append("reused")
        if st["level"] <= 1 and "leaked" not in issues:
            issues.append("weak")
        sk = _skeleton(e.password or "")
        if len(sk) >= 4 and len({x.password for x in by_skel[sk]}) > 1 and "reused" not in issues:
            issues.append("similar")
        if now - (e.changed or now) > YEAR:
            issues.append("old")
        if (e.url or "").lower().startswith("http://"):
            issues.append("insecure_url")
        risk = sum(WEIGHTS[i] for i in issues)
        results[e.id] = {"issues": issues, "risk": risk, "level": st["level"], "strength": st["name"]}
    n = len(entries) or 1
    penalty = sum(min(60, r["risk"]) for r in results.values()) / n
    score = max(0, round(100 - penalty * 1.4))
    counts = {k: sum(1 for r in results.values() if k in r["issues"]) for k in LABELS}
    return {"score": score, "entries": results, "counts": counts,
            "reuse_groups": [g for g in by_pw.values() if len(g) > 1]}


# ------------------------------------------------------------------ Domino analizi
def domino(entries: list[Entry]) -> list[dict]:
    """Bir hesap ele geçirilirse başka hangi hesaplar düşer?

    Kenarlar: (1) aynı parola → doğrudan, (2) e-posta hesabı → o e-postayı kullanıcı adı/kurtarma adresi olarak
    kullanan bütün hesaplar ('parolamı unuttum' ile sıfırlanabilir). Sonuç: en büyük etki alanına göre sıralı.
    """
    email_accounts = {}
    for e in entries:
        d = e.domain
        if d in CRITICAL_DOMAINS and "@" in (e.username or ""):
            email_accounts[e.username.casefold()] = e
        elif d in CRITICAL_DOMAINS and e.username:
            email_accounts[f"{e.username.casefold()}@{d}"] = e
    graph = defaultdict(set)
    by_pw = defaultdict(list)
    for e in entries:
        if e.password:
            by_pw[e.password].append(e.id)
    for ids in by_pw.values():
        for a in ids:
            graph[a] |= set(ids) - {a}
    for e in entries:
        for mail in {(e.username or "").casefold(), (e.recovery_email or "").casefold()}:
            src = email_accounts.get(mail)
            if src is not None and src.id != e.id:
                graph[src.id].add(e.id)
    out = []
    ids = {e.id: e for e in entries}
    for e in entries:
        seen, stack = {e.id}, [e.id]
        while stack:
            for nxt in graph[stack.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        fallen = [ids[i] for i in seen if i != e.id]
        if fallen:
            out.append({"entry": e, "fallen": fallen, "is_email": e in email_accounts.values()})
    return sorted(out, key=lambda d: (-len(d["fallen"]), d["entry"].title.casefold()))


# ------------------------------------------------------------------ Oltalama kalkanı
_CONFUSABLE = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "4": "a", "7": "t", "$": "s", "@": "a",
                             "ı": "i", "і": "i", "ο": "o", "а": "a", "е": "e", "р": "p", "с": "c", "у": "y", "х": "x",
                             "ѕ": "s", "ԁ": "d", "ɡ": "g", "ⅼ": "l"})


def _norm(label: str) -> str:
    s = unicodedata.normalize("NFKC", label.casefold()).translate(_CONFUSABLE)
    return s.replace("rn", "m").replace("vv", "w").replace("-", "")


def _lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def lookalike(host_or_url: str, known_domains) -> dict | None:
    """Ziyaret edilen alan adı, kasadaki gerçek bir alan adını taklit ediyor mu?"""
    d = registrable_domain(host_or_url)
    if not d or d in known_domains:
        return None
    host = host_or_url.casefold()
    name = d.split(".")[0]
    for k in known_domains:
        kn = k.split(".")[0]
        if len(kn) < 4:
            continue
        if _norm(name) == _norm(kn):
            return {"real": k, "fake": d, "why": "Harf benzeri karakterlerle taklit (ör. 0→o, rn→m, Kiril harfleri)"}
        if kn in name and name != kn:
            return {"real": k, "fake": d, "why": f"Gerçek adı içeren farklı bir alan adı: “{kn}” + ekler"}
        if f"{kn}." in host and d != k:
            return {"real": k, "fake": d, "why": "Gerçek ad yalnızca alt alan adında; asıl alan adı farklı"}
        if len(name) >= 5 and _lev(name, kn) == 1:
            return {"real": k, "fake": d, "why": "Tek harf farkıyla yazım hatası taklidi (typosquatting)"}
    return None


# ------------------------------------------------------------------ isteğe bağlı çevrim içi kontrol
def hibp_prefix(password: str) -> tuple[str, str]:
    # SHA-1, Pwned Passwords k-anonimlik protokolünün gereğidir; güvenlik amacıyla kullanılmaz.
    h = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()  # nosemgrep
    return h[:5], h[5:]


def hibp_count(password: str, fetch) -> int:
    """fetch(prefix) -> 'SUFFIX:COUNT' satırları. Parola veya tam özet asla gönderilmez."""
    prefix, suffix = hibp_prefix(password)
    for line in fetch(prefix).splitlines():
        s, _, c = line.strip().partition(":")
        if s == suffix:
            return int(c or 0)
    return 0
