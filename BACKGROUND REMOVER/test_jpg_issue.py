# -*- coding: utf-8 -*-
"""JPG hatasını yeniden üretme testi."""
import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOG = os.path.join(os.environ["TEMP"], "br_jpg_result.txt")
_logf = open(LOG, "w", encoding="utf-8")

def log(*a):
    msg = " ".join(str(x) for x in a)
    _logf.write(msg + "\n")
    _logf.flush()
    print(msg, flush=True)

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import background_remover as br  # noqa: E402

tmp = os.environ["TEMP"]
jpg_path = os.path.join(tmp, "br_test_kaynak.jpg")
jpg_cmyk = os.path.join(tmp, "br_test_cmyk.jpg")

# CMYK jpg + normal jpg oluştur
Image.new("RGB", (100, 100), (10, 20, 30)).save(jpg_path, quality=92)
Image.new("CMYK", (100, 100), (10, 20, 30, 5)).save(jpg_cmyk, quality=92)

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
win = br.MainWindow()
win.show()

# 1) JPG yükleme testi
win.add_paths([jpg_path, jpg_cmyk])
log("1) yuklenen:", win.listw.count(), "dosya (beklenen 2)")

# 2) isleme
item = win.listw.item(0)
d = win._item_data(item)
try:
    result, note = br.remove_background(d["original"], "u2net", None, False)
    log("2) isleme OK:", note)
except Exception:
    log("2) isleme HATA:", traceback.format_exc(limit=2))

# 3) kaydetme: RGBA sonucu .jpg olarak kaydet (kullanicinin senaryosu)
try:
    result.save(jpg_path.replace(".jpg", "_cikti.jpg"))
    log("3) RGBA->JPG direkt kayit OK")
except Exception as exc:
    log("3) RGBA->JPG HATA:", type(exc).__name__, str(exc))

# 4) _background_image beyaz secimde mi RGB donuyor?
win.cmb_bg.setCurrentText("Beyaz")
bg_img = win._background_image(result)
log("4) Beyaz seciminde mode:", bg_img.mode)

_logf.close()
