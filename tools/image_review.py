"""Build a local review page from a manifest of image candidates."""

import json
from pathlib import Path


def load_manifest(path) -> dict:
    """Read and validate a manifest; every path is resolved against its folder."""
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent

    if not data.get("source"):
        raise ValueError("manifest has no source")

    for entry in data.get("words", []):
        word = entry.get("word")
        if not word:
            raise ValueError("manifest has a word entry without a word")

        seen = set()
        for candidate in entry.get("candidates", []):
            candidate_id = candidate["id"]
            if candidate_id in seen:
                raise ValueError(f"{word}: duplicate candidate id '{candidate_id}'")
            seen.add(candidate_id)

            resolved = (base / candidate["file"]).resolve()
            if not resolved.is_file():
                raise ValueError(f"{word}: candidate file not found: {candidate['file']}")
            candidate["path"] = resolved

        pick = entry.get("pick")
        if pick is not None and pick not in seen:
            raise ValueError(f"{word}: pick '{pick}' is not among the candidate ids")

    return data
