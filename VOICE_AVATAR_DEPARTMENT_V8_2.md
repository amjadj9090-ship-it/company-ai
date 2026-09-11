# Company AI v8.2 — Universal Voice & Avatar AI Department

## Decision
Company AI is **universal-language by design**. Voice and avatar are not Arabic-only and are not tied to a fixed small list of languages.

## Customer experience
- Detect the visitor's browser/device language automatically.
- Layan speaks and listens in that language whenever the Company AI voice model supports it.
- A small language control allows manual override at any time.
- Switching language changes the active voice/session language without changing the customer's business context.
- Unknown or unavailable languages use a controlled fallback rather than silently pretending native support.
- No separate customer-facing translation layer is required for same-language conversation; the AI conversation layer is multilingual.

## Owned stack
`microphone → language detection → STT → Company AI Central Brain → TTS → voice identity → lip-sync → facial/head/eye/body motion → avatar renderer`

External providers may be optional adapters for development, capacity, or fallback. They are not required core infrastructure.

## APIs
- `GET /api/voice-avatar/languages`
- `POST /api/voice-avatar/detect-language`
- `GET /api/voice-avatar/architecture`
- `GET/POST /api/voice-avatar/voice-profiles`
- `GET/POST /api/voice-avatar/avatar-profiles`
- `POST /api/voice-avatar/sessions`
- `POST /api/voice-avatar/jobs`

## Engineering note
“Universal” is an architecture and product requirement, not a claim that every language has an equally mature neural voice model on day one. The registry is extensible so additional languages can be added without changing the Company AI business workflow.
