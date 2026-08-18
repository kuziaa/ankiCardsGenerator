import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

def setup_logger(name: str, log_file: str = "logs/anki_generator.log") -> logging.Logger:
    """
    Initialize logger with output to console and file.
    
    Args:
        name: Logger name (usually __name__)
        log_file: Path to log file
        
    Returns:
        Logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Log format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console output (INFO and above only)
    # Windows consoles often default to a legacy codepage; never crash on unicode
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    # File output (all levels)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: failed to create file handler: {e}")
    
    logger.addHandler(console_handler)
    
    return logger
