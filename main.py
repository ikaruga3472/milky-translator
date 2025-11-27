from flask import Flask, render_template, request

app = Flask(__name__)

LANG_OPTIONS = [
    ("ko", "한국어"),
    ("en", "English"),
    ("ja", "日本語"),
]


def translate_text(text: str, source: str, target: str) -> str:
    # TODO: Replace with real AI translation (e.g., call your model or API)
    return f"[MOCK] {text} ({source} → {target})"


@app.route("/", methods=["GET", "POST"])
def index():
    translation = None
    error = None
    text = ""
    source_language = "ko"
    target_language = "en"
    target_label = "English"

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        source_language = request.form.get("source_language", source_language)
        target_language = request.form.get("target_language", target_language)

        if not text:
            error = "번역할 문장을 입력해주세요."
        elif source_language == target_language:
            error = "출발어와 도착어가 동일합니다."
        else:
            translation = translate_text(text, source_language, target_language)

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
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
