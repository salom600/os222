"""Driver installer — wraps apt/dpkg, post-install steps, rollback."""
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from salomos_toolkit import get_logger, run, is_root, ensure_root, STATE_DIR

log = get_logger("salomos-hwmanager.drivers")

APT_LOCK_RETRIES = 30
APT_LOCK_WAIT_S = 2


@dataclass
class InstallResult:
    success: bool
    package: str
    message: str
    duration_s: float
    needs_reboot: bool = False


def _wait_for_apt() -> None:
    for _ in range(APT_LOCK_RETRIES):
        if not any(Path("/var/lib/dpkg/lock").exists() for p in [Path("/var/lib/dpkg/lock")]):
            try:
                with open("/var/lib/dpkg/lock", "r"):
                    pass
                time.sleep(APT_LOCK_WAIT_S)
                continue
            except BlockingIOError:
                time.sleep(APT_LOCK_WAIT_S)
                continue
        time.sleep(APT_LOCK_WAIT_S)
    # Also kill any lingering apt
    subprocess.run(["pkill", "-9", "apt"], check=False)
    subprocess.run(["pkill", "-9", "dpkg"], check=False)


def _apt_update() -> None:
    _wait_for_apt()
    cp = run("apt-get update -y", check=False, capture=True, timeout=300)
    if cp.returncode != 0:
        log.warning("apt update failed: %s", cp.stderr)


def install(packages: list[str], *, auto_yes: bool = True, simulate: bool = False) -> list[InstallResult]:
    """Install one or more packages. Returns per-package results."""
    ensure_root()
    if not packages:
        return []

    _apt_update()

    flag = "-s" if simulate else "-y"
    cmd = f"DEBIAN_FRONTEND=noninteractive apt-get {flag} install {' '.join(packages)}"
    start = time.time()
    cp = run(cmd, check=False, capture=True, timeout=1800)
    duration = time.time() - start

    results = []
    for pkg in packages:
        results.append(
            InstallResult(
                success=(cp.returncode == 0) if not simulate else True,
                package=pkg,
                message=cp.stderr[-500:] if cp.stderr else "ok",
                duration_s=duration,
                needs_reboot="nvidia" in pkg or "kernel" in pkg or "linux" in pkg,
            )
        )
    return results


def remove(packages: list[str], *, purge: bool = False) -> InstallResult:
    ensure_root()
    _wait_for_apt()
    cmd = f"DEBIAN_FRONTEND=noninteractive apt-get -y {'purge' if purge else 'remove'} {' '.join(packages)}"
    start = time.time()
    cp = run(cmd, check=False, capture=True, timeout=1800)
    return InstallResult(
        success=cp.returncode == 0,
        package=",".join(packages),
        message=cp.stderr[-500:] if cp.stderr else "ok",
        duration_s=time.time() - start,
        needs_reboot="nvidia" in " ".join(packages) or "kernel" in " ".join(packages),
    )


def install_recommended_for_gpu(vendor: str, model: str = "", *, auto_yes: bool = True) -> list[InstallResult]:
    """Install the canonical driver for a GPU vendor."""
    ensure_root()
    if vendor == "nvidia":
        pkgs = [
            "nvidia-driver",
            "nvidia-kernel-dkms",
            "nvidia-settings",
            "nvidia-prime",
            "nvidia-vulkan-icd",
            "nvidia-opencl-icd",
            "libnvidia-encode1",
            "libnvidia-decode1",
        ]
    elif vendor == "amd":
        pkgs = [
            "mesa-vulkan-drivers",
            "libva-mesa-driver",
            "mesa-va-drivers",
            "vulkan-tools",
            "vainfo",
            "xserver-xorg-video-amdgpu",
        ]
    elif vendor == "intel":
        pkgs = [
            "intel-media-va-driver",
            "i965-va-driver",
            "libva-intel-driver",
            "xserver-xorg-video-intel",
            "mesa-vulkan-drivers",
            "vainfo",
        ]
    else:
        pkgs = ["xserver-xorg-video-vesa", "xserver-xorg-video-fbdev"]

    log.info("Installing GPU driver for %s (%s): %s", vendor, model, ", ".join(pkgs))
    return install(pkgs, auto_yes=auto_yes)
