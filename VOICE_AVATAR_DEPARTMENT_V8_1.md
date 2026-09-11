# Company AI v8.1 — Voice & Avatar AI Department

## Mission
Build and own the company's complete speech and avatar stack so customer-facing AI employees can listen, understand, speak, and animate naturally without making an external vendor a core dependency.

## Scope
- Speech-to-text (STT)
- Text-to-speech (TTS)
- Voice identity and voice profiles
- Arabic-first voice capability for Layan and future AI employees
- Full-duplex voice sessions
- Realistic avatar runtime
- Lip synchronization
- Facial expression and emotion controls
- Head, eye and upper-body motion
- Media rendering and asset management
- Voice/avatar model registry and versioning
- Safety, consent and audit boundaries

## Architecture
`Microphone → STT → Company AI Central Brain → response → TTS → voice identity → lip-sync → facial/head/eye/body motion → avatar renderer → customer`

The business layer communicates only with Company AI interfaces. Model implementations can be swapped behind those interfaces without changing customer workflows.

## Ownership rule
External providers may be connected later as optional adapters for experimentation, capacity, or fallback. They are not the required foundation of Company AI's product architecture.

## Current v8.1 foundation
- Active department record: `voice-avatar`
- Layan Arabic voice profile: `layan-arabic`
- Layan avatar profile: `layan`
- Local-first model slots:
  - `company-ai-voice-v1`
  - `company-ai-stt-v1`
  - `company-ai-lipsync-v1`
  - `company-ai-avatar-motion-v1`
- Voice session pipeline and avatar job queue APIs
- Completion audit coverage

## Important distinction
v8.1 establishes the owned interfaces, governance, data model and runtime pipeline. The actual neural model training/inference engines are a separate engineering workstream; the architecture is deliberately designed so they can be introduced without replacing the company core.
