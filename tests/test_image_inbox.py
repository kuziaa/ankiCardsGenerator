from PIL import Image

from utils.image_inbox import index_inbox, normalize_name, unmatched_files


def write_image(path, size=(40, 30), color=(120, 160, 200)):
    Image.new("RGB", size, color).save(path)
    return path


def test_normalize_name_ignores_case_and_separators():
    assert normalize_name("On the verge of") == "on the verge of"
    assert normalize_name("on-the-verge-of") == "on the verge of"
    assert normalize_name("ON_THE_VERGE_OF") == "on the verge of"


def test_index_inbox_maps_supported_files_and_ignores_the_rest(tmp_path):
    write_image(tmp_path / "Parochial.PNG")
    write_image(tmp_path / "on-the-verge-of.jpg")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    index = index_inbox(tmp_path)

    assert set(index) == {"parochial", "on the verge of"}
    assert index["parochial"].name == "Parochial.PNG"


def test_index_inbox_returns_empty_for_missing_directory(tmp_path):
    assert index_inbox(tmp_path / "does-not-exist") == {}


def test_index_inbox_keeps_one_file_per_normalized_name(tmp_path):
    write_image(tmp_path / "Verge.png")
    write_image(tmp_path / "verge.jpg")

    index = index_inbox(tmp_path)

    assert list(index) == ["verge"]
    assert index["verge"].name == "Verge.png"


def test_unmatched_files_reports_names_no_word_claims(tmp_path):
    write_image(tmp_path / "parochial.jpg")
    write_image(tmp_path / "verge.jpg")

    index = index_inbox(tmp_path)

    assert unmatched_files(index, ["Parochial", "On the verge of"]) == ["verge.jpg"]
