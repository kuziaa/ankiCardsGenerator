import json
import os
from datetime import date
from pathlib import Path

from utils.csv_validator import _norm
from utils.logger import setup_logger

logger = setup_logger(__name__)

LEDGER_VERSION = 1


def load_known_words(path) -> dict:
    """Load the ledger as {normalized_word: entry}. Missing file -> empty dict."""
    ledger_path = Path(path)
    if not ledger_path.exists():
        return {}
    try:
        data = json.loads(ledger_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Known-words ledger is unreadable, ignoring it: {e}")
        return {}
    words = data.get('words', {}) if isinstance(data, dict) else {}
    return words if isinstance(words, dict) else {}


def filter_known_words(cards: list, ledger: dict, source_stem: str) -> tuple:
    """Split cards into (kept, skipped_words).

    A word is skipped only when the ledger attributes it to a DIFFERENT
    source - re-generating the same file must keep producing its own words.
    """
    kept = []
    skipped = []
    for card in cards:
        entry = ledger.get(_norm(card.english))
        if entry and entry.get('source') != source_stem:
            skipped.append(card.english)
        else:
            kept.append(card)
    return kept, skipped


def record_known_words(path, cards: list, source_stem: str) -> int:
    """Add generated words to the ledger; existing entries keep their source.

    Returns the number of newly recorded words.
    """
    ledger_path = Path(path)
    words = load_known_words(ledger_path)
    added = 0
    for card in cards:
        key = _norm(card.english)
        if key not in words:
            words[key] = {
                'word': card.english,
                'source': source_stem,
                'added': date.today().isoformat(),
            }
            added += 1
    if added:
        payload = json.dumps(
            {'version': LEDGER_VERSION, 'words': dict(sorted(words.items()))},
            ensure_ascii=False, indent=2)
        tmp = ledger_path.with_suffix(ledger_path.suffix + '.tmp')
        tmp.write_text(payload + '\n', encoding='utf-8')
        os.replace(tmp, ledger_path)
    return added
