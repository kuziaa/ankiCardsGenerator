from anki_generator import derive_deck_id
from utils.card_generator import CardData, CardGenerator, safe_media_name


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
