import genanki

from models import en_ru_cloze_model
from models.factory import RETIRED_MODEL_IDS


def test_model_id_and_name_are_frozen_and_not_retired():
    assert en_ru_cloze_model.model.model_id == 1795263408
    assert en_ru_cloze_model.model.name == "EN-RU Cloze"
    assert en_ru_cloze_model.model.model_id not in RETIRED_MODEL_IDS


def test_the_previous_cloze_id_is_retired():
    assert 1631442296 in RETIRED_MODEL_IDS


def test_field_order_puts_english_first_and_audio_last():
    names = [field["name"] for field in en_ru_cloze_model.model.fields]

    assert names == ["English", "Text", "Hint", "ExampleAudio"]


def test_both_sides_carry_the_typing_input():
    template = en_ru_cloze_model.model.templates[0]

    assert "{{type:cloze:Text}}" in template["qfmt"]
    assert "{{type:cloze:Text}}" in template["afmt"]


def test_example_audio_plays_on_the_back_only():
    template = en_ru_cloze_model.model.templates[0]

    assert "{{ExampleAudio}}" in template["afmt"]
    assert "{{ExampleAudio}}" not in template["qfmt"]


def test_hint_is_collapsible_on_the_front_and_open_on_the_back():
    template = en_ru_cloze_model.model.templates[0]

    assert "{{hint:Hint}}" in template["qfmt"]
    assert "{{Hint}}" in template["afmt"]


def test_model_stays_a_cloze_type():
    assert en_ru_cloze_model.model.model_type == genanki.Model.CLOZE
