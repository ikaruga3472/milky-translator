import os
from typing import Optional

from google import genai
from google.genai import types

from providers.base import Message, TranslationError


class GeminiProvider:
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise TranslationError("GEMINI_API_KEY가 설정되지 않았습니다.")

        self.client = genai.Client(api_key=api_key)

    def generate(
        self,
        model: str,
        messages: list[Message],
        level: Optional[str] = None,
    ) -> str:
        contents, config = self._build_request(model, messages, level)

        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            translated_text = response.text if response else None
            if not translated_text:
                raise TranslationError("번역 결과가 비어 있습니다.")
            return translated_text
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError("Gemini 번역 요청 중 오류가 발생했습니다.") from exc

    @staticmethod
    def _build_request(
        model: str,
        messages: list[Message],
        level: Optional[str],
    ) -> tuple[list[types.Content], types.GenerateContentConfig]:
        system_messages = []
        contents = []

        for message in messages:
            if message["role"] == "system":
                system_messages.append(message["content"])
                continue

            role = "model" if message["role"] == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=message["content"])],
                )
            )

        config_kwargs = {}
        if system_messages:
            config_kwargs["system_instruction"] = "\n\n".join(system_messages)

        if model in {"gemini-3-pro-preview", "gemini-3-flash-preview"}:
            thinking_config = types.ThinkingConfig(thinking_level=level or "minimal")
        else:
            thinking_config = types.ThinkingConfig(thinking_budget=-1)

        config = types.GenerateContentConfig(
            thinking_config=thinking_config,
            **config_kwargs,
        )
        return contents, config
