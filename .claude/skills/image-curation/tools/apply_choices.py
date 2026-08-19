"""Write confirmed image-review choices into the deck's manual image inbox.

Reads the ``manifest.json`` produced by ``collect_candidates.py`` and the
``choices.json`` the review page saved, and for every word the owner chose to
``keep`` copies the ORIGINAL candidate file (not the downscaled page preview)
into the inbox the deck generator reads. ``none`` and ``more`` are left alone -
the first is a deliberate no-picture, the second needs a fresh search round.

The inbox path mirrors the generator: ``<images root>/<source>/<word><ext>``
where ``<images root>`` is ``IMAGES_ROOT`` from ``config.properties`` (or the
project's ``images/`` folder) and ``<source>`` is the manifest source, which
must equal the input file's stem so the two sides point at the same folder.

Run with ``--dry-run`` first to show exactly what would be written where -
copying into someone's vault should never be a surprise.

Usage (run from the repo root)::

    python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json --dry-run
    python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json
    python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json --inbox "D:/deck-images/Chapter"
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


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
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def resolve_inbox(args, manifest, config) -> Path:
    """Inbox folder: explicit --inbox wins, else <images root>/<source>."""
    if args.inbox:
        return Path(args.inbox).expanduser()
    if args.images_root:
        root = Path(args.images_root).expanduser()
    elif config.get("IMAGES_ROOT", "").strip():
        root = Path(config["IMAGES_ROOT"].strip()).expanduser()
    else:
        root = repo_root() / "images"
    source = args.source or manifest.get("source")
    if not source:
        raise ValueError("no --source and manifest has no source")
    return root / source


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy confirmed review choices into the deck image inbox.")
    parser.add_argument("manifest", help="manifest.json from collect_candidates.py")
    parser.add_argument("choices", help="choices.json saved by the review page")
    parser.add_argument("--inbox", help="Target inbox folder (overrides the config path)")
    parser.add_argument("--images-root", help="Root folder; <source> is appended")
    parser.add_argument("--source", help="Source stem (default: manifest source)")
    parser.add_argument("--config", help="config.properties (default: repo root)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written, copy nothing")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        choices = json.loads(Path(args.choices).read_text(encoding="utf-8"))["choices"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: cannot read inputs: {exc}", file=sys.stderr)
        return 1

    # Index candidate files by (word, id) so a pick resolves to its original.
    by_word = {w["word"]: w for w in manifest.get("words", [])}
    manifest_dir = manifest_path.parent

    config_path = Path(args.config) if args.config else repo_root() / "config.properties"
    try:
        inbox = resolve_inbox(args, manifest, load_config(config_path))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"inbox: {inbox}")
    planned, skipped, problems = [], 0, []
    for word, choice in choices.items():
        action = choice.get("action")
        if action != "keep":
            skipped += 1
            continue
        entry = by_word.get(word)
        if entry is None:
            problems.append(f"{word}: not in manifest")
            continue
        pick = choice.get("pick")
        candidate = next((c for c in entry.get("candidates", []) if c["id"] == pick), None)
        if candidate is None:
            problems.append(f"{word}: pick '{pick}' not among candidates")
            continue
        src = (manifest_dir / candidate["file"]).resolve()
        if not src.is_file():
            problems.append(f"{word}: candidate file missing: {candidate['file']}")
            continue
        # Keep the candidate's real extension; the inbox reads jpg/png/webp and
        # the word is the file name the generator matches on.
        dest = inbox / f"{word}{src.suffix.lower()}"
        planned.append((word, src, dest))

    for word, src, dest in planned:
        print(f"  {'[dry-run] ' if args.dry_run else ''}{word} -> {dest.name}")

    if problems:
        print("\nproblems:", file=sys.stderr)
        for problem in problems:
            print(f"  ! {problem}", file=sys.stderr)

    print(f"\n{len(planned)} to write | {skipped} skipped (none/more) | "
          f"{len(problems)} problem(s)")

    if args.dry_run:
        print("dry run - nothing written")
        return 1 if problems else 0

    inbox.mkdir(parents=True, exist_ok=True)
    for word, src, dest in planned:
        shutil.copy2(src, dest)
    print(f"wrote {len(planned)} image(s) to {inbox}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
