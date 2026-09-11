# Company AI v8.5.0 — Layan Real Voice Session

## Delivered
- Public `/api/voice-avatar/public-session` endpoint for Layan website sessions.
- Public `/api/central-ai/public-respond` endpoint connecting voice requests to the Central AI orchestration layer.
- Browser microphone capture through SpeechRecognition/Web Speech API.
- Automatic visitor language selection from browser locale.
- Browser speech synthesis response playback.
- Layan live visual state: listening, analysis, speaking, head motion and simple lip-sync animation.
- Session ID and routed department displayed to the visitor.
- No login required for the public website voice experience.
- Protected decisions remain blocked by the central governance rules.

## Validation
- Backend tests: 37/37 passed.
- Python compileall: passed.

## Architecture note
The runtime voice in this release uses the browser speech layer so the experience is immediately executable without an external avatar provider. The Company-owned neural voice/STT/lip-sync model slots remain in the Voice & Avatar AI department and can later replace browser runtime without changing the business workflow.
