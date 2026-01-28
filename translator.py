import os
from typing import Optional

from google import genai
from google.genai import types


DEFAULT_PROMPT_TEMPLATE = ('''# Role
You are a professional translator.

# Task
Translate the following text from {{source}} into {{target}}.

# Constraints
1. **Accuracy**: Preserve the original meaning and nuance accurately.
2. **No Fluff**: Output ONLY the translated text. Do not include notes, explanations, or conversational fillers (e.g., "Here is the translation").

# Input Data
- Source Language: {{source}}
- Target Language: {{target}}
- Text to Translate:
"""
{{text}}
"""
'''
)


class TranslationError(Exception):
    """Raised when translation fails or configuration is missing."""


def _load_env_file() -> None:
    """Best-effort .env loader without hard dependency on python-dotenv."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _build_generate_config(model: str, level: str) -> Optional[types.GenerateContentConfig]:
    if model == "gemini-3-pro-preview" or model == 'gemini-3-flash-preview':
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=level),
        )
    else:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
        )



def _format_prompt(
    template: Optional[str],
    *,
    source: str,
    target: str,
    text: str,
) -> str:
    """Fill the prompt template with user text and language settings."""
    resolved = template or DEFAULT_PROMPT_TEMPLATE
    return (
        resolved.replace("{{source}}", source)
        .replace("{{target}}", target)
        .replace("{{text}}", text)
        .strip()
    )


class GeminiTranslator:
    def __init__(self, default_model: str = "gemini-flash-latest", api_key: Optional[str] = None) -> None:
        _load_env_file()
        resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            raise TranslationError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=resolved_api_key)
        self.default_model = default_model

    # 번역
    def translate(
        self,
        text: str,
        source: str,
        target: str,
        model: Optional[str] = None,
        level: Optional[str] = None,
        api_key_override: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> str:
        selected_model = model or self.default_model
        prompt = _format_prompt(
            prompt_template,
            source=source,
            target=target,
            text=text,
        )

        try:
            client = self.client
            if api_key_override:
                client = genai.Client(api_key=api_key_override)

            generate_config = _build_generate_config(selected_model, level)

            translated_text = client.models.generate_content(
                model=selected_model,
                contents=prompt,
                config=generate_config
            )

            if not translated_text:
                raise TranslationError("번역 결과가 비어 있습니다.")
            return translated_text
        except TranslationError:
            raise
        except Exception as exc:
            print(exc)
            raise TranslationError("번역 요청 중 오류가 발생했습니다.") from exc


def create_translator(default_model: str = "gemini-flash-latest", api_key: Optional[str] = None) -> GeminiTranslator:
    return GeminiTranslator(default_model=default_model, api_key=api_key)
