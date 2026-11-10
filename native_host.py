"""ElfCaesar tarayıcı yardımcısı (native messaging host).

Tarayıcı bu programı eklenti adına başlatır; stdin/stdout üzerinden 4 bayt uzunluk + JSON mesajlaşır
ve istekleri yerel, belirteçli bağlantıyla çalışan ElfCaesar Studio'ya iletir. Kendisi hiçbir şey saklamaz.
"""
from __future__ import annotations

import json
import struct
import sys

from studio_ui import runtime

ALLOWED = {"status", "associate", "query", "get", "open_app"}
MAX_MSG = 1024 * 1024


def read_message(stream):
    head = stream.read(4)
    if len(head) < 4:
        return None
    (n,) = struct.unpack("<I", head)
    if n > MAX_MSG:
        raise ValueError("mesaj çok büyük")
    return json.loads(stream.read(n).decode("utf-8"))


def write_message(stream, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(data)))
    stream.write(data)
    stream.flush()


def handle(msg: dict, forward=runtime.request) -> dict:
    req = msg.get("request")
    if req not in ALLOWED:
        return {"ok": False, "error": "unknown_request"}
    payload = {k: msg[k] for k in ("request", "key", "origin", "id", "browser", "code") if k in msg}
    resp = forward(payload)
    if "rid" in msg:
        resp["rid"] = msg["rid"]
    return resp


def main():
    inp, out = sys.stdin.buffer, sys.stdout.buffer
    while True:
        try:
            msg = read_message(inp)
        except (ValueError, OSError):
            return 1
        if msg is None:
            return 0
        write_message(out, handle(msg))


if __name__ == "__main__":
    raise SystemExit(main())
