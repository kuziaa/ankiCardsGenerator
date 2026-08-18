from models.factory import make_choice_model

model = make_choice_model(
    model_id=2343456,
    direction="EN-RU",
    prompt_field="English",
    answer_field="Russian",
    incorrect_prefix="RussianIncorrect",
    audio_on_front=True,
)
