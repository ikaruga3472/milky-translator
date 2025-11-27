from flask import Flask, render_template, request

from translator import TranslationError, create_translator

app = Flask(__name__)

LANG_OPTIONS = [
    ("ko", "한국어"),
    ("en", "English"),
    ("ja", "日本語"),
]

MODEL_OPTIONS = [
    ("gemini-flash-latest", "gemini-flash-latest"),
    ("gemini-3-pro-preview", "gemini-3-pro-preview"),
]
DEFAULT_MODEL = MODEL_OPTIONS[0][0]

translator = None
translator_init_error = None
try:
    translator = create_translator(default_model=DEFAULT_MODEL)
except TranslationError as exc:
    translator_init_error = str(exc)


def translate_text(text: str, source: str, target: str, model: str) -> str:
    if translator is None:
        raise TranslationError(
            translator_init_error or "번역기를 초기화하지 못했습니다. 환경변수를 확인해주세요."
        )
    return translator.translate(text, source, target, model=model)


@app.route("/", methods=["GET", "POST"])
def index():
    translation = None
    error = translator_init_error
    text = ""
    source_language = "ko"
    target_language = "en"
    target_label = "English"
    model = DEFAULT_MODEL

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        source_language = request.form.get("source_language", source_language)
        target_language = request.form.get("target_language", target_language)
        model = request.form.get("model", model)

        if model not in dict(MODEL_OPTIONS):
            model = DEFAULT_MODEL

        if not text:
            error = "번역할 문장을 입력해주세요."
        elif source_language == target_language:
            error = "출발어와 도착어가 동일합니다."
        else:
            try:
                translation = translate_text(text, source_language, target_language, model=model)
            except TranslationError as exc:
                error = str(exc)

    target_label = next((label for code, label in LANG_OPTIONS if code == target_language), target_language)

    return render_template(
        "index.html",
        translation=translation,
        error=error,
        text=text,
        source_language=source_language,
        target_language=target_language,
        target_label=target_label,
        languages=LANG_OPTIONS,
        model=model,
        model_options=MODEL_OPTIONS,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
