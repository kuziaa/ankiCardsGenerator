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


_SCRAMBLE_QFMT = """
                <div class="card scramble">
                    <div class="image-front">
                        {{Image}}
                    </div>
                    
                    <div class="question-text">{{Russian}}</div>
                    {{Audio}}<br>
                    
                    <!-- Input field container -->
                    <div class="input-container">
                        <!-- Answer input field -->
                        <div id="answer-field">
                            {{type:English}}
                        </div>
                    </div>
                    
                    <!-- Shuffled English word letter buttons container -->
                    <div id="letters-container" class="letters-container">
                        <!-- Letters will be added by script -->
                    </div>
                    
                    <!-- Error counter -->
                    <div id="error-counter" class="error-counter">
                        Errors: <span id="error-count">0</span>
                    </div>
                </div>
                
                <script>
                // Function to shuffle array
                function shuffleArray(array) {
                    const newArray = [...array];
                    for (let i = newArray.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
                    }
                    return newArray;
                }
                
                // Function to get next expected character based on current input
                function getNextExpectedChar() {
                    const input = document.querySelector('#answer-field input');
                    const correctWord = "{{English}}";
                    if (!input) return null;
                    
                    const currentInput = input.value;
                    return correctWord[currentInput.length];
                }
                
                // Function to check if character is the next correct one
                function isNextCorrectChar(char) {
                    const expectedChar = getNextExpectedChar();
                    return char === expectedChar;
                }
                
                // Function to update button states (not used anymore, kept for compatibility)
                function updateButtonStates() {
                    // This function is no longer used - button marking logic
                    // is implemented in click handler and input event handler
                }
                
                // Function to increment error counter
                function incrementErrorCounter() {
                    const errorCountElement = document.getElementById('error-count');
                    if (errorCountElement) {
                        errorCountElement.textContent = parseInt(errorCountElement.textContent) + 1;
                    }
                }
                
                // Function to block incorrect keyboard input
                function setupInputValidation() {
                    const input = document.querySelector('#answer-field input');
                    if (!input) return;
                    
                    let isKeyboardInput = false;  // Flag to track input source
                    
                    input.addEventListener('keydown', function(e) {
                        // Allow special keys (Backspace, Tab, arrows, etc.)
                        if (e.key.length > 1 || e.ctrlKey || e.metaKey) {
                            return;
                        }
                        
                        const correctWord = "{{English}}";
                        const currentValue = this.value;
                        const nextChar = correctWord[currentValue.length];
                        
                        // If input char doesn't match expected, block input and increment error counter
                        if (!nextChar || e.key !== nextChar) {
                            e.preventDefault();
                            // Increment error counter on wrong keyboard input
                            incrementErrorCounter();
                        } else {
                            // Mark that input is from keyboard
                            isKeyboardInput = true;
                        }
                    });
                    
                    // Handler to mark button on keyboard input
                    input.addEventListener('input', function(e) {
                        // Process ONLY on keyboard input, not on mouse click
                        if (isKeyboardInput) {
                            // Mark last entered character
                            const buttons = document.querySelectorAll('.letter-btn');
                            const lastChar = this.value[this.value.length - 1];
                            
                            if (lastChar) {
                                // Find first NON-marked button with this character and mark it
                                let found = false;
                                buttons.forEach(button => {
                                    if (!found) {
                                        const buttonChar = button.textContent === '␣' ? ' ' : button.textContent;
                                        if (buttonChar === lastChar && !button.disabled) {
                                            // Mark first available button with this character
                                            button.style.backgroundColor = '#888';
                                            button.disabled = true;
                                            found = true;
                                        }
                                    }
                                });
                            }
                            isKeyboardInput = false;
                        }
                    });
                }
                
                // Function to create letter buttons
                function createLetterButtons() {
                    const englishWord = "{{English}}";
                    const container = document.getElementById('letters-container');
                    
                    // Clear container
                    container.innerHTML = '';
                    
                    // Split word into characters (including spaces) and shuffle
                    const characters = englishWord.split('');
                    const shuffledCharacters = shuffleArray(characters);
                    
                    // Create buttons for each character
                    shuffledCharacters.forEach(char => {
                        const button = document.createElement('button');
                        button.className = 'letter-btn';
                        
                        // Use special display for space
                        if (char === ' ') {
                            button.textContent = '␣';  // Space character
                            button.title = 'Space';
                            button.classList.add('space-btn');
                        } else {
                            button.textContent = char;
                        }
                        
                        button.style.cssText = `
                            margin: 3px;
                            padding: 10px 15px;
                            font-size: 18px;
                            cursor: pointer;
                            background-color: #4CAF50;
                            color: black;
                            border: none;
                            border-radius: 5px;
                            min-width: 40px;
                            transition: all 0.3s;
                        `;
                        
                        button.addEventListener('click', function() {
                            const input = document.querySelector('#answer-field input');
                            if (input) {
                                // Check if clicked character is the next expected one
                                if (isNextCorrectChar(char)) {
                                    // Add character to current value
                                    // For space add normal space, for others add character as is
                                    input.value += (char === ' ') ? ' ' : char;
                                    
                                    // Mark clicked button with gray color
                                    this.style.backgroundColor = '#888';
                                    this.disabled = true;
                                    
                                    // Do NOT call dispatchEvent - this prevents double marking
                                } else {
                                    // Increment error counter on wrong button click
                                    incrementErrorCounter();
                                }
                            }
                        });
                        
                        container.appendChild(button);
                    });
                }
                
                // Initialize on card load
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        createLetterButtons();
                        setupInputValidation();
                    });
                } else {
                    createLetterButtons();
                    setupInputValidation();
                }
                </script>
            """

_SCRAMBLE_AFMT = """
                <div class="card scramble">
                    <div class="image-back">
                        {{Image}}
                    </div>
                    
                    <h2>{{Russian}}</h2><br>
                    {{Audio}}<br>
                    
                    <!-- Check entered answer -->
                    {{type:English}}
                    
                    <hr id="answer">
                    
                    <div class="example-text">{{Example}}</div>
                    {{ExampleAudio}}
                </div>
            """

SCRAMBLE_WIDGET_CSS = """        .question-text {
            font-size: 24px;
            font-weight: bold;
            margin: 15px 0;
            color: #333;
        }

        .example-text {
            font-style: italic;
            margin: 20px 0;
            color: #555;
            padding: 0 10px;
            text-align: center;
        }

        .input-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }

        /* Scoped: the Choice widget styles the same ids globally */
        .scramble #answer-field {
            margin: 0;
            max-width: 400px;
            text-align: center;
        }

        .scramble #answer-field input {
            font-size: 18px;
            padding: 12px;
            width: 100%;
            text-align: center;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            box-sizing: border-box;
        }

        .letters-container {
            margin: 20px 0;
            min-height: 50px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
        }

        .error-counter {
            margin: 15px 0;
            font-size: 18px;
            font-weight: bold;
        }

        #error-count {
            color: red;
            font-size: 20px;
        }

        .letter-btn {
            color: black;
            font-weight: bold;
            margin: 3px;
            padding: 10px 15px;
            font-size: 18px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
            min-width: 40px;
            transition: all 0.3s;
            background-color: #4CAF50;
        }

        .letter-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .letter-btn:disabled {
            background-color: #888;
            cursor: default;
            transform: none;
            box-shadow: none;
        }"""


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
