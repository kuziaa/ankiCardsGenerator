import csv

from utils.csv_validator import EXPECTED_COLUMNS, validate_csv


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def valid_row(english="dojo", russian="додзё"):
    return {
        "english": english,
        "russian": russian,
        "example": "She trained in the dojo.",
        "incorrectEnVariant1": "mojo",
        "incorrectEnVariant2": "doge",
        "incorrectEnVariant3": "dose",
        "incorrectEnVariant4": "doze",
        "incorrectRuVariant1": "зал ожидания",
        "incorrectRuVariant2": "игровая площадка",
        "incorrectRuVariant3": "спальная комната",
        "incorrectRuVariant4": "офис",
    }


def test_validate_csv_accepts_example_file():
    report = validate_csv("src/resources/cards.example.csv")

    assert report.ok
    assert report.row_count == 12
    assert report.errors == []


def test_validate_csv_reports_missing_file(tmp_path):
    report = validate_csv(str(tmp_path / "missing.csv"))

    assert not report.ok
    assert report.errors == [f"file not found: {tmp_path / 'missing.csv'}"]


def test_validate_csv_reports_duplicate_word_and_answer_distractor(tmp_path):
    csv_path = tmp_path / "bad.csv"
    first = valid_row()
    second = valid_row(english="Dojo", russian="додзё")
    second["incorrectEnVariant1"] = "dojo"
    write_csv(csv_path, [first, second])

    report = validate_csv(str(csv_path))

    assert not report.ok
    assert any("EN distractor equals the answer" in error for error in report.errors)
    assert any("duplicate word 'Dojo'" in error for error in report.errors)


def test_validate_csv_reports_wrong_field_count(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        ",".join(EXPECTED_COLUMNS) + "\nonly,three,fields\n",
        encoding="utf-8",
    )

    report = validate_csv(str(csv_path))

    assert not report.ok
    assert any("3 fields instead of 11" in error for error in report.errors)
