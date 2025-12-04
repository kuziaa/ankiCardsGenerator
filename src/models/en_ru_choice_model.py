import genanki

model = genanki.Model(
    2343456,
    "EN-RU Choice Model",
    fields=[
        {"name": "English"},
        {"name": "Russian"},
        {"name": "Example"},
        {"name": "Audio"},
        {"name": "RussianIncorrect1"},
        {"name": "RussianIncorrect2"},
        {"name": "RussianIncorrect3"},
        {"name": "RussianIncorrect4"},
        {"name": "Image"},
    ],
    templates=[
        {
            "name": "EN-RU Choice",
            "qfmt": """
                <div class="image-front">
                    {{Image}}
                </div>
                <h2>{{English}}</h2>
                {{Audio}}<br>
                
                <!-- Поле ввода для перевода -->
                <div id="answer-field">
                    {{type:Russian}}
                </div>
                
                <!-- Контейнер для вариантов ответа -->
                <div id="choices-container" style="margin: 20px 0;">
                    <button class="choice-btn" data-answer="{{Russian}}">{{Russian}}</button>
                    <button class="choice-btn" data-answer="{{RussianIncorrect1}}">{{RussianIncorrect1}}</button>
                    <button class="choice-btn" data-answer="{{RussianIncorrect2}}">{{RussianIncorrect2}}</button>
                    <button class="choice-btn" data-answer="{{RussianIncorrect3}}">{{RussianIncorrect3}}</button>
                    <button class="choice-btn" data-answer="{{RussianIncorrect4}}">{{RussianIncorrect4}}</button>
                </div>
                
                <script>
                // Функция для перемешивания массива
                function shuffleArray(array) {
                    for (let i = array.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [array[i], array[j]] = [array[j], array[i]];
                    }
                    return array;
                }
                
                // Перемешиваем кнопки после полной загрузки карточки
                function shuffleButtons() {
                    const container = document.getElementById('choices-container');
                    if (container) {
                        const buttons = Array.from(container.getElementsByClassName('choice-btn'));
                        
                        // Удаляем все кнопки
                        while (container.firstChild) {
                            container.removeChild(container.firstChild);
                        }
                        
                        // Перемешиваем и добавляем обратно
                        shuffleArray(buttons).forEach(btn => container.appendChild(btn));
                    }
                }
                
                // Пытаемся перемешать при загрузке DOM
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', shuffleButtons);
                } else {
                    shuffleButtons();
                }
                
                // Обработчики событий для кнопок выбора
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
            </script>
            """,
            "afmt": """
                <div class="image-back">
                    {{Image}}
                </div>
                <h2>{{English}}</h2>
                {{Audio}}<br>
                          
                <div id="answer-field">
                    {{type:Russian}}
                </div>
                
                <hr id=answer>
                
                {{Example}}
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