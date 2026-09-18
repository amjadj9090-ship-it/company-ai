/* Company AI — Layan canonical live voice bridge
 * One voice path only: browser WebRTC -> /api/voice-avatar/realtime-call -> OpenAI Realtime.
 * Uses the existing approved Layan stage/asset. No duplicate overlay, STT loop, or TTS fallback.
 */
(function(){
  'use strict';
  const VERSION='20260919-02';
  const state={pc:null,mic:null,audio:null,dc:null,running:false,offerPending:false,fallback:false,recognition:null,speaking:false};
  window.LayanVoiceBridge={mode:'webrtc-realtime-with-free-browser-fallback',version:VERSION};

  const stage=()=>document.getElementById('layanVoiceStage');
  const text=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
  function apiBase(){return (window.COMPANY_AI_API_BASE||'').replace(/\/$/,'');}
  function setState(a,b){
    text('layanVoiceState',a); text('layanVoiceSub',b||'');
    const s=stage(); if(s)s.setAttribute('data-layan-status',a);
  }
  function setMode(mode){
    const s=stage(); if(!s)return;
    s.classList.remove('listening','speaking');
    if(mode)s.classList.add(mode);
  }
  function cleanup(){
    if(state.recognition){try{state.recognition.onend=null;state.recognition.stop()}catch(_){}}
    if(state.dc){try{state.dc.close()}catch(_){}}
    if(state.pc){try{state.pc.close()}catch(_){}}
    if(state.mic)state.mic.getTracks().forEach(t=>{try{t.stop()}catch(_){}});
    if(state.audio){try{state.audio.pause();state.audio.srcObject=null;state.audio.remove()}catch(_){}}
    if('speechSynthesis' in window)try{speechSynthesis.cancel()}catch(_){}
    state.pc=state.mic=state.audio=state.dc=state.recognition=null;
    state.running=false;state.offerPending=false;state.fallback=false;state.speaking=false;setMode('');
  }
  async function startFreeBrowserVoice(){
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR)throw new Error('المتصفح لا يدعم وضع الصوت المجاني.');
    state.fallback=true;state.running=true;state.offerPending=false;
    const lang=(document.documentElement.lang||'ar').toLowerCase().split('-')[0];
    const recognition=new SR();state.recognition=recognition;
    recognition.lang=lang==='ar'?'ar-SA':lang+'-'+lang.toUpperCase();
    recognition.interimResults=true;recognition.continuous=false;recognition.maxAlternatives=1;
    let heard='';
    recognition.onstart=()=>{setMode('listening');setState('ليان تستمع إليك…','وضع صوت مجاني: احكي براحتك.');};
    recognition.onresult=e=>{
      let finalText='';
      for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0]?.transcript||'';if(e.results[i].isFinal)finalText+=t;else text('layanVoiceText',t);}
      if(finalText.trim())heard=(heard+' '+finalText).trim();
      if(heard)text('layanVoiceText',heard);
    };
    recognition.onerror=e=>{
      if(e.error==='not-allowed'||e.error==='service-not-allowed'){setState('الميكروفون غير مسموح','اسمح للمتصفح باستخدام الميكروفون ثم جرّب مرة ثانية.');return;}
      setState('تعذر التقاط الكلام',e.error||'جرّب مرة ثانية.');
    };
    recognition.onend=async()=>{
      if(state.recognition!==recognition)return;
      state.recognition=null;
      if(!heard.trim()){if(state.running&&!state.fallback)return;setMode('');setState('ليان جاهزة','اضغط الصوت واحكي معها.');return;}
      try{
        setMode('speaking');setState('ليان تحلل كلامك…','عم نجهّز الرد.');
        const aid=await fetch(apiBase()+'/api/sales-agent/public/config',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('تعذر الوصول لخدمة ليان النصية.');return r.json()});
        const r=await fetch(apiBase()+'/api/sales-agent/'+aid.build_id+'/conversation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:heard,language:lang,channel:'voice',assistant:'layan'})});
        if(!r.ok)throw Error('تعذر الحصول على رد ليان.');
        const d=await r.json();const reply=(d.reply||'').trim();
        if(!reply)throw Error('ليان أعادت رداً فارغاً.');
        text('layanVoiceText',reply);
        if(!('speechSynthesis' in window))throw Error('المتصفح لا يدعم إخراج الصوت.');
        const u=new SpeechSynthesisUtterance(reply);u.lang=lang==='ar'?'ar-SA':lang+'-'+lang.toUpperCase();u.rate=.94;u.pitch=1.02;
        u.onstart=()=>{state.speaking=true;setMode('speaking');setState('ليان تتحدث…','وضع صوت مجاني. بعد الرد رح تسمعك من جديد.');};
        u.onend=()=>{state.speaking=false;if(state.running&&state.fallback){setMode('');setState('ليان تستمع إليك…','احكي براحتك.');setTimeout(()=>{if(state.running&&state.fallback)startFreeBrowserVoice()},250);}};
        u.onerror=()=>{state.speaking=false;setMode('');setState('ليان جاهزة','إخراج الصوت غير متاح حالياً.');};
        speechSynthesis.cancel();speechSynthesis.speak(u);
      }catch(err){setMode('');setState('تعذر الرد الصوتي',err?.message||'جرّب مرة ثانية.');}
    };
    recognition.start();
    return true;
  }
  function closeLayanVoice(){
    cleanup();
    const s=stage(); if(s){s.classList.remove('open');s.setAttribute('aria-hidden','true');}
    document.body.style.overflow='';
    return false;
  }
  async function startLayanVoice(){
    if(state.running||state.offerPending)return;
    const s=stage(); if(!s)return false;
    state.offerPending=true;
    s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
    setState('جاري الاتصال بليان…','عم نجهّز الميكروفون والجلسة الصوتية الآمنة.');
    try{
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('المتصفح لا يوفّر الوصول إلى الميكروفون.');
      state.mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      state.pc=new RTCPeerConnection();
      state.audio=document.createElement('audio');
      state.audio.autoplay=true;state.audio.playsInline=true;state.audio.setAttribute('aria-hidden','true');state.audio.style.display='none';
      document.body.appendChild(state.audio);
      state.pc.ontrack=e=>{if(e.streams[0]){state.audio.srcObject=e.streams[0];state.audio.play().catch(()=>{})}};
      state.mic.getTracks().forEach(t=>state.pc.addTrack(t,state.mic));
      state.dc=state.pc.createDataChannel('oai-events');
      state.dc.onopen=()=>{
        const lang=(document.documentElement.lang||'ar').toLowerCase().split('-')[0];
        state.dc.send(JSON.stringify({type:'session.update',session:{
          type:'realtime',
          instructions:'You are Layan, the live voice assistant for Company AI. Detect the visitor language automatically and answer in the same language. For Arabic, use clear Syrian/Levantine Arabic, never Egyptian phrasing. Be concise and helpful. Never claim a financial transfer, withdrawal, contract signing, legal commitment, or other protected action was completed without owner approval.',
          audio:{input:{noise_reduction:{type:'near_field'},transcription:{model:'gpt-4o-transcribe'},turn_detection:{type:'semantic_vad',eagerness:'auto',create_response:true,interrupt_response:true}},output:{voice:'marin'}},
          output_modalities:['audio'],
          metadata:{interface_language:lang}
        }}));
      };
      state.dc.onmessage=event=>{
        let d;try{d=JSON.parse(event.data)}catch(_){return}
        const type=d.type||'';
        if(type==='session.created'||type==='session.updated'){
          state.running=true;setState('متصل — ليان معك','احكي بشكل طبيعي، وليان رح تسمعك وترد عليك.');return;
        }
        if(type==='input_audio_buffer.speech_started'){
          setMode('listening');setState('ليان تستمع إليك…','كمّل كلامك براحتك.');return;
        }
        if(type==='conversation.item.input_audio_transcription.completed'){
          if(d.transcript)text('layanVoiceText',d.transcript);
          return;
        }
        if(type==='response.created'){setMode('speaking');setState('ليان عم ترد…','فيك تقاطعها وتحكي بأي لحظة.');return;}
        if(type==='response.output_audio.delta'||type==='response.audio.delta'){
          setMode('speaking');setState('ليان تتحدث…','فيك تقاطعها بأي لحظة.');return;
        }
        if(type==='response.output_audio_transcript.delta'||type==='response.audio_transcript.delta'){
          const e=document.getElementById('layanVoiceText');if(e)e.textContent+=(d.delta||'');
          return;
        }
        if(type==='response.output_audio_transcript.done'||type==='response.audio_transcript.done'){
          if(d.transcript)text('layanVoiceText',d.transcript);
          return;
        }
        if(type==='response.done'){
          setMode('');setState('متصل — احكي مع ليان','الجلسة مستمرة. احكي عندما تكون جاهزاً.');return;
        }
        if(type==='error'){
          console.error('Layan Realtime error',d);
          setMode('');setState('خطأ في جلسة ليان الصوتية',d.error?.message||'تعذر إكمال الرد الصوتي.');
        }
      };
      state.pc.onconnectionstatechange=()=>{
        const cs=state.pc?.connectionState;
        if(cs==='connected'){state.running=true;state.offerPending=false;setState('متصل — ليان معك','الجلسة الصوتية لايف. احكي بشكل طبيعي.');}
        else if(cs==='failed'||cs==='disconnected'){
          setMode('');setState('انقطع الاتصال الصوتي','اضغط زر الإغلاق ثم جرّب مرة ثانية.');
        }
      };
      const offer=await state.pc.createOffer({offerToReceiveAudio:true});
      await state.pc.setLocalDescription(offer);
      const response=await fetch(apiBase()+'/api/voice-avatar/realtime-call',{method:'POST',headers:{'Content-Type':'application/sdp','Accept':'application/sdp'},body:offer.sdp,cache:'no-store'});
      const answer=await response.text();
      if(!response.ok){
        if(response.status===402||response.status===429||/insufficient_quota|credit_balance_exhausted|no credits remaining/i.test(answer)){
          cleanup();
          s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
          setState('الصوت المباشر غير متاح حالياً','عم ننتقل تلقائياً لوضع الصوت المجاني على المتصفح.');
          await startFreeBrowserVoice();
          return false;
        }
        throw new Error(answer||('Voice backend HTTP '+response.status));
      }
      if(!/^v=0(?:\r?\n|$)/.test(answer.trim()))throw new Error('الخادم أعاد SDP غير صالح.');
      await state.pc.setRemoteDescription({type:'answer',sdp:answer});
      state.offerPending=false;
    }catch(err){
      console.error('Layan voice start failed',err);
      state.offerPending=false;state.running=false;setMode('');
      setState('تعذر تشغيل صوت ليان',err?.message||'تحقق من إذن الميكروفون والاتصال.');
      if(state.mic||state.pc){cleanup();s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';}
    }
    return false;
  }
  function toggle(){return state.running?closeLayanVoice():startLayanVoice();}
  window.startLayanVoice=startLayanVoice;
  window.stopLayanVoice=closeLayanVoice;
  window.closeLayanVoice=closeLayanVoice;
  window.openLayanVoice=startLayanVoice;
  window.toggleLayanVoice=toggle;
  window.demoLayanVoice=async function(){
    const s=stage();if(!s)return;
    s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
    text('layanVoiceText','للتأكد من المسار الحقيقي، اضغط «تحدث مع ليان» واسمح بالميكروفون.');
    setState('ليان جاهزة','هذا الاختبار لا يستخدم صوتاً تجريبياً مزيفاً.');
  };
  function bind(){
    const b=document.getElementById('layanVoiceEntry');
    if(b&&!b.dataset.layanCanonicalBound){
      b.dataset.layanCanonicalBound='1';
      b.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();startLayanVoice();return false};
    }
    const start=document.getElementById('layanStart');
    if(start&&!start.dataset.layanCanonicalBound){
      start.dataset.layanCanonicalBound='1';
      start.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();toggle();return false};
    }
    const close=document.querySelector('.layanClose');
    if(close&&!close.dataset.layanCanonicalBound){close.dataset.layanCanonicalBound='1';close.onclick=e=>{e.preventDefault();closeLayanVoice();return false};}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
  window.addEventListener('load',bind);
})();