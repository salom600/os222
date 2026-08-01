"""SalomOS Toolkit — common library shared by all salomos-* tools.

Provides:
- configuration loading from /etc/salomos/salomos.conf
- logging utilities
- privilege detection
- hardware probing helpers
- subprocess wrappers that don't barf on spaces / weird shells
- i18n shim
"""
from __future__ import annotations

import configparser
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path("/etc/salomos/salomos.conf")
LOG_DIR = Path("/var/log/salomos")
STATE_DIR = Path("/var/lib/salomos")

__all__ = [
    "CONFIG_PATH",
    "LOG_DIR",
    "STATE_DIR",
    "load_config",
    "get_logger",
    "is_root",
    "run",
    "DistroInfo",
    "detect_distro",
]


@dataclass(frozen=True)
class DistroInfo:
    name: str
    version: str
    codename: str
    pretty: str
    id: str
    id_like: str
    home_url: str


def _read_os_release() -> dict[str, str]:
    out: dict[str, str] = {}
    p = Path("/etc/os-release")
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def detect_distro() -> DistroInfo:
    data = _read_os_release()
    return DistroInfo(
        name=data.get("NAME", "SalomOS"),
        version=data.get("VERSION_ID", "1.0"),
        codename=data.get("VERSION_CODENAME", data.get("SALOMOS_CODENAME", "Aurora")),
        pretty=data.get("PRETTY_NAME", "SalomOS 1.0 Aurora"),
        id=data.get("ID", "salomos"),
        id_like=data.get("ID_LIKE", "debian"),
        home_url=data.get("HOME_URL", "https://github.com/salom600/os222"),
    )


def load_config(path: Optional[Path] = None) -> configparser.ConfigParser:
    p = path or CONFIG_PATH
    cp = configparser.ConfigParser()
    if p.exists():
        cp.read(p, encoding="utf-8")
    else:
        # Hard-coded defaults so tools don't crash on a mis-configured system
        cp.read_string(
            """
[meta]
version=1.0.0-salom
codename=Aurora

[ui]
default_theme=win11
default_dark=true

[store]
auto_refresh=true
show_native=true
show_flatpak=true
show_snap=false
curated_only=false
auto_install_drivers=true

[hw]
auto_detect_gpu=true
auto_install_drivers=true

[updates]
channel=stable
auto_apply_security=true
auto_apply_regular=false
"""
        )
    return cp


def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    log.addHandler(sh)
    if log_file:
        fh = logging.FileHandler(LOG_DIR / log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    return log


def is_root() -> bool:
    return os.geteuid() == 0


def run(
    cmd: str | list[str],
    *,
    check: bool = True,
    capture: bool = True,
    env: Optional[dict] = None,
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> subprocess.CompletedProcess:
    """Run a command with sensible defaults. If `cmd` is a string we use shell=True."""
    if isinstance(cmd, str):
        return subprocess.run(
            cmd,
            shell=True,
            check=check,
            text=True,
            capture_output=capture,
            env={**os.environ, **(env or {})},
            cwd=cwd,
            timeout=timeout,
        )
    return subprocess.run(
        cmd,
        shell=False,
        check=check,
        text=True,
        capture_output=capture,
        env={**os.environ, **(env or {})},
        cwd=cwd,
        timeout=timeout,
    )


def ensure_root() -> None:
    if not is_root():
        print("This operation requires root. Re-run with sudo or pkexec.", file=sys.stderr)
        sys.exit(1)
