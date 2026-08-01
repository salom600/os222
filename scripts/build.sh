#!/bin/bash
# scripts/build.sh — build SalomOS ISO inside Docker.
#
# Usage:
#   ./scripts/build.sh               # amd64, default
#   ./scripts/build.sh i386          # i386 build
#   ./scripts/build.sh arm64         # arm64 build
#   ./scripts/build.sh --no-docker   # build directly on host (Debian only)
#
# Requires: docker (default) or live-build on a Debian host.
set -e

# ---- args -----------------------------------------------------------------
ARCH="${1:-amd64}"
USE_DOCKER=true
DOCKER_IMAGE="${DOCKER_IMAGE:-debian:bookworm}"
SALOMOS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$ARCH" = "--no-docker" ]; then
  USE_DOCKER=false
  ARCH="${2:-amd64}"
fi

if [ "$ARCH" = "--help" ] || [ "$ARCH" = "-h" ]; then
  sed -n '2,12p' "$0"
  exit 0
fi

# ---- sanity checks --------------------------------------------------------
if [ "$USE_DOCKER" = true ] && ! command -v docker >/dev/null; then
  echo "❌ Docker not found. Re-run with --no-docker on a Debian system, or install Docker." >&2
  exit 1
fi

# ---- banner ---------------------------------------------------------------
cat <<EOF
╔════════════════════════════════════════════════════════╗
║   SalomOS 1.0 — Aurora                                ║
║   Building ISO for: $ARCH
║   Mode:           $([ "$USE_DOCKER" = true ] && echo "docker ($DOCKER_IMAGE)" || echo "host")
║   Time:           $(date -u +%Y-%m-%dT%H:%M:%SZ)
╚════════════════════════════════════════════════════════╝
EOF

cd "$SALOMOS_ROOT"

if [ "$USE_DOCKER" = true ]; then
  exec docker run --rm --privileged \
    --tmpfs /tmp:size=4g \
    --tmpfs /var/cache:size=4g \
    -v "$SALOMOS_ROOT:/salomos" \
    -w /salomos \
    "$DOCKER_IMAGE" \
    bash -c '
      set -e
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y --no-install-recommends \
        sudo ca-certificates curl git gnupg wget \
        python3 python3-pip \
        live-build debootstrap squashfs-tools xorriso isolinux syslinux-common \
        grub-pc-bin grub-efi-amd64-bin grub-efi-arm64-bin grub-common \
        fakeroot
      case "'"$ARCH"'" in
        amd64) apt-get install -y --no-install-recommends linux-image-amd64 ;;
        i386)  apt-get install -y --no-install-recommends linux-image-686-pae ;;
        arm64) apt-get install -y --no-install-recommends linux-image-arm64 ;;
      esac
      ./auto/config "'"$ARCH"'" bookworm
      time ./auto/build 2>&1 | tee build.log
    '
else
  # Build directly on host
  ./auto/config "$ARCH" bookworm
  time ./auto/build 2>&1 | tee build.log
fi

ISO=$(ls -1 live-image-*.hybrid.iso 2>/dev/null | head -1 || true)
if [ -n "$ISO" ]; then
  echo ""
  echo "✅ Build complete: $ISO"
  echo "   Size: $(du -h "$ISO" | cut -f1)"
  echo "   SHA256: $(sha256sum "$ISO" | cut -d' ' -f1)"
  echo ""
  echo "Next steps:"
  echo "  1. Flash to USB: sudo dd if=$ISO of=/dev/sdX bs=4M status=progress conv=fdatasync"
  echo "  2. Or test in a VM: qemu-system-x86_64 -m 2048 -cdrom $ISO -boot d"
fi
