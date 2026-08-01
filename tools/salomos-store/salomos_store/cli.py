#!/usr/bin/env python3
"""SalomOS Store CLI."""
from __future__ import annotations

import argparse
import json
import sys

from salomos_toolkit import get_logger
log = get_logger("salomos-store.cli")

from .backends import Store, App


def cmd_list(args):
    s = Store()
    apps = s.list(query=args.query, category=args.category)
    if args.json:
        print(json.dumps([a.to_dict() for a in apps], indent=2))
        return 0
    for a in apps[:args.limit or 50]:
        inst = "✓" if a.installed else " "
        size = f"{a.size/1024/1024:.1f} MB" if a.size else ""
        print(f"[{inst}] {a.backend:8} {a.category:12} {a.name:30}  {a.summary[:60]:60}  {size}")
    return 0


def cmd_search(args):
    return cmd_list(argparse.Namespace(query=args.query, category=None, json=False, limit=args.limit))


def cmd_install(args):
    s = Store()
    for pkg in args.packages:
        # Try to find by name across all backends
        for a in s.list(query=pkg):
            if a.id == pkg or a.name.lower() == pkg.lower():
                print(f"Installing {a.id} from {a.backend}…")
                ok = s.install(a)
                print(f"  {'OK' if ok else 'FAIL'}: {a.id}")
                break
        else:
            print(f"  Not found: {pkg}", file=sys.stderr)
    return 0


def cmd_remove(args):
    s = Store()
    for pkg in args.packages:
        for a in s.list(query=pkg):
            if a.id == pkg or a.name.lower() == pkg.lower():
                print(f"Removing {a.id} from {a.backend}…")
                ok = s.remove(a)
                print(f"  {'OK' if ok else 'FAIL'}: {a.id}")
                break
        else:
            print(f"  Not found: {pkg}", file=sys.stderr)
    return 0


def cmd_categories(_args):
    s = Store()
    for cat, count in s.categories():
        print(f"  {cat:20} {count:5}")
    return 0


def cmd_gui(_args):
    try:
        from .ui.main_window import MainWindow
        from PyQt6.QtWidgets import QApplication
    except ImportError as e:
        print(f"GUI unavailable: {e}", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    app.setApplicationName("SalomOS Store")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


def build_parser():
    p = argparse.ArgumentParser(prog="salomos-store", description="SalomOS Store")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="List available apps")
    s.add_argument("--query", "-q")
    s.add_argument("--category", "-c")
    s.add_argument("--limit", "-n", type=int)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("search", help="Search apps")
    s.add_argument("query")
    s.add_argument("--limit", "-n", type=int)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("install", help="Install one or more apps")
    s.add_argument("packages", nargs="+")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("remove", help="Remove one or more apps")
    s.add_argument("packages", nargs="+")
    s.set_defaults(func=cmd_remove)

    s = sub.add_parser("categories", help="List categories with counts")
    s.set_defaults(func=cmd_categories)

    s = sub.add_parser("gui", help="Launch GUI")
    s.set_defaults(func=cmd_gui)

    return p


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
