"""SalomOS Control Center — PyQt6 main window."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QStackedWidget, QFrame,
)

from salomos_toolkit import get_logger
log = get_logger("salomos-control.ui")

from .panels import SystemPanel, AppearancePanel, UsersPanel, NetworkPanel, BackupPanel


PANELS = [
    ("🖥️  System", SystemPanel),
    ("🎨  Appearance", AppearancePanel),
    ("👥  Users", UsersPanel),
    ("📡  Network", NetworkPanel),
    ("💾  Backup", BackupPanel),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SalomOS Control Center")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet("""
            QMainWindow { background: #181a20; }
            QWidget { color: #e8eaed; font-family: 'Inter', sans-serif; }
            QListWidget { background: #14161b; color: #e8eaed; border: 0; outline: 0; }
            QListWidget::item { padding: 14px 18px; border-radius: 0; }
            QListWidget::item:selected { background: rgba(26,115,232,0.25); border-left: 3px solid #1a73e8; }
            QListWidget::item:hover { background: rgba(255,255,255,0.05); }
        """)
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QListWidget()
        sidebar.setFixedWidth(260)
        for name, _ in PANELS:
            sidebar.addItem(QListWidgetItem(name))
        sidebar.currentRowChanged.connect(self._switch)
        root.addWidget(sidebar)

        # Stack
        self.stack = QStackedWidget()
        for _, panel_cls in PANELS:
            self.stack.addWidget(panel_cls())
        root.addWidget(self.stack, 1)

        sidebar.setCurrentRow(0)

    def _switch(self, idx: int):
        self.stack.setCurrentIndex(idx)
