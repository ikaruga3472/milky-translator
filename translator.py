import os
from typing import Optional

from google import genai
from google.genai import types


class TranslationError(Exception):
    """Raised when translation fails or configuration is missing."""


def _load_env_file() -> None:
    """Best-effort .env loader without hard dependency on python-dotenv."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _build_generate_config() -> Optional[types.GenerateContentConfig]:
    """
    Build the GenerateContentConfig with the thinking budget set to -1.

    The API surfaces have changed a few times; we try the documented snake_case
    form first and fall back to camelCase if the installed version expects it.
    """
    try:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(budget_tokens=-1)
        )
    except Exception:
        try:
            return types.GenerateContentConfig(thinkingConfig={"thinkingBudget": -1})
        except Exception:
            return None


class GeminiTranslator:
    def __init__(self, model: str = "gemini-flash-latest") -> None:
        _load_env_file()
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise TranslationError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.generate_config = _build_generate_config()

    def translate(self, text: str, source: str, target: str) -> str:
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=(
                            "You are a translation engine. "
                            "Translate the user text precisely without adding explanations. "
                            f"Source language: {source}\n"
                            f"Target language: {target}\n\n"
                            f"Text:\n{text}"
                        )
                    )
                ],
            ),
        ]

        try:
            stream_kwargs = {
                "model": self.model,
                "contents": contents,
            }
            if self.generate_config is not None:
                stream_kwargs["config"] = self.generate_config

            translated_chunks = []
            for chunk in self.client.models.generate_content_stream(**stream_kwargs):
                if getattr(chunk, "text", None):
                    translated_chunks.append(chunk.text)

            translated_text = "".join(translated_chunks).strip()
            if not translated_text:
                raise TranslationError("번역 결과가 비어 있습니다.")
            return translated_text
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError("번역 요청 중 오류가 발생했습니다.") from exc


def create_translator(model: str = "gemini-flash-latest") -> GeminiTranslator:
    return GeminiTranslator(model=model)
