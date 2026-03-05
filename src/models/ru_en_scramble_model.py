import genanki

model = genanki.Model(
    234556757,  # Unique model ID
    "EN-RU Scramble Model",
    fields=[
        {"name": "English"},
        {"name": "Russian"},
        {"name": "Example"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[
        {
            "name": "RU-EN Scramble",
            "qfmt": """
                <div class="card">
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
            """,
            "afmt": """
                <div class="card">
                    <div class="image-back">
                        {{Image}}
                    </div>
                    
                    <h2>{{Russian}}</h2><br>
                    {{Audio}}<br>
                    
                    <!-- Check entered answer -->
                    {{type:English}}
                    
                    <hr id="answer">
                    
                    <div class="example-text">{{Example}}</div>
                </div>
            """,
        }
    ],
    css="""
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
        
        .question-text {
            font-size: 24px;
            font-weight: bold;
            margin: 15px 0;
            color: #333;
        }
        
        .example-text {
            font-style: italic;
            margin: 20px 0;
            color: #555;
            text-align: left;
            padding: 0 10px;
            text-align: center;
        }
        
        /* Контейнер для поля ввода */
        .input-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }
        
        /* Styles for input field */
        #answer-field {
            max-width: 400px;
            text-align: center;
        }
        
        #answer-field input {
            font-size: 18px;
            padding: 12px;
            width: 100%;
            text-align: center;
            border: 2px solid #4CAF50;
            border-radius: 5px;
            box-sizing: border-box;
        }
        
        /* Letter buttons container */
        .letters-container {
            margin: 20px 0;
            min-height: 50px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        /* Error counter styling */
        .error-counter {
            margin: 15px 0;
            font-size: 18px;
            font-weight: bold;
        }
        
        #error-count {
            color: red;
            font-size: 20px;
        }
        
        /* Styles for letter buttons */
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
        
        /* Styles for letter buttons on hover */
        .letter-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* Styles for disabled buttons */
        .letter-btn:disabled {
            background-color: #888;
            cursor: default;
            transform: none;
            box-shadow: none;
        }
        
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
        }
    """
)
