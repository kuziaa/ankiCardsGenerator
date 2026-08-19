# Unified Note Type (v3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace the five per-direction note types with one unified `EN-RU Vocabulary` note type (5 templates, gate fields), so a word is one note instead of six.

**Architecture:** A new frozen genanki model (id 1712849305, 19 fields) whose five card templates are the existing v2 qfmt/afmt wrapped in `{{#Gate}}...{{/Gate}}` sections; `CardGenerator.create_cards` emits one unified note plus the optional cloze note; `push_notes` becomes a merge that never degrades a stored note. The five v2 models are retired (ids into `RETIRED_MODEL_IDS`, names into `LEGACY_MODEL_NAMES`).

**Tech Stack:** Python 3.9+, genanki 0.13.1, pytest, AnkiConnect (JSON API).

**Spec:** `docs/superpowers/specs/2026-08-19-unified-note-type-design.md`

## Global Constraints

- Unified model id is exactly **1712849305**; cloze model id **1631442296** stays untouched. Retired ids (v1: 73727116, 4392726, 2343456, 23436536, 234556757; v2: 1298336501, 1354702052, 1427185897, 1495623708, 1563008841) must never be reused.
- The 19-field order of the unified model is frozen (see Task 1 table); templates in frozen order: `EN-RU Typing`, `RU-EN Typing`, `EN-RU Choice`, `RU-EN Choice`, `RU-EN Scramble`.
- Cards must render pixel-identical to v2; gate values never appear on a card.
- CSV contract, LLM prompts, `--from-md` parsing, media pipeline, CLI surface (`--models` numbering 1–6) do not change.
- Everything written to the repo is English-only.
- **The owner reviews every diff before each commit** (team workflow rule). At each Commit step, stop and ask for approval first, unless blanket commit permission was granted for the session.
- Run tests from the repo root: `python -m pytest` (pythonpath is configured in `pyproject.toml`).

---

### Task 1: The unified model (`vocab_model.py`) + scramble template sources in `factory.py`

**Files:**
- Modify: `src/models/factory.py` (append three constants; change nothing existing)
- Create: `src/models/vocab_model.py`
- Create: `tests/test_vocab_model.py`

**Interfaces:**
- Consumes: `factory._render`, `factory._TYPING_QFMT/_TYPING_AFMT`, `factory._CHOICE_QFMT/_CHOICE_AFMT/_CHOICE_SCRIPT`, `factory.CARD_CSS/CHOICE_WIDGET_CSS/IMAGE_CSS` (all exist today).
- Produces: `vocab_model.model` (genanki.Model), `vocab_model.MODEL_ID = 1712849305`, `vocab_model.MODEL_NAME = "EN-RU Vocabulary"`, `vocab_model.GATE_ON = "y"`, `vocab_model.GATE_FIELDS = ["EnRuTyping", "RuEnTyping", "EnRuChoice", "RuEnChoice", "Scramble"]`. Task 2 relies on all five names.

The unified field order (frozen forever):

| ord | field |
|-----|-------|
| 0–5 | `English`, `Russian`, `Example`, `Audio`, `Image`, `ExampleAudio` |
| 6–9 | `RussianIncorrect1..4` |
| 10–13 | `EnglishIncorrect1..4` |
| 14–18 | `EnRuTyping`, `RuEnTyping`, `EnRuChoice`, `RuEnChoice`, `Scramble` |

- [x] **Step 1: Move the scramble template into `factory.py` as constants**

Append to `src/models/factory.py` (after `_CHOICE_AFMT`, before `def _render`):

1. `_SCRAMBLE_QFMT` — copy the entire `"qfmt"` string of the `RU-EN Scramble` template from `src/models/ru_en_scramble_model.py` **verbatim**, changing only the outer wrapper line
   `<div class="card">` → `<div class="card scramble">` (first line of the markup; the `<script>` block and everything else stays byte-identical).
2. `_SCRAMBLE_AFMT` — copy the entire `"afmt"` string from the same file verbatim, with the same single change: `<div class="card">` → `<div class="card scramble">`.
3. `SCRAMBLE_WIDGET_CSS` — the scramble-specific rules from that file's `css` (drop its duplicated `.card`, `.image-front img`, `.image-back img` rules — those come from `CARD_CSS`/`IMAGE_CSS`), with the two `#answer-field` rules scoped under `.scramble` so they cannot leak into Choice cards, and `margin: 0;` added to neutralize the Choice widget's global `#answer-field { margin: 20px 0; }`:

```python
SCRAMBLE_WIDGET_CSS = """\
        .question-text {
            font-size: 24px;
            font-weight: bold;
            margin: 15px 0;
            color: #333;
        }

        .example-text {
            font-style: italic;
            margin: 20px 0;
            color: #555;
            padding: 0 10px;
            text-align: center;
        }

        .input-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }

        /* Scoped: the Choice widget styles the same ids globally */
        .scramble #answer-field {
            margin: 0;
            max-width: 400px;
            text-align: center;
        }

        .scramble #answer-field input {
            font-size: 18px;
            padding: 12px;
            width: 100%;
            text-align: center;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            box-sizing: border-box;
        }

        .letters-container {
            margin: 20px 0;
            min-height: 50px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
        }

        .error-counter {
            margin: 15px 0;
            font-size: 18px;
            font-weight: bold;
        }

        #error-count {
            color: red;
            font-size: 20px;
        }

        .letter-btn {
            color: black;
            font-weight: bold;
            margin: 3px;
            padding: 10px 15px;
            font-size: 18px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
            min-width: 40px;
            transition: all 0.3s;
            background-color: #4CAF50;
        }

        .letter-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .letter-btn:disabled {
            background-color: #888;
            cursor: default;
            transform: none;
            box-shadow: none;
        }"""
```

Note: the v2 scramble file has a Russian comment (`/* Контейнер для поля ввода */`) — do not carry it over (English-only repo); the rules above already replace it with nothing / English comments.

Do NOT touch `src/models/ru_en_scramble_model.py` in this task — it keeps working from its own inline copy until Task 3 deletes it.

- [x] **Step 2: Write the failing tests**

Create `tests/test_vocab_model.py`:

```python
from models import vocab_model
from models.factory import RETIRED_MODEL_IDS
from utils.card_generator import VocabNote

DATA_FIELDS = ["English", "Russian", "Example", "Audio", "Image", "ExampleAudio"]
DISTRACTOR_FIELDS = [f"RussianIncorrect{i}" for i in range(1, 5)] + \
                    [f"EnglishIncorrect{i}" for i in range(1, 5)]
GATE_FIELDS = ["EnRuTyping", "RuEnTyping", "EnRuChoice", "RuEnChoice", "Scramble"]
TEMPLATE_NAMES = ["EN-RU Typing", "RU-EN Typing",
                  "EN-RU Choice", "RU-EN Choice", "RU-EN Scramble"]


def field_names(model):
    return [field["name"] for field in model.fields]


def template(name):
    return next(t for t in vocab_model.model.templates if t["name"] == name)


def make_note(gates):
    """A note with data everywhere and the given 5 gate values."""
    fields = (["dojo", "додзё", "She trained in the dojo.",
               "[sound:a.mp3]", '<img src="a.jpg">', "[sound:ae.mp3]"]
              + ["d1", "d2", "d3", "d4", "e1", "e2", "e3", "e4"]
              + list(gates))
    return VocabNote(model=vocab_model.model, fields=fields)


def test_model_id_name_and_field_order_are_frozen():
    assert vocab_model.MODEL_ID == 1712849305
    assert vocab_model.model.model_id == 1712849305
    assert vocab_model.model.name == "EN-RU Vocabulary"
    assert field_names(vocab_model.model) == DATA_FIELDS + DISTRACTOR_FIELDS + GATE_FIELDS
    assert vocab_model.GATE_FIELDS == GATE_FIELDS
    assert vocab_model.MODEL_ID not in RETIRED_MODEL_IDS


def test_template_names_and_order_are_frozen():
    assert [t["name"] for t in vocab_model.model.templates] == TEMPLATE_NAMES


def test_every_front_is_wrapped_in_its_gate():
    for tmpl_name, gate in zip(TEMPLATE_NAMES, GATE_FIELDS):
        qfmt = template(tmpl_name)["qfmt"].strip()
        assert qfmt.startswith("{{#%s}}" % gate)
        assert qfmt.endswith("{{/%s}}" % gate)
        # the gate never leaks into the answer side
        assert gate not in template(tmpl_name)["afmt"]


def test_note_cards_match_gates_exactly():
    on = vocab_model.GATE_ON
    assert sorted(c.ord for c in make_note([on, "", on, "", ""]).cards) == [0, 2]
    assert sorted(c.ord for c in make_note([on] * 5).cards) == [0, 1, 2, 3, 4]
    assert make_note([""] * 5).cards == []


def test_cards_exist_regardless_of_missing_data():
    # gates alone decide existence: a note with empty distractors still
    # produces the choice cards (markdown mode fills data later)
    fields = (["dojo", "додзё", "", "", "", ""] + [""] * 8
              + ["", "", vocab_model.GATE_ON, vocab_model.GATE_ON, ""])
    note = VocabNote(model=vocab_model.model, fields=fields)
    assert sorted(c.ord for c in note.cards) == [2, 3]


def test_audio_placement_semantics_carry_over_from_v2():
    # Typing: audio always on the front; only EN-RU repeats it on the back
    assert "{{Audio}}" in template("EN-RU Typing")["qfmt"]
    assert "{{Audio}}" in template("RU-EN Typing")["qfmt"]
    assert "{{Audio}}" in template("EN-RU Typing")["afmt"]
    assert "{{Audio}}" not in template("RU-EN Typing")["afmt"]
    # Choice: RU-EN keeps English audio off the front (it gives the answer away)
    assert "{{Audio}}" in template("EN-RU Choice")["qfmt"]
    assert "{{Audio}}" not in template("RU-EN Choice")["qfmt"]
    ru_en_afmt = template("RU-EN Choice")["afmt"]
    assert ru_en_afmt.index("<hr id=answer>") < ru_en_afmt.index("{{Audio}}")


def test_choice_buttons_use_direction_specific_distractors():
    en_ru_qfmt = template("EN-RU Choice")["qfmt"]
    ru_en_qfmt = template("RU-EN Choice")["qfmt"]
    for i in range(1, 5):
        assert f"{{{{RussianIncorrect{i}}}}}" in en_ru_qfmt
        assert f"{{{{EnglishIncorrect{i}}}}}" in ru_en_qfmt
    assert 'data-answer="{{Russian}}"' in en_ru_qfmt
    assert 'data-answer="{{English}}"' in ru_en_qfmt


def test_prompt_and_answer_are_mirrored():
    assert "{{type:Russian}}" in template("EN-RU Typing")["qfmt"]
    assert "{{type:English}}" in template("RU-EN Typing")["qfmt"]
    assert "<h2>{{English}}</h2>" in template("EN-RU Choice")["qfmt"]
    assert "<h2>{{Russian}}</h2>" in template("RU-EN Choice")["qfmt"]


def test_example_audio_plays_on_backs_only():
    for tmpl in vocab_model.model.templates:
        assert "{{ExampleAudio}}" not in tmpl["qfmt"]
        assert "{{ExampleAudio}}" in tmpl["afmt"]


def test_scramble_styles_are_scoped_and_template_carries_the_class():
    assert 'class="card scramble"' in template("RU-EN Scramble")["qfmt"]
    assert 'class="card scramble"' in template("RU-EN Scramble")["afmt"]
    assert ".scramble #answer-field" in vocab_model.model.css
    # the choice widget styles stay global, unscoped
    assert ".choice-btn" in vocab_model.model.css


def test_service_fields_carry_editor_hints():
    by_name = {field["name"]: field for field in vocab_model.model.fields}
    for name in DISTRACTOR_FIELDS + GATE_FIELDS:
        assert by_name[name].get("collapsed") is True
        assert by_name[name].get("description")
    for name in DATA_FIELDS:
        assert "collapsed" not in by_name[name]
```

- [x] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_vocab_model.py -q`
Expected: FAIL at import time — `cannot import name 'vocab_model' from 'models'`.

- [x] **Step 4: Implement `src/models/vocab_model.py`**

```python
"""The unified vocabulary note type (v3): one note per word, five templates.

Card existence is controlled by gate fields: each template's front is wrapped
in a {{#Gate}}...{{/Gate}} section, so an empty gate renders an empty front
and neither genanki nor Anki generates that card. The gate value itself never
appears on a card. The model id, the 19-field order and the template order
are frozen: changing them corrupts existing Anki collections.
"""

import genanki

from models.factory import (CARD_CSS, CHOICE_WIDGET_CSS, IMAGE_CSS,
                            SCRAMBLE_WIDGET_CSS, _CHOICE_AFMT, _CHOICE_QFMT,
                            _CHOICE_SCRIPT, _SCRAMBLE_AFMT, _SCRAMBLE_QFMT,
                            _TYPING_AFMT, _TYPING_QFMT, _render)

MODEL_ID = 1712849305
MODEL_NAME = "EN-RU Vocabulary"
GATE_ON = "y"
# Order is frozen: card ords in existing collections depend on it
GATE_FIELDS = ["EnRuTyping", "RuEnTyping", "EnRuChoice", "RuEnChoice", "Scramble"]

VOCAB_CSS = ("\n" + CARD_CSS + "\n\n" + CHOICE_WIDGET_CSS + "\n\n" + IMAGE_CSS
             + "\n\n" + SCRAMBLE_WIDGET_CSS + "\n    ")


def _gated(qfmt: str, gate: str) -> str:
    """Wrap a front in a gate section: an empty gate means no card."""
    return "{{#%s}}\n%s\n{{/%s}}" % (gate, qfmt, gate)


def _service_field(name: str, description: str) -> dict:
    # collapsed/description are best-effort editor hints (Anki 23.10+)
    return {"name": name, "collapsed": True, "description": description}


_FIELDS = (
    [{"name": name} for name in
     ("English", "Russian", "Example", "Audio", "Image", "ExampleAudio")]
    + [_service_field(f"RussianIncorrect{i}", "EN-RU Choice distractor")
       for i in range(1, 5)]
    + [_service_field(f"EnglishIncorrect{i}", "RU-EN Choice distractor")
       for i in range(1, 5)]
    + [_service_field(gate, "y = this card exists") for gate in GATE_FIELDS]
)

_TEMPLATES = [
    {
        "name": "EN-RU Typing",
        "qfmt": _gated(_render(_TYPING_QFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian"}), "EnRuTyping"),
        "afmt": _render(_TYPING_AFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__AUDIO_LINE__": "{{Audio}}<br><br><br>"}),
    },
    {
        "name": "RU-EN Typing",
        "qfmt": _gated(_render(_TYPING_QFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English"}), "RuEnTyping"),
        "afmt": _render(_TYPING_AFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__AUDIO_LINE__": None}),
    },
    {
        "name": "EN-RU Choice",
        "qfmt": _gated(_render(_CHOICE_QFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__INC__": "RussianIncorrect", "__SCRIPT__": _CHOICE_SCRIPT,
            "__AUDIO_FRONT__": "{{Audio}}<br>"}), "EnRuChoice"),
        "afmt": _render(_CHOICE_AFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__AUDIO_AFTER_HEADING__": "{{Audio}}<br>",
            "__AUDIO_AFTER_HR__": None}),
    },
    {
        "name": "RU-EN Choice",
        "qfmt": _gated(_render(_CHOICE_QFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__INC__": "EnglishIncorrect", "__SCRIPT__": _CHOICE_SCRIPT,
            "__AUDIO_FRONT__": None}), "RuEnChoice"),
        "afmt": _render(_CHOICE_AFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__AUDIO_AFTER_HEADING__": None,
            "__AUDIO_AFTER_HR__": "{{Audio}}<br>"}),
    },
    {
        "name": "RU-EN Scramble",
        "qfmt": _gated(_SCRAMBLE_QFMT, "Scramble"),
        "afmt": _SCRAMBLE_AFMT,
    },
]

model = genanki.Model(
    MODEL_ID,
    MODEL_NAME,
    fields=_FIELDS,
    templates=_TEMPLATES,
    css=VOCAB_CSS,
)
```

The per-template audio mappings above reproduce v2 exactly: EN-RU Typing repeats audio on the back, RU-EN Typing does not; EN-RU Choice plays audio on the front and after the heading, RU-EN Choice only after the `<hr>` divider.

- [x] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_vocab_model.py -q`
Expected: all PASS. Also run `python -m pytest -q` — the v2 suite must still pass untouched.

- [x] **Step 6: Commit (after owner review)**

```bash
git add src/models/factory.py src/models/vocab_model.py tests/test_vocab_model.py
git commit -m "feat: add the unified vocabulary note type (v3) with gate fields"
```

---

### Task 2: `CardGenerator` emits one unified note per word

**Files:**
- Modify: `src/utils/card_generator.py`
- Modify: `tests/test_card_generator.py`

**Interfaces:**
- Consumes: `vocab_model.model`, `vocab_model.GATE_ON`, `vocab_model.GATE_FIELDS` (Task 1).
- Produces: `CardGenerator.create_cards(...) -> List[genanki.Note]` returning 1–2 notes (unified + optional cloze); `ALL_MODELS == [vocab_model.model, en_ru_cloze_model.model]`; `model_names_for_sync()` covering unified + cloze + all legacy names. `src/anki_generator.py` needs **no changes** — it consumes `create_cards` and note `.model` attributes generically.

- [x] **Step 1: Update the tests**

In `tests/test_card_generator.py`, replace the tests listed below; keep `make_card_data`, the `safe_media_name`/`derive_deck_id`/`build_cloze_text` tests and the cloze tests (`test_cloze_note_structure`, `test_cloze_note_skipped_when_word_not_in_example`, `test_cloze_note_carries_no_example_audio`) unchanged.

Replace `test_create_cards_respects_selected_models_and_unique_guids`:

```python
def test_create_cards_returns_one_unified_note_with_gated_cards():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING,
                                               CardGenerator.RU_EN_SCRAMBLE])

    notes = generator.create_cards(make_card_data(), audio_path="dojo.mp3",
                                   image_path="dojo.jpg")

    assert len(notes) == 1
    note = notes[0]
    assert note.model.model_id == 1712849305
    assert sorted(card.ord for card in note.cards) == [0, 4]
    assert note.fields[3] == "[sound:dojo_5e09bf57.mp3]"
    assert note.fields[4] == '<img src="dojo_5e09bf57.jpg">'
    assert note.fields[14:19] == ["y", "", "", "", "y"]
```

Replace `test_choice_card_uses_russian_distractors_for_en_ru_choice`:

```python
def test_unified_note_carries_both_distractor_sets():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_CHOICE])

    notes = generator.create_cards(make_card_data())

    assert len(notes) == 1
    assert notes[0].fields[6:10] == ["зал ожидания", "игровая площадка",
                                     "спальная комната", "офис"]
    assert notes[0].fields[10:14] == ["mojo", "doge", "dose", "doze"]
    assert sorted(card.ord for card in notes[0].cards) == [2]
```

Add:

```python
def test_distractors_fill_even_when_choice_models_are_unselected():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(make_card_data())

    assert notes[0].fields[6:10] == ["зал ожидания", "игровая площадка",
                                     "спальная комната", "офис"]
    assert notes[0].fields[14:19] == ["y", "", "", "", ""]


def test_missing_distractors_pad_to_empty_strings():
    card = CardData("dojo", "додзё", "She trained in the dojo.", [], [])

    notes = CardGenerator(selected_models=[CardGenerator.RU_EN_TYPING]).create_cards(card)

    assert notes[0].fields[6:14] == [""] * 8


def test_all_models_produce_unified_plus_cloze_notes():
    generator = CardGenerator()

    notes = generator.create_cards(make_card_data())

    assert len(notes) == 2
    assert notes[0].model.model_id == 1712849305
    assert notes[1].model.model_id == 1631442296
    assert notes[0].guid != notes[1].guid


def test_unified_guid_is_stable_across_runs():
    first = CardGenerator(selected_models=[1]).create_cards(make_card_data())
    second = CardGenerator(selected_models=[1, 2, 3]).create_cards(make_card_data())

    assert first[0].guid == second[0].guid
```

Replace `test_example_audio_field_lands_last_on_v2_models` and `test_example_audio_field_empty_without_path`:

```python
def test_example_audio_lands_in_its_frozen_slot():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(
        make_card_data(), example_audio_path="x_example.mp3")

    assert notes[0].fields[5] == "[sound:dojo_5e09bf57_example.mp3]"


def test_example_audio_field_empty_without_path():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(make_card_data())

    assert notes[0].fields[5] == ""
```

Replace `test_sync_names_cover_v2_cloze_and_legacy`:

```python
def test_sync_names_cover_unified_cloze_and_legacy():
    from utils.card_generator import model_names_for_sync
    names = model_names_for_sync()
    assert "EN-RU Vocabulary" in names
    assert "EN-RU Cloze Model" in names
    assert "EN-RU Typing Model v2" in names       # v2, now legacy
    assert "RU-EN Scramble Model v2" in names
    assert "EN-RU Typing Model" in names          # v1 legacy
    assert "RU-EN Scramble Model" in names
```

- [x] **Step 2: Run tests to verify the new ones fail**

Run: `python -m pytest tests/test_card_generator.py -q`
Expected: the replaced/added tests FAIL (create_cards still returns per-model notes); the kept cloze/util tests PASS.

- [x] **Step 3: Rewrite `create_cards` and the module constants**

In `src/utils/card_generator.py`:

Imports — replace the five v2 model imports with the unified one (keep `en_ru_cloze_model`):

```python
from models import en_ru_cloze_model
from models import vocab_model
```

Constants:

```python
ALL_MODELS = [
    vocab_model.model,
    en_ru_cloze_model.model,
]

# Note-type names retired by the v2/v3 migrations; mature cards may still live on them
LEGACY_MODEL_NAMES = [
    "EN-RU Typing Model", "RU-EN Typing Model",
    "EN-RU Choice Model", "RU-EN Choice Model",
    "EN-RU Scramble Model", "RU-EN Scramble Model",
    "EN-RU Typing Model v2", "RU-EN Typing Model v2",
    "EN-RU Choice Model v2", "RU-EN Choice Model v2",
    "RU-EN Scramble Model v2",
]
```

In `CardGenerator`: keep the six numeric constants and `MODEL_NAMES` exactly as they are (the CLI and the interactive menu depend on them). Add one class constant right after `MODEL_NAMES` — its order must mirror `vocab_model.GATE_FIELDS`:

```python
    # Model numbers that live as gates on the unified note, in gate-field order
    VOCAB_MODEL_NUMBERS = (EN_RU_TYPING, RU_EN_TYPING, EN_RU_CHOICE,
                           RU_EN_CHOICE, RU_EN_SCRAMBLE)
```

In `__init__`: delete the six `self.model_* = ...` assignments (nothing else uses them); keep the `selected_models` defaulting logic unchanged.

Replace the whole body of `create_cards` (keep the signature and docstring shape):

```python
    def create_cards(self, card_data: CardData, audio_path: str = None,
                    image_path: str = None,
                    example_audio_path: str = None) -> List[genanki.Note]:
        """
        Create the word's notes: one unified note (5 gated card templates)
        plus an optional cloze note.

        Returns:
            List of created notes (Note objects)
        """
        notes = []

        # Prepare audio and image
        audio_field = f"[sound:{card_data.safe_filename}.mp3]" if audio_path else ""
        image_field = f'<img src="{card_data.safe_filename}.jpg">' if image_path else ""
        example_audio_field = (f"[sound:{card_data.safe_filename}_example.mp3]"
                               if example_audio_path else "")

        try:
            # Unified note: data fields always filled, gates mirror the selection
            if any(m in self.VOCAB_MODEL_NUMBERS for m in self.selected_models):
                incorrect_ru = (card_data.incorrect_ru + [""] * 4)[:4]
                incorrect_en = (card_data.incorrect_en + [""] * 4)[:4]
                gates = [vocab_model.GATE_ON if m in self.selected_models else ""
                         for m in self.VOCAB_MODEL_NUMBERS]
                notes.append(
                    VocabNote(
                        model=vocab_model.model,
                        fields=[card_data.english, card_data.russian, card_data.example,
                                audio_field, image_field, example_audio_field,
                                *incorrect_ru, *incorrect_en, *gates],
                    )
                )

            # EN cloze card: the example with the word hidden
            if self.EN_CLOZE in self.selected_models:
                cloze_text = build_cloze_text(card_data.english, card_data.example)
                if cloze_text is None:
                    logger.warning(f"No exact occurrence of '{card_data.english}' "
                                   "in its example - cloze card skipped")
                else:
                    notes.append(
                        VocabNote(
                            model=en_ru_cloze_model.model,
                            fields=[card_data.english, cloze_text, card_data.russian],
                        )
                    )

            logger.debug(f"Successfully created {len(notes)} note(s) for word: {card_data.english}")
            return notes

        except Exception as e:
            logger.error(f"✗ Error creating flashcards for '{card_data.english}': {e}")
            return []
```

Note the cloze block previously referenced `self.model_en_cloze` — it now uses `en_ru_cloze_model.model` directly.

- [x] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: everything passes, including `tests/test_models_factory.py` (v2 models still exist) and `tests/test_cli.py` / `tests/test_md_loader.py` (untouched surfaces).

- [x] **Step 5: Commit (after owner review)**

```bash
git add src/utils/card_generator.py tests/test_card_generator.py
git commit -m "feat: generate one unified note per word instead of five"
```

---

### Task 3: Retire the v2 models

**Files:**
- Delete: `src/models/en_ru_typing_model.py`, `src/models/ru_en_typing_model.py`, `src/models/en_ru_choice_model.py`, `src/models/ru_en_choice_model.py`, `src/models/ru_en_scramble_model.py`
- Modify: `src/models/factory.py` (retire ids; delete dead factories)
- Delete: `tests/test_models_factory.py` (its v3 replacements live in `tests/test_vocab_model.py` since Task 1)
- Modify: `tests/test_vocab_model.py` (retired-set guard)

**Interfaces:**
- Consumes: nothing new.
- Produces: `RETIRED_MODEL_IDS` covering v1 + v2 ids. Nothing may import the five deleted modules or `make_typing_model`/`make_choice_model`/`TYPING_CSS`/`CHOICE_CSS` afterwards.

- [x] **Step 1: Update the retired-ids guard**

In `tests/test_vocab_model.py`, leave the existing tests unchanged and add:

```python
def test_retired_ids_cover_v1_and_v2_and_are_not_reused():
    assert RETIRED_MODEL_IDS == {
        # v1
        73727116, 4392726, 2343456, 23436536, 234556757,
        # v2
        1298336501, 1354702052, 1427185897, 1495623708, 1563008841,
    }
    assert vocab_model.MODEL_ID not in RETIRED_MODEL_IDS
    assert 1631442296 not in RETIRED_MODEL_IDS  # cloze stays current
```

- [x] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_vocab_model.py::test_retired_ids_cover_v1_and_v2_and_are_not_reused -q`
Expected: FAIL — the set still holds only the five v1 ids.

- [x] **Step 3: Retire ids, delete dead code**

In `src/models/factory.py`:

```python
# v1 and v2 note-type ids, retired by the v2/v3 migrations - never reuse
RETIRED_MODEL_IDS = frozenset({
    # v1
    73727116, 4392726, 2343456, 23436536, 234556757,
    # v2
    1298336501, 1354702052, 1427185897, 1495623708, 1563008841,
})
```

Then delete from `factory.py`: `make_typing_model`, `make_choice_model`, and the `TYPING_CSS` / `CHOICE_CSS` composites (only the deleted factories used them). Update the module docstring to say the factory holds the shared CSS fragments, template sources and the sentinel renderer for `vocab_model`. Keep `CARD_CSS` — `en_ru_cloze_model.py` imports it.

Delete the five v2 model files and the old test file:

```bash
git rm src/models/en_ru_typing_model.py src/models/ru_en_typing_model.py \
       src/models/en_ru_choice_model.py src/models/ru_en_choice_model.py \
       src/models/ru_en_scramble_model.py tests/test_models_factory.py
```

Verify nothing references the deleted names:

```bash
grep -rn "en_ru_typing_model\|ru_en_typing_model\|en_ru_choice_model\|ru_en_choice_model\|ru_en_scramble_model\|make_typing_model\|make_choice_model\|TYPING_CSS\|CHOICE_CSS" src tests
```

Expected matches: none (`CHOICE_WIDGET_CSS` does not match the `CHOICE_CSS` pattern and stays).

- [x] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all PASS.

- [x] **Step 5: Commit (after owner review)**

```bash
git add -A src/models tests
git commit -m "feat: retire the five v2 note types in favor of the unified model"
```

---

### Task 4: Push updates merge instead of overwrite

**Files:**
- Modify: `src/utils/anki_connect.py:103-130` (`push_notes`)
- Modify: `tests/test_anki_connect.py`

**Interfaces:**
- Consumes: existing `client.invoke` contract; new AnkiConnect action used: `notesInfo` (returns `[{"fields": {name: {"value": ...}, ...}, ...}]`).
- Produces: `push_notes(client, notes, deck_name) -> (added, updated)` — same signature, merge semantics on update.

- [x] **Step 1: Update the existing push test and add merge tests**

In `tests/test_anki_connect.py`, replace `test_push_notes_updates_existing_and_adds_missing`:

```python
def test_push_notes_updates_existing_and_adds_missing():
    model = FakeModel("EN-RU Vocabulary")
    existing_note = FakeNote(model, ["dojo", "додзё"])
    new_note = FakeNote(model, ["hinges", "петли"])
    client = FakeClient(results={
        "findNotes": [[101], []],
        "notesInfo": [{"fields": {"English": {"value": "dojo"},
                                  "Russian": {"value": "старое"}}}],
    })

    added, updated = push_notes(client, [existing_note, new_note], "Base::deck")

    assert (added, updated) == (1, 1)
    actions = [c[0] for c in client.calls]
    assert actions == ["findNotes", "notesInfo", "updateNoteFields",
                       "findNotes", "addNote"]
    update_params = client.calls[2][1]
    assert update_params["note"]["id"] == 101
    assert update_params["note"]["fields"] == {"English": "dojo", "Russian": "додзё"}
    add_params = client.calls[4][1]
    assert add_params["note"]["deckName"] == "Base::deck"
    assert add_params["note"]["modelName"] == "EN-RU Vocabulary"
    assert add_params["note"]["fields"]["English"] == "hinges"
```

Add (uses a 4-field fake model, so extend `FakeModel` usage locally instead of changing the class):

```python
def test_push_update_never_degrades_stored_fields():
    model = FakeModel("EN-RU Vocabulary")
    model.fields = [{"name": "English"}, {"name": "Russian"},
                    {"name": "RussianIncorrect1"}, {"name": "EnRuChoice"}]
    # markdown-mode rerun: no distractors, choice gate off
    incoming = FakeNote(model, ["dojo", "додзё-новое", "", ""])
    client = FakeClient(results={
        "findNotes": [[101]],
        "notesInfo": [{"fields": {"English": {"value": "dojo"},
                                  "Russian": {"value": "додзё"},
                                  "RussianIncorrect1": {"value": "храм"},
                                  "EnRuChoice": {"value": "y"}}}],
    })

    added, updated = push_notes(client, [incoming], "Base::deck")

    assert (added, updated) == (0, 1)
    merged = client.calls[2][1]["note"]["fields"]
    assert merged == {"English": "dojo",
                      "Russian": "додзё-новое",      # non-empty incoming wins
                      "RussianIncorrect1": "храм",   # empty incoming keeps stored
                      "EnRuChoice": "y"}             # gates are never cleared


def test_push_add_writes_fields_as_generated():
    model = FakeModel("EN-RU Vocabulary")
    model.fields = [{"name": "English"}, {"name": "Russian"},
                    {"name": "EnRuChoice"}]
    incoming = FakeNote(model, ["dojo", "додзё", ""])
    client = FakeClient(results={"findNotes": [[]]})

    added, updated = push_notes(client, [incoming], "Base::deck")

    assert (added, updated) == (1, 0)
    assert client.calls[1][1]["note"]["fields"] == {"English": "dojo",
                                                    "Russian": "додзё",
                                                    "EnRuChoice": ""}
```

Note on `FakeClient`: its list-of-lists convention pops sequential responses for `findNotes`; the `notesInfo` result above is a plain list of dicts, which `FakeClient` returns whole on every call — exactly what these tests need.

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_anki_connect.py -q`
Expected: the three tests above FAIL (no `notesInfo` call, no merge).

- [x] **Step 3: Implement the merge**

Replace `push_notes` in `src/utils/anki_connect.py`:

```python
def push_notes(client, notes, deck_name: str) -> tuple:
    """Add new notes or merge fields into existing ones. Returns (added, updated).

    A note is matched by its first field + note type - the same identity the
    genanki GUID uses, so .apkg imports and pushes agree on what "same card"
    means. An update never degrades the stored note: an empty incoming value
    keeps the stored one, so a partial rerun (fewer models, markdown mode,
    offline media) cannot clear gates, distractors or media references.
    """
    added = 0
    updated = 0
    for note in notes:
        field_names = [field["name"] for field in note.model.fields]
        fields = dict(zip(field_names, note.fields))
        word = note.fields[0].replace('"', '\\"')
        query = f'"note:{note.model.name}" "{field_names[0]}:{word}"'
        found = client.invoke("findNotes", query=query)
        if found:
            info = client.invoke("notesInfo", notes=[found[0]]) or []
            stored = {name: value.get("value", "")
                      for name, value in (info[0].get("fields", {}) if info else {}).items()}
            merged = {name: value if value else stored.get(name, "")
                      for name, value in fields.items()}
            client.invoke("updateNoteFields", note={"id": found[0], "fields": merged})
            updated += 1
        else:
            client.invoke("addNote", note={
                "deckName": deck_name,
                "modelName": note.model.name,
                "fields": fields,
                "options": {"allowDuplicate": False},
            })
            added += 1
    return added, updated
```

- [x] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all PASS.

- [x] **Step 5: Commit (after owner review)**

```bash
git add src/utils/anki_connect.py tests/test_anki_connect.py
git commit -m "feat: push updates merge fields and never degrade a stored note"
```

---

### Task 5: Documentation

**Files:**
- Modify: `.claude/CLAUDE.md` (frozen invariants + architecture blurbs)
- Modify: `README.md` (note-type description, migration note)

**Interfaces:** none — docs only.

- [x] **Step 1: Update `.claude/CLAUDE.md`**

Replace the **Model IDs and field lists** bullet under "Frozen invariants" with:

```markdown
- **Model IDs and field lists** in `src/models/` are frozen and guarded by
  `tests/test_vocab_model.py`. Never renumber models or add/remove/reorder
  fields of an existing model. Current (v3) ids: unified vocabulary
  1712849305 (19 fields: 6 data, 8 distractors, then 5 gate fields whose
  non-empty value means "this card exists"), cloze 1631442296. Retired ids
  (v1: 73727116, 4392726, 2343456, 23436536, 234556757; v2: 1298336501,
  1354702052, 1427185897, 1495623708, 1563008841) must never be reused
  (`RETIRED_MODEL_IDS` in `models/factory.py`).
```

In the Architecture section, adjust the pipeline sentence: `notes (utils/card_generator.py, 6 models)` becomes `notes (utils/card_generator.py, one unified note per word + optional cloze)`. Replace the paragraph about the factory ("The four typing/choice models are generated by `src/models/factory.py`...") with:

```markdown
The unified vocabulary model (5 gated card templates) is assembled in
`src/models/vocab_model.py` from template sources in `src/models/factory.py`;
card existence per note is controlled by the 5 gate fields, which mirror the
`--models` selection. `en_ru_cloze_model.py` stays a separate note type.
```

Append to the push bullet in "Non-obvious design decisions" (after "preserving scheduling."):

```markdown
  Push updates are merges: an empty incoming field never overwrites a stored
  value, so gates, distractors and media survive partial reruns; `.apkg` is
  the initial-import path, push is the update path.
```

- [x] **Step 2: Update `README.md`**

Find the note-types / v2 migration section (search for `Old decks keep working on the` around line 377) and rework it to describe v3: one `EN-RU Vocabulary` note type with five card templates gated per word, plus the separate cloze note type; the v2/v1 note types are retired but their mature cards still feed the known-words ledger until the owner deletes the old decks. Also state the migration step order for existing collections: run the generator once with Anki open (so mature words land in the ledger), then delete the old decks and note types manually. Keep the "6 card types" feature list as is — the six card *types* still exist, they just live on two note types now.

- [x] **Step 3: Verify docs**

Run: `python -m pytest -q` (nothing should break) and re-read both diffs for stray Russian text or stale v2 references:

```bash
git diff -- .claude/CLAUDE.md README.md
grep -n "Model v2\|make_typing_model\|make_choice_model" .claude/CLAUDE.md README.md
```

Expected grep hits: only intentional mentions of retired v2 names in the migration note (if any).

- [x] **Step 4: Commit (after owner review)**

```bash
git add .claude/CLAUDE.md README.md
git commit -m "docs: describe the unified note type and the v3 migration"
```

---

### Task 6: End-to-end verification

**Files:** none created (throwaway artifacts under `results/` and a scratch script).

- [x] **Step 1: Full test suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [x] **Step 2: Build a real package offline**

```bash
cd src && python anki_generator.py --csv cards.example.csv --models all --offline
```

Expected: exit code 0, `results/cards.example.apkg` written.

- [x] **Step 3: Inspect the package**

Run this snippet (adjust the word count to `cards.example.csv`, which has N data rows):

```python
import sqlite3, tempfile, zipfile, pathlib
apkg = pathlib.Path("results/cards.example.apkg")
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(apkg).extractall(tmp)
    db = next(p for p in ("collection.anki21", "collection.anki2")
              if (pathlib.Path(tmp) / p).exists())
    con = sqlite3.connect(pathlib.Path(tmp) / db)
    notes = con.execute("SELECT count(*) FROM notes").fetchone()[0]
    cards = con.execute("SELECT count(*) FROM cards").fetchone()[0]
    print(f"notes={notes} cards={cards}")
```

Expected for N words that all contain their word in the example: `notes == 2*N` (unified + cloze) and `cards == 6*N` (5 gated + 1 cloze). Words whose example lacks the exact word produce one note less (cloze skipped) — cross-check against the run's warnings.

- [x] **Step 4: Owner's manual check (hand over, do not automate)**

Ask the owner to: import `results/cards.example.apkg` into Anki (or run with `--push` against a live Anki), confirm a word shows five cards visually identical to v2, no gate values visible on any card, the Browse editor lists the 19 fields with distractors/gates collapsed (or note that the `collapsed` flag did not survive — the documented fallback is a one-time manual "Collapse by default" setup), and the Scramble and Choice cards keep their v2 input-field styling.

- [x] **Step 5: Report results**

Report pytest, package-inspection numbers and any deviations to the owner. No commit in this task.
