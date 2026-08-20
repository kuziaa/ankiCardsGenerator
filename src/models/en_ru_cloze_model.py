import genanki

from models.factory import CARD_CSS

CLOZE_CSS = """\
        .cloze {
            font-weight: bold;
            color: #2a7ae2;
        }"""

model = genanki.Model(
    1795263408,
    "EN-RU Cloze",
    model_type=genanki.Model.CLOZE,
    fields=[
        {"name": "English"},
        {"name": "Text"},
        {"name": "Hint"},
        {"name": "ExampleAudio"},
    ],
    templates=[
        {
            "name": "EN-RU Cloze",
            "qfmt": """
                {{cloze:Text}}
                <br><br>
                {{type:cloze:Text}}
                <br>
                {{hint:Hint}}
            """,
            "afmt": """
                {{cloze:Text}}
                <hr id=answer>
                {{type:cloze:Text}}
                <br>
                {{Hint}}
                {{ExampleAudio}}
            """,
        }
    ],
    css="\n" + CARD_CSS + "\n\n" + CLOZE_CSS + "\n    ",
)
