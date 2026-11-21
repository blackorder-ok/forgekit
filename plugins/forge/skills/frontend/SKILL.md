---
name: frontend
description: Frontend stack and rules, covering React, TypeScript, Vite, TanStack Query, Vitest, Playwright and nginx in the app container, with API types generated from OpenAPI. Use when a project has a web page or a feature changes what it shows or calls.
pack: stack
---

# Frontend

Stack: TypeScript strict · React 18 · Vite · TanStack Query · `openapi-typescript` from `openapi.json` · Vitest and Testing Library · Playwright · nginx in the app container. Pin exact versions (`npm install -E`), commit the lockfile, `npm ci` in CI and Docker.

## Rules
- `openapi.json` is the contract; every route has a `response_model`. `npm run gen:api` regenerates `schema.d.ts`, never edited by hand. CI fails if `openapi.json` is stale.
- All HTTP goes through `src/api/client.ts` with relative `/api` paths. No `fetch` in components, no hardcoded host.
- Render server text as text. Never `innerHTML` (CI fails on it).
- Map API errors to plain sentences, never raw JSON.
- No secrets in `frontend/`; the user id in `localStorage` is a convenience, not a credential.
- nginx CSP `default-src 'self'`, no inline scripts or styles.
- Works at phone width. Inputs have labels, errors use `role="alert"`, everything is keyboard-reachable.
- Coverage gate: lines 80, functions 80, branches 70, statements 80.

## Tests
`unit` (Vitest, Testing Library with a fake `ApiClient`) · `contract` (paths exist in `openapi.json`) · `e2e` (Playwright on develop and qa).

## Commands
`npm run dev` (proxies `/api` to `127.0.0.1:8000`), `npm test`, `npm run typecheck`, `npm run build`, `npm run gen:api`.

Layout and full rules: `references/full-rules.md`.
