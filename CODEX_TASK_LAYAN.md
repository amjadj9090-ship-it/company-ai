# Codex Task — Diagnose and Fix Layan End-to-End

Work directly on the current repository state. The user reports that Layan still does not actually work despite release documentation claiming v8.5.0 is complete.

## Required outcome
Make the real Layan experience work end-to-end, not just pass superficial checks.

### Required behavior
- The approved Layan office visual is used from repository assets.
- The visitor sees two separate choices: Text chat with Layan and Voice chat with Layan.
- Voice mode captures speech, reaches the correct backend/AI endpoint, receives a response, and speaks it aloud.
- Layan visibly animates while speaking (mouth/lips plus natural eye/head/gesture motion supported by the implementation).
- Visitor language is detected and respected, with manual language selection.
- Sensitive finance/legal/cybersecurity actions remain protected by approval gates.

## Investigation sequence
1. Read AGENTS.md, PROJECT_STATE.md, LAYAN_REAL_VOICE_SESSION_V8_5.md, and the latest Layan/realtime workflow files.
2. Map the actual frontend -> voice/session -> backend -> Central AI -> response -> speech -> animation path.
3. Locate the actual runtime entry points and deployment artifacts. Do not trust release notes as proof.
4. Identify the first real break in the chain and its root cause.
5. Fix the root cause coherently across all affected files.
6. Add regression coverage where practical.
7. Run all relevant tests/build/lint/type checks available in the repo.
8. Inspect GitHub Actions/CI results and fix failures caused by the change.
9. Only then report what was changed, what was tested, and any remaining blocker that requires an external credential/service or manual browser verification.

## Important
Do not create another disconnected hotfix workflow unless the existing architecture genuinely requires it. Prefer fixing the canonical application path. Do not weaken security gates or replace the approved Layan asset with a placeholder.
