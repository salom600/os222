#!/bin/bash
# scripts/clean.sh — full clean.
set -e
cd "$(dirname "$0")/.."

echo "==> Cleaning live-build artifacts…"
./auto/clean

echo "==> Cleaning build artifacts…"
rm -rf cache/ build/ downloads/ qemu-test/
rm -f *.iso *.iso.sha256 *.iso.b2 build.log qemu-test.log

echo "==> Done."
