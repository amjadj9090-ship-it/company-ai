/* Company AI — Layan Realtime hotfix v6 */
(function(){
'use strict';
var S={pc:null,mic:null,dc:null,audio:null,root:null,running:false,busy:false};
var API='https://company-ai-0mya.onrender.com';
function overlay(){
  if(S.root)return S.root;
  var r=document.createElement('div');
  r.id='layanRealtimeHotfix';
  r.innerHTML='<style>#layanRealtimeHotfix{position:fixed;inset:0;z-index:2147483647;display:none;background:#07111d url("assets/layan-office.webp") center/cover no-repeat;font-family:Arial,Tahoma,sans-serif}#layanRealtimeHotfix.open{display:block}#layanRealtimeHotfix:before{content:"";position:absolute;inset:0;background:rgba(2,8,16,.28)}#layanRealtimeHotfix .box{position:absolute;right:24px;top:24px;bottom:24px;width:min(410px,calc(100vw - 48px));background:rgba(250,252,255,.98);border-radius:24px;padding:24px;box-sizing:border-box;display:flex;flex-direction:column;box-shadow:0 20px 70px rgba(0,0,0,.45)}#layanRealtimeHotfix h2{margin:0;color:#10213a}#layanRealtimeHotfix .status{margin-top:7px;color:#65768d}#layanRealtimeHotfix .msg{margin-top:22px;background:#fff;border:1px solid #dbe5f2;border-radius:16px;padding:16px;min-height:90px;line-height:1.7;color:#263b55;white-space:pre-wrap}#layanRealtimeHotfix .end{margin-top:auto;border:0;border-radius:14px;padding:15px;background:#b52243;color:#fff;font-weight:800;font-size:16px;cursor:pointer}#layanRealtimeHotfix .close{position:absolute;right:16px;top:16px;border:0;border-radius:50%;width:40px;height:40px;background:#edf2f8;font-size:22px;cursor:pointer}#layanRealtimeHotfix .live{margin-top:20px;text-align:center;font-weight:800;color:#233b5c}@media(max-width:700px){#layanRealtimeHotfix .box{left:12px;right:12px;top:auto;bottom:12px;width:auto;height:55dvh;min-height:330px}}</style><div class="box"><button class="close" id="lhClose" type="button">×</button><h2>ليان — جلسة صوتية مباشرة</h2><div class="status" id="lhStatus">جاري التحضير…</div><div class="live" id="lhLive">الميكروفون رح يشتغل بشكل مستمر</div><div class="msg" id="lhMsg">جاري إنشاء الاتصال…</div><button class="end" id="lhEnd" type="button">إنهاء المحادثة</button></div>';
  document.body.appendChild(r);
  r.querySelector('#lhClose').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
  r.querySelector('#lhEnd').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
  S.root=r;
  return r;
}
function set(status,msg){var r=overlay();r.classList.add('open');r.querySelector('#lhStatus').textContent=status;r.querySelector('#lhMsg').textContent=msg||''}
function sessionConfig(){return {type:'realtime',model:'gpt-realtime-2.1',instructions:'You are Layan, the live voice assistant for Company AI. Detect visitor language automatically. For Arabic, speak clear Syrian/Levantine Arabic and never Egyptian phrasing. Be natural and concise. Do not claim sensitive financial, legal, transfer, withdrawal, or contract actions are completed without owner approval.',audio:{input:{transcription:{model:'gpt-4o-transcribe'},turn_detection:{type:'semantic_vad',eagerness:'auto',create_response:true,interrupt_response:true}},output:{voice:'marin'}},output_modalities:['audio']}}
function looksLikeVoice(el){
  if(!el)return false;
  var x=el.closest('button,[role="button"],a,[onclick],.voiceChoice');
  if(!x)return false;
  var t=((x.innerText||x.textContent||'')+' '+(x.getAttribute('aria-label')||'')+' '+(x.getAttribute('title')||'')+' '+(x.className||'')).toLowerCase();
  return /voice|audio|speak|talk|live|صوت|صوتي|صوتية|محادثة صوت|دردشة صوت|تكلم|تحدث/.test(t);
}
function interceptVoiceClicks(){
  document.addEventListener('pointerdown',function(e){
    if(S.root && S.root.contains(e.target))return;
    if(looksLikeVoice(e.target)){e.preventDefault();e.stopImmediatePropagation();start()}
  },true);
  document.addEventListener('click',function(e){
    if(S.root && S.root.contains(e.target))return;
    if(looksLikeVoice(e.target)){e.preventDefault();e.stopImmediatePropagation();start()}
  },true);
}
async function start(){
  if(S.running||S.busy)return;
  S.busy=true;S.running=true;set('جاري الاتصال…','عم نطلب جلسة صوت آمنة من الخادم…');
  try{
    var res=await fetch(API+'/api/voice-avatar/public-session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var d=await res.json().catch(function(){return{}});
    if(!res.ok)throw Error(d.detail||('الخادم أعاد HTTP '+res.status));
    if(!d.value||!String(d.value).startsWith('ek_'))throw Error('الخادم لم يرجّع مفتاح Realtime صالح');
    set('تم الاتصال بالخادم','السماح بالميكروفون مطلوب لبدء المحادثة.');
    S.mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    S.pc=new RTCPeerConnection();
    S.audio=document.createElement('audio');S.audio.autoplay=true;S.audio.playsInline=true;S.audio.setAttribute('aria-hidden','true');S.audio.style.position='fixed';S.audio.style.width='1px';S.audio.style.height='1px';S.audio.style.opacity='0';S.audio.style.pointerEvents='none';document.body.appendChild(S.audio);
    S.pc.ontrack=function(e){if(e.streams&&e.streams[0])S.audio.srcObject=e.streams[0];S.audio.play().catch(function(){})};
    S.mic.getTracks().forEach(function(t){S.pc.addTrack(t,S.mic)});
    S.dc=S.pc.createDataChannel('oai-events');
    S.dc.onopen=function(){set('لايف — ليان عم تسمعك','الميكروفون شغّال. احكي بشكل طبيعي، وفيك تقاطع ليان بأي لحظة.')};
    S.dc.onmessage=function(e){var x;try{x=JSON.parse(e.data)}catch(_){return}if(x.type==='input_audio_buffer.speech_started')set('ليان عم تسمعك','كمل كلامك…');else if(x.type==='response.created')set('ليان عم ترد','فيك تقاطعها بأي لحظة.');else if(x.type==='response.audio_transcript.done')set('ليان عم تحكي',x.transcript||'');else if(x.type==='response.done')set('لايف — احكي مع ليان','الميكروفون شغّال بشكل مستمر.');else if(x.type==='error')set('خطأ من جلسة الصوت',(x.error&&x.error.message)||'تعذر إكمال الجلسة.')};
    S.pc.onconnectionstatechange=function(){if(!S.pc)return;if(S.pc.connectionState==='connected')set('لايف — احكي مع ليان','الجلسة مستمرة حتى تضغط إنهاء.');else if(S.pc.connectionState==='failed')set('تعذر الاتصال','الاتصال الصوتي فشل. الجلسة بقيت مفتوحة حتى تشوف الخطأ.')};
    var offer=await S.pc.createOffer();await S.pc.setLocalDescription(offer);
    var fd=new FormData();fd.append('sdp',S.pc.localDescription.sdp);fd.append('session',JSON.stringify(sessionConfig()));
    var rr=await fetch('https://api.openai.com/v1/realtime/calls',{method:'POST',headers:{Authorization:'Bearer '+d.value},body:fd});
    var answer=await rr.text();if(!rr.ok)throw Error(answer||('Realtime أعاد HTTP '+rr.status));
    await S.pc.setRemoteDescription({type:'answer',sdp:answer});
    set('لايف — احكي مع ليان','تم فتح المحادثة الصوتية. احكي الآن.');
  }catch(e){console.error('Layan hotfix v6 error',e);set('تعذر تشغيل المحادثة الصوتية',e.message||'خطأ غير معروف.');S.running=false}
  finally{S.busy=false}
}
function stop(){S.running=false;S.busy=false;if(S.dc){try{S.dc.close()}catch(_){ }S.dc=null}if(S.pc){try{S.pc.close()}catch(_){ }S.pc=null}if(S.mic){S.mic.getTracks().forEach(function(t){try{t.stop()}catch(_){ }});S.mic=null}if(S.audio){try{S.audio.pause();S.audio.srcObject=null;S.audio.remove()}catch(_){ }S.audio=null}if(S.root)S.root.classList.remove('open')}
window.startLayanVoice=start;window.openLayanVoice=start;window.stopLayanVoice=stop;window.closeLayanVoice=stop;window.toggleLayanVoice=function(){S.running?stop():start()};
interceptVoiceClicks();
})();
