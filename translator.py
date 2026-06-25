import os
from typing import Optional

from google import genai
from google.genai import types


CHATML_START_MARKER = "<|im_start|>"
CHATML_END_MARKER = "<|im_end|>"
ROLE_MAP = {
    "system": "system",
    "sys": "system",
    "user": "user",
    "human": "user",
    "assistant": "assistant",
    "bot": "assistant",
    "char": "assistant",
    "model": "assistant",
}


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


def _build_generate_config(
    model: str,
    level: str,
    system_instruction: Optional[str] = None,
) -> Optional[types.GenerateContentConfig]:
    config_kwargs = {}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction

    if model == "gemini-3-pro-preview" or model == 'gemini-3-flash-preview':
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=level),
            **config_kwargs,
        )
    else:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            **config_kwargs,
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


def _parse_role_markers(text: str) -> list[dict[str, str]]:
    if CHATML_START_MARKER not in text:
        return [{"role": "user", "content": text}]

    messages = []
    for part in text.split(CHATML_START_MARKER):
        if not part.strip():
            continue

        newline_index = part.find("\n")
        if newline_index < 0:
            continue

        role_name = part[:newline_index].strip().lower()
        content = part[newline_index + 1:]

        end_index = content.find(CHATML_END_MARKER)
        if end_index >= 0:
            content = content[:end_index]

        content = content.strip()
        if not content:
            continue

        role = ROLE_MAP.get(role_name, "user")
        messages.append({"role": role, "content": content})

    if not messages:
        return [{"role": "user", "content": text}]
    return messages


def _format_contents(
    template: Optional[str],
    *,
    source: str,
    target: str,
    text: str,
) -> tuple[Optional[str], str | list[types.Content]]:
    prompt = _format_prompt(template, source=source, target=target, text=text)
    if CHATML_START_MARKER not in prompt:
        return None, prompt

    messages = _parse_role_markers(prompt)
    system_messages = []
    contents = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            system_messages.append(content)
            continue

        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part(text=content)],
            )
        )

    if not contents:
        raise TranslationError("ChatML 프롬프트에는 user 또는 assistant 메시지가 필요합니다.")

    system_instruction = "\n\n".join(system_messages) if system_messages else None
    return system_instruction, contents


class GeminiTranslator:
    def __init__(self, default_model: str = "gemini-2.5-flash") -> None:
        _load_env_file()
        resolved_api_key = os.environ.get("GEMINI_API_KEY")
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
        prompt_template: Optional[str] = None,
    ) -> str:
        selected_model = model or self.default_model
        system_instruction, contents = _format_contents(
            prompt_template,
            source=source,
            target=target,
            text=text,
        )

        try:
            generate_config = _build_generate_config(selected_model, level, system_instruction)

            translated_text = self.client.models.generate_content(
                model=selected_model,
                contents=contents,
                config=generate_config
            )
            print(f'[DEBUG] Model: {selected_model}, Thinking Config: {generate_config.thinking_config}')

            if not translated_text:
                raise TranslationError("번역 결과가 비어 있습니다.")
            return translated_text.text
        except TranslationError:
            raise
        except Exception as exc:
            print(exc)
            raise TranslationError("번역 요청 중 오류가 발생했습니다.") from exc


def create_translator(default_model: str = "gemini-2.5-flash") -> GeminiTranslator:
    return GeminiTranslator(default_model=default_model)
