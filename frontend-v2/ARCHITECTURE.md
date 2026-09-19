# Clean Architecture Contract

## Boundaries
1. UI components render data; they do not own business data.
2. Content lives in data files; translations are not hard-coded into component logic.
3. Language detection and direction are handled by one language service.
4. Layan is an integration boundary; UI does not know provider credentials or backend secrets.
5. Public routes never expose internal CRM, finance, security or administrative data.
6. API validation, authorization, rate limiting and secrets remain server-side.
7. Assets are referenced by stable paths; changing an asset must not require changing unrelated logic.
8. Every major feature gets an isolated test before integration.

## Delivery gates
- Gate A: syntax/static validation
- Gate B: responsive/mobile validation
- Gate C: service navigation and data validation
- Gate D: language fallback and direction validation
- Gate E: security review
- Gate F: integrated browser test
- Gate G: isolated preview deployment
- Gate H: live verification
- Gate I: only then merge to main

## Non-goals
- Do not reuse the legacy v10 script.
- Do not layer a redesign on top of the old DOM.
- Do not declare a preview valid because a deployment is merely LIVE.
