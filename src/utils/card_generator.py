import genanki
import hashlib
import re
import unicodedata
from typing import List, Tuple
from models import en_ru_typing_model
from models import ru_en_typing_model
from models import en_ru_choice_model
from models import ru_en_choice_model
from models import ru_en_scramble_model
from models import en_ru_cloze_model
from utils.logger import setup_logger

logger = setup_logger(__name__)

ALL_MODELS = [
    en_ru_typing_model.model,
    ru_en_typing_model.model,
    en_ru_choice_model.model,
    ru_en_choice_model.model,
    ru_en_scramble_model.model,
    en_ru_cloze_model.model,
]

# Note-type names retired by the v2 migration; mature cards may still live on them
LEGACY_MODEL_NAMES = [
    "EN-RU Typing Model", "RU-EN Typing Model",
    "EN-RU Choice Model", "RU-EN Choice Model",
    "EN-RU Scramble Model", "RU-EN Scramble Model",
]


def model_names_for_sync() -> list:
    """Model names to scan for mature words: current types plus retired v1 names."""
    return [model.name for model in ALL_MODELS] + LEGACY_MODEL_NAMES


def build_cloze_text(word: str, example: str):
    """Wrap the first whole-word, case-insensitive occurrence of word in {{c1::...}}."""
    if not example:
        return None
    match = re.search(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])",
                      example, re.IGNORECASE)
    if match is None:
        return None
    return f"{example[:match.start()]}{{{{c1::{match.group(0)}}}}}{example[match.end():]}"


def safe_media_name(text: str) -> str:
    """Deterministic filesystem-safe media name: ASCII slug + short hash suffix."""
    slug = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_").lower()[:40]
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{slug}_{digest}" if slug else digest


class VocabNote(genanki.Note):
    """Note identified by word + model instead of the full field set.

    Keeps scheduling history on re-import after edits and prevents GUID
    collisions between models that share the same field list.
    """

    @property
    def guid(self):
        return genanki.guid_for(self.fields[0], str(self.model.model_id))


class CardData:
    """Class for storing data of one flashcard."""
    
    def __init__(self, english: str, russian: str, example: str,
                 incorrect_en: List[str], incorrect_ru: List[str]):
        self.english = english
        self.russian = russian
        self.example = example
        self.incorrect_en = incorrect_en
        self.incorrect_ru = incorrect_ru
        self.safe_filename = safe_media_name(english)


class CardGenerator:
    """Class for generating Anki flashcards of various types."""
    
    # Model type constants
    EN_RU_TYPING = 1
    RU_EN_TYPING = 2
    EN_RU_CHOICE = 3
    RU_EN_CHOICE = 4
    RU_EN_SCRAMBLE = 5
    EN_CLOZE = 6
    
    # Mapping of model numbers to names
    MODEL_NAMES = {
        EN_RU_TYPING: "EN→RU Typing",
        RU_EN_TYPING: "RU→EN Typing",
        EN_RU_CHOICE: "EN→RU Choice",
        RU_EN_CHOICE: "RU→EN Choice",
        RU_EN_SCRAMBLE: "RU→EN Scramble",
        EN_CLOZE: "EN-RU Cloze",
    }
    
    def __init__(self, selected_models: list = None):
        """
        Initialize card generator with models.
        
        Args:
            selected_models: List of model numbers to use (1-5). If None, all models are used.
        """
        self.model_en_ru_typing = en_ru_typing_model.model
        self.model_ru_en_typing = ru_en_typing_model.model
        self.model_en_ru_choice = en_ru_choice_model.model
        self.model_ru_en_choice = ru_en_choice_model.model
        self.model_ru_en_scramble = ru_en_scramble_model.model
        self.model_en_cloze = en_ru_cloze_model.model
        
        # Use all models if not specified
        if selected_models is None:
            self.selected_models = [self.EN_RU_TYPING, self.RU_EN_TYPING, 
                                   self.EN_RU_CHOICE, self.RU_EN_CHOICE, 
                                   self.RU_EN_SCRAMBLE, self.EN_CLOZE]
        else:
            self.selected_models = selected_models
    
    def create_cards(self, card_data: CardData, audio_path: str = None,
                    image_path: str = None,
                    example_audio_path: str = None) -> List[genanki.Note]:
        """
        Create a set of flashcards for one word based on selected models.
        
        Args:
            card_data: Object with flashcard data
            audio_path: Path to audio file (can be None)
            image_path: Path to image (can be None)
            
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
            # EN → RU typing card
            if self.EN_RU_TYPING in self.selected_models:
                notes.append(
                    VocabNote(
                        model=self.model_en_ru_typing,
                        fields=[card_data.english, card_data.russian, card_data.example,
                               audio_field, image_field, example_audio_field],
                    )
                )
            
            # RU → EN typing card
            if self.RU_EN_TYPING in self.selected_models:
                notes.append(
                    VocabNote(
                        model=self.model_ru_en_typing,
                        fields=[card_data.english, card_data.russian, card_data.example,
                               audio_field, image_field, example_audio_field],
                    )
                )
            
            # EN → RU choice card
            if self.EN_RU_CHOICE in self.selected_models:
                notes.append(
                    VocabNote(
                        model=self.model_en_ru_choice,
                        fields=[card_data.english, card_data.russian, card_data.example,
                               audio_field] + card_data.incorrect_ru + [image_field, example_audio_field],
                    )
                )
            
            # RU → EN choice card
            if self.RU_EN_CHOICE in self.selected_models:
                notes.append(
                    VocabNote(
                        model=self.model_ru_en_choice,
                        fields=[card_data.english, card_data.russian, card_data.example,
                               audio_field] + card_data.incorrect_en + [image_field, example_audio_field],
                    )
                )
            
            # RU → EN scramble card
            if self.RU_EN_SCRAMBLE in self.selected_models:
                notes.append(
                    VocabNote(
                        model=self.model_ru_en_scramble,
                        fields=[card_data.english, card_data.russian, card_data.example,
                               audio_field, image_field, example_audio_field],
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
                            model=self.model_en_cloze,
                            fields=[card_data.english, cloze_text, card_data.russian],
                        )
                    )
            
            logger.debug(f"Successfully created {len(notes)} flashcards for word: {card_data.english}")
            return notes
            
        except Exception as e:
            logger.error(f"✗ Error creating flashcards for '{card_data.english}': {e}")
            return []


def create_deck_from_cards(cards: List[genanki.Note], deck_id: int,
                          deck_name: str) -> genanki.Deck:
    """
    Create Anki deck from list of flashcards.
    
    Args:
        cards: List of notes (Note objects)
        deck_id: Deck ID
        deck_name: Deck name
        
    Returns:
        Anki deck object
    """
    try:
        deck = genanki.Deck(deck_id, deck_name)
        for note in cards:
            deck.add_note(note)
        logger.info(f"✓ Deck successfully created: '{deck_name}' ({len(cards)} flashcards)")
        return deck
    except Exception as e:
        logger.error(f"✗ Error creating deck: {e}")
        raise
