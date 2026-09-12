# -*- coding: utf-8 -*-
"""Sag tik menusu + Kaydet tusu aktiflestirme testi."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

LOG = os.path.join(os.environ["TEMP"], "br_menu_result.txt")
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

app = QApplication([])
win = br.MainWindow()
win.show()

# sentetik gorunus: gri arka plan + kirmizi kare
img = Image.new("RGB", (160, 160), (0, 180, 0))
for x in range(50, 110):
    for y in range(50, 110):
        img.putpixel((x, y), (255, 0, 0))

try:
    p = os.path.join(tmp, "br_menu_test.png")
    img.save(p)
    win.add_paths([p])

    # islenmemisken kaydet tusu kapali olmali
    log("1) islemeden once btn_save enabled:", win.btn_save.isEnabled())
    assert not win.btn_save.isEnabled()

    # GrabCut ile sonuc uret ve oggeye bagla
    result = br.grabcut_remove(img)
    d = win._item_data(win.listw.item(0))
    d["result"] = result
    win._set_item_data(win.listw.item(0), d)
    win._refresh_item_text(win.listw.item(0), d)
    win.listw.setCurrentRow(0)
    win._update_buttons()
    app.processEvents()
    log("2) isledikten sonra btn_save enabled:", win.btn_save.isEnabled())
    log("   item_data result var mi:", win._item_data(win.listw.item(0)).get("result") is not None)
    assert win.btn_save.isEnabled(), "cikti seciliyken Kaydet tuşu aktiflesmedi!"

    log("3) save_selected var:", hasattr(win, "save_selected"),
        "| _on_list_menu var:", hasattr(win, "_on_list_menu"),
        "| canvas contextMenuEvent var:", hasattr(win.canvas_result, "contextMenuEvent"))

    out = os.path.join(tmp, "br_menu_cikti.png")
    win._save_image(result, out)
    log("4) _save_image OK, mode:", Image.open(out).mode)

    log("TUM MENU TESTLERI BASARILI")
except Exception:
    import traceback
    log("HATA:")
    log(traceback.format_exc())
finally:
    _logf.close()
    sys.exit(0)

