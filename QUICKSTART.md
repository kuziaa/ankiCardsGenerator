## Быстрый старт

### 1️⃣ Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2️⃣ Проверка окружения

```bash
python check_setup.py
```

### 3️⃣ Конфигурация (опционально)

```bash
cp config.properties.sample config.properties
# Отредактируйте config.properties если нужны изображения
```

### 4️⃣ Запуск

```bash
cd src
python anki_generator.py
```

### 5️⃣ Импорт в Anki

- Откройте Anki
- File → Import → выберите `vocabulary.apkg`

---

## Основные улучшения версии 2.0

| Улучшение | Описание |
|-----------|---------|
| 🏗️ Архитектура | Разбито на модули: logger, media_manager, card_generator |
| 📝 Логирование | Структурированное логирование в консоль и файл |
| 🛡️ Ошибки | Graceful error handling - продолжение при ошибках |
| ⚙️ Конфигурация | Гибкая конфигурация через properties файл |
| 📚 Документация | Полный README, IMPROVEMENTS, примеры кода |
| ✅ Валидация | Проверка CSV данных перед обработкой |
| 🎯 Удобство | Прогресс выполнения, информативные логи |

---

## Структура новых модулей

### `src/utils/logger.py`
```python
from utils.logger import setup_logger
logger = setup_logger(__name__)
logger.info("Сообщение")  # Логирование
```

### `src/utils/media_manager.py`
```python
from utils.media_manager import MediaManager
media_mgr = MediaManager(api_key="...", cx="...")
audio = media_mgr.generate_audio("word", "word")
image = media_mgr.download_image("word", "word")
```

### `src/utils/card_generator.py`
```python
from utils.card_generator import CardGenerator, CardData, create_deck_from_cards
gen = CardGenerator()
card_data = CardData("word", "перевод", "пример", [...], [...])
notes = gen.create_cards(card_data, audio, image)
deck = create_deck_from_cards(notes, 999004, "Deck Name")
```

---

## Новые функции

✨ **Что добавлено**:
- Модульная архитектура для легкого расширения
- Класс CardData для типизированного хранения данных
- Класс MediaManager для управления медиа
- Класс CardGenerator для создания карточек
- Логирование в файл logs/anki_generator.log
- Проверка существования файлов перед использованием
- Валидация CSV перед обработкой
- Graceful error handling на каждом шаге
- Параметризуемые ID деки и имя из config
- Скрипт check_setup.py для проверки окружения

---

## Файлы проекта

```
├── README.md                    # Полная документация
├── IMPROVEMENTS.md              # Описание улучшений
├── QUICKSTART.md                # Этот файл
├── requirements.txt             # Зависимости
├── check_setup.py              # Проверка окружения
├── config.properties.sample    # Шаблон конфигурации
└── src/
    ├── anki_generator.py       # Основной скрипт (переписан)
    ├── models/                 # Модели карточек (без изменений)
    ├── utils/
    │   ├── logger.py           # Новый: логирование
    │   ├── media_manager.py    # Новый: управление медиа
    │   ├── card_generator.py   # Новый: генерация карточек
    │   └── properties_util.py  # Без изменений
    └── resources/
        └── cards.csv           # Ваши данные
```

---

## Часто задаваемые вопросы

**Q: Скрипт работает без API ключей?**  
A: Да! Без API ключей будут созданы карточки без изображений, но с аудио.

**Q: Как изменить имя деки?**  
A: Отредактируйте DECK_NAME в config.properties

**Q: Где находятся логи?**  
A: В файле logs/anki_generator.log

**Q: Почему медленно скачиваются изображения?**  
A: Это нормально - Google Custom Search может быть медленным. Проверьте интернет.

**Q: Как добавить новый тип карточки?**  
A: Смотрите раздел "Расширение функционала" в README.md

---

**Готово! 🎉 Проект полностью переработан и готов к использованию.**
