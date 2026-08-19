# image-curation tools

Authoring helpers for the `image-curation` skill (the assistant-side loop for
choosing vocabulary-card images). They are not part of the deck pipeline and
are not installed with the package. Run them from the repo root with
`python .claude/skills/image-curation/tools/<name>.py`.

## `collect_candidates.py` - gather image candidates

Turns a curator-authored spec (the search query, or a no-image decision, for
each word) into the `manifest.json` that `image_review.py` renders. It does
the mechanical, repeatable half of image curation - querying the backends,
validating downloads, deduping, saving the originals and assembling the
manifest - while the judgement (which query evokes an abstract word, which
words not to search) stays in the spec you write.

```bash
python .claude/skills/image-curation/tools/collect_candidates.py spec.json          # manifest + candidates/ next to spec
python .claude/skills/image-curation/tools/collect_candidates.py spec.json --out-dir DIR --per-word 5
python .claude/skills/image-curation/tools/collect_candidates.py spec.json --providers openverse,wikimedia
```

### Input: `spec.json`

```json
{
  "source": "chapter-file-name-without-extension",
  "per_word": 5,
  "words": [
    {"word": "on the verge of", "translation": "На грани", "example": "...",
     "reason": "a cliff edge = literally on the edge",
     "queries": ["person on cliff edge", "on the verge of"]},
    {"word": "skull cracking", "no_image": true,
     "reason": "graphic violence, not searched on purpose"}
  ]
}
```

- `word` is byte-for-byte the source word; `queries` are tried in order until
  `per_word` candidates are collected; `no_image: true` skips the search and
  emits an empty candidate list with the `reason`.
- Backends are tried Google → Openverse → Wikimedia; Google needs `API_KEY`
  and `CX` in `config.properties` and falls back automatically on quota
  (`403`/`429`). Restrict or reorder with `--providers`.
- Originals are saved (never re-encoded here); `pick` defaults to the first
  candidate. Run `--help` for all flags.

## `image_review.py` - image review page

Turns a manifest of image candidates into a single self-contained HTML page
where the deck owner confirms or overrides the proposed pictures. The
automatic image search is good at concrete nouns and bad at abstract words,
so the decision that matters - does this picture actually evoke this word -
stays with a human, and this page makes that decision cheap.

```bash
python .claude/skills/image-curation/tools/image_review.py path/to/manifest.json   # writes review.html next to it
python .claude/skills/image-curation/tools/image_review.py path/to/manifest.json --out /tmp/review.html
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
- `candidates` may be empty with `pick: null` for a word that should not be
  searched at all (explicit slang, clinical terms). The page then shows the
  `reason` where the thumbnails would be, so the row reads as a decision
  rather than a glitch.

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

## `apply_choices.py` - write confirmed choices into the inbox

Reads the `manifest.json` and the `choices.json` the page saved, and copies
every `keep` candidate's **original** (not the page preview) into the inbox
the deck generator reads. `none` and `more` are left alone.

```bash
python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json --dry-run   # show the plan
python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json             # copy the files
python .claude/skills/image-curation/tools/apply_choices.py manifest.json choices.json --inbox "D:/deck-images/Chapter"
```

- The inbox defaults to `<images root>/<source>/`, where `<images root>` is
  `IMAGES_ROOT` from `config.properties` (or the project `images/` folder) and
  `<source>` is the manifest source - which must equal the input file's stem
  so it lands in the folder the generator scans. Override with `--inbox`,
  `--images-root` or `--source`.
- Each file is named `<word><ext>`, keeping the candidate's original
  extension (`.jpg`/`.png`/`.webp`, all read by the inbox).
- `--dry-run` prints what would be copied and writes nothing - run it first
  and show it before touching someone's vault.
