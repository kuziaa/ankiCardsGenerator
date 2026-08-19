# Tools

Authoring helpers that are not part of the deck pipeline. They are not
installed with the package; run them with `python tools/<name>.py`.

## `image_review.py` - image review page

Turns a manifest of image candidates into a single self-contained HTML page
where the deck owner confirms or overrides the proposed pictures. The
automatic image search is good at concrete nouns and bad at abstract words,
so the decision that matters - does this picture actually evoke this word -
stays with a human, and this page makes that decision cheap.

```bash
python tools/image_review.py path/to/manifest.json          # writes review.html next to it
python tools/image_review.py path/to/manifest.json --out /tmp/review.html
```

### Input: `manifest.json`

```json
{
  "source": "chapter-file-name-without-extension",
  "words": [
    {
      "word": "On the verge of",
      "translation": "На грани",
      "example": "...had been on the verge of war...",
      "pick": "c5",
      "reason": "A rock ledge over a canyon - literally on the edge",
      "candidates": [
        {"id": "a1", "file": "candidates/verge/a1.jpg", "query": "on the verge of"},
        {"id": "c5", "file": "candidates/verge/c5.jpg", "query": "person standing on cliff edge"}
      ]
    }
  ]
}
```

- `word` becomes the image file name in the inbox later, so it must match the
  source word list exactly.
- `file` paths are relative to the manifest; `pick` may be `null` to propose
  no image at all.
- Validation fails loudly on a missing file, an unknown `pick` or duplicate
  candidate ids - a broken manifest never renders a half-empty page.

### The page

- One row per word: the word, translation, example and the one-line reason on
  the left, the candidates as selectable thumbnails on the right.
- Three states per word: a candidate, **No image** (a deliberate choice for
  abstract words) and **Need more options** (the candidate set is unusable and
  a new search round is needed).
- Previews are downscaled to 420 px and embedded as data URIs, so the page is
  one portable file that works offline from `file://`. The full-size original
  named in the manifest is what should reach the deck - never the preview.

### Output: `choices.json`

Saving uses the browser's file picker where available (Chromium-based
browsers), suggesting `choices.json` next to the page; when the browser
refuses to write, the page shows the same JSON in a dialog to copy or
download.

Keep the whole round in `image-review/<source>/` inside the repository
(git-ignored). Browsers block File System Access writes into system
locations such as `AppData\Local\Temp`, so a page generated there cannot
save the choices beside itself.

```json
{
  "source": "chapter-file-name-without-extension",
  "choices": {
    "Parochial": {"action": "keep", "pick": "c3"},
    "Marginal": {"action": "none", "pick": null},
    "Viable": {"action": "more", "pick": null}
  }
}
```

Confirmed images belong in `<images root>/<source>/<word>.jpg` - the manual
image inbox that the deck generator prefers over its own search. See
`.claude/skills/image-curation/SKILL.md` for the full assistant-side loop.
