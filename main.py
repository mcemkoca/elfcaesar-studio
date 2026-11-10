from elfcaesar.engine import encode, decode, brute_force
import argparse
p = argparse.ArgumentParser(description="ElfCaesar Studio CLI")
sub = p.add_subparsers(dest="cmd", required=True)
e = sub.add_parser("encode"); e.add_argument("text"); e.add_argument("--shift", type=int, default=3)
d = sub.add_parser("decode"); d.add_argument("payload"); d.add_argument("--shift", type=int, default=3)
b = sub.add_parser("brute"); b.add_argument("payload")
a = p.parse_args()
if a.cmd == "encode": print(encode(a.text, a.shift))
elif a.cmd == "decode": print(decode(a.payload, a.shift))
else:
    for shift, text in brute_force(a.payload): print(f"{shift:02d}  {text}")
