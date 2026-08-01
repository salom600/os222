#!/usr/bin/env python3
"""SalomOS Hardware Manager daemon.

Runs at first boot, after the live-config hooks fire.
1. Detects GPU + storage
2. If NVIDIA / AMD proprietary driver is missing, prompts user (or auto-installs per config)
3. Logs the result to /var/log/salomos/hwmanager.log
4. Writes a one-shot flag to /var/lib/salomos/hwmanager.done so we don't run again
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from salomos_toolkit import get_logger, run, is_root, STATE_DIR, load_config

log = get_logger("salomos-hwmanager.daemon")


DONE_FLAG = STATE_DIR / "hwmanager.done"
LOG_FILE = "hwmanager.log"


def _should_run() -> bool:
    if DONE_FLAG.exists():
        log.info("Already run; skipping.")
        return False
    return True


def _mark_done() -> None:
    DONE_FLAG.write_text(json.dumps({"ts": time.time(), "status": "ok"}))


def main() -> int:
    if not is_root():
        log.error("Must be root to run hwmanager daemon.")
        return 1
    if not _should_run():
        return 0

    log.info("=== SalomOS Hardware Manager daemon starting ===")
    cfg = load_config()
    auto_install = cfg.getboolean("hw", "auto_install_drivers", fallback=True)
    auto_detect = cfg.getboolean("hw", "auto_detect_gpu", fallback=True)

    if not auto_detect:
        log.info("auto_detect disabled; bailing out.")
        _mark_done()
        return 0

    # Lazy import so we don't need PyQt6 if we're headless
    from .detectors import detect_gpus, full_report

    report = full_report()
    log.info("Detected: %d GPU(s), %d NIC(s), %d storage device(s)",
             len(report["gpus"]), len(report["nics"]), len(report["storage"]))

    # Persist the full report
    Path("/var/lib/salomos/hw-report.json").write_text(json.dumps(report, indent=2))

    if not auto_install:
        log.info("auto_install disabled; user will trigger driver install via the GUI.")
        _mark_done()
        return 0

    needs_action = False
    for g in report["gpus"]:
        if g["vendor"] == "nvidia":
            # Check if a kernel module is already loaded
            cp = run("lsmod | grep -E '^nvidia '", check=False, capture=True)
            if not cp.stdout.strip():
                log.info("NVIDIA GPU detected, no driver loaded — installing.")
                needs_action = True
        elif g["vendor"] in ("amd", "intel"):
            # Mesa is usually installed by default; check anyway
            cp = run("dpkg -l mesa-vulkan-drivers | grep -E '^ii'", check=False, capture=True)
            if not cp.stdout.strip():
                log.info("%s GPU detected, mesa missing — installing.", g["vendor"])
                needs_action = True

    if needs_action:
        from .drivers import install_recommended_for_gpu
        for g in report["gpus"]:
            try:
                results = install_recommended_for_gpu(g["vendor"], g["model"])
                for r in results:
                    log.info("install: %s → %s (%s)", r.package,
                             "ok" if r.success else "FAIL", r.message.strip()[:200])
            except Exception as e:
                log.exception("driver install failed: %s", e)
    else:
        log.info("All detected GPUs already have drivers — no action needed.")

    _mark_done()
    return 0


if __name__ == "__main__":
    sys.exit(main())
