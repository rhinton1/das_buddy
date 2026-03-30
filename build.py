#!/usr/bin/env python
"""
build.py -- packages das_buddy into a standalone executable.

Usage (from the project root):
    python build.py

Output:
    dist/das_buddy/das_buddy.exe   ← run this to launch the app
    dist/das_buddy/                ← zip this folder to distribute
"""

import os
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
CLT  = os.path.join(ROOT, "clt")
SVR  = os.path.join(ROOT, "svr")

# Force UTF-8 output on Windows so plain print() never crashes
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run(cmd, **kwargs):
    print(f"\n> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.run(cmd, check=True, **kwargs)


def main():
    print("\n-- Step 1/3  Building React frontend (npm run build) ...")
    run(["npm", "run", "build"], cwd=CLT, shell=(sys.platform == "win32"))

    dist_dir = os.path.join(CLT, "dist")
    if not os.path.isdir(dist_dir):
        print("ERROR: clt/dist not found after npm build. Aborting.")
        sys.exit(1)
    print(f"  OK  Frontend built -> {dist_dir}")

    print("\n-- Step 2/3  Ensuring PyInstaller is installed ...")
    run([sys.executable, "-m", "pip", "install", "--quiet", "pyinstaller"])

    print("\n-- Step 3/3  Running PyInstaller ...")
    run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "das_buddy.spec"],
        cwd=ROOT,
    )

    exe_path = os.path.join(ROOT, "dist", "das_buddy.exe")
    if os.path.isfile(exe_path):
        print(f"\nBuild complete!\n")
        print(f"   Executable : {exe_path}")
        print(f"   Share      : send just  dist/das_buddy.exe  -- that's it!")
        print(f"\n   Run it     : .\\dist\\das_buddy.exe")
    else:
        print("\nWARN: Build finished but exe not found -- check PyInstaller output above.")


if __name__ == "__main__":
    main()
