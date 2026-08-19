# Unified note type (v3) — design

Date: 2026-08-19. Status: pending owner review.

## Problem

One word currently produces six independent notes — one per note type
(typing ×2, choice ×2, scramble, cloze). Anki has no idea they are related:
the same translation, example, audio, image and distractors are copied six
times, an in-Anki edit fixes one copy and silently desyncs the rest, `--push`
spends six round-trips per word, the mature-words pull scans six model names,
and the sibling mechanics of Anki (burying, spaced introduction of a word's
cards) can never apply because the cards live in different notes.

The note is Anki's unit of *knowledge*; the card is the unit of *practice*.
Our unit of knowledge is the word — the six-note layout is an artifact of
incremental growth, not a design.

## Goal

One note per word carrying all word data, with the five non-cloze card types
as templates of a single note type. Cards look pixel-identical to v2. The CSV
contract, the LLM prompts, the CLI surface and the markdown mode do not
change.

## Decisions (owner-approved)

- **One unified model, five templates.** New frozen model id **1712849305**,
  name `EN-RU Vocabulary`. Existing qfmt/afmt/JS are reused verbatim; only a
  gate wrapper is added around each front.
- **Cloze stays a separate note type** (`EN-RU Cloze Model`, id 1631442296,
  unchanged). A word is 1–2 notes: unified + optional cloze.
- **Gate fields control card existence.** Anki generates a card when its
  front renders non-empty; the typing and scramble templates share the same
  data fields, so field presence alone cannot express `--models` subsets.
  Five gate fields (`y` / empty) make the selection per-note data.
- **Data is filled independently of gates.** Distractors from the CSV are
  always written when present, even if the choice models are not selected.
  Enabling a model later is a gate flip, not a regeneration.
- **Clean generation cut, no scheduling migration.** v2 notes are not
  converted; the owner deletes the old decks and note types manually. Before
  deleting, run the generator once with Anki open so the mature-words pull
  records learned words into the ledger (source `anki`).
- **Push updates merge, never degrade** (see Push section).

## The unified model

Nineteen fields, in this frozen order — data first, service fields last:

| # | Field | Notes |
|---|-------|-------|
| 1 | `English` | sort field, note identity |
| 2 | `Russian` | |
| 3 | `Example` | |
| 4 | `Audio` | `[sound:...]` |
| 5 | `Image` | `<img ...>` |
| 6 | `ExampleAudio` | `[sound:..._example.mp3]` |
| 7–10 | `RussianIncorrect1..4` | EN→RU Choice distractors |
| 11–14 | `EnglishIncorrect1..4` | RU→EN Choice distractors |
| 15–19 | `EnRuTyping`, `RuEnTyping`, `EnRuChoice`, `RuEnChoice`, `Scramble` | gates, `y` / empty |

Five templates, in this frozen order: `EN-RU Typing`, `RU-EN Typing`,
`EN-RU Choice`, `RU-EN Choice`, `RU-EN Scramble` (v2 naming style). Each template's qfmt is the
v2 qfmt wrapped entirely in `{{#<Gate>}}...{{/<Gate>}}`; afmt is the v2 afmt
unchanged. An empty gate renders an empty front, so neither genanki's `_req`
computation nor Anki generates the card — verified against genanki 0.13.1
(`model.py::_req`, chevron section semantics) and Anki's card-generation rule.

The gate value never appears on a card: `{{#Gate}}` is a conditional wrapper,
not an interpolation.

CSS is the union of the v2 typing, choice-widget, image and scramble styles
(one stylesheet per note type; class names do not collide).

Audio-placement semantics carry over per template exactly as in v2: typing
plays audio on the front (EN→RU repeats it on the back), EN→RU Choice plays
audio on the front, RU→EN Choice only after the answer divider.

Editor ergonomics (best-effort): distractor and gate field definitions carry
`collapsed: True` and a short `description`. genanki serializes unknown field
keys into the `.apkg` model JSON and Anki 23.10+ understands both keys; if a
real import shows they do not survive, the fallback is a one-time manual
"Collapse by default" setup in the Fields dialog — the flags must not become
load-bearing anywhere.

The model lives in a new module `src/models/vocab_model.py`. The five v2
model modules and the `make_typing_model` / `make_choice_model` factories are
deleted; `factory.py` keeps the shared CSS constants, the template sources
and the sentinel renderer used to build the unified templates.

## Generation

- `CardGenerator.create_cards` returns one unified `VocabNote` plus the
  optional cloze note (same skip rule as today when the word does not occur
  in its example) — instead of up to six notes.
- Note GUID: `guid_for(word, "1712849305")` — one per word; the cloze GUID is
  unchanged. Re-import after edits keeps updating instead of duplicating.
- `selected_models` (CLI `--models`, interactive menu, `MARKDOWN_SAFE_MODELS`)
  keeps the exact same surface and numbering 1–6. Numbers 1–5 now set gates
  on the single note; 6 controls the cloze note as before.
- Deck naming, deck ids, media naming, known-words ledger: unchanged.

## Push

`updateNoteFields` replaces all fields, which becomes destructive with a
shared note: a rerun with a smaller `--models` would clear gates (turning
live scheduled cards into empty cards), and a `--from-md` push (no
distractors) would blank distractors previously loaded from a CSV.

Policy — **an update is a merge that never degrades the note**:

- an empty incoming field value never overwrites a non-empty stored value
  (covers distractors, media fields in `--offline` runs);
- gates are only ever set to `y` by an update, never cleared.

Implementation: for each note found by the existing first-field + note-type
query, read its current fields with one `notesInfo` call, merge, then update.
Adding brand-new notes is unchanged (fields and gates written as generated).

The `.apkg` path cannot merge (genanki has no access to collection state);
re-importing a package generated with fewer models than the note already has
may blank fields. Documented limitation: push is the update path, `.apkg` is
the initial-import path.

`ensure_models` already expands multi-template models — no changes.

## Mature-words sync and legacy

- `ALL_MODELS` becomes `[vocab_model, cloze_model]`.
- The five v2 model names (`EN-RU Typing Model v2` ... `RU-EN Scramble Model
  v2`; the cloze model stays current) join `LEGACY_MODEL_NAMES` next to the
  v1 names, so `fetch_mature_words` keeps seeing v2 cards until the owner
  deletes them; afterwards the legacy queries simply match nothing.
- The five v2 model ids join `RETIRED_MODEL_IDS`; the guard test asserts no
  reuse.
- CLAUDE.md frozen-invariants section is updated: the v2 id list moves to
  retired, the unified 19-field order becomes the frozen invariant, and the
  "ExampleAudio is always the LAST field" rule is retired with v2.

## Testing

- `tests/test_models_factory.py` rewritten for v3: frozen id and 19-field
  order, template names and order, gate wrapping of every qfmt, per-template
  audio placement semantics, `ExampleAudio` on backs only, distractor buttons
  per direction, retired-id non-reuse (v1 + v2).
- New card-generation tests: a unified note's `note.cards` contains exactly
  the ords of the selected gates (direct check of the `_req` contract);
  `create_cards` returns 1–2 notes; distractor fields filled even when choice
  models are unselected.
- Push tests on the fake client: merge policy (empty incoming keeps stored,
  gates never cleared, non-empty incoming wins), `notesInfo` used on update,
  add path unchanged.
- Manual verification: import a generated `.apkg` into Anki and push into a
  live Anki — five cards per word with the expected fronts, no gate values
  visible, collapsed fields honored (or fallback noted).

## Out of scope

- Scheduling/revlog migration of v2 notes; deck or note-type deletion
  tooling.
- Bury/siblings configuration (a deck-options toggle the owner sets).
- Any change to the CSV contract, the LLM prompts, `--from-md` parsing, or
  the media pipeline.
