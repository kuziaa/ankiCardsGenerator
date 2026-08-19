# Example audio + cloze cards (v2 note types) — design

Date: 2026-08-18. Status: approved by the owner (chat review), pending
implementation plan.

## Goal

Two features shipped as one note-type schema migration:

1. **Example audio**: a second mp3 per word — the whole example sentence —
   played on the back of every card. Listening practice on top of the
   existing pipeline.
2. **Cloze cards**: a sixth card type — the example sentence with the word
   hidden (`{{c1::…}}`), a collapsible Russian hint on the front.

Both need note-type changes, so they ship together: one migration instead of
two.

## Decisions (owner-approved)

- Migration strategy: **new model ids** for all five existing models plus the
  new cloze model. Old note types stay untouched in the collection; the owner
  will delete the old decks for the first two chapters manually, and new
  generations use only v2 types.
- New note-type names carry an explicit **" v2" suffix** ("EN-RU Typing Model
  v2", …). The cloze model has no v1 ancestor and is named without a suffix.
- Example audio is **enabled by default**, disabled via `EXAMPLE_AUDIO=FALSE`
  in `config.properties` (the key must actually be read by the code).
- Cloze is model number **6**, included in `--models all` and allowed in
  `--from-md` (it needs no distractors). No audio of any kind on cloze cards.
- Russian hint on the cloze front is collapsible (`{{hint:Hint}}`), the back
  shows the full sentence and the translation.

## Frozen model ids

Retired (v1) — never reuse: 73727116, 4392726, 2343456, 23436536, 234556757.

New (v2 + cloze) — frozen from now on:

| Model | ID |
|---|---|
| EN-RU Typing Model v2 | 1298336501 |
| RU-EN Typing Model v2 | 1354702052 |
| EN-RU Choice Model v2 | 1427185897 |
| RU-EN Choice Model v2 | 1495623708 |
| RU-EN Scramble Model v2 | 1563008841 |
| EN-RU Cloze Model | 1631442296 |

## Section 1 — v2 note types

- `src/models/factory.py`: `make_typing_model` / `make_choice_model` gain a
  name-suffix parameter and an `ExampleAudio` field appended **last** to the
  field list (last position keeps the first-field GUID identity intact).
  Templates gain `{{ExampleAudio}}` on the answer side after `{{Example}}`.
- The four factory call sites switch to the v2 ids and the " v2" suffix.
- `ru_en_scramble_model.py` (hand-written) is edited in place: new id, name
  "RU-EN Scramble Model v2", `ExampleAudio` field appended, played on the
  back.
- Old ids remain documented as retired constants; `.claude/CLAUDE.md` frozen
  invariants section is updated.

**Accepted consequence**: regenerating an old chapter with the new version
creates parallel notes on v2 types. The known-words ledger makes this rare;
the owner deletes old decks before regenerating.

## Section 2 — example audio

- `config.properties` key `EXAMPLE_AUDIO` (default true).
- Generation reuses `MediaManager.generate_audio` with the example text and
  the media name `<safe>_example` (existing cache, retries, validation and
  throttling apply). Empty example → no file, empty field.
- `CardGenerator.create_cards` gains `example_audio_path`; the field value is
  `[sound:<safe>_example.mp3]` for all five v2 models.

## Section 3 — cloze model (number 6)

- `genanki.Model` with `model_type=CLOZE`, fields `[English, Text, Hint]`:
  `English` first (GUID + push identity), `Text` is the example with
  `{{c1::…}}`, `Hint` is the Russian translation.
- Front: `{{cloze:Text}}` + `{{hint:Hint}}`; back: full sentence + hint
  revealed. Card CSS shared with the other models; standard cloze styling.
- Cloze building rule: find the **exact, case-insensitive** occurrence of the
  word in the example (works for multi-word expressions); wrap the first
  occurrence. No occurrence (inflected form in the text) → no cloze note for
  this word, a warning with the word, other card types unaffected.
- CLI: `6 = EN-RU Cloze` in the model list, part of `all`; markdown-safe
  models become 1, 2, 5, 6.

## Section 4 — identity, push, pull

- `VocabNote` GUID policy unchanged (first field + model id); v2 ids yield
  fresh GUIDs by design. Cloze notes use the same class — first field is
  `English`, so `--push` matching ("word + note type") works uniformly.
- `ensure_models` creates the v2 types and cloze on first `--push`.
- `fetch_mature_words` scans **both** legacy and v2 model names (legacy names
  kept as a constant), so words learned on old decks keep flowing into the
  ledger.

## Section 5 — testing and verification

- TDD throughout: tests first, watch them fail.
- Guard tests move to v2: new ids differ from all retired ids, field lists
  end with `ExampleAudio`, names carry the suffix.
- New tests: cloze building (found / not found / multi-word / case
  insensitivity / first occurrence only), example-audio field wiring and the
  `EXAMPLE_AUDIO=FALSE` switch, `all` = 1–6, `--from-md` allows 6, mature-word
  pull covers legacy + v2 names.
- E2E offline on `cards.example.csv`, all models: expected 12 × 6 = 72 notes
  (minus cloze misses when a word does not occur verbatim in its example).
- Docs: README (model 6, example audio, upgrade note about v2), CLAUDE.md.

## Out of scope

- Migrating existing notes/cards to v2 (owner deletes old decks manually).
- Audio on cloze cards; per-occurrence multi-cloze (`c2`, `c3`).
- Any AnkiConnect model-mutation actions (`modelFieldAdd`) — rejected in
  favor of clean v2 types.
