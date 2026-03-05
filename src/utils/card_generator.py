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
    """Класс для хранения данных одной карточки."""
    
    def __init__(self, english: str, russian: str, example: str,
                 incorrect_en: List[str], incorrect_ru: List[str]):
        self.english = english
        self.russian = russian
        self.example = example
        self.incorrect_en = incorrect_en
        self.incorrect_ru = incorrect_ru
        self.safe_filename = english.replace(" ", "_")


class CardGenerator:
    """Класс для генерации Anki карточек различных типов."""
    
    def __init__(self):
        """Инициализирует генератор карточек с моделями."""
        self.model_en_ru_typing = en_ru_typing_model.model
        self.model_ru_en_typing = ru_en_typing_model.model
        self.model_en_ru_choice = en_ru_choice_model.model
        self.model_ru_en_choice = ru_en_choice_model.model
        self.model_ru_en_scramble = ru_en_scramble_model.model
    
    def create_cards(self, card_data: CardData, audio_path: str = None,
                    image_path: str = None) -> List[genanki.Note]:
        """
        Создает набор карточек для одного слова (все 5 типов).
        
        Args:
            card_data: Объект с данными карточки
            audio_path: Путь к аудиофайлу (может быть None)
            image_path: Путь к изображению (может быть None)
            
        Returns:
            Список созданных заметок (Note объектов)
        """
        notes = []
        
        # Подготавливаем звук и изображение
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
            
            logger.debug(f"Успешно созданы 5 карточек для слова: {card_data.english}")
            return notes
            
        except Exception as e:
            logger.error(f"✗ Ошибка при создании карточек для '{card_data.english}': {e}")
            return []


def create_deck_from_cards(cards: List[genanki.Note], deck_id: int,
                          deck_name: str) -> genanki.Deck:
    """
    Создает Anki деку из списка карточек.
    
    Args:
        cards: Список заметок (Note объектов)
        deck_id: ID деки
        deck_name: Имя деки
        
    Returns:
        Объект Anki деки
    """
    try:
        deck = genanki.Deck(deck_id, deck_name)
        for note in cards:
            deck.add_note(note)
        logger.info(f"✓ Дека успешно создана: '{deck_name}' ({len(cards)} карточек)")
        return deck
    except Exception as e:
        logger.error(f"✗ Ошибка при создании деки: {e}")
        raise
