#!/usr/bin/env python3
"""
Anki Cards Generator - Генератор карточек для изучения английских слов

Этот скрипт создает Anki деку с карточками из CSV файла, включая:
- Генерацию аудио для каждого слова
- Скачивание изображений через Google Custom Search
- Создание 5 типов карточек (typing, choice, scramble)
"""

import csv
import random
import sys
from pathlib import Path

import genanki

from utils.logger import setup_logger
from utils.properties_util import load_properties
from utils.media_manager import MediaManager
from utils.card_generator import CardGenerator, CardData, create_deck_from_cards

# Инициализируем логгер
logger = setup_logger(__name__)


def load_cards_from_csv(csv_file_path: str) -> list:
    """
    Загружает карточки из CSV файла.
    
    Args:
        csv_file_path: Путь к CSV файлу
        
    Returns:
        Список объектов CardData
    """
    cards = []
    
    if not Path(csv_file_path).exists():
        logger.error(f"✗ Файл {csv_file_path} не найден!")
        return cards
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Проверяем наличие необходимых столбцов
            required_columns = {
                'english', 'russian', 'example',
                'incorrectEnVariant1', 'incorrectEnVariant2', 
                'incorrectEnVariant3', 'incorrectEnVariant4',
                'incorrectRuVariant1', 'incorrectRuVariant2',
                'incorrectRuVariant3', 'incorrectRuVariant4'
            }
            
            if reader.fieldnames is None:
                logger.error("CSV файл пуст или повреждён!")
                return cards
            
            if not required_columns.issubset(set(reader.fieldnames)):
                missing = required_columns - set(reader.fieldnames)
                logger.error(f"В CSV файле отсутствуют столбцы: {missing}")
                return cards
            
            for idx, row in enumerate(reader, 1):
                try:
                    card = CardData(
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
                    
                    # Валидация данных
                    if not card.english or not card.russian:
                        logger.warning(f"Строка {idx}: пропущена (отсутствует английское или русское слово)")
                        continue
                    
                    cards.append(card)
                    
                except KeyError as e:
                    logger.warning(f"Строка {idx}: ошибка при чтении столбца {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Строка {idx}: непредвиденная ошибка {e}")
                    continue
        
        logger.info(f"✓ Успешно загружено {len(cards)} карточек из {csv_file_path}")
        return cards
        
    except Exception as e:
        logger.error(f"✗ Ошибка при чтении CSV файла: {e}")
        return []


def main():
    """Основная функция для генерации Anki деки."""
    
    logger.info("=" * 60)
    logger.info("Запуск Anki Cards Generator")
    logger.info("=" * 60)
    
    # Загружаем настройки
    try:
        # Ищем config в корневой папке проекта
        config_path = Path(__file__).parent.parent / 'config.properties'
        properties = load_properties(str(config_path))
    except Exception as e:
        logger.error(f"✗ Не удалось загрузить настройки: {e}")
        return False
    
    # Получаем параметры из конфига
    api_key = properties.get('API_KEY', '')
    cx = properties.get('CX', '')
    deck_id = int(properties.get('DECK_ID', '999004'))
    deck_name = properties.get('DECK_NAME', 'Custom EN-RU Vocabulary Deck')
    
    # Преобразуем пути относительно корневой папки проекта
    root_path = Path(__file__).parent.parent
    csv_file_path = root_path / properties.get('CSV_FILE_PATH', 'src/resources/cards.csv')
    media_dir = root_path / properties.get('MEDIA_DIR', 'media')
    output_file = root_path / properties.get('OUTPUT_FILE', 'vocabulary.apkg')
    
    # Загружаем карточки из CSV
    cards_data = load_cards_from_csv(str(csv_file_path))
    
    if not cards_data:
        logger.error("✗ Нет карточек для обработки. Выход.")
        return False
    
    # Инициализируем менеджер медиа и генератор карточек
    media_manager = MediaManager(media_dir=str(media_dir), api_key=api_key, cx=cx)
    card_generator = CardGenerator()
    
    all_notes = []
    media_files = []
    
    logger.info(f"Обработка {len(cards_data)} слов...")
    
    # Обрабатываем каждое слово
    for idx, card_data in enumerate(cards_data, 1):
        try:
            logger.info(f"[{idx}/{len(cards_data)}] Обработка: {card_data.english}")
            
            # Генерируем аудио
            audio_path = media_manager.generate_audio(
                text=card_data.english,
                safe_filename=card_data.safe_filename
            )
            if audio_path:
                media_files.append(audio_path)
            
            # Скачиваем изображение
            image_path = media_manager.download_image(
                search_term=card_data.english,
                safe_filename=card_data.safe_filename
            )
            if image_path:
                media_files.append(image_path)
            
            # Создаем карточки
            notes = card_generator.create_cards(
                card_data=card_data,
                audio_path=audio_path,
                image_path=image_path
            )
            
            if notes:
                all_notes.extend(notes)
            else:
                logger.warning(f"Не удалось создать карточки для {card_data.english}")
                
        except Exception as e:
            logger.error(f"✗ Ошибка при обработке слова '{card_data.english}': {e}")
            continue
    
    if not all_notes:
        logger.error("✗ Не удалось создать ни одну карточку. Выход.")
        return False
    
    # Перемешиваем карточки
    logger.info(f"Перемешивание {len(all_notes)} карточек...")
    random.shuffle(all_notes)
    
    # Создаем деку
    try:
        deck = create_deck_from_cards(all_notes, deck_id, deck_name)
    except Exception as e:
        logger.error(f"✗ Не удалось создать деку: {e}")
        return False
    
    # Упаковываем в APKG файл
    try:
        logger.info(f"Сохранение деки в {output_file}...")
        genanki.Package(deck, media_files).write_to_file(str(output_file))
        logger.info(f"✓ APKG файл успешно создан: {output_file}")
    except Exception as e:
        logger.error(f"✗ Ошибка при сохранении APKG файла: {e}")
        return False
    
    logger.info("=" * 60)
    logger.info("✓ Процесс успешно завершен!")
    logger.info(f"  Всего карточек создано: {len(all_notes)}")
    logger.info(f"  Файл сохранен: {output_file}")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠ Процесс прерван пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"✗ Неожиданная ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
