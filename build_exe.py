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

    icon_path = ROOT / "src" / "app.ico"
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "DJCloneHero",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
    ]

    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])

    args.extend([
        "--add-data",
        "src;src",
        "--add-data",
        "data;data",
        "src/main.py",
    ])

    run(args)
    exe_path = output_dir / "DJCloneHero.exe"
    print("\nBuild complete. Executable:", exe_path)
    print("Share-ready artifact:", exe_path)
