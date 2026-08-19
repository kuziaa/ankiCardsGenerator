# Image review page — design

Date: 2026-08-19. Status: pending owner review.

## Problem

Image curation currently happens in chat: the assistant searches, picks, and
describes the result in prose. The owner never sees the alternatives, so
overriding a mediocre pick costs a round of messages per word. A live run on
the "Holden" chapter made the cost concrete — the assistant needed three
blind rounds of query rewriting for two words, and its final pick for
`parochial` was still the weakest of the five.

The missing piece is a cheap confirmation step: the owner should see every
candidate, the proposed pick, and the reasoning, and change any of it in one
pass.

## Goal

A repeatable loop where the assistant proposes and the owner disposes,
ending with confirmed images in the vault inbox that the deck generator
already consumes.

## The loop

1. The owner asks for images for a chapter.
2. The assistant collects candidates per word, writes them to a temporary
   folder, and writes `manifest.json`: word, translation, example, the
   candidate list, its own pick and a one-line reason.
3. The assistant runs `python tools/image_review.py <manifest>` and gets a
   single self-contained `review.html`.
4. The owner opens the page locally, adjusts what they disagree with, and
   presses Save, which writes `choices.json`.
5. The owner says they are done. The assistant copies the confirmed images
   into `<images root>/<source stem>/<word>.jpg`, opens a new search round
   for every word marked "need more options", and deletes the temporary
   folder.

Step 5 lands exactly on the convention the manual image inbox already
implements, so nothing new is needed on the deck-building side.

## Input contract — `manifest.json`

```json
{
  "source": "holden",
  "words": [
    {
      "word": "On the verge of",
      "translation": "На грани",
      "example": "...had been on the verge of war...",
      "pick": "c5",
      "reason": "A rock ledge over a canyon - literally on the edge",
      "candidates": [
        {"id": "a1", "file": "candidates/verge/a1.jpg",
         "query": "on the verge of", "source": "openverse", "license": "CC0"},
        {"id": "c5", "file": "candidates/verge/c5.jpg",
         "query": "person standing on cliff edge", "source": "openverse",
         "license": "BY"}
      ]
    }
  ]
}
```

- `word` must be byte-identical to the word in the source CSV: it becomes the
  inbox file name, and a mismatch means the deck silently keeps the old image.
- `file` paths are relative to the manifest.
- `pick` may be `null` when the assistant proposes no image at all.

## The page

- **Header**: source name, counters (`29 words · 24 with a proposed image ·
  5 proposed without`), and a Save button that stays reachable while
  scrolling.
- **One row per word**: on the left the word, the translation, the example
  and the assistant's one-line reason; on the right the candidates as a radio
  group of thumbnails, the proposed one preselected and visibly marked.
- **Three states per word**, all in the same radio group: a candidate, *no
  image* (a deliberate decision for abstract words), and *need more options*
  (the signal that the whole candidate set is unusable and the assistant
  should search again with different queries). Without the third state the
  owner is forced to pick the least bad option, and the assistant never
  learns it missed.
- **Self-contained**: candidate previews are embedded as base64 data URIs and
  downscaled to 420 px for display, so the page is one portable file with no
  external requests. The manifest keeps the path to the full-size original —
  that is what gets copied into the vault, never the preview.
- Works from `file://`: no fonts, scripts or styles from the network.

## Output contract — `choices.json`

```json
{
  "source": "holden",
  "choices": {
    "Parochial": {"action": "keep", "pick": "c3"},
    "On the verge of": {"action": "keep", "pick": "c5"},
    "Marginal": {"action": "none", "pick": null},
    "Viable": {"action": "more", "pick": null}
  }
}
```

Saving uses `showSaveFilePicker` with `choices.json` suggested next to the
page; browsers without the File System Access API fall back to a normal
download. The assistant looks for the file next to the page first, then in
the downloads folder.

## What lives in the repository

- `tools/image_review.py` — the generator: reads a manifest, validates it,
  downscales previews with Pillow (already a dependency), renders the page.
- `tools/image_review_template.html` — the page shell with `string.Template`
  placeholders, so HTML, CSS and JS stay readable instead of being glued
  together in Python string literals.
- `tests/test_image_review.py`.
- A `.claude/` skill describing the loop above, created with the
  `skill-creator` skill.

Candidate collection stays **outside** the project: it needs no keys only
because the assistant uses ad-hoc sources, and the deck pipeline is
deliberately agnostic about where images come from. The repository owns two
stable things — the page format and the `choices.json` contract.

## Testing

Automated, on the generator:

- one row per word, in manifest order;
- one radio input per candidate plus the two extra states;
- the proposed pick is the checked input;
- previews are embedded as `data:image/jpeg;base64,` and no `file`
  path leaks into an `src` attribute;
- words, translations and examples are HTML-escaped;
- header counters match the manifest;
- a missing candidate file, an unknown `pick` id or a duplicate candidate id
  fails with a clear error instead of rendering a broken page.

Not automatable here: the Save button depends on a browser API, so it is
verified once manually on the first real page. The download fallback is the
safety net if the picker is unavailable.

## Out of scope

- Collecting candidates from inside the project (would need API keys).
- Cropping, rotating or otherwise editing images.
- Writing images into the vault from the page itself: the assistant does the
  write, because that is where file names are matched against the CSV words
  and where a silent mismatch would otherwise slip through.
- Any change to the deck pipeline, note types or the inbox convention.

## Documentation note

Documentation goes into `tools/README.md` and the skill, deliberately not
into `README.md` or `.claude/CLAUDE.md`: a parallel story is editing those
files in the main working copy. A pointer can be added once that story lands.
