#!/usr/bin/env python3
"""Simple CLI to run and manage VN projects."""
import argparse
import sys
import os

# When running from the project root, ensure `src/` is on `sys.path`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

try:
    from vn_engine.core import VNApp
except ModuleNotFoundError as e:
    missing = getattr(e, "name", None) or str(e)
    print(f"Missing Python dependency: {missing}")
    print("Install the project requirements in your active virtualenv:")
    print()
    print("Windows (PowerShell):")
    print("  .venv\\Scripts\\Activate.ps1")
    print("  pip install -r requirements.txt")
    print()
    print("macOS / Linux:")
    print("  source .venv/bin/activate")
    print("  pip install -r requirements.txt")
    print()
    print("Or install the minimal runtime packages:")
    print("  pip install pygame PyYAML Pillow")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="vn")
    sub = parser.add_subparsers(dest="command")
    run_parser = sub.add_parser('run')
    run_parser.add_argument('story', nargs='?', default='examples/story.yaml')

    args = parser.parse_args()
    if args.command == 'run':
        app = VNApp(args.story)
        app.run()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
