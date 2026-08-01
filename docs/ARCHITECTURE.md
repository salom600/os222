# SalomOS Architecture

> The full design of the SalomOS distribution.

## 1. Design goals

SalomOS is built for **everyone** — from a 12-year-old laptop to a brand-new workstation.
The four pillars are:

| Pillar | Means |
|---|---|
| **Sleek** | KDE Plasma 6 with custom theming; Fluent Win11 + WhiteSur macOS alternatives |
| **Lightweight** | Boots in 1.5 GB RAM, idle CPU < 1 %; XFCE auto-fallback for weak hardware |
| **Easy** | One-click Store, one-click driver install, one-click first-boot wizard |
| **Stable** | Debian base, signed Secure Boot, ZRAM, BTRFS+ZSTD default, AppArmor |

## 2. High-level stack

```
┌────────────────────────────────────────────────────────────────────┐
│ SalomOS User Space                                                  │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │ SalomOS     │  │ SalomOS      │  │ SalomOS     │  │ SalomOS  │  │
│  │ Store       │  │ Control      │  │ Hardware    │  │ Launcher │  │
│  │ (PyQt6)     │  │ (PyQt6)      │  │ Manager     │  │ (PyQt6)  │  │
│  └─────┬───────┘  └──────┬───────┘  └──────┬──────┘  └────┬─────┘  │
│        │                 │                  │              │        │
│  ┌─────┴─────────────────┴──────────────────┴──────────────┴────┐  │
│  │                  salomos-toolkit (Python lib)                  │  │
│  └─────────────────────────┬────────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────┴────────────────────────────────────┐  │
│  │  KDE Plasma 6  ·  PipeWire  ·  NetworkManager  ·  systemd    │  │
│  └─────────────────────────┬────────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────┴────────────────────────────────────┐  │
│  │  Debian 12 (Bookworm) — Linux 6.1 LTS — Mesa 22.3           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## 3. ISO build pipeline

The ISO is built with **live-build** inside a clean Debian 12 container
(Docker in CI, native on a developer's box).

```
                 ┌─────────────────┐
                 │  auto/config    │  → runs `lb config` with all options
                 │  auto/build     │  → runs `lb build`
                 │  auto/clean     │  → removes intermediate state
                 └────────┬────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   config/           config/hooks/      config/
   package-lists/    normal/            includes.chroot/
                                         (e.g. /etc/salomos,
                                          /usr/bin/salomos-*,
                                          /etc/systemd/system/
                                          salomos-*.service)
```

### 3.1 Hook execution order

`config/hooks/normal/*.hook.chroot` runs in numeric order:

1. `0001` — Create the `salom` user, set groups, configure sudo
2. `0002` — Install the first-party Python tooling
3. `0003` — Apply KDE global theming and font defaults
4. `0004` — Enable systemd services
5. `0005` — DE auto-fallback for low-RAM systems
6. `0006` — Configure Flatpak remotes
7. `0007` — Create canonical SalomOS directories and `/etc/os-release`
8. `0008` — Secure Boot shim
9. `0009` — Firewall defaults
10. `0010` — Cleanup
11. `0011` — Install SalomOS Python packages from `/usr/share/salomos/project`

### 3.2 What gets included in the chroot

| Path | Purpose |
|---|---|
| `/etc/salomos/salomos.conf` | Global config (theme, store, hw, updates) |
| `/etc/os-release` | Identifies the system as SalomOS |
| `/etc/lsb-release` | Same, LSB-compatible |
| `/usr/bin/salomos-*` | CLI / GUI entry points |
| `/usr/share/applications/salomos-*.desktop` | Menu entries |
| `/usr/share/backgrounds/salomos/` | Wallpapers |
| `/etc/systemd/system/salomos-*.{service,timer}` | Auto-start |
| `/etc/calamares/branding/salomos/` | Installer branding |
| `/var/lib/salomos/` | Runtime state, first-boot flag, hw report |

## 4. First-boot flow

1. GRUB → Plymouth splash → live system boots
2. `live-config` script `0020-salomos-de-select` checks RAM
   - `≥ 2 GB` → SDDM (KDE Plasma 6) on tty7
   - `< 2 GB` → LightDM (XFCE) on tty7
3. Auto-login as `salom`
4. `salomos-firstboot.service` triggers the wizard
5. User picks language, theme, account, drivers, privacy
6. Wizard writes `/var/lib/salomos/firstboot.done`
7. `salomos-hwmanager.service` runs (one-shot) and installs any missing drivers
8. Desktop is ready

## 5. Update flow

- **Daily** security updates via `unattended-upgrades` (auto)
- **Weekly** scheduled `salomos-update.timer` (auto)
- **Manual** `salomos-update` runs apt-get update + unattended-upgrade
- **Weekly** scheduled GitHub Actions rebuilds produce fresh ISOs

## 6. CI/CD

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | every push | Lint Python + shell |
| `build-iso.yml` | every push to main | Build ISO inside Docker, upload artifact |
| `auto-fix.yml` | on build-iso failure | Detect + patch, push fix branch, open PR |
| `nightly.yml` | cron Mon 03:00 | Weekly rolling snapshot |
| `release.yml` | on `v*` tag | Build, sign, publish to GitHub Releases |

### 6.1 Self-healing algorithm

```
                  ┌──────────────────┐
                  │  build-iso.yml   │
                  │     runs          │
                  └────────┬─────────┘
                           │
                  success? │
                  ┌────────┴────────┐
                  │                 │
                 yes               no
                  │                 │
                  ▼                 ▼
            ┌─────────┐    ┌──────────────────┐
            │ upload  │    │  auto-fix.yml    │
            │ artifact│    │     runs          │
            └─────────┘    └────────┬─────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │ download log      │
                          └────────┬──────────┘
                                   ▼
                          ┌───────────────────┐
                          │ auto-fixer.py     │
                          │  (heuristics +    │
                          │  optional AI)     │
                          └────────┬──────────┘
                                   ▼
                          ┌───────────────────┐
                          │  patch.diff       │
                          └────────┬──────────┘
                                   ▼
                          ┌───────────────────┐
                          │ push branch,      │
                          │ open PR           │
                          └────────┬──────────┘
                                   ▼
                          ┌───────────────────┐
                          │ build-iso.yml     │
                          │ re-runs on PR     │
                          └───────────────────┘
```

### 6.2 Self-healing fix rules

| Rule | Trigger | Fix |
|---|---|---|
| missing-package | `Unable to locate package XYZ` | comment out the offending line in the package list |
| chroot-failure  | `chroot: failed to run command 'XYZ'` | wrap the call in `if command -v XYZ` |
| permission      | `Permission denied` | inject `chmod 0775` after the failed line |
| python-import   | `ModuleNotFoundError` | add `python3-XYZ` to the install hook |
| yaml-syntax     | YAML scanner error | log a warning, mark the file for human review |
| disk-full       | `No space left on device` | lower squashfs compression to -1 |
| dpkg-lock       | `Could not get lock` | inject `_wait_for_apt()` at the start of install scripts |

If no rule matches, the workflow opens a GitHub issue with the log tail
labelled `auto-fix-exhausted`, and a human takes over.

## 7. Security model

- **No root password** in live mode; sudo for `salom` only.
- **AppArmor** profiles enabled for browsers, SalomOS native apps.
- **firewalld** active; SSH server disabled.
- **Secure Boot** signed via shim + signed GRUB.
- **Hardened sysctl** (kernel ASLR, ptrace restrictions).
- **Reproducible builds** via live-build (sort of — full determinism in 2026 is
  not quite there; we aim for byte-stable *package list* reproducibility).

## 8. Theming

- **Default theme**: Win11 (Fluent design, rounded corners, acrylic)
- **Alternative**: macOS (WhiteSur)
- **Per-user override**: `salomos-set-theme win11|macos|breeze`
- **Files**:
  - `/usr/share/color-schemes/SalomOSAccent.colors` — accent color override
  - `/usr/share/plasma/look-and-feel/org.kde.salomos.desktop/` — LAF package
  - `/etc/skel/.config/` — default user dotfiles

## 9. The Store

- Aggregates: **apt** (Debian) + **flatpak** (Flathub) + curated list
- Backend in `tools/salomos-store/salomos_store/backends.py`
- Curated list at `/etc/salomos/curated-flatpaks.list`
- One install path per app — Store calls the right backend
- Desktop file at `/usr/share/applications/salomos-store.desktop`

## 10. Hardware Manager

- Detects GPU via `lspci -nn` (fallback `/sys/class/drm`)
- Detects NIC and storage
- Recommends driver per vendor:
  - NVIDIA → `nvidia-driver` (DKMS)
  - AMD → `mesa-vulkan-drivers` + amdgpu
  - Intel → `intel-media-va-driver` + i965 + vulkan
- Runs once at first boot (`salomos-hwmanager.service` oneshot)
- Can be re-run from the GUI: `salomos-hwmanager gui`

## 11. Future plans

- Wayland-only mode (KDE Plasma 6 is ready)
- Snap-store backend (opt-in)
- Cloud-init integration for cloud images
- Immutable root with transactional updates (ostree)
- ARM64 image with Plasma Mobile
