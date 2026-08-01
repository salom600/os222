"""SalomOS first-boot wizard.

Steps:
  1. Welcome
  2. Language & keyboard
  3. Theme (Win11 / macOS / Breeze)
  4. User account (real name, username, password)
  5. Driver auto-install (review detected hardware + pick drivers)
  6. Privacy & telemetry opt-in
  7. Done — launch desktop
"""
from __future__ import annotations

import os
import pwd
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLineEdit, QCheckBox, QComboBox, QRadioButton,
    QButtonGroup, QListWidget, QListWidgetItem, QProgressBar, QMessageBox,
    QFormLayout, QFrame, QStackedWidget, QWidget, QTextEdit,
)

from salomos_toolkit import get_logger, run, is_root, STATE_DIR
log = get_logger("salomos-installer")


# ---- Pages ------------------------------------------------------------------

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to SalomOS")
        self.setSubTitle("Let's get your system set up. This should take about 2 minutes.")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 40, 40, 40)
        banner = QLabel("""
<h1 style='font-size:32pt; margin: 0'>
  <span style='color:#1a73e8'>Salom</span>OS
</h1>
<p style='font-size:13pt; color:#9aa0a6; margin: 12px 0 32px 0'>
  Sleek · Modern · Lightweight
</p>
<p style='font-size:11pt; line-height: 1.6; color: #c2c7d0'>
  You're about to configure your SalomOS installation. We'll walk you through:
</p>
<ul style='font-size:11pt; line-height: 1.8; color: #c2c7d0'>
  <li>Language &amp; keyboard layout</li>
  <li>Desktop theme (Windows 11 / macOS / default)</li>
  <li>Your user account</li>
  <li>Graphics drivers — we'll auto-detect and install the right one</li>
  <li>Privacy preferences</li>
</ul>
""")
        banner.setWordWrap(True)
        lay.addWidget(banner)
        lay.addStretch()


class LanguagePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Language & Keyboard")
        self.setSubTitle("Pick your language and keyboard layout.")
        lay = QVBoxLayout(self)
        self.lang = QComboBox()
        self.lang.addItems(["English (US)", "English (UK)", "العربية (Arabic)", "Français (France)",
                            "Español (España)", "Deutsch", "Русский", "中文 (简体)"])
        lay.addWidget(QLabel("<b>Language</b>"))
        lay.addWidget(self.lang)
        lay.addSpacing(12)
        self.kbd = QComboBox()
        self.kbd.addItems(["US", "UK", "Arabic", "French", "Spanish", "German", "Russian", "Chinese"])
        lay.addWidget(QLabel("<b>Keyboard layout</b>"))
        lay.addWidget(self.kbd)
        lay.addStretch()
        self.registerField("language", self.lang, "currentText")
        self.registerField("keyboard", self.kbd, "currentText")


class ThemePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Choose your look")
        self.setSubTitle("You can change this any time from the Control Center.")
        self.selected = "win11"
        lay = QVBoxLayout(self)
        grid = QGridLayout()
        themes = [
            ("win11", "Windows 11", "Fluent design, rounded corners, acrylic surfaces.\nFamiliar for Windows users."),
            ("macos", "macOS", "WhiteSur Big Sur-like, light & airy.\nElegant, calm, refined."),
            ("breeze", "SalomOS Breeze", "KDE Plasma default with our custom dark tweaks.\nThe classic SalomOS look."),
        ]
        self.group = QButtonGroup(self)
        for i, (key, name, desc) in enumerate(themes):
            card = QFrame()
            card.setObjectName("ThemeCard")
            card.setStyleSheet("""
                #ThemeCard { background: #23272e; border: 1px solid #3a3f4b; border-radius: 12px; padding: 20px; }
                #ThemeCard:hover { border: 1px solid #1a73e8; }
            """)
            card.setFixedHeight(160)
            cl = QVBoxLayout(card)
            radio = QRadioButton(f"<b style='font-size:13pt'>{name}</b>")
            radio.setStyleSheet("color: #e8eaed;")
            radio.setProperty("key", key)
            radio.toggled.connect(self._on_toggle)
            self.group.addButton(radio)
            cl.addWidget(radio)
            d = QLabel(desc)
            d.setStyleSheet("color: #9aa0a6; font-size: 10pt;")
            d.setWordWrap(True)
            cl.addWidget(d)
            grid.addWidget(card, 0, i)
        lay.addLayout(grid)
        lay.addStretch()
        self.registerField("theme", self, "selected")

    def _on_toggle(self, checked: bool):
        if checked:
            btn = self.group.checkedButton()
            self.selected = btn.property("key")


class AccountPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Create your account")
        self.setSubTitle("This is the user you'll log in as.")
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.fullname = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.hostname = QLineEdit("salomos")
        form.addRow("Full name:", self.fullname)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
        form.addRow("Confirm:", self.confirm)
        form.addRow("Computer name:", self.hostname)
        lay.addLayout(form)
        lay.addStretch()
        self.registerField("fullname*", self.fullname)
        self.registerField("username*", self.username)
        self.registerField("password*", self.password)
        self.registerField("hostname", self.hostname)

    def validatePage(self) -> bool:
        if self.password.text() != self.confirm.text():
            QMessageBox.warning(self, "Passwords don't match", "Please re-enter the same password in both fields.")
            return False
        if len(self.password.text()) < 4:
            QMessageBox.warning(self, "Password too short", "Please use at least 4 characters.")
            return False
        return True


class DriversPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Drivers")
        self.setSubTitle("SalomOS has detected the following hardware.")
        self.detected: list[dict] = []
        self.choices: dict[str, str] = {}  # pci_id → driver

        lay = QVBoxLayout(self)
        self.list = QListWidget()
        lay.addWidget(self.list)
        row = QHBoxLayout()
        detect = QPushButton("Re-detect")
        detect.clicked.connect(self._detect)
        row.addWidget(detect)
        auto = QCheckBox("Install all recommended drivers automatically")
        auto.setChecked(True)
        auto.toggled.connect(self._toggle_auto)
        row.addWidget(auto)
        row.addStretch()
        lay.addLayout(row)
        self._detect()

    def _detect(self):
        self.list.clear()
        self.detected.clear()
        self.choices.clear()
        try:
            from salomos_hwmanager.detectors import detect_gpus
            gpus = detect_gpus()
        except Exception:
            gpus = []
        for g in gpus:
            self.detected.append({
                "vendor": g.vendor,
                "model": g.model,
                "pci_id": g.pci_id,
                "recommended": g.driver_recommended,
                "alternatives": g.driver_alternatives,
            })
            self.choices[g.pci_id] = g.driver_recommended
            text = f"🎮  {g.vendor.upper():8}  {g.model:40}  →  {g.driver_recommended}"
            item = QListWidgetItem(text)
            self.list.addItem(item)
        if not gpus:
            self.list.addItem("No GPU detected — using the default open-source drivers.")

    def _toggle_auto(self, checked: bool):
        if checked:
            for d in self.detected:
                self.choices[d["pci_id"]] = d["recommended"]


class PrivacyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Privacy")
        self.setSubTitle("You can change these any time in the Control Center.")
        lay = QVBoxLayout(self)
        self.telemetry = QCheckBox("Send anonymous usage statistics (helps us improve SalomOS)")
        self.telemetry.setChecked(False)
        lay.addWidget(self.telemetry)
        self.reports = QCheckBox("Send error reports automatically when the system crashes")
        self.reports.setChecked(True)
        lay.addWidget(self.reports)
        self.auto_update = QCheckBox("Install security updates automatically")
        self.auto_update.setChecked(True)
        lay.addWidget(self.auto_update)
        self.locationservices = QCheckBox("Allow applications to use your location")
        self.locationservices.setChecked(False)
        lay.addWidget(self.locationservices)
        lay.addStretch()
        self.registerField("telemetry", self.telemetry)
        self.registerField("reports", self.reports)
        self.registerField("auto_update", self.auto_update)


class ApplyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setting things up…")
        self.setSubTitle("Hang tight. We're configuring your system.")
        lay = QVBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        lay.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("background: #0d0e12; color: #c2c7d0; font-family: 'JetBrains Mono', monospace;")
        lay.addWidget(self.log, 1)
        self.setCommitPage(True)
        self.setButtonText(QWizard.WizardButton.NextButton, "Finish")

    def initializePage(self):
        self.progress.setValue(0)
        self._run_all()

    def _log(self, msg: str):
        self.log.append(msg)
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

    def _run_all(self):
        from PyQt6.QtCore import QCoreApplication
        wiz: InstallerWizard = self.wizard()
        steps = [
            ("Setting hostname", 10, lambda: self._set_hostname(wiz.field("hostname"))),
            ("Creating user account", 30, lambda: self._create_user(wiz)),
            ("Applying theme", 45, lambda: self._apply_theme(wiz.field("theme"))),
            ("Installing drivers", 75, lambda: self._install_drivers(wiz)),
            ("Configuring privacy", 90, lambda: self._set_privacy(wiz)),
            ("Marking first-boot done", 100, lambda: self._mark_done()),
        ]
        for name, pct, fn in steps:
            self._log(f"→ {name}…")
            try:
                fn()
                self.progress.setValue(pct)
                QCoreApplication.processEvents()
            except Exception as e:
                self._log(f"  ! error: {e}")
        self._log("\n✅ All done! Click Finish to start using SalomOS.")

    def _set_hostname(self, name: str):
        run(f"hostnamectl set-hostname {name}", check=False, capture=True)

    def _create_user(self, wiz):
        uname = wiz.field("username")
        pwd_text = wiz.field("password")
        full = wiz.field("fullname") or uname
        if not uname:
            return
        # If the user already exists, update password only
        try:
            pwd.getpwnam(uname)
            run(f"echo '{uname}:{pwd_text}' | chpasswd", check=False, capture=True)
        except KeyError:
            run(f"useradd -m -s /bin/bash -c '{full}' {uname}", check=False, capture=True)
            run(f"echo '{uname}:{pwd_text}' | chpasswd", check=False, capture=True)
        for g in ("audio", "sudo", "video", "netdev", "plugdev", "bluetooth", "lpadmin"):
            run(f"usermod -aG {g} {uname}", check=False, capture=True)

    def _apply_theme(self, key: str):
        cmd = f"/usr/bin/salomos-set-theme {key}"
        if not is_root():
            cmd = f"pkexec {cmd}"
        run(cmd, check=False, capture=True, timeout=120)

    def _install_drivers(self, wiz):
        # Trigger the hwmanager daemon path
        run("systemctl start salomos-hwmanager.service", check=False, capture=True, timeout=600)

    def _set_privacy(self, wiz):
        import json
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "privacy.json").write_text(json.dumps({
            "telemetry": wiz.field("telemetry"),
            "reports": wiz.field("reports"),
            "auto_update": wiz.field("auto_update"),
        }, indent=2))

    def _mark_done(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "firstboot.done").write_text("ok\n")


# ---- Main wizard -----------------------------------------------------------

class InstallerWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SalomOS First-Boot Setup")
        self.setMinimumSize(900, 650)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setStyleSheet("""
            QWizard { background: #181a20; }
            QWizard QLabel { color: #e8eaed; font-family: 'Inter', sans-serif; }
            QWizard QLabel#qt_wizard_title { font-size: 22pt; font-weight: 700; }
            QPushButton {
                background: #1a73e8; color: white; border: 0;
                padding: 10px 24px; border-radius: 8px; font-weight: 600; min-width: 100px;
            }
            QPushButton:hover { background: #1765cc; }
        """)

        self.addPage(WelcomePage())
        self.addPage(LanguagePage())
        self.addPage(ThemePage())
        self.addPage(AccountPage())
        self.addPage(DriversPage())
        self.addPage(PrivacyPage())
        self.addPage(ApplyPage())


def main():
    if not is_root():
        # Re-exec via pkexec for system-modifying steps
        # but we still need to show the GUI as the user.
        pass
    app = QApplication(sys.argv)
    app.setApplicationName("SalomOS First-Boot")
    wiz = InstallerWizard()
    wiz.show()
    rc = wiz.exec()
    if rc == QWizard.DialogCode.Accepted:
        # If we became root via pkexec, we already wrote /var/lib/salomos/firstboot.done
        pass
    sys.exit(rc)


if __name__ == "__main__":
    main()
