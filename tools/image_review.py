"""Build a local review page from a manifest of image candidates."""

import argparse
import base64
import html
import io
import json
import sys
from pathlib import Path
from string import Template

from PIL import Image

TEMPLATE_PATH = Path(__file__).with_name("image_review_template.html")
PREVIEW_MAX_SIDE = 420


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


def preview_data_uri(path, max_side: int = PREVIEW_MAX_SIDE) -> str:
    """Downscaled JPEG preview of a candidate, inlined so the page is portable."""
    with Image.open(path) as image:
        image.load()
        preview = image.convert("RGB")
        preview.thumbnail((max_side, max_side))
        buffer = io.BytesIO()
        preview.save(buffer, "JPEG", quality=80)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _candidate_html(name: str, candidate: dict, checked: bool) -> str:
    mark = " checked" if checked else ""
    tag = html.escape(f"{candidate['id']} - {candidate.get('query', '')}".strip(" -"))
    return (f'<label class="cand"><input type="radio" name="{name}" '
            f'value="{html.escape(candidate["id"])}"{mark}>'
            f'<img src="{preview_data_uri(candidate["path"])}" alt="">'
            f'<span class="tag">{tag}</span></label>')


def _word_html(index: int, entry: dict) -> str:
    name = f"w{index}"
    pick = entry.get("pick")
    candidates = "".join(
        _candidate_html(name, candidate, candidate["id"] == pick)
        for candidate in entry.get("candidates", [])
    )
    none_checked = " checked" if pick is None else ""
    return (
        f'<section class="word" data-word="{html.escape(entry["word"], quote=True)}">'
        f'<div class="meta"><h2>{html.escape(entry["word"])}</h2>'
        f'<p class="ru">{html.escape(entry.get("translation", ""))}</p>'
        f'<p class="ex">{html.escape(entry.get("example", ""))}</p>'
        f'<p class="why">{html.escape(entry.get("reason", ""))}</p></div>'
        f'<div class="candidates"><div class="strip">{candidates}</div>'
        f'<div class="specials">'
        f'<label class="special"><input type="radio" name="{name}" '
        f'value="__none__"{none_checked}>No image</label>'
        f'<label class="special"><input type="radio" name="{name}" '
        f'value="__more__">Need more options</label>'
        f'</div></div></section>'
    )


def render_page(manifest: dict, template_text: str) -> str:
    """Fill the template with one section per word and inline previews."""
    words = manifest.get("words", [])
    with_image = sum(1 for entry in words if entry.get("pick") is not None)
    counters = (f"{len(words)} words | {with_image} with a proposed image | "
                f"{len(words) - with_image} proposed without")
    rows = "\n".join(_word_html(index, entry) for index, entry in enumerate(words))
    return Template(template_text).safe_substitute(
        SOURCE=html.escape(manifest["source"]),
        SOURCE_JSON=json.dumps(manifest["source"]),
        COUNTERS=html.escape(counters),
        ROWS=rows,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local image review page from a candidates manifest.")
    parser.add_argument("manifest", help="Path to manifest.json")
    parser.add_argument("--out",
                        help="Output HTML path (default: review.html next to the manifest)")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    try:
        manifest = load_manifest(manifest_path)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    page = render_page(manifest, TEMPLATE_PATH.read_text(encoding="utf-8"))
    out_path = Path(args.out) if args.out else manifest_path.parent / "review.html"
    out_path.write_text(page, encoding="utf-8")
    print(f"page written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
