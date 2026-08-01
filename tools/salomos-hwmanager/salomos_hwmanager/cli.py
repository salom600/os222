#!/usr/bin/env python3
"""SalomOS Hardware Manager — CLI entry point.

Usage:
  salomos-hwmanager detect                      # JSON report of all hardware
  salomos-hwmanager gpu                         # just GPUs
  salomos-hwmanager install-gpu --auto          # install recommended driver for detected GPU
  salomos-hwmanager install nvidia-driver ...   # install arbitrary packages
  salomos-hwmanager driver-status               # check which driver is currently loaded
  salomos-hwmanager rollback                    # remove last installed driver
  salomos-hwmanager gui                         # launch GUI
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from salomos_toolkit import get_logger, ensure_root, run

log = get_logger("salomos-hwmanager.cli")

from .detectors import detect_gpus, detect_nics, detect_storage, full_report
from .drivers import install_recommended_for_gpu, install, remove, _wait_for_apt


def cmd_detect(_args):
    print(json.dumps(full_report(), indent=2))


def cmd_gpu(_args):
    gpus = detect_gpus()
    print(json.dumps([g.to_dict() for g in gpus], indent=2))


def cmd_install_gpu(args):
    ensure_root()
    gpus = detect_gpus()
    if not gpus:
        print("No GPU detected.", file=sys.stderr)
        return 1
    results = []
    for g in gpus:
        log.info("GPU: %s (%s) → %s", g.model, g.vendor, g.driver_recommended)
        r = install_recommended_for_gpu(g.vendor, g.model, auto_yes=args.auto_yes)
        results.extend(r)
    for r in results:
        print(f"  {'OK' if r.success else 'FAIL':4} {r.package:30} ({r.duration_s:.1f}s) {'REBOOT' if r.needs_reboot else ''}")
    return 0 if all(r.success for r in results) else 1


def cmd_install(args):
    ensure_root()
    r = install(args.packages, auto_yes=True)
    for x in r:
        print(f"  {'OK' if x.success else 'FAIL':4} {x.package:30}")
    return 0 if all(x.success for x in r) else 1


def cmd_remove(args):
    ensure_root()
    r = remove(args.packages, purge=args.purge)
    print(f"  {'OK' if r.success else 'FAIL':4} {r.package}")
    return 0 if r.success else 1


def cmd_driver_status(_args):
    cp = run("lsmod | grep -E 'nvidia|amdgpu|i915|radeon|nouveau'", check=False, capture=True)
    print(cp.stdout or "No GPU driver currently loaded.")
    cp = run("glxinfo | grep -E 'OpenGL renderer|OpenGL version'", check=False, capture=True)
    print(cp.stdout or "glxinfo not installed.")
    return 0


def cmd_rollback(_args):
    ensure_root()
    state = Path("/var/lib/salomos/last-driver-rollback.json")
    if not state.exists():
        print("No rollback state recorded.", file=sys.stderr)
        return 1
    info = json.loads(state.read_text())
    print(f"Rolling back: {info}")
    r = remove(info["packages"], purge=True)
    print(f"  {'OK' if r.success else 'FAIL':4} {','.join(info['packages'])}")
    state.unlink(missing_ok=True)
    return 0 if r.success else 1


def cmd_gui(_args):
    # Lazy-import GUI so the CLI works even on a headless system
    try:
        from .ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
    except Exception as e:
        print(f"GUI unavailable: {e}", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setApplicationName("SalomOS Hardware Manager")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="salomos-hwmanager",
        description="SalomOS Hardware Manager — auto-detect and install GPU drivers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("detect", help="Full hardware JSON report")
    s.set_defaults(func=cmd_detect)

    s = sub.add_parser("gpu", help="Detect GPUs only")
    s.set_defaults(func=cmd_gpu)

    s = sub.add_parser("install-gpu", help="Install recommended driver for detected GPU")
    s.add_argument("--auto", dest="auto_yes", action="store_true", default=True)
    s.set_defaults(func=cmd_install_gpu)

    s = sub.add_parser("install", help="Install arbitrary packages")
    s.add_argument("packages", nargs="+")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("remove", help="Remove packages")
    s.add_argument("packages", nargs="+")
    s.add_argument("--purge", action="store_true")
    s.set_defaults(func=cmd_remove)

    s = sub.add_parser("driver-status", help="Show currently loaded GPU driver")
    s.set_defaults(func=cmd_driver_status)

    s = sub.add_parser("rollback", help="Roll back the last driver install")
    s.set_defaults(func=cmd_rollback)

    s = sub.add_parser("gui", help="Launch GUI")
    s.set_defaults(func=cmd_gui)

    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
