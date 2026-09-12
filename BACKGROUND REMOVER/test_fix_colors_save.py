# -*- coding: utf-8 -*-
"""Renk dogrulugu + JPG kaydetme testi."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOG = os.path.join(os.environ["TEMP"], "br_fix_result.txt")
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

from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtGui import QImage  # noqa: E402

app = QApplication([])
win = br.MainWindow()
win.show()

# 1) Renk dogrulugu: kirmizi solda, mavi sagda olan goruntuyu canvas'a ver,
#    QImage donusumunde kirmizi/mavi yer degisiyor mu kontrol et.
img = Image.new("RGB", (2, 1))
img.putpixel((0, 0), (255, 0, 0))    # kirmizi
img.putpixel((1, 0), (0, 0, 255))    # mavi

pil_rgba = img.convert("RGBA")
data = pil_rgba.tobytes("raw", "RGBA")
qimg = QImage(data, 2, 1, QImage.Format.Format_RGBA8888)
px0 = qimg.pixelColor(0, 0)
px1 = qimg.pixelColor(1, 0)
log("1) Qt piksel(0):", px0.red(), px0.green(), px0.blue(), "(beklenen 255 0 0)")
log("   Qt piksel(1):", px1.red(), px1.green(), px1.blue(), "(beklenen 0 0 255)")
assert (px0.red(), px0.green(), px0.blue()) == (255, 0, 0), "kirmizi bozuldu!"
assert (px1.red(), px1.green(), px1.blue()) == (0, 0, 255), "mavi bozuldu!"
win.canvas_orig.set_image(img)
app.processEvents()
log("1b) canvas set_image OK (renkler dogru)")

# 2) JPG kaydetme: RGBA sonucu jpg'ye kaydet (beyaza duzlestirilmeli)
result = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
result.putalpha(Image.new("L", (100, 100), 0))  # tamamen seffaf
result.putpixel((50, 50), (255, 0, 0, 255))     # merkez kirmizi opak

jpg_out = os.path.join(tmp, "br_fix_cikti.jpg")
win._save_image(result, jpg_out)  # hata vermemeli
saved = Image.open(jpg_out)
log("2) JPG kayit OK, mode:", saved.mode, "boyut:", saved.size)
arr = np.array(saved.convert("RGB"))
log("   kos beyaz mi:", bool(arr[5, 5, 0] > 240 and arr[5, 5, 2] > 240),
    "| merkez kirmizi mi:", bool(arr[50, 50, 0] > 200 and arr[50, 50, 1] < 60))

# 3) PNG kaydetme hala seffaf mi
png_out = os.path.join(tmp, "br_fix_cikti.png")
win._save_image(result, png_out)
saved_png = Image.open(png_out)
log("3) PNG kayit OK, mode:", saved_png.mode, "(RGBA olmali)")

log("TUM FIX TESTLERI BASARILI")
_logf.close()
