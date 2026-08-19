import base64
import io
import json
import re

import pytest
from PIL import Image

from image_review import TEMPLATE_PATH, load_manifest, main, render_page


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


def render(tmp_path, **overrides):
    manifest = load_manifest(build_manifest(tmp_path, **overrides))
    return render_page(manifest, TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_page_renders_a_section_per_word(tmp_path):
    html = render(tmp_path)

    assert html.count('<section class="word"') == 1
    assert 'data-word="On the verge of"' in html


def test_proposed_pick_is_preselected(tmp_path):
    html = render(tmp_path)

    assert 'value="c5" checked' in html
    assert 'value="a1" checked' not in html


def test_page_offers_the_two_extra_states(tmp_path):
    html = render(tmp_path)

    assert 'value="__none__"' in html
    assert 'value="__more__"' in html


def test_candidates_sit_in_one_strip_beside_the_extra_states(tmp_path):
    html = render(tmp_path)

    strip = html.split('<div class="strip">')[1].split("</div>")[0]
    assert strip.count('class="cand"') == 2
    assert "__none__" not in strip
    assert html.index('<div class="specials">') > html.index('<div class="strip">')


def test_word_without_candidates_explains_itself(tmp_path):
    manifest_path = build_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["words"].append({
        "word": "Necrosis", "translation": "Некроз", "example": "keep the necrosis under control",
        "pick": None, "reason": "Clinical imagery only - not searched on purpose",
        "candidates": [],
    })
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    html = render_page(load_manifest(manifest_path),
                       TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert 'class="empty"' in html
    assert "Clinical imagery only - not searched on purpose" in html
    assert html.count('value="__none__" checked') == 1


def test_page_carries_a_copyable_fallback(tmp_path):
    html = render(tmp_path)

    assert '<dialog id="fallback">' in html
    assert 'id="payload"' in html
    assert 'id="download"' in html


def test_previews_are_embedded_and_paths_do_not_leak(tmp_path):
    html = render(tmp_path)

    assert html.count("data:image/jpeg;base64,") == 2
    assert "candidates/verge/a1.jpg" not in html


def test_previews_are_downscaled(tmp_path):
    write_candidate(tmp_path / "candidates" / "verge" / "a1.jpg", size=(2000, 1500))
    html = render(tmp_path)

    encoded = re.search(r'data:image/jpeg;base64,([^"]+)"', html).group(1)
    with Image.open(io.BytesIO(base64.b64decode(encoded))) as image:
        assert max(image.size) == 420


def test_text_is_escaped(tmp_path):
    manifest_path = build_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["words"][0]["example"] = "war & <b>peace</b>"
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    html = render_page(load_manifest(manifest_path),
                       TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert "war &amp; &lt;b&gt;peace&lt;/b&gt;" in html
    assert "<b>peace</b>" not in html


def test_header_counters_match_the_manifest(tmp_path):
    manifest_path = build_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["words"].append({
        "word": "Marginal", "translation": "Незначительный", "example": "x",
        "pick": None, "reason": "no usable candidate",
        "candidates": [{"id": "a1", "file": "candidates/verge/a1.jpg", "query": "marginal"}],
    })
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    html = render_page(load_manifest(manifest_path),
                       TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert "2 words" in html
    assert "1 with a proposed image" in html
    assert "1 proposed without" in html


def test_main_writes_the_page_next_to_the_manifest(tmp_path):
    manifest_path = build_manifest(tmp_path)

    assert main([str(manifest_path)]) == 0

    page = tmp_path / "review.html"
    assert page.exists()
    assert "Image review" in page.read_text(encoding="utf-8")


def test_main_reports_a_bad_manifest_without_a_traceback(tmp_path, capsys):
    manifest_path = build_manifest(tmp_path)
    (tmp_path / "candidates" / "verge" / "c5.jpg").unlink()

    assert main([str(manifest_path)]) == 1
    assert "candidate file not found" in capsys.readouterr().err
