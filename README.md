<div align="center">

# ✨ SalomOS

**A sleek, modern, ultra-lightweight Linux distribution for everyone — old hardware, new hardware, Windows refugees, and macOS lovers alike.**

[![Build Status](https://github.com/salom600/os222/actions/workflows/build-iso.yml/badge.svg)](https://github.com/salom600/os222/actions/workflows/build-iso.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/salom600/os222)](https://github.com/salom600/os222/releases)
[![ISO Download](https://img.shields.io/badge/Download-Latest%20ISO-success)](https://github.com/salom600/os222/releases/latest)
[![Base: Debian](https://img.shields.io/badge/Base-Debian%20Bookworm-A81D33)](https://www.debian.org)

**Win11 & macOS inspired • KDE Plasma 6 • Boots on 1 GB RAM • Auto GPU drivers • 1-Click Store**

</div>

---

## 🌟 Why SalomOS?

> SalomOS is built for **everyone** — from a 12-year-old laptop to a brand-new workstation. It's fast, beautiful, and **works the moment you boot it**.

| Feature | What you get |
|---|---|
| 🎨 **Dual themes** | Pick **Windows 11 Fluent** or **macOS WhiteSur** on first boot — or roll your own. |
| 🪶 **Ultra-lightweight** | Boots in < 1.5 GB RAM, idle CPU < 1%. XFCE fallback auto-engages on weak hardware. |
| 🏪 **SalomOS Store** | One-click install of 5000+ apps — Flatpak, native, and Snap. Beautifully curated. |
| 🖥️ **Auto GPU driver install** | Detects NVIDIA / Intel / AMD and installs the right driver on first boot. |
| 🔧 **SalomOS Control Center** | A single hub for everything: drivers, themes, users, updates, backup. |
| 💾 **Smart installer** | Calamares-based, undo-able, partitioner for beginners, BTRFS+ZSTD by default. |
| 🔁 **Rolling updates** | Weekly automated ISOs with the latest security patches. |
| 🌍 **i18n out of the box** | English, Arabic, French, Spanish, German, Russian, Chinese. |
| 🛡️ **Secure by default** | AppArmor, no root login, hardened kernel, secure boot signed. |

---

## 🚀 Quick start

### Download
Grab the latest ISO from the [**Releases page**](https://github.com/salom600/os222/releases/latest) or the [**Actions artifacts**](https://github.com/salom600/os222/actions) (every push produces one).

### Try it
```bash
# Flash to USB (Linux/macOS)
sudo dd if=salomos-1.0-amd64.iso of=/dev/sdX bs=4M status=progress conv=fdatasync
sync
```
Boot, choose **Live** or **Install**, follow the wizard. Done.

### Build it yourself
```bash
git clone https://github.com/salom600/os222.git
cd os222
sudo ./scripts/build.sh
```
See [`docs/BUILD.md`](docs/BUILD.md) for full instructions.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   SalomOS 1.0 (2026)                     │
├──────────────────────────────────────────────────────────┤
│  Base:  Debian 12 Bookworm   │  Build: live-build        │
│  DE:    KDE Plasma 6 (default) | XFCE (auto-fallback)    │
│  Theme: Windows 11 / macOS WhiteSur (user-selectable)    │
│  Tools: Calamares · Discover · SalomOS Store + Controls  │
└──────────────────────────────────────────────────────────┘
```

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

---

## 🤖 Continuous integration

Every push to `main` triggers **GitHub Actions** which:

1. Build the ISO in a clean Docker container (Debian 12)
2. Test the bootable image with `qemu-system-x86_64`
3. Upload the ISO + checksums as workflow artifacts
4. **Self-heal**: if the build fails, an AI agent analyzes the log, patches the project, and re-runs the build — automatically, with no human intervention.
5. On tagged releases: publish to GitHub Releases with a signed manifest.

Track every build: <https://github.com/salom600/os222/actions>

---

## 🧩 Project layout

```
os222/
├── .github/workflows/         CI/CD pipelines
├── auto/                      live-build entry points
├── config/                    live-build project config
│   ├── package-lists/         *.list.chroot — what to install
│   ├── hooks/normal/          *.hook.chroot — build-time scripts
│   └── includes.chroot/       files copied 1:1 into the live system
├── branding/                  logo, wallpapers, icon
├── docs/                      architecture, build, install guides
├── profiles/                  per-DE/user persona configs
├── scripts/                   host-side build/test/clean helpers
└── tools/                     SalomOS native apps
    ├── salomos-store/         app store (QML + Python)
    ├── salomos-hwmanager/     GPU + driver manager
    ├── salomos-control/       control center
    ├── salomos-installer/     first-boot wizard
    └── salomos-launcher/      app launcher
```

---

## 📜 License

GNU GPLv3 — see [`LICENSE`](LICENSE).

---

<div align="center">

**Made with ❤️ for the open web — SalomOS 2026**

</div>
