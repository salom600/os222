"""SalomOS Hardware Manager — PyQt6 GUI window."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFrame,
    QProgressBar,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QGroupBox,
)

from salomos_toolkit import get_logger

log = get_logger("salomos-hwmanager.ui")

from ..detectors import detect_gpus, detect_nics, detect_storage, full_report
from ..drivers import install_recommended_for_gpu, install, remove


# ----- Background workers ----------------------------------------------------

class Worker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(bool, str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self._fn(*self._args, **self._kwargs)
            self.done.emit(True, "ok")
        except Exception as e:
            self.done.emit(False, str(e))


# ----- Widgets ---------------------------------------------------------------

class GPUCard(QFrame):
    def __init__(self, gpu, parent=None):
        super().__init__(parent)
        self.gpu = gpu
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #23272e;
                border: 1px solid #3a3f4b;
                border-radius: 12px;
                padding: 16px;
                margin: 6px 0;
            }
        """)
        lay = QVBoxLayout(self)
        title = QLabel(f"<b style='font-size:14pt'>{gpu.vendor.upper()}</b>  ·  {gpu.model}")
        title.setStyleSheet("color: #e8eaed;")
        lay.addWidget(title)
        meta = QLabel(
            f"PCI: <code>{gpu.pci_id}</code> · "
            f"Driver: <code>{gpu.driver_recommended}</code> · "
            f"Vulkan: {'✓' if gpu.vulkan else '✗'} · "
            f"OpenCL: {'✓' if gpu.opencl else '✗'} · "
            f"{'Integrated' if gpu.is_integrated else 'Discrete'}"
        )
        meta.setStyleSheet("color: #9aa0a6;")
        lay.addWidget(meta)

        btn_row = QHBoxLayout()
        install_btn = QPushButton("Install recommended driver")
        install_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #0f9d58);
                color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 600;
            }
            QPushButton:hover { background: #1765cc; }
        """)
        install_btn.clicked.connect(self._on_install)
        btn_row.addWidget(install_btn)

        alt_btn = QPushButton("Choose alternative…")
        alt_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #1a73e8; border: 1px solid #1a73e8;
                          padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background: rgba(26,115,232,0.1); }
        """)
        alt_btn.clicked.connect(self._on_choose_alt)
        btn_row.addWidget(alt_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _on_install(self):
        ret = QMessageBox.question(
            self, "Install driver",
            f"Install {self.gpu.driver_recommended} for {self.gpu.vendor.upper()} {self.gpu.model}?\n\nA reboot may be required.",
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        results = install_recommended_for_gpu(self.gpu.vendor, self.gpu.model)
        ok = all(r.success for r in results)
        QMessageBox.information(self, "Done",
            "Driver installed successfully. Please reboot." if ok
            else "Some packages failed. See /var/log/salomos/hwmanager.log")

    def _on_choose_alt(self):
        QMessageBox.information(self, "Alternatives",
            f"Available: {', '.join(self.gpu.driver_alternatives)}\n\n"
            f"Run `pkexec salomos-hwmanager install <pkg>` to install one.")


# ----- Main window -----------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SalomOS Hardware Manager")
        self.setMinimumSize(900, 620)
        self.setStyleSheet("""
            QMainWindow { background: #181a20; }
            QLabel { color: #e8eaed; font-family: 'Inter', sans-serif; }
            QTabWidget::pane { border: 0; background: #1f2127; }
            QTabBar::tab {
                background: transparent; color: #9aa0a6;
                padding: 10px 20px; border: 0;
            }
            QTabBar::tab:selected { color: #1a73e8; border-bottom: 2px solid #1a73e8; }
            QListWidget { background: #1f2127; color: #e8eaed; border: 0; }
            QListWidget::item { padding: 12px; }
            QListWidget::item:selected { background: rgba(26,115,232,0.2); border-radius: 8px; }
            QStatusBar { background: #23272e; color: #9aa0a6; }
        """)

        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)

        header = QLabel("<h1 style='font-size:24pt; margin:0'>Hardware Manager</h1>"
                        "<p style='color:#9aa0a6; margin:4px 0 24px 0'>"
                        "Detect, install, and roll back drivers for your hardware.</p>")
        root.addWidget(header)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        # --- GPU tab ---
        gpu_tab = QWidget()
        gpu_lay = QVBoxLayout(gpu_tab)
        self.gpu_list = QVBoxLayout()
        gpu_lay.addLayout(self.gpu_list)
        gpu_lay.addStretch()
        tabs.addTab(gpu_tab, "🎮  GPU")

        # --- Network tab ---
        nic_tab = QWidget()
        nic_lay = QVBoxLayout(nic_tab)
        self.nic_list = QListWidget()
        nic_lay.addWidget(self.nic_list)
        tabs.addTab(nic_tab, "📡  Network")

        # --- Storage tab ---
        st_tab = QWidget()
        st_lay = QVBoxLayout(st_tab)
        self.storage_list = QListWidget()
        st_lay.addWidget(self.storage_list)
        tabs.addTab(st_tab, "💾  Storage")

        # --- Logs tab ---
        log_tab = QWidget()
        log_lay = QVBoxLayout(log_tab)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background: #0d0e12; color: #c2c7d0; font-family: 'JetBrains Mono', monospace;")
        log_lay.addWidget(self.log_view)
        tabs.addTab(log_tab, "📋  Logs")

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.refresh()

    def refresh(self):
        # Clear
        for i in reversed(range(self.gpu_list.count())):
            item = self.gpu_list.itemAt(i).widget()
            if item:
                item.setParent(None)

        # GPU
        gpus = detect_gpus()
        if not gpus:
            empty = QLabel("No GPU detected.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.gpu_list.addWidget(empty)
        for g in gpus:
            self.gpu_list.addWidget(GPUCard(g))

        # NIC
        self.nic_list.clear()
        for n in detect_nics():
            kind = "Wi-Fi" if n.is_wifi else "Ethernet"
            self.nic_list.addItem(f"{kind:8}  {n.vendor.upper():10}  {n.model:40}  driver: {n.driver}")

        # Storage
        self.storage_list.clear()
        for s in detect_storage():
            kind = "NVMe" if s.is_nvme else "SSD" if s.is_ssd else "HDD"
            self.storage_list.addItem(f"{kind:5}  {s.size:>6}  {s.model:35}  driver: {s.driver}")

        # Logs
        lp = Path("/var/log/salomos/hwmanager.log")
        if lp.exists():
            self.log_view.setPlainText(lp.read_text()[-5000:])
        else:
            self.log_view.setPlainText("(no log yet)")

        self.statusBar().showMessage(
            f"Detected {len(gpus)} GPU(s) · {self.nic_list.count()} NIC(s) · {self.storage_list.count()} storage"
        )
