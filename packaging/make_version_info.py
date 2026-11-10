"""studio_ui/version.py'den PyInstaller için Windows sürüm kaynağı (build/version_info.txt) üretir."""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ns: dict = {}
exec((ROOT / "studio_ui" / "version.py").read_text(encoding="utf-8"), ns)
nums = ([int(x) for x in re.findall(r"\d+", ns["APP_VERSION"])] + [0, 0, 0])[:3]
tup = tuple(nums + [int(ns.get("APP_BUILD", 0))])
text = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041F04B0', [
      StringStruct('CompanyName', '{ns["PUBLISHER"]}'),
      StringStruct('FileDescription', '{ns["APP_NAME"]}'),
      StringStruct('FileVersion', '{".".join(map(str, tup))}'),
      StringStruct('Comments', 'Bir Dante eseri'),
      StringStruct('InternalName', '{ns["EXE_NAME"]}'),
      StringStruct('LegalCopyright', '{ns["COPYRIGHT"]}'),
      StringStruct('OriginalFilename', '{ns["EXE_NAME"]}.exe'),
      StringStruct('ProductName', '{ns["APP_NAME"]}'),
      StringStruct('ProductVersion', '{ns["APP_VERSION"]}')])]),
    VarFileInfo([VarStruct('Translation', [1055, 1200])])
  ]
)
"""
out = ROOT / "build" / "version_info.txt"
out.parent.mkdir(exist_ok=True)
out.write_text(text, encoding="utf-8")
print(ns["APP_VERSION"] + " " + str(ns.get("APP_BUILD", 0)))
sys.exit(0)
