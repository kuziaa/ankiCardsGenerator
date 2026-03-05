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
    """Class for managing media file downloads and generation (audio, images)."""
    
    def __init__(self, media_dir: str = "media", api_key: str = "", cx: str = ""):
        """
        Initialize the media manager.
        
        Args:
            media_dir: Directory for saving media files
            api_key: Google Custom Search API key
            cx: Google Custom Search CX parameter
        """
        self.media_dir = Path(media_dir)
        self.api_key = api_key
        self.cx = cx
        self.has_api_keys = bool(api_key and cx)
        
        # Create media directory if it doesn't exist
        self.media_dir.mkdir(exist_ok=True)
        
        if not self.has_api_keys:
            logger.warning("API keys for Google Custom Search not found. "
                         "Image downloading will be skipped.")
    
    def generate_audio(self, text: str, safe_filename: str, lang: str = "en") -> str:
        """
        Generate audio file for text.
        
        Args:
            text: Text to speak
            safe_filename: Safe filename (without extension)
            lang: Language (English by default)
            
        Returns:
            Path to audio file or None if error
        """
        audio_path = self.media_dir / f"{safe_filename}.mp3"
        
        # If file already exists, return path
        if audio_path.exists():
            logger.debug(f"Audio file already exists: {audio_path}")
            return str(audio_path)
        
        try:
            logger.info(f"Generating audio for: {text}")
            tts = gTTS(text=text, lang=lang)
            tts.save(str(audio_path))
            logger.info(f"✓ Audio file successfully created: {audio_path}")
            return str(audio_path)
        except Exception as e:
            logger.error(f"✗ Error generating audio for '{text}': {e}")
            return None
    
    def download_image(self, search_term: str, safe_filename: str, max_attempts: int = 5) -> str:
        """
        Download image via Google Custom Search.
        
        Args:
            search_term: Search query
            safe_filename: Safe filename (without extension)
            max_attempts: Maximum number of attempts
            
        Returns:
            Path to downloaded image or None if error/missing keys
        """
        # Skip if API keys are not loaded
        if not self.has_api_keys:
            logger.debug(f"Skipping image download for '{search_term}' "
                        "(API keys missing)")
            return None
        
        image_path = self.media_dir / f"{safe_filename}.jpg"
        
        # If image already exists, don't download again
        if image_path.exists():
            logger.debug(f"Image already exists: {image_path}")
            return str(image_path)
        
        try:
            # Search for images via Google Custom Search
            url = (f"https://www.googleapis.com/customsearch/v1?"
                   f"q={urllib.parse.quote(search_term)}&"
                   f"searchType=image&"
                   f"key={self.api_key}&"
                   f"cx={self.cx}&"
                   f"num={max_attempts}")
            
            logger.info(f"Searching for images: {search_term}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            if 'items' not in results or len(results['items']) == 0:
                logger.warning(f"No images found for: {search_term}")
                return None
            
            # Try to download each image in sequence
            for i, item in enumerate(results['items'][:max_attempts]):
                image_url = item['link']
                logger.debug(f"Attempt {i+1}/{max_attempts}: {image_url}")
                
                try:
                    # Download image
                    img_response = requests.get(image_url, timeout=10)
                    img_response.raise_for_status()
                    
                    # Try to open image for validation
                    image = Image.open(io.BytesIO(img_response.content))
                    image.verify()
                    
                    # Reset pointer and open again
                    image = Image.open(io.BytesIO(img_response.content))
                    
                    # Convert to RGB if necessary
                    if image.mode in ('RGBA', 'P', 'LA'):
                        image = image.convert('RGB')
                    
                    # Save image
                    image.save(str(image_path), 'JPEG', quality=85)
                    logger.info(f"✓ Image successfully downloaded: {search_term}")
                    return str(image_path)
                    
                except Exception as e:
                    logger.debug(f"Failed to process image {i+1} "
                               f"for '{search_term}': {e}")
                    continue
            
            logger.warning(f"Failed to download any image for: {search_term}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"✗ Error searching for images for '{search_term}': {e}")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error downloading image "
                        f"for '{search_term}': {e}")
            return None
    
    def get_media_files_list(self) -> list:
        """
        Get list of all media files in directory.
        
        Returns:
            List of paths to media files
        """
        media_files = []
        if self.media_dir.exists():
            media_files = [str(f) for f in self.media_dir.glob("*") if f.is_file()]
        return media_files
