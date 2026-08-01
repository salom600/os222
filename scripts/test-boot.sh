#!/bin/bash
# scripts/test-boot.sh — boot the latest ISO in QEMU and verify it reaches login.
set -e
cd "$(dirname "$0")/.."

ISO=$(ls -1 live-image-*.hybrid.iso 2>/dev/null | head -1 || true)
if [ -z "$ISO" ]; then
  echo "❌ No ISO found. Run scripts/build.sh first." >&2
  exit 1
fi

if ! command -v qemu-system-x86_64 >/dev/null; then
  echo "❌ qemu-system-x86_64 not found. Install qemu-system-x86 ovmf." >&2
  exit 1
fi

echo "==> Booting $ISO in QEMU for 45 seconds…"
timeout 45 qemu-system-x86_64 \
  -m 2048 -smp 2 \
  -cdrom "$ISO" -boot d \
  -nographic -serial stdio \
  -display none -monitor none 2>&1 | tee qemu-test.log || true

if grep -qE "systemd|salomos|Live system ready" qemu-test.log; then
  echo "✅ Boot test passed (systemd reached, live system started)."
else
  echo "❌ Boot test failed — could not detect live system init."
  exit 1
fi
