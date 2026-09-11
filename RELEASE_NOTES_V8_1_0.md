# Company AI v8.1.0 — Voice & Avatar AI Foundation

## Added
- Dedicated Voice & Avatar AI department.
- Company-owned voice/avatar architecture and permission boundary.
- Voice profiles and Arabic-first Layan profile.
- Avatar profiles and Layan profile with speech, lip-sync and motion capabilities.
- Voice session API with listen → STT → central AI → response → TTS → lip-sync → motion pipeline.
- Avatar job queue API for lip-sync and future rendering jobs.
- Speech/model registry with local-first Company AI model slots.
- Completion audit coverage for the new department.

## Design rule
Company AI owns the orchestration interfaces and workflow. External providers are optional adapters, not required dependencies of the core product.

## Launch
Production launch remains deferred as previously decided.
