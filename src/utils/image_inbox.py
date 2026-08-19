import re
import unicodedata
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)

SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def normalize_name(text: str) -> str:
    """Fold case, accents and every separator so file names match words loosely."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", stripped).strip().casefold()


def index_inbox(inbox_dir) -> dict:
    """Map normalized file names to paths for every supported image in the inbox."""
    directory = Path(inbox_dir)
    if not directory.is_dir():
        return {}

    index = {}
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        key = normalize_name(path.stem)
        if not key:
            continue
        if key in index:
            logger.warning(f"Duplicate inbox image for '{key}': keeping "
                           f"{index[key].name}, ignoring {path.name}")
            continue
        index[key] = path
    return index


def unmatched_files(index: dict, words) -> list:
    """Inbox file names that no word in the source file claims."""
    claimed = {normalize_name(word) for word in words}
    return sorted(path.name for key, path in index.items() if key not in claimed)
