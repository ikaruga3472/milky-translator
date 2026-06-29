from typing import Optional, Protocol


Message = dict[str, str]


class TranslationError(Exception):
    """Raised when translation fails or configuration is missing."""


class Provider(Protocol):
    def generate(
        self,
        model: str,
        messages: list[Message],
        level: Optional[str] = None,
    ) -> str: ...
