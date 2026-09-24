from pathlib import Path
import json
import sys
import os

# ensure workspace root is on path so 'src' package imports work
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.search_runner import run_search


def progress(msg):
    print(msg)


if __name__ == '__main__':
    artists = ["Daft Punk"]
    difficulties = {"easy": True, "medium": True, "hard": True, "expert": True}
    print("Starting run_search test...")
    summary = run_search(artists, difficulties, on_progress=progress, close_browser=True)
    print("Summary:")
    print(json.dumps(summary, indent=2))
