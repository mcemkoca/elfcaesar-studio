// ElfCaesar Parola Köprüsü — sayfa betiği: parola alanlarını bulur, ElfCaesar düğmesini ekler, doldurur, oltalamayı uyarır.
(() => {
  if (window.top !== window || window.__elfcaesar) return;
  window.__elfcaesar = true;
  // simge gömülü: web_accessible_resources kullanılmaz, siteler eklentinin kurulu olduğunu algılayamaz
  const ICON = "data:image/png;base64,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";
  const seen = new WeakSet();
  let warned = false;

  const send = (msg) => new Promise((res) => chrome.runtime.sendMessage(msg, (r) => res(r || { ok: false })));

  function visible(el) {
    const r = el.getBoundingClientRect();
    return r.width > 20 && r.height > 10 && getComputedStyle(el).visibility !== "hidden";
  }

  function userFieldFor(pw) {
    const scope = pw.form || document;
    const inputs = [...scope.querySelectorAll("input")].filter((i) => visible(i));
    const idx = inputs.indexOf(pw);
    const auto = inputs.find((i) => (i.autocomplete || "").includes("username"));
    if (auto) return auto;
    for (let i = idx - 1; i >= 0; i--) {
      const t = (inputs[i].type || "text").toLowerCase();
      if (["text", "email", "tel"].includes(t)) return inputs[i];
    }
    return null;
  }

  function setValue(el, value) {
    const proto = Object.getPrototypeOf(el);
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    el.focus();
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  const NEW_RX = /new|yeni|confirm|onay|tekrar|repeat|again|retype|register|kayit|kayıt|signup|sign-up|create/i;
  const CUR_RX = /current|old|eski|mevcut|existing/i;
  const attrs = (el) => [el.name, el.id, el.placeholder, el.getAttribute("aria-label")].filter(Boolean).join(" ");
  const pwFields = (scope) => [...(scope || document).querySelectorAll('input[type="password"]')].filter((i) => visible(i));
  function isCurrent(el) { return (el.autocomplete || "").includes("current-password") || CUR_RX.test(attrs(el)); }
  function isNewField(el) {
    if (isCurrent(el)) return false;
    if ((el.autocomplete || "").includes("new-password") || NEW_RX.test(attrs(el))) return true;
    const scope = el.form || document;
    return pwFields(scope).length >= 2 || NEW_RX.test((scope.getAttribute && (scope.getAttribute("action") || scope.id)) || "");
  }
  function rulesOf(el) {
    return { maxlength: el.maxLength > 0 ? el.maxLength : 0, minlength: el.minLength > 0 ? el.minLength : 0,
             passwordrules: el.getAttribute("passwordrules") || "", pattern: el.getAttribute("pattern") || "" };
  }

  // ---------- arayüz (Shadow DOM: sayfa stillerinden yalıtılmış)
  const host = document.createElement("elfcaesar-ui");
  host.style.cssText = "all:initial;position:absolute;top:0;left:0;z-index:2147483647";
  const root = host.attachShadow({ mode: "closed" });
  const style = document.createElement("style");
  style.textContent = `
    .btn{position:absolute;width:22px;height:22px;border-radius:6px;border:0;padding:0;cursor:pointer;
         background:#0f1a27 url(${ICON}) center/18px no-repeat;box-shadow:0 1px 3px rgba(0,0,0,.4)}
    .menu{position:absolute;min-width:260px;max-width:360px;background:#0f1a27;color:#e9f0f7;border:1px solid #b59cff;
          border-radius:10px;font:13px/1.4 "Segoe UI",system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.45);overflow:hidden}
    .head{padding:9px 12px;font:700 11px/1 Consolas,monospace;letter-spacing:.08em;color:#b59cff;border-bottom:1px solid #22364b}
    .item{padding:9px 12px;cursor:pointer;display:block;width:100%;text-align:left;background:none;border:0;color:inherit;font:inherit}
    .item:hover,.item:focus{background:#25415a;outline:none}
    .item b{display:block} .item span{color:#8a9db1;font-size:12px}
    .note{padding:10px 12px;color:#8a9db1;font-size:12px}
    .banner{position:fixed;left:0;right:0;top:0;padding:12px 18px;background:#5c1018;color:#fff;
            font:600 14px/1.4 "Segoe UI",system-ui,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.4);display:flex;gap:14px;align-items:center}
    .banner button{margin-left:auto;background:#fff;color:#5c1018;border:0;border-radius:6px;padding:6px 10px;font-weight:700;cursor:pointer}
    .item.gen b{color:#f4b65e}
    .save{position:fixed;right:18px;bottom:18px;width:340px;background:#0f1a27;color:#e9f0f7;border:1px solid #f4b65e;border-radius:12px;
          font:13px/1.45 "Segoe UI",system-ui,sans-serif;box-shadow:0 12px 34px rgba(0,0,0,.5);overflow:hidden}
    .save .head{color:#f4b65e}
    .save .txt{padding:10px 12px 4px} .save .txt b{color:#fff} .save .sub{padding:0 12px 10px;color:#8a9db1;font-size:12px}
    .save .row{display:flex;gap:8px;justify-content:flex-end;padding:0 12px 12px}
    .save button{border:0;border-radius:7px;padding:7px 12px;font:700 12px "Segoe UI",system-ui,sans-serif;cursor:pointer}
    .save .yes{background:#f4b65e;color:#1a1206} .save .no{background:#22364b;color:#e9f0f7}
  `;
  root.appendChild(style);
  document.documentElement.appendChild(host);
  let menu = null;

  function closeMenu() { if (menu) { menu.remove(); menu = null; } }
  document.addEventListener("mousedown", (e) => { if (!e.composedPath().includes(host)) closeMenu(); }, true);

  function place(el, target, dx, dy) {
    const r = target.getBoundingClientRect();
    el.style.left = `${r.left + window.scrollX + dx(r)}px`;
    el.style.top = `${r.top + window.scrollY + dy(r)}px`;
  }

  function phishBanner(look) {
    if (warned) return;
    warned = true;
    const b = document.createElement("div");
    b.className = "banner";
    b.innerHTML = `<span>⚠ ElfCaesar Oltalama Kalkanı: <b></b> sitesi, kasandaki <b></b> sitesini taklit ediyor olabilir. Parolanı GİRME.</span><button>Anladım</button>`;
    const bs = b.querySelectorAll("b");
    bs[0].textContent = look.fake; bs[1].textContent = look.real;
    b.querySelector("button").onclick = () => b.remove();
    root.appendChild(b);
  }

  function openNote(btn, text) {
    closeMenu();
    menu = document.createElement("div");
    menu.className = "menu";
    menu.innerHTML = `<div class="head">ELFCAESAR · PAROLA KASASI</div><div class="note"></div>`;
    menu.querySelector(".note").textContent = text;
    root.appendChild(menu);
    place(menu, btn, () => -236, (r) => r.height + 6);
  }

  async function openMenu(pw, btn) {
    closeMenu();
    menu = document.createElement("div");
    menu.className = "menu";
    menu.innerHTML = `<div class="head">ELFCAESAR · PAROLA KASASI</div><div class="note">Kasaya soruluyor…</div>`;
    root.appendChild(menu);
    place(menu, btn, () => -236, (r) => r.height + 6);
    if (isNewField(pw)) {
      const g = document.createElement("button");
      g.className = "item gen";
      g.innerHTML = "<b>✦ Güçlü parola öner</b><span>Sitenin kurallarına uyar, kasaya da yazılır</span>";
      g.onclick = (ev) => { if (ev.isTrusted) suggest(pw, btn); };
      menu.insertBefore(g, menu.querySelector(".note"));
    }
    const r = await send({ type: "query" });
    const note = menu && menu.querySelector(".note");
    if (!menu) return;
    if (!r.ok) {
      note.textContent = r.error === "not_paired" ? "Eklenti eşleşmemiş: araç çubuğundaki ElfCaesar simgesinden EŞLEŞTİR."
        : r.error === "host_missing" ? "ElfCaesar yardımcısı bulunamadı: ElfCaesar Studio'yu kur/yeniden kur."
        : r.error === "app_not_running" ? "ElfCaesar Studio açık değil. Uygulamayı aç ve parola kasasını aç." : `Hata: ${r.error}`;
      return;
    }
    if (r.lookalike) { note.textContent = `Bu site ${r.lookalike.real} değil! Parola verilmez.`; phishBanner(r.lookalike); return; }
    if (r.locked) {
      note.innerHTML = "Parola kasası kilitli. ";
      const open = document.createElement("button"); open.className = "item"; open.innerHTML = "<b>ElfCaesar'ı aç</b>";
      open.onclick = () => { send({ type: "open_app" }); closeMenu(); };
      menu.appendChild(open);
      return;
    }
    if (!r.entries.length) { note.textContent = isNewField(pw) ? `${r.domain} için kayıt yok; yukarıdan güçlü parola önerebilirim.` : `${r.domain} için kasada kayıt yok.`; return; }
    note.remove();
    for (const e of r.entries) {
      const it = document.createElement("button");
      it.className = "item";
      it.innerHTML = "<b></b><span></span>";
      it.querySelector("b").textContent = e.title;
      it.querySelector("span").textContent = e.username || "(kullanıcı adı yok)";
      it.onclick = async (ev) => {
        if (!ev.isTrusted) return; // yalnızca gerçek kullanıcı tıklaması
        const g = await send({ type: "get", id: e.id });
        closeMenu();
        if (!g.ok) {
          openNote(btn, g.error === "insecure_origin" ? "Bu sayfa şifresiz (http). Kayıt https olduğu için parola verilmedi."
            : g.error === "domain_mismatch" ? "Alan adı eşleşmedi; parola verilmedi." : `Hata: ${g.error}`);
          return;
        }
        const uf = userFieldFor(pw);
        if (uf && g.username) setValue(uf, g.username);
        setValue(pw, g.password);
      };
      menu.appendChild(it);
    }
  }

  async function suggest(pw, btn) {
    const r = await send({ type: "generate", rules: rulesOf(pw) });
    closeMenu();
    if (!r.ok) {
      openNote(btn, r.error === "locked" ? "Parola kasası kilitli: ElfCaesar'da kasayı aç."
        : r.error === "lookalike" ? "Bu site kasandaki bir siteyi taklit ediyor olabilir; parola önerilmedi."
        : r.error === "not_paired" ? "Eklenti eşleşmemiş: araç çubuğundaki ElfCaesar simgesinden EŞLEŞTİR." : `Hata: ${r.error}`);
      return;
    }
    const scope = pw.form || document;
    let targets = pwFields(scope).filter((i) => !isCurrent(i));
    if (!targets.length) targets = [pw];
    targets.forEach((t) => setValue(t, r.password));
    filledByUs = r.password;
    openNote(btn, `Güçlü parola yazıldı (${r.bits} bit) ve ElfCaesar'da “son üretilenler”e kaydedildi. Formu gönderince kasaya kaydetmeyi soracağım.`);
    setTimeout(closeMenu, 6000);
  }

  // ---------- gönderimde kaydet / güncelle
  let filledByUs = "", lastCapture = "", saveBox = null;
  function capture(scope) {
    const fields = pwFields(scope && scope.querySelectorAll ? scope : document);
    if (!fields.length) return;
    const fresh = fields.filter((f) => !isCurrent(f) && f.value);
    const pick = (fresh.length ? fresh : fields.filter((f) => f.value))[0];
    if (!pick || !pick.value) return;
    const uf = userFieldFor(fields[0]);
    const username = uf ? uf.value.trim() : "";
    const sig = `${username}\u0000${pick.value}`;
    if (sig === lastCapture) return;
    lastCapture = sig;
    send({ type: "stash", username, password: pick.value }).then((r) => { if (r && r.show) showSave(r); });
  }
  function showSave(r) {
    if (saveBox) saveBox.remove();
    saveBox = document.createElement("div");
    saveBox.className = "save";
    const head = r.state === "different" ? "PAROLA DEĞİŞMİŞ" : r.state === "pending_match" ? "DEĞİŞİM PLANI" : "YENİ HESAP";
    const yes = r.state === "different" ? "Güncelle" : r.state === "pending_match" ? "Onayla" : "Kaydet";
    const mk = (tag, cls, text) => { const el = document.createElement(tag); el.className = cls; if (text) el.textContent = text; return el; };
    const txt = mk("div", "txt"), sub = mk("div", "sub"), row = mk("div", "row");
    row.append(mk("button", "no", "Şimdi değil"), mk("button", "yes"));
    saveBox.append(mk("div", "head", `ELFCAESAR · ${head}`), txt, sub, row);
    const who = r.username ? `${r.username} · ${r.host}` : r.host;
    txt.textContent = r.state === "different" ? `“${r.title}” kaydındaki parola güncellensin mi?`
      : r.state === "pending_match" ? `“${r.title}” için hazırlanan yeni parola sitede kullanıldı. Değişim tamamlansın mı?`
      : r.state === "locked" ? "Parola kasası kilitli. ElfCaesar'da kasayı açıp Kaydet'e bas." : "Bu giriş ElfCaesar parola kasasına kaydedilsin mi?";
    sub.textContent = who + (r.state === "different" ? " · eski parola geçmişte saklanır" : "");
    const yb = saveBox.querySelector(".yes");
    yb.textContent = yes;
    yb.onclick = async (ev) => {
      if (!ev.isTrusted) return;
      const res = await send({ type: "save_stash" });
      if (res.ok) {
        txt.textContent = res.result === "created" ? "Kasaya kaydedildi ✓" : res.result === "updated" ? "Parola güncellendi ✓"
          : res.result === "confirmed" ? "Değişim tamamlandı ✓" : "Zaten kayıtlı ✓";
        sub.textContent = ""; saveBox.querySelector(".row").remove();
        setTimeout(() => { if (saveBox) { saveBox.remove(); saveBox = null; } }, 2500);
      } else {
        sub.textContent = res.error === "locked" ? "Kasa hâlâ kilitli: ElfCaesar'da kasayı aç, sonra tekrar Kaydet."
          : res.error === "insecure_origin" ? "Şifresiz (http) sayfalarda parola kaydedilmez." : `Kaydedilemedi: ${res.error}`;
      }
    };
    saveBox.querySelector(".no").onclick = (ev) => { if (!ev.isTrusted) return; send({ type: "drop_stash" }); saveBox.remove(); saveBox = null; };
    root.appendChild(saveBox);
  }
  document.addEventListener("submit", (e) => { if (e.isTrusted) capture(e.target); }, true);
  document.addEventListener("click", (e) => {
    if (!e.isTrusted) return;
    const b = e.target.closest && e.target.closest('button,input[type="submit"],[role="button"]');
    if (!b) return;
    const scope = b.form || b.closest("form") || document;
    if (pwFields(scope).some((f) => f.value)) setTimeout(() => capture(scope), 0);
  }, true);
  document.addEventListener("keydown", (e) => {
    if (e.isTrusted && e.key === "Enter" && e.target && e.target.type === "password") capture(e.target.form || document);
  }, true);
  // önceki sayfada gönderilmiş, henüz yanıtlanmamış kaydetme sorusu
  // (gönderim ile yeni sayfanın yüklenmesi yarışabilir: birkaç kez sor)
  [0, 1200, 3000].forEach((ms) => setTimeout(() => {
    if (saveBox) return;
    send({ type: "pending_save" }).then((r) => { if (r && r.show && !saveBox) showSave(r); });
  }, ms));

  function attach(pw) {
    if (seen.has(pw) || !visible(pw)) return;
    seen.add(pw);
    const btn = document.createElement("button");
    btn.className = "btn";
    btn.title = isNewField(pw) ? "ElfCaesar: güçlü parola öner" : "ElfCaesar ile doldur";
    root.appendChild(btn);
    const pos = () => place(btn, pw, (r) => r.width - 28, (r) => (r.height - 22) / 2);
    pos();
    window.addEventListener("resize", pos);
    window.addEventListener("scroll", pos, true);
    new ResizeObserver(pos).observe(pw);
    btn.addEventListener("click", (ev) => { ev.preventDefault(); if (ev.isTrusted) openMenu(pw, btn); });
    // sayfada parola alanı var: oltalama denetimi (eşleşmişse)
    if (!warned) send({ type: "query" }).then((r) => { if (r && r.ok && r.lookalike) phishBanner(r.lookalike); });
  }

  function scan() { document.querySelectorAll('input[type="password"]').forEach(attach); }
  scan();
  new MutationObserver(() => scan()).observe(document.documentElement, { childList: true, subtree: true });
})();
