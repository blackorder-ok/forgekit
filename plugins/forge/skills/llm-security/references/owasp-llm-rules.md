<!-- Reference for the llm-security skill. Ported from setting-up-claude/llm-security (v0.1.0); read only when the digest is not enough. -->

# LLM security

Model output and retrieved text are untrusted input. Prompt rules reduce risk but never remove it. Enforce every rule in code.

## 1. Prompt injection (LLM01)
- System instructions live in the system message only. User text and retrieved text go in clearly separated messages, and are labelled as data.
- No instruction in user or retrieved text can change tools, permissions, or the output schema. Enforce this in code, not in the prompt.
- Test with a fixed set of injection strings in the `security` level. Each must leave tool calls and the output schema unchanged.

## 2. Sensitive information (LLM02)
- No secrets, keys, or internal endpoints in any prompt.
- Personal data is removed or pseudonymised before a cloud provider call, unless the plan allows it for that feature.
- Logs record the model name, token counts, and a hash of the prompt. Never the full prompt or the response.

## 3. Supply chain (LLM03)
- Model IDs are pinned to a version in `config/application-<env>.properties`. No `latest` aliases.
- Local model files are checked against a known hash before loading.
- Each cloud provider used is recorded in the plan with its data-processing terms.

## 4. Data and model poisoning (LLM04)
- Documents added to a vector index come from a known source and pass the same input checks as any other data.
- Eval and fine-tuning data is kept separate from production data.

## 5. Insecure output handling (LLM05)
- Every model response is parsed into a Pydantic model. Parse failures are retried once, then raised as an error.
- Model output is never executed, never used as a shell command, never used to build SQL, and never used as a file path or URL without the checks in `python-security`.
- Output rendered in a browser is escaped.

```python
# ❌ model output used as SQL
db.execute(model_reply)

# ✅ model output parsed, then used as a value
result = QueryPlan.model_validate_json(model_reply)
db.execute(text("SELECT * FROM notes WHERE id = :id"), {"id": result.note_id})
```

## 6. System prompt leakage (LLM07)
- Assume the system prompt will be seen. It contains no secrets, no credentials, and no rules whose disclosure would be harmful.
- Access control is never implemented in the prompt.

## 7. Excessive agency (LLM06)
- Each usecase has an explicit tool allowlist in code. A tool not on the list cannot be called.
- Each tool has the narrowest scope it needs, such as read-only, or one table.
- Any tool that writes, sends, deletes, or spends money needs a confirmation step from a user, or a dry-run result shown first.
- The number of tool-call rounds per request is capped in code.

## 8. Vector and retrieval weaknesses (LLM08)
- Access filters (user, tenant, or role) are applied by the server to every retrieval, as metadata filters in the Pinecone query. The model never supplies them.
- A document a user cannot read is never retrieved, even if it is similar.
- Each environment uses its own Pinecone index, so no retrieval can cross environments.

## 9. Misinformation (LLM09)
- Answers that state facts from retrieved text cite the document ID they used. Answers with no supporting document say so.
- The `llm` level checks that refusals happen when no supporting document exists.

## 10. Unbounded consumption (LLM10)
- Every call sets `max_tokens`, a timeout, and a retry limit.
- Each user has a per-day request and token budget. The request is refused with a clear error when it is spent.
- Each environment has a monthly token budget from the plan. A run that reaches it stops.
- Cost per request is measured in the `load` and `llm` levels.

## Tests for each LLM feature
- `unit`: the tool allowlist, output parsing, retry limit, and budget refusal, using the fake LLM.
- `security`: the injection set from section 1, and cross-user retrieval attempts.
- `llm`: the eval set in `evals/`, under the `llm-eval` skill.

## Review checklist
- Prompt sections are separated, and tool allowlist and schema checks are enforced in code.
- No personal data or secrets go into prompts or logs without a recorded decision.
- Model output is validated before any use.
- Every write-capable tool has a confirmation step or dry-run.
- Retrieval filters come from the server, and every call has limits.
