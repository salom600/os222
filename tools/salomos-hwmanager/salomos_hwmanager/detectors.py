"""Hardware detection — GPU, NIC, storage, audio.

Uses lspci, lsusb, lshw, dmidecode where available. Falls back to /sys probing."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from salomos_toolkit import get_logger, run

log = get_logger("salomos-hwmanager.detectors")


@dataclass
class GPU:
    vendor: str           # nvidia | intel | amd | unknown
    model: str
    pci_id: str
    driver_recommended: str
    driver_alternatives: list[str] = field(default_factory=list)
    vulkan: bool = False
    opencl: bool = False
    is_integrated: bool = False
    raw_lspci: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class NIC:
    vendor: str
    model: str
    driver: str
    interface: Optional[str] = None
    mac: Optional[str] = None
    is_wifi: bool = False


@dataclass
class StorageDevice:
    name: str
    model: str
    size: str
    rot: bool
    driver: str
    is_nvme: bool = False
    is_ssd: bool = False


def _lspci() -> str:
    try:
        cp = run(["lspci", "-nn"], capture=True, check=False)
        return cp.stdout or ""
    except Exception as e:
        log.warning("lspci failed: %s", e)
        return ""


def _lsusb() -> str:
    try:
        cp = run(["lsusb"], capture=True, check=False)
        return cp.stdout or ""
    except Exception as e:
        log.warning("lsusb failed: %s", e)
        return ""


def _lshw() -> str:
    try:
        cp = run(["lshw", "-json", "-short"], capture=True, check=False, timeout=10)
        return cp.stdout or ""
    except Exception as e:
        log.warning("lshw failed: %s", e)
        return ""


# ---- GPU detection --------------------------------------------------------

_VENDOR_MAP = [
    # (regex, vendor name, recommended driver)
    (re.compile(r"NVIDIA", re.I),                "nvidia", "nvidia-driver"),
    (re.compile(r"Intel.*Graphics|Intel.*HD Graphics|Intel.*UHD|Intel.*Iris", re.I), "intel", "intel-media-va-driver"),
    (re.compile(r"Advanced Micro Devices|AMD/ATI|ATI Technologies|Radeon", re.I),     "amd",   "mesa-vulkan-drivers"),
    (re.compile(r"VMware", re.I),                "vmware", "mesa-vulkan-drivers"),
    (re.compile(r"VirtualBox", re.I),            "virtualbox", "mesa-vulkan-drivers"),
    (re.compile(r"QXL|VirtIO", re.I),            "virtio", "mesa-vulkan-drivers"),
    (re.compile(r"Matrox", re.I),                "matrox", "vesa"),
]

_DRIVER_ALT = {
    "nvidia": ["nvidia-driver", "nvidia-driver-latest", "nvidia-driver-535", "nvidia-driver-545"],
    "intel":  ["intel-media-va-driver", "i965-va-driver", "intel-driver"],
    "amd":    ["mesa-vulkan-drivers", "xserver-xorg-video-amdgpu", "xserver-xorg-video-radeon"],
}


def detect_gpus() -> list[GPU]:
    gpus: list[GPU] = []
    lspci_out = _lspci()
    for line in lspci_out.splitlines():
        # Match "VGA compatible controller" or "3D controller" or "Display controller"
        if not re.search(r"(VGA compatible|3D controller|Display controller)", line, re.I):
            continue
        vendor = "unknown"
        recommended = "vesa"
        for rx, vname, drv in _VENDOR_MAP:
            if rx.search(line):
                vendor = vname
                recommended = drv
                break
        # Extract PCI ID [xxxx:xxxx]
        m = re.search(r"\[([0-9a-f]{4}):([0-9a-f]{4})\]", line)
        pci_id = f"{m.group(1)}:{m.group(2)}" if m else ""
        # Extract model name (everything before [)
        model = re.sub(r"\[.*$", "", line.split(":", 2)[-1]).strip() if ":" in line else line
        # Vulkan availability
        vulkan = bool(re.search(r"NVIDIA|AMD|Intel.*Graphics|Intel.*Iris|Intel.*UHD", line, re.I))
        # OpenCL — almost all modern GPUs
        opencl = vulkan
        # Integrated heuristic: Intel + in CPU, or "Mobile", or "HD Graphics" without dedicated name
        is_integrated = (
            vendor == "intel"
            or re.search(r"Mobile|HD Graphics|UHD Graphics|Iris", line, re.I) is not None
        ) and "RTX" not in line.upper() and "Radeon RX" not in line
        gpus.append(
            GPU(
                vendor=vendor,
                model=model,
                pci_id=pci_id,
                driver_recommended=recommended,
                driver_alternatives=_DRIVER_ALT.get(vendor, ["vesa"]),
                vulkan=vulkan,
                opencl=opencl,
                is_integrated=is_integrated,
                raw_lspci=line,
            )
        )
    if not gpus:
        # Fallback: try /sys
        for drm in sorted((Path("/sys/class/drm")).glob("card*/device/vendor")):
            try:
                vid = drm.read_text().strip()
                if vid == "0x10de":
                    gpus.append(GPU("nvidia", "Unknown NVIDIA", "", "nvidia-driver", ["nvidia-driver"], True, True, False, ""))
                elif vid in ("0x8086",):
                    gpus.append(GPU("intel", "Unknown Intel", "", "intel-media-va-driver", ["intel-media-va-driver"], True, True, True, ""))
                elif vid in ("0x1002", "0x1022"):
                    gpus.append(GPU("amd", "Unknown AMD", "", "mesa-vulkan-drivers", ["mesa-vulkan-drivers"], True, True, False, ""))
            except Exception as e:
                log.debug("drm probe failed: %s", e)
    return gpus


# ---- NIC detection --------------------------------------------------------

def detect_nics() -> list[NIC]:
    out: list[NIC] = []
    lspci_out = _lspci()
    for line in lspci_out.splitlines():
        if "Network controller" in line or "Ethernet controller" in line:
            vendor = "unknown"
            if re.search(r"Intel", line, re.I):
                vendor = "intel"
            elif re.search(r"Realtek", line, re.I):
                vendor = "realtek"
            elif re.search(r"Broadcom", line, re.I):
                vendor = "broadcom"
            elif re.search(r"Qualcomm|Atheros", line, re.I):
                vendor = "atheros"
            elif re.search(r"MediaTek|MTK", line, re.I):
                vendor = "mediatek"
            model = line.split(":", 2)[-1].strip() if ":" in line else line
            is_wifi = "Network controller" in line
            # Driver guess
            driver = "iwlwifi" if (vendor == "intel" and is_wifi) else "r8169" if vendor == "realtek" else "b44" if vendor == "broadcom" else "ath9k" if vendor == "atheros" else "kernel"
            out.append(NIC(vendor=vendor, model=model, driver=driver, is_wifi=is_wifi))
    return out


# ---- Storage detection ----------------------------------------------------

def detect_storage() -> list[StorageDevice]:
    out: list[StorageDevice] = []
    try:
        cp = run("lsblk -J -b -o NAME,MODEL,SIZE,ROTA,TRAN", capture=True, check=False)
        if cp.returncode == 0:
            data = json.loads(cp.stdout or "{}")
            for d in data.get("blockdevices", []):
                if d.get("type") != "disk":
                    continue
                size_bytes = int(d.get("size", 0) or 0)
                size_gb = size_bytes / (1024 ** 3)
                size_h = f"{size_gb:.1f}G"
                tran = (d.get("tran") or "").lower()
                is_nvme = tran == "nvme"
                rot = bool(d.get("rota", 0))
                is_ssd = tran == "sata" and not rot
                driver = "nvme" if is_nvme else "ahci" if tran == "sata" else "usb-storage" if tran == "usb" else "kernel"
                out.append(
                    StorageDevice(
                        name=d.get("name", ""),
                        model=d.get("model") or "Unknown",
                        size=size_h,
                        rot=rot,
                        driver=driver,
                        is_nvme=is_nvme,
                        is_ssd=is_ssd,
                    )
                )
    except Exception as e:
        log.warning("lsblk probe failed: %s", e)
    return out


# ---- Top-level entry-point ------------------------------------------------

def full_report() -> dict:
    return {
        "gpus": [g.to_dict() for g in detect_gpus()],
        "nics": [asdict(n) for n in detect_nics()],
        "storage": [asdict(s) for s in detect_storage()],
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(full_report(), indent=2))
    sys.exit(0)
