from pathlib import Path

import pytest

from anki_generator import (cli, example_audio_enabled, parse_args,
                            parse_model_selection, resolve_csv_path,
                            resolve_images_root)
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


def test_from_md_resolves_markdown_path_and_models_all_uses_markdown_safe_models(tmp_path):
    md_path = tmp_path / "note.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | She trained in the dojo. |
""",
        encoding="utf-8",
    )

    options = parse_args(["--from-md", str(md_path), "--models", "all"])

    assert options.markdown_path == md_path
    assert options.csv_path is None
    assert options.selected_models == [1, 2, 5, 6]


def test_from_md_rejects_choice_models_with_usage_error(tmp_path):
    md_path = tmp_path / "note.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | She trained in the dojo. |
""",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--from-md", str(md_path), "--models", "3"])

    assert exc_info.value.code == 2


def test_validate_from_md_returns_success_for_valid_markdown(tmp_path):
    md_path = tmp_path / "note.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | She trained in the dojo. |
""",
        encoding="utf-8",
    )

    assert cli(["--validate", "--from-md", str(md_path)]) == 0


def test_from_md_and_csv_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--from-md", "x.md", "--csv", "y.csv"])

    assert exc_info.value.code == 2


def test_include_known_flag_is_parsed():
    options = parse_args(["--include-known"])

    assert options.include_known is True


def test_overwrite_media_requires_push():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--overwrite-media"])

    assert exc_info.value.code == 2


def test_push_options_are_parsed():
    options = parse_args(["--push", "--overwrite-media"])

    assert options.push is True
    assert options.overwrite_media is True


def test_example_audio_enabled_by_default():
    assert example_audio_enabled({}) is True


def test_example_audio_disabled_by_config():
    assert example_audio_enabled({"EXAMPLE_AUDIO": "FALSE"}) is False
    assert example_audio_enabled({"EXAMPLE_AUDIO": "false "}) is False


def write_md_fixture(tmp_path):
    md_path = tmp_path / "words.md"
    nl = chr(10)
    md_path.write_text(
        "| Word | Translation | Example |" + nl
        + "| --- | --- | --- |" + nl
        + "| dojo | додзё | She trained in the dojo. |" + nl,
        encoding="utf-8",
    )
    return md_path


def test_all_includes_cloze():
    assert parse_model_selection("all") == [1, 2, 3, 4, 5, 6]


def test_from_md_default_models_include_cloze(tmp_path):
    options = parse_args(["--from-md", str(write_md_fixture(tmp_path))])

    assert options.selected_models == [1, 2, 5, 6]


def test_from_md_allows_cloze_explicitly(tmp_path):
    options = parse_args(["--from-md", str(write_md_fixture(tmp_path)), "--models", "6"])

    assert options.selected_models == [6]


def test_images_root_flag_is_parsed():
    options = parse_args(["--images-root", "D:/pics"])

    assert options.images_root == "D:/pics"


def test_resolve_images_root_prefers_the_flag(tmp_path):
    root = resolve_images_root("D:/from-flag", {"IMAGES_ROOT": "D:/from-config"}, tmp_path)

    assert root == Path("D:/from-flag")


def test_resolve_images_root_falls_back_to_config(tmp_path):
    root = resolve_images_root(None, {"IMAGES_ROOT": "D:/from-config"}, tmp_path)

    assert root == Path("D:/from-config")


def test_resolve_images_root_defaults_to_project_images(tmp_path):
    assert resolve_images_root(None, {}, tmp_path) == tmp_path / "images"


def test_from_md_still_rejects_choice_models(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--from-md", str(write_md_fixture(tmp_path)), "--models", "3"])

    assert exc_info.value.code == 2
