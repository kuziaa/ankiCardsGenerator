import logging
import sys
from pathlib import Path

# Создаем папку logs если её еще нет
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

def setup_logger(name: str, log_file: str = "logs/anki_generator.log") -> logging.Logger:
    """
    Инициализирует логгер с выводом в консоль и в файл.
    
    Args:
        name: Имя логгера (обычно __name__)
        log_file: Путь к файлу логов
        
    Returns:
        Объект логгера
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Формат для логов
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Вывод в консоль (только INFO и выше)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # Вывод в файл (все уровни)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Предупреждение: не удалось создать обработчик файлов логов: {e}")
    
    logger.addHandler(console_handler)
    
    return logger
