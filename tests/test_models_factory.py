from models import (
    en_ru_choice_model,
    en_ru_typing_model,
    ru_en_choice_model,
    ru_en_scramble_model,
    ru_en_typing_model,
)

BASE_FIELDS = ["English", "Russian", "Example", "Audio", "Image"]


def field_names(model):
    return [field["name"] for field in model.fields]


def test_model_ids_and_fields_are_frozen():
    assert en_ru_typing_model.model.model_id == 73727116
    assert ru_en_typing_model.model.model_id == 4392726
    assert en_ru_choice_model.model.model_id == 2343456
    assert ru_en_choice_model.model.model_id == 23436536
    assert ru_en_scramble_model.model.model_id == 234556757

    assert field_names(en_ru_typing_model.model) == BASE_FIELDS
    assert field_names(ru_en_typing_model.model) == BASE_FIELDS
    assert field_names(ru_en_scramble_model.model) == BASE_FIELDS
    assert field_names(en_ru_choice_model.model) == [
        "English", "Russian", "Example", "Audio",
        "RussianIncorrect1", "RussianIncorrect2",
        "RussianIncorrect3", "RussianIncorrect4", "Image"]
    assert field_names(ru_en_choice_model.model) == [
        "English", "Russian", "Example", "Audio",
        "EnglishIncorrect1", "EnglishIncorrect2",
        "EnglishIncorrect3", "EnglishIncorrect4", "Image"]


def test_model_and_template_names():
    assert en_ru_typing_model.model.name == "EN-RU Typing Model"
    assert ru_en_typing_model.model.name == "RU-EN Typing Model"
    assert en_ru_choice_model.model.name == "EN-RU Choice Model"
    assert ru_en_choice_model.model.name == "RU-EN Choice Model"
    assert ru_en_scramble_model.model.name == "RU-EN Scramble Model"
    assert en_ru_choice_model.model.templates[0]["name"] == "EN-RU Choice"
    assert ru_en_scramble_model.model.templates[0]["name"] == "RU-EN Scramble"


def test_audio_placement_semantics():
    # Typing: audio always on the front; only EN-RU repeats it on the back
    assert "{{Audio}}" in en_ru_typing_model.model.templates[0]["qfmt"]
    assert "{{Audio}}" in ru_en_typing_model.model.templates[0]["qfmt"]
    assert "{{Audio}}" in en_ru_typing_model.model.templates[0]["afmt"]
    assert "{{Audio}}" not in ru_en_typing_model.model.templates[0]["afmt"]

    # Choice: RU-EN keeps English audio off the front (it would give the answer away)
    assert "{{Audio}}" in en_ru_choice_model.model.templates[0]["qfmt"]
    assert "{{Audio}}" not in ru_en_choice_model.model.templates[0]["qfmt"]
    ru_en_afmt = ru_en_choice_model.model.templates[0]["afmt"]
    assert ru_en_afmt.index("<hr id=answer>") < ru_en_afmt.index("{{Audio}}")


def test_choice_buttons_use_direction_specific_distractors():
    en_ru_qfmt = en_ru_choice_model.model.templates[0]["qfmt"]
    ru_en_qfmt = ru_en_choice_model.model.templates[0]["qfmt"]
    for i in range(1, 5):
        assert f"{{{{RussianIncorrect{i}}}}}" in en_ru_qfmt
        assert f"{{{{EnglishIncorrect{i}}}}}" in ru_en_qfmt
    assert 'data-answer="{{Russian}}"' in en_ru_qfmt
    assert 'data-answer="{{English}}"' in ru_en_qfmt


def test_prompt_and_answer_are_mirrored():
    assert "{{type:Russian}}" in en_ru_typing_model.model.templates[0]["qfmt"]
    assert "{{type:English}}" in ru_en_typing_model.model.templates[0]["qfmt"]
    assert "<h2>{{English}}</h2>" in en_ru_choice_model.model.templates[0]["qfmt"]
    assert "<h2>{{Russian}}</h2>" in ru_en_choice_model.model.templates[0]["qfmt"]
