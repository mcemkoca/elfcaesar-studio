import os, sys, threading, time, json
sys.path.insert(0, "/home/claude/v6110")
from pathlib import Path
from studio_ui import runtime, browser_bridge as bb
from studio_ui.pwvault import Entry, PasswordVault
from studio_ui import pwgen, lifecycle
class App:
    def gen_policy(self, domain=""): return pwgen.Policy(length=20)
    def generate_for(self, domain="", via="", policy=None):
        pw = pwgen.generate(policy); lifecycle.add_generated(self._pv.meta, pw, domain, via); return pw
app = App(); app.prefs = {"browser_keys": []}
app._pv = PasswordVault(Path("/tmp/e2e/k.elfvault")); app._pv.create("Test-Ana-Parola-2026!")
app._pv.add(Entry("Elf Market", "ayse@ornek.com", "T-parola-1", "https://www.elfmarket.com"))
br = bb.BrowserBridge(app)
srv = runtime.InstanceServer(); srv.request_handler = br.handle; srv.start()
log = open("/tmp/e2e/server.log", "w")
while True:
    kind, payload = br.ui_tasks.get()
    if kind == "associate":
        browser, code, box, done = payload; box["ok"] = True; done.set(); print("associate", browser, code, file=log, flush=True)
    elif kind == "call":
        fn, box, done = payload
        try: box["result"] = fn()
        except Exception as exc: box["error"] = str(exc)
        done.set()
        print("call", file=log, flush=True)
    elif kind == "save_keys":
        app.prefs["browser_keys"] = payload
