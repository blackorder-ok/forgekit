---
name: llm-security
description: Security rules for features that call an LLM or let a model use tools, mapped to the OWASP LLM Top 10 (2025). Use when designing or reviewing prompts, tools, retrieval, output handling or cost controls.
pack: stack
---

# LLM security

Model output and retrieved text are untrusted input. Prompts reduce risk; code enforces it.

- **Injection (LLM01):** system rules in the system message only; user and retrieved text are labelled data. No text can change tools, permissions or schema. Test with a fixed injection set at the `security` level.
- **Sensitive data (LLM02):** no secrets in prompts; remove or pseudonymise personal data before cloud calls unless the plan allows it; log model, token counts and a prompt hash only.
- **Supply chain (LLM03):** pin model IDs per env, check local model hashes, record each provider's data terms in the plan.
- **Poisoning (LLM04):** index only known sources; keep eval data apart from production.
- **Output (LLM05):** parse every response into a Pydantic model (retry once, then raise). Never execute it, build SQL, shell, path or URL from it without the `python-security` checks. Escape in browsers.
- **Prompt leakage (LLM07):** assume the system prompt is seen; no secrets or access control in it.
- **Agency (LLM06):** explicit tool allowlist in code, narrowest scope, confirmation or dry-run for writes, sends, deletes and spend, capped tool rounds.
- **Retrieval (LLM08):** server-side metadata filters per user, tenant or role; own index per env.
- **Misinformation (LLM09):** cite document IDs; say so when there is no support.
- **Consumption (LLM10):** `max_tokens`, timeout and retry limit on every call; per-user daily budget; monthly env budget from the plan.

## Tests per LLM feature
`unit`: allowlist, parsing, retry limit, budget refusal (fake LLM). `security`: injection set, cross-user retrieval. `llm`: the eval set.

Full text with code examples: `references/owasp-llm-rules.md`.
