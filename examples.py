#!/usr/bin/env python3
"""
Примеры использования компонентов Anki Cards Generator
"""

# ============================================================================
# ПРИМЕР 1: Использование Logger (логирование)
# ============================================================================

from utils.logger import setup_logger

# Создаем логгер
logger = setup_logger(__name__)

# Логирование на разных уровнях
logger.debug("Это сообщение DEBUG (видно только в файле логов)")
logger.info("Это сообщение INFO (видно в консоли и файле)")
logger.warning("Это сообщение WARNING (видно в консоли и файле)")
logger.error("Это сообщение ERROR (видно в консоли и файле)")

# Логирование с параметрами
word = "example"
logger.info(f"Обработка слова: {word}")


# ============================================================================
# ПРИМЕР 2: Использование MediaManager (медиа)
# ============================================================================

from utils.media_manager import MediaManager

# Инициализируем менеджер медиа
media_mgr = MediaManager(
    media_dir="media",
    api_key="your_api_key",
    cx="your_cx"
)

# Генерируем аудио
audio_path = media_mgr.generate_audio(
    text="hello world",
    safe_filename="hello_world"
)
print(f"Аудиофайл: {audio_path}")
# Результат: media/hello_world.mp3

# Скачиваем изображение (требует API ключи)
image_path = media_mgr.download_image(
    search_term="hello world",
    safe_filename="hello_world"
)
print(f"Изображение: {image_path}")
# Результат: media/hello_world.jpg или None


# ============================================================================
# ПРИМЕР 3: Использование CardGenerator (создание карточек)
# ============================================================================

from utils.card_generator import CardGenerator, CardData, create_deck_from_cards

# Создаем генератор карточек
generator = CardGenerator()

# Подготавливаем данные одного слова
card_data = CardData(
    english="express my gratitude",
    russian="выразить благодарность",
    example="I want to express my gratitude to you",
    incorrect_en=[
        "impress my gratitude",
        "depress my gratitude",
        "compress my gratitude",
        "oppress my gratitude"
    ],
    incorrect_ru=[
        "выразить легкую благодарность",
        "выразить поверхностную признательность",
        "выразить формальную благодарность",
        "выразить обычную признательность"
    ]
)

# Создаем 5 карточек для этого слова
notes = generator.create_cards(
    card_data=card_data,
    audio_path="media/express_my_gratitude.mp3",
    image_path="media/express_my_gratitude.jpg"
)
print(f"Создано карточек: {len(notes)}")
# Результат: 5


# ============================================================================
# ПРИМЕР 4: Создание полной деки
# ============================================================================

import genanki

# Получаем генератор
generator = CardGenerator()

# Создаем несколько карточек
all_notes = []

cards_to_process = [
    CardData("hello", "привет", "Hello, how are you?", 
             ["hallo", "hullo", "helo", "hello2"],
             ["пока", "до свидания", "привет пока", "добрый день"]),
    CardData("goodbye", "пока", "Goodbye my friend", 
             ["goodby", "good-bye", "bye", "good bye"],
             ["привет", "здравствуйте", "пока пока", "до встречи"]),
]

for card_data in cards_to_process:
    notes = generator.create_cards(card_data)
    all_notes.extend(notes)

# Создаем деку
deck = create_deck_from_cards(
    cards=all_notes,
    deck_id=999004,
    deck_name="My English Deck"
)

# Сохраняем деку
media_files = ["media/hello.mp3", "media/goodbye.mp3"]
genanki.Package(deck, media_files).write_to_file("my_deck.apkg")
print("Дека сохранена в my_deck.apkg")


# ============================================================================
# ПРИМЕР 5: Работа с конфигурацией
# ============================================================================

from utils.properties_util import load_properties

# Загружаем конфигурацию
properties = load_properties("config.properties")

# Получаем значения
api_key = properties.get('API_KEY', '')
deck_name = properties.get('DECK_NAME', 'Default Deck')
csv_file = properties.get('CSV_FILE_PATH', 'cards.csv')

print(f"API Key: {api_key[:10]}..." if api_key else "API Key не задан")
print(f"Имя деки: {deck_name}")
print(f"CSV файл: {csv_file}")


# ============================================================================
# ПРИМЕР 6: Полный цикл обработки (упрощенный)
# ============================================================================

import random
import csv

def process_word(word, translation, example, 
                incorrect_en, incorrect_ru):
    """Обрабатывает одно слово и создает карточки."""
    
    logger = setup_logger(__name__)
    media_mgr = MediaManager()
    generator = CardGenerator()
    
    safe_word = word.replace(" ", "_")
    
    # Генерируем аудио
    audio = media_mgr.generate_audio(word, safe_word)
    
    # Скачиваем изображение
    image = media_mgr.download_image(word, safe_word)
    
    # Создаем карточки
    card_data = CardData(word, translation, example, 
                         incorrect_en, incorrect_ru)
    notes = generator.create_cards(card_data, audio, image)
    
    return notes

# Использование
# notes = process_word("hello", "привет", "Hello world", [...], [...])


# ============================================================================
# ПРИМЕР 7: Обработка CSV и генерация деки (как в основном скрипте)
# ============================================================================

def generate_full_deck_from_csv(csv_file, output_apkg):
    """Пример полной генерации деки из CSV."""
    
    logger = setup_logger(__name__)
    media_mgr = MediaManager(api_key="", cx="")
    generator = CardGenerator()
    
    all_notes = []
    media_files = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, 1):
                try:
                    # Подготавливаем данные
                    card_data = CardData(
                        english=row['english'].strip(),
                        russian=row['russian'].strip(),
                        example=row['example'].strip(),
                        incorrect_en=[
                            row['incorrectEnVariant1'].strip(),
                            row['incorrectEnVariant2'].strip(),
                            row['incorrectEnVariant3'].strip(),
                            row['incorrectEnVariant4'].strip(),
                        ],
                        incorrect_ru=[
                            row['incorrectRuVariant1'].strip(),
                            row['incorrectRuVariant2'].strip(),
                            row['incorrectRuVariant3'].strip(),
                            row['incorrectRuVariant4'].strip(),
                        ]
                    )
                    
                    # Генерируем медиа
                    audio = media_mgr.generate_audio(
                        card_data.english, card_data.safe_filename
                    )
                    if audio:
                        media_files.append(audio)
                    
                    image = media_mgr.download_image(
                        card_data.english, card_data.safe_filename
                    )
                    if image:
                        media_files.append(image)
                    
                    # Создаем карточки
                    notes = generator.create_cards(
                        card_data, audio, image
                    )
                    all_notes.extend(notes)
                    
                    logger.info(f"[{idx}] Обработано: {card_data.english}")
                    
                except Exception as e:
                    logger.error(f"Ошибка в строке {idx}: {e}")
                    continue
        
        # Перемешиваем и сохраняем
        random.shuffle(all_notes)
        deck = create_deck_from_cards(all_notes, 999004, "My Deck")
        genanki.Package(deck, media_files).write_to_file(output_apkg)
        
        logger.info(f"✓ Дека сохранена: {output_apkg}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации деки: {e}")

# Использование:
# generate_full_deck_from_csv("cards.csv", "output.apkg")


print("=" * 70)
print("Примеры использования компонентов успешно загружены!")
print("Смотрите выше примеры использования каждого модуля")
print("=" * 70)
