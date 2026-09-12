# -*- coding: utf-8 -*-
"""pythonw altinda calisma testi: stdout/stderr None iken uygulama kurulumu."""
import os
import sys

LOG = os.path.join(os.environ["TEMP"], "br_pythonw_result.txt")
_f = open(LOG, "w", encoding="utf-8")

def log(*a):
    msg = " ".join(str(x) for x in a)
    _f.write(msg + "\n")
    _f.flush()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

log("1) pythonw std:", type(sys.stdout).__name__, "|", type(sys.stderr).__name__)

# modul importu None-stream guard'i tetikler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import background_remover as br  # noqa: E402

log("2) import OK, guard sonrasi:", type(sys.stdout).__name__, "|", type(sys.stderr).__name__)

# print + stderr yazma (pythonw'de normalde cokerdi)
print("stdout'a yazim")
print("stderr'e yazim", file=sys.stderr)
import traceback  # noqa: E402
try:
    raise ValueError("test")
except ValueError:
    traceback.print_exc()
log("3) print/traceback OK")

# GUI kurulumu
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
win = br.MainWindow()
win.show()
app.processEvents()
log("4) GUI OK")
log("PYTHONW TEST BASARILI")
_f.close()
sys.exit(0)
