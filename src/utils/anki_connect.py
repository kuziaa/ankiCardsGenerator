"""Thin AnkiConnect client and push helpers.

AnkiConnect is an Anki add-on exposing a JSON API on localhost while the
desktop app is running. Everything here is best-effort friendly: a dead or
missing Anki raises AnkiNotAvailableError with an actionable message.
"""

import base64
from pathlib import Path

import requests

from utils.logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_URL = "http://127.0.0.1:8765"
API_VERSION = 6
# Anki calls a card "mature" once its interval reaches 21 days
MATURE_INTERVAL_DAYS = 21
REQUEST_TIMEOUT = (3, 30)


class AnkiConnectError(Exception):
    """AnkiConnect responded with an error."""


class AnkiNotAvailableError(AnkiConnectError):
    """Anki is not running or the AnkiConnect add-on is not installed."""


class AnkiConnectClient:
    def __init__(self, url: str = DEFAULT_URL, session=None):
        self.url = url
        self.session = session or requests.Session()

    def invoke(self, action: str, **params):
        payload = {"action": action, "version": API_VERSION, "params": params}
        try:
            response = self.session.post(self.url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            raise AnkiNotAvailableError(
                f"Anki is not reachable at {self.url} "
                f"({type(e).__name__})") from e
        result = response.json()
        if result.get("error"):
            raise AnkiConnectError(result["error"])
        return result.get("result")


def ensure_deck(client, deck_name: str) -> None:
    """Create the deck if missing (createDeck is idempotent)."""
    client.invoke("createDeck", deck=deck_name)


def ensure_models(client, models) -> list:
    """Create note types that do not exist in the collection yet.

    AnkiConnect matches models by NAME, not by genanki model id.
    Returns the list of created model names.
    """
    existing = set(client.invoke("modelNames") or [])
    created = []
    for model in models:
        if model.name in existing:
            continue
        client.invoke(
            "createModel",
            modelName=model.name,
            inOrderFields=[field["name"] for field in model.fields],
            css=model.css,
            cardTemplates=[
                {"Name": template["name"], "Front": template["qfmt"], "Back": template["afmt"]}
                for template in model.templates
            ],
        )
        created.append(model.name)
    return created


def store_media(client, media_paths, overwrite: bool = False) -> tuple:
    """Upload media files. Returns (stored, skipped) counts.

    Without overwrite, files already present in the collection are kept.
    """
    stored = 0
    skipped = 0
    for media_path in media_paths:
        path = Path(media_path)
        if not overwrite and client.invoke("retrieveMediaFile", filename=path.name):
            skipped += 1
            continue
        data = base64.b64encode(path.read_bytes()).decode()
        client.invoke("storeMediaFile", filename=path.name, data=data)
        stored += 1
    return stored, skipped


def push_notes(client, notes, deck_name: str) -> tuple:
    """Add new notes or update fields of existing ones. Returns (added, updated).

    A note is matched by its first field + note type - the same identity the
    genanki GUID uses, so .apkg imports and pushes agree on what "same card"
    means. Updating fields keeps the scheduling history intact.
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
            client.invoke("updateNoteFields", note={"id": found[0], "fields": fields})
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


def trigger_sync(client) -> bool:
    """Kick off AnkiWeb sync. Returns False instead of raising on API errors."""
    try:
        client.invoke("sync")
        return True
    except AnkiConnectError as e:
        logger.debug(f"AnkiWeb sync failed: {e}")
        return False


def fetch_mature_words(client, model_names, min_interval: int = MATURE_INTERVAL_DAYS) -> set:
    """Collect English words whose cards are mature (interval >= min_interval)."""
    words = set()
    for model_name in model_names:
        query = f'"note:{model_name}" prop:ivl>={min_interval}'
        card_ids = client.invoke("findCards", query=query)
        if not card_ids:
            continue
        for info in client.invoke("cardsInfo", cards=card_ids) or []:
            english = info.get("fields", {}).get("English", {}).get("value", "").strip()
            if english:
                words.add(english)
    return words
