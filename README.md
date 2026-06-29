# Milky Translator

Google Gemini와 Ollama Cloud를 선택해서 사용하는 Flask 번역기입니다.

## 환경 변수

```env
GEMINI_API_KEY=your_gemini_api_key
OLLAMA_API_KEY=your_ollama_api_key
FLASK_SECRET_KEY=your_flask_secret
```

Ollama는 기본적으로 `https://ollama.com/api/chat`을 호출합니다. 다른 Ollama
호스트를 사용하려면 `OLLAMA_BASE_URL`을 설정할 수 있습니다.

현재 Ollama 모델은 다음 두 가지입니다.

- `gemma4:31b`
- `gemma3:27b`
