# -*- coding: utf-8 -*-
"""Otomatik bagimlilik kurulum mantigi testi."""
import os
import sys

LOG = os.path.join(os.environ["TEMP"], "br_autoinst_result.txt")
_f = open(LOG, "w", encoding="utf-8")

def log(*a):
    msg = " ".join(str(x) for x in a)
    _f.write(msg + "\n")
    _f.flush()
    print(msg, flush=True)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log("1) modul importu (autostart kontrolu)...")
import background_remover as br  # noqa: E402
log("2) import OK — mevcut kurulumda _autostart_main no-op calismali")

missing = br._missing()
log("3) _missing():", missing)
assert missing == [], "tum paketler kurulu olmali"

# pip cagrisi mekanizmasi: zaten kurulu zararsiz paketle test
rc = br._pip_install(["six"])
log("4) _pip_install(['six']) donus kodu:", rc)
assert rc == 0, "pip cagrisi basarisiz"

# tablo dogru mu
log("5) _REQUIREMENTS anahtarlari:", sorted(br._REQUIREMENTS.keys()))
assert set(br._REQUIREMENTS.keys()) == {"PyQt6", "cv2", "numpy", "PIL", "rembg"}

log("AUTOINST TEST BASARILI")
_f.close()
sys.exit(0)
