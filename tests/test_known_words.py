from utils.card_generator import CardData
from utils.known_words import filter_known_words, load_known_words, record_known_words, record_word_list


def make_card(english):
    return CardData(english, "перевод", "Example.", [], [])


def test_missing_ledger_loads_empty(tmp_path):
    assert load_known_words(tmp_path / "known_words.json") == {}


def test_corrupt_ledger_is_ignored(tmp_path):
    path = tmp_path / "known_words.json"
    path.write_text("not json", encoding="utf-8")

    assert load_known_words(path) == {}


def test_record_and_load_roundtrip(tmp_path):
    path = tmp_path / "known_words.json"

    added = record_known_words(path, [make_card("dojo"), make_card("hinges")], "prologue")

    assert added == 2
    ledger = load_known_words(path)
    assert ledger["dojo"]["word"] == "dojo"
    assert ledger["dojo"]["source"] == "prologue"
    assert set(ledger) == {"dojo", "hinges"}


def test_words_from_other_sources_are_skipped(tmp_path):
    path = tmp_path / "known_words.json"
    record_known_words(path, [make_card("dojo")], "prologue")
    ledger = load_known_words(path)

    kept, skipped = filter_known_words(
        [make_card("Dojo"), make_card("hinges")], ledger, "chapter-1")

    assert [card.english for card in kept] == ["hinges"]
    assert skipped == ["Dojo"]


def test_same_source_words_are_kept_on_regeneration(tmp_path):
    path = tmp_path / "known_words.json"
    record_known_words(path, [make_card("dojo")], "prologue")
    ledger = load_known_words(path)

    kept, skipped = filter_known_words([make_card("dojo")], ledger, "prologue")

    assert len(kept) == 1
    assert skipped == []


def test_recording_does_not_reassign_source(tmp_path):
    path = tmp_path / "known_words.json"
    record_known_words(path, [make_card("dojo")], "prologue")

    added = record_known_words(path, [make_card("dojo")], "chapter-1")

    assert added == 0
    assert load_known_words(path)["dojo"]["source"] == "prologue"


def test_record_word_list_adds_words_with_source(tmp_path):
    path = tmp_path / "known_words.json"

    added = record_word_list(path, ["dojo", "hinges"], "anki")

    assert added == 2
    assert load_known_words(path)["dojo"]["source"] == "anki"


def test_record_word_list_keeps_existing_source(tmp_path):
    path = tmp_path / "known_words.json"
    record_known_words(path, [make_card("dojo")], "prologue")

    added = record_word_list(path, ["dojo"], "anki")

    assert added == 0
    assert load_known_words(path)["dojo"]["source"] == "prologue"
