---
name: genai-client
description: The one pattern for every LLM or embedding call, local or cloud. Use when a feature calls a model or creates embeddings, or when reviewing such code.
pack: stack
---

# GenAI client

One OpenAI-compatible client; the target is config only. Local (develop): `llm.baseUrl` at Ollama, `llm.apiKey=ollama`. Cloud (qa, release, master): provider URL and a real key from the secrets file.

## Rules
- Model names from `llm.model` / `llm.embeddingModel` or the DB, never hardcoded. All settings through the config loader; fail loudly on a missing key.
- Set `timeout`, `max_retries`, `max_tokens` and `temperature` explicitly.
- Structured output: a Pydantic model as schema, validate the result; on parse failure retry once with the error, then raise.
- Embeddings use the same client; check vector dimension against config before storing.
- No `@lru_cache` on methods. Log model, token counts, latency, never prompts or user content.

## Testing
Unit tests use a fake client with canned responses (no network, no tokens). At most one real-endpoint test per usecase, marked `llm` and off by default.

## Usecase shape
Class with `createPromptMessage(input)`, `modelRequest(prompt)`, `execute(input)` returning the validated result.
