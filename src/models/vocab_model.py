"""The unified vocabulary note type (v4): one note per word, five templates.

Card existence is controlled by gate fields: each template's front is wrapped
in a {{#Gate}}...{{/Gate}} section, so an empty gate renders an empty front
and neither genanki nor Anki generates that card. The gate value itself never
appears on a card. The model id, the 19-field order and the template order
are frozen: changing them corrupts existing Anki collections, because a
card's ord is what binds it to a template.

Template order is the study order Anki shows new cards in: recognition
(choice, scramble) before production (typing). Gate fields keep their own
frozen order, so a template finds its gate by name, not by position.
"""

import genanki

from models.factory import (CARD_CSS, CHOICE_WIDGET_CSS, IMAGE_CSS,
                            SCRAMBLE_WIDGET_CSS, _CHOICE_AFMT, _CHOICE_QFMT,
                            _CHOICE_SCRIPT, _SCRAMBLE_AFMT, _SCRAMBLE_QFMT,
                            _TYPING_AFMT, _TYPING_QFMT, _render)

MODEL_ID = 1868432571
MODEL_NAME = "EN-RU Vocabulary v4"
GATE_ON = "y"
# Order is frozen: card ords in existing collections depend on it
GATE_FIELDS = ["EnRuTyping", "RuEnTyping", "EnRuChoice", "RuEnChoice", "Scramble"]

VOCAB_CSS = ("\n" + CARD_CSS + "\n\n" + CHOICE_WIDGET_CSS + "\n\n" + IMAGE_CSS
             + "\n\n" + SCRAMBLE_WIDGET_CSS + "\n    ")


def _gated(qfmt: str, gate: str) -> str:
    """Wrap a front in a gate section: an empty gate means no card."""
    return "{{#%s}}\n%s\n{{/%s}}" % (gate, qfmt, gate)


def _service_field(name: str, description: str) -> dict:
    # collapsed/description are best-effort editor hints (Anki 23.10+)
    return {"name": name, "collapsed": True, "description": description}


_FIELDS = (
    [{"name": name} for name in
     ("English", "Russian", "Example", "Audio", "Image", "ExampleAudio")]
    + [_service_field(f"RussianIncorrect{i}", "EN-RU Choice distractor")
       for i in range(1, 5)]
    + [_service_field(f"EnglishIncorrect{i}", "RU-EN Choice distractor")
       for i in range(1, 5)]
    + [_service_field(gate, "y = this card exists") for gate in GATE_FIELDS]
)

_TEMPLATES = [
    {
        "name": "EN-RU Choice",
        "qfmt": _gated(_render(_CHOICE_QFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__INC__": "RussianIncorrect", "__SCRIPT__": _CHOICE_SCRIPT,
            "__AUDIO_FRONT__": "{{Audio}}<br>"}), "EnRuChoice"),
        "afmt": _render(_CHOICE_AFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__AUDIO_AFTER_HEADING__": "{{Audio}}<br>",
            "__AUDIO_AFTER_HR__": None}),
    },
    {
        "name": "RU-EN Choice",
        "qfmt": _gated(_render(_CHOICE_QFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__INC__": "EnglishIncorrect", "__SCRIPT__": _CHOICE_SCRIPT,
            "__AUDIO_FRONT__": None}), "RuEnChoice"),
        "afmt": _render(_CHOICE_AFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__AUDIO_AFTER_HEADING__": None,
            "__AUDIO_AFTER_HR__": "{{Audio}}<br>"}),
    },
    {
        "name": "RU-EN Scramble",
        "qfmt": _gated(_SCRAMBLE_QFMT, "Scramble"),
        "afmt": _SCRAMBLE_AFMT,
    },
    {
        "name": "RU-EN Typing",
        "qfmt": _gated(_render(_TYPING_QFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English"}), "RuEnTyping"),
        "afmt": _render(_TYPING_AFMT, {
            "__PROMPT__": "Russian", "__ANSWER__": "English",
            "__AUDIO_LINE__": None}),
    },
    {
        "name": "EN-RU Typing",
        "qfmt": _gated(_render(_TYPING_QFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian"}), "EnRuTyping"),
        "afmt": _render(_TYPING_AFMT, {
            "__PROMPT__": "English", "__ANSWER__": "Russian",
            "__AUDIO_LINE__": "{{Audio}}<br><br><br>"}),
    },
]

model = genanki.Model(
    MODEL_ID,
    MODEL_NAME,
    fields=_FIELDS,
    templates=_TEMPLATES,
    css=VOCAB_CSS,
)
