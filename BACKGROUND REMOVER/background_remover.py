# -*- coding: utf-8 -*-
"""
Arka Plan Kaldırıcı — PyQt6 tabanlı arka plan kaldırma uygulaması.

Ana yöntem : rembg (U²-Net / ISNet tabanlı AI modelleri)
Yedek      : OpenCV GrabCut (rembg yoksa / model indirilemezse otomatik devreye girer)
"""
from __future__ import annotations

import os
import subprocess
import sys
import traceback

# ---------------------------------------------------------------------------
# OTOMATIK BAGIMLILIK KURULUMU
# Import hatalarini yonet: eksik kutuphane varsa pip ile sessizce kur,
# ardindan sureci bastan baslat.
# ---------------------------------------------------------------------------
_REQUIREMENTS = {
    "PyQt6": "PyQt6",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "PIL": "pillow",
    "rembg": "rembg[cpu]",
}

def _pip_install(pkgs):
    """pip install'i pencere acmadan calistirir; donus kodunu verir."""
    return subprocess.call(
        [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *pkgs],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def _missing():
    """Kurulu olmayan paket modullerini listeler."""
    import importlib.util
    return [mod for mod in _REQUIREMENTS if importlib.util.find_spec(mod) is None]

def _autostart_main():
    if _missing():
        _pip_install([_REQUIREMENTS[m] for m in _missing()])
        if _missing():
            # kurulum basarisiz -> ikinci deneme (requirements.txt ile)
            _pip_install(["-r", os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")])
        if _missing():
            # hala eksik varsa kullaniciya gorunur hata verip cik
            # (PyQt6 da eksik olabilecegi icin ctypes kullaniliyor)
            msg = ("Gerekli kütüphaneler kurulamadı:\n"
                   + ", ".join(_missing())
                   + "\n\nLütfen internet bağlantınızı kontrol edip tekrar deneyin.\n"
                   + "Manuel kurulum: pip install -r requirements.txt")
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg, "Arka Plan Kaldırıcı", 0x10)
            except Exception:
                pass
            sys.exit(1)
        # tum bagimliliklar kuruldu -> sureci taze baslat
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

_autostart_main()
# ---------------------------------------------------------------------------

# pythonw.exe ile calisirken stdout/stderr None olur; print()/traceback
# AttributeError ile cokmasini engellemek icin devnull'a yonlendir.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import cv2
import numpy as np
from PIL import Image

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDropEvent,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QPen,
    QColor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------- rembg import
try:
    from rembg import remove as _rembg_remove, new_session as _rembg_new_session

    REMBG_AVAILABLE = True
except Exception:  # ImportError veya başka bir hata -> GrabCut yedeğine düş
    _rembg_remove = None
    _rembg_new_session = None
    REMBG_AVAILABLE = False

APP_TITLE = "Arka Plan Kaldırıcı"
SUPPORTED_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")

MODELS = [
    ("u2net",              "U²-Net (Genel — varsayılan)"),
    ("isnet-general-use",  "ISNet (Genel — daha yeni)"),
    ("u2net_human_seg",    "U²-Net İnsan (portre)"),
    ("silueta",            "Silueta (hafif, hızlı)"),
]


# =================================================================== Çekirdek
def grabcut_remove(img: Image.Image) -> Image.Image:
    """OpenCV GrabCut ile arka plan kaldırma (çevrimdışı yedek yöntem)."""
    rgb = np.array(img.convert("RGB"))
    h, w = rgb.shape[:2]

    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)

    mx, my = max(1, int(w * 0.04)), max(1, int(h * 0.04))
    rect = (mx, my, w - 2 * mx, h - 2 * my)
    cv2.grabCut(rgb, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)

    binary = np.where(
        (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0
    ).astype(np.uint8)

    # Kenarları yumuşat: hafif erozyon + bulanıklaştırma
    binary = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(binary, (5, 5), 0)

    out = np.dstack([rgb, alpha])
    return Image.fromarray(out, "RGBA")


def remove_background(
    img: Image.Image,
    model: str,
    session,
    alpha_matting: bool,
) -> tuple[Image.Image, str]:
    """Tek görselin arka planını kaldırır. Dönüş: (sonuç, yöntem_notu)."""
    if REMBG_AVAILABLE:
        try:
            kwargs = {}
            if alpha_matting:
                kwargs["alpha_matting"] = True
                kwargs["alpha_matting_foreground_threshold"] = 240
                kwargs["alpha_matting_background_threshold"] = 15
                kwargs["alpha_matting_erode_size"] = 8
            out = _rembg_remove(img, session=session, **kwargs)
            return out.convert("RGBA"), "AI ({})".format(model)
        except Exception as exc:
            print(f"[uyarı] rembg başarısız ({exc}) -> GrabCut yedeği", file=sys.stderr)
    return grabcut_remove(img), "GrabCut (yedek)"


# ============================================================== GUI yardımcı
class CheckerCanvas(QWidget):
    """Dama deseni üzerinde PNG şeffaflığını gösteren tuval."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._pixmap: QPixmap | None = None
        self.setMinimumSize(280, 220)
        self.setAcceptDrops(True)

    def set_image(self, pil_img):
        if pil_img is None:
            self._pixmap = None
        else:
            pil = pil_img if pil_img.mode in ("RGB", "RGBA") else pil_img.convert("RGBA")
            data = pil.tobytes("raw", "RGBA")
            # Format_RGBA8888: bellekte R,G,B,A sırasi bekler (PIL ile birebir uyumlu).
            # Format_ARGB32 kullanirsak R ve B kanallari yer degisir (renkler bozulur).
            qimg = QImage(data, pil.width, pil.height, QImage.Format.Format_RGBA8888)
            self._pixmap = QPixmap.fromImage(qimg.copy())
        self.update()

    def has_image(self) -> bool:
        return self._pixmap is not None

    # --- sürükle bırak -----------------------------------------------------
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        win = self.window()
        if paths and hasattr(win, "add_paths"):
            win.add_paths(paths)

    # --- boyama ------------------------------------------------------------
    def contextMenuEvent(self, event):
        """Sağ tık: gorunurde goruntusu varsa 'Farklı Kaydet…' menusu."""
        if not self.has_image():
            return
        menu = QMenu(self)
        act_save = menu.addAction("💾  Farklı Kaydet…")
        chosen = menu.exec(event.globalPos())
        if chosen is act_save:
            win = self.window()
            if hasattr(win, "save_selected"):
                win.save_selected()

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()

        # arka plan: koyu + dama deseni
        p.fillRect(self.rect(), QColor(38, 38, 42))
        cell = 12
        p.setPen(Qt.PenStyle.NoPen)
        for y in range(0, h, cell):
            for x in range(0, w, cell):
                if ((x // cell) + (y // cell)) % 2 == 0:
                    p.fillRect(x, y, cell, cell, QColor(52, 52, 58))

        # başlık
        p.setPen(QColor(160, 160, 170))
        f = self.font(); f.setPointSize(9)
        p.setFont(f)
        p.drawText(self.rect().adjusted(8, 4, -8, -4),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, self.title)

        if self._pixmap is None:
            p.setPen(QColor(110, 110, 120))
            f2 = self.font(); f2.setPointSize(10)
            p.setFont(f2)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Görsel yok\nSürükleyip bırakın veya\n'Dosya Aç' ile seçin")
            p.end()
            return

        scaled = self._pixmap.scaled(
            w - 16, h - 34,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (w - scaled.width()) // 2
        y = 26 + (h - 34 - scaled.height()) // 2
        p.drawPixmap(x, y, scaled)

        # ince çerçeve
        p.setPen(QPen(QColor(90, 90, 100), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(x - 1, y - 1, scaled.width() + 1, scaled.height() + 1)
        p.end()


class ProcessWorker(QThread):
    """Seçilen tüm görselleri sırayla işleyen arka plan iş parçacığı."""

    progress = pyqtSignal(int, int, str)          # sıradaki index, toplam, durum metni
    item_done = pyqtSignal(int, object, str)      # index, sonuç PIL imajı, yöntem notu
    item_failed = pyqtSignal(int, str)            # index, hata metni
    finished_all = pyqtSignal()

    def __init__(self, items, model: str, alpha_matting: bool, parent=None):
        super().__init__(parent)
        self.items = items            # [(index, path, PIL original), ...]
        self.model = model
        self.alpha_matting = alpha_matting
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        session = None
        if REMBG_AVAILABLE:
            try:
                session = _rembg_new_session(self.model)
            except Exception as exc:
                print(f"[uyarı] oturum oluşturulamadı ({exc})", file=sys.stderr)
                session = None

        total = len(self.items)
        for i, (idx, _path, original) in enumerate(self.items):
            if self._stop:
                break
            self.progress.emit(i, total, "İşleniyor: " + os.path.basename(_path))
            try:
                result, note = remove_background(
                    original, self.model, session, self.alpha_matting
                )
                self.item_done.emit(idx, result, note)
            except Exception as exc:
                traceback.print_exc()
                self.item_failed.emit(idx, str(exc))
        self.finished_all.emit()


# ================================================================ Ana pencere
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 700)
        self.setAcceptDrops(True)

        # item.setData(Qt.ItemDataRole.UserRole) -> dict(path, original, ...)
        self._worker: ProcessWorker | None = None

        self._build_ui()
        self._build_menu()
        self._update_buttons()
        self.statusBar().showMessage(
            "Hazır." + ("  |  rembg (AI) kullanılabilir." if REMBG_AVAILABLE
                        else "  |  UYARI: rembg bulunamadı — GrabCut yedeği kullanılacak.")
        )

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)

        # ---- sol: liste ------------------------------------------------
        left = QVBoxLayout()
        left.addWidget(QLabel("Görseller"))
        self.listw = QListWidget()
        self.listw.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.listw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.listw.customContextMenuRequested.connect(self._on_list_menu)
        self.listw.itemSelectionChanged.connect(self._on_selection_changed)
        left.addWidget(self.listw)

        btns_col = QVBoxLayout()
        self.btn_open = QPushButton("Dosya Aç…")
        self.btn_remove_sel = QPushButton("Listeden Kaldır")
        self.btn_clear = QPushButton("Listeyi Temizle")
        self.btn_open.clicked.connect(self._on_open)
        self.btn_remove_sel.clicked.connect(self._on_remove_selected)
        self.btn_clear.clicked.connect(self._on_clear)
        for b in (self.btn_open, self.btn_remove_sel, self.btn_clear):
            btns_col.addWidget(b)
        left.addLayout(btns_col)

        # ---- sağ: üst kontroller + önizleme ----------------------------
        right = QVBoxLayout()

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Model:"))
        self.cmb_model = QComboBox()
        for _mid, label in MODELS:
            self.cmb_model.addItem(label, _mid)
        self.cmb_model.setEnabled(REMBG_AVAILABLE)
        ctrl.addWidget(self.cmb_model)

        self.chk_matting = QCheckBox("Kenar yumuşatma (alpha matting)")
        self.chk_matting.setToolTip("Daha yumuşak kenarlar; işlem biraz yavaşlar.")
        ctrl.addWidget(self.chk_matting)

        ctrl.addWidget(QLabel("Arka plan:"))
        self.cmb_bg = QComboBox()
        self.cmb_bg.addItems(["Şeffaf", "Beyaz", "Siyah", "Özel renk…"])
        ctrl.addWidget(self.cmb_bg)
        ctrl.addStretch(1)
        right.addLayout(ctrl)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.canvas_orig = CheckerCanvas("Orijinal")
        self.canvas_result = CheckerCanvas("Sonuç")
        split.addWidget(self.canvas_orig)
        split.addWidget(self.canvas_result)
        split.setSizes([590, 590])
        right.addWidget(split, 1)

        actions = QHBoxLayout()
        self.btn_process = QPushButton("🪄  Arka Planı Kaldır")
        self.btn_process.setDefault(True)
        self.btn_save = QPushButton("💾  Kaydet (Ctrl+S)")
        self.btn_save_all = QPushButton("💾  Tümünü Kaydet…")
        self.btn_process.clicked.connect(self._on_process)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save_all.clicked.connect(self._on_save_all)
        actions.addWidget(self.btn_process)
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_save_all)
        actions.addStretch(1)
        right.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        right.addWidget(self.progress)

        root.addLayout(left, 1)
        root.addLayout(right, 3)
        self.setCentralWidget(central)

    def _build_menu(self):
        m = self.menuBar().addMenu("&Dosya")
        act_open = QAction("Dosya Aç…", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self._on_open)
        act_quit = QAction("Çıkış", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        m.addAction(act_open)
        m.addAction(act_quit)

        ms = self.menuBar().addMenu("&Yardım")
        act_about = QAction("Hakkında", self)
        act_about.triggered.connect(self._on_about)
        ms.addAction(act_about)

    # ------------------------------------------------------------ yardımcı
    def _item_data(self, item: QListWidgetItem) -> dict:
        return item.data(Qt.ItemDataRole.UserRole) or {}

    def _set_item_data(self, item: QListWidgetItem, data: dict):
        item.setData(Qt.ItemDataRole.UserRole, data)

    def _refresh_item_text(self, item: QListWidgetItem, data: dict):
        name = os.path.basename(data["path"])
        if data.get("result") is not None:
            tag = "  ✔ " + (data.get("note") or "tamam")
        elif data.get("error"):
            tag = "  ✖ hata"
        else:
            tag = "  (bekliyor)"
        item.setText(name + tag)

    def _update_buttons(self):
        busy = self._worker is not None and self._worker.isRunning()
        has_items = self.listw.count() > 0
        self.btn_process.setEnabled(has_items and not busy)
        cur = self.listw.currentItem()
        self.btn_save.setEnabled(
            not busy and cur is not None
            and (self._item_data(cur).get("result") is not None)
        )
        self.btn_save_all.setEnabled(
            not busy and any(
                self._item_data(self.listw.item(i)).get("result") is not None
                for i in range(self.listw.count())
            )
        )

    def add_paths(self, paths):
        added = 0
        for path in paths:
            if not os.path.isfile(path) or not path.lower().endswith(SUPPORTED_EXT):
                continue
            try:
                original = Image.open(path).convert("RGB")
            except Exception as exc:
                QMessageBox.warning(self, APP_TITLE, f"{path} açılamadı:\n{exc}")
                continue
            item = QListWidgetItem()
            data = {"path": path, "original": original, "result": None,
                    "note": None, "error": None}
            self._set_item_data(item, data)
            self._refresh_item_text(item, data)
            self.listw.addItem(item)
            added += 1
        if added:
            self.statusBar().showMessage(f"{added} görsel eklendi.")
        if self.listw.currentItem() is None and self.listw.count():
            self.listw.setCurrentRow(0)
        self._update_buttons()

    # ------------------------------------------------------------ olaylar
    def _on_open(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Görsel seç", "",
            "Görseller (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff);;"
            "Tüm dosyalar (*)"
        )
        if paths:
            self.add_paths(paths)

    def _on_remove_selected(self):
        for item in reversed(self.listw.selectedItems()):
            self.listw.takeItem(self.listw.row(item))
        self._on_selection_changed()

    def _on_clear(self):
        self.listw.clear()
        self.canvas_orig.set_image(None)
        self.canvas_result.set_image(None)
        self._update_buttons()

    def _on_selection_changed(self):
        item = self.listw.currentItem()
        if item is None:
            self.canvas_orig.set_image(None)
            self.canvas_result.set_image(None)
        else:
            d = self._item_data(item)
            self.canvas_orig.set_image(d.get("original"))
            self.canvas_result.set_image(d.get("result"))
        self._update_buttons()

    def _on_process(self):
        if self._worker is not None and self._worker.isRunning():
            return
        targets = []
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            d = self._item_data(item)
            d["error"] = None
            self._set_item_data(item, d)
            self._refresh_item_text(item, d)
            targets.append((i, d["path"], d["original"]))
        if not targets:
            return

        model = self.cmb_model.currentData() or "u2net"
        self._worker = ProcessWorker(targets, model, self.chk_matting.isChecked())
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.item_done.connect(self._on_worker_done)
        self._worker.item_failed.connect(self._on_worker_failed)
        self._worker.finished_all.connect(self._on_worker_finished)
        self.progress.setRange(0, max(1, len(targets)))
        self.progress.setValue(0)
        self._update_buttons()
        if not REMBG_AVAILABLE:
            self.statusBar().showMessage("rembg yok — GrabCut yedeği kullanılıyor.")
        self._worker.start()

    def _on_worker_progress(self, i, total, text):
        self.statusBar().showMessage(
            f"[{i + 1}/{total}] {text}" +
            ("" if REMBG_AVAILABLE else "  (GrabCut yedeği)")
        )
        self.progress.setValue(i)

    def _on_worker_done(self, idx, result, note):
        item = self.listw.item(idx)
        if item is None:
            return
        d = self._item_data(item)
        bg = self._background_image(result)
        d["result"] = bg
        d["note"] = note
        self._set_item_data(item, d)
        self._refresh_item_text(item, d)
        if item is self.listw.currentItem():
            self.canvas_result.set_image(bg)
        self.progress.setValue(idx + 1)
        self._update_buttons()

    def _on_worker_failed(self, idx, err):
        item = self.listw.item(idx)
        if item is None:
            return
        d = self._item_data(item)
        d["error"] = "hata"
        self._set_item_data(item, d)
        self._refresh_item_text(item, d)
        self.statusBar().showMessage(f"İşlem hatası: {err[:120]}")
        self.progress.setValue(idx + 1)

    def _on_worker_finished(self):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self._worker = None
        self._update_buttons()
        self.statusBar().showMessage("İşlem tamamlandı.")

    # ------------------------------------------------------------ kaydetme
    def save_selected(self):
        """Sağ tık menüsünden ve Kaydet düğmesinden çağrılır."""
        self._on_save()

    def _on_list_menu(self, pos):
        """Listede sağ tık menüsü."""
        item = self.listw.itemAt(pos)
        if item is None:
            return
        # sağ tıklanan öğeyi seçili yap (kaydet düğmesi ve önizleme güncellensin)
        self.listw.setCurrentItem(item)
        d = self._item_data(item)
        menu = QMenu(self)
        act_save = menu.addAction("💾  Farklı Kaydet…")
        act_save.setEnabled(d.get("result") is not None)
        act_remove = menu.addAction("🗑  Listeden Kaldır")
        chosen = menu.exec(self.listw.mapToGlobal(pos))
        if chosen is act_save:
            self._on_save()
        elif chosen is act_remove:
            self._on_remove_selected()

    def _background_image(self, result: Image.Image) -> Image.Image:
        """Seçilen arka plan seçimine göre RGBA sonucu hazırla."""
        mode = self.cmb_bg.currentText()
        if mode == "Şeffaf":
            return result.convert("RGBA")
        if mode == "Özel renk…":
            color = QColorDialog.getColor(QColor(255, 255, 255), self, "Arka plan rengi")
            if not color.isValid():
                return result.convert("RGBA")
            rgb = (color.red(), color.green(), color.blue())
        elif mode == "Beyaz":
            rgb = (255, 255, 255)
        else:
            rgb = (0, 0, 0)
        base = Image.new("RGB", result.size, rgb)
        base.paste(result, mask=result.split()[-1])
        return base

    def _on_save(self):
        item = self.listw.currentItem()
        if item is None:
            return
        d = self._item_data(item)
        if d.get("result") is None:
            QMessageBox.information(self, APP_TITLE, "Bu görsel henüz işlenmedi.")
            return
        default = os.path.splitext(d["path"])[0] + "_arksiz.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Sonucu kaydet", default,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;Tüm dosyalar (*)"
        )
        if not path:
            return
        try:
            self._save_image(d["result"], path)
            self.statusBar().showMessage(f"Kaydedildi: {path}")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Kaydedilemedi:\n{exc}")

    def _on_save_all(self):
        folder = QFileDialog.getExistingDirectory(self, "Kayıt klasörü seç")
        if not folder:
            return
        saved, failed = 0, 0
        for i in range(self.listw.count()):
            d = self._item_data(self.listw.item(i))
            if d.get("result") is None:
                continue
            name = os.path.splitext(os.path.basename(d["path"]))[0] + "_arksiz.png"
            try:
                self._save_image(d["result"], os.path.join(folder, name))
                saved += 1
            except Exception as exc:
                failed += 1
                print(f"[hata] {name} kaydedilemedi: {exc}", file=sys.stderr)
        msg = f"{saved} görsel kaydedildi: {folder}"
        if failed:
            msg += f"  ({failed} başarısız)"
        self.statusBar().showMessage(msg)

    @staticmethod
    def _save_image(result: Image.Image, path: str):
        """Şeffaflık desteklemeyen formatlara (JPG/BMP) kaydederken
        alpha kanalını beyaz arka planla düzleştirir; aksi halde PIL hata verir."""
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg", ".bmp"):
            rgb = Image.new("RGB", result.size, (255, 255, 255))
            if result.mode == "RGBA":
                rgb.paste(result, mask=result.split()[-1])
            else:
                rgb.paste(result.convert("RGB"))
            rgb.save(path, quality=95)
        else:
            result.save(path)

    # drag & drop --------------------------------------------------------
    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_paths(paths)

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        super().closeEvent(event)

    def _on_about(self):
        QMessageBox.about(
            self, "Hakkında",
            f"{APP_TITLE}\n\nrembg (U²-Net) ile AI tabanlı arka plan kaldırma.\n"
            "rembg yoksa OpenCV GrabCut yedeği devreye girer.\n\n"
            "PyQt6 + OpenCV + Pillow"
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()




