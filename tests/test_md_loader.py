import pytest

from utils.md_loader import MarkdownTableError, load_cards_from_markdown


def test_load_cards_from_markdown_parses_simple_table(tmp_path):
    md_path = tmp_path / "words.md"
    md_path.write_text(
        """
Intro text.

| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | She trained in the dojo. |
""",
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert len(cards) == 1
    assert cards[0].english == "dojo"
    assert cards[0].russian == "додзё"
    assert cards[0].example == "She trained in the dojo."
    assert cards[0].incorrect_en == []
    assert cards[0].incorrect_ru == []


def test_load_cards_from_markdown_strips_markdown_and_html_entities(tmp_path):
    md_path = tmp_path / "words.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| **look up** | *искать* | Use `look up` &amp; remember it. |
""",
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert cards[0].english == "look up"
    assert cards[0].russian == "искать"
    assert cards[0].example == "Use look up & remember it."


def test_load_cards_from_markdown_supports_column_aliases(tmp_path):
    md_path = tmp_path / "aliases.md"
    md_path.write_text(
        """
| English | Russian | Example |
| --- | --- | --- |
| cut corners | срезать углы | Do not cut corners. |
""",
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert cards[0].english == "cut corners"
    assert cards[0].russian == "срезать углы"
    assert cards[0].example == "Do not cut corners."


def test_load_cards_from_markdown_skips_non_vocabulary_tables(tmp_path):
    md_path = tmp_path / "multiple-tables.md"
    md_path.write_text(
        """
| Date | Notes |
| --- | --- |
| 2026-08-18 | Review vocabulary below |

| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | She trained in the dojo. |
""",
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert len(cards) == 1
    assert cards[0].english == "dojo"


def test_load_cards_from_markdown_reports_missing_table(tmp_path):
    md_path = tmp_path / "empty.md"
    md_path.write_text("No vocabulary table here.", encoding="utf-8")

    with pytest.raises(MarkdownTableError, match="markdown table"):
        load_cards_from_markdown(md_path)


def test_load_cards_from_markdown_reports_missing_required_columns(tmp_path):
    md_path = tmp_path / "missing-columns.md"
    md_path.write_text(
        """
| Word | Notes |
| --- | --- |
| dojo | place for training |
""",
        encoding="utf-8",
    )

    with pytest.raises(MarkdownTableError, match="missing required columns"):
        load_cards_from_markdown(md_path)
