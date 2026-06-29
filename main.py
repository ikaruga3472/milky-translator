import os

from flask import Flask, jsonify, render_template, request, redirect, session, url_for

from translator import DEFAULT_PROMPT_TEMPLATE, TranslationError, create_translator

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

LANG_OPTIONS = [
    ("ko", "한국어"),
    ("en", "English"),
    ("ja", "日本語"),
    ("ch", "中國語"),
]

PROVIDER_OPTIONS = [
    ("gemini", "Google Gemini"),
    ("ollama", "Ollama Cloud"),
]

MODEL_OPTIONS = {
    "gemini": [
        ("gemini-3-flash-preview", "gemini-3-flash-preview"),
    ],
    "ollama": [
        ("gemma4:31b", "gemma4:31b"),
    ],
}

THINKING_LEVEL_OPTIONS = [
    ("minimal", "MInimal"),
    ("low", "Low"),
    ("high", "High"),
]
DEFAULT_PROVIDER = PROVIDER_OPTIONS[0][0]
DEFAULT_MODEL = MODEL_OPTIONS[DEFAULT_PROVIDER][0][0]
DEFAULT_LEVEL = THINKING_LEVEL_OPTIONS[0][0]

translator = create_translator()


def _get_app_password() -> str:
    return os.environ.get("FLASK_SECRET_KEY", "")

# 서버 비밀번호가 설정되지 않으면 그냥 통과함
def _is_password_authenticated() -> bool:
    password = _get_app_password()
    if not password:
        return True
    return bool(session.get("password_authenticated"))


@app.before_request
def require_password_auth():
    """Redirect unauthenticated users to /login when a password is configured."""
    # Skip auth for login page and static assets
    if request.endpoint in {"login", "static"}:
        return None

    if bool(_get_app_password()) and not _is_password_authenticated():
        next_path = request.path if request.path != "/login" else url_for("index")
        return redirect(url_for("login", next=next_path))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    password_required = bool(_get_app_password())
    password_authenticated = _is_password_authenticated()
    auth_error = None

    if request.method == "POST" and password_required:
        submitted_password = request.form.get("auth_password", "")
        if submitted_password and submitted_password == _get_app_password():
            session["password_authenticated"] = True
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        auth_error = (
            "비밀번호가 올바르지 않습니다."
            if submitted_password
            else "비밀번호를 입력해주세요."
        )

    if not password_required:
        return redirect(url_for("index"))

    if password_authenticated:
        return redirect(url_for("index"))

    return render_template(
        "login.html",
        auth_error=auth_error,
        password_required=password_required,
    )


def translate_text(
    text: str,
    source: str,
    target: str,
    provider: str,
    model: str,
    level: str,
    prompt_template: str,
) -> str:
    return translator.translate(
        text,
        source,
        target,
        provider=provider,
        model=model,
        level=level,
        prompt_template=prompt_template,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    password_required = bool(_get_app_password())
    password_authenticated = _is_password_authenticated()
    translation = None
    error = None
    text = ""
    source_language = "ko"
    target_language = "en"
    target_label = "English"
    provider = DEFAULT_PROVIDER
    model = DEFAULT_MODEL
    level = DEFAULT_LEVEL
    prompt_template = DEFAULT_PROMPT_TEMPLATE

    if password_required and not password_authenticated:
        return redirect(url_for("login"))

    if request.method == "POST":
        error = None
        text = request.form.get("text", "").strip()
        source_language = request.form.get("source_language", source_language)
        target_language = request.form.get("target_language", target_language)
        provider = request.form.get("provider", provider)
        if provider not in dict(PROVIDER_OPTIONS):
            provider = DEFAULT_PROVIDER

        model = request.form.get("model", MODEL_OPTIONS[provider][0][0])
        level = request.form.get("level", level)
        prompt_template = (
            request.form.get("prompt_template", "").strip()
            or DEFAULT_PROMPT_TEMPLATE
        )

        if model not in dict(MODEL_OPTIONS[provider]):
            model = MODEL_OPTIONS[provider][0][0]

        if not text:
            error = "번역할 내용을 입력해주세요."
        elif source_language == target_language:
            error = "출발어와 도착어가 동일합니다."
        elif (
            provider == "gemini"
            and level == "minimal"
            and model == "gemini-3-pro-preview"
        ):
            error = "Gemini 3 Pro 모델은 Minimal을 지원하지 않습니다."

        else:
            try:
                translation = translate_text(
                    text,
                    source_language,
                    target_language,
                    provider=provider,
                    model=model,
                    level=level,
                    prompt_template=prompt_template,
                )
            except TranslationError as exc:
                error = str(exc)

    target_label = next(
        (label for code, label in LANG_OPTIONS if code == target_language),
        target_language,
    )

    return render_template(
        "index.html",
        translation=translation,
        error=error,
        text=text,
        source_language=source_language,
        target_language=target_language,
        target_label=target_label,
        languages=LANG_OPTIONS,
        provider=provider,
        model=model,
        level=level,
        provider_options=PROVIDER_OPTIONS,
        model_options=[
            (provider_code, code, label)
            for provider_code, models in MODEL_OPTIONS.items()
            for code, label in models
        ],
        thinking_level_options=THINKING_LEVEL_OPTIONS,
        prompt_template=prompt_template,
        password_required=password_required,
    )


@app.get("/prompt-template")
def prompt_template_api():
    return jsonify({"prompt_template": DEFAULT_PROMPT_TEMPLATE})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
