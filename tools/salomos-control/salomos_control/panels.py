"""Control center panels — each exposes a QWidget with the panel UI."""
from __future__ import annotations

import subprocess
import shutil
import time
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGridLayout, QScrollArea, QProgressBar, QSlider, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QGroupBox, QMessageBox, QFileDialog, QSpinBox, QFormLayout,
)

from salomos_toolkit import get_logger, run, is_root
log = get_logger("salomos-control.panels")


# ----- Style -----------------------------------------------------------------

STYLE = """
QWidget { background: transparent; color: #e8eaed; font-family: 'Inter', sans-serif; }
QFrame#Card {
    background: #23272e; border: 1px solid #3a3f4b;
    border-radius: 12px; padding: 18px;
}
QPushButton {
    background: #1a73e8; color: white; border: 0;
    padding: 10px 20px; border-radius: 8px; font-weight: 600;
}
QPushButton:hover { background: #1765cc; }
QPushButton:disabled { background: #3a3f4b; color: #6b7280; }
QPushButton.secondary {
    background: transparent; color: #1a73e8; border: 1px solid #1a73e8;
}
QPushButton.secondary:hover { background: rgba(26,115,232,0.1); }
QPushButton.danger { background: #d93025; }
QPushButton.danger:hover { background: #b3261e; }
QLineEdit, QComboBox, QSpinBox {
    background: #181a20; color: #e8eaed; border: 1px solid #3a3f4b;
    border-radius: 6px; padding: 8px 10px;
}
QCheckBox { color: #e8eaed; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QListWidget {
    background: #181a20; color: #e8eaed; border: 1px solid #3a3f4b; border-radius: 6px;
}
QListWidget::item { padding: 8px; }
QListWidget::item:selected { background: rgba(26,115,232,0.3); }
QTextEdit { background: #181a20; color: #c2c7d0; border: 1px solid #3a3f4b; border-radius: 6px; }
QSlider::groove:horizontal { background: #3a3f4b; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #1a73e8; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }
"""


def card(title: str, subtitle: str = "") -> QFrame:
    f = QFrame()
    f.setObjectName("Card")
    l = QVBoxLayout(f)
    l.setContentsMargins(0, 0, 0, 0)
    h = QLabel(f"<h2 style='margin:0'>{title}</h2>"
               f"<p style='color:#9aa0a6; margin:4px 0 12px 0'>{subtitle}</p>")
    l.addWidget(h)
    return f


# ----- Panel: System --------------------------------------------------------

class SystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #181a20; border: 0;")
        host = QWidget()
        host.setStyleSheet("background: #181a20;")
        root = QVBoxLayout(host)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Info card
        info = card("System", "Live information about your SalomOS installation.")
        il = QFormLayout()
        self.os_label = QLabel("Loading…")
        self.kernel_label = QLabel("Loading…")
        self.cpu_label = QLabel("Loading…")
        self.ram_label = QLabel("Loading…")
        self.disk_label = QLabel("Loading…")
        self.uptime_label = QLabel("Loading…")
        il.addRow("Operating system:", self.os_label)
        il.addRow("Kernel:", self.kernel_label)
        il.addRow("CPU:", self.cpu_label)
        il.addRow("Memory:", self.ram_label)
        il.addRow("Disk:", self.disk_label)
        il.addRow("Uptime:", self.uptime_label)
        info.layout().addLayout(il)
        root.addWidget(info)

        # Actions card
        act = card("Maintenance", "Update, restart, and clean up.")
        al = QVBoxLayout()
        update_btn = QPushButton("Check for updates")
        update_btn.clicked.connect(self._update)
        al.addWidget(update_btn)
        restart_btn = QPushButton("Restart computer")
        restart_btn.setProperty("class", "danger")
        restart_btn.setStyleSheet("background: #d93025;")
        restart_btn.clicked.connect(self._restart)
        al.addWidget(restart_btn)
        shutdown_btn = QPushButton("Shut down")
        shutdown_btn.setStyleSheet("background: #d93025;")
        shutdown_btn.clicked.connect(self._shutdown)
        al.addWidget(shutdown_btn)
        act.layout().addLayout(al)
        root.addWidget(act)

        scroll.setWidget(host)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)

        self._load_info()

    def _load_info(self):
        # OS
        from salomos_toolkit import detect_distro
        d = detect_distro()
        self.os_label.setText(d.pretty)
        # Kernel
        cp = run("uname -rm", check=False, capture=True)
        self.kernel_label.setText(cp.stdout.strip() or "—")
        # CPU
        cp = run("lscpu | grep 'Model name' | head -1 | cut -d: -f2 | sed 's/^ //'", check=False, capture=True)
        self.cpu_label.setText(cp.stdout.strip() or "—")
        # RAM
        cp = run("free -h | head -2 | tail -1 | awk '{print $3 \" / \" $2}'", check=False, capture=True)
        self.ram_label.setText(cp.stdout.strip() or "—")
        # Disk
        cp = run("df -h / | tail -1 | awk '{print $3 \" / \" $2 \" (\" $5 \" used)\"}'", check=False, capture=True)
        self.disk_label.setText(cp.stdout.strip() or "—")
        # Uptime
        cp = run("uptime -p", check=False, capture=True)
        self.uptime_label.setText(cp.stdout.strip() or "—")

    def _update(self):
        run("pkexec /usr/bin/salomos-update", check=False, capture=True, timeout=600)

    def _restart(self):
        if QMessageBox.question(self, "Restart", "Restart the computer?") == QMessageBox.StandardButton.Yes:
            run("pkexec systemctl reboot", check=False)

    def _shutdown(self):
        if QMessageBox.question(self, "Shutdown", "Shut down the computer?") == QMessageBox.StandardButton.Yes:
            run("pkexec systemctl poweroff", check=False)


# ----- Panel: Appearance ----------------------------------------------------

class AppearancePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #181a20; border: 0;")
        host = QWidget()
        host.setStyleSheet("background: #181a20;")
        root = QVBoxLayout(host)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Theme picker
        theme = card("Theme", "Pick the look and feel of your desktop.")
        tl = QGridLayout()
        themes = [
            ("Windows 11", "Fluent design, rounded corners, acrylic surfaces.", "win11"),
            ("macOS", "WhiteSur Big Sur-like, light & airy.", "macos"),
            ("SalomOS Breeze", "KDE Plasma default with custom dark tweaks.", "breeze"),
        ]
        for i, (name, desc, key) in enumerate(themes):
            btn = QPushButton(f"<b style='font-size:11pt'>{name}</b><br>"
                              f"<span style='font-size:8pt; color:#9aa0a6'>{desc}</span>")
            btn.setStyleSheet("""
                QPushButton { background: #23272e; color: #e8eaed; border: 1px solid #3a3f4b;
                              border-radius: 10px; padding: 20px; text-align: left; }
                QPushButton:hover { border: 1px solid #1a73e8; }
            """)
            btn.setFixedHeight(90)
            btn.clicked.connect(lambda _, k=key: self._apply_theme(k))
            tl.addWidget(btn, 0, i)
        theme.layout().addLayout(tl)
        root.addWidget(theme)

        # Dark mode
        dark = card("Appearance", "Light or dark mode.")
        dl = QHBoxLayout()
        self.dark = QCheckBox("Use dark mode")
        self.dark.setChecked(True)
        dl.addWidget(self.dark)
        dl.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_dark)
        dl.addWidget(apply_btn)
        dark.layout().addLayout(dl)
        root.addWidget(dark)

        # Accent
        acc = card("Accent color", "The color of buttons and highlights.")
        al = QHBoxLayout()
        self.accent = QComboBox()
        self.accent.addItems(["Blue (#1a73e8)", "Green (#0f9d58)", "Red (#d93025)",
                              "Purple (#9334e6)", "Teal (#12b5cb)", "SalomOS Pink (#ff4081)"])
        al.addWidget(self.accent)
        al.addStretch()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_accent)
        al.addWidget(apply_btn)
        acc.layout().addLayout(al)
        root.addWidget(acc)

        # Animations
        anim = card("Animations", "Smooth or snappy.")
        aal = QHBoxLayout()
        self.anim = QSlider(Qt.Orientation.Horizontal)
        self.anim.setMinimum(0)
        self.anim.setMaximum(200)
        self.anim.setValue(100)
        aal.addWidget(self.anim)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_anim)
        aal.addWidget(apply_btn)
        anim.layout().addLayout(aal)
        root.addWidget(anim)

        # Wallpaper
        wall = card("Wallpaper", "Change your desktop background.")
        wl = QHBoxLayout()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_wallpaper)
        wl.addWidget(browse)
        wl.addStretch()
        wall.layout().addLayout(wl)
        root.addWidget(wall)

        root.addStretch()
        scroll.setWidget(host)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)

    def _apply_theme(self, key: str):
        run(f"pkexec salomos-set-theme {key}", check=False, capture=True, timeout=60)

    def _apply_dark(self):
        v = "yes" if self.dark.isChecked() else "no"
        run(f"pkexec salomos-set-dark {v}", check=False, capture=True, timeout=30)

    def _apply_accent(self):
        text = self.accent.currentText()
        # extract the hex
        import re
        m = re.search(r"#[0-9a-fA-F]{6}", text)
        if m:
            run(f"pkexec salomos-set-accent {m.group(0)}", check=False, capture=True, timeout=30)

    def _apply_anim(self):
        v = self.anim.value() / 100.0
        run(f"pkexec salomos-set-animations {v}", check=False, capture=True, timeout=30)

    def _browse_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose wallpaper", str(Path.home()),
                                              "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            run(f"pkexec salomos-set-wallpaper '{path}'", check=False, capture=True, timeout=30)


# ----- Panel: Users ---------------------------------------------------------

class UsersPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        host.setStyleSheet("background: #181a20;")
        root = QVBoxLayout(host)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        c = card("Users", "Manage accounts on this computer.")
        self.list = QListWidget()
        c.layout().addWidget(self.list)

        row = QHBoxLayout()
        add_btn = QPushButton("Add user…")
        add_btn.clicked.connect(self._add)
        row.addWidget(add_btn)
        pwd_btn = QPushButton("Set password…")
        pwd_btn.clicked.connect(self._set_pwd)
        row.addWidget(pwd_btn)
        admin_btn = QPushButton("Toggle admin")
        admin_btn.clicked.connect(self._toggle_admin)
        row.addWidget(admin_btn)
        row.addStretch()
        c.layout().addLayout(row)
        root.addWidget(c)
        root.addStretch()
        scroll.setWidget(host)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        self.refresh()

    def refresh(self):
        self.list.clear()
        cp = run("getent passwd | awk -F: '$3 >= 1000 && $3 < 65000 {print $1\":\"$7}'",
                 check=False, capture=True)
        if cp.stdout:
            for line in cp.stdout.splitlines():
                user, shell = line.split(":", 1)
                self.list.addItem(f"👤  {user}  (shell: {shell})")

    def _add(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Add user", "Username:")
        if not ok or not name:
            return
        pw, ok = QInputDialog.getText(self, "Add user", "Password:", QLineEdit.EchoMode.Password)
        if not ok or not pw:
            return
        run(f"pkexec useradd -m -s /bin/bash {name} && echo '{name}:{pw}' | pkexec chpasswd",
            check=False, capture=True, timeout=60)
        self.refresh()

    def _set_pwd(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text().split()[1]
        from PyQt6.QtWidgets import QInputDialog
        pw, ok = QInputDialog.getText(self, "Set password", f"New password for {name}:",
                                      QLineEdit.EchoMode.Password)
        if not ok or not pw:
            return
        run(f"echo '{name}:{pw}' | pkexec chpasswd", check=False, capture=True, timeout=30)

    def _toggle_admin(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text().split()[1]
        cp = run(f"groups {name}", check=False, capture=True)
        if "sudo" in cp.stdout:
            run(f"pkexec gpasswd -d {name} sudo", check=False, capture=True, timeout=30)
        else:
            run(f"pkexec gpasswd -a {name} sudo", check=False, capture=True, timeout=30)
        self.refresh()


# ----- Panel: Network -------------------------------------------------------

class NetworkPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        host.setStyleSheet("background: #181a20;")
        root = QVBoxLayout(host)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        c = card("Network", "Available Wi-Fi and wired networks.")
        self.list = QListWidget()
        c.layout().addWidget(self.list)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        c.layout().addWidget(refresh)
        root.addWidget(c)
        root.addStretch()
        scroll.setWidget(host)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        self.refresh()

    def refresh(self):
        self.list.clear()
        # Wi-Fi
        cp = run("nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list 2>/dev/null",
                 check=False, capture=True, timeout=10)
        if cp.stdout:
            for line in cp.stdout.splitlines()[:20]:
                parts = line.split(":")
                if len(parts) >= 2 and parts[0]:
                    ssid, signal, security = parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else ""
                    self.list.addItem(f"📶  {ssid:30}  signal: {signal:>3}%  security: {security}")
        # Wired
        cp = run("nmcli -t -f NAME,STATE,TYPE,DEVICE con show --active 2>/dev/null",
                 check=False, capture=True, timeout=10)
        if cp.stdout:
            for line in cp.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and "ethernet" in parts[2].lower():
                    self.list.addItem(f"🔌  {parts[0]:30}  device: {parts[3] if len(parts) > 3 else ''}  {parts[1]}")


# ----- Panel: Backup --------------------------------------------------------

class BackupPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        host.setStyleSheet("background: #181a20;")
        root = QVBoxLayout(host)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        c = card("Backup", "Timeshift snapshots — restore your system to a previous point in time.")
        info = QLabel("Timeshift is a system-restore tool. It uses rsync or btrfs snapshots "
                      "to record the state of your system at a moment in time.")
        info.setWordWrap(True)
        c.layout().addWidget(info)

        actions = QGridLayout()
        snap_btn = QPushButton("Create snapshot now")
        snap_btn.clicked.connect(lambda: run("pkexec timeshift --create", check=False, capture=True, timeout=300))
        actions.addWidget(snap_btn, 0, 0)
        list_btn = QPushButton("List snapshots")
        list_btn.clicked.connect(self._list_snaps)
        actions.addWidget(list_btn, 0, 1)
        restore_btn = QPushButton("Restore…")
        restore_btn.setStyleSheet("background: #d93025;")
        restore_btn.clicked.connect(self._restore)
        actions.addWidget(restore_btn, 1, 0)
        c.layout().addLayout(actions)

        self.snap_list = QListWidget()
        c.layout().addWidget(self.snap_list)
        root.addWidget(c)
        root.addStretch()
        scroll.setWidget(host)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        self._list_snaps()

    def _list_snaps(self):
        self.snap_list.clear()
        cp = run("timeshift --list 2>/dev/null | head -50", check=False, capture=True, timeout=10)
        if cp.stdout:
            for line in cp.stdout.splitlines():
                self.snap_list.addItem(line)
        else:
            self.snap_list.addItem("No snapshots found. Click 'Create snapshot now' to make one.")

    def _restore(self):
        QMessageBox.warning(self, "Restore",
                            "Restoring a snapshot will reboot the system. Make sure to save your work.")
