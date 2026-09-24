import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    output_dir = ROOT / "dist"
    output_dir.mkdir(exist_ok=True)

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "DJCloneHero",
        "--add-data",
        "src;src",
        "--add-data",
        "data;data",
        "src/main.py",
    ]

    run(args)
    print("\nBuild complete. Executable:", output_dir / "DJCloneHero.exe")
