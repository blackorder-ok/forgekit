<!-- Reference for the frontend skill. Ported from setting-up-claude/frontend (v0.1.0); read only when the digest is not enough. -->

# Frontend

## Stack
| Part | Choice | Why |
|---|---|---|
| Language | TypeScript, `strict` on | Catches API mismatches before they run |
| UI | React 18 | Largest hiring pool and ecosystem |
| Build | Vite | Fast dev server, standard production build |
| Server state | TanStack Query | Caching, retries, loading and error states in one place |
| API types | `openapi-typescript`, generated from `openapi.json` | The client cannot drift from the API |
| Unit and component tests | Vitest and React Testing Library | Standard for Vite projects |
| End-to-end tests | Playwright | Real browser, real API |
| Serving | nginx inside the environment's app container | Serves the build, forwards `/api/` to the API, sets security headers |

Pin every version exactly (`npm install -E`). Commit `package-lock.json`. Use `npm ci` in CI and Docker.

## Layout
```
frontend/
  package.json, package-lock.json, tsconfig.json, vite.config.ts, index.html
  src/
    main.tsx          entry: query client and root render
    App.tsx           layout and user id gate
    api/client.ts     typed API client (the only place that calls fetch)
    api/schema.d.ts   generated from openapi.json, never edited by hand
    components/       one component per file, with its test in the same folder
    hooks/            shared hooks
    test/setup.ts     Testing Library and jest-dom setup
  e2e/                Playwright tests (when the plan has an e2e level)
docker/frontend.Dockerfile   build with node; output is copied into the app image
docker/app.Dockerfile        nginx in the app container: serves the build, /api/ to the backend, security headers
openapi.json            exported from the API by scripts/export_openapi.py
```

## Rules
- The API contract is `openapi.json`. Every route the API serves has a typed response model (`response_model`). A route without one fails the contract test.
- `npm run gen:api` regenerates `schema.d.ts`. CI runs `python scripts/export_openapi.py --check` and fails if `openapi.json` is stale.
- All HTTP calls go through `api/client.ts`. Components never call `fetch` directly.
- The client uses relative paths under `/api`. No hardcoded host or port.
- Text from the server is rendered as text. Never assign `innerHTML`. CI fails on any `.innerHTML =` assignment.
- Errors from the API become plain sentences (`429`, `502`, `503`, and so on). Raw JSON is never shown.
- The user id is a stub header for the trial. It is remembered in `localStorage` for convenience only and is never treated as a credential. Real sign-in replaces it when the plan says so.
- No secrets, keys, or tokens in any file under `frontend/`. Everything in the build is public.
- Content Security Policy in nginx: `default-src 'self'`, no inline scripts or styles. Any change that needs inline code is a design decision, not a quick fix.
- Works at phone width. No fixed widths above 100%, no horizontal scroll.
- Accessibility: every input has a label, every error uses `role="alert"`, every interactive element is reachable by keyboard.
- Coverage gate in `vite.config.ts`: lines 80, functions 80, branches 70, statements 80. Below the gate, the test run fails.

## Tests
- `unit` (Vitest): API client behaviour (headers, bodies, error mapping, 204 handling). Runs on every branch.
- `unit` (Testing Library): each component's loading, success, and error states, with a fake `ApiClient`.
- `contract`: every path the client calls exists in `openapi.json`. Generated types match the committed spec.
- `e2e` (Playwright): one user, one conversation, one message, one saved note, one delete. Runs on `develop` and `qa` against the compose stack. Not run on `release` or `master` except as smoke.

## Commands
- `npm run dev`: local development, proxies `/api` to the backend on `127.0.0.1:8000`.
- `npm test`, `npm run typecheck`, `npm run build`: the CI gate.
- `npm run gen:api`: after any API change, then commit the new `schema.d.ts`.

## Done when
The page works in a browser, typecheck, tests, and build pass, the contract test passes, and the change is in `docs/` and the changelog.
