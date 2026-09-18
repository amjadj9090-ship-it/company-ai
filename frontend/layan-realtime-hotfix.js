/* Company AI — Layan voice bridge
 * The browser SpeechRecognition/SpeechSynthesis conversation engine in index.html
 * is the single voice-session owner for the free production path.
 * This compatibility file intentionally does not create a second microphone,
 * WebRTC session, recognition loop, or TTS loop.
 */
(function(){
  'use strict';
  window.LayanVoiceBridge = {
    mode: 'browser-stt-gemini-browser-tts',
    realtimeProvider: 'optional-adapter',
    version: '20260918-07'
  };
})();