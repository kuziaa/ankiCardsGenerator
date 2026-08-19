import io
import os
import socket
import time
import urllib.parse
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from gtts import gTTS
from PIL import Image

from utils.image_inbox import index_inbox, normalize_name
from utils.logger import setup_logger

logger = setup_logger(__name__)

# gTTS uses requests internally without a timeout; this is the only way to bound it
socket.setdefaulttimeout(30)

AUDIO_MIN_BYTES = 1024
MP3_MAGIC_PREFIXES = (b"ID3", b"\xff")
IMAGE_MIN_BYTES = 5000
MANUAL_IMAGE_MAX_SIDE = 800
TTS_ATTEMPTS = 3
TTS_THROTTLE_SECONDS = 0.4
REQUEST_TIMEOUT = (5, 20)


def _atomic_write(path: Path, data: bytes) -> None:
    """Write to a temp file and rename so the cache never holds partial files."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _looks_like_mp3(data: bytes) -> bool:
    return len(data) >= AUDIO_MIN_BYTES and data.startswith(MP3_MAGIC_PREFIXES)


class MediaManager:
    """Class for managing media file downloads and generation (audio, images)."""

    def __init__(self, media_dir: str = "media", api_key: str = "", cx: str = "",
                 offline: bool = False, inbox_dir: str = ""):
        """
        Initialize the media manager.

        Args:
            media_dir: Directory for saving media files
            api_key: Google Custom Search API key
            cx: Google Custom Search CX parameter
            offline: Use only validated cached media files and skip network calls
            inbox_dir: Directory with manually curated images for this source file
        """
        self.media_dir = Path(media_dir)
        self.api_key = api_key
        self.cx = cx
        self.offline = offline
        self.has_api_keys = bool(api_key and cx)
        self.search_disabled = False
        self.inbox_index = index_inbox(inbox_dir) if inbox_dir else {}
        self.manual_count = 0
        self.auto_count = 0
        self.session = self._make_session()

        # Create media directory if it doesn't exist
        self.media_dir.mkdir(exist_ok=True)

        if not self.has_api_keys and not self.offline:
            logger.warning("API keys for Google Custom Search not found. "
                         "Image downloading will be skipped.")

    @staticmethod
    def _make_session() -> requests.Session:
        """One session for all downloads: keep-alive, retries with backoff, sane UA."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers["User-Agent"] = "ankiCardsGenerator/1.0 (personal tool)"
        return session

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

        # Reuse the cached file only when it passes validation
        if audio_path.exists():
            if _looks_like_mp3(audio_path.read_bytes()):
                logger.debug(f"Audio file already exists: {audio_path}")
                return str(audio_path)
            logger.warning(f"Cached audio is corrupt, removing: {audio_path}")
            audio_path.unlink()

        if self.offline:
            logger.debug(f"Skipping audio generation for '{text}' (offline mode)")
            return None

        for attempt in range(1, TTS_ATTEMPTS + 1):
            try:
                logger.info(f"Generating audio for: {text}")
                buffer = io.BytesIO()
                gTTS(text=text, lang=lang).write_to_fp(buffer)
                data = buffer.getvalue()
                if not _looks_like_mp3(data):
                    raise ValueError(f"TTS returned invalid audio ({len(data)} bytes)")
                _atomic_write(audio_path, data)
                logger.info(f"✓ Audio file successfully created: {audio_path}")
                # Small pause so batch runs do not hammer the TTS endpoint
                time.sleep(TTS_THROTTLE_SECONDS)
                return str(audio_path)
            except Exception as e:
                logger.warning(f"Audio attempt {attempt}/{TTS_ATTEMPTS} failed "
                              f"for '{text}': {e}")
                if attempt < TTS_ATTEMPTS:
                    time.sleep(1.5 * attempt)

        logger.error(f"✗ Error generating audio for '{text}': all attempts failed")
        return None

    def _manual_image(self, search_term: str, image_path: Path) -> bool:
        """Copy a curated inbox file into the deck media, converted and capped."""
        source = self.inbox_index.get(normalize_name(search_term))
        if source is None:
            return False

        try:
            with Image.open(source) as image:
                image.load()
                converted = image.convert("RGB")
                converted.thumbnail((MANUAL_IMAGE_MAX_SIDE, MANUAL_IMAGE_MAX_SIDE))
                buffer = io.BytesIO()
                converted.save(buffer, "JPEG", quality=85)
        except Exception as e:
            logger.error(f"✗ Broken image in inbox ({source.name}): {e}")
            return False

        _atomic_write(image_path, buffer.getvalue())
        logger.info(f"✓ Image taken from inbox: {source.name}")
        return True

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
        image_path = self.media_dir / f"{safe_filename}.jpg"

        # A curated file wins over the cache and the search
        if self._manual_image(search_term, image_path):
            self.manual_count += 1
            return str(image_path)

        # Reuse the cached file only when it passes validation
        if image_path.exists():
            if self._valid_cached_image(image_path):
                logger.debug(f"Image already exists: {image_path}")
                self.auto_count += 1
                return str(image_path)
            logger.warning(f"Cached image is corrupt, removing: {image_path}")
            image_path.unlink()

        if self.offline:
            logger.debug(f"Skipping image download for '{search_term}' (offline mode)")
            return None

        # Skip if API keys are not loaded
        if not self.has_api_keys:
            logger.debug(f"Skipping image download for '{search_term}' "
                        "(API keys missing)")
            return None

        # Skip once the daily search quota is exhausted
        if self.search_disabled:
            logger.debug(f"Skipping image search for '{search_term}' (quota exhausted)")
            return None

        try:
            # Search for images via Google Custom Search
            url = (f"https://www.googleapis.com/customsearch/v1?"
                   f"q={urllib.parse.quote(search_term)}&"
                   f"searchType=image&"
                   f"key={self.api_key}&"
                   f"cx={self.cx}&"
                   f"num={max_attempts}")

            logger.info(f"Searching for images: {search_term}")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            results = response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (403, 429):
                self.search_disabled = True
                logger.error(f"✗ Image search returned {status} - daily quota likely "
                            "exhausted, skipping image search for the remaining words")
            else:
                logger.error(f"✗ Error searching for images for '{search_term}': {e}")
            return None
        except requests.RequestException as e:
            logger.error(f"✗ Error searching for images for '{search_term}': {e}")
            return None

        if 'items' not in results or len(results['items']) == 0:
            logger.warning(f"No images found for: {search_term}")
            return None

        # Try to download each image in sequence
        for i, item in enumerate(results['items'][:max_attempts]):
            image_url = item['link']
            logger.debug(f"Attempt {i+1}/{max_attempts}: {image_url}")

            try:
                img_response = self.session.get(image_url, timeout=REQUEST_TIMEOUT)
                img_response.raise_for_status()

                content_type = img_response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    raise ValueError(f"not an image: Content-Type={content_type}")
                if len(img_response.content) < IMAGE_MIN_BYTES:
                    raise ValueError(f"too small ({len(img_response.content)} bytes)")

                # Try to open image for validation
                image = Image.open(io.BytesIO(img_response.content))
                image.verify()

                # Reset pointer and open again
                image = Image.open(io.BytesIO(img_response.content))

                # Convert to RGB if necessary
                if image.mode in ('RGBA', 'P', 'LA'):
                    image = image.convert('RGB')

                # Re-encode and save atomically
                buffer = io.BytesIO()
                image.save(buffer, 'JPEG', quality=85)
                _atomic_write(image_path, buffer.getvalue())
                logger.info(f"✓ Image successfully downloaded: {search_term}")
                self.auto_count += 1
                return str(image_path)

            except Exception as e:
                logger.debug(f"Failed to process image {i+1} "
                           f"for '{search_term}': {e}")
                continue

        logger.warning(f"Failed to download any image for: {search_term}")
        return None

    @staticmethod
    def _valid_cached_image(path: Path) -> bool:
        try:
            if path.stat().st_size < IMAGE_MIN_BYTES:
                return False
            with Image.open(path) as image:
                image.verify()
            return True
        except Exception:
            return False

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
