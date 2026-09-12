# -*- coding: utf-8 -*-
"""background_remover.py için hızlı otomatik test — sonuçları dosyaya yazar."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOG = os.path.join(os.environ["TEMP"], "br_test_result.txt")
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

# 1) GrabCut yedeği: sentetik görsel (üstte arka plan, ortada keskin kare)
img = Image.new("RGB", (160, 160), (0, 200, 0))
for x in range(50, 110):
    for y in range(50, 110):
        img.putpixel((x, y), (255, 0, 0))
out, note = br.remove_background(img, "u2net", None, False)
arr = np.array(out)
alpha = arr[..., 3]
log("1) grabcut cikti:", out.size, out.mode, "| note:", note)
log("   alpha range:", alpha.min(), alpha.max(),
    "| merkez opak:", bool(alpha[80, 80] > 200),
    "| kos seffaf:", bool(alpha[5, 5] < 100))
assert alpha[80, 80] > 200, "merkez seffaf kaldi"
assert alpha[5, 5] < 100, "kose opak kaldi"

# 2) rembg import durumu
log("2) REMBG_AVAILABLE:", br.REMBG_AVAILABLE)

# 3) GUI kurulumu (offscreen)
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
win = br.MainWindow()
win.resize(1100, 650)
win.show()

test_path = os.path.join(os.environ["TEMP"], "br_test_img.png")
img.save(test_path)
win.add_paths([test_path])
assert win.listw.count() == 1, "gorsel listeye eklenmedi"
log("3) liste:", win.listw.item(0).text())
win.canvas_orig.set_image(img)
win.canvas_result.set_image(out)
app.processEvents()
log("4) GUI OK")
log("TUM TESTLER BASARILI")
_logf.close()
