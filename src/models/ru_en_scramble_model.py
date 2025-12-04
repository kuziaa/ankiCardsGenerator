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
                    
                    <!-- Контейнер для поля ввода и кнопки перемешивания -->
                    <div class="input-container">
                        <!-- Поле ввода для ответа -->
                        <div id="answer-field">
                            {{type:English}}
                        </div>
                        
                        <!-- Кнопка для перестановки букв -->
                        <button id="shuffle-btn" class="shuffle-button">Перемешать буквы</button>
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
                                // Добавляем символ к текущему значению
                                // Для пробела добавляем обычный пробел, для остальных - символ как есть
                                input.value += (char === ' ') ? ' ' : char;
                                // Активируем событие для Anki
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                
                                // Визуальная обратная связь - кнопка становится неактивной
                                this.style.backgroundColor = '#888';
                                this.style.cursor = 'default';
                                this.disabled = true;
                            }
                        });
                        
                        container.appendChild(button);
                    });
                }
                
                // Функция для сброса кнопок (при перестановке)
                function resetLetterButtons() {
                    const buttons = document.getElementsByClassName('letter-btn');
                    Array.from(buttons).forEach(btn => {
                        // Возвращаем исходный цвет в зависимости от типа кнопки
                        if (btn.classList.contains('space-btn')) {
                            btn.style.backgroundColor = '#FF9800';
                        } else {
                            btn.style.backgroundColor = '#4CAF50';
                        }
                        btn.style.cursor = 'pointer';
                        btn.disabled = false;
                    });
                }
                
                // Инициализация при загрузке карточки
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        createLetterButtons();
                    });
                } else {
                    createLetterButtons();
                }
                
                // Обработчик для кнопки перестановки
                document.addEventListener('click', function(e) {
                    if (e.target.id === 'shuffle-btn') {
                        createLetterButtons();
                        
                        // Сбрасываем поле ввода
                        const input = document.querySelector('#answer-field input');
                        if (input) {
                            input.value = '';
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                });
                
                // Обработчик для очистки поля ввода (двойной клик)
                document.addEventListener('dblclick', function(e) {
                    if (e.target.matches('#answer-field input')) {
                        e.target.value = '';
                        e.target.dispatchEvent(new Event('input', { bubbles: true }));
                        
                        // Сбрасываем кнопки букв
                        resetLetterButtons();
                    }
                });
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
        
        /* Контейнер для поля ввода и кнопки */
        .input-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        /* Стили для поля ввода */
        #answer-field {
            flex: 1;
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
        
        /* Стили для кнопки перемешивания */
        .shuffle-button {
            background-color: #2196F3;
            color: black;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            padding: 12px 20px;
            font-size: 16px;
            white-space: nowrap;
            transition: all 0.3s;
            height: fit-content;
        }
        
        .shuffle-button:hover {
            transform: scale(1.05);
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
