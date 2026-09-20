# Layan Voice — Gemini Root-Cause Input

This folder contains the actual voice-related source extracted from the current Company AI launch build. It is a BACKUP branch only; do not modify the live branch.

## Source files
- frontend/layan-realtime-hotfix.js
- frontend/layan-realtime-ga-fix.js
- frontend/layan-realtime-guard-v12.js
- frontend/layan-realtime-lock-v11.js
- frontend/company-ai-live-bridge.js
- frontend/index.html
- launch_backend.py

## Task
Perform a ROOT-LEVEL rebuild analysis of Layan voice. Do not patch yet and do not change the live project.

Trace:
Microphone -> recording -> voice activity/turn detection -> end of speech -> upload -> backend -> STT/audio understanding -> AI -> response -> TTS/playback -> next turn.

Find the real root cause and all legacy/conflicting paths. Pay special attention to multiple voice implementations, duplicate listeners, SpeechRecognition vs MediaRecorder vs WebRTC/realtime paths, timers/silence detection, second/third turn failures, microphone reactivation, mobile keyboard/focus, audio format compatibility, backend /launch-api/chat-audio, Gemini request format/model, context preservation, language/dialect handling, and any hidden hard limits.

Required behavior:
- Natural ChatGPT-like multi-turn conversation.
- No automatic keyboard in voice mode.
- User can speak naturally and pause without premature cutoff.
- No arbitrary 4/4.5-minute session cutoff.
- Long explanations must be supported within practical transport/API limits.
- Correct turn detection; distinguish short pauses from end of turn.
- After each answer, return to listening automatically.
- Preserve conversation context across turns.
- Detect and preserve user's language/dialect naturally.
- Natural TTS; no artificial diacritics/stilted language or unwanted Shami/Fusha mixing.
- Robust mobile/Android behavior.
- Clean architecture with one authoritative voice path, not competing legacy systems.
- Errors must fail clearly and recover where possible.

FIRST return only an analysis report:
1. ROOT CAUSE
2. ALL CONFLICTS / LEGACY VOICE PATHS
3. CURRENT ACTUAL VOICE FLOW
4. WHY THE SECOND/THIRD REQUEST CAN FAIL
5. FILES THAT MUST CHANGE
6. PROPOSED NEW ARCHITECTURE
7. TEST PLAN

Do not implement until the report is reviewed/approved.
