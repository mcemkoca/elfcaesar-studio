"""Kırılma süresi tablosu (Parola Laboratuvarı) ve kompakt satır (parola penceresi)."""
from __future__ import annotations

import tkinter as tk

from .cracktime import estimate, estimate_hw, elfc2_crack, HARDWARE, HARDWARE_ORDER
from .theme import F, PANEL, INPUT, LINE, FG, FG_2, MUTED, DIM, RED, ORANGE, AMBER, GREEN, CYAN, mix
from .widgets import Chip, Segmented

RISK_COLORS = {"critical": RED, "weak": ORANGE, "fair": AMBER, "strong": GREEN, "excellent": CYAN}
RISK_LABELS = {"critical": "KRİTİK", "weak": "ZAYIF", "fair": "ORTA", "strong": "GÜÇLÜ", "excellent": "ÇOK GÜÇLÜ"}
METHOD_COLORS = {"high": RED, "medium": AMBER, "low": GREEN}
METHOD_LABELS = {"high": "YÜKSEK RİSK", "medium": "DİKKAT", "low": "DÜŞÜK RİSK"}


def rate_text(rate: float) -> str:
    if rate < 1:
        return f"{rate * 3600:.0f} / saat"
    for value, name in ((1e9, "milyar"), (1e6, "milyon"), (1e3, "bin")):
        if rate >= value:
            n = rate / value
            return (f"{n:.1f}".replace(".", ",").rstrip("0").rstrip(",") + f" {name} / sn")
    return f"{rate:.0f} / sn"


HW_LABELS = {"rtx3060": "EV PC", "rtx4090": "OYUN PC", "cloud": "BULUT", "farm": "ÇİFTLİK"}


class CrackTable(tk.Frame):
    def __init__(self, parent, hardware="rtx4090", on_hardware=None):
        super().__init__(parent, bg=PANEL)
        self.hardware, self.on_hardware, self.password = hardware, on_hardware, ""
        top = tk.Frame(self, bg=PANEL)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="SALDIRGAN DONANIMI", bg=PANEL, fg=DIM, font=F["label"]).pack(side="left")
        self.hw_note = tk.Label(top, text="", bg=PANEL, fg=MUTED, font=F["tiny"])
        self.hw_note.pack(side="right")
        Segmented(top, [(k, HW_LABELS[k]) for k in HARDWARE_ORDER], self._set_hw, hardware).pack(side="left", padx=10)
        self.leak = tk.Frame(self, bg=PANEL)
        self.leak.pack(fill="x")
        self.rows = tk.Frame(self, bg=PANEL)
        self.rows.pack(fill="x")
        tk.Label(self, text="SALDIRI YÖNTEMLERİ", bg=PANEL, fg=DIM, font=F["label"], anchor="w").pack(fill="x", pady=(12, 4))
        self.methods = tk.Frame(self, bg=PANEL)
        self.methods.pack(fill="x")
        e = elfc2_crack()
        tk.Label(self, text=f"Karşılaştırma: ELFC2 kodlaması {e['guesses']} denemede, {e['text']} çözülür — şifreleme değildir.",
                 bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x", pady=(10, 0))
        tk.Label(self, text="Ortalama süre = olası parola sayısının yarısı ÷ saldırgan hızı. Hızlar ve kiralama ücretleri yaklaşık varsayımdır.",
                 bg=PANEL, fg=DIM, font=F["tiny"], anchor="w").pack(fill="x")
        self.update_password("")

    def _set_hw(self, hw):
        self.hardware = hw
        if self.on_hardware:
            self.on_hardware(hw)
        self.update_password(self.password)

    def update_password(self, password: str):
        self.password = password
        hw = HARDWARE[self.hardware]
        cost = f" · kiralama ≈ {hw['usd_hour']:.0f} $/saat" if hw["usd_hour"] else ""
        self.hw_note.configure(text=f"{hw['name']} · {hw['gear']}{cost}")
        for f in (self.leak, self.rows, self.methods):
            for ch in f.winfo_children():
                ch.destroy()
        for f in (self.leak, self.rows, self.methods):
            f.configure(height=1)  # boşalan çerçeve eski yüksekliğini korumasın
        if not password:
            tk.Label(self.rows, text="Parola girildiğinde seçili donanıma göre tahmini kırılma süresi burada görünür.",
                     bg=PANEL, fg=MUTED, font=F["small"], anchor="w").pack(fill="x", pady=6)
            return
        r = estimate_hw(password, self.hardware)
        if r["leak"]:
            lk = r["leak"]
            box = tk.Frame(self.leak, bg=mix(RED, PANEL, .85), highlightthickness=1, highlightbackground=mix(RED, PANEL, .5))
            box.pack(fill="x", pady=(0, 8))
            tk.Frame(box, bg=RED, width=3).pack(side="left", fill="y")
            t = tk.Frame(box, bg=box.cget("bg"))
            t.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            tk.Label(t, text=f"Sızıntı / yaygın parola listesinde: “{lk['base']}” · #{lk['rank']:,} sırada".replace(",", "."),
                     bg=box.cget("bg"), fg=RED, font=F["body_b"], anchor="w").pack(fill="x")
            tk.Label(t, text="Saldırganlar bu listeleri ve türevlerini (büyük harf, yıl, sembol, a→@) ilk saniyelerde dener. "
                     "Bu parola yeni kasa parolası olarak kabul edilmez.", bg=box.cget("bg"), fg=FG_2, font=F["tiny"],
                     anchor="w").pack(fill="x")
        head = tk.Frame(self.rows, bg=PANEL)
        head.pack(fill="x", pady=(0, 4))
        for text, w in (("SENARYO", 30), ("SALDIRGAN HIZI", 18), ("ORTALAMA KIRILMA SÜRESİ", 0)):
            tk.Label(head, text=text, bg=PANEL, fg=DIM, font=F["label"], width=w or None, anchor="w").pack(side="left")
        for row in r["scenarios"]:
            col = RISK_COLORS[row["risk"]]
            line = tk.Frame(self.rows, bg=INPUT, highlightthickness=1, highlightbackground=LINE)
            line.pack(fill="x", pady=2)
            tk.Frame(line, bg=col, width=3).pack(side="left", fill="y")
            name = tk.Frame(line, bg=INPUT, width=1)
            name.pack(side="left", padx=(10, 0), pady=5)
            tk.Label(name, text=row["name"], bg=INPUT, fg=FG, font=F["body_b"], width=27, anchor="w").pack(anchor="w")
            tk.Label(name, text=row["desc"], bg=INPUT, fg=DIM, font=F["tiny"], width=46, anchor="w").pack(anchor="w")
            tk.Label(line, text=rate_text(row["rate"]), bg=INPUT, fg=MUTED, font=F["mono_xs"], width=18, anchor="w").pack(side="left")
            tcol = tk.Frame(line, bg=INPUT)
            tcol.pack(side="left", padx=(6, 0))
            tk.Label(tcol, text=row["text"], bg=INPUT, fg=col, font=F["h3"], anchor="w").pack(anchor="w")
            if row.get("cost_text"):
                tk.Label(tcol, text=f"kiralama maliyeti ≈ {row['cost_text']}", bg=INPUT, fg=MUTED, font=F["tiny"], anchor="w").pack(anchor="w")
            Chip(line, RISK_LABELS[row["risk"]], col).pack(side="right", padx=10)
        for m in r["methods"]:
            col = METHOD_COLORS[m["level"]]
            line = tk.Frame(self.methods, bg=PANEL)
            line.pack(fill="x", pady=1)
            chip = Chip(line, METHOD_LABELS[m["level"]], col)
            chip.configure(width=12)
            chip.pack(side="left")
            tk.Label(line, text=m["name"], bg=PANEL, fg=FG_2, font=F["body_b"], width=30, anchor="w").pack(side="left", padx=8)
            tk.Label(line, text=f"{m['why']} — {m['desc']}", bg=PANEL, fg=MUTED, font=F["tiny"], anchor="w").pack(side="left")


def crack_summary(password: str) -> tuple[str, str]:
    """Parola penceresi için kısa satır ve renk."""
    if not password:
        return "", MUTED
    rows = {r["key"]: r for r in estimate(password)["scenarios"]}
    one, farm = rows["vault_1gpu"], rows["vault_farm"]
    return (f"ElfCaesar kasasına karşı tahmini kırılma: 1 GPU ≈ {one['text']} · 1.000 GPU ≈ {farm['text']}",
            RISK_COLORS[farm["risk"]])
