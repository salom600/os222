"""SalomOS Store — PyQt6 GUI window.

Layout: sidebar of categories · main area grid of app cards · detail pane on right.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QAction, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit,
    QStackedWidget, QFrame, QScrollArea, QGridLayout, QMessageBox,
    QStatusBar, QSplitter, QProgressBar, QTextEdit, QTabWidget,
    QToolButton, QButtonGroup,
)

from salomos_toolkit import get_logger
log = get_logger("salomos-store.ui")

from ..backends import Store, App


# ----- Card ------------------------------------------------------------------

class AppCard(QFrame):
    clicked = pyqtSignal(object)  # App

    def __init__(self, app: App, parent=None):
        super().__init__(parent)
        self.app = app
        self.setObjectName("AppCard")
        self.setStyleSheet("""
            #AppCard {
                background: #23272e;
                border: 1px solid #3a3f4b;
                border-radius: 12px;
                padding: 16px;
            }
            #AppCard:hover {
                background: #2a2f37;
                border: 1px solid #1a73e8;
            }
        """)
        self.setFixedHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setSpacing(14)

        # Icon
        icon = QLabel()
        icon.setFixedSize(56, 56)
        icon.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1a73e8, stop:1 #0f9d58);
            color: white; font-size: 22pt; font-weight: 700;
            border-radius: 14px;
        """)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setText(app.name[0].upper())
        lay.addWidget(icon)

        # Text
        text = QVBoxLayout()
        text.setSpacing(4)
        name = QLabel(f"<b style='font-size:13pt; color:#e8eaed'>{app.name}</b>")
        text.addWidget(name)
        summary = QLabel(app.summary[:90] + ("…" if len(app.summary) > 90 else ""))
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #9aa0a6; font-size: 9pt;")
        text.addWidget(summary)
        meta = QLabel(
            f"<span style='color:#1a73e8'>{app.category}</span>  ·  "
            f"<span style='color:#9aa0a6'>{app.backend}</span>  ·  "
            + ("<span style='color:#0f9d58'>installed</span>" if app.installed
               else f"<span style='color:#9aa0a6'>{(app.size/1024/1024):.1f} MB</span>")
        )
        meta.setStyleSheet("font-size: 8pt;")
        text.addWidget(meta)
        text.addStretch()
        lay.addLayout(text, 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.app)


# ----- Detail pane ----------------------------------------------------------

class AppDetail(QFrame):
    install_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #1f2127; border-left: 1px solid #3a3f4b;
            }
            QLabel { color: #e8eaed; }
        """)
        self.setMinimumWidth(380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)

        self.title = QLabel("<h1>Pick an app</h1>")
        lay.addWidget(self.title)
        self.subtitle = QLabel("Click on a card to see details.")
        self.subtitle.setStyleSheet("color: #9aa0a6;")
        self.subtitle.setWordWrap(True)
        lay.addWidget(self.subtitle)

        self.desc = QTextEdit()
        self.desc.setReadOnly(True)
        self.desc.setStyleSheet("background: #181a20; color: #c2c7d0; border: 0; padding: 8px;")
        self.desc.setVisible(False)
        lay.addWidget(self.desc, 1)

        self.meta = QLabel()
        self.meta.setStyleSheet("color: #9aa0a6; font-size: 9pt;")
        self.meta.setWordWrap(True)
        lay.addWidget(self.meta)

        self.btn_row = QHBoxLayout()
        self.install_btn = QPushButton("Install")
        self.install_btn.setStyleSheet("""
            QPushButton { background: #1a73e8; color: white; border: 0; padding: 12px 28px;
                          border-radius: 8px; font-weight: 600; font-size: 11pt; }
            QPushButton:hover { background: #1765cc; }
        """)
        self.install_btn.setVisible(False)
        self.install_btn.clicked.connect(self._install)
        self.btn_row.addWidget(self.install_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #d93025; border: 1px solid #d93025;
                          padding: 12px 28px; border-radius: 8px; font-weight: 600; }
            QPushButton:hover { background: rgba(217,48,37,0.1); }
        """)
        self.remove_btn.setVisible(False)
        self.remove_btn.clicked.connect(self._remove)
        self.btn_row.addWidget(self.remove_btn)
        self.btn_row.addStretch()
        lay.addLayout(self.btn_row)

        self.app: App | None = None

    def show_app(self, app: App):
        self.app = app
        self.title.setText(f"<h1 style='margin:0'>{app.name}</h1>")
        self.subtitle.setText(app.summary)
        self.desc.setPlainText(app.description or app.summary)
        self.desc.setVisible(True)
        meta = []
        if app.category: meta.append(f"Category: {app.category}")
        if app.backend: meta.append(f"Source: {app.backend}")
        if app.size: meta.append(f"Size: {app.size/1024/1024:.1f} MB")
        if app.homepage: meta.append(f"Homepage: {app.homepage}")
        if app.license: meta.append(f"License: {app.license}")
        self.meta.setText("\n".join(meta))
        self.install_btn.setVisible(not app.installed)
        self.remove_btn.setVisible(app.installed)

    def _install(self):
        if self.app:
            self.install_requested.emit(self.app)
    def _remove(self):
        if self.app:
            self.remove_requested.emit(self.app)


# ----- Worker ---------------------------------------------------------------

class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(bool, str)

    def __init__(self, store: Store, app: App, remove: bool = False):
        super().__init__()
        self.store = store
        self.app = app
        self.remove = remove

    def run(self):
        try:
            self.progress.emit(20, f"Resolving {self.app.id}…")
            ok = self.store.remove(self.app) if self.remove else self.store.install(self.app)
            self.progress.emit(100, "Done")
            self.done.emit(ok, "ok" if ok else "failed")
        except Exception as e:
            self.done.emit(False, str(e))


# ----- Main window ---------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SalomOS Store")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet("""
            QMainWindow { background: #181a20; }
            QLabel { color: #e8eaed; font-family: 'Inter', sans-serif; }
            QLineEdit {
                background: #23272e; color: #e8eaed; border: 1px solid #3a3f4b;
                border-radius: 8px; padding: 10px 14px; font-size: 11pt;
            }
            QLineEdit:focus { border: 1px solid #1a73e8; }
            QListWidget { background: #181a20; color: #e8eaed; border: 0; outline: 0; }
            QListWidget::item { padding: 10px 14px; border-radius: 8px; }
            QListWidget::item:selected { background: rgba(26,115,232,0.25); color: #fff; }
            QListWidget::item:hover { background: rgba(255,255,255,0.05); }
            QStatusBar { background: #23272e; color: #9aa0a6; }
        """)
        self.store = Store()
        self._build()
        self.refresh()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background: #14161b;")
        sbl = QVBoxLayout(sidebar)
        sbl.setContentsMargins(16, 24, 16, 16)
        brand = QLabel("<h1 style='margin:0; font-size:18pt; color:#fff'>"
                       "<span style='color:#1a73e8'>Salom</span>OS Store</h1>")
        sbl.addWidget(brand)
        sbl.addSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Search apps…")
        self.search.textChanged.connect(self.refresh)
        sbl.addWidget(self.search)

        sbl.addSpacing(12)
        sbl.addWidget(QLabel("<b style='color:#9aa0a6; font-size:9pt'>CATEGORIES</b>"))
        self.cat_list = QListWidget()
        self.cat_list.itemSelectionChanged.connect(self.refresh)
        sbl.addWidget(self.cat_list, 1)

        sbl.addSpacing(8)
        self.refresh_btn = QPushButton("🔄  Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton { background: #23272e; color: #e8eaed; border: 0; padding: 10px;
                          border-radius: 8px; }
            QPushButton:hover { background: #2a2f37; }
        """)
        self.refresh_btn.clicked.connect(self.refresh_full)
        sbl.addWidget(self.refresh_btn)

        root.addWidget(sidebar)

        # Main area
        splitter = QSplitter()
        splitter.setStyleSheet("QSplitter::handle { background: #3a3f4b; width: 1px; }")
        root.addWidget(splitter, 1)

        # Grid of cards
        self.grid_host = QWidget()
        self.grid_host.setStyleSheet("background: #181a20;")
        gl = QVBoxLayout(self.grid_host)
        gl.setContentsMargins(24, 24, 24, 24)
        self.grid_header = QLabel("<h2 style='margin:0; color:#fff'>All Apps</h2>"
                                   "<p style='color:#9aa0a6; margin:4px 0 16px 0'>"
                                   "Discover and install applications curated for SalomOS.</p>")
        gl.addWidget(self.grid_header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: #181a20; border: 0;")
        self.grid = QWidget()
        self.grid.setStyleSheet("background: #181a20;")
        self.grid_layout = QGridLayout(self.grid)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid)
        gl.addWidget(self.scroll, 1)

        # Status bar with progress
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.setVisible(False)
        self.status.addPermanentWidget(self.progress)

        # Detail pane
        self.detail = AppDetail()
        self.detail.install_requested.connect(self.on_install)
        self.detail.remove_requested.connect(self.on_remove)

        splitter.addWidget(self.grid_host)
        splitter.addWidget(self.detail)
        splitter.setSizes([900, 380])

    def refresh_full(self):
        # Force re-read of apt index
        run("apt-get update -y", check=False, capture=True, timeout=300)
        self.refresh()

    def refresh(self):
        # Categories
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        all_item = QListWidgetItem("🌐  All apps")
        self.cat_list.addItem(all_item)
        for cat, _ in self.store.categories():
            item = QListWidgetItem(f"   {cat}")
            self.cat_list.addItem(item)
        self.cat_list.setCurrentRow(0)
        self.cat_list.blockSignals(False)

        # Apps
        query = self.search.text().strip() or None
        cat_item = self.cat_list.currentItem()
        cat = None
        if cat_item and cat_item.text().strip() != "🌐  All apps":
            cat = cat_item.text().strip()

        apps = self.store.list(query=query, category=cat)
        self.grid_header.setText(
            f"<h2 style='margin:0; color:#fff'>{cat or ('Search: ' + query if query else 'All Apps')}</h2>"
            f"<p style='color:#9aa0a6; margin:4px 0 16px 0'>{len(apps)} apps</p>"
        )

        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            it = self.grid_layout.itemAt(i)
            if it.widget():
                it.widget().setParent(None)

        # Add cards
        cols = 3
        for idx, app in enumerate(apps[:120]):
            card = AppCard(app)
            card.clicked.connect(self._on_card_clicked)
            self.grid_layout.addWidget(card, idx // cols, idx % cols)

        self.status.showMessage(f"{len(apps)} apps available")

    def _on_card_clicked(self, app: App):
        self.detail.show_app(app)

    def on_install(self, app: App):
        ret = QMessageBox.question(self, "Install", f"Install {app.name} from {app.backend}?")
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.worker = InstallWorker(self.store, app)
        self.worker.progress.connect(lambda v, m: (self.progress.setValue(v), self.status.showMessage(m)))
        self.worker.done.connect(self._on_install_done)
        self.worker.start()

    def on_remove(self, app: App):
        ret = QMessageBox.question(self, "Remove", f"Remove {app.name}?")
        if ret != QMessageBox.StandardButton.Yes:
            return
        self.progress.setVisible(True)
        self.worker = InstallWorker(self.store, app, remove=True)
        self.worker.progress.connect(lambda v, m: (self.progress.setValue(v), self.status.showMessage(m)))
        self.worker.done.connect(self._on_install_done)
        self.worker.start()

    def _on_install_done(self, ok: bool, msg: str):
        self.progress.setVisible(False)
        if ok:
            self.status.showMessage("Done.", 3000)
        else:
            QMessageBox.warning(self, "Failed", f"Operation failed: {msg}")
        self.refresh()
