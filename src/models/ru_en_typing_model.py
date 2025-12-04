import genanki

model = genanki.Model(
    4392726,
    "RU-EN Typing Model",
    fields=[
        {"name": "English"},
        {"name": "Russian"},
        {"name": "Example"},
        {"name": "Audio"},
        {"name": "Image"},
    ],
    templates=[
        {
            "name": "RU-EN Typing",
            "qfmt": """
                <div class="image-front">
                    {{Image}}
                </div>
                <h2>{{Russian}}</h2>
                {{type:English}}
            """,
            "afmt": """
                <div class="image-back">
                    {{Image}}
                </div>
                <h2>{{Russian}}</h2>
                {{Audio}}<br><br><br>
                {{type:English}}
                
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