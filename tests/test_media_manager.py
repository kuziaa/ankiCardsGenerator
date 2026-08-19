from pathlib import Path

import pytest
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


def make_inbox(tmp_path, name, size=(2000, 1500), color=(10, 200, 10)):
    inbox = tmp_path / "inbox"
    inbox.mkdir(exist_ok=True)
    Image.new("RGB", size, color).save(inbox / name)
    return inbox


def test_manual_image_is_converted_and_downscaled(tmp_path):
    inbox = make_inbox(tmp_path, "Parochial.png")
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    result = manager.download_image(search_term="Parochial",
                                    safe_filename="parochial_abc12345")

    assert result is not None
    with Image.open(result) as image:
        assert image.format == "JPEG"
        assert max(image.size) == 800
    assert manager.manual_count == 1


def test_small_manual_image_is_not_upscaled(tmp_path):
    inbox = make_inbox(tmp_path, "dojo.jpg", size=(120, 90))
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    result = manager.download_image(search_term="dojo", safe_filename="dojo_abc12345")

    with Image.open(result) as image:
        assert image.size == (120, 90)


def test_manual_image_overrides_a_cached_file(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    Image.new("RGB", (60, 40), (220, 10, 10)).save(media / "verge_abc12345.jpg")
    inbox = make_inbox(tmp_path, "on the verge of.jpg", size=(60, 40))

    manager = MediaManager(media_dir=str(media), offline=True, inbox_dir=str(inbox))
    result = manager.download_image(search_term="On the verge of",
                                    safe_filename="verge_abc12345")

    with Image.open(result) as image:
        red, green, _ = image.convert("RGB").getpixel((30, 20))
    assert green > 150 and red < 100


def test_manual_image_skips_the_search(tmp_path):
    inbox = make_inbox(tmp_path, "parochial.jpg", size=(60, 40))
    manager = MediaManager(media_dir=str(tmp_path / "media"), api_key="key",
                           cx="cx", inbox_dir=str(inbox))
    manager.session.get = lambda *args, **kwargs: pytest.fail("search must not run")

    assert manager.download_image("Parochial", "parochial_abc12345") is not None


def test_broken_manual_file_falls_through(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "parochial.jpg").write_bytes(b"this is not an image")
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    assert manager.download_image("Parochial", "parochial_abc12345") is None
    assert manager.manual_count == 0


def test_inbox_file_is_left_untouched(tmp_path):
    inbox = make_inbox(tmp_path, "dojo.png", size=(1600, 1200))
    source = inbox / "dojo.png"
    before = source.read_bytes()
    manager = MediaManager(media_dir=str(tmp_path / "media"), offline=True,
                           inbox_dir=str(inbox))

    manager.download_image("dojo", "dojo_abc12345")

    assert source.read_bytes() == before


def test_cached_image_counts_as_auto(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    write_valid_jpeg(media / "dojo_abc12345.jpg")
    manager = MediaManager(media_dir=str(media), offline=True)

    assert manager.download_image("dojo", "dojo_abc12345") is not None
    assert manager.auto_count == 1
    assert manager.manual_count == 0
