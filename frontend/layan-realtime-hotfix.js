/* Company AI — Layan multilingual live voice
 * Canonical free path: browser microphone -> Company AI/Gemini -> browser voice.
 * No OpenAI Realtime dependency and no quota-based fallback.
 */
(function(){
'use strict';
const VERSION='20260919-07';
const state={recognition:null,running:false,busy:false,history:[],speaking:false,wakeLock:null};
window.LayanVoiceBridge={mode:'browser-live-gemini-multilingual',version:VERSION};
const stage=()=>document.getElementById('layanVoiceStage');
async function keepScreenAwake(){try{if(!('wakeLock' in navigator))return; if(state.wakeLock?.released===false)return; state.wakeLock=await navigator.wakeLock.request('screen'); state.wakeLock.addEventListener('release',()=>{state.wakeLock=null;});}catch(_){} }
async function refreshScreenAwake(){if(state.running)await keepScreenAwake();}
const text=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
const setState=(a,b)=>{text('layanVoiceState',a);text('layanVoiceSub',b||'');const s=stage();if(s)s.setAttribute('data-layan-status',a)};
const setMode=m=>{const s=stage();if(!s)return;s.classList.remove('listening','speaking');if(m)s.classList.add(m)};
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
 u.onstart=()=>{state.speaking=true;setMode('speaking');setState('ليان تتحدث…','عم تحكي معك بنفس لغة المحادثة.');};
 u.onend=()=>{state.speaking=false;setMode('');if(state.running)setTimeout(startRecognition,250);};
 u.onerror=()=>{state.speaking=false;setMode('');if(state.running)setTimeout(startRecognition,250);};
 speechSynthesis.speak(u);
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
   state.busy=false;speak(reply,outLang);return true;
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
 r.onresult=e=>{
   let interim='';
   for(let i=e.resultIndex;i<e.results.length;i++){const t=(e.results[i][0]?.transcript||'').trim();if(e.results[i].isFinal)heard+=(heard?' ':'')+t;else interim+=(interim?' ':'')+t}
   const shown=(heard+' '+interim).trim();if(shown)text('layanVoiceText',shown);
 };
 r.onerror=e=>{state.recognition=null;if(e.error==='not-allowed'){setState('الميكروفون غير مسموح','اسمح بالميكروفون ثم جرّب مرة ثانية.');return}if(state.running&&!state.busy)setTimeout(startRecognition,500)};
 r.onend=()=>{state.recognition=null;if(heard.trim()){const finalText=heard.trim();heard='';setState('ليان تنتظر أن تنهي كلامك…','كمّل براحتك. لن أرسل الكلام قبل ما تتوقف قليلاً.');setTimeout(()=>{if(state.running&&!state.busy&&!state.speaking)askGemini(finalText,lang)},1800)}else if(state.running&&!state.busy)setTimeout(startRecognition,300)};
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