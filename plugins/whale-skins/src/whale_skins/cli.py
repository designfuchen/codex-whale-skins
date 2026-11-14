from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile

from .packages import SkinError, doctor, inspect_package, install, package_run, package_source


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Native Codex pet skin manager")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "install"):
        sub = commands.add_parser(name)
        sub.add_argument("source", type=Path)
        sub.add_argument("--allow-v1", action="store_true", help="Allow an existing legacy pet; new pets use v2")
        sub.add_argument("--id")
        sub.add_argument("--name")
        if name == "install":
            sub.add_argument("--codex-home", type=Path)
            sub.add_argument("--replace", action="store_true")
    sub = commands.add_parser("doctor")
    sub.add_argument("--codex-home", type=Path)
    sub = commands.add_parser("pack")
    sub.add_argument("run", type=Path)
    sub.add_argument("destination", type=Path)
    sub.add_argument("--id", required=True)
    sub.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.codex_home)
        elif args.command == "install":
            result = install(args.source, home=args.codex_home, replace=args.replace, allow_v1=args.allow_v1, pet_id=args.id, name=args.name)
        elif args.command == "validate":
            with package_source(args.source, pet_id=args.id, name=args.name) as root:
                result = inspect_package(root, allow_v1=args.allow_v1)
                result.pop("image", None)
                result.pop("manifest", None)
        else:
            result = package_run(args.run, args.destination, pet_id=args.id, name=args.name)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        return 0
    except (SkinError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
