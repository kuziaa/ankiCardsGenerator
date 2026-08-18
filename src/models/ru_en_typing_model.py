from models.factory import make_typing_model

# English audio on the front is intentional: the card doubles as dictation by ear
model = make_typing_model(
    model_id=4392726,
    direction="RU-EN",
    prompt_field="Russian",
    answer_field="English",
    audio_in_answer=False,
)
