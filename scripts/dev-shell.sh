#!/bin/bash
# scripts/dev-shell.sh — drop into a Debian container for development.
set -e
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null; then
  echo "❌ Docker not found." >&2
  exit 1
fi

docker run --rm -it --privileged \
  --tmpfs /tmp:size=4g \
  --tmpfs /var/cache:size=4g \
  -v "$PWD:/salomos" \
  -w /salomos \
  debian:bookworm \
  bash -c '
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends \
      sudo ca-certificates curl git gnupg wget \
      python3 python3-pip \
      live-build debootstrap squashfs-tools xorriso isolinux syslinux-common \
      grub-pc-bin grub-efi-amd64-bin grub-common \
      fakeroot linux-image-amd64 vim nano
    exec bash
  '
