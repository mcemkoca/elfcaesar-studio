const $ = (id) => document.getElementById(id);
const send = (msg) => new Promise((res) => chrome.runtime.sendMessage(msg, (r) => res(r || { ok: false })));
function set(id, text, cls) { $(id).textContent = text; $(id).className = cls; }

async function refresh() {
  const s = await send({ type: "status", origin: "" });
  if (!s.ok) {
    set("app", s.error === "host_missing" ? "yardımcı yok" : "kapalı", "bad");
    set("pair", "—", ""); set("vault", "—", "");
    $("pairBtn").hidden = true; $("unpairBtn").hidden = true; $("openBtn").hidden = true;
    return;
  }
  set("app", `açık · ${s.version}`, "ok");
  set("pair", s.paired ? "eşleşti" : "eşleşmedi", s.paired ? "ok" : "warn");
  set("vault", s.vault_open ? "açık" : "kilitli", s.vault_open ? "ok" : "warn");
  $("pairBtn").hidden = !!s.paired;
  $("unpairBtn").hidden = !s.paired;
  $("openBtn").hidden = !(s.paired && !s.vault_open);
}

$("pairBtn").onclick = async () => {
  const code = String(Math.floor(1000 + Math.random() * 9000));
  $("code").textContent = code; $("codebox").hidden = false;
  $("pairBtn").disabled = true;
  const r = await send({ type: "associate", code });
  $("codebox").hidden = true; $("pairBtn").disabled = false;
  if (!r.ok) set("pair", r.error === "denied" ? "reddedildi" : "başarısız", "bad");
  refresh();
};
$("unpairBtn").onclick = async () => { await send({ type: "unpair" }); refresh(); };
$("openBtn").onclick = async () => { await send({ type: "open_app" }); window.close(); };
refresh();
