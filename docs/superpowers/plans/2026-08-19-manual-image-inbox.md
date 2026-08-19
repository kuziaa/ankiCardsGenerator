# Manual Image Inbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a curated image file win over the automatic Google search, so the generator stops caring who picked the picture.

**Architecture:** A new pure module `utils/image_inbox.py` owns name normalization, directory indexing and reporting strings. `MediaManager` consults that index before its cache and before the search. The CLI resolves the inbox root (flag > config key > project default), creates the folder, and reports what happened.

**Tech Stack:** Python 3.9+, Pillow, pytest (`pythonpath = ["src"]`, so tests import `utils.*` directly).

**Spec:** `docs/superpowers/specs/2026-08-19-manual-image-inbox-design.md`

## Global Constraints

- Resolution order is fixed: manual inbox → cached `media/<stem>/<safe>.jpg` → automatic search. Manual must beat an existing cache file.
- The effective inbox is always `<root>/<source stem>/`. Both `--images-root` and `IMAGES_ROOT` name a **root**, never a per-chapter folder.
- Supported inbox extensions: `.jpg`, `.jpeg`, `.png`, `.webp`. Everything is written into the deck as JPEG q=85, longest side capped at 800 px, never upscaled.
- Inbox files are read-only for the generator: never modified, moved or deleted.
- `src/anki_generator.py` and `config.properties*` must NEVER be read raw into the agent's context (corporate DLP appliance resets the connection on the API-key property line). Read them only through the sanitizing pipe `| perl -pe 's/[A-Z][A-Z0-9_]*(ACCOUNT|CRED|USER|PASS|TOKEN|SECRET|AUTH|LOGIN|KEY)[A-Z0-9_]*/<RID>/g; s/[A-Za-z0-9_-]{30,}/<RVAL>/g'`, and edit them only with anchored replacement scripts (anchors are given verbatim in each task).
- No changes to note types, fields, templates or model ids.
- Repository files are English-only. Comments stay to one line, and only where the code is not self-explanatory.
- Run the suite with `python -m pytest tests/ -q` from the project root; single files with `python -m pytest tests/test_x.py -v`.

## File Structure

- `src/utils/image_inbox.py` (new) — pure helpers, no I/O beyond directory listing: `normalize_name`, `index_inbox`, `unmatched_files`, `format_image_summary`.
- `src/utils/media_manager.py` — gains an `inbox_dir` constructor argument, the `_manual_image` step inside `download_image`, and the `manual_count` / `auto_count` counters.
- `src/anki_generator.py` — gains `--images-root`, `CliOptions.images_root`, `resolve_images_root`, inbox creation and the closing image report.
- `tests/test_image_inbox.py` (new), `tests/test_media_manager.py`, `tests/test_cli.py`.
- Docs: `README.md`, `.claude/CLAUDE.md`, `config.properties.sample`.

---

### Task 1: Inbox indexing module

**Files:**
- Create: `src/utils/image_inbox.py`
- Test: `tests/test_image_inbox.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `normalize_name(text: str) -> str`, `index_inbox(inbox_dir) -> dict[str, Path]`, `unmatched_files(index: dict, words: Iterable[str]) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_inbox.py`:

```python
from PIL import Image

from utils.image_inbox import index_inbox, normalize_name, unmatched_files


def write_image(path, size=(40, 30), color=(120, 160, 200)):
    Image.new("RGB", size, color).save(path)
    return path


def test_normalize_name_ignores_case_and_separators():
    assert normalize_name("On the verge of") == "on the verge of"
    assert normalize_name("on-the-verge-of") == "on the verge of"
    assert normalize_name("ON_THE_VERGE_OF") == "on the verge of"


def test_index_inbox_maps_supported_files_and_ignores_the_rest(tmp_path):
    write_image(tmp_path / "Parochial.PNG")
    write_image(tmp_path / "on-the-verge-of.jpg")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    index = index_inbox(tmp_path)

    assert set(index) == {"parochial", "on the verge of"}
    assert index["parochial"].name == "Parochial.PNG"


def test_index_inbox_returns_empty_for_missing_directory(tmp_path):
    assert index_inbox(tmp_path / "does-not-exist") == {}


def test_index_inbox_keeps_one_file_per_normalized_name(tmp_path):
    write_image(tmp_path / "Verge.png")
    write_image(tmp_path / "verge.jpg")

    index = index_inbox(tmp_path)

    assert list(index) == ["verge"]
    assert index["verge"].name == "Verge.png"


def test_unmatched_files_reports_names_no_word_claims(tmp_path):
    write_image(tmp_path / "parochial.jpg")
    write_image(tmp_path / "verge.jpg")

    index = index_inbox(tmp_path)

    assert unmatched_files(index, ["Parochial", "On the verge of"]) == ["verge.jpg"]
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m pytest tests/test_image_inbox.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'utils.image_inbox'`.

- [ ] **Step 3: Write the module**

Create `src/utils/image_inbox.py`:

```python
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
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_image_inbox.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/utils/image_inbox.py tests/test_image_inbox.py
git commit -m "feat: add inbox indexing for manually curated images"
```

---

### Task 2: MediaManager resolves the inbox first

**Files:**
- Modify: `src/utils/media_manager.py`
- Test: `tests/test_media_manager.py`

**Interfaces:**
- Consumes: `index_inbox`, `normalize_name` from Task 1.
- Produces: `MediaManager(..., inbox_dir: str = "")` with attributes `inbox_index: dict`, `manual_count: int`, `auto_count: int`; `download_image` unchanged in signature.

- [ ] **Step 1: Write the failing tests**

Add `import pytest` to the existing imports of `tests/test_media_manager.py`
(the file already imports `Path`, `Image` and `MediaManager`), then append:

```python
def make_inbox(tmp_path, name, size=(2000, 1500), color=(10, 200, 10)):
    inbox = tmp_path / "inbox"
    inbox.mkdir(exist_ok=True)
    Image.new("RGB", size, color).save(inbox / name)
    return inbox


def test_manual_image_is_converted_and_downscaled(tmp_path):
    inbox = make_inbox(tmp_path, "Parochial.png")
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    result = manager.download_image(search_term="Parochial",
                                    safe_filename="parochial_abc12345")

    assert result is not None
    with Image.open(result) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 800
    assert manager.manual_count == 1


def test_small_manual_image_is_not_upscaled(tmp_path):
    inbox = make_inbox(tmp_path, "dojo.jpg", size=(120, 90))
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    result = manager.download_image(search_term="dojo", safe_filename="dojo_abc12345")

    with Image.open(result) as image:
        assert image.size == (120, 90)


def test_manual_image_overrides_a_cached_file(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    Image.new("RGB", (60, 40), (220, 10, 10)).save(media / "verge_abc12345.jpg")
    inbox = make_inbox(tmp_path, "on the verge of.jpg", size=(60, 40))

    manager = MediaManager(media_dir=str(media), offline=True, inbox_dir=str(inbox))
    result = manager.download_image(search_term="On the verge of",
                                    safe_filename="verge_abc12345")

    with Image.open(result) as image:
        red, green, _ = image.convert("RGB").getpixel((30, 20))
    assert green > 150 and red < 100


def test_manual_image_skips_the_search(tmp_path):
    inbox = make_inbox(tmp_path, "parochial.jpg", size=(60, 40))
    manager = MediaManager(media_dir=str(tmp_path / "media"), api_key="key",
                           cx="cx", inbox_dir=str(inbox))
    manager.session.get = lambda *args, **kwargs: pytest.fail("search must not run")

    assert manager.download_image("Parochial", "parochial_abc12345") is not None


def test_broken_manual_file_falls_through(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "parochial.jpg").write_bytes(b"this is not an image")
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    assert manager.download_image("Parochial", "parochial_abc12345") is None
    assert manager.manual_count == 0


def test_inbox_file_is_left_untouched(tmp_path):
    inbox = make_inbox(tmp_path, "dojo.png", size=(1600, 1200))
    source = inbox / "dojo.png"
    before = source.read_bytes()
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    manager.download_image("dojo", "dojo_abc12345")

    assert source.read_bytes() == before


def test_cached_image_counts_as_auto(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    Image.new("RGB", (600, 400), (30, 30, 200)).save(media / "dojo_abc12345.jpg")
    manager = MediaManager(media_dir=str(media), offline=True)

    assert manager.download_image("dojo", "dojo_abc12345") is not None
    assert manager.auto_count == 1
    assert manager.manual_count == 0
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m pytest tests/test_media_manager.py -v`
Expected: `TypeError: __init__() got an unexpected keyword argument 'inbox_dir'` on the new tests, the four pre-existing tests still passing.

- [ ] **Step 3: Implement the inbox step**

In `src/utils/media_manager.py`, add to the import block after `from utils.logger import setup_logger`:

```python
from utils.image_inbox import index_inbox, normalize_name
```

Add the cap next to the other constants (after `IMAGE_MIN_BYTES = 5000`):

```python
MANUAL_IMAGE_MAX_SIDE = 800
```

Extend the constructor signature and body (`inbox_dir` last, so positional callers are unaffected):

```python
    def __init__(self, media_dir: str = "media", api_key: str = "", cx: str = "",
                 offline: bool = False, inbox_dir: str = ""):
```

and extend the attribute block in `__init__` — anchor on the existing
`self.search_disabled = False` line:

```python
        self.search_disabled = False
        self.inbox_index = index_inbox(inbox_dir) if inbox_dir else {}
        self.manual_count = 0
        self.auto_count = 0
```

Add the new method directly above `download_image`:

```python
    def _manual_image(self, search_term: str, image_path: Path) -> bool:
        """Copy a curated inbox file into the deck media, converted and capped."""
        source = self.inbox_index.get(normalize_name(search_term))
        if source is None:
            return False

        try:
            with Image.open(source) as image:
                image.load()
                converted = image.convert("RGB")
                converted.thumbnail((MANUAL_IMAGE_MAX_SIDE, MANUAL_IMAGE_MAX_SIDE))
                buffer = io.BytesIO()
                converted.save(buffer, "JPEG", quality=85)
        except Exception as e:
            logger.error(f"✗ Broken image in inbox ({source.name}): {e}")
            return False

        _atomic_write(image_path, buffer.getvalue())
        logger.info(f"✓ Image taken from inbox: {source.name}")
        return True
```

In `download_image`, insert the inbox check between the `image_path` assignment and the cache block, and count the cache hit:

```python
        image_path = self.media_dir / f"{safe_filename}.jpg"

        # A curated file wins over the cache and the search
        if self._manual_image(search_term, image_path):
            self.manual_count += 1
            return str(image_path)

        # Reuse the cached file only when it passes validation
        if image_path.exists():
            if self._valid_cached_image(image_path):
                logger.debug(f"Image already exists: {image_path}")
                self.auto_count += 1
                return str(image_path)
```

Finally, count a successful download: in the candidate loop, right before `return str(image_path)` after `logger.info(f"✓ Image successfully downloaded: {search_term}")`, add:

```python
                self.auto_count += 1
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_media_manager.py -v`
Expected: all pass, including the four pre-existing ones.

- [ ] **Step 5: Commit**

```bash
git add src/utils/media_manager.py tests/test_media_manager.py
git commit -m "feat: prefer curated inbox images over cache and search"
```

---

### Task 3: CLI resolves the inbox root

**Files:**
- Modify: `src/anki_generator.py` (anchored script only — never read this file raw)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `MediaManager(..., inbox_dir=...)` from Task 2.
- Produces: `CliOptions.images_root: str = None`, `--images-root DIR`, `resolve_images_root(images_root_arg, properties: dict, root_path: Path) -> Path`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py` (extend the existing import line from `anki_generator` with `resolve_images_root`):

```python
def test_images_root_flag_is_parsed():
    options = parse_args(["--images-root", "D:/pics"])

    assert options.images_root == "D:/pics"


def test_resolve_images_root_prefers_the_flag(tmp_path):
    root = resolve_images_root("D:/from-flag", {"IMAGES_ROOT": "D:/from-config"}, tmp_path)

    assert root == Path("D:/from-flag")


def test_resolve_images_root_falls_back_to_config(tmp_path):
    root = resolve_images_root(None, {"IMAGES_ROOT": "D:/from-config"}, tmp_path)

    assert root == Path("D:/from-config")


def test_resolve_images_root_defaults_to_project_images(tmp_path):
    assert resolve_images_root(None, {}, tmp_path) == tmp_path / "images"
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: `ImportError: cannot import name 'resolve_images_root'`.

- [ ] **Step 3: Apply the anchored edits**

Write `apply_images_root.py` in the scratchpad and run it from the project root (heredocs mangle backslashes — use a file):

```python
import os

os.chdir(r"C:/My/ankiCardsGenerator")


def edit(path, replacements):
    raw = open(path, 'rb').read()
    crlf = b'\r\n' in raw
    text = raw.decode('utf-8').replace('\r\n', '\n')
    for old, new, count in replacements:
        found = text.count(old)
        assert found == count, f"{path}: anchor {found}x expected {count}: {old[:70]!r}"
        text = text.replace(old, new)
    open(path, 'wb').write((text.replace('\n', '\r\n') if crlf else text).encode('utf-8'))
    print(f"OK {path}")


edit('src/anki_generator.py', [
    ("""    push: bool = False
    overwrite_media: bool = False""",
     """    push: bool = False
    overwrite_media: bool = False
    images_root: str = None""", 1),

    ("""    parser.add_argument(
        '--overwrite-media',
        action='store_true',
        help="With --push: overwrite media files that already exist in the Anki collection.",
    )""",
     """    parser.add_argument(
        '--overwrite-media',
        action='store_true',
        help="With --push: overwrite media files that already exist in the Anki collection.",
    )
    parser.add_argument(
        '--images-root',
        metavar='DIR',
        help="Root folder of the manual image inbox; the source file name is appended.",
    )""", 1),

    ("""                         include_known=args.include_known, push=args.push,
                         overwrite_media=args.overwrite_media)""",
     """                         include_known=args.include_known, push=args.push,
                         overwrite_media=args.overwrite_media,
                         images_root=args.images_root)""", 1),

    ("""def derive_deck_id(source_stem: str) -> int:""",
     """def resolve_images_root(images_root_arg, properties: dict, root_path: Path) -> Path:
    \"\"\"Inbox root: CLI flag wins, then the config key, then the project folder.\"\"\"
    if images_root_arg:
        return Path(images_root_arg).expanduser()
    configured = properties.get('IMAGES_ROOT', '').strip()
    if configured:
        return Path(configured).expanduser()
    return root_path / 'images'


def derive_deck_id(source_stem: str) -> int:""", 1),

    ("""    # Create media subdirectory for this input file
    media_dir = media_root_dir / source_name_no_ext
    media_dir.mkdir(parents=True, exist_ok=True)""",
     """    # Create media subdirectory for this input file
    media_dir = media_root_dir / source_name_no_ext
    media_dir.mkdir(parents=True, exist_ok=True)

    # Inbox for manually curated images
    inbox_dir = resolve_images_root(options.images_root, properties, root_path) / source_name_no_ext
    try:
        inbox_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Manual image inbox: {inbox_dir}")
    except OSError as e:
        logger.warning(f"Manual image inbox unavailable ({inbox_dir}): {e}")""", 1),

    ("""    media_manager = MediaManager(
        media_dir=str(media_dir),
        api_key=api_key,
        cx=cx,
        offline=options.offline,
    )""",
     """    media_manager = MediaManager(
        media_dir=str(media_dir),
        api_key=api_key,
        cx=cx,
        offline=options.offline,
        inbox_dir=str(inbox_dir),
    )""", 1),
])

print("images root wired")
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: all pass. Then confirm the edit visually with `git diff --stat` and a sanitized read:
`sed -n '400,430p' src/anki_generator.py | perl -pe 's/[A-Z][A-Z0-9_]*(ACCOUNT|CRED|USER|PASS|TOKEN|SECRET|AUTH|LOGIN|KEY)[A-Z0-9_]*/<RID>/g'`

- [ ] **Step 5: Commit**

```bash
git add src/anki_generator.py tests/test_cli.py
git commit -m "feat: resolve the manual image inbox from flag, config or project"
```

---

### Task 4: Report what the images came from

**Files:**
- Modify: `src/utils/image_inbox.py`, `src/anki_generator.py` (anchored script)
- Test: `tests/test_image_inbox.py`

**Interfaces:**
- Consumes: `manual_count` / `auto_count` / `inbox_index` from Task 2, `unmatched_files` from Task 1.
- Produces: `format_image_summary(manual: int, auto: int, missing_words: list) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_inbox.py` (extend the import with `format_image_summary`):

```python
def test_format_image_summary_without_missing_words():
    assert format_image_summary(7, 18, []) == "Images: 7 manual, 18 auto, 0 missing"


def test_format_image_summary_lists_missing_words():
    line = format_image_summary(1, 2, ["Marginal", "Parochial"])

    assert line == "Images: 1 manual, 2 auto, 2 missing (Marginal, Parochial)"


def test_format_image_summary_caps_the_preview():
    words = [f"word{i}" for i in range(23)]

    assert format_image_summary(0, 0, words).endswith("word19 and 3 more)")
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m pytest tests/test_image_inbox.py -v`
Expected: `ImportError: cannot import name 'format_image_summary'`.

- [ ] **Step 3: Implement the helper**

Append to `src/utils/image_inbox.py`:

```python
def format_image_summary(manual: int, auto: int, missing_words: list) -> str:
    """One-line provenance report for the end of a run."""
    line = f"Images: {manual} manual, {auto} auto, {len(missing_words)} missing"
    if not missing_words:
        return line
    preview = ', '.join(missing_words[:20])
    if len(missing_words) > 20:
        preview += f" and {len(missing_words) - 20} more"
    return f"{line} ({preview})"
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_image_inbox.py -v`
Expected: 8 passed.

- [ ] **Step 5: Wire the report into the run**

Run this anchored script (same `edit` helper as Task 3):

```python
edit('src/anki_generator.py', [
    ("""from utils.known_words import (filter_known_words, load_known_words,
                               record_known_words, record_word_list)""",
     """from utils.image_inbox import format_image_summary, unmatched_files
from utils.known_words import (filter_known_words, load_known_words,
                               record_known_words, record_word_list)""", 1),

    ("""    # Known-words ledger: skip vocabulary already generated from other sources
    ledger_path = root_path / 'known_words.json'""",
     """    # Inbox warnings compare against every word of the source, not the filtered rest
    all_source_words = [card.english for card in cards_data]

    # Known-words ledger: skip vocabulary already generated from other sources
    ledger_path = root_path / 'known_words.json'""", 1),

    ("""    all_notes = []
    media_files = []""",
     """    all_notes = []
    media_files = []
    words_without_image = []""", 1),

    ("""            if image_path:
                media_files.append(image_path)""",
     """            if image_path:
                media_files.append(image_path)
            else:
                words_without_image.append(card_data.english)""", 1),

    ("""    logger.info(f"  Total flashcards created: {len(all_notes)}")""",
     """    logger.info(f"  Total flashcards created: {len(all_notes)}")
    logger.info(f"  {format_image_summary(media_manager.manual_count, media_manager.auto_count, words_without_image)}")
    unmatched = unmatched_files(media_manager.inbox_index, all_source_words)
    if unmatched:
        logger.warning(f"Unmatched files in inbox: {', '.join(unmatched[:20])}")""", 1),
])
```

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest tests/ -q`
Expected: every test passes.

- [ ] **Step 7: Commit**

```bash
git add src/utils/image_inbox.py src/anki_generator.py tests/test_image_inbox.py
git commit -m "feat: report image provenance and unmatched inbox files"
```

---

### Task 5: Documentation

**Files:**
- Modify: `README.md`, `.claude/CLAUDE.md`, `config.properties.sample` (anchored script — never read raw)

**Interfaces:**
- Consumes: the finished behaviour of Tasks 1-4.
- Produces: no code.

- [ ] **Step 1: Add the CLI option and a section to README.md**

In the options table, after the `--overwrite-media` row:

```markdown
| `--images-root DIR` | Root folder of the manual image inbox; the source file name is appended |
```

After the "Known Words Ledger" section:

```markdown
### Manual Images

The automatic image search works well for concrete nouns and badly for
abstract ones. Any image you drop into the inbox wins over the search:

```
<images root>/<source file name>/<english word>.jpg
```

- The root comes from `--images-root`, else `IMAGES_ROOT` in
  `config.properties`, else `<project>/images`. The folder is created on every
  run and its path is printed in the log.
- File names are matched loosely: case, spaces, hyphens and underscores are
  interchangeable, so `On the verge of.jpg`, `on-the-verge-of.png` and
  `ON_THE_VERGE_OF.webp` all match the word `On the verge of`.
- Supported: `.jpg`, `.jpeg`, `.png`, `.webp`. Files are copied into the deck
  as JPEG, capped at 800 px on the longest side; the originals are never
  touched.
- A curated file also beats a previously downloaded image, so replacing a bad
  picture is a matter of dropping a file and rerunning.
- With a fully curated inbox a deck builds with `--offline` and no API keys.
- The run ends with `Images: N manual, M auto, K missing` and warns about
  inbox files that match no word — usually a typo in a file name.
```

- [ ] **Step 2: Add the invariant to .claude/CLAUDE.md**

After the bullet about `config.properties` being optional:

```markdown
- Image resolution order is fixed: manual inbox (`<images root>/<source
  stem>/<word>.*`) beats the `media/` cache, which beats the Google search.
  A curated file must always win, otherwise the cache silently defeats the
  feature. Inbox files are read-only for the generator.
```

- [ ] **Step 3: Add the config key**

Anchored edit of `config.properties.sample` (anchor on the AnkiConnect block, never on the key line):

```python
edit('config.properties.sample', [
    ("""# AnkiConnect endpoint for --push and the learned-words sync (optional)
#ANKICONNECT_URL=http://127.0.0.1:8765""",
     """# AnkiConnect endpoint for --push and the learned-words sync (optional)
#ANKICONNECT_URL=http://127.0.0.1:8765

# Root folder for manually curated images; the source file name is appended (optional)
#IMAGES_ROOT=C:\\\\path\\\\to\\\\vault\\\\_deck-images""", 1),
])
```

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/ -q` (docs must not break anything) and check the sample renders as intended:
`cat config.properties.sample | perl -pe 's/[A-Z][A-Z0-9_]*(ACCOUNT|CRED|USER|PASS|TOKEN|SECRET|AUTH|LOGIN|KEY)[A-Z0-9_]*/<RID>/g'`

- [ ] **Step 5: Commit**

```bash
git add README.md .claude/CLAUDE.md config.properties.sample
git commit -m "docs: describe the manual image inbox"
```

---

### Task 6: End-to-end verification

**Files:**
- No production changes; a temporary inbox under the scratchpad.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Prepare an inbox for the example CSV**

The first words of `src/resources/cards.example.csv` are `armored men`, `dojo`, `outcropping`. Create two files with deliberately awkward names:

```python
from PIL import Image
from pathlib import Path

inbox = Path(r"C:\Users\akhmaru\AppData\Local\Temp\claude\C--My-FamilyManagerVault\397d6818-794f-4c2b-88b3-07c312b965a3\scratchpad\inbox-e2e\cards.example")
inbox.mkdir(parents=True, exist_ok=True)
Image.new("RGB", (1600, 1200), (200, 40, 40)).save(inbox / "armored-men.PNG")
Image.new("RGB", (100, 80), (40, 200, 40)).save(inbox / "Dojo.jpg")
```

- [ ] **Step 2: Run offline against it**

```bash
anki-cards-generator --csv cards.example.csv --models 1 --offline \
  --images-root "C:/Users/akhmaru/AppData/Local/Temp/claude/C--My-FamilyManagerVault/397d6818-794f-4c2b-88b3-07c312b965a3/scratchpad/inbox-e2e"
```

Expected in the log: `Manual image inbox: ...\inbox-e2e\cards.example`, and a closing
`Images: 2 manual, ... missing (...)` with no unmatched-file warning.

- [ ] **Step 3: Verify the packaged deck carries the manual images**

```python
import zipfile

with zipfile.ZipFile(r"C:\My\ankiCardsGenerator\results\cards.example.apkg") as pkg:
    names = pkg.namelist()
print(len(names))
```

Expected: the package contains media entries; additionally check that
`media/cards.example/` holds a JPEG for `armored men` whose longest side is 800
(downscaled) and one for `dojo` still 100x80 (untouched).

- [ ] **Step 4: Verify the unmatched warning fires**

Add `Image.new("RGB", (50, 50), (0, 0, 0)).save(inbox / "verge.jpg")`, rerun the same
command, and confirm the log ends with `Unmatched files in inbox: verge.jpg`.

- [ ] **Step 5: Clean up and run the whole suite**

Delete the scratchpad inbox, `results/cards.example.apkg`, `media/cards.example/` and
the `known_words.json` entries created by the run (delete the file if it was created
by these runs only).

Run: `python -m pytest tests/ -q`
Expected: every test passes.

- [ ] **Step 6: Finish the branch**

**REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch.
