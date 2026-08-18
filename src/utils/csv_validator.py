"""Pre-flight CSV validator: catches broken rows before the expensive media phase."""

import csv
import re
import unicodedata
from pathlib import Path

from utils.card_generator import safe_media_name

EXPECTED_COLUMNS = [
    'english', 'russian', 'example',
    'incorrectEnVariant1', 'incorrectEnVariant2',
    'incorrectEnVariant3', 'incorrectEnVariant4',
    'incorrectRuVariant1', 'incorrectRuVariant2',
    'incorrectRuVariant3', 'incorrectRuVariant4',
]

# Characters that break media file names, <img src> or the scramble JS
HOSTILE_CHARS = re.compile(r'[\/:*?"<>|]')


def _norm(text: str) -> str:
    """Compare form: casefold + diacritics stripped, so 'dojō' matches 'dojo'."""
    decomposed = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.row_count = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _check_word(result, line_num, english, russian, example,
                seen_words, seen_names) -> bool:
    """Word-level checks shared by all input formats. Returns False when the row is unusable."""
    if not english or not russian:
        result.errors.append(f"line {line_num}: empty english or russian field")
        return False
    if not example:
        result.warnings.append(f"line {line_num} ({english}): empty example")

    if HOSTILE_CHARS.search(english):
        result.errors.append(
            f"line {line_num} ({english}): english contains characters that break "
            r'file names or card templates: \ / : * ? " < > |')

    word_key = _norm(english)
    if word_key in seen_words:
        result.errors.append(
            f"line {line_num}: duplicate word '{english}' "
            f"(first seen at line {seen_words[word_key]})")
    else:
        seen_words[word_key] = line_num

    media_name = safe_media_name(english)
    if media_name in seen_names and seen_names[media_name][0] != word_key:
        result.errors.append(
            f"line {line_num}: '{english}' collides with "
            f"'{seen_names[media_name][1]}' after filename sanitization")
    else:
        seen_names.setdefault(media_name, (word_key, english))
    return True


def validate_word_entries(entries) -> ValidationResult:
    """Validate (line_num, word, translation, example) rows from a non-CSV source."""
    result = ValidationResult()
    seen_words = {}
    seen_names = {}
    for line_num, english, russian, example in entries:
        result.row_count += 1
        _check_word(result, line_num, english, russian, example, seen_words, seen_names)
    return result


def validate_csv(csv_path: str) -> ValidationResult:
    """Validate the whole file and collect every problem with physical line numbers."""
    result = ValidationResult()
    path = Path(csv_path)

    if not path.exists():
        result.errors.append(f"file not found: {csv_path}")
        return result

    try:
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            rows = []
            for row in reader:
                rows.append((reader.line_num, row))
    except UnicodeDecodeError:
        result.errors.append(
            "file is not UTF-8 (looks like cp1251 or another encoding) - re-save it as UTF-8")
        return result

    if not rows:
        result.errors.append("file is empty")
        return result

    header = [name.strip() for name in rows[0][1]]
    missing = [c for c in EXPECTED_COLUMNS if c not in header]
    unexpected = [c for c in header if c not in EXPECTED_COLUMNS]
    if unexpected:
        result.warnings.append(f"unexpected columns (ignored): {', '.join(unexpected)}")
    if missing:
        result.errors.append(f"missing columns: {', '.join(missing)}")
        return result

    col = {name: header.index(name) for name in EXPECTED_COLUMNS}
    seen_words = {}
    seen_names = {}

    for line_num, row in rows[1:]:
        if not any(field.strip() for field in row):
            continue
        result.row_count += 1

        if len(row) != len(header):
            preview = row[0][:40] if row else ''
            result.errors.append(
                f"line {line_num}: {len(row)} fields instead of {len(header)} "
                f"(unquoted comma or glued rows?): '{preview}'")
            continue

        values = {name: row[col[name]].strip() for name in EXPECTED_COLUMNS}
        english, russian = values['english'], values['russian']

        if not _check_word(result, line_num, english, russian, values['example'],
                           seen_words, seen_names):
            continue

        for group, answer, columns in (
            ('EN', english, EXPECTED_COLUMNS[3:7]),
            ('RU', russian, EXPECTED_COLUMNS[7:11]),
        ):
            variants = [values[c] for c in columns]
            for variant in variants:
                if variant and _norm(variant) == _norm(answer):
                    result.errors.append(
                        f"line {line_num} ({english}): {group} distractor equals "
                        f"the answer: '{variant}'")
            filled = [_norm(v) for v in variants if v]
            for dupe in sorted({v for v in filled if filled.count(v) > 1}):
                result.errors.append(
                    f"line {line_num} ({english}): duplicate {group} distractor: '{dupe}'")
            if any(not v for v in variants):
                result.warnings.append(f"line {line_num} ({english}): empty {group} distractor")

    return result
