from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from search_runner import difficulty_matches_result


def test_single_difficulty_uses_word_boundary_match():
    assert difficulty_matches_result("Expert chart", ["expert"])
    assert not difficulty_matches_result("Hard chart", ["expert"])


def test_multiple_difficulties_use_letter_match():
    assert difficulty_matches_result("EMHX", ["easy", "medium", "hard", "expert"])
    assert difficulty_matches_result("HX", ["hard", "expert"])
    assert not difficulty_matches_result("H", ["hard", "expert"])


def test_empty_selection_ignores_difficulty():
    assert difficulty_matches_result("No difficulty text here", [])
