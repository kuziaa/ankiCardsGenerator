import os
import io
import requests
from pathlib import Path
from gtts import gTTS
from PIL import Image
import urllib.parse
from utils.logger import setup_logger

logger = setup_logger(__name__)


class MediaManager:
    """Класс для управления скачиванием и генерацией медиафайлов (аудио, изображения)."""
    
    def __init__(self, media_dir: str = "media", api_key: str = "", cx: str = ""):
        """
        Инициализирует менеджер медиа.
        
        Args:
            media_dir: Папка для сохранения медиафайлов
            api_key: Google Custom Search API ключ
            cx: Google Custom Search CX параметр
        """
        self.media_dir = Path(media_dir)
        self.api_key = api_key
        self.cx = cx
        self.has_api_keys = bool(api_key and cx)
        
        # Создаем папку для медиа если её нет
        self.media_dir.mkdir(exist_ok=True)
        
        if not self.has_api_keys:
            logger.warning("API ключи для Google Custom Search не найдены. "
                         "Скачивание изображений будет пропущено.")
    
    def generate_audio(self, text: str, safe_filename: str, lang: str = "en") -> str:
        """
        Генерирует аудиофайл для текста.
        
        Args:
            text: Текст для озвучивания
            safe_filename: Безопасное имя файла (без расширения)
            lang: Язык (по умолчанию английский)
            
        Returns:
            Путь к файлу аудио или None если ошибка
        """
        audio_path = self.media_dir / f"{safe_filename}.mp3"
        
        # Если файл уже существует, возвращаем путь
        if audio_path.exists():
            logger.debug(f"Аудиофайл уже существует: {audio_path}")
            return str(audio_path)
        
        try:
            logger.info(f"Генерирование аудио для: {text}")
            tts = gTTS(text=text, lang=lang)
            tts.save(str(audio_path))
            logger.info(f"✓ Аудиофайл успешно создан: {audio_path}")
            return str(audio_path)
        except Exception as e:
            logger.error(f"✗ Ошибка при генерировании аудио для '{text}': {e}")
            return None
    
    def download_image(self, search_term: str, safe_filename: str, max_attempts: int = 5) -> str:
        """
        Скачивает изображение через Google Custom Search.
        
        Args:
            search_term: Поисковый запрос
            safe_filename: Безопасное имя файла (без расширения)
            max_attempts: Максимальное количество попыток
            
        Returns:
            Путь к скачанному изображению или None если ошибка/отсутствуют ключи
        """
        # Если API ключи не загружены, пропускаем
        if not self.has_api_keys:
            logger.debug(f"Пропуск скачивания картинки для '{search_term}' "
                        "(отсутствуют API ключи)")
            return None
        
        image_path = self.media_dir / f"{safe_filename}.jpg"
        
        # Если картинка уже существует, не скачиваем повторно
        if image_path.exists():
            logger.debug(f"Изображение уже существует: {image_path}")
            return str(image_path)
        
        try:
            # Поиск картинок через Google Custom Search
            url = (f"https://www.googleapis.com/customsearch/v1?"
                   f"q={urllib.parse.quote(search_term)}&"
                   f"searchType=image&"
                   f"key={self.api_key}&"
                   f"cx={self.cx}&"
                   f"num={max_attempts}")
            
            logger.info(f"Поиск изображений для: {search_term}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            if 'items' not in results or len(results['items']) == 0:
                logger.warning(f"Изображения не найдены для: {search_term}")
                return None
            
            # Пытаемся скачать каждую картинку по очереди
            for i, item in enumerate(results['items'][:max_attempts]):
                image_url = item['link']
                logger.debug(f"Попытка {i+1}/{max_attempts}: {image_url}")
                
                try:
                    # Скачиваем картинку
                    img_response = requests.get(image_url, timeout=10)
                    img_response.raise_for_status()
                    
                    # Пытаемся открыть изображение для проверки
                    image = Image.open(io.BytesIO(img_response.content))
                    image.verify()
                    
                    # Сбрасываем указатель и снова открываем
                    image = Image.open(io.BytesIO(img_response.content))
                    
                    # Конвертируем в RGB если необходимо
                    if image.mode in ('RGBA', 'P', 'LA'):
                        image = image.convert('RGB')
                    
                    # Сохраняем картинку
                    image.save(str(image_path), 'JPEG', quality=85)
                    logger.info(f"✓ Изображение успешно скачано: {search_term}")
                    return str(image_path)
                    
                except Exception as e:
                    logger.debug(f"Не удалось обработать изображение {i+1} "
                               f"для '{search_term}': {e}")
                    continue
            
            logger.warning(f"Не удалось скачать ни одно изображение для: {search_term}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"✗ Ошибка при поиске изображений для '{search_term}': {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка при скачивании изображения "
                        f"для '{search_term}': {e}")
            return None
    
    def get_media_files_list(self) -> list:
        """
        Возвращает список всех медиафайлов в папке.
        
        Returns:
            Список путей к медиафайлам
        """
        media_files = []
        if self.media_dir.exists():
            media_files = [str(f) for f in self.media_dir.glob("*") if f.is_file()]
        return media_files
