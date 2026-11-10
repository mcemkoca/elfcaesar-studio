import os, sys, threading, time, json
sys.path.insert(0, "/home/claude/v6102")
from pathlib import Path
from studio_ui import runtime, browser_bridge as bb
from studio_ui.pwvault import Entry, PasswordVault
class App: pass
app = App(); app.prefs = {"browser_keys": []}
app._pv = PasswordVault(Path("/tmp/e2e/k.elfvault")); app._pv.create("Test-Ana-Parola-2026!")
app._pv.add(Entry("Trendyol", "ayse@gmail.com", "T-parola-1", "https://www.trendyol.com"))
br = bb.BrowserBridge(app)
srv = runtime.InstanceServer(); srv.request_handler = br.handle; srv.start()
log = open("/tmp/e2e/server.log", "w")
while True:
    kind, payload = br.ui_tasks.get()
    if kind == "associate":
        browser, code, box, done = payload; box["ok"] = True; done.set(); print("associate", browser, code, file=log, flush=True)
    elif kind == "save_keys":
        app.prefs["browser_keys"] = payload
