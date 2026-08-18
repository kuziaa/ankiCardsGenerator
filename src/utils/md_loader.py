import html
import re
from pathlib import Path

from utils.card_generator import CardData

WORD_ALIASES = {"word", "english"}
TRANSLATION_ALIASES = {"translation", "russian"}
EXAMPLE_ALIASES = {"example"}


class MarkdownTableError(ValueError):
    """Raised when a markdown note does not contain a usable vocabulary table."""


def _clean_cell(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("**", "").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def _split_row(line: str) -> list:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [_clean_cell(cell) for cell in line.split("|")]


def _is_separator(line: str) -> bool:
    cells = _split_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _normalized_header(value: str) -> str:
    return re.sub(r"[^a-z]+", "", _clean_cell(value).casefold())


def _find_column(header: list, aliases: set, label: str) -> int:
    normalized = [_normalized_header(value) for value in header]
    for alias in aliases:
        if alias in normalized:
            return normalized.index(alias)
    raise MarkdownTableError(f"missing required columns: {label}")


def _find_columns(header: list) -> tuple:
    return (
        _find_column(header, WORD_ALIASES, "word/english"),
        _find_column(header, TRANSLATION_ALIASES, "translation/russian"),
        _find_column(header, EXAMPLE_ALIASES, "example"),
    )


def _find_table(lines: list) -> tuple:
    found_table = False
    for index in range(len(lines) - 1):
        if "|" in lines[index] and _is_separator(lines[index + 1]):
            found_table = True
            header = _split_row(lines[index])
            try:
                columns = _find_columns(header)
            except MarkdownTableError:
                continue
            return header, lines[index + 2:], columns
    if found_table:
        raise MarkdownTableError("missing required columns")
    raise MarkdownTableError("no markdown table found")


def load_cards_from_markdown(path) -> list[CardData]:
    markdown_path = Path(path)
    if not markdown_path.exists():
        raise MarkdownTableError(f"file not found: {markdown_path}")

    lines = markdown_path.read_text(encoding="utf-8-sig").splitlines()
    _header, data_lines, columns = _find_table(lines)
    word_index, translation_index, example_index = columns
    required_width = max(word_index, translation_index, example_index) + 1

    cards = []
    for line in data_lines:
        if "|" not in line:
            break
        cells = _split_row(line)
        if len(cells) < required_width:
            continue
        if not any(cells):
            continue
        english = cells[word_index]
        russian = cells[translation_index]
        example = cells[example_index]
        if not english or not russian:
            raise MarkdownTableError("empty required word/translation cell")
        cards.append(CardData(english, russian, example, [], []))

    if not cards:
        raise MarkdownTableError("markdown table contains no cards")
    return cards
