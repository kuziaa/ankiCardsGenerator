import genanki
from gtts import gTTS
import os
import requests
from PIL import Image
from models import en_ru_typing_model
from models import ru_en_typing_model
from models import en_ru_choice_model
from models import ru_en_choice_model
from models import ru_en_scramble_model
import urllib.parse
import io
import csv

# Ваши API ключи для Google Custom Search
API_KEY = 'xxx'
CX = 'xxx'

# ----------------------- ЧТЕНИЕ ДАННЫХ ИЗ CSV ----------------------------
def load_cards_from_csv(csv_file_path='cards.csv'):
    cards = []
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Извлекаем данные из строки CSV
                english = row['english']
                russian = row['russian'] 
                example = row['example']
                incorrectEnVariant1 = row['incorrectEnVariant1']
                incorrectEnVariant2 = row['incorrectEnVariant2']
                incorrectEnVariant3 = row['incorrectEnVariant3']
                incorrectEnVariant4 = row['incorrectEnVariant4']
                incorrectRuVariant1 = row['incorrectRuVariant1']
                incorrectRuVariant2 = row['incorrectRuVariant2']
                incorrectRuVariant3 = row['incorrectRuVariant3']
                incorrectRuVariant4 = row['incorrectRuVariant4']
                
                cards.append((
                    english, russian, example, 
                    incorrectEnVariant1, incorrectEnVariant2, incorrectEnVariant3, incorrectEnVariant4,
                    incorrectRuVariant1, incorrectRuVariant2, incorrectRuVariant3, incorrectRuVariant4
                ))
                
        print(f"Успешно загружено {len(cards)} карточек из {csv_file_path}")
        return cards
        
    except FileNotFoundError:
        print(f"Ошибка: Файл {csv_file_path} не найден!")
        return []
    except KeyError as e:
        print(f"Ошибка: В CSV файле отсутствует необходимый столбец: {e}")
        return []
    except Exception as e:
        print(f"Ошибка при чтении CSV файла: {e}")
        return []

# Загружаем карточки из CSV
cards = load_cards_from_csv()

# ----------------------- MODELS ----------------------------
model_en_ru_typing = en_ru_typing_model.model
model_ru_en_typing = ru_en_typing_model.model
model_en_ru_choice = en_ru_choice_model.model
model_ru_en_choice = ru_en_choice_model.model
model_ru_en_scramble = ru_en_scramble_model.model


# ----------------------- Функция для скачивания картинок ----------------------------
def download_image(search_term, safe_word, max_attempts=5):
    image_path = f"media/{safe_word}.jpg"
    
    # Если картинка уже существует, не скачиваем повторно
    if os.path.exists(image_path):
        return image_path
    
    try:
        # Поиск картинок через Google Custom Search (ищем несколько результатов)
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(search_term)}&searchType=image&key={API_KEY}&cx={CX}&num={max_attempts}"
        print(f'Поиск картинок для: {search_term}')
        response = requests.get(url)
        results = response.json()
        
        if 'items' in results and len(results['items']) > 0:
            # Пытаемся скачать каждую картинку по очереди, пока не найдем рабочую
            for i, item in enumerate(results['items']):
                if i >= max_attempts:
                    break
                    
                image_url = item['link']
                print(f"Попытка {i+1}/{max_attempts}: {image_url}")
                
                try:
                    # Скачиваем картинку
                    img_response = requests.get(image_url, timeout=10)
                    img_response.raise_for_status()
                    
                    # Пытаемся открыть изображение с помощью PIL для проверки
                    image = Image.open(io.BytesIO(img_response.content))
                    
                    # Проверяем, что это действительно изображение
                    image.verify()
                    
                    # Сбрасываем указатель файла и снова открываем для обработки
                    image = Image.open(io.BytesIO(img_response.content))
                    
                    # Конвертируем в RGB если необходимо (для JPEG)
                    if image.mode in ('RGBA', 'P', 'LA'):
                        image = image.convert('RGB')
                    
                    # Сохраняем картинку
                    image.save(image_path, 'JPEG', quality=85)
                    print(f"✓ Успешно скачана картинка для: {search_term}")
                    return image_path
                    
                except Exception as e:
                    print(f"✗ Ошибка при обработке картинки {i+1} для {search_term}: {e}")
                    continue
            
            # Если все попытки неудачны
            print(f"Не удалось скачать ни одну картинку для: {search_term}")
            return None
            
        else:
            print(f"Не найдены картинки для: {search_term}")
            return None
            
    except Exception as e:
        print(f"Ошибка при поиске картинок для {search_term}: {e}")
        return None

# ----------------------- CREATE DECK ----------------------------

deck = genanki.Deck(999004, "Custom EN-RU Vocabulary Deck Type-In test1")

if not os.path.exists("media"):
    os.makedirs("media")

media_files = []

for word, translation, example, incorrectEnVariant1, incorrectEnVariant2, incorrectEnVariant3, incorrectEnVariant4, incorrectRuVariant1, incorrectRuVariant2, incorrectRuVariant3, incorrectRuVariant4 in cards:
    safe = word.replace(" ", "_")
    tts_path = f"media/{safe}.mp3"

    if not os.path.exists(tts_path):
        tts = gTTS(text=word, lang="en")
        tts.save(tts_path)

    media_files.append(tts_path)

    # Скачиваем картинку для слова
    image_path = download_image(word, safe)
    image_field = f'<img src="{safe}.jpg">' if image_path else ""
    
    # Добавляем картинку в media_files если она была скачана
    if image_path:
        media_files.append(image_path)

    # # EN → RU typing card
    # deck.add_note(
    #     genanki.Note(
    #         model=model_en_ru_typing,
    #         fields=[word, translation, example, f"[sound:{safe}.mp3]", image_field],
    #     )
    # )

    # # RU → EN typing card
    # deck.add_note(
    #     genanki.Note(
    #         model=model_ru_en_typing,
    #         fields=[word, translation, example, f"[sound:{safe}.mp3]", image_field],
    #     )
    # )

    # # EN → RU choice card
    # deck.add_note(
    #     genanki.Note(
    #         model=model_en_ru_choice,
    #         fields=[word, translation, example, f"[sound:{safe}.mp3]", incorrectRuVariant1, incorrectRuVariant2, incorrectRuVariant3, incorrectRuVariant4, image_field],
    #     )
    # )

    # # RU → EN choice card
    # deck.add_note(
    #     genanki.Note(
    #         model=model_ru_en_choice,
    #         fields=[word, translation, example, f"[sound:{safe}.mp3]", incorrectEnVariant1, incorrectEnVariant2, incorrectEnVariant3, incorrectEnVariant4, image_field],
    #     )
    # )

    # RU → EN scrumble card
    deck.add_note(
        genanki.Note(
            model=model_ru_en_scramble,
            fields=[word, translation, example, f"[sound:{safe}.mp3]", image_field],
        )
    )

# ----------------------- PACKAGE ----------------------------

genanki.Package(deck, media_files).write_to_file("vocabulary_typein.apkg")

print("Done! Created vocabulary_typein.apkg")
