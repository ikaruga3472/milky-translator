from typing import Optional

from providers.base import Message, Provider, TranslationError


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


DEFAULT_PROMPT_TEMPLATE = '''# Role
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


def _load_env_file() -> None:
    """Best-effort .env loader without hard dependency on python-dotenv."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _format_prompt(
    template: Optional[str],
    *,
    source: str,
    target: str,
    text: str,
) -> str:
    resolved = template or DEFAULT_PROMPT_TEMPLATE
    return (
        resolved.replace("{{source}}", source)
        .replace("{{target}}", target)
        .replace("{{text}}", text)
        .strip()
    )


def _parse_role_markers(text: str) -> list[Message]:
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
        content = part[newline_index + 1 :]
        end_index = content.find(CHATML_END_MARKER)
        if end_index >= 0:
            content = content[:end_index]

        content = content.strip()
        if content:
            messages.append(
                {"role": ROLE_MAP.get(role_name, "user"), "content": content}
            )

    if not any(message["role"] != "system" for message in messages):
        raise TranslationError("ChatML 프롬프트에는 user 또는 assistant 메시지가 필요합니다.")
    return messages


def _build_messages(
    template: Optional[str],
    *,
    source: str,
    target: str,
    text: str,
) -> list[Message]:
    prompt = _format_prompt(template, source=source, target=target, text=text)
    return _parse_role_markers(prompt)


class Translator:
    def __init__(self) -> None:
        _load_env_file()
        self.providers: dict[str, Provider] = {}

    def _get_provider(self, provider: str) -> Provider:
        if provider not in self.providers:
            if provider == "gemini":
                from providers.gemini import GeminiProvider

                self.providers[provider] = GeminiProvider()
            elif provider == "ollama":
                from providers.ollama import OllamaProvider

                self.providers[provider] = OllamaProvider()
            else:
                raise TranslationError(f"지원하지 않는 번역 공급자입니다: {provider}")
        return self.providers[provider]

    def translate(
        self,
        text: str,
        source: str,
        target: str,
        *,
        provider: str,
        model: str,
        level: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> str:
        messages = _build_messages(
            prompt_template,
            source=source,
            target=target,
            text=text,
        )
        return self._get_provider(provider).generate(model, messages, level)


def create_translator() -> Translator:
    return Translator()
