import html
import re
from pathlib import Path

from utils.card_generator import CardData
from utils.csv_validator import validate_word_entries

WORD_ALIASES = ("word", "english")
TRANSLATION_ALIASES = ("translation", "russian")
EXAMPLE_ALIASES = ("example",)

# Split on pipes that are not escaped with a backslash (Obsidian escapes | in cells)
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


class MarkdownTableError(ValueError):
    """Raised when a markdown note does not contain a usable vocabulary table."""


def _clean_cell(value: str) -> str:
    value = html.unescape(value)
    value = value.replace("\\|", "|")
    value = value.replace("**", "").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", value).strip()


def _split_row(line: str) -> list:
    parts = _CELL_SPLIT.split(line.strip())
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [_clean_cell(part) for part in parts]


def _is_separator(line: str) -> bool:
    cells = _split_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _normalized_header(value: str) -> str:
    return re.sub(r"[^a-z]+", "", _clean_cell(value).casefold())


def _find_column(header: list, aliases: tuple, label: str) -> int:
    normalized = [_normalized_header(value) for value in header]
    # Prefix match so vault-style headers like "Word / Expression" or
    # "Translation (RU)" resolve to the expected columns
    for alias in aliases:
        for index, value in enumerate(normalized):
            if value.startswith(alias):
                return index
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
            # Data starts two lines below the header; +3 converts to 1-based
            return lines[index + 2:], columns, index + 3
    if found_table:
        raise MarkdownTableError("missing required columns")
    raise MarkdownTableError("no markdown table found")


def load_rows_from_markdown(path) -> tuple:
    """Parse the vocabulary table into (line_num, word, translation, example) rows.

    Returns (rows, errors) where errors describe malformed table lines with
    physical line numbers. Word-level validation is left to the caller
    (validate_word_entries). Raises MarkdownTableError when the note has no
    usable table at all.
    """
    markdown_path = Path(path)
    if not markdown_path.exists():
        raise MarkdownTableError(f"file not found: {markdown_path}")

    lines = markdown_path.read_text(encoding="utf-8-sig").splitlines()
    data_lines, columns, first_line_num = _find_table(lines)
    word_index, translation_index, example_index = columns
    required_width = max(columns) + 1

    rows = []
    errors = []
    for offset, line in enumerate(data_lines):
        if "|" not in line:
            break
        line_num = first_line_num + offset
        cells = _split_row(line)
        if not any(cells):
            continue
        if len(cells) < required_width:
            errors.append(f"line {line_num}: {len(cells)} cells instead of at least {required_width}")
            continue
        rows.append((line_num, cells[word_index], cells[translation_index], cells[example_index]))

    if not rows and not errors:
        raise MarkdownTableError("markdown table contains no cards")
    return rows, errors


def load_cards_from_markdown(path) -> list[CardData]:
    """Parse and validate a markdown note, raising on any problem."""
    rows, errors = load_rows_from_markdown(path)
    report = validate_word_entries(rows)
    problems = errors + report.errors
    if problems:
        raise MarkdownTableError("; ".join(problems))
    return [CardData(english, russian, example, [], [])
            for _line_num, english, russian, example in rows]
