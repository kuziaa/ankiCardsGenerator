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


def test_retired_ids_cover_v1_and_v2_and_are_not_reused():
    assert RETIRED_MODEL_IDS == {
        # v1
        73727116, 4392726, 2343456, 23436536, 234556757,
        # v2
        1298336501, 1354702052, 1427185897, 1495623708, 1563008841,
    }
    assert vocab_model.MODEL_ID not in RETIRED_MODEL_IDS
    assert 1631442296 not in RETIRED_MODEL_IDS  # cloze stays current


def test_service_fields_carry_editor_hints():
    by_name = {field["name"]: field for field in vocab_model.model.fields}
    for name in DISTRACTOR_FIELDS + GATE_FIELDS:
        assert by_name[name].get("collapsed") is True
        assert by_name[name].get("description")
    for name in DATA_FIELDS:
        assert "collapsed" not in by_name[name]
