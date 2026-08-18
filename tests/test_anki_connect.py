import base64

import pytest
import requests

from utils.anki_connect import (
    AnkiConnectClient,
    AnkiConnectError,
    AnkiNotAvailableError,
    ensure_deck,
    ensure_models,
    fetch_mature_words,
    push_notes,
    store_media,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    """Records posts and replies from a canned {action: result} map."""

    def __init__(self, results=None, error=None):
        self.results = results or {}
        self.error = error
        self.requests = []

    def post(self, url, json=None, timeout=None):
        self.requests.append(json)
        if self.error is not None:
            raise self.error
        return FakeResponse({"result": self.results.get(json["action"]), "error": None})


class FakeClient:
    """Stub for the high-level helpers: canned results per action, call log."""

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def invoke(self, action, **params):
        self.calls.append((action, params))
        result = self.results.get(action)
        # A list of lists means sequential per-call responses; anything else is returned whole
        if isinstance(result, list) and result and all(isinstance(item, list) for item in result):
            return result.pop(0)
        return result


class FakeModel:
    def __init__(self, name):
        self.name = name
        self.fields = [{"name": "English"}, {"name": "Russian"}]
        self.templates = [{"name": f"{name} T", "qfmt": "Q {{English}}", "afmt": "A {{Russian}}"}]
        self.css = ".card {}"


class FakeNote:
    def __init__(self, model, fields):
        self.model = model
        self.fields = fields


def test_invoke_posts_protocol_and_returns_result():
    session = FakeSession(results={"version": 6})
    client = AnkiConnectClient(url="http://test:1", session=session)

    assert client.invoke("version") == 6
    assert session.requests == [{"action": "version", "version": 6, "params": {}}]


def test_invoke_raises_on_api_error():
    session = FakeSession()
    session.post = lambda url, json=None, timeout=None: FakeResponse(
        {"result": None, "error": "deck was not found"})
    client = AnkiConnectClient(session=session)

    with pytest.raises(AnkiConnectError, match="deck was not found"):
        client.invoke("createDeck", deck="X")


def test_invoke_raises_not_available_when_anki_is_down():
    session = FakeSession(error=requests.ConnectionError("refused"))
    client = AnkiConnectClient(session=session)

    with pytest.raises(AnkiNotAvailableError, match="not reachable"):
        client.invoke("version")


def test_ensure_deck_creates_deck():
    client = FakeClient()

    ensure_deck(client, "Base::chapter")

    assert client.calls == [("createDeck", {"deck": "Base::chapter"})]


def test_ensure_models_creates_only_missing_models():
    existing = FakeModel("Existing Model")
    missing = FakeModel("Missing Model")
    client = FakeClient(results={"modelNames": ["Existing Model"]})

    created = ensure_models(client, [existing, missing])

    assert created == ["Missing Model"]
    create_calls = [c for c in client.calls if c[0] == "createModel"]
    assert len(create_calls) == 1
    params = create_calls[0][1]
    assert params["modelName"] == "Missing Model"
    assert params["inOrderFields"] == ["English", "Russian"]
    assert params["cardTemplates"] == [{"Name": "Missing Model T", "Front": "Q {{English}}", "Back": "A {{Russian}}"}]


def test_store_media_skips_existing_without_overwrite(tmp_path):
    media = tmp_path / "dojo.mp3"
    media.write_bytes(b"ID3data")
    client = FakeClient(results={"retrieveMediaFile": "already-there"})

    stored, skipped = store_media(client, [str(media)], overwrite=False)

    assert (stored, skipped) == (0, 1)
    assert [c[0] for c in client.calls] == ["retrieveMediaFile"]


def test_store_media_overwrites_when_requested(tmp_path):
    media = tmp_path / "dojo.mp3"
    media.write_bytes(b"ID3data")
    client = FakeClient()

    stored, skipped = store_media(client, [str(media)], overwrite=True)

    assert (stored, skipped) == (1, 0)
    action, params = client.calls[0]
    assert action == "storeMediaFile"
    assert params["filename"] == "dojo.mp3"
    assert params["data"] == base64.b64encode(b"ID3data").decode()


def test_push_notes_updates_existing_and_adds_missing():
    model = FakeModel("EN-RU Typing Model")
    existing_note = FakeNote(model, ["dojo", "додзё"])
    new_note = FakeNote(model, ["hinges", "петли"])
    client = FakeClient(results={"findNotes": [[101], []]})

    added, updated = push_notes(client, [existing_note, new_note], "Base::deck")

    assert (added, updated) == (1, 1)
    actions = [c[0] for c in client.calls]
    assert actions == ["findNotes", "updateNoteFields", "findNotes", "addNote"]
    update_params = client.calls[1][1]
    assert update_params["note"]["id"] == 101
    assert update_params["note"]["fields"] == {"English": "dojo", "Russian": "додзё"}
    add_params = client.calls[3][1]
    assert add_params["note"]["deckName"] == "Base::deck"
    assert add_params["note"]["modelName"] == "EN-RU Typing Model"
    assert add_params["note"]["fields"]["English"] == "hinges"


def test_fetch_mature_words_collects_first_fields():
    client = FakeClient(results={
        "findCards": [[1, 2], []],
        "cardsInfo": [
            {"fields": {"English": {"value": "dojo"}, "Russian": {"value": "додзё"}}},
            {"fields": {"English": {"value": "dojo"}, "Russian": {"value": "додзё"}}},
        ],
    })

    words = fetch_mature_words(client, ["EN-RU Typing Model", "RU-EN Typing Model"])

    assert words == {"dojo"}
    first_query = client.calls[0][1]["query"]
    assert "EN-RU Typing Model" in first_query and "prop:ivl>=21" in first_query


def test_trigger_sync_returns_true_on_success():
    from utils.anki_connect import trigger_sync

    assert trigger_sync(FakeClient()) is True


def test_trigger_sync_returns_false_on_api_error():
    from utils.anki_connect import trigger_sync

    class FailingClient:
        def invoke(self, action, **params):
            raise AnkiConnectError("sync failed")

    assert trigger_sync(FailingClient()) is False


def test_ensure_models_marks_cloze_models():
    from models import en_ru_cloze_model
    client = FakeClient(results={"modelNames": []})

    ensure_models(client, [en_ru_cloze_model.model])

    params = [c for c in client.calls if c[0] == "createModel"][0][1]
    assert params["isCloze"] is True


def test_ensure_models_marks_standard_models_as_non_cloze():
    client = FakeClient(results={"modelNames": []})

    ensure_models(client, [FakeModel("Missing Model")])

    params = [c for c in client.calls if c[0] == "createModel"][0][1]
    assert params["isCloze"] is False
