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


def test_create_cards_returns_one_unified_note_with_gated_cards():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING,
                                               CardGenerator.RU_EN_SCRAMBLE])

    notes = generator.create_cards(make_card_data(), audio_path="dojo.mp3",
                                   image_path="dojo.jpg")

    assert len(notes) == 1
    note = notes[0]
    assert note.model.model_id == 1868432571
    # EN-RU Typing is the last template now, scramble the middle one
    assert sorted(card.ord for card in note.cards) == [2, 4]
    assert note.fields[3] == "[sound:dojo_5e09bf57.mp3]"
    assert note.fields[4] == '<img src="dojo_5e09bf57.jpg">'
    assert note.fields[14:19] == ["y", "", "", "", "y"]


def test_unified_note_carries_both_distractor_sets():
    generator = CardGenerator(selected_models=[CardGenerator.EN_RU_CHOICE])

    notes = generator.create_cards(make_card_data())

    assert len(notes) == 1
    assert notes[0].fields[6:10] == ["зал ожидания", "игровая площадка",
                                     "спальная комната", "офис"]
    assert notes[0].fields[10:14] == ["mojo", "doge", "dose", "doze"]
    assert sorted(card.ord for card in notes[0].cards) == [0]


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
    assert notes[0].model.model_id == 1868432571
    assert notes[1].model.model_id == 1795263408
    assert notes[0].guid != notes[1].guid


def test_cloze_note_carries_the_example_audio():
    generator = CardGenerator(selected_models=[6])

    notes = generator.create_cards(make_card_data(), example_audio_path="dojo_example.mp3")

    assert notes[0].fields[3] == "[sound:%s_example.mp3]" % safe_media_name("dojo")


def test_cloze_note_leaves_the_audio_field_empty_without_audio():
    generator = CardGenerator(selected_models=[6])

    notes = generator.create_cards(make_card_data())

    assert notes[0].fields[3] == ""


def test_unified_guid_is_stable_across_runs():
    first = CardGenerator(selected_models=[1]).create_cards(make_card_data())
    second = CardGenerator(selected_models=[1, 2, 3]).create_cards(make_card_data())

    assert first[0].guid == second[0].guid


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
    assert notes[0].model.model_id == 1795263408
    assert notes[0].fields == ["dojo", "She trained in the {{c1::dojo}}.", "додзё", ""]


def test_cloze_note_skipped_when_word_not_in_example():
    card = CardData("sport", "спорт", "One moon sported five thousand.", [], [])

    notes = CardGenerator(selected_models=[CardGenerator.EN_CLOZE]).create_cards(card)

    assert notes == []


def test_example_audio_lands_in_its_frozen_slot():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(
        make_card_data(), example_audio_path="x_example.mp3")

    assert notes[0].fields[5] == "[sound:dojo_5e09bf57_example.mp3]"


def test_cloze_note_plays_the_example_audio_after_the_answer():
    generator = CardGenerator(selected_models=[CardGenerator.EN_CLOZE])

    notes = generator.create_cards(make_card_data(), example_audio_path="x_example.mp3")

    assert len(notes[0].fields) == 4
    assert notes[0].fields[3].startswith("[sound:")


def test_example_audio_field_empty_without_path():
    notes = CardGenerator(selected_models=[CardGenerator.EN_RU_TYPING]).create_cards(make_card_data())

    assert notes[0].fields[5] == ""


def test_sync_names_cover_unified_cloze_and_legacy():
    from utils.card_generator import model_names_for_sync
    names = model_names_for_sync()
    assert "EN-RU Vocabulary" in names
    assert "EN-RU Cloze Model" in names
    assert "EN-RU Typing Model v2" in names       # v2, now legacy
    assert "RU-EN Scramble Model v2" in names
    assert "EN-RU Typing Model" in names          # v1 legacy
    assert "RU-EN Scramble Model" in names
