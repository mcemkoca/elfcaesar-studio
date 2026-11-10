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

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    const key = await storedKey();
    if (msg.type === "associate") {
      const resp = await native({ request: "associate", browser: browserName(), code: msg.code });
      if (resp.ok && resp.key) await chrome.storage.local.set({ elfKey: resp.key });
      sendResponse(resp);
    } else if (msg.type === "unpair") {
      await chrome.storage.local.remove("elfKey");
      sendResponse({ ok: true });
    } else if (["status", "query", "get", "open_app"].includes(msg.type)) {
      // origin her zaman tarayıcının bildirdiği gönderen sekmeden alınır; sayfa betiği değiştiremez
      const origin = sender.tab ? new URL(sender.tab.url).origin : (msg.origin || "");
      sendResponse(await native({ request: msg.type, key, origin, id: msg.id }));
    } else {
      sendResponse({ ok: false, error: "unknown" });
    }
  })();
  return true;
});
