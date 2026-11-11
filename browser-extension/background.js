// ElfCaesar Parola Köprüsü — arka plan: eklenti ↔ yerel yardımcı (native messaging) ↔ ElfCaesar Studio
const HOST = "com.dante.elfcaesar";

function browserName() {
  const ua = navigator.userAgent;
  if (ua.includes("Firefox/")) return "Mozilla Firefox";
  if (ua.includes("Edg/")) return "Microsoft Edge";
  if (ua.includes("OPR/")) return "Opera";
  if (navigator.brave) return "Brave";
  return "Google Chrome";
}

async function storedKey() {
  const { elfKey } = await chrome.storage.local.get("elfKey");
  return elfKey || "";
}

function native(msg) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST, msg, (resp) => {
        if (chrome.runtime.lastError || !resp) {
          resolve({ ok: false, error: "host_missing", detail: chrome.runtime.lastError && chrome.runtime.lastError.message });
        } else {
          resolve(resp);
        }
      });
    } catch (e) {
      resolve({ ok: false, error: "host_missing", detail: String(e) });
    }
  });
}

// ---- kaydetme bekleyen form (sayfa gönderilip yeni sayfaya geçilse de soru kaybolmasın)
const memStash = {};
const sessionStore = chrome.storage && chrome.storage.session;
async function getStash(tabId) {
  if (sessionStore) { const r = await sessionStore.get(`stash_${tabId}`); return r[`stash_${tabId}`] || null; }
  return memStash[tabId] || null;
}
async function setStash(tabId, v) {
  if (sessionStore) { if (v) await sessionStore.set({ [`stash_${tabId}`]: v }); else await sessionStore.remove(`stash_${tabId}`); }
  else if (v) memStash[tabId] = v; else delete memStash[tabId];
}
// kaba "aynı site" karşılaştırması (asıl alan adı doğrulamasını uygulama yapar)
function siteOf(host) {
  const p = host.toLowerCase().split(".");
  const two = ["com.tr", "org.tr", "net.tr", "gov.tr", "edu.tr", "k12.tr", "co.uk", "org.uk", "com.au", "co.jp", "com.br"];
  const n = p.length >= 3 && two.includes(p.slice(-2).join(".")) ? 3 : 2;
  return p.slice(-n).join(".");
}
const STASH_TTL = 3 * 60 * 1000;

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    const key = await storedKey();
    // origin her zaman tarayıcının bildirdiği gönderen sekmeden alınır; sayfa betiği değiştiremez
    const origin = sender.tab ? new URL(sender.tab.url).origin : (msg.origin || "");
    const tabId = sender.tab ? sender.tab.id : -1;
    if (msg.type === "associate") {
      const resp = await native({ request: "associate", browser: browserName(), code: msg.code });
      if (resp.ok && resp.key) await chrome.storage.local.set({ elfKey: resp.key });
      sendResponse(resp);
    } else if (msg.type === "unpair") {
      await chrome.storage.local.remove("elfKey");
      sendResponse({ ok: true });
    } else if (["status", "query", "get", "open_app"].includes(msg.type)) {
      sendResponse(await native({ request: msg.type, key, origin, id: msg.id }));
    } else if (msg.type === "generate") {
      const rules = msg.rules && typeof msg.rules === "object" ? msg.rules : {};
      sendResponse(await native({ request: "generate", key, origin, rules }));
    } else if (msg.type === "stash") {
      const username = String(msg.username || "").slice(0, 256);
      const password = String(msg.password || "").slice(0, 512);
      if (!password) { sendResponse({ show: false }); return; }
      const r = await native({ request: "check", key, origin, username, password });
      const state = r.ok ? r.state : (r.error === "locked" ? "locked" : "");
      const show = ["new", "different", "pending_match", "locked"].includes(state);
      await setStash(tabId, show ? { origin, username, password, state, title: r.title || "", t: Date.now() } : null);
      sendResponse({ show, state, title: r.title || "", host: new URL(origin).hostname, username });
    } else if (msg.type === "pending_save") {
      const st = await getStash(tabId);
      if (!st || Date.now() - st.t > STASH_TTL || siteOf(new URL(st.origin).hostname) !== siteOf(new URL(origin).hostname)) {
        if (st && Date.now() - st.t > STASH_TTL) await setStash(tabId, null);
        sendResponse({ show: false });
        return;
      }
      sendResponse({ show: true, state: st.state, title: st.title, host: new URL(st.origin).hostname, username: st.username });
    } else if (msg.type === "save_stash") {
      const st = await getStash(tabId);
      if (!st) { sendResponse({ ok: false, error: "expired" }); return; }
      // kayıt, parolanın YAZILDIĞI sayfanın adresiyle yapılır (sonraki sayfanın değil)
      const r = await native({ request: "save", key, origin: st.origin, username: st.username, password: st.password });
      if (r.ok) await setStash(tabId, null);
      sendResponse(r);
    } else if (msg.type === "drop_stash") {
      await setStash(tabId, null);
      sendResponse({ ok: true });
    } else {
      sendResponse({ ok: false, error: "unknown" });
    }
  })();
  return true;
});
