# Contributing to SalomOS

> How to get involved.

Thanks for your interest in SalomOS! There are many ways to help.

## Quick links

- 🐛 [Issues](https://github.com/salom600/os222/issues) — bug reports
- 💡 [Discussions](https://github.com/salom600/os222/discussions) — ideas, questions
- 🔧 [Pull requests](https://github.com/salom600/os222/pulls) — code
- 🌐 [Translate](https://github.com/salom600/os222/tree/main/po) — i18n
- 🎨 [Themes](https://github.com/salom600/os222/discussions/categories/themes) — share your look

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/).
Be kind, be constructive, assume good intent.

## Development setup

```bash
git clone https://github.com/salom600/os222.git
cd os222
./scripts/dev-shell.sh    # drops you into a Debian container
```

Inside the container:

```bash
# Edit anything…
./scripts/build.sh
./scripts/test-boot.sh
```

## Project layout

| Path | What it is |
|---|---|
| `config/package-lists/*.list.chroot` | What packages go into the ISO |
| `config/hooks/normal/*.hook.chroot` | What runs during the build (in numeric order) |
| `config/includes.chroot/...` | Files copied 1:1 into the live system |
| `tools/salomos-*/` | First-party Python apps |
| `.github/workflows/` | CI/CD |
| `branding/` | Logo, wallpaper, icon assets |
| `docs/` | Documentation |

## How to add a new package to the ISO

1. Add the package name to `config/package-lists/desktop.list.chroot`
   (or a more specific list if you've created one)
2. (Optional) add it to `config/package-lists/salomos.list.chroot` if it's a
   SalomOS-shipped tool
3. Add the corresponding enable/disable in
   `config/hooks/normal/0004-configure-services.hook.chroot` (if it's a service)
4. Test locally: `./scripts/build.sh && qemu-system-x86_64 -m 2048 -cdrom live-image-*.iso`
5. Open a PR

## How to add a new SalomOS app

1. `mkdir tools/salomos-myapp/salomos_myapp`
2. Add `__init__.py`, `cli.py`, `__main__.py`, `ui/main_window.py`
3. Add a desktop entry: `config/includes.chroot/usr/share/applications/salomos-myapp.desktop`
4. Add a CLI wrapper: `config/includes.chroot/usr/bin/salomos-myapp`
5. Add to `config/package-lists/salomos.list.chroot`
6. Test and PR

## How to fix a bug

1. Search existing issues
2. If none, open one describing the bug
3. Reference it in your PR (`Closes #123`)
4. Add a regression test if possible

## How to add a new language

1. Create a `.po` file in `po/<lang>.po` (we use standard gettext)
2. Add the locale to `config/hooks/normal/0007-setup-salomos-dirs.hook.chroot`
3. Add a flag image to `branding/flags/`
4. Submit a PR

## Commit message style

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Flatpak support to SalomOS Store
fix(hwmanager): don't crash on unknown GPU vendor
docs: update INSTALL.md with MBR boot note
chore: bump version to 1.0.1
ci: add Python 3.12 to test matrix
```

Commit messages are also used to generate the changelog.

## Release process

1. Bump version in `VERSION`
2. Update `CHANGELOG.md`
3. Tag: `git tag v1.0.1`
4. Push tag: `git push origin v1.0.1`
5. CI builds, signs, and publishes to GitHub Releases

## Recognition

Contributors are listed in `CREDITS.md` (auto-generated from the git log).
Top contributors get a special "SalomOS Maintainer" badge in the app store.
