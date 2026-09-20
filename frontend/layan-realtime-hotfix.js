/* Company AI — Layan voice ROOT FIX 20260920 (Updated for Mobile & Natural VAD) */
(function(){ 
    'use strict'; 
    const VERSION='20260920-mediarecorder-natural-v2'; 
    const state={stream:null,recorder:null,chunks:[],recording:false,busy:false,speaking:false,history:[],silenceTimer:null,startedAt:0,levelTimer:null,wakeLock:null}; 
    window.LayanVoiceBridge={mode:'mediarecorder-gemini-audio',version:VERSION};

    const stage=()=>document.getElementById('layanVoiceStage'); 
    const text=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v}; 
    const setMode=m=>{const s=stage();if(!s)return;s.classList.remove('listening','speaking');if(m)s.classList.add(m)}; 
    const setState=(a,b)=>{text('layanVoiceState',a);text('layanVoiceSub',b||'')}; 
    const lang=()=>String(document.documentElement.lang||navigator.language||'en').toLowerCase().split('-')[0]; 
    const mime=()=>{const a=['audio/webm;codecs=opus','audio/webm','audio/mp4'];return a.find(x=>window.MediaRecorder&&MediaRecorder.isTypeSupported(x))||''};

    function blurKeyboard(){ try{ const a=document.activeElement; if(a&&typeof a.blur==='function')a.blur(); if(document.body)document.body.focus?.({preventScroll:true}); }catch(_){} }

    async function keepAwake(){ try{ if('wakeLock' in navigator){ if(!state.wakeLock||state.wakeLock.released)state.wakeLock=await navigator.wakeLock.request('screen'); } }catch(){} } 
    function releaseAwake(){try{state.wakeLock?.release()}catch(){}state.wakeLock=null}

    function stopLevel(){ if(state.levelTimer)clearInterval(state.levelTimer); state.levelTimer=null; const s=stage();if(s)s.style.setProperty('--audio-level','0'); } 
    function startLevel(){ 
        stopLevel(); 
        if(!state.stream)return; 
        try{ 
            const C=window.AudioContext||window.webkitAudioContext;if(!C)return; 
            const ctx=new C(),src=ctx.createMediaStreamSource(state.stream),an=ctx.createAnalyser(); 
            an.fftSize=256;src.connect(an);const data=new Uint8Array(an.fftSize); 
            state.levelTimer=setInterval(()=>{ 
                if(!state.recording){ctx.close().catch(()=>{});stopLevel();return} 
                an.getByteTimeDomainData(data);let sum=0; 
                for(const n of data){const x=(n-128)/128;sum+=x*x} 
                const rms=Math.min(1,Math.sqrt(sum/data.length)*4); 
                const s=stage();if(s)s.style.setProperty('--audio-level',String(rms)); 
                if(state.recording && rms>0.03) armSilence(); 
            },80); 
        }catch(_){} 
    }

    function stopStream(){ if(state.stream){state.stream.getTracks().forEach(t=>{try{t.stop()}catch(){}});state.stream=null} stopLevel(); } 
    function cleanup(){ 
        if(state.silenceTimer)clearTimeout(state.silenceTimer); 
        state.silenceTimer=null; 
        try{if(state.recorder&&state.recorder.state!=='inactive')state.recorder.stop()}catch(){} 
        state.recorder=null;state.recording=false;state.busy=false;state.speaking=false; 
        stopStream();releaseAwake();setMode(''); 
    }

    function output(reply,outLang){ 
        const s=stage();text('layanVoiceText',reply); 
        // الربط الصحيح لصورة ليان داخل واجهة المحادثة (Office Chat) مع حماية الـ Fallback
        const imgEl = s?.querySelector('.layanVoicePortrait') || s?.querySelector('img');
        if(imgEl && !imgEl.src.includes('layan')) {
            imgEl.src = 'assets/layan-office.webp';
            imgEl.onerror = () => { imgEl.src = 'assets/layan-avatar.png'; };
        }

        if(!('speechSynthesis' in window)){setState('ليان جاهزة','الرد ظهر نصياً لأن إخراج الصوت غير متاح.');return} 
        try{speechSynthesis.cancel()}catch(_){} 
        const u=new SpeechSynthesisUtterance(reply); 
        u.lang=outLang||lang();u.rate=.96;u.pitch=1; 
        const voices=speechSynthesis.getVoices(); 
        const v=voices.find(x=>x.lang.toLowerCase().startsWith(u.lang.toLowerCase()+'-'))||voices.find(x=>x.lang.toLowerCase()===u.lang.toLowerCase()); 
        if(v)u.voice=v; 
        
        u.onstart=()=>{state.speaking=true;setMode('speaking');setState('ليان تتحدث…','بعد ما أخلص، رح أسمعك.');}; 
        u.onend=()=>{state.speaking=false;setMode('');cleanup();if(state.startedAt>0)beginRecording()}; 
        u.onerror=()=>{state.speaking=false;setMode('');cleanup();if(state.startedAt>0)beginRecording()}; 
        speechSynthesis.speak(u); 
    }

    async function sendAudio(blob){ 
        state.busy=true;setMode('speaking');setState('ليان تحلل طلبك…','عم أسمع التسجيل وأفهم المعنى قبل ما أجاوب.'); 
        try{ 
            const b64=await new Promise((resolve,reject)=>{ const fr=new FileReader();fr.onload=()=>resolve(String(fr.result).split(',')[1]||'');fr.onerror=reject;fr.readAsDataURL(blob); }); 
            const r=await fetch('/launch-api/chat-audio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ message:'voice input',language:lang(),audio_base64:b64,mime_type:blob.type||'audio/webm', history:state.history.slice(-10).map(x=>({role:x.role,content:x.content})) })}); 
            const d=await r.json().catch(()=>({})); 
            if(!r.ok)throw Error(d.error||'تعذر الوصول لمحرك ليان'); 
            const reply=String(d.reply||'').trim();if(!reply)throw Error('رد فارغ'); 
            state.history.push({role:'user',content:'[voice]'}, {role:'assistant',content:reply}); 
            state.busy=false;state.startedAt=Date.now(); 
            output(reply,d.language||lang()); 
        }catch(e){ 
            state.busy=false;setMode('');setState('تعذر الرد حالياً',e.message||'حاول مرة ثانية.'); 
            if(state.startedAt>0)setTimeout(beginRecording,900); 
        } 
    }

    function finishRecording(){ 
        if(!state.recording)return; 
        if(state.silenceTimer)clearTimeout(state.silenceTimer);state.silenceTimer=null; 
        state.recording=false; 
        const r=state.recorder;state.recorder=null; 
        try{if(r&&r.state!=='inactive')r.stop()}catch(_){} 
    }

    // تعديل VAD الطبيعي ليكون 3500ms (3.5 ثوانٍ) لمنع القطع المبكر أثناء التفكير
    function armSilence(){ 
        if(state.silenceTimer)clearTimeout(state.silenceTimer); 
        state.silenceTimer=setTimeout(finishRecording,3500); 
    }

    function beginRecording(){ 
        if(!state.startedAt||state.busy||state.speaking||state.recording)return false; 
        if(!state.stream){start();return false} 
        const type=mime(); 
        try{ 
            state.chunks=[];state.recorder=type?new MediaRecorder(state.stream,{mimeType:type}):new MediaRecorder(state.stream); 
            const r=state.recorder; 
            r.ondataavailable=e=>{if(e.data&&e.data.size)state.chunks.push(e.data)}; 
            r.onerror=()=>{state.recording=false;setState('تعذر التقاط الصوت','حاول مرة ثانية.');setTimeout(beginRecording,700)}; 
            r.onstop=()=>{ 
                const blob=new Blob(state.chunks,{type:r.mimeType||type||'audio/webm'}); 
                state.chunks=[];state.recorder=null; 
                if(blob.size>0)sendAudio(blob);else if(state.startedAt>0)setTimeout(beginRecording,300); 
            }; 
            r.start(250); 
            state.recording=true;setMode('listening');setState('ليان تستمع إليك…','احكي براحتك، ولما توقف لفترة رح أرسل كلامك.'); 
            startLevel();armSilence(); 
            return true; 
        }catch(e){ 
            state.recording=false;state.recorder=null;setState('تعذر تشغيل الميكروفون','جرّب الضغط مرة ثانية.');return false; 
        } 
    }

    async function start(){ 
        if(state.recording||state.busy||state.speaking)return false; 
        const s=stage();if(!s)return false; 
        blurKeyboard(); 
        s.classList.add('open');s.setAttribute('aria-hidden','false'); 
        document.body.style.overflow='hidden';document.documentElement.style.overflow='hidden'; 
        setState('ليان جاهزة…','لحظة، عم فعّل الميكروفون.'); 
        try{ 
            if(!navigator.mediaDevices?.getUserMedia)throw Error('هذا المتصفح لا يدعم الميكروفون.'); 
            state.stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}}); 
            await keepAwake(); 
            state.history=[];state.startedAt=Date.now(); 
            setTimeout(beginRecording,180); 
            return false; 
        }catch(e){ 
            stopStream();state.startedAt=0;setState('الميكروفون غير مفعّل','اسمح للموقع بالوصول إلى الميكروفون ثم اضغط مرة ثانية.'); 
            return false; 
        } 
    } 

    function stop(){ cleanup();state.startedAt=0; try{speechSynthesis.cancel()}catch(_){} const s=stage();if(s){s.classList.remove('open','listening','speaking');s.setAttribute('aria-hidden','true')} document.body.style.overflow='';document.documentElement.style.overflow=''; blurKeyboard(); } 
    function toggle(){return state.recording||state.busy||state.speaking?stop():start()}

    function bind(){ 
        blurKeyboard(); 
        const entry=document.getElementById('layanVoiceEntry'); 
        if(entry&&!entry.dataset.layanRootBound){entry.dataset.layanRootBound='1';entry.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();return start()}} 
        const btn=document.getElementById('layanStart'); 
        if(btn&&!btn.dataset.layanRootBound){btn.dataset.layanRootBound='1';btn.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();return toggle()}} 
        document.querySelectorAll('.layanClose').forEach(b=>{if(!b.dataset.layanRootBound){b.dataset.layanRootBound='1';b.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();stop();return false}}}); 
    } 

    window.startLayanVoice=start;window.stopLayanVoice=stop;window.closeLayanVoice=stop;window.openLayanVoice=start;window.toggleLayanVoice=toggle; 
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind(); 
    window.addEventListener('load',bind); 
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&state.startedAt&&!state.recording&&!state.busy&&!state.speaking)beginRecording()}); 
    if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=()=>speechSynthesis.getVoices();

    /* Mobile Responsive Layout & Keyboard Guard (100dvh for Android) */ 
    (function mobileGuard(){ 
        const id='layan-root-mobile-css'; 
        function css(){ 
            if(document.getElementById(id))return; 
            const st=document.createElement('style');st.id=id; 
            st.textContent=`
                html:has(#layanVoiceStage.open),body:has(#layanVoiceStage.open){overflow:hidden!important;width:100%!important;height:100%!important} 
                .layanVoiceStage{width:100vw!important;height:100dvh!important;max-width:100vw!important;max-height:100dvh!important;overflow:hidden!important;position:fixed!important;inset:0!important;z-index:999999!important;} 
                .layanVoiceShell{width:100vw!important;height:100dvh!important;min-height:0!important;overflow:hidden!important} 
                @media(max-width:850px){ 
                    .layanVoiceShell{grid-template-columns:1fr!important;grid-template-rows:minmax(0,50dvh) minmax(0,50dvh)!important} 
                    .layanVoiceBody{padding:10px 12px!important;overflow:auto!important;justify-content:flex-start!important} 
                    .layanVoiceText{min-height:42px!important;max-height:72px!important;padding:9px!important;font-size:14px!important;overflow:auto!important} 
                }
            `; 
            document.head.appendChild(st); 
        } 
        function guard(){ css();blurKeyboard(); } 
        if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',guard,{once:true});else guard(); 
        window.addEventListener('pageshow',guard); 
    })(); 
})();