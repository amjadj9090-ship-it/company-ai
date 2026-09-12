/* Company AI — Layan Model 2 / Realtime GA repair */
(function () {
  'use strict';
  var state = { pc: null, mic: null, audio: null, dc: null, overlay: null, running: false };

  function apiBase() {
    return (window.COMPANY_AI_API_BASE || (location.hostname.endsWith('github.io') ? 'https://company-ai-free-beta.onrender.com' : '')).replace(/\/$/, '');
  }

  function ensureOverlay() {
    if (state.overlay) return state.overlay;
    var root = document.createElement('div');
    root.id = 'layanRealtimeSession2';
    root.innerHTML = `
      <style>
        #layanRealtimeSession2{position:fixed;inset:0;z-index:200000;background:#050b13;display:none;overflow:hidden;font-family:Arial,Tahoma,sans-serif}
        #layanRealtimeSession2.open{display:block}
        #layanRealtimeSession2 .office{position:absolute;inset:0;background:#08121f url('assets/layan-office.webp') center/cover no-repeat}
        #layanRealtimeSession2 .shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(3,10,18,.22),rgba(3,10,18,.08) 55%,rgba(3,10,18,.58))}
        #layanRealtimeSession2 .panel{position:absolute;right:28px;top:28px;bottom:28px;width:min(390px,calc(100vw - 56px));background:rgba(248,251,255,.96);border:1px solid rgba(255,255,255,.45);border-radius:26px;box-shadow:0 30px 90px rgba(0,0,0,.38);display:flex;flex-direction:column;overflow:hidden;backdrop-filter:blur(16px)}
        #layanRealtimeSession2 .head{padding:20px;border-bottom:1px solid #dce5f0;display:flex;justify-content:space-between;align-items:center}
        #layanRealtimeSession2 .head b{color:#10213a;font-size:18px}#layanRealtimeSession2 .head small{display:block;color:#728198;margin-top:4px}
        #layanRealtimeSession2 .close{border:0;background:#edf2f8;color:#172b45;width:42px;height:42px;border-radius:50%;font-size:21px;cursor:pointer}
        #layanRealtimeSession2 .body{flex:1;padding:24px;display:flex;flex-direction:column;justify-content:center}
        #layanRealtimeSession2 .state{text-align:center;font-size:25px;font-weight:900;color:#10213a}
        #layanRealtimeSession2 .sub{text-align:center;color:#6b7d94;margin-top:8px;line-height:1.6}
        #layanRealtimeSession2 .wave{height:58px;display:flex;align-items:center;justify-content:center;gap:6px;margin:20px 0}
        #layanRealtimeSession2 .wave i{width:7px;height:13px;border-radius:9px;background:linear-gradient(#5fe7ff,#7657ff)}
        #layanRealtimeSession2.active .wave i{animation:layanRealtimeWave .55s infinite alternate}
        #layanRealtimeSession2.active .wave i:nth-child(2){animation-delay:.08s}#layanRealtimeSession2.active .wave i:nth-child(3){animation-delay:.16s}#layanRealtimeSession2.active .wave i:nth-child(4){animation-delay:.24s}#layanRealtimeSession2.active .wave i:nth-child(5){animation-delay:.32s}
        #layanRealtimeSession2 .transcript{background:#fff;border:1px solid #dbe5f3;border-radius:18px;padding:15px;min-height:90px;color:#273b55;line-height:1.75;overflow:auto}
        #layanRealtimeSession2 .end{margin-top:14px;border:0;border-radius:14px;padding:15px;background:linear-gradient(135deg,#d92d4f,#a71f42);color:#fff;font-weight:900;cursor:pointer}
        #layanRealtimeSession2 .hint{text-align:center;color:#7b8ba0;font-size:11px;margin-top:10px}
        @keyframes layanRealtimeWave{from{height:12px}to{height:48px}}
        @media(max-width:700px){#layanRealtimeSession2 .panel{right:12px;left:12px;top:auto;bottom:12px;width:auto;height:44dvh;min-height:300px;border-radius:22px}#layanRealtimeSession2 .state{font-size:20px}#layanRealtimeSession2 .body{padding:16px}}
      </style>
      <div class="office"></div><div class="shade"></div>
      <section class="panel" role="dialog" aria-modal="true" aria-label="جلسة ليان الصوتية المباشرة">
        <header class="head"><div><b>ليان — جلسة صوتية مباشرة</b><small id="layanRealtimeStatus">جاري التحضير…</small></div><button class="close" id="layanRealtimeClose" aria-label="إنهاء">×</button></header>
        <div class="body"><div class="state" id="layanRealtimeState">اتصلنا بجلسة ليان</div><div class="sub" id="layanRealtimeSub">احكِ بشكل طبيعي، ليان رح تسمعك وترد عليك. ما في داعي تضغط زر كل مرة.</div><div class="wave"><i></i><i></i><i></i><i></i><i></i></div><div class="transcript" id="layanRealtimeTranscript">بانتظار الصوت…</div><button class="end" id="layanRealtimeEnd">إنهاء المحادثة</button><div class="hint">المحادثة تبقى مفتوحة حتى تنهيها أنت. ويمكنك مقاطعة ليان أثناء كلامها.</div></div>
      </section>`;
    document.body.appendChild(root);
    root.querySelector('#layanRealtimeClose').onclick = window.stopLayanVoice;
    root.querySelector('#layanRealtimeEnd').onclick = window.stopLayanVoice;
    state.overlay = root;
    return root;
  }

  function ui(stateText, subText, transcript) {
    var root = ensureOverlay();
    root.querySelector('#layanRealtimeStatus').textContent = stateText;
    root.querySelector('#layanRealtimeState').textContent = stateText;
    root.querySelector('#layanRealtimeSub').textContent = subText || '';
    if (transcript !== undefined) root.querySelector('#layanRealtimeTranscript').textContent = transcript || '…';
  }

  function setActive(on) {
    ensureOverlay().classList.toggle('active', !!on);
  }

  async function getEphemeralKey() {
    var response = await fetch(apiBase() + '/api/voice-avatar/public-session', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'
    });
    var data = await response.json().catch(function(){ return {}; });
    if (!response.ok) throw new Error(data.detail || ('Voice backend returned HTTP ' + response.status));
    if (!data.value || !String(data.value).startsWith('ek_')) throw new Error('Voice backend returned no valid ephemeral key');
    return data.value;
  }

  async function startLayanVoice() {
    if (state.running) return;
    state.running = true;
    var root = ensureOverlay();
    root.classList.add('open');
    ui('جاري الاتصال…', 'عم نجهّز جلسة الصوت المباشرة.', 'جاري إنشاء جلسة آمنة…');
    try {
      var key = await getEphemeralKey();
      state.mic = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});
      state.pc = new RTCPeerConnection();
      state.audio = document.createElement('audio'); state.audio.autoplay = true; state.audio.playsInline = true; state.audio.style.display='none'; document.body.appendChild(state.audio);
      state.pc.ontrack = function(e){ state.audio.srcObject = e.streams[0]; state.audio.play().catch(function(){}); };
      state.mic.getTracks().forEach(function(t){ state.pc.addTrack(t, state.mic); });
      state.dc = state.pc.createDataChannel('oai-events');
      state.dc.onopen = function(){
        state.dc.send(JSON.stringify({type:'session.update',session:{type:'realtime',instructions:'You are Layan, the live voice assistant for Company AI. Detect the visitor language automatically. For Arabic, use clear Syrian/Levantine Arabic and never Egyptian phrasing. Speak naturally, concisely and professionally. Do not claim protected financial, legal or contract actions were completed without owner approval.',audio:{input:{noise_reduction:{type:'near_field'},transcription:{model:'gpt-4o-transcribe'},turn_detection:{type:'semantic_vad',eagerness:'auto',create_response:true,interrupt_response:true}},output:{voice:'marin'},},output_modalities:['audio']}}));
        ui('متصل — احكي مع ليان', 'الميكروفون شغّال بشكل مستمر. احكي بشكل طبيعي وقاطع ليان بأي لحظة.', 'بانتظار كلامك…'); setActive(true);
      };
      state.dc.onmessage = function(event){
        var data; try{data=JSON.parse(event.data);}catch(_){return;}
        if(data.type==='input_audio_buffer.speech_started'){ui('عم اسمعك…','كمل كلامك بشكل طبيعي.','ليان عم تسمعك…');}
        else if(data.type==='response.created'){ui('ليان عم ترد…','إذا بدك تقاطعها، احكي مباشرة.','');}
        else if(data.type==='response.audio_transcript.delta'){var el=root.querySelector('#layanRealtimeTranscript');el.textContent+=(data.delta||'');}
        else if(data.type==='response.audio_transcript.done'){ui('ليان عم تحكي…','فيك تقاطعها بأي لحظة.',data.transcript||'');}
        else if(data.type==='response.done'){ui('متصل — احكي مع ليان','الميكروفون شغّال بشكل مستمر.','بانتظار كلامك…');}
        else if(data.type==='error'){ui('صار خطأ بالصوت',data.error&&data.error.message||'تعذر إكمال جلسة الصوت.', 'رح نوقف الجلسة بأمان.'); console.error('Layan Realtime error',data);}
      };
      state.pc.onconnectionstatechange = function(){
        if(!state.pc)return;
        if(state.pc.connectionState==='connected'){ui('متصل — احكي مع ليان','الجلسة لايف ومستمرة حتى تضغط إنهاء.','بانتظار كلامك…');}
        if(['failed','disconnected','closed'].includes(state.pc.connectionState) && state.running){ui('انقطع الاتصال', 'رح نغلق الجلسة الحالية بأمان.', 'الاتصال انقطع.');}
      };
      var offer = await state.pc.createOffer(); await state.pc.setLocalDescription(offer);
      var answerResponse = await fetch('https://api.openai.com/v1/realtime/calls', {method:'POST',headers:{'Authorization':'Bearer '+key,'Content-Type':'application/sdp'},body:offer.sdp});
      var answer = await answerResponse.text();
      if(!answerResponse.ok) throw new Error(answer || ('Realtime call failed with HTTP '+answerResponse.status));
      await state.pc.setRemoteDescription({type:'answer',sdp:answer});
    } catch (err) {
      console.error('Layan live voice failed',err);
      ui('تعذر تشغيل الصوت', 'في مشكلة بالاتصال بالخدمة الصوتية.', err && err.message ? err.message : 'Unknown voice error');
      stopLayanVoice();
    }
  }

  function stopLayanVoice() {
    state.running=false;
    if(state.dc){try{state.dc.close();}catch(_){ } state.dc=null;}
    if(state.pc){try{state.pc.close();}catch(_){ } state.pc=null;}
    if(state.mic){state.mic.getTracks().forEach(function(t){try{t.stop();}catch(_){ }});state.mic=null;}
    if(state.audio){try{state.audio.pause();state.audio.srcObject=null;state.audio.remove();}catch(_){ }state.audio=null;}
    if(state.overlay){state.overlay.classList.remove('open','active');}
  }

  function toggleLayanVoice(){ if(state.running) stopLayanVoice(); else startLayanVoice(); }
  window.startLayanVoice=startLayanVoice; window.stopLayanVoice=stopLayanVoice; window.toggleLayanVoice=toggleLayanVoice; window.openLayanVoice=startLayanVoice; window.closeLayanVoice=stopLayanVoice;

  function bind(){
    document.querySelectorAll('.voiceChoice').forEach(function(btn){btn.addEventListener('click',function(e){e.preventDefault();startLayanVoice();});});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
})();
