# Company AI — Coding Agent Instructions

## Mission
Fix the Layan experience end-to-end. Do not assume the documentation is proof that the feature works. Verify the actual code paths and runtime behavior.

## Primary objective
Layan must:
1. Load the approved Layan office visual from the repository assets.
2. Offer two distinct entry modes: Text chat with Layan and Voice chat with Layan.
3. Voice mode must actually capture visitor speech, send it to the real backend/AI path, receive a response, and speak the response aloud.
4. While Layan speaks, the visual must visibly react: mouth/lip movement, eyes/head/gesture animation as implemented by the project.
5. Language must follow the visitor/device language with manual language selection available.
6. Protected finance/legal/cyber/security actions must remain approval-gated.

## Debugging rules
- Inspect the entire relevant code path before changing files.
- Treat PROJECT_STATE.md and release notes as claims to verify, not as evidence that runtime behavior works.
- Find the root cause; do not stack another hotfix on top of an unverified broken path.
- Check frontend, backend, API routes, asset loading, environment/configuration, CORS/auth/session behavior, and deployment workflow as relevant.
- Reproduce failures with tests or executable checks whenever the environment permits.
- Make the smallest coherent fix that makes the complete path work.
- Add or update regression tests for the failure where practical.
- After changes, run the project's available tests/build/lint checks and inspect CI results.
- Do not remove the approved Layan asset or replace it with a placeholder.
- Do not weaken security or approval gates just to make the demo appear to work.

## Completion criteria
Do not report success merely because files changed or tests that do not exercise Layan pass. Success requires evidence that the actual Layan voice/text flow is wired correctly from browser to backend and back, and that the relevant automated checks pass.

## Repository
GitHub repository: amjadj9090-ship-it/company-ai
Default branch: main
