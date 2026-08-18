from pathlib import Path

import pytest

from anki_generator import parse_args, parse_model_selection, resolve_csv_path
from utils.card_generator import CardGenerator


def test_resolve_csv_path_uses_explicit_path(tmp_path):
    csv_path = tmp_path / "words.csv"
    csv_path.write_text("english,russian\n", encoding="utf-8")

    assert resolve_csv_path(str(csv_path), tmp_path / "resources") == csv_path


def test_resolve_csv_path_falls_back_to_resources_for_bare_name(tmp_path):
    resources_dir = tmp_path / "resources"
    resources_dir.mkdir()
    csv_path = resources_dir / "words.csv"
    csv_path.write_text("english,russian\n", encoding="utf-8")

    assert resolve_csv_path("words.csv", resources_dir) == csv_path


def test_resolve_csv_path_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_csv_path("missing.csv", tmp_path)


def test_parse_model_selection_accepts_all():
    assert parse_model_selection("all") == sorted(CardGenerator.MODEL_NAMES.keys())


def test_parse_model_selection_deduplicates_and_sorts_numbers():
    assert parse_model_selection("5,1,5") == [1, 5]


def test_parse_model_selection_rejects_unknown_model():
    with pytest.raises(ValueError, match="unknown model"):
        parse_model_selection("0")


def test_validate_mode_ignores_invalid_models():
    options = parse_args(["--validate", "--models", "0"])

    assert options.validate_only is True
    assert options.selected_models is None


def test_planned_flags_return_usage_error():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--push"])

    assert exc_info.value.code == 2
