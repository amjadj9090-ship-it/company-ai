# Company AI Foundation V1

## Purpose
This branch establishes the clean foundation for Company AI without deleting or rewriting the existing v8/v9 work.

## Layers
1. **Experience** — mobile-first web UI, text/voice entry, language and navigation.
2. **Conversation** — Layan as an interface, not the business authority.
3. **Central AI** — one intake contract that classifies intent, department, priority and approval mode.
4. **Specialists** — CRM, marketing, finance/legal, operations, development and other domain executors.
5. **Governance** — owner approval, permissions, audit trail and idempotency.
6. **Data** — PostgreSQL in production; no privileged state in the browser.
7. **Infrastructure** — Render deployment remains a separate verification gate.

## Core request lifecycle
User -> Experience -> Central AI intake -> decision -> specialist -> approval gate when required -> execution -> audit -> user-visible result.

## Non-negotiable rules
- Inspect before changing.
- Do not stack hotfixes over an unverified root cause.
- Keep the existing main branch intact until verification passes.
- No money movement, contract signing, or other binding protected operation without owner approval.
- No secrets in frontend code.
- Layan may collect and present requests; it does not bypass Company AI governance.
- Every executable operation must have a traceable request/decision/execution path.
- Every phase must have an automated regression check where practical.
- Deployment is successful only after live health and functional smoke checks.

## Current baseline
- Repository: amjadj9090-ship-it/company-ai
- Baseline branch: main
- Foundation branch: foundation-v1
- Existing backend already contains central orchestration, approvals, audit, CRM and Layan integrations.
- Existing frontend-v2 is a presentation layer and remains preserved.

## First implementation gate
Before changing the public experience, the foundation contract must pass unit tests and the existing main-branch behavior must remain untouched.
