# Changelog

All notable changes to SalomOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-salom] — Aurora — 2026-Q3

### Added
- KDE Plasma 6 as the default desktop environment.
- Windows 11 Fluent + macOS WhiteSur theme packs, user-selectable at first boot.
- XFCE 4.18 auto-fallback for systems with < 2 GB RAM.
- SalomOS Store — QML app store wrapping apt, flatpak, and snap with curated categories.
- SalomOS Hardware Manager — automatic GPU detection (NVIDIA, Intel, AMD) with one-click driver install.
- SalomOS Control Center — central hub for users, themes, updates, backup, network, power.
- SalomOS Installer — first-boot wizard for language, theme, account, and driver setup.
- Calamares-based graphical installer with BTRFS+ZSTD default, encrypted LUKS option.
- Live-build reproducible ISO build pipeline (Docker-based).
- GitHub Actions workflows: `build-iso.yml`, `auto-fix.yml`, `release.yml`, `nightly.yml`.
- Self-healing build workflow: on failure, an agent reads the log, patches the project, and re-runs.
- Multi-architecture builds: amd64, i386, arm64.
- QEMU smoke-test for every built ISO before artifact upload.
- Signed SHA256 + BLAKE2b checksums for every published ISO.
- Weekly automated nightly ISO builds.
- Documentation: ARCHITECTURE.md, BUILD.md, INSTALL.md, THEMING.md, CONTRIBUTING.md.

### Security
- AppArmor profiles enabled by default for browsers and SalomOS native apps.
- No root password set in live mode; sudo for the `salom` user only.
- Secure Boot signed bootloader (shim + GRUB).
- Hardened sysctl profile (kernel ASLR, ptrace restrictions, kptr_restrict).
- firewalld active by default; SSH server not enabled.

### Performance
- ZRAM swap auto-sized to 50 % of RAM.
- zstd -3 compression on root filesystem.
- Plymouth boot splash with low-latency KMS.
- `preload` and `systemd-oomd` enabled for smoother multi-tasking.
