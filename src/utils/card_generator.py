import genanki
from typing import List, Tuple
from models import en_ru_typing_model
from models import ru_en_typing_model
from models import en_ru_choice_model
from models import ru_en_choice_model
from models import ru_en_scramble_model
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CardData:
    """Class for storing data of one flashcard."""
    
    def __init__(self, english: str, russian: str, example: str,
                 incorrect_en: List[str], incorrect_ru: List[str]):
        self.english = english
        self.russian = russian
        self.example = example
        self.incorrect_en = incorrect_en
        self.incorrect_ru = incorrect_ru
        self.safe_filename = english.replace(" ", "_")


class CardGenerator:
    """Class for generating Anki flashcards of various types."""
    
    def __init__(self):
        """Initialize card generator with models."""
        self.model_en_ru_typing = en_ru_typing_model.model
        self.model_ru_en_typing = ru_en_typing_model.model
        self.model_en_ru_choice = en_ru_choice_model.model
        self.model_ru_en_choice = ru_en_choice_model.model
        self.model_ru_en_scramble = ru_en_scramble_model.model
    
    def create_cards(self, card_data: CardData, audio_path: str = None,
                    image_path: str = None) -> List[genanki.Note]:
        """
        Create a set of flashcards for one word (all 5 types).
        
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
        
        try:
            # EN → RU typing card
            notes.append(
                genanki.Note(
                    model=self.model_en_ru_typing,
                    fields=[card_data.english, card_data.russian, card_data.example,
                           audio_field, image_field],
                )
            )
            
            # RU → EN typing card
            notes.append(
                genanki.Note(
                    model=self.model_ru_en_typing,
                    fields=[card_data.english, card_data.russian, card_data.example,
                           audio_field, image_field],
                )
            )
            
            # EN → RU choice card
            notes.append(
                genanki.Note(
                    model=self.model_en_ru_choice,
                    fields=[card_data.english, card_data.russian, card_data.example,
                           audio_field] + card_data.incorrect_ru + [image_field],
                )
            )
            
            # RU → EN choice card
            notes.append(
                genanki.Note(
                    model=self.model_ru_en_choice,
                    fields=[card_data.english, card_data.russian, card_data.example,
                           audio_field] + card_data.incorrect_en + [image_field],
                )
            )
            
            # RU → EN scramble card
            notes.append(
                genanki.Note(
                    model=self.model_ru_en_scramble,
                    fields=[card_data.english, card_data.russian, card_data.example,
                           audio_field, image_field],
                )
            )
            
            logger.debug(f"Successfully created 5 flashcards for word: {card_data.english}")
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
