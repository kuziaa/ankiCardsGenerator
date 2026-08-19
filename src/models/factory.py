"""Factory for the mirrored typing/choice card models.

The EN-RU and RU-EN variants of each model differ only in model id, direction
name, prompt/answer fields, distractor field prefix and audio placement -
everything else used to be copy-paste. Model ids and field lists are frozen:
changing them breaks note types in existing Anki collections.
"""

import genanki

# v1 note-type ids, retired by the v2 migration - never reuse
RETIRED_MODEL_IDS = frozenset({73727116, 4392726, 2343456, 23436536, 234556757})

CARD_CSS = """\
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }"""

CHOICE_WIDGET_CSS = """\
        .choice-btn {
            margin: 5px;
            padding: 10px 15px;
            font-size: 16px;
            cursor: pointer;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 5px;
            transition: background-color 0.3s;
        }

        .choice-btn:hover {
            background-color: #e0e0e0;
        }

        #answer-field {
            margin: 20px 0;
        }

        #answer-field input {
            font-size: 18px;
            padding: 8px;
            width: 300px;
            text-align: center;
        }"""

IMAGE_CSS = """\
        /* Limit size and blur image on front side */
        .image-front img {
            filter: blur(8px);
            transition: filter 0.5s ease;
            max-width: 300px;
            max-height: 200px;
            width: auto;
            height: auto;
            margin: 0 auto;
            display: block;
        }

        /* Limit size and normal image on back side */
        .image-back img {
            filter: none;
            max-width: 300px;
            max-height: 200px;
            width: auto;
            height: auto;
            margin: 0 auto;
            display: block;
        }"""

TYPING_CSS = "\n" + CARD_CSS + "\n\n" + IMAGE_CSS + "\n    "
CHOICE_CSS = "\n" + CARD_CSS + "\n\n" + CHOICE_WIDGET_CSS + "\n\n" + IMAGE_CSS + "\n    "

_TYPING_QFMT = """
                <div class="image-front">
                    {{Image}}
                </div>
                <h2>{{__PROMPT__}}</h2>
                {{Audio}}<br><br><br>
                {{type:__ANSWER__}}
            """

_TYPING_AFMT = """
                <div class="image-back">
                    {{Image}}
                </div>
                <h2>{{__PROMPT__}}</h2>
                __AUDIO_LINE__
                {{type:__ANSWER__}}

                <hr id=answer>
                {{Example}}
                {{ExampleAudio}}
            """

_CHOICE_SCRIPT = """<script>
                // Function to shuffle array
                function shuffleArray(array) {
                    for (let i = array.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [array[i], array[j]] = [array[j], array[i]];
                    }
                    return array;
                }

                // Shuffle buttons after full card load
                function shuffleButtons() {
                    const container = document.getElementById('choices-container');
                    if (container) {
                        const buttons = Array.from(container.getElementsByClassName('choice-btn'));

                        // Remove all buttons
                        while (container.firstChild) {
                            container.removeChild(container.firstChild);
                        }

                        // Shuffle and add back
                        shuffleArray(buttons).forEach(btn => container.appendChild(btn));
                    }
                }

                // Try to shuffle on DOM load
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', shuffleButtons);
                } else {
                    shuffleButtons();
                }

                // Click handlers for choice buttons
                document.addEventListener('click', function(e) {
                    if (e.target.classList.contains('choice-btn')) {
                        const answerInput = document.querySelector('#answer-field input');
                        if (answerInput) {
                            answerInput.value = e.target.getAttribute('data-answer');
                            // Trigger input event for Anki
                            answerInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                });
            </script>"""

_CHOICE_QFMT = """
                <div class="image-front">
                    {{Image}}
                </div>
                <h2>{{__PROMPT__}}</h2>
                __AUDIO_FRONT__

                <!-- Answer input field -->
                <div id="answer-field">
                    {{type:__ANSWER__}}
                </div>

                <!-- Answer choices container -->
                <div id="choices-container" style="margin: 20px 0;">
                    <button class="choice-btn" data-answer="{{__ANSWER__}}">{{__ANSWER__}}</button>
                    <button class="choice-btn" data-answer="{{__INC__1}}">{{__INC__1}}</button>
                    <button class="choice-btn" data-answer="{{__INC__2}}">{{__INC__2}}</button>
                    <button class="choice-btn" data-answer="{{__INC__3}}">{{__INC__3}}</button>
                    <button class="choice-btn" data-answer="{{__INC__4}}">{{__INC__4}}</button>
                </div>

                __SCRIPT__
            """

_CHOICE_AFMT = """
                <div class="image-back">
                    {{Image}}
                </div>
                <h2>{{__PROMPT__}}</h2>
                __AUDIO_AFTER_HEADING__
                <div id="answer-field">
                    {{type:__ANSWER__}}
                </div>

                <hr id=answer>
                __AUDIO_AFTER_HR__
                {{Example}}
                {{ExampleAudio}}
            """


def _render(template: str, mapping: dict) -> str:
    """Substitute sentinel tokens; a None value removes the token's whole line."""
    out = template
    for token, value in mapping.items():
        if value is None:
            out = "\n".join(line for line in out.split("\n") if token not in line)
        else:
            out = out.replace(token, value)
    return out


def make_typing_model(model_id: int, direction: str, prompt_field: str,
                      answer_field: str, audio_in_answer: bool,
                      name_suffix: str = "") -> genanki.Model:
    """Typing card: prompt on the front, the answer is typed in.

    Audio is always on the front; audio_in_answer controls the back side.
    """
    mapping = {
        "__PROMPT__": prompt_field,
        "__ANSWER__": answer_field,
        "__AUDIO_LINE__": "{{Audio}}<br><br><br>" if audio_in_answer else None,
    }
    return genanki.Model(
        model_id,
        f"{direction} Typing Model{name_suffix}",
        fields=[
            {"name": "English"},
            {"name": "Russian"},
            {"name": "Example"},
            {"name": "Audio"},
            {"name": "Image"},
            {"name": "ExampleAudio"},
        ],
        templates=[
            {
                "name": f"{direction} Typing",
                "qfmt": _render(_TYPING_QFMT, mapping),
                "afmt": _render(_TYPING_AFMT, mapping),
            }
        ],
        css=TYPING_CSS,
    )


def make_choice_model(model_id: int, direction: str, prompt_field: str,
                      answer_field: str, incorrect_prefix: str,
                      audio_on_front: bool, name_suffix: str = "") -> genanki.Model:
    """Multiple-choice card with shuffled answer buttons.

    audio_on_front=False keeps the pronunciation off the question side (it
    would give the answer away) and plays it after the answer field instead.
    """
    mapping = {
        "__PROMPT__": prompt_field,
        "__ANSWER__": answer_field,
        "__INC__": incorrect_prefix,
        "__SCRIPT__": _CHOICE_SCRIPT,
        "__AUDIO_FRONT__": "{{Audio}}<br>" if audio_on_front else None,
        "__AUDIO_AFTER_HEADING__": "{{Audio}}<br>" if audio_on_front else None,
        "__AUDIO_AFTER_HR__": None if audio_on_front else "{{Audio}}<br>",
    }
    return genanki.Model(
        model_id,
        f"{direction} Choice Model{name_suffix}",
        fields=[
            {"name": "English"},
            {"name": "Russian"},
            {"name": "Example"},
            {"name": "Audio"},
            {"name": f"{incorrect_prefix}1"},
            {"name": f"{incorrect_prefix}2"},
            {"name": f"{incorrect_prefix}3"},
            {"name": f"{incorrect_prefix}4"},
            {"name": "Image"},
            {"name": "ExampleAudio"},
        ],
        templates=[
            {
                "name": f"{direction} Choice",
                "qfmt": _render(_CHOICE_QFMT, mapping),
                "afmt": _render(_CHOICE_AFMT, mapping),
            }
        ],
        css=CHOICE_CSS,
    )
