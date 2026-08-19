# Image Review Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A generator that turns a manifest of image candidates into one self-contained HTML page where the owner confirms or overrides the assistant's picks.

**Architecture:** `tools/image_review.py` validates a manifest, downscales previews with Pillow, embeds them as data URIs and fills `tools/image_review_template.html` through `string.Template`. The page writes `choices.json`; the assistant consumes that file and copies the confirmed originals into the vault inbox.

**Tech Stack:** Python 3.9+, Pillow, pytest. No new dependencies. The page uses no external assets and works from `file://`.

**Spec:** `docs/superpowers/specs/2026-08-19-image-review-page-design.md`

## Global Constraints

- Worktree: `C:\My\ankiCardsGenerator.image-review`, branch `feature/image-review-page`. The main working copy holds a parallel story — never touch it.
- Do not edit `README.md` or `.claude/CLAUDE.md`: the parallel story edits both. Documentation goes to `tools/README.md` and the skill.
- Repository files are English-only, the page UI included. Russian appears only as *data* coming from the manifest (translations, examples, reasons).
- The manifest's `word` is the inbox file name later, so it must survive rendering unchanged and be HTML-escaped on display only.
- Previews are downscaled for display; the manifest keeps the path to the full-size original, which is what gets copied into the vault.
- The skill MUST be created with the `skill-creator` skill, never hand-written.
- Run tests with `python -m pytest tests/ -q` from the worktree root.

## File Structure

- `tools/image_review.py` — manifest loading and validation, preview embedding, page rendering, CLI.
- `tools/image_review_template.html` — page shell with `$SOURCE`, `$SOURCE_JSON`, `$COUNTERS`, `$ROWS` placeholders.
- `tools/README.md` — how to run the generator and what the two contracts look like.
- `tests/test_image_review.py`.
- `pyproject.toml` — one line: `pythonpath = ["src", "tools"]`.
- `.claude/skills/<name>/SKILL.md` — the assistant-side loop, created via `skill-creator`.

---

### Task 1: Manifest loading and validation

**Files:**
- Create: `tools/image_review.py`
- Modify: `pyproject.toml`
- Test: `tests/test_image_review.py`

**Interfaces:**
- Produces: `load_manifest(path) -> dict` raising `ValueError` with a message naming the offending word.

- [ ] **Step 1: Put `tools` on the test path**

In `pyproject.toml`, change `pythonpath = ["src"]` to:

```toml
pythonpath = ["src", "tools"]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_image_review.py`:

```python
import json

import pytest
from PIL import Image

from image_review import load_manifest


def write_candidate(path, size=(600, 400), color=(120, 160, 200)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def build_manifest(tmp_path, **overrides):
    write_candidate(tmp_path / "candidates" / "verge" / "a1.jpg")
    write_candidate(tmp_path / "candidates" / "verge" / "c5.jpg")
    manifest = {
        "source": "holden",
        "words": [
            {
                "word": "On the verge of",
                "translation": "На грани",
                "example": "...on the verge of war...",
                "pick": "c5",
                "reason": "A rock ledge over a canyon",
                "candidates": [
                    {"id": "a1", "file": "candidates/verge/a1.jpg", "query": "on the verge of"},
                    {"id": "c5", "file": "candidates/verge/c5.jpg", "query": "person on cliff edge"},
                ],
            }
        ],
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_manifest_returns_words(tmp_path):
    manifest = load_manifest(build_manifest(tmp_path))

    assert manifest["source"] == "holden"
    assert manifest["words"][0]["pick"] == "c5"


def test_load_manifest_rejects_unknown_pick(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["pick"] = "zz"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="On the verge of.*zz"):
        load_manifest(path)


def test_load_manifest_rejects_duplicate_candidate_ids(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["candidates"][1]["id"] = "a1"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate candidate id 'a1'"):
        load_manifest(path)


def test_load_manifest_rejects_missing_candidate_file(tmp_path):
    path = build_manifest(tmp_path)
    (tmp_path / "candidates" / "verge" / "c5.jpg").unlink()

    with pytest.raises(ValueError, match="candidate file not found"):
        load_manifest(path)


def test_load_manifest_accepts_a_null_pick(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["pick"] = None
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert load_manifest(path)["words"][0]["pick"] is None
```

- [ ] **Step 3: Run the tests and watch them fail**

Run: `python -m pytest tests/test_image_review.py -v`
Expected: `ModuleNotFoundError: No module named 'image_review'`.

- [ ] **Step 4: Write the loader**

Create `tools/image_review.py`:

```python
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
```

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_image_review.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add tools/image_review.py tests/test_image_review.py pyproject.toml
git commit -m "feat: load and validate image review manifests"
```

---

### Task 2: Render the page

**Files:**
- Create: `tools/image_review_template.html`
- Modify: `tools/image_review.py`
- Test: `tests/test_image_review.py`

**Interfaces:**
- Consumes: `load_manifest` from Task 1.
- Produces: `preview_data_uri(path, max_side=420) -> str`, `render_page(manifest, template_text) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_image_review.py` (extend the import with `render_page`
and `TEMPLATE_PATH`):

```python
import base64
import io
import re


def render(tmp_path, **overrides):
    manifest = load_manifest(build_manifest(tmp_path, **overrides))
    return render_page(manifest, TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_page_renders_a_section_per_word(tmp_path):
    html = render(tmp_path)

    assert html.count('<section class="word"') == 1
    assert 'data-word="On the verge of"' in html


def test_proposed_pick_is_preselected(tmp_path):
    html = render(tmp_path)

    assert 'value="c5" checked' in html
    assert 'value="a1" checked' not in html


def test_page_offers_the_two_extra_states(tmp_path):
    html = render(tmp_path)

    assert 'value="__none__"' in html
    assert 'value="__more__"' in html


def test_previews_are_embedded_and_paths_do_not_leak(tmp_path):
    html = render(tmp_path)

    assert html.count("data:image/jpeg;base64,") == 2
    assert "candidates/verge/a1.jpg" not in html


def test_previews_are_downscaled(tmp_path):
    write_candidate(tmp_path / "candidates" / "verge" / "a1.jpg", size=(2000, 1500))
    html = render(tmp_path)

    encoded = re.search(r'data:image/jpeg;base64,([^"]+)"', html).group(1)
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
        assert max(image.size) == 420


def test_text_is_escaped(tmp_path):
    manifest_path = build_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["words"][0]["example"] = 'war & <b>peace</b>'
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    html = render_page(load_manifest(manifest_path),
                       TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert "war &amp; &lt;b&gt;peace&lt;/b&gt;" in html
    assert "<b>peace</b>" not in html


def test_header_counters_match_the_manifest(tmp_path):
    manifest_path = build_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["words"].append({
        "word": "Marginal", "translation": "Незначительный", "example": "x",
        "pick": None, "reason": "no usable candidate",
        "candidates": [{"id": "a1", "file": "candidates/verge/a1.jpg", "query": "marginal"}],
    })
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    html = render_page(load_manifest(manifest_path),
                       TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert "2 words" in html
    assert "1 with a proposed image" in html
    assert "1 proposed without" in html
```

Remove the dead first line of `test_text_is_escaped` while writing it — it is shown here only to keep the diff obvious; the test starts at `manifest_path = build_manifest(tmp_path)`.

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m pytest tests/test_image_review.py -v`
Expected: `ImportError: cannot import name 'render_page'`.

- [ ] **Step 3: Write the template**

Create `tools/image_review_template.html`:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Image review - $SOURCE</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0;
         background: #f4f4f6; color: #1c1c1e; }
  header { position: sticky; top: 0; z-index: 5; display: flex; align-items: center;
           gap: 16px; padding: 14px 24px; background: #fff; border-bottom: 1px solid #e2e2e8; }
  header h1 { font-size: 18px; margin: 0; }
  .counts { color: #6b6b72; font-size: 14px; }
  .spacer { flex: 1; }
  #status { font-size: 14px; color: #2f9e44; }
  button { font-size: 15px; padding: 8px 18px; border: 0; border-radius: 8px;
           background: #2f9e44; color: #fff; cursor: pointer; }
  button:hover { background: #268a3a; }
  main { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
  section.word { display: grid; grid-template-columns: minmax(220px, 300px) 1fr; gap: 20px;
                 background: #fff; border: 1px solid #e2e2e8; border-radius: 12px; padding: 16px; }
  section.word h2 { margin: 0 0 4px; font-size: 20px; }
  .ru { margin: 0 0 8px; color: #2a7ae2; font-weight: 600; }
  .ex { margin: 0 0 8px; font-style: italic; color: #444; line-height: 1.45; }
  .why { margin: 0; line-height: 1.45; }
  .candidates { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; }
  .cand { display: block; cursor: pointer; padding: 4px; border: 3px solid transparent;
          border-radius: 10px; }
  .cand img { display: block; width: 210px; height: 150px; object-fit: contain;
              background: #fafafa; border-radius: 6px; }
  .cand .tag { display: block; max-width: 210px; margin-top: 4px; font-size: 11px; color: #77777e; }
  .special { display: flex; align-items: center; gap: 6px; align-self: flex-start;
             padding: 12px 14px; border: 1px dashed #b9b9c0; border-radius: 10px;
             font-size: 14px; cursor: pointer; }
  .selected { border-color: #2f9e44; background: #f2fbf4; }
  @media (max-width: 900px) { section.word { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>Image review - $SOURCE</h1>
  <span class="counts">$COUNTERS</span>
  <span class="spacer"></span>
  <span id="status"></span>
  <button id="save">Save choices</button>
</header>
<main>
$ROWS
</main>
<script>
const SOURCE = $SOURCE_JSON;

function paint() {
  document.querySelectorAll('.cand, .special').forEach(label => {
    label.classList.toggle('selected', label.querySelector('input').checked);
  });
}

function collect() {
  const choices = {};
  document.querySelectorAll('section.word').forEach(section => {
    const checked = section.querySelector('input[type=radio]:checked');
    const value = checked ? checked.value : '__none__';
    if (value === '__none__') {
      choices[section.dataset.word] = { action: 'none', pick: null };
    } else if (value === '__more__') {
      choices[section.dataset.word] = { action: 'more', pick: null };
    } else {
      choices[section.dataset.word] = { action: 'keep', pick: value };
    }
  });
  return { source: SOURCE, choices: choices };
}

async function save() {
  const text = JSON.stringify(collect(), null, 2);
  const status = document.getElementById('status');
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName: 'choices.json' });
      const writable = await handle.createWritable();
      await writable.write(text);
      await writable.close();
      status.textContent = 'Saved';
      return;
    } catch (error) {
      if (error.name === 'AbortError') { return; }
    }
  }
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
  link.download = 'choices.json';
  link.click();
  URL.revokeObjectURL(link.href);
  status.textContent = 'Downloaded';
}

document.addEventListener('change', paint);
document.getElementById('save').addEventListener('click', save);
paint();
</script>
</body>
</html>
```

- [ ] **Step 4: Write the renderer**

Append to `tools/image_review.py` (imports first: `base64`, `html`, `io`, `string.Template`, `PIL.Image`):

```python
TEMPLATE_PATH = Path(__file__).with_name("image_review_template.html")
PREVIEW_MAX_SIDE = 420


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
        f'<div class="candidates">{candidates}'
        f'<label class="special"><input type="radio" name="{name}" '
        f'value="__none__"{none_checked}>No image</label>'
        f'<label class="special"><input type="radio" name="{name}" '
        f'value="__more__">Need more options</label>'
        f'</div></section>'
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
```

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_image_review.py -v`
Expected: 12 passed. The counter assertions expect the wording `2 words`,
`1 with a proposed image`, `1 proposed without` — keep the format string in
sync with them.

- [ ] **Step 6: Commit**

```bash
git add tools/image_review.py tools/image_review_template.html tests/test_image_review.py
git commit -m "feat: render a self-contained image review page"
```

---

### Task 3: Command line entry point

**Files:**
- Modify: `tools/image_review.py`
- Test: `tests/test_image_review.py`

**Interfaces:**
- Produces: `main(argv=None) -> int`, writing `review.html` next to the manifest unless `--out` is given.

- [ ] **Step 1: Write the failing test**

```python
def test_main_writes_the_page_next_to_the_manifest(tmp_path):
    manifest_path = build_manifest(tmp_path)

    assert main([str(manifest_path)]) == 0

    page = tmp_path / "review.html"
    assert page.exists()
    assert "Image review" in page.read_text(encoding="utf-8")


def test_main_reports_a_bad_manifest_without_a_traceback(tmp_path, capsys):
    manifest_path = build_manifest(tmp_path)
    (tmp_path / "candidates" / "verge" / "c5.jpg").unlink()

    assert main([str(manifest_path)]) == 1
    assert "candidate file not found" in capsys.readouterr().err
```

- [ ] **Step 2: Run and watch them fail**

Run: `python -m pytest tests/test_image_review.py -v`
Expected: `ImportError: cannot import name 'main'`.

- [ ] **Step 3: Implement the entry point**

```python
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local image review page from a candidates manifest.")
    parser.add_argument("manifest", help="Path to manifest.json")
    parser.add_argument("--out", help="Output HTML path (default: review.html next to the manifest)")
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
```

Add `argparse` and `sys` to the imports.

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/ -q`
Expected: everything passes (100 existing + 14 new).

- [ ] **Step 5: Commit**

```bash
git add tools/image_review.py tests/test_image_review.py
git commit -m "feat: add the image review CLI entry point"
```

---

### Task 4: The assistant-side skill

**Files:**
- Create: `.claude/skills/<name>/SKILL.md` (name chosen by the skill-creator run)

- [ ] **Step 1: Invoke the skill-creator skill**

**REQUIRED SUB-SKILL:** `skill-creator`. Hand-writing the skill file violates the
project rule; run the skill and follow its flow.

- [ ] **Step 2: Content the skill must carry**

- The five-step loop from the spec, with the assistant's obligations at each step.
- The two contracts (`manifest.json` in, `choices.json` out) with a short example each.
- Collection guidance: several candidates per word from more than one query, a
  scene-style query for abstract words, and an honest "no image" proposal when
  nothing fits - a bad picture is worse than none.
- The three failure modes worth stating explicitly:
  - `word` must be byte-identical to the CSV word, because it becomes the inbox
    file name;
  - copy the **original** into the vault, never the downscaled preview;
  - after the write-back, delete the temporary candidates folder, and start a
    fresh search round for every word marked `more`.
- Where the confirmed images go: `<images root>/<source stem>/<word>.jpg`, the
  inbox the deck generator already reads.
- A reminder that writing into the vault needs the owner's approval first.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills
git commit -m "docs: add the image review skill"
```

---

### Task 5: Tool documentation

**Files:**
- Create: `tools/README.md`

- [ ] **Step 1: Write it**

Cover: what the generator is for, how to run it, the manifest fields, the
`choices.json` shape, the three per-word states, and the note that the page
saves through the File System Access API with a download fallback. State that
`README.md` and `.claude/CLAUDE.md` get their pointer once the parallel story
lands.

- [ ] **Step 2: Verify and commit**

Run: `python -m pytest tests/ -q`

```bash
git add tools/README.md
git commit -m "docs: describe the image review generator"
```

---

### Task 6: First real page and hand-off

**Files:** none in the repository.

- [ ] **Step 1: Build a manifest from the Holden candidates**

The candidates collected earlier live in the scratchpad
(`scratchpad/image-demo/<word>/<A-E><n>.jpg`) with `manifest*.json` recording
each candidate's query, title and licence. Convert them into the review
manifest for the five words `Parochial`, `On the verge of`, `Viable`,
`Marginal`, `Schematics`, using the CSV spelling of each word, the vault
translations and examples, the earlier picks and their one-line reasons.

- [ ] **Step 2: Generate the page**

```bash
python tools/image_review.py <scratchpad>/holden-review/manifest.json
```

- [ ] **Step 3: Hand it to the owner**

Report the page path and ask them to review, adjust and press Save. This is
also the one manual verification the plan cannot automate: whether the picker
saves `choices.json` next to the page or the fallback download fires.

- [ ] **Step 4: Write back on confirmation**

After the owner reports they are done: read `choices.json`, ask for approval
to write into the vault, copy the confirmed originals to
`<images root>/holden/<word>.jpg`, list the words marked `more` for a new
search round, and delete the temporary folder.

- [ ] **Step 5: Finish the branch**

**REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch.
