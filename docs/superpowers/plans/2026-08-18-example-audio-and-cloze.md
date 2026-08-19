# Example Audio + Cloze Cards (v2 Note Types) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship example-sentence audio on all cards and a sixth cloze card type as one v2 note-type migration.

**Architecture:** All five models get v2 successors (new frozen ids, " v2" name suffix, `ExampleAudio` field appended last, played on the back). A new CLOZE-type model (number 6) hides the word inside its example with a collapsible Russian hint. The media pipeline reuses `MediaManager.generate_audio` for `<safe>_example.mp3`; identity (GUID = first field + model id) and push/pull flows are unchanged, with the mature-words pull additionally scanning legacy model names.

**Tech Stack:** Python 3.9+, genanki 0.13.1, gTTS, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-18-example-audio-and-cloze-design.md`

## Global Constraints

- Frozen v2 ids (never change after this ships): EN-RU Typing v2 = 1298336501, RU-EN Typing v2 = 1354702052, EN-RU Choice v2 = 1427185897, RU-EN Choice v2 = 1495623708, RU-EN Scramble v2 = 1563008841, EN-RU Cloze = 1631442296.
- Retired v1 ids (must never be reused): 73727116, 4392726, 2343456, 23436536, 234556757.
- `ExampleAudio` is always the LAST field (first-field GUID identity must not move).
- All repo text is English. Tests run with `.venv/Scripts/python -m pytest` from the repo root.
- DLP caution (machine-local): never read `src/anki_generator.py` or `config.properties.sample` raw — only through the sanitizing perl pipe; edit them with scripted anchor replacements that avoid the API-key line.

---

### Task 1: Factory v2 (typing + choice)

**Files:**
- Modify: `src/models/factory.py`
- Modify: `src/models/en_ru_typing_model.py`, `src/models/ru_en_typing_model.py`, `src/models/en_ru_choice_model.py`, `src/models/ru_en_choice_model.py`
- Test: `tests/test_models_factory.py`

**Interfaces:**
- Produces: `make_typing_model(..., name_suffix: str = "")`, `make_choice_model(..., name_suffix: str = "")`; `RETIRED_MODEL_IDS` frozenset in `factory.py`; four `model` objects with v2 ids/names and field lists ending in `"ExampleAudio"`.

- [ ] **Step 1: Update guard tests to the v2 contract (failing first).** In `tests/test_models_factory.py` replace the id/field/name expectations:

```python
BASE_FIELDS = ["English", "Russian", "Example", "Audio", "Image", "ExampleAudio"]

def test_model_ids_and_fields_are_frozen():
    assert en_ru_typing_model.model.model_id == 1298336501
    assert ru_en_typing_model.model.model_id == 1354702052
    assert en_ru_choice_model.model.model_id == 1427185897
    assert ru_en_choice_model.model.model_id == 1495623708
    assert field_names(en_ru_typing_model.model) == BASE_FIELDS
    assert field_names(ru_en_typing_model.model) == BASE_FIELDS
    assert field_names(en_ru_choice_model.model) == [
        "English", "Russian", "Example", "Audio",
        "RussianIncorrect1", "RussianIncorrect2",
        "RussianIncorrect3", "RussianIncorrect4", "Image", "ExampleAudio"]
    assert field_names(ru_en_choice_model.model) == [
        "English", "Russian", "Example", "Audio",
        "EnglishIncorrect1", "EnglishIncorrect2",
        "EnglishIncorrect3", "EnglishIncorrect4", "Image", "ExampleAudio"]

def test_model_names_carry_v2_suffix():
    assert en_ru_typing_model.model.name == "EN-RU Typing Model v2"
    assert ru_en_typing_model.model.name == "RU-EN Typing Model v2"
    assert en_ru_choice_model.model.name == "EN-RU Choice Model v2"
    assert ru_en_choice_model.model.name == "RU-EN Choice Model v2"
```

Add:

```python
def test_v2_ids_do_not_reuse_retired_ids():
    from models.factory import RETIRED_MODEL_IDS
    v2_ids = {m.model.model_id for m in (en_ru_typing_model, ru_en_typing_model,
              en_ru_choice_model, ru_en_choice_model, ru_en_scramble_model)}
    assert RETIRED_MODEL_IDS == {73727116, 4392726, 2343456, 23436536, 234556757}
    assert not v2_ids & RETIRED_MODEL_IDS

def test_example_audio_plays_on_the_back_only():
    for mod in (en_ru_typing_model, ru_en_typing_model, en_ru_choice_model, ru_en_choice_model):
        assert "{{ExampleAudio}}" not in mod.model.templates[0]["qfmt"]
        assert "{{ExampleAudio}}" in mod.model.templates[0]["afmt"]
```

(Scramble expectations switch in Task 2 — in this task keep scramble asserts at v1 values so the suite isolates Task 1.)

- [ ] **Step 2: Run and watch it fail.** `.venv/Scripts/python -m pytest tests/test_models_factory.py -q` — expect failures on ids/names/fields for the four factory models, scramble still green.

- [ ] **Step 3: Implement factory v2.** In `factory.py`: add `RETIRED_MODEL_IDS = frozenset({73727116, 4392726, 2343456, 23436536, 234556757})`; add `{"name": "ExampleAudio"}` as the last field in both `make_*_model` field lists; add `name_suffix: str = ""` parameter used as `f"{direction} Typing Model{name_suffix}"` / `f"{direction} Choice Model{name_suffix}"` (template names unchanged); append the example-audio line to both afmt templates after `{{Example}}`:

```
                {{Example}}
                {{ExampleAudio}}
```

Update the four call sites, e.g.:

```python
model = make_typing_model(
    model_id=1298336501,
    direction="EN-RU",
    prompt_field="English",
    answer_field="Russian",
    audio_in_answer=True,
    name_suffix=" v2",
)
```

(ru_en_typing: 1354702052; en_ru_choice: 1427185897; ru_en_choice: 1495623708.)

- [ ] **Step 4: Run tests.** Same command — the four factory-model tests pass; `test_card_generator.py` may fail on field counts (fixed in Task 4; if it fails here, note it and continue — the suite gate is at Task 4's end).

- [ ] **Step 5: Commit** `feat: v2 typing/choice models with ExampleAudio field`.

### Task 2: Scramble v2 (hand-written file)

**Files:**
- Modify: `src/models/ru_en_scramble_model.py`
- Test: `tests/test_models_factory.py`

**Interfaces:**
- Produces: scramble `model` with id 1563008841, name `"RU-EN Scramble Model v2"`, fields ending `"ExampleAudio"`, `{{ExampleAudio}}` in afmt only.

- [ ] **Step 1: Update scramble guard tests (failing first).** Id 1563008841, name `"RU-EN Scramble Model v2"`, fields `BASE_FIELDS`, and extend `test_example_audio_plays_on_the_back_only` to include `ru_en_scramble_model`.
- [ ] **Step 2: Watch them fail** (`pytest tests/test_models_factory.py -q`).
- [ ] **Step 3: Edit `ru_en_scramble_model.py` in place:** id `234556757` → `1563008841`; name → `"RU-EN Scramble Model v2"`; append `{"name": "ExampleAudio"}` after `{"name": "Image"}`; in the afmt add `{{ExampleAudio}}` on the line after `{{Example}}` (back side only — the scramble qfmt must stay untouched).
- [ ] **Step 4: Run tests** — scramble guards pass.
- [ ] **Step 5: Commit** `feat: v2 scramble model with ExampleAudio field`.

### Task 3: Cloze model and card building

**Files:**
- Create: `src/models/en_ru_cloze_model.py`
- Modify: `src/utils/card_generator.py`
- Test: `tests/test_card_generator.py` (new cloze tests)

**Interfaces:**
- Consumes: `CARD_CSS` from `models.factory`; `VocabNote`, `CardData` from `card_generator`.
- Produces: `en_ru_cloze_model.model` (id 1631442296, CLOZE type, fields `[English, Text, Hint]`); `build_cloze_text(word: str, example: str) -> str | None` in `card_generator.py`; `CardGenerator.EN_CLOZE = 6`; `MODEL_NAMES[6] == "EN-RU Cloze"`; cloze notes emitted by `create_cards`; `ALL_MODELS` includes the cloze model.

- [ ] **Step 1: Write failing tests** in `tests/test_card_generator.py`:

```python
from utils.card_generator import build_cloze_text

def test_build_cloze_text_wraps_first_occurrence_case_insensitive():
    assert build_cloze_text("dojo", "She trained in the Dojo daily.") == \
        "She trained in the {{c1::Dojo}} daily."

def test_build_cloze_text_handles_multiword_expressions():
    assert build_cloze_text("rolled over", "The ship rolled over slowly.") == \
        "The ship {{c1::rolled over}} slowly."

def test_build_cloze_text_wraps_only_the_first_occurrence():
    assert build_cloze_text("dojo", "dojo here, dojo there") == \
        "{{c1::dojo}} here, dojo there"

def test_build_cloze_text_returns_none_when_word_absent():
    assert build_cloze_text("sport", "One moon sported five thousand.") is None
    assert build_cloze_text("dojo", "") is None

def test_cloze_note_structure():
    generator = CardGenerator(selected_models=[CardGenerator.EN_CLOZE])
    notes = generator.create_cards(make_card_data())
    assert len(notes) == 1
    assert notes[0].model.model_id == 1631442296
    assert notes[0].fields == ["dojo", "She trained in the {{c1::dojo}}.", "додзё"]

def test_cloze_note_skipped_when_word_not_in_example():
    card = CardData("sport", "спорт", "One moon sported five thousand.", [], [])
    notes = CardGenerator(selected_models=[CardGenerator.EN_CLOZE]).create_cards(card)
    assert notes == []
```

Note: `test_build_cloze_text_returns_none_when_word_absent` — "sport" IS a substring of "sported"; the expected behavior needs word-boundary matching, NOT plain substring. Implementation below uses a regex with boundaries.

- [ ] **Step 2: Watch them fail** (`pytest tests/test_card_generator.py -q` — ImportError/AttributeError = feature missing).

- [ ] **Step 3: Implement.** New `src/models/en_ru_cloze_model.py`:

```python
import genanki

from models.factory import CARD_CSS

CLOZE_CSS = """\
        .cloze {
            font-weight: bold;
            color: #2a7ae2;
        }"""

model = genanki.Model(
    1631442296,
    "EN-RU Cloze Model",
    model_type=genanki.Model.CLOZE,
    fields=[
        {"name": "English"},
        {"name": "Text"},
        {"name": "Hint"},
    ],
    templates=[
        {
            "name": "EN-RU Cloze",
            "qfmt": """
                {{cloze:Text}}
                <br><br>
                {{hint:Hint}}
            """,
            "afmt": """
                {{cloze:Text}}
                <hr id=answer>
                {{Hint}}
            """,
        }
    ],
    css="\n" + CARD_CSS + "\n\n" + CLOZE_CSS + "\n    ",
)
```

In `card_generator.py`: import the module; add to `ALL_MODELS`; constants `EN_CLOZE = 6`, `MODEL_NAMES[EN_CLOZE] = "EN-RU Cloze"`; `self.model_en_cloze = en_ru_cloze_model.model` in `__init__` (and 6 joins the default all-models list); module function:

```python
def build_cloze_text(word: str, example: str):
    """Wrap the first whole-word, case-insensitive occurrence of word in {{c1::...}}."""
    if not example:
        return None
    match = re.search(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", example, re.IGNORECASE)
    if match is None:
        return None
    return f"{example[:match.start()]}{{{{c1::{match.group(0)}}}}}{example[match.end():]}"
```

and the branch inside `create_cards` (before the final `logger.debug`):

```python
            # EN cloze card: the example with the word hidden
            if self.EN_CLOZE in self.selected_models:
                cloze_text = build_cloze_text(card_data.english, card_data.example)
                if cloze_text is None:
                    logger.warning(f"No exact occurrence of '{card_data.english}' "
                                   "in its example - cloze card skipped")
                else:
                    notes.append(
                        VocabNote(
                            model=self.model_en_cloze,
                            fields=[card_data.english, cloze_text, card_data.russian],
                        )
                    )
```

- [ ] **Step 4: Run tests** — cloze tests pass, no other regressions (`pytest -q`).
- [ ] **Step 5: Commit** `feat: EN-RU cloze model built from the example sentence`.

### Task 4: Example-audio pipeline

**Files:**
- Modify: `src/utils/card_generator.py` (create_cards signature), `src/anki_generator.py` (config + loop), `config.properties.sample`
- Test: `tests/test_card_generator.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `MediaManager.generate_audio(text, safe_filename)` (exists).
- Produces: `create_cards(..., example_audio_path: str = None)`; `example_audio_enabled(properties: dict) -> bool` in `anki_generator.py`; media name convention `<safe_filename>_example.mp3`.

- [ ] **Step 1: Write failing tests.** In `tests/test_card_generator.py`:

```python
def test_example_audio_field_lands_last_on_v2_models():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING, CardGenerator.EN_RU_CHOICE])
    notes = generator.create_cards(make_card_data(), example_audio_path="x_example.mp3")
    for note in notes:
        assert note.fields[-1] == "[sound:dojo_5e09bf57_example.mp3]"

def test_cloze_note_carries_no_example_audio():
    generator = CardGenerator(selected_models=[CardGenerator.EN_CLOZE])
    notes = generator.create_cards(make_card_data(), example_audio_path="x_example.mp3")
    assert len(notes[0].fields) == 3

def test_example_audio_field_empty_without_path():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(make_card_data())
    assert notes[0].fields[-1] == ""
```

In `tests/test_cli.py`:

```python
from anki_generator import example_audio_enabled

def test_example_audio_enabled_by_default():
    assert example_audio_enabled({}) is True

def test_example_audio_disabled_by_config():
    assert example_audio_enabled({"EXAMPLE_AUDIO": "FALSE"}) is False
    assert example_audio_enabled({"EXAMPLE_AUDIO": "false "}) is False
```

- [ ] **Step 2: Watch them fail.**
- [ ] **Step 3: Implement.** `create_cards(self, card_data, audio_path=None, image_path=None, example_audio_path=None)`; alongside `audio_field`/`image_field`:

```python
        example_audio_field = (f"[sound:{card_data.safe_filename}_example.mp3]"
                               if example_audio_path else "")
```

append `example_audio_field` as the last element of the `fields=[...]` list of all five v2-model branches (NOT the cloze branch). In `anki_generator.py` (scripted anchor edits only — DLP): module function

```python
def example_audio_enabled(properties: dict) -> bool:
    """EXAMPLE_AUDIO=FALSE in config.properties disables example-sentence audio."""
    return properties.get('EXAMPLE_AUDIO', 'true').strip().lower() != 'false'
```

read it once in `main()` next to the other config reads (`generate_example_audio = example_audio_enabled(properties)`), and in the per-word loop after the word-audio block:

```python
            # Example-sentence audio (second mp3, played on the back)
            example_audio_path = None
            if generate_example_audio and card_data.example:
                example_audio_path = media_manager.generate_audio(
                    text=card_data.example,
                    safe_filename=f"{card_data.safe_filename}_example",
                )
                if example_audio_path:
                    media_files.append(example_audio_path)
```

pass `example_audio_path=example_audio_path` into `create_cards`. Add to `config.properties.sample` after DECK_NAME block:

```
# Example-sentence audio on card backs (doubles TTS calls). Set FALSE to disable.
EXAMPLE_AUDIO=TRUE
```

- [ ] **Step 4: Run the full suite** — everything green, including any Task 1 leftovers.
- [ ] **Step 5: Commit** `feat: example-sentence audio on all v2 cards, EXAMPLE_AUDIO config`.

### Task 5: CLI — model 6 everywhere

**Files:**
- Modify: `src/anki_generator.py` (interactive menu, markdown-safe list)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `CardGenerator.MODEL_NAMES` now has 6 keys (Task 3).
- Produces: `MARKDOWN_SAFE_MODELS == [1, 2, 5, 6]`; `parse_model_selection("all") == [1..6]`; interactive menu lists 6 models with "7. All models".

- [ ] **Step 1: Write failing tests** in `tests/test_cli.py`:

```python
def write_md_fixture(tmp_path):
    md_path = tmp_path / "words.md"
    md_path.write_text(
        "| Word | Translation | Example |
"
        "| --- | --- | --- |
"
        "| dojo | додзё | She trained in the dojo. |
",
        encoding="utf-8",
    )
    return md_path

def test_all_includes_cloze():
    assert parse_model_selection("all") == [1, 2, 3, 4, 5, 6]

def test_from_md_default_models_include_cloze(tmp_path):
    options = parse_args(["--from-md", str(write_md_fixture(tmp_path))])
    assert options.selected_models == [1, 2, 5, 6]

def test_from_md_allows_cloze_explicitly(tmp_path):
    options = parse_args(["--from-md", str(write_md_fixture(tmp_path)), "--models", "6"])
    assert options.selected_models == [6]

def test_from_md_still_rejects_choice_models(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--from-md", str(write_md_fixture(tmp_path)), "--models", "3"])
    assert exc_info.value.code == 2
```

(`parse_model_selection("all")` already derives from `MODEL_NAMES`, so the first test goes green in Task 3 — keep it as a regression guard; the from-md ones fail until this task.)

- [ ] **Step 2: Watch the from-md tests fail.**
- [ ] **Step 3: Implement** (scripted anchor edits): `MARKDOWN_SAFE_MODELS` gains `CardGenerator.EN_CLOZE`; the `--from-md` model-gate error message becomes "--from-md supports only models 1, 2, 5, and 6"; interactive `select_card_models`: menu lines become the 6 models + `"7. All models"`, `choice == "7"` selects `[1, 2, 3, 4, 5, 6]`, range validation `1 <= c <= 6`.
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit** `feat: cloze available in CLI, markdown mode and interactive menu`.

### Task 6: Mature-words pull covers legacy names

**Files:**
- Modify: `src/utils/card_generator.py`, `src/anki_generator.py`
- Test: `tests/test_card_generator.py`

**Interfaces:**
- Produces: `LEGACY_MODEL_NAMES` (list) and `model_names_for_sync() -> list` in `card_generator.py`; `_sync_learned_words_from_anki` uses it.

- [ ] **Step 1: Write failing test:**

```python
def test_sync_names_cover_v2_cloze_and_legacy():
    from utils.card_generator import model_names_for_sync
    names = model_names_for_sync()
    assert "EN-RU Typing Model v2" in names and "EN-RU Cloze Model" in names
    assert "EN-RU Typing Model" in names            # legacy v1
    assert "EN-RU Scramble Model" in names          # pre-rename scramble
    assert "RU-EN Scramble Model" in names          # post-rename scramble
```

- [ ] **Step 2: Watch it fail.**
- [ ] **Step 3: Implement** in `card_generator.py`:

```python
LEGACY_MODEL_NAMES = [
    "EN-RU Typing Model", "RU-EN Typing Model",
    "EN-RU Choice Model", "RU-EN Choice Model",
    "EN-RU Scramble Model", "RU-EN Scramble Model",
]

def model_names_for_sync() -> list:
    """Model names to scan for mature words: current types plus retired v1 names."""
    return [model.name for model in ALL_MODELS] + LEGACY_MODEL_NAMES
```

In `_sync_learned_words_from_anki` replace `[model.name for model in ALL_MODELS]` with `model_names_for_sync()` (adjust the import).

- [ ] **Step 3b: Cloze push support (failing test first).** AnkiConnect's `createModel` builds a standard model unless `isCloze` is passed - without it, a first `--push` on a fresh collection would create a broken cloze type. In `tests/test_anki_connect.py`:

```python
def test_ensure_models_marks_cloze_models():
    from models import en_ru_cloze_model
    client = FakeClient(results={"modelNames": []})

    ensure_models(client, [en_ru_cloze_model.model])

    params = [c for c in client.calls if c[0] == "createModel"][0][1]
    assert params["isCloze"] is True
```

Watch it fail, then in `ensure_models` (in `src/utils/anki_connect.py`) add `import genanki` and pass `isCloze=(getattr(model, "model_type", 0) == genanki.Model.CLOZE)` to the `createModel` invoke.

- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit** `feat: mature-words pull scans legacy note types too`.

### Task 7: E2E, docs, spec/plan files

**Files:**
- Modify: `README.md`, `.claude/CLAUDE.md`
- Add: `docs/superpowers/specs/...-design.md`, `docs/superpowers/plans/...-example-audio-and-cloze.md` (this file) to git

**Interfaces:** none (documentation + verification).

- [ ] **Step 1: E2E with network.** `.venv/Scripts/anki-cards-generator --csv cards.example.csv --models all` (word audio comes from cache, 12 example mp3s are new TTS calls; images skipped without keys). Expect: ~72 notes (12 × 6; minus any cloze skip warnings — read them and confirm each is a genuinely absent occurrence), `.apkg` written. Then rerun `--offline` — 0 TTS calls, same note count.
- [ ] **Step 2: Cleanup.** Delete `known_words.json` (test artifact) and the generated `results/cards.example.apkg` stays gitignored.
- [ ] **Step 3: Docs.** README: model 6 in the "Card Types Created" list and the models table ("6 = EN-RU Cloze", `all` = 1–6, menu shows 7 = All); `EXAMPLE_AUDIO` row in the config section; short "v2 note types" upgrade note (old decks keep working; delete old decks before regenerating old chapters). `.claude/CLAUDE.md`: frozen-invariants section — v2 id table + retired v1 ids + "ExampleAudio always last".
- [ ] **Step 4: Full suite one last time; commit** `docs: v2 migration, cloze and example audio` (includes spec + this plan file).

## Verification (whole feature)

1. `pytest -q` fully green.
2. E2E from Task 7 (fresh media names `_example.mp3` on disk; cloze notes present in the .apkg).
3. Manual (deferred to the live-Anki session recorded in the vault note "Проверка AnkiConnect push"): `--push` creates the six v2/cloze note types, collapsible RU hint works on a cloze card, example audio plays on backs.
