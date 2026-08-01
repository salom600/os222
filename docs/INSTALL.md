# Installing SalomOS

> Step-by-step guide for first-time users.

## Before you start

You'll need:

- A USB stick with at least **4 GB** free (8 GB recommended)
- The latest **SalomOS ISO** — download from
  [Releases](https://github.com/salom600/os222/releases/latest)
- A few minutes (15-30 minutes for the install itself)

## 1. Create a bootable USB

### Linux / macOS

```bash
# Find your USB device (be careful!)
lsblk
# e.g. /dev/sdb

# Flash
sudo dd if=salomos-1.0-amd64.iso of=/dev/sdX bs=4M status=progress conv=fdatasync
sync
```

### Windows

Use [Rufus](https://rufus.ie) or [balenaEtcher](https://etcher.balena.io).

1. Open Rufus / Etcher
2. Pick the ISO
3. Pick your USB stick
4. Click "Start"

## 2. Boot from USB

1. Plug in the USB stick
2. Restart your computer
3. Press the boot-menu key (F12 / F2 / DEL — depends on your BIOS)
4. Pick the USB stick from the list
5. You'll see the SalomOS GRUB menu

## 3. Try it first (recommended)

Pick **"SalomOS Live"** from the menu. You'll boot into a full desktop without
touching your hard drive.

In the live session you can:
- Browse the web
- Try the Store
- Test GPU drivers
- Verify Wi-Fi / network
- Make sure everything works

When you're ready, double-click the **"Install SalomOS"** icon on the desktop.

## 4. Run the installer

The installer is a step-by-step wizard:

1. **Welcome** — read the release notes
2. **Language & keyboard** — pick yours
3. **Theme** — Windows 11, macOS, or SalomOS Breeze
4. **Disk** — pick the disk to install to. SalomOS defaults to **BTRFS + ZSTD**
   for snapshots and compression. Pick "Erase disk" if this is a clean install.
5. **User account** — your name, username, password
6. **Summary** — review, then click Install
7. Wait 5-15 minutes (it'll show progress)
8. **Done!** — click Restart, remove the USB stick

## 5. First boot (after install)

When you boot into your new installation, the **SalomOS First-Boot Wizard**
will run:

1. Confirm language
2. Confirm theme
3. Detect hardware and install any missing drivers
4. Configure privacy
5. Done — desktop appears

## 6. Post-install tips

### Update the system

```bash
salomos-update
# or
sudo apt update && sudo apt upgrade
```

### Install apps

Open **SalomOS Store** from the application menu (or run `salomos-store`).

### Change theme

```bash
# Switch between Win11, macOS, and Breeze
sudo salomos-set-theme win11
sudo salomos-set-theme macos
sudo salomos-set-theme breeze
```

Or use **Control Center → Appearance**.

### Auto-installed GPU drivers

Drivers are installed on first boot by **SalomOS Hardware Manager**. You can
re-run detection any time:

```bash
salomos-hwmanager detect
salomos-hwmanager gpu
salomos-hwmanager install-gpu
```

### Snapshots / rollback

**Timeshift** is installed by default. Open **Control Center → Backup** to
manage snapshots.

```bash
sudo timeshift --create    # snapshot now
sudo timeshift --list      # list snapshots
sudo timeshift --restore   # restore (reboots)
```

## Troubleshooting

### Wi-Fi doesn't work

```bash
salomos-hwmanager detect
# Look for your NIC; if no driver is listed, install one:
sudo apt install firmware-iwlwifi  # Intel
sudo apt install firmware-atheros  # Atheros
sudo apt install firmware-realtek  # Realtek
```

### Black screen on boot

Boot into safe mode from GRUB:
- Edit the boot entry (press `e`)
- Append `nomodeset` to the `linux` line
- Press `Ctrl+X` to boot

Then run the Hardware Manager to install the right GPU driver.

### Sound doesn't work

```bash
pavucontrol
# Check the output device
```

### Touchpad not working

```bash
sudo apt install xserver-xorg-input-synaptics
```

## Getting help

- 🐛 [Open an issue](https://github.com/salom600/os222/issues)
- 💬 [Discussions](https://github.com/salom600/os222/discussions)
- 📖 [Wiki](https://github.com/salom600/os222/wiki)
