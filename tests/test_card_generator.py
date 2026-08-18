from anki_generator import derive_deck_id
from utils.card_generator import CardData, CardGenerator, build_cloze_text, safe_media_name


def make_card_data():
    return CardData(
        english="dojo",
        russian="додзё",
        example="She trained in the dojo.",
        incorrect_en=["mojo", "doge", "dose", "doze"],
        incorrect_ru=["зал ожидания", "игровая площадка", "спальная комната", "офис"],
    )


def test_safe_media_name_is_deterministic_and_ascii():
    assert safe_media_name("dojo") == "dojo_5e09bf57"
    assert safe_media_name("выступ") == "445ceb7c"


def test_derive_deck_id_is_stable_per_csv_name():
    assert derive_deck_id("cards.example") == derive_deck_id("cards.example")
    assert derive_deck_id("cards.example") != derive_deck_id("another.deck")


def test_create_cards_respects_selected_models_and_unique_guids():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING, CardGenerator.RU_EN_SCRAMBLE])

    notes = generator.create_cards(make_card_data(), audio_path="dojo.mp3", image_path="dojo.jpg")

    assert len(notes) == 2
    assert len({note.guid for note in notes}) == 2
    assert all("[sound:dojo_5e09bf57.mp3]" in note.fields for note in notes)
    assert all('<img src="dojo_5e09bf57.jpg">' in note.fields for note in notes)


def test_choice_card_uses_russian_distractors_for_en_ru_choice():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_CHOICE])

    notes = generator.create_cards(make_card_data())

    assert len(notes) == 1
    assert notes[0].fields[4:8] == ["зал ожидания", "игровая площадка", "спальная комната", "офис"]


def test_build_cloze_text_wraps_first_occurrence_case_insensitive():
    assert build_cloze_text("dojo", "She trained in the Dojo daily.") ==         "She trained in the {{c1::Dojo}} daily."


def test_build_cloze_text_handles_multiword_expressions():
    assert build_cloze_text("rolled over", "The ship rolled over slowly.") ==         "The ship {{c1::rolled over}} slowly."


def test_build_cloze_text_wraps_only_the_first_occurrence():
    assert build_cloze_text("dojo", "dojo here, dojo there") ==         "{{c1::dojo}} here, dojo there"


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


def test_example_audio_field_lands_last_on_v2_models():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING,
                                               CardGenerator.EN_RU_CHOICE])

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
