/* Company AI — Layan voice bridge + visual presentation layer
 * Free production voice owner remains the browser SpeechRecognition/SpeechSynthesis engine in index.html.
 * This file adds only the presentation layer: compact transcript, live status badge, accessible controls,
 * and subtle human-like visual reactions. It does not create a second microphone, recognition loop, TTS loop, or WebRTC session.
 */
(function(){
  'use strict';
  var VERSION='20260918-08';
  window.LayanVoiceBridge={mode:'browser-stt-gemini-browser-tts',realtimeProvider:'optional-adapter',version:VERSION};

  function injectStyle(){
    if(document.getElementById('layanVoicePolishStyle'))return;
    var s=document.createElement('style');s.id='layanVoicePolishStyle';
    s.textContent=''+
      '.layanVoiceStage{font-family:Arial,Tahoma,sans-serif}'+
      '.layanVoiceStage .layanVoiceVisual:after{content:"";position:absolute;inset:auto 0 0;height:24%;background:linear-gradient(transparent,rgba(3,10,18,.45));pointer-events:none}'+
      '.layanLiveBadge{position:absolute;top:18px;left:18px;z-index:5;display:flex;align-items:center;gap:8px;padding:9px 12px;border-radius:999px;background:rgba(5,15,28,.72);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:12px;font-weight:800;box-shadow:0 10px 30px rgba(0,0,0,.2)}'+
      '.layanLiveDot{width:8px;height:8px;border-radius:50%;background:#6b7f94;box-shadow:0 0 0 0 rgba(95,231,255,.5)}'+
      '.layanVoiceStage.listening .layanLiveDot{background:#39e58c;animation:layanLivePulse 1.2s infinite}'+
      '.layanVoiceStage.speaking .layanLiveDot{background:#5fe7ff;animation:layanLivePulse .75s infinite}'+
      '.layanTranscriptLabel{display:flex;justify-content:space-between;align-items:center;margin:18px 0 7px;color:#708198;font-size:11px;font-weight:800}'+
      '.layanTranscriptLabel span:last-child{font-weight:600;color:#9aa9ba}'+
      '.layanVoiceText{max-height:118px;overflow:auto;transition:border-color .2s,box-shadow .2s}'+
      '.layanVoiceStage.listening .layanVoiceText{border-color:#9fe7ce;box-shadow:0 0 0 3px rgba(57,229,140,.08)}'+
      '.layanVoiceStage.speaking .layanVoiceText{border-color:#a8dff0;box-shadow:0 0 0 3px rgba(95,231,255,.08)}'+
      '.layanVoiceActions button:focus-visible,.layanClose:focus-visible{outline:3px solid #5fe7ff;outline-offset:2px}'+
      '@keyframes layanLivePulse{0%{box-shadow:0 0 0 0 rgba(95,231,255,.55)}70%{box-shadow:0 0 0 8px rgba(95,231,255,0)}100%{box-shadow:0 0 0 0 rgba(95,231,255,0)}}'+
      '@media(max-width:850px){.layanLiveBadge{top:12px;left:12px}.layanTranscriptLabel{margin-top:10px}.layanVoiceText{max-height:82px}}';
    document.head.appendChild(s);
  }

  function polish(){
    injectStyle();
    var stage=document.getElementById('layanVoiceStage');
    if(!stage||stage.dataset.layanPolished==='1')return;
    stage.dataset.layanPolished='1';
    var visual=stage.querySelector('.layanVoiceVisual');
    if(visual){
      var badge=document.createElement('div');badge.className='layanLiveBadge';badge.innerHTML='<i class="layanLiveDot" aria-hidden="true"></i><span>ليان • محادثة صوتية مباشرة</span>';
      visual.appendChild(badge);
    }
    var text=document.getElementById('layanVoiceText');
    if(text){
      var label=document.createElement('div');label.className='layanTranscriptLabel';label.innerHTML='<span>آخر ما قيل</span><span>النص يظهر باختصار أثناء المحادثة</span>';
      text.parentNode.insertBefore(label,text);
      text.setAttribute('aria-live','polite');text.setAttribute('role','status');
    }
    var close=document.querySelector('.layanClose');if(close)close.setAttribute('aria-label','إغلاق محادثة ليان');
    var start=document.getElementById('layanStart');if(start)start.setAttribute('aria-label','بدء أو إيقاف المحادثة الصوتية مع ليان');
    var demo=document.querySelector('.layanDemo');if(demo)demo.setAttribute('aria-label','تجربة صوت ليان');
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',polish);else polish();
})();