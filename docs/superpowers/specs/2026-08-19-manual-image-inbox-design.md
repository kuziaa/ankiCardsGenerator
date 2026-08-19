# Manual image inbox — design

Date: 2026-08-19. Status: pending owner review.

## Problem

Images are the weakest part of a generated deck. `download_image` queries
Google Custom Search with the bare English word and keeps the first candidate
that downloads and decodes. For concrete nouns that works; for abstract words
(`parochial`, `marginal`, `on the verge of`) the whole result set is noise, so
no amount of ranking helps — the query itself is wrong.

A live experiment on the first five words of the "Holden" chapter confirmed
this: three of five words had no usable candidate for the bare-word query,
while a scene-style query ("person standing on cliff edge") found a good image
in one attempt. Picking those queries — and judging the results — is work a
human or an assistant does well and a script does badly.

## Goal

Let a curated image win over the automatic search, without the generator
caring who curated it. The pipeline must not know or care whether a file was
chosen by the owner, by an assistant, or downloaded automatically.

## Decisions (owner-approved)

- **Convention, not a flag.** The presence of a file is the signal. No
  `--images-manual` mode: real chapters are mixed — most words search fine,
  a few need a hand-picked image, and a binary flag cannot express that.
- **Inbox lives in the Obsidian vault**, grouped per book:
  `<images root>/<source stem>/<word>.<ext>`, e.g.
  `1-Projects/Reading Leviathan Wakes/_deck-images/holden/on the verge of.jpg`.
- The vault copies **are committed** to the shared vault repository, so the
  curation survives a reinstall and syncs between devices.
- The inbox root is configured in `config.properties`, which is git-ignored
  in this repository — the personal vault path never reaches GitHub — and can
  be overridden per run with `--images-root`.

## Resolution order

For every word, `MediaManager` resolves the image in this order:

1. **Manual inbox hit** — always wins, including over a previously cached
   automatic image. Dropping a file must visibly change the next run;
   otherwise the cache silently defeats the whole feature.
2. **Cached** `media/<stem>/<safe>.jpg` — reused when it passes the existing
   validity check.
3. **Automatic search** — unchanged behaviour, skipped in offline mode, when
   keys are missing, or after the daily quota is exhausted.

A fully curated inbox therefore produces a complete deck with `--offline` and
no API keys at all.

## Name matching

The inbox is indexed once per run: every `.jpg`, `.jpeg`, `.png` and `.webp`
file in the effective inbox directory is mapped by a normalized form of its
base name. Normalization: NFKD, strip combining marks, casefold, replace every run
of non-alphanumeric characters with a single space, trim. The same
normalization is applied to the English word.

Consequently `On the verge of.jpg`, `on-the-verge-of.png` and
`ON_THE_VERGE_OF.webp` all match the word `On the verge of`.

Two files normalizing to the same key: warn, and take the first in sorted
order, so a run stays deterministic.

## Copying into the deck

A matched file is decoded with Pillow, converted to RGB, downscaled so the
longest side is at most 800 px (smaller images are left alone), and written
atomically to `media/<stem>/<safe>.jpg` — the same name, format and quality
(JPEG q=85) the automatic path produces. Nothing downstream changes: genanki
packaging, `--push` media upload and the note field all stay as they are.

Inbox files are **read only**. The vault copy is never modified, moved or
deleted by the generator.

A file that fails to decode is reported as an error naming the file, and the
word falls through to the cache and then to the search — one broken file must
not abort a chapter.

## Reporting

Silent conventions rot, so the run states what it did:

- The inbox directory is created at start-up and its path is logged, so there
  is always a known place to drop files into.
- The final summary reports counts: `Images: 7 manual, 18 auto, 4 missing`,
  and lists the words that ended up with no image (capped like the existing
  known-words preview).
- Inbox files that matched no word are listed as a warning. The comparison
  uses **all** words loaded from the source file, not the words left after
  the known-words filter — otherwise every image of an already-known word
  would be reported as unmatched on every run.

## Configuration

`config.properties` gains one optional key:

```
IMAGES_ROOT=C:\...\vault\Reading Leviathan Wakes\_deck-images
```

The root is resolved in this order:

1. `--images-root <path>` —a one-off override, for a run against a folder
   that is not the usual vault location;
2. `IMAGES_ROOT` in `config.properties` —the steady-state setting;
3. `<project root>/images` —the fallback when neither is given.

Both the flag and the key name a **root**, never a per-chapter folder: the
effective inbox is always `<root>/<source stem>/`. Giving the two spellings
the same meaning keeps chapters from colliding and keeps the folder name
decoupled from Obsidian's own folder naming.

## Testing

TDD throughout. Cases:

- name matching: case, hyphens, underscores, spaces, each supported extension;
- a manual file overrides an existing cached `media/<safe>.jpg`;
- a manual file prevents the search from being called at all;
- offline mode still yields the manual image;
- a corrupt manual file logs an error and falls through;
- downscaling: a 2000 px source becomes ≤ 800 px, a 400 px source is untouched;
- the unmatched-files warning is computed from the unfiltered word list;
- root resolution: `--images-root` beats `IMAGES_ROOT`, which beats
  `<project root>/images`, and the source stem is appended in every case.

Plus an end-to-end offline run on the example CSV with a prepared inbox,
asserting that the packaged deck carries the manual image.

## Out of scope

- `--refresh-images <word>` to force re-downloading specific words.
- `image_choices.json` pins by URL and assistant-driven candidate collection
  (`--collect-images` contact sheets) — a separate feature that would *fill*
  this inbox rather than change it.
- Turning the automatic search off from configuration.
- Any change to note types, fields or templates.
