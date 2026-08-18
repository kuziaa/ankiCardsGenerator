from pathlib import Path

from PIL import Image

from utils.media_manager import MediaManager


def write_valid_jpeg(path: Path):
    image = Image.new("RGB", (300, 300))
    image.putdata([
        ((x * 7) % 256, (y * 11) % 256, (x * y) % 256)
        for y in range(300)
        for x in range(300)
    ])
    image.save(path, "JPEG", quality=95)


def test_generate_audio_offline_uses_valid_cached_file(tmp_path):
    audio_path = tmp_path / "dojo.mp3"
    audio_path.write_bytes(b"ID3" + (b"0" * 2048))
    manager = MediaManager(media_dir=str(tmp_path), offline=True)

    assert manager.generate_audio("dojo", "dojo") == str(audio_path)


def test_generate_audio_offline_removes_corrupt_cache_without_network(tmp_path):
    audio_path = tmp_path / "dojo.mp3"
    audio_path.write_bytes(b"bad")
    manager = MediaManager(media_dir=str(tmp_path), offline=True)

    assert manager.generate_audio("dojo", "dojo") is None
    assert not audio_path.exists()


def test_download_image_offline_uses_valid_cached_file_without_api_keys(tmp_path):
    image_path = tmp_path / "dojo.jpg"
    write_valid_jpeg(image_path)
    manager = MediaManager(media_dir=str(tmp_path), offline=True)

    assert manager.download_image("dojo", "dojo") == str(image_path)


def test_download_image_offline_removes_corrupt_cache_without_network(tmp_path):
    image_path = tmp_path / "dojo.jpg"
    image_path.write_bytes(b"bad")
    manager = MediaManager(media_dir=str(tmp_path), offline=True)

    assert manager.download_image("dojo", "dojo") is None
    assert not image_path.exists()
