"""Backends for the SalomOS Store.

- apt: native Debian packages via /var/lib/apt/lists
- flatpak: Flathub via flatpak-remotes
- snap: optional, off by default
- curated: hand-picked list from /etc/salomos/curated-flatpaks.list

Every backend exposes:
  list(query: str | None) -> list[App]
  install(app_id: str) -> bool
  remove(app_id: str) -> bool
  info(app_id: str) -> App | None
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Iterable

from salomos_toolkit import get_logger, run

log = get_logger("salomos-store.backends")


@dataclass
class App:
    id: str
    name: str
    summary: str
    description: str = ""
    category: str = "Other"
    icon: str = "package"
    backend: str = "unknown"   # apt | flatpak | snap | curated
    installed: bool = False
    size: int = 0              # bytes
    rating: float = 0.0
    downloads: int = 0
    screenshots: list[str] = field(default_factory=list)
    homepage: str = ""
    license: str = ""

    def to_dict(self):
        return asdict(self)


# ---- apt backend -----------------------------------------------------------

_APT_INDEX = Path("/var/lib/apt/lists")


def _read_apt_index() -> dict[str, dict]:
    """Read package metadata from /var/lib/apt/lists/*_Packages files."""
    if not _APT_INDEX.exists():
        return {}
    out: dict[str, dict] = {}
    for f in _APT_INDEX.glob("*_Packages"):
        try:
            current: dict[str, str] = {}
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith(" "):
                    if current.get("Description"):
                        current["Description"] += "\n" + line.strip()
                    continue
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    if current and current.get("Package") and current["Package"] not in out:
                        # First stanza wins (highest priority)
                        if current["Package"] not in out:
                            out[current["Package"]] = current
                    current = {k.strip(): v.strip()}
                if line.strip() == "" and current:
                    if current.get("Package") and current["Package"] not in out:
                        out[current["Package"]] = current
                    current = {}
            if current.get("Package") and current["Package"] not in out:
                out[current["Package"]] = current
        except Exception as e:
            log.warning("Failed to read %s: %s", f, e)
    return out


def _apt_status(pkg: str) -> tuple[bool, str]:
    cp = run(f"dpkg-query -W -f='${{Status}}\\n' {pkg}", check=False, capture=True)
    if cp.returncode != 0:
        return False, "not installed"
    s = cp.stdout.strip()
    if s.startswith("install ok installed"):
        return True, "installed"
    if "half-installed" in s:
        return True, "broken"
    return False, s


class AptBackend:
    name = "apt"

    def __init__(self):
        self._index: dict[str, dict] = {}
        self._loaded_at = 0.0
        self._load()

    def _load(self):
        log.info("Loading apt index…")
        self._index = _read_apt_index()
        self._loaded_at = time.time()
        log.info("Loaded %d packages.", len(self._index))

    def list(self, query: Optional[str] = None) -> list[App]:
        if time.time() - self._loaded_at > 600:
            self._load()
        out: list[App] = []
        q = (query or "").lower()
        for pkg, meta in self._index.items():
            if q and q not in pkg.lower() and q not in meta.get("Description", "").lower():
                continue
            inst, _ = _apt_status(pkg)
            out.append(
                App(
                    id=pkg,
                    name=meta.get("Package", pkg),
                    summary=meta.get("Description", "").split("\n")[0][:200],
                    description=meta.get("Description", ""),
                    category=_guess_category(pkg, meta),
                    backend="apt",
                    installed=inst,
                    size=int(meta.get("Size", 0) or 0),
                    homepage=meta.get("Homepage", ""),
                    license=meta.get("License", ""),
                )
            )
        return out

    def install(self, app_id: str) -> bool:
        cp = run(f"DEBIAN_FRONTEND=noninteractive pkexec apt-get install -y {app_id}", check=False, capture=True, timeout=1800)
        return cp.returncode == 0

    def remove(self, app_id: str) -> bool:
        cp = run(f"DEBIAN_FRONTEND=noninteractive pkexec apt-get remove -y {app_id}", check=False, capture=True, timeout=1800)
        return cp.returncode == 0

    def info(self, app_id: str) -> Optional[App]:
        meta = self._index.get(app_id)
        if not meta:
            return None
        inst, _ = _apt_status(app_id)
        return App(
            id=app_id,
            name=meta.get("Package", app_id),
            summary=meta.get("Description", "").split("\n")[0][:200],
            description=meta.get("Description", ""),
            category=_guess_category(app_id, meta),
            backend="apt",
            installed=inst,
            size=int(meta.get("Size", 0) or 0),
            homepage=meta.get("Homepage", ""),
            license=meta.get("License", ""),
        )


# ---- flatpak backend -------------------------------------------------------

class FlatpakBackend:
    name = "flatpak"

    def list(self, query: Optional[str] = None) -> list[App]:
        cp = run("flatpak remote-ls --columns=application,name,summary 2>/dev/null",
                 check=False, capture=True, timeout=60)
        out: list[App] = []
        if cp.returncode != 0 or not cp.stdout:
            return out
        for line in cp.stdout.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            app_id, name, summary = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if query and query.lower() not in (app_id + summary).lower():
                continue
            inst, _ = self._status(app_id)
            out.append(App(
                id=app_id,
                name=name or app_id,
                summary=summary,
                category=_guess_category(app_id, {"Description": summary}),
                backend="flatpak",
                installed=inst,
            ))
        return out

    def install(self, app_id: str) -> bool:
        cp = run(f"pkexec flatpak install -y flathub {app_id}", check=False, capture=True, timeout=1800)
        return cp.returncode == 0

    def remove(self, app_id: str) -> bool:
        cp = run(f"pkexec flatpak uninstall -y {app_id}", check=False, capture=True, timeout=600)
        return cp.returncode == 0

    def info(self, app_id: str) -> Optional[App]:
        cp = run(f"flatpak info {app_id}", check=False, capture=True, timeout=30)
        if cp.returncode != 0:
            return None
        inst, _ = self._status(app_id)
        return App(id=app_id, name=app_id, summary=cp.stdout[:200], backend="flatpak", installed=inst)

    @staticmethod
    def _status(app_id: str) -> tuple[bool, str]:
        cp = run(f"flatpak list | grep -E '^{app_id}\\s'", check=False, capture=True)
        return (bool(cp.stdout.strip()), "" if cp.stdout.strip() else "not installed")


# ---- curated backend (pre-installed list) ----------------------------------

CURATED_PATH = Path("/etc/salomos/curated-flatpaks.list")


class CuratedBackend:
    name = "curated"

    def list(self, query: Optional[str] = None) -> list[App]:
        if not CURATED_PATH.exists():
            return []
        out: list[App] = []
        for line in CURATED_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) < 3:
                continue
            app_id, cat, desc = parts[0].strip(), parts[1].strip(), parts[2].strip()
            if query and query.lower() not in (app_id + desc).lower():
                continue
            inst, _ = FlatpakBackend._status(app_id)
            out.append(App(
                id=app_id, name=app_id.split(".")[-1].title(),
                summary=desc, category=cat, backend="flatpak", installed=inst,
            ))
        return out

    def install(self, app_id: str) -> bool:
        return FlatpakBackend().install(app_id)

    def remove(self, app_id: str) -> bool:
        return FlatpakBackend().remove(app_id)

    def info(self, app_id: str) -> Optional[App]:
        if not CURATED_PATH.exists():
            return None
        for line in CURATED_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split("|")
            if len(parts) >= 3 and parts[0].strip() == app_id:
                return App(
                    id=app_id, name=app_id.split(".")[-1].title(),
                    summary=parts[2].strip(), category=parts[1].strip(),
                    backend="flatpak",
                )
        return None


# ---- helpers ---------------------------------------------------------------

_CAT_MAP = {
    "browser": "Internet", "firefox": "Internet", "chromium": "Internet", "chrome": "Internet",
    "code": "Development", "vim": "Development", "vscode": "Development", "neovim": "Development",
    "git": "Development", "gimp": "Graphics", "inkscape": "Graphics", "krita": "Graphics",
    "vlc": "Video", "mpv": "Video", "obs": "Video", "kdenlive": "Video",
    "libreoffice": "Office", "calc": "Office", "writer": "Office", "impress": "Office",
    "qbittorrent": "Network", "transmission": "Network", "wireshark": "Network",
    "steam": "Games", "lutris": "Games", "minecraft": "Games", "wine": "Games",
    "telegram": "Chat", "signal": "Chat", "discord": "Chat", "thunderbird": "Internet",
    "blender": "Graphics", "darktable": "Photography", "rawtherapee": "Photography",
    "audacity": "Audio", "ardour": "Audio", "elisa": "Audio",
    "keepassxc": "Security", "veracrypt": "Security", "bitwarden": "Security",
    "docker": "System", "podman": "System", "virtualbox": "System",
}


def _guess_category(pkg: str, meta: dict) -> str:
    name = pkg.lower()
    desc = (meta.get("Description") or meta.get("summary") or "").lower()
    for key, cat in _CAT_MAP.items():
        if key in name or key in desc:
            return cat
    section = (meta.get("Section") or "").split("/")[-1]
    if section:
        return section.title()
    return "Other"


# ---- Unified facade --------------------------------------------------------

class Store:
    def __init__(self, *, use_apt: bool = True, use_flatpak: bool = True, use_curated: bool = True):
        self.apt = AptBackend() if use_apt else None
        self.flatpak = FlatpakBackend() if use_flatpak else None
        self.curated = CuratedBackend() if use_curated else None

    def list(self, query: Optional[str] = None, category: Optional[str] = None) -> list[App]:
        all_apps: list[App] = []
        for backend in (self.curated, self.apt, self.flatpak):
            if backend is None:
                continue
            try:
                all_apps.extend(backend.list(query))
            except Exception as e:
                log.warning("%s.list failed: %s", backend.name, e)
        if category:
            all_apps = [a for a in all_apps if a.category == category]
        # Deduplicate by id+backend
        seen = set()
        unique = []
        for a in all_apps:
            k = (a.id, a.backend)
            if k in seen:
                continue
            seen.add(k)
            unique.append(a)
        # Sort: installed first, then by name
        unique.sort(key=lambda a: (not a.installed, a.name.lower()))
        return unique

    def install(self, app: App) -> bool:
        if app.backend == "apt" and self.apt:
            return self.apt.install(app.id)
        if app.backend == "flatpak" and self.flatpak:
            return self.flatpak.install(app.id)
        return False

    def remove(self, app: App) -> bool:
        if app.backend == "apt" and self.apt:
            return self.apt.remove(app.id)
        if app.backend == "flatpak" and self.flatpak:
            return self.flatpak.remove(app.id)
        return False

    def categories(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for a in self.list():
            counts[a.category] = counts.get(a.category, 0) + 1
        return sorted(counts.items(), key=lambda kv: -kv[1])
