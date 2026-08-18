import pytest

from utils.md_loader import MarkdownTableError, load_cards_from_markdown, load_rows_from_markdown


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


def test_reads_vault_style_header_variants(tmp_path):
    md_path = tmp_path / "vault.md"
    md_path.write_text(
        """
| Word / Expression | Translation (RU) | Example from the text |
| --- | --- | --- |
| dojo | додзё | She trained in the **dojo**. |
""",
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert cards[0].english == "dojo"
    assert cards[0].russian == "додзё"
    assert cards[0].example == "She trained in the dojo."


def test_unescapes_escaped_pipes_in_cells(tmp_path):
    backslash = chr(92)
    md_path = tmp_path / "pipes.md"
    md_path.write_text(
        "| Word | Translation | Example |" + chr(10)
        + "| --- | --- | --- |" + chr(10)
        + f"| pipe word | перевод | Example with [[link{backslash}|alias]] inside. |" + chr(10),
        encoding="utf-8",
    )

    cards = load_cards_from_markdown(md_path)

    assert cards[0].example == "Example with [[link|alias]] inside."


def test_duplicate_words_are_rejected(tmp_path):
    md_path = tmp_path / "dups.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | First. |
| Dojo | другой | Second. |
""",
        encoding="utf-8",
    )

    with pytest.raises(MarkdownTableError, match="duplicate word"):
        load_cards_from_markdown(md_path)


def test_hostile_characters_in_word_are_rejected(tmp_path):
    md_path = tmp_path / "hostile.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| sla/sh | перевод | Broken word. |
""",
        encoding="utf-8",
    )

    with pytest.raises(MarkdownTableError, match="characters that break"):
        load_cards_from_markdown(md_path)


def test_short_rows_are_reported_with_line_numbers(tmp_path):
    md_path = tmp_path / "short.md"
    md_path.write_text(
        """
| Word | Translation | Example |
| --- | --- | --- |
| dojo | додзё | Fine row. |
| broken row |
""",
        encoding="utf-8",
    )

    rows, errors = load_rows_from_markdown(md_path)

    assert len(rows) == 1
    assert errors == ["line 5: 1 cells instead of at least 3"]
