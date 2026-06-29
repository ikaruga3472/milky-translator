import json
import os
from typing import Optional
from urllib import error, request

from providers.base import Message, TranslationError


class OllamaProvider:
    def __init__(self) -> None:
        api_key = os.environ.get("OLLAMA_API_KEY")
        if not api_key:
            raise TranslationError("OLLAMA_API_KEY가 설정되지 않았습니다.")

        base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")
        self.endpoint = f"{base_url.rstrip('/')}/api/chat"
        self.api_key = api_key

    def generate(
        self,
        model: str,
        messages: list[Message],
        level: Optional[str] = None,
    ) -> str:
        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
            }
        ).encode("utf-8")
        api_request = request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(api_request, timeout=180) as response:
                result = json.loads(response.read())
        except error.HTTPError as exc:
            raise TranslationError(
                f"Ollama Cloud 요청이 실패했습니다. (HTTP {exc.code})"
            ) from exc
        except error.URLError as exc:
            raise TranslationError("Ollama Cloud에 연결할 수 없습니다.") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise TranslationError("Ollama Cloud 응답을 해석할 수 없습니다.") from exc

        translated_text = result.get("message", {}).get("content")
        if not translated_text:
            raise TranslationError("번역 결과가 비어 있습니다.")
        return translated_text
