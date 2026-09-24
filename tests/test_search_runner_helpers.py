import json
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from search_runner import (
    append_download_entry,
    clear_download_history,
    extract_chart_artist,
    format_download_success_message,
    format_download_skip_message,
    get_downloads_root,
    is_cover_title,
    should_stop_scrolling,
    title_matches_artist,
)

from main import should_show_artist_placeholder


def test_extract_chart_artist_uses_prefix_before_separator():
    assert extract_chart_artist("The Artist - Song Title") == "The Artist"
    assert extract_chart_artist("The Artist – Song Title") == "The Artist"
    assert extract_chart_artist("The Artist / Song Title") == "The Artist / Song Title"


def test_is_cover_title_rejects_cover_variants():
    assert is_cover_title("Artist - Cover") is True
    assert is_cover_title("Cover of a Song") is True
    assert is_cover_title("Artist - Song Title") is False


def test_clear_download_history_resets_manifest(tmp_path):
    manifest_path = tmp_path / "downloaded_files.json"
    manifest_path.write_text("[{\"artist\": \"A\"}]", encoding="utf-8")
    manifest = [{"artist": "A"}]

    result = clear_download_history(manifest, manifest_path)

    assert result == []
    assert not manifest_path.exists()


def test_download_status_messages_are_concise():
    assert format_download_success_message("The Beatles", "Yesterday") == "Downloaded The Beatles - Yesterday (Charter)"
    assert format_download_skip_message("The Beatles", "Yesterday") == "Skipping 'The Beatles - Yesterday' already recorded in download manifest"


def test_should_show_artist_placeholder_only_when_idle_and_empty():
    assert should_show_artist_placeholder("", False) is True
    assert should_show_artist_placeholder("", True) is False
    assert should_show_artist_placeholder("The Beatles", False) is False
    assert should_show_artist_placeholder("The Beatles", True) is False


def test_downloads_root_uses_standard_user_downloads_folder():
    root = get_downloads_root()
    assert root == Path.home() / "Downloads" / "DJ Extractor"


def test_title_matches_artist_requires_exact_artist_match():
    assert title_matches_artist("Ado - New World", "Ado") is True
    assert title_matches_artist("Ado & Camellia - New World", "Ado") is True
    assert title_matches_artist("Ado / Camellia - New World", "Ado") is True
    assert title_matches_artist("Adonis - New World", "Ado") is False
    assert title_matches_artist("The Ado - New World", "Ado") is False


def test_should_stop_scrolling_only_after_stable_result_count():
    assert should_stop_scrolling(current_count=10, previous_count=10, stable_rounds=2, bottom_reached=True) is False
    assert should_stop_scrolling(current_count=10, previous_count=10, stable_rounds=8, bottom_reached=True) is True
    assert should_stop_scrolling(current_count=12, previous_count=10, stable_rounds=8, bottom_reached=True) is False
    assert should_stop_scrolling(current_count=None, previous_count=10, stable_rounds=8, bottom_reached=True) is False
    assert should_stop_scrolling(current_count=10, previous_count=10, stable_rounds=8, loading=True, bottom_reached=True) is False
    assert should_stop_scrolling(current_count=10, previous_count=10, stable_rounds=8, bottom_reached=False) is False
    assert should_stop_scrolling(current_count=10, previous_count=10, stable_rounds=8, bottom_reached=True, height_delta=10) is False


def test_append_download_entry_persists_full_history_and_dedupes(tmp_path):
    manifest_path = tmp_path / "downloaded_files.json"
    first = {"artist": "Artist A", "title": "Song 1", "filename": "Song 1.zip", "sha256": "abc"}
    second = {"artist": "Artist A", "title": "Song 2", "filename": "Song 2.zip", "sha256": "def"}

    manifest = append_download_entry(manifest_path, first)
    manifest = append_download_entry(manifest_path, second, existing_manifest=manifest)
    manifest = append_download_entry(manifest_path, first, existing_manifest=manifest)

    assert len(manifest) == 2
    assert manifest[0]["title"] == "Song 1"
    assert manifest[1]["title"] == "Song 2"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))[1]["title"] == "Song 2"
