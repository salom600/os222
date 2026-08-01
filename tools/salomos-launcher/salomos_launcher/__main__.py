"""SalomOS Launcher — entry point.

A lightweight, keyboard-driven app launcher that pops up with Super+Space.
Uses PyQt6 with a frameless translucent window.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QFrame, QGraphicsBlurEffect,
)

from salomos_toolkit import get_logger
log = get_logger("salomos-launcher")


APPS = [
    ("⚙️", "Settings", "salomos-control", "Control Center"),
    ("🏪", "Store", "salomos-store", "SalomOS Store"),
    ("🎮", "Drivers", "salomos-hwmanager gui", "Hardware Manager"),
    ("🌐", "Firefox", "firefox", "Mozilla Firefox"),
    ("📁", "Files", "dolphin", "KDE file manager"),
    ("💻", "Terminal", "konsole", "KDE terminal"),
    ("📝", "Text Editor", "kate", "KDE text editor"),
    ("🎵", "Music", "elisa", "KDE music player"),
    ("📷", "Photos", "gwenview", "KDE image viewer"),
    ("🎬", "Videos", "vlc", "VLC media player"),
    ("🧮", "Calculator", "kcalc", "KDE calculator"),
    ("📧", "Mail", "thunderbird", "Thunderbird mail"),
    ("📦", "Packages", "plasma-discover", "Discover software center"),
    ("🔄", "Update", "salomos-update", "Run system update"),
    ("⏻", "Shutdown", "salomos-shutdown", "Power options"),
    ("🔒", "Lock", "loginctl lock-session", "Lock the screen"),
    ("🖥️", "System Monitor", "plasma-systemmonitor", "KDE system monitor"),
    ("🌍", "Browser", "chromium", "Chromium web browser"),
    ("🎨", "Paint", "kolourpaint", "KDE paint program"),
    ("📊", "Office", "libreoffice --calc", "LibreOffice Calc"),
]


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SalomOS Launcher")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(720, 520)
        self.setStyleSheet("""
            QWidget#root {
                background: rgba(24, 26, 32, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 0.06);
                color: #e8eaed;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 16px 20px;
                font-size: 16pt;
                font-family: 'Inter', sans-serif;
            }
            QLineEdit:focus { border: 1px solid #1a73e8; }
            QListWidget {
                background: transparent; color: #e8eaed; border: 0; outline: 0;
            }
            QListWidget::item {
                padding: 14px 18px; border-radius: 8px; font-size: 11pt;
                font-family: 'Inter', sans-serif;
            }
            QListWidget::item:selected {
                background: rgba(26, 115, 232, 0.25);
            }
            QLabel#hint {
                color: #6b7280; font-size: 8pt; font-family: 'JetBrains Mono', monospace;
                padding: 4px 18px;
            }
        """)

        root = QWidget(self)
        root.setObjectName("root")
        root.setGeometry(0, 0, 720, 520)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(20, 20, 20, 20)

        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Type to search…")
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._launch_selected)
        lay.addWidget(self.search)

        # List
        self.list = QListWidget()
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lay.addWidget(self.list, 1)

        # Hint
        self.hint = QLabel("↵  launch   ·   ⌫  Esc   ·   navigate with ↑ ↓")
        self.hint.setObjectName("hint")
        lay.addWidget(self.hint)

        self._populate("")

    def showEvent(self, e):
        super().showEvent(e)
        # Center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + (screen.width() - self.width()) // 2,
            screen.y() + (screen.height() - self.height()) // 3,
        )
        self.search.clear()
        self.search.setFocus()
        self._populate("")
        self.list.setCurrentRow(0)

    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_Escape:
            self.hide()
        elif e.key() in (Qt.Key.Key_Down,):
            self._move(1)
        elif e.key() in (Qt.Key.Key_Up,):
            self._move(-1)
        elif e.key() in (Qt.Key.Key_Tab,):
            self._move(1)
        else:
            super().keyPressEvent(e)

    def _move(self, delta: int):
        n = self.list.count()
        if n == 0:
            return
        cur = self.list.currentRow()
        nxt = (cur + delta) % n
        self.list.setCurrentRow(nxt)

    def _populate(self, query: str):
        self.list.clear()
        q = query.lower()
        for emoji, name, cmd, desc in APPS:
            if q and q not in name.lower() and q not in desc.lower() and q not in cmd.lower():
                continue
            item = QListWidgetItem(f"  {emoji}   {name:18}   {desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.list.addItem(item)
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _filter(self, text: str):
        self._populate(text)

    def _launch_selected(self):
        item = self.list.currentItem()
        if not item:
            return
        cmd = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        try:
            subprocess.Popen(cmd, shell=True, start_new_session=True,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.error("launch failed: %s", e)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SalomOS Launcher")
    win = Launcher()
    win.show()
    # Toggle on/off via SIGUSR1 (used by systemd --user)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
