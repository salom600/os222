# Dockerfile for building SalomOS in a clean Debian 12 environment.
# This is used both locally and in CI.

FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Tools to install
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    ca-certificates \
    curl \
    git \
    gnupg \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    live-build \
    debootstrap \
    squashfs-tools \
    xorriso \
    isolinux \
    syslinux-common \
    syslinux-efi \
    grub-pc-bin \
    grub-efi-amd64-bin \
    grub-efi-arm64-bin \
    grub-common \
    fakeroot \
    qemu-system-x86 \
    qemu-system-arm \
    ovmf \
    linux-image-amd64 \
    linux-image-arm64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /salomos
COPY . /salomos

# Make all the scripts executable
RUN chmod +x auto/config auto/build auto/clean scripts/*.sh 2>/dev/null || true

# Default command: build
CMD ["./auto/config", "amd64", "bookworm"]
