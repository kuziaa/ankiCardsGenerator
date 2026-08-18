import genanki

from models.factory import CARD_CSS

CLOZE_CSS = """\
        .cloze {
            font-weight: bold;
            color: #2a7ae2;
        }"""

model = genanki.Model(
    1631442296,
    "EN-RU Cloze Model",
    model_type=genanki.Model.CLOZE,
    fields=[
        {"name": "English"},
        {"name": "Text"},
        {"name": "Hint"},
    ],
    templates=[
        {
            "name": "EN-RU Cloze",
            "qfmt": """
                {{cloze:Text}}
                <br><br>
                {{hint:Hint}}
            """,
            "afmt": """
                {{cloze:Text}}
                <hr id=answer>
                {{Hint}}
            """,
        }
    ],
    css="\n" + CARD_CSS + "\n\n" + CLOZE_CSS + "\n    ",
)
