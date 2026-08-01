# Theming SalomOS

> How the Win11 / macOS theming works and how to customize it.

## Three built-in themes

| Theme | Look & feel | Base |
|---|---|---|
| **win11** (default) | Fluent design, rounded corners, acrylic surfaces, centered taskbar | Breeze dark + custom overrides |
| **macos** | WhiteSur Big Sur-style, light & airy, dock at the bottom | WhiteSur theme pack |
| **breeze** | Classic KDE Plasma 6, customizable | Breeze |

## Switch themes

### From the GUI

**Control Center → Appearance → Theme → click a card**.

### From the command line

```bash
sudo salomos-set-theme win11
sudo salomos-set-theme macos
sudo salomos-set-theme breeze
```

Sign out and back in for all changes to take effect.

## Where the files live

```
/usr/share/color-schemes/
├── BreezeClassicDark.colors      # KDE default dark
├── WhiteSurDark.colors           # macOS dark
└── SalomOSAccent.colors          # custom accent override

/usr/share/plasma/look-and-feel/
├── org.kde.breezedark.desktop/
├── org.kde.breeze.desktop/
└── org.kde.salomos.desktop/      # our custom LAF

/usr/share/icons/
├── Papirus-Dark/                 # default icon theme
├── Whitesur-dark/                # macOS icons
└── salomos/                      # our custom icon set

/usr/share/backgrounds/salomos/
├── wallpaper.png                 # 1920x1080
├── wallpaper-dark.png
└── wallpaper-light.png
```

## Custom accent color

```bash
sudo salomos-set-accent "#9334e6"   # purple
sudo salomos-set-accent "#0f9d58"   # green
sudo salomos-set-accent "#d93025"   # red
```

This writes a custom `SalomOSAccent.colors` and applies it via
`plasma-apply-colorscheme`.

## Custom wallpaper

```bash
sudo salomos-set-wallpaper /path/to/your/image.png
```

For all users:

```bash
sudo cp /path/to/image.png /usr/share/backgrounds/salomos/wallpaper.png
```

## Animation speed

```bash
sudo salomos-set-animations 1.0     # default
sudo salomos-set-animations 0.5     # snappier
sudo salomos-set-animations 0.0     # disable
```

## Custom icons

Drop a directory into `/usr/share/icons/` and select it from
**System Settings → Appearance → Icons**.

We ship:
- `salomos` (our base — see `/usr/share/icons/salomos/`)
- `Papirus-Dark` (default for Win11)
- `Whitesur-dark` (default for macOS)
- `Breeze` (default for Breeze)

## Custom fonts

We ship:
- **Inter** — UI font
- **JetBrains Mono** — monospace / terminal
- **Noto** / **Cantarell** — fallback
- **Hack** — fallback monospace

Add your own:

```bash
sudo cp -r my-font/ /usr/share/fonts/truetype/
sudo fc-cache -fv
```

## Custom cursors

```bash
sudo cp -r my-cursors/ /usr/share/icons/
# Then pick from System Settings → Appearance → Cursors
```

## Authoring a new look-and-feel package

A Plasma Look-and-Feel (LAF) is a `.desktop` file in
`/usr/share/plasma/look-and-feel/<id>/`:

```
/usr/share/plasma/look-and-feel/org.kde.salomos.mytheme.desktop
/usr/share/plasma/look-and-feel/org.kde.salomos.mytheme/
├── contents/
│   ├── default.svg
│   ├── previews/
│   │   ├── full.png
│   │   └── thumbnail.png
│   ├── widgets/
│   ├── layout-templates/
│   │   └── org.kde.desktopcontainment/
│   ├── splash/
│   └── lock/
└── metadata.json
```

See the [Plasma LAF docs](https://develop.kde.org/docs/features/look_and_feel/)
for full details.

## The `salomos-toolkit` styling API

All SalomOS native apps share a consistent look via
[`salomos_toolkit`](../tools/salomos-toolkit/salomos_toolkit/__init__.py).
The style string is:

```css
QMainWindow { background: #181a20; }
QFrame#Card { background: #23272e; border: 1px solid #3a3f4b; border-radius: 12px; }
QPushButton { background: #1a73e8; color: white; border: 0; padding: 10px 20px; border-radius: 8px; }
```

Change these hex values to re-skin every SalomOS app at once.
