import json

import pytest
from PIL import Image

from image_review import load_manifest


def write_candidate(path, size=(600, 400), color=(120, 160, 200)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def build_manifest(tmp_path, **overrides):
    write_candidate(tmp_path / "candidates" / "verge" / "a1.jpg")
    write_candidate(tmp_path / "candidates" / "verge" / "c5.jpg")
    manifest = {
        "source": "holden",
        "words": [
            {
                "word": "On the verge of",
                "translation": "На грани",
                "example": "...on the verge of war...",
                "pick": "c5",
                "reason": "A rock ledge over a canyon",
                "candidates": [
                    {"id": "a1", "file": "candidates/verge/a1.jpg", "query": "on the verge of"},
                    {"id": "c5", "file": "candidates/verge/c5.jpg", "query": "person on cliff edge"},
                ],
            }
        ],
    }
    manifest.update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_manifest_returns_words(tmp_path):
    manifest = load_manifest(build_manifest(tmp_path))

    assert manifest["source"] == "holden"
    assert manifest["words"][0]["pick"] == "c5"


def test_load_manifest_rejects_unknown_pick(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["pick"] = "zz"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="On the verge of.*zz"):
        load_manifest(path)


def test_load_manifest_rejects_duplicate_candidate_ids(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["candidates"][1]["id"] = "a1"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate candidate id 'a1'"):
        load_manifest(path)


def test_load_manifest_rejects_missing_candidate_file(tmp_path):
    path = build_manifest(tmp_path)
    (tmp_path / "candidates" / "verge" / "c5.jpg").unlink()

    with pytest.raises(ValueError, match="candidate file not found"):
        load_manifest(path)


def test_load_manifest_accepts_a_null_pick(tmp_path):
    path = build_manifest(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["words"][0]["pick"] = None
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    assert load_manifest(path)["words"][0]["pick"] is None
