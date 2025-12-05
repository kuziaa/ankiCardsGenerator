import genanki

model = genanki.Model(
    234556757,  # Уникальный ID модели
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
                    
                    <!-- Контейнер для поля ввода -->
                    <div class="input-container">
                        <!-- Поле ввода для ответа -->
                        <div id="answer-field">
                            {{type:English}}
                        </div>
                    </div>
                    
                    <!-- Контейнер для перемешанных букв английского слова -->
                    <div id="letters-container" class="letters-container">
                        <!-- Буквы будут добавлены скриптом -->
                    </div>
                </div>
                
                <script>
                // Функция для перемешивания массива
                function shuffleArray(array) {
                    const newArray = [...array];
                    for (let i = newArray.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
                    }
                    return newArray;
                }
                
                // Функция для получения следующей ожидаемой буквы на основе текущего ввода
                function getNextExpectedChar() {
                    const input = document.querySelector('#answer-field input');
                    const correctWord = "{{English}}";
                    if (!input) return null;
                    
                    const currentInput = input.value;
                    return correctWord[currentInput.length];
                }
                
                // Функция для проверки, является ли буква следующей правильной
                function isNextCorrectChar(char) {
                    const expectedChar = getNextExpectedChar();
                    return char === expectedChar;
                }
                
                // Функция для проверки, была ли буква уже использована
                function isCharUsed(char) {
                    const input = document.querySelector('#answer-field input');
                    if (!input) return false;
                    
                    const currentInput = input.value;
                    const correctWord = "{{English}}";
                    
                    // Считаем, сколько раз эта буква уже встречается в введенном тексте
                    const usedCount = (currentInput.match(new RegExp(char, 'g')) || []).length;
                    
                    // Считаем, сколько раз эта буква должна встречаться в правильном слове
                    const requiredCount = (correctWord.match(new RegExp(char, 'g')) || []).length;
                    
                    return usedCount >= requiredCount;
                }
                
                // Функция для обновления состояния кнопок при вводе с клавиатуры
                function updateButtonStates() {
                    const input = document.querySelector('#answer-field input');
                    const correctWord = "{{English}}";
                    if (!input) return;
                    
                    const currentInput = input.value;
                    
                    // Для каждой буквы в правильном слове проверяем, была ли она уже введена
                    const buttons = document.querySelectorAll('.letter-btn');
                    buttons.forEach(button => {
                        const buttonChar = button.textContent === '␣' ? ' ' : button.textContent;
                        
                        // Определяем, была ли эта буква уже использована
                        if (isCharUsed(buttonChar)) {
                            button.style.backgroundColor = '#888';
                            button.disabled = true;
                        } else {
                            // Восстанавливаем исходный цвет
                            if (button.classList.contains('space-btn')) {
                                button.style.backgroundColor = '#FF9800';
                            } else {
                                button.style.backgroundColor = '#4CAF50';
                            }
                            button.disabled = false;
                        }
                    });
                }
                
                // Функция для блокировки неправильного ввода с клавиатуры
                function setupInputValidation() {
                    const input = document.querySelector('#answer-field input');
                    if (!input) return;
                    
                    input.addEventListener('keydown', function(e) {
                        // Разрешаем служебные клавиши (Backspace, Tab, стрелки и т.д.)
                        if (e.key.length > 1 || e.ctrlKey || e.metaKey) {
                            return;
                        }
                        
                        const correctWord = "{{English}}";
                        const currentValue = this.value;
                        const nextChar = correctWord[currentValue.length];
                        
                        // Если вводимый символ не соответствует ожидаемому, блокируем ввод
                        if (!nextChar || e.key !== nextChar) {
                            e.preventDefault();
                        }
                    });
                    
                    // Обработчик для обновления состояния кнопок при вводе
                    input.addEventListener('input', function(e) {
                        updateButtonStates();
                    });
                }
                
                // Функция для создания кнопок с буквами
                function createLetterButtons() {
                    const englishWord = "{{English}}";
                    const container = document.getElementById('letters-container');
                    
                    // Очищаем контейнер
                    container.innerHTML = '';
                    
                    // Разбиваем слово на символы (включая пробелы) и перемешиваем
                    const characters = englishWord.split('');
                    const shuffledCharacters = shuffleArray(characters);
                    
                    // Создаем кнопки для каждого символа
                    shuffledCharacters.forEach(char => {
                        const button = document.createElement('button');
                        button.className = 'letter-btn';
                        
                        // Для пробела используем специальное отображение
                        if (char === ' ') {
                            button.textContent = '␣';  // Символ пробела
                            button.title = 'Пробел';
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
                                // Проверяем, является ли нажатая буква следующей ожидаемой
                                // и не была ли она уже использована
                                if (isNextCorrectChar(char) && !isCharUsed(char)) {
                                    // Добавляем символ к текущему значению
                                    // Для пробела добавляем обычный пробел, для остальных - символ как есть
                                    input.value += (char === ' ') ? ' ' : char;
                                    // Активируем событие для Anki
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    
                                    // Обновляем состояние кнопок
                                    updateButtonStates();
                                } 
                            }
                        });
                        
                        container.appendChild(button);
                    });
                }
                
                // Инициализация при загрузке карточки
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
                    
                    <!-- Проверка введенного ответа -->
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
        
        /* Стили для поля ввода */
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
        
        /* Контейнер для букв */
        .letters-container {
            margin: 20px 0;
            min-height: 50px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        /* Базовые стили для кнопок букв */
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
        }
        
        /* Стили для обычных букв */
        .letter-btn:not(.space-btn) {
            background-color: #4CAF50;
        }
        
        /* Стили для кнопки пробела */
        .letter-btn.space-btn {
            background-color: #FF9800;
        }
        
        /* Стили для кнопок букв при наведении */
        .letter-btn:hover:not(:disabled) {
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* Стили для отключенных кнопок */
        .letter-btn:disabled {
            background-color: #888;
            cursor: default;
            transform: none;
            box-shadow: none;
        }
        
        /* Ограничение размера и размытие изображения на лицевой стороне */
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
        
        /* Ограничение размера и нормальное изображение на оборотной стороне */
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
