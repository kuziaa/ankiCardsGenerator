"""Collect image candidates for vocabulary words into a review manifest.

Read a curator-authored spec (the word list plus the search query or the
no-image decision for each word), fetch several candidates per word, validate
them, save the originals, and write the ``manifest.json`` that its sibling
``image_review.py`` renders.

The judgement stays in the spec you write - which query evokes an abstract
word, which words should not be searched at all. This tool only does the
mechanical, repeatable part: querying the backends, validating the downloads,
deduping and assembling the manifest, with an automatic fall back from the
keyed Google search to keyless Openverse and Wikimedia Commons when the daily
quota is spent. That is the part worth not rebuilding by hand every chapter.

Spec format (JSON)::

    {
      "source": "chapter-file-name-without-extension",
      "per_word": 5,                       # optional, default 5
      "words": [
        {
          "word": "on the verge of",       # byte-for-byte the source word
          "translation": "На грани",       # optional, carried to the manifest
          "example": "...",                # optional, carried to the manifest
          "reason": "a cliff edge = ...",  # optional one-line justification
          "queries": ["person on cliff edge", "on the verge of"]
        },
        {
          "word": "skull cracking",
          "no_image": true,                # skip the search on purpose
          "reason": "graphic violence, not searched"
        }
      ]
    }

Usage (run from the repo root)::

    python .claude/skills/image-curation/tools/collect_candidates.py spec.json
    python .claude/skills/image-curation/tools/collect_candidates.py spec.json --out-dir DIR --per-word 5
    python .claude/skills/image-curation/tools/collect_candidates.py spec.json --providers openverse,wikimedia
"""

import argparse
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image

# Mirror the validation media_manager.py applies, so a candidate that passes
# here will not be rejected when the deck is built.
IMAGE_MIN_BYTES = 5000
REQUEST_TIMEOUT = (5, 20)
# The inbox only reads these; collecting anything else would be a dead file.
EXT_BY_FORMAT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
USER_AGENT = ("ankiCardsGenerator-image-curation/1.0 "
              "(personal vocabulary tool)")


class QuotaExhausted(Exception):
    """Raised when the keyed Google search returns 403/429 (daily quota spent)."""


def repo_root() -> Path:
    """Find the project root by walking up to config.properties / .git.

    The tool lives under .claude/skills/... so a fixed parent offset is wrong;
    walking up keeps it working wherever it is checked out.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "config.properties").is_file() or (parent / ".git").is_dir():
            return parent
    return Path.cwd()


def load_config(path: Path) -> dict:
    """Parse a ``key=value`` properties file, ignoring blanks and comments."""
    config = {}
    if not path.is_file():
        return config
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


def make_session() -> requests.Session:
    """Keep-alive session with backoff on transient server errors (not on quota)."""
    session = requests.Session()
    # 429/403 stay out of the forcelist: on quota we want to fail fast and fall
    # back to a keyless source, not sit through retry backoff.
    retry = Retry(total=3, backoff_factor=1.0,
                  status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["User-Agent"] = USER_AGENT
    return session


def slugify(text: str, limit: int = 40) -> str:
    """Filesystem-safe folder key for a word (ASCII, underscores)."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return slug[:limit] or "word"


# --- search backends: each returns a list of candidate image URLs ------------

def search_google(session, query, key, cx, limit):
    """Google Custom Search image URLs; raises QuotaExhausted on 403/429."""
    url = ("https://www.googleapis.com/customsearch/v1?"
           f"q={urllib.parse.quote(query)}&searchType=image&"
           f"key={key}&cx={cx}&num={min(limit, 10)}")
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (403, 429):
            raise QuotaExhausted(str(exc)) from exc
        raise
    items = response.json().get("items", [])
    return [item["link"] for item in items if item.get("link")]


def search_openverse(session, query, limit):
    """Openverse (openly licensed aggregator) image URLs."""
    url = ("https://api.openverse.org/v1/images/?"
           f"q={urllib.parse.quote(query)}&page_size={min(limit, 20)}")
    response = session.get(url, timeout=REQUEST_TIMEOUT,
                           headers={"Accept": "application/json"})
    response.raise_for_status()
    results = response.json().get("results", [])
    return [r["url"] for r in results if r.get("url")]


def search_wikimedia(session, query, limit):
    """Wikimedia Commons file URLs (prefers a scaled thumb over huge originals)."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": str(min(limit, 20)),
        "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": "1024",
    }
    response = session.get("https://commons.wikimedia.org/w/api.php",
                           params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    urls = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        link = info.get("thumburl") or info.get("url")
        if link:
            urls.append(link)
    return urls


PROVIDERS = {"google", "openverse", "wikimedia"}


def download_valid(session, url):
    """Download a URL and return (original_bytes, ext) if it is a usable image.

    Validation mirrors media_manager.py: an ``image/*`` content type, a
    minimum size, and a successful PIL decode. The ORIGINAL bytes are kept -
    the review page makes its own downscaled preview, and the full-size file is
    what eventually reaches the deck.
    """
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException:
        return None
    data = response.content
    if len(data) < IMAGE_MIN_BYTES:
        return None
    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        return None
    try:
        Image.open(io.BytesIO(data)).verify()
        image_format = Image.open(io.BytesIO(data)).format
    except Exception:
        return None
    ext = EXT_BY_FORMAT.get(image_format or "")
    if ext is None:  # gif/bmp/tiff etc. - the inbox would ignore them
        return None
    return data, ext


def collect_word(session, entry, out_dir, per_word, config, providers, google_enabled):
    """Fetch candidates for one word; returns (manifest_entry, google_still_ok)."""
    word = entry["word"]
    base = {
        "word": word,
        "translation": entry.get("translation", ""),
        "example": entry.get("example", ""),
        "reason": entry.get("reason", ""),
    }

    if entry.get("no_image"):
        print(f"  {word}: no-image on purpose")
        return {**base, "pick": None, "candidates": []}, google_enabled

    queries = entry.get("queries") or [word]
    key, cx = config.get("API_KEY", ""), config.get("CX", "")
    have_google = google_enabled and bool(key and cx) \
        and key != "yourGoogleCustomSearchApiKey"

    word_dir = out_dir / "candidates" / slugify(word)
    candidates, seen_hashes = [], set()

    for query in queries:
        if len(candidates) >= per_word:
            break
        # Provider order per query: keyed Google first, then keyless fallbacks.
        chain = []
        if have_google:
            chain.append("google")
        chain += [p for p in ("openverse", "wikimedia") if p in providers]

        for provider in chain:
            if len(candidates) >= per_word:
                break
            try:
                if provider == "google":
                    urls = search_google(session, query, key, cx, per_word * 2)
                elif provider == "openverse":
                    urls = search_openverse(session, query, per_word * 2)
                else:
                    urls = search_wikimedia(session, query, per_word * 2)
            except QuotaExhausted:
                print("    ! Google quota exhausted - keyless sources only "
                      "from here on")
                have_google = google_enabled = False
                continue
            except requests.RequestException as exc:
                print(f"    ! {provider} failed for '{query}': {exc}")
                continue

            for url in urls:
                if len(candidates) >= per_word:
                    break
                result = download_valid(session, url)
                if result is None:
                    continue
                data, ext = result
                digest = hashlib.sha1(data).hexdigest()
                if digest in seen_hashes:
                    continue
                seen_hashes.add(digest)
                word_dir.mkdir(parents=True, exist_ok=True)
                cid = f"c{len(candidates) + 1}"
                path = word_dir / f"{cid}{ext}"
                path.write_bytes(data)
                candidates.append({
                    "id": cid,
                    "file": str(path.relative_to(out_dir)).replace("\\", "/"),
                    "query": query,
                    "provider": provider,
                })

    providers_used = sorted({c["provider"] for c in candidates})
    print(f"  {word}: {len(candidates)} candidate(s)"
          + (f" from {', '.join(providers_used)}" if providers_used else " - NONE"))

    if not candidates:
        reason = base["reason"] or "search returned nothing"
        base["reason"] = f"{reason} - hit 'Need more options' to retry"
        return {**base, "pick": None, "candidates": []}, google_enabled

    return {**base, "pick": candidates[0]["id"], "candidates": candidates}, google_enabled


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect image candidates into a review manifest.")
    parser.add_argument("spec", help="Path to the curator-authored spec JSON")
    parser.add_argument("--out-dir",
                        help="Where to write manifest.json and candidates/ "
                             "(default: next to the spec)")
    parser.add_argument("--per-word", type=int,
                        help="Candidates to keep per word (default: spec or 5)")
    parser.add_argument("--config",
                        help="Path to config.properties (default: repo root)")
    parser.add_argument("--providers", default="google,openverse,wikimedia",
                        help="Comma-separated backend order to try")
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read spec: {exc}", file=sys.stderr)
        return 1
    if not spec.get("source") or not spec.get("words"):
        print("error: spec needs a 'source' and a non-empty 'words' list",
              file=sys.stderr)
        return 1

    requested = [p.strip() for p in args.providers.split(",") if p.strip()]
    unknown = [p for p in requested if p not in PROVIDERS]
    if unknown:
        print(f"error: unknown provider(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    providers = set(requested)

    out_dir = Path(args.out_dir) if args.out_dir else spec_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    per_word = args.per_word or spec.get("per_word") or 5
    config_path = Path(args.config) if args.config else repo_root() / "config.properties"
    config = load_config(config_path)

    session = make_session()
    google_enabled = "google" in providers
    print(f"Collecting for '{spec['source']}' ({len(spec['words'])} words, "
          f"up to {per_word} each) from: {', '.join(requested)}")

    words_out = []
    for entry in spec["words"]:
        if not entry.get("word"):
            print("  ! skipping a spec entry with no 'word'", file=sys.stderr)
            continue
        result, google_enabled = collect_word(
            session, entry, out_dir, per_word, config, providers, google_enabled)
        words_out.append(result)

    manifest = {"source": spec["source"], "words": words_out}
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    with_image = sum(1 for w in words_out if w["pick"] is not None)
    print(f"\nmanifest written: {manifest_path}")
    print(f"{len(words_out)} words | {with_image} with a proposed image | "
          f"{len(words_out) - with_image} without")
    print(f"next: python .claude/skills/image-curation/tools/image_review.py \"{manifest_path}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
