from models.factory import make_choice_model

model = make_choice_model(
    model_id=1495623708,
    direction="RU-EN",
    prompt_field="Russian",
    answer_field="English",
    incorrect_prefix="EnglishIncorrect",
    audio_on_front=False,
    name_suffix=" v2",
)
