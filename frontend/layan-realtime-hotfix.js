/* Company AI — Layan multilingual live voice
 * Canonical free path: browser microphone -> Company AI/Gemini -> browser voice.
 * No OpenAI Realtime dependency and no quota-based fallback.
 */
(function(){
'use strict';
const VERSION='20260919-09';
const state={recognition:null,running:false,busy:false,history:[],speaking:false,wakeLock:null,audio:null,audioCtx:null,analyser:null,raf:null};
window.LayanVoiceBridge={mode:'browser-live-gemini-multilingual',version:VERSION};
const stage=()=>document.getElementById('layanVoiceStage');
async function keepScreenAwake(){try{if(!('wakeLock' in navigator))return; if(state.wakeLock?.released===false)return; state.wakeLock=await navigator.wakeLock.request('screen'); state.wakeLock.addEventListener('release',()=>{state.wakeLock=null;});}catch(_){} }
async function refreshScreenAwake(){if(state.running)await keepScreenAwake();}
const text=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
const setState=(a,b)=>{text('layanVoiceState',a);text('layanVoiceSub',b||'');const s=stage();if(s)s.setAttribute('data-layan-status',a)};
const setMode=m=>{const s=stage();if(!s)return;s.classList.remove('listening','speaking');if(m)s.classList.add(m)};
const setAudioLevel=v=>{const s=stage();if(s)s.style.setProperty('--audio-level',String(Math.max(0,Math.min(1,v||0))))};
function stopAudioMeter(){if(state.raf)cancelAnimationFrame(state.raf);state.raf=null;if(state.audioCtx){try{state.audioCtx.close()}catch(_){}}state.audioCtx=null;state.analyser=null;setAudioLevel(0)}
function startAudioMeter(audio){stopAudioMeter();try{const C=window.AudioContext||window.webkitAudioContext;if(!C)return;const ctx=new C(),an=ctx.createAnalyser();an.fftSize=256;an.smoothingTimeConstant=.72;const src=ctx.createMediaElementSource(audio);src.connect(an);an.connect(ctx.destination);state.audioCtx=ctx;state.analyser=an;const data=new Uint8Array(an.fftSize);const tick=()=>{if(!state.analyser||state.audio!==audio)return;an.getByteTimeDomainData(data);let sum=0;for(let i=0;i<data.length;i++){const x=(data[i]-128)/128;sum+=x*x}const rms=Math.min(1,Math.sqrt(sum/data.length)*3.8);setAudioLevel(rms);state.raf=requestAnimationFrame(tick)};tick();}catch(_){setAudioLevel(.35)}}
function startSyntheticMeter(){stopAudioMeter();let t=0;const tick=()=>{if(!state.speaking)return;t+=.16;setAudioLevel(.18+.16*(.5+.5*Math.sin(t*2.7))+.08*(.5+.5*Math.sin(t*5.1)));state.raf=requestAnimationFrame(tick)};tick()}
function language(){
 const n=(document.documentElement.lang||navigator.language||'en').toLowerCase();
 return n.split('-')[0];
}
function voiceFor(lang){
 if(!('speechSynthesis' in window))return null;
 const vs=speechSynthesis.getVoices();
 return (lang==='ar'&&vs.find(v=>/^ar-(lb|jo|sy)/i.test(v.lang)))||vs.find(v=>v.lang.toLowerCase().startsWith(lang.toLowerCase()+'-'))||vs.find(v=>v.lang.toLowerCase()===lang.toLowerCase())||null;
}
function cleanup(){
 if(state.audio){try{state.audio.pause();state.audio.currentTime=0}catch(_){}} state.audio=null;
 if(state.recognition){try{state.recognition.onend=null;state.recognition.onerror=null;state.recognition.stop()}catch(_){}}
 if('speechSynthesis' in window)try{speechSynthesis.cancel()}catch(_){}
 if(state.wakeLock){try{state.wakeLock.release()}catch(_){} state.wakeLock=null;}
 state.recognition=null;state.running=false;state.busy=false;state.speaking=false;setMode('');
}
function speak(reply,lang){
 const s=stage();text('layanVoiceText',reply);
 if(!('speechSynthesis' in window)){setState('ليان جاهزة','الرد ظهر نصياً لأن إخراج الصوت غير مدعوم في هذا المتصفح.');return}
 speechSynthesis.cancel();
 const u=new SpeechSynthesisUtterance(reply);u.lang=lang||language();u.rate=1.0;u.pitch=1;
 const v=voiceFor(u.lang);if(v)u.voice=v;
 u.onstart=()=>{state.speaking=true;setMode('speaking');startSyntheticMeter();setState('ليان تتحدث…','عم تحكي معك بنفس لغة المحادثة.');};
 u.onend=()=>{state.speaking=false;stopAudioMeter();setMode('');if(state.running)setTimeout(startRecognition,250);};
 u.onerror=()=>{state.speaking=false;stopAudioMeter();setMode('');if(state.running)setTimeout(startRecognition,250);};
 speechSynthesis.speak(u);
}
async function speakWithGeminiTTS(reply,lang){
 try{
  const aid=await fetch((window.COMPANY_AI_API_BASE||'')+'/api/sales-agent/public/config',{cache:'no-store'}).then(r=>r.json()).then(d=>d.build_id);
  const r=await fetch((window.COMPANY_AI_API_BASE||'')+'/api/sales-agent/'+aid+'/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:reply,language:lang})});
  if(!r.ok)throw Error('tts_unavailable');
  const d=await r.json(); if(!d.audio_base64)throw Error('tts_empty');
  const audio=new Audio('data:audio/wav;base64,'+d.audio_base64); audio.preload='auto';
  state.audio=audio; state.speaking=true; setMode('speaking'); startAudioMeter(audio); setState('ليان تتحدث…','صوت ليان الطبيعي بنفس لغة المحادثة.');
  await audio.play();
  await new Promise(resolve=>{audio.onended=resolve;audio.onerror=resolve;});
  state.audio=null;state.speaking=false;stopAudioMeter();setMode('');if(state.running)setTimeout(startRecognition,250);return true;
 }catch(_){return false}
}
async function askGemini(message,lang){
 state.busy=true;setMode('speaking');setState('ليان تفهم طلبك…','عم تحلل المعنى والسياق قبل الرد.');
 try{
   const aid=await fetch((window.COMPANY_AI_API_BASE||'')+'/api/sales-agent/public/config',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error('تعذر الوصول لمحرك ليان');return r.json()});
   const r=await fetch((window.COMPANY_AI_API_BASE||'')+'/api/sales-agent/'+aid.build_id+'/conversation',{
     method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({message,language:lang,channel:'voice',assistant:'layan',history:state.history.slice(-10)})
   });
   const d=await r.json();if(!r.ok)throw Error(d.detail||'تعذر الحصول على رد ليان');
   const reply=String(d.reply||'').trim();if(!reply)throw Error('رد فارغ');
   const outLang=(d.language||lang||'en').split('-')[0];
   state.history.push({role:'user',text:message},{role:'assistant',text:reply});
   state.busy=false; if(!(await speakWithGeminiTTS(reply,outLang))) speak(reply,outLang); return true;
 }catch(e){
   state.busy=false;setMode('');setState('تعذر الرد حالياً',e.message||'حاول مرة ثانية.');return false;
 }
}
function startRecognition(){
 if(!state.running||state.busy||state.speaking)return false;
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SR){setState('الصوت غير مدعوم','استخدم متصفحاً يدعم الميكروفون والتعرف على الكلام.');return false}
 const r=new SR();state.recognition=r;
 const lang=language();r.lang=lang==='zh'?'zh-CN':lang==='pt'?'pt-BR':lang==='en'?'en-US':lang==='fr'?'fr-FR':lang==='de'?'de-DE':lang==='es'?'es-ES':lang==='it'?'it-IT':lang==='ja'?'ja-JP':lang==='ko'?'ko-KR':lang==='ru'?'ru-RU':lang==='tr'?'tr-TR':lang==='nl'?'nl-NL':'ar-LB';
 r.interimResults=true;r.continuous=true;r.maxAlternatives=1;
 let heard='';
 r.onstart=()=>{setMode('listening');setState('ليان تستمع إليك…','احكي بلغتك وبلهجتك بشكل طبيعي.');};
 let silenceTimer=null;
 const clearSilence=()=>{if(silenceTimer){clearTimeout(silenceTimer);silenceTimer=null;}};
 const armSilence=()=>{
   clearSilence();
   silenceTimer=setTimeout(()=>{
     if(!state.running||state.busy||state.speaking)return;
     const finalText=heard.trim();
     if(!finalText)return;
     heard='';
     try{r.stop()}catch(_){}
     setState('ليان تفهم طلبك…','عم أجهز الرد.');
     askGemini(finalText,lang);
   },3000);
 };
 r.onresult=e=>{
   let interim='';
   for(let i=e.resultIndex;i<e.results.length;i++){const t=(e.results[i][0]?.transcript||'').trim();if(e.results[i].isFinal)heard+=(heard?' ':'')+t;else interim+=(interim?' ':'')+t}
   const shown=(heard+' '+interim).trim();if(shown)text('layanVoiceText',shown);
   if(shown)armSilence();
 };
 r.onerror=e=>{state.recognition=null;if(e.error==='not-allowed'){setState('الميكروفون غير مسموح','اسمح بالميكروفون ثم جرّب مرة ثانية.');return}if(state.running&&!state.busy)setTimeout(startRecognition,500)};
 r.onend=()=>{clearSilence();state.recognition=null;if(heard.trim()){const finalText=heard.trim();heard='';if(state.running&&!state.busy&&!state.speaking)askGemini(finalText,lang)}else if(state.running&&!state.busy)setTimeout(startRecognition,300)};
 try{r.start();return true}catch(_){state.recognition=null;return false}
}
async function start(){
 if(state.running)return;
 const s=stage();if(!s)return false;
 state.running=true;state.history=[];
 s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
 setState('ليان جاهزة…','احكي معها بأي لغة أو لهجة.');
 try{
  if(navigator.mediaDevices?.getUserMedia){const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(t=>t.stop())}
  await keepScreenAwake();
 }catch(e){state.running=false;setState('الميكروفون غير مفعّل','اسمح بالوصول إلى الميكروفون ثم جرّب مرة ثانية.');return false}
 startRecognition();return false;
}
function stop(){
 cleanup();const s=stage();if(s){s.classList.remove('open');s.setAttribute('aria-hidden','true')};document.body.style.overflow='';
}
function toggle(){return state.running?stop():start()}
function bind(){
 const entry=document.getElementById('layanVoiceEntry');
 if(entry&&!entry.dataset.layanCanonicalBound){entry.dataset.layanCanonicalBound='1';entry.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();start();return false}}
 const btn=document.getElementById('layanStart');
 if(btn&&!btn.dataset.layanCanonicalBound){btn.dataset.layanCanonicalBound='1';btn.onclick=e=>{e.preventDefault();e.stopImmediatePropagation();toggle();return false}}
 document.querySelectorAll('.layanClose').forEach(b=>{if(!b.dataset.layanCanonicalBound){b.dataset.layanCanonicalBound='1';b.onclick=e=>{e.preventDefault();stop();return false}}});
}
window.startLayanVoice=start;window.stopLayanVoice=stop;window.closeLayanVoice=stop;window.openLayanVoice=start;window.toggleLayanVoice=toggle;
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
window.addEventListener('load',bind);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')refreshScreenAwake();});
if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=()=>speechSynthesis.getVoices();
})();

/* ROOT OFFICE-VISUAL FIX 20260919: create the voice office image from the voice runtime itself. */
(function ensureLayanOfficeVisual(){
  const OFFICE_SRC='/assets/layan-office.webp?v=20260919-rootfix2';
  const CSS_ID='layan-office-rootfix-css';
  function installCss(){if(document.getElementById(CSS_ID))return;const s=document.createElement('style');s.id=CSS_ID;s.textContent='.layanVoiceVisual{position:relative!important;overflow:hidden!important;background:#071322!important}.layanVoiceVisual .layanOfficeDedicated{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;display:block!important;visibility:visible!important;opacity:1!important;object-fit:cover!important;object-position:center center!important;z-index:1!important}.layanVoiceVisual .layanVoicePortraitWrap{display:none!important}.layanVoiceVisual .layanVoiceGlow{z-index:2!important}.layanVoiceVisual .layanVoiceOfficeBadge{z-index:5!important}';(document.head||document.documentElement).appendChild(s)}
  function mount(){installCss();const v=document.querySelector('.layanVoiceVisual');if(!v)return false;let img=v.querySelector('.layanOfficeDedicated');if(!img){img=document.createElement('img');img.className='layanOfficeDedicated';img.alt='مكتب ليان';img.decoding='async';img.loading='eager';v.insertBefore(img,v.firstChild)}if(img.dataset.rootfix!=='2'){img.dataset.rootfix='2';img.src=OFFICE_SRC}return true}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();window.addEventListener('pageshow',mount);let tries=0;const timer=setInterval(()=>{if(mount()||++tries>20)clearInterval(timer)},250);
})();
