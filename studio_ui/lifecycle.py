"""Parola Yaşam Döngüsü: değişim planı, süreç takibi ve geçmiş.

Bir parolanın yolculuğu:  oluşturuldu → (risk tespit edildi) → değiştirilmeli → değişim sürüyor → değiştirildi.

• Değişim planı: her kayıt için nedenler (site ihlali, sızıntı, tekrar, zayıf, hatırlatma süresi, yaş) ve öncelik.
• Değişim süreci: yeni parola önce "bekleyen" olarak saklanır (sitedeki eski parola hâlâ geçerlidir, kaybolmaz);
  kullanıcı sitede değiştirdiğini onaylayınca yeni parola asıl parola olur, eskisi geçmişe girer.
• Zaman çizelgesi ve puan geçmişi kasanın içinde (şifreli) tutulur; dışarı hiçbir şey gönderilmez.
NIST SP 800-63B'ye uygun olarak, risk yokken zorunlu periyodik değişim dayatılmaz; hatırlatma kullanıcı isteğiyle açılır.
"""
from __future__ import annotations

import time

from . import pwaudit
from .pwvault import Entry

DAY = 86400
REASONS = {
    # anahtar: (öncelik, etiket)
    "site_breach": (95, "Site veri ihlali yaşadı"),
    "hibp": (90, "Parola çevrim içi sızıntı veritabanında"),
    "leaked": (85, "Parola sızıntı listesinde"),
    "reused": (65, "Başka hesapta da kullanılıyor"),
    "weak": (55, "Zayıf parola"),
    "rotation_due": (35, "Yenileme zamanı geldi"),
    "similar": (25, "Diğer parolalara çok benziyor"),
    "old": (15, "1 yıldan eski"),
    "insecure_url": (10, "Şifresiz bağlantı (http)"),
}
URGENT = 80
STATES = {"pending": "Değişim sürüyor", "urgent": "Acil", "recommended": "Önerilen", "snoozed": "Ertelendi", "ok": "Güvende"}
ROTATE_CHOICES = [(0, "Yalnızca risk varsa"), (90, "90 günde bir"), (180, "180 günde bir"), (365, "Yılda bir")]


def hibp_valid(e: Entry) -> bool:
    return bool(e.hibp) and abs(e.hibp.get("changed", -1) - (e.changed or 0)) < 1e-6


def record_hibp(e: Entry, count: int, now: float | None = None):
    e.hibp = {"count": int(count), "at": now or time.time(), "changed": e.changed}
    e.modified = now or time.time()


def plan(entries: list[Entry], catalog=None, now: float | None = None) -> dict:
    now = now or time.time()
    audit = pwaudit.audit(entries, now=now)
    items = []
    for e in entries:
        reasons = []
        res = audit["entries"].get(e.id, {"issues": []})
        if catalog is not None:
            st = catalog.status(e)
            if st and st["open"]:
                b = st["open"][0]
                from .breaches import fmt_count, fmt_date
                reasons.append({"key": "site_breach", "label": REASONS["site_breach"][1],
                                "detail": f"{b['t']} · {fmt_date(b['bd'])} · {fmt_count(b['c'])} hesap", "breach": b["n"]})
        if hibp_valid(e) and e.hibp.get("count", 0) > 0:
            reasons.append({"key": "hibp", "label": REASONS["hibp"][1], "detail": f"{e.hibp['count']:,} kez görülmüş".replace(",", ".")})
        for k in res["issues"]:
            if k in REASONS and not (k == "leaked" and any(r["key"] == "hibp" for r in reasons)):
                reasons.append({"key": k, "label": REASONS[k][1], "detail": ""})
        if e.rotate_days and now - (e.changed or now) > e.rotate_days * DAY:
            days = int((now - e.changed) / DAY)
            reasons.append({"key": "rotation_due", "label": REASONS["rotation_due"][1], "detail": f"{days} gündür aynı"})
        prio = max((REASONS[r["key"]][0] for r in reasons), default=0)
        if prio and e.domain in pwaudit.CRITICAL_DOMAINS:
            prio += 5  # e-posta hesabı düşerse diğerleri de düşer (Domino)
        if e.pending:
            state = "pending"
        elif not reasons:
            state = "ok"
        elif e.snooze_until > now and prio < URGENT:
            state = "snoozed"
        else:
            state = "urgent" if prio >= URGENT else "recommended"
        items.append({"entry": e, "reasons": reasons, "priority": prio + (200 if state == "pending" else 0), "state": state})
    order = {"pending": 0, "urgent": 1, "recommended": 2, "snoozed": 3, "ok": 4}
    items.sort(key=lambda x: (order[x["state"]], -x["priority"], (x["entry"].title or "").casefold()))
    counts = {k: sum(1 for i in items if i["state"] == k) for k in order}
    breached = sum(1 for i in items if any(r["key"] == "site_breach" for r in i["reasons"]))
    score = max(0, audit["score"] - min(30, breached * 8))
    return {"items": items, "counts": counts, "score": score, "audit": audit, "breached": breached}


# ------------------------------------------------------------------ değişim süreci
def start_change(e: Entry, new_password: str, reason: str = "", now: float | None = None):
    now = now or time.time()
    e.pending = {"password": new_password, "since": now, "reason": reason}
    e.modified = now


def confirm_change(meta: dict, e: Entry, now: float | None = None) -> bool:
    if not e.pending:
        return False
    now = now or time.time()
    reason = e.pending.get("reason", "")
    e.set_password(e.pending["password"])
    e.pending = {}
    e.breach_ack = []
    e.modified = now
    log_event(meta, "changed", e, reason, now)
    return True


def cancel_change(e: Entry, now: float | None = None):
    e.pending = {}
    e.modified = now or time.time()


def snooze(e: Entry, days: int = 7, now: float | None = None):
    now = now or time.time()
    e.snooze_until = now + days * DAY
    e.modified = now


def ack_breach(e: Entry, breach_name: str, now: float | None = None):
    if breach_name and breach_name not in e.breach_ack:
        e.breach_ack = list(e.breach_ack) + [breach_name]
        e.modified = now or time.time()


# ------------------------------------------------------------------ zaman çizelgesi, puan, üretici geçmişi
def log_event(meta: dict, kind: str, e: Entry | None, detail: str = "", now: float | None = None):
    tl = list(meta.get("timeline", []))
    tl.append({"t": now or time.time(), "kind": kind, "id": e.id if e else "", "title": e.title if e else "",
               "detail": detail[:120]})
    meta["timeline"] = tl[-500:]


def record_score(meta: dict, score: int, now: float | None = None) -> bool:
    now = now or time.time()
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    log = list(meta.get("score_log", []))
    if log and log[-1]["d"] == day:
        if log[-1]["s"] == score:
            return False
        log[-1] = {"d": day, "s": score}
    else:
        log.append({"d": day, "s": score})
    meta["score_log"] = log[-365:]
    return True


def add_generated(meta: dict, password: str, domain: str = "", via: str = "uygulama", now: float | None = None):
    """Üretilen parolalar kasada saklanır: kaydetmeyi unutsan da sitede kullandığın parola kaybolmaz."""
    hist = [h for h in meta.get("gen_history", []) if h.get("p") != password]
    hist.insert(0, {"p": password, "t": now or time.time(), "d": domain, "via": via})
    meta["gen_history"] = hist[:30]


def entry_timeline(meta: dict, e: Entry) -> list[dict]:
    """Bir kaydın yolculuğu: oluşturma, parola değişimleri, olaylar (en yeni üstte)."""
    ev = [{"t": e.created, "text": "Kayıt oluşturuldu" + (f" ({e.source})" if e.source else "")}]
    for h in e.history:
        ev.append({"t": h.get("until", 0), "text": "Parola değiştirildi (eskisi geçmişte)"})
    if e.pending:
        ev.append({"t": e.pending.get("since", 0), "text": "Yeni parola hazır, sitede değiştirilmesi bekleniyor"})
    if e.hibp:
        c = e.hibp.get("count", 0)
        ev.append({"t": e.hibp.get("at", 0), "text": "Çevrim içi sızıntı kontrolü: " +
                   ("temiz" if not c else f"{c:,} kez sızmış".replace(",", "."))})
    for x in meta.get("timeline", []):
        if x.get("id") == e.id and x.get("kind") != "changed":
            ev.append({"t": x["t"], "text": x.get("detail") or x["kind"]})
    return sorted(ev, key=lambda x: -x["t"])


def stats(meta: dict, now: float | None = None) -> dict:
    now = now or time.time()
    tl = meta.get("timeline", [])
    changed_30 = sum(1 for x in tl if x.get("kind") == "changed" and now - x["t"] < 30 * DAY)
    log = meta.get("score_log", [])
    first = next((x["s"] for x in log if now - time.mktime(time.strptime(x["d"], "%Y-%m-%d")) < 31 * DAY), None)
    last = log[-1]["s"] if log else None
    return {"changed_30d": changed_30, "score_then": first, "score_now": last, "series": [x["s"] for x in log[-60:]]}
