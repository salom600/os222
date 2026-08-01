# Building SalomOS

> How to build the ISO from source.

## Prerequisites

Choose **one** of:

### A. Docker (recommended)

- Docker 20.10+ (any host OS)
- ~10 GB free disk
- 4 GB free RAM (build uses up to 4 GB)

### B. Native Debian 12 host

- Debian 12 "Bookworm" (same release as the target)
- `sudo` access
- ~10 GB free disk
- 4 GB free RAM

> The native path is **not** recommended because it modifies your system.

## Quick start

```bash
git clone https://github.com/salom600/os222.git
cd os222
./scripts/build.sh                # Docker build, amd64
ls -lh live-image-*.hybrid.iso
```

That's it. The build takes 15-45 minutes depending on hardware.

## Build options

```bash
# Build for a different architecture
./scripts/build.sh arm64
./scripts/build.sh i386

# Build without Docker (Debian host)
./scripts/build.sh --no-docker

# Open a development shell
./scripts/dev-shell.sh
```

## What happens during a build

1. `auto/config` runs `lb config` with all our options
2. `live-build` debootstraps a minimal Debian into a chroot
3. Package lists in `config/package-lists/*.list.chroot` are installed
4. Hooks in `config/hooks/normal/*.hook.chroot` run in numeric order
5. Files in `config/includes.chroot/...` are copied into the chroot
6. The chroot is squashed (zstd -3) and assembled into a hybrid ISO
7. The ISO is signed for UEFI + legacy boot

## Output

A hybrid ISO at `live-image-amd64.hybrid.iso` (typically 2-3 GB).

It works on:
- USB stick (dd or Etcher)
- DVD
- Virtual machines (QEMU, VirtualBox, VMware, Hyper-V)
- Direct boot via GRUB chain-load

## Testing the build

### Quick smoke test

```bash
./scripts/test-boot.sh
```

Boots the ISO in QEMU for 45 seconds, checks the log for `systemd` and
`salomos` strings.

### Manual test

```bash
qemu-system-x86_64 -m 2048 -smp 2 -cdrom live-image-amd64.hybrid.iso -boot d
```

## Cleaning

```bash
./scripts/clean.sh   # full clean
```

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `lb: command not found` | live-build not installed | `apt install live-build` |
| `debootstrap failed` | network issue or wrong mirror | `lb config --mirror-bootstrap http://deb.debian.org/debian` |
| Out of disk space | build artifacts take ~5 GB | `df -h .`; free space |
| ISO won't boot | UEFI shim missing | install `grub-efi-amd64-signed` in build host |
| `Permission denied` writing `/salomos` | wrong user in Docker | `sudo chown -R $USER:$USER .` |

## Verifying the ISO

```bash
sha256sum live-image-amd64.hybrid.iso
# Compare to the value in the build artifact on GitHub Actions
```

## Continuous integration

Every push to `main` triggers a build via GitHub Actions. See
[`.github/workflows/build-iso.yml`](../.github/workflows/build-iso.yml) for details.
