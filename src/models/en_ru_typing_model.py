from models.factory import make_typing_model

model = make_typing_model(
    model_id=73727116,
    direction="EN-RU",
    prompt_field="English",
    answer_field="Russian",
    audio_in_answer=True,
)
