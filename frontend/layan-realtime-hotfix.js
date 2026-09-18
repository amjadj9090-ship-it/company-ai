/* Company AI — Layan Realtime v17 — mobile-safe voice start + diagnostics */
(function(){
'use strict';
var S={pc:null,stream:null,audio:null,dc:null,root:null,running:false,busy:false,answering:false,lastTap:0,fallbackRec:null};
var API='';
function overlay(){
 if(S.root)return S.root;
 var r=document.createElement('div');r.id='layanRealtimeHotfix';
 r.innerHTML='<style>#layanRealtimeHotfix{position:fixed;inset:0;z-index:2147483647;display:none;background:#07111d url("/assets/layan-office.webp") center/cover no-repeat;font-family:Arial,Tahoma,sans-serif}#layanRealtimeHotfix.open{display:block}#layanRealtimeHotfix:before{content:"";position:absolute;inset:0;background:rgba(2,8,16,.25)}#layanRealtimeHotfix .box{position:absolute;right:24px;top:24px;bottom:24px;width:min(410px,calc(100vw - 48px));background:rgba(250,252,255,.98);border-radius:24px;padding:24px;box-sizing:border-box;display:flex;flex-direction:column;box-shadow:0 20px 70px rgba(0,0,0,.45)}#layanRealtimeHotfix h2{margin:0;color:#10213a;padding-right:42px}#layanRealtimeHotfix .status{margin-top:7px;color:#65768d}#layanRealtimeHotfix .msg{margin-top:22px;background:#fff;border:1px solid #dbe5f2;border-radius:16px;padding:16px;min-height:90px;line-height:1.7;color:#263b55;white-space:pre-wrap}#layanRealtimeHotfix .end{margin-top:auto;border:0;border-radius:14px;padding:15px;background:#b52243;color:#fff;font-weight:800;font-size:16px;cursor:pointer}#layanRealtimeHotfix .close{position:absolute;right:16px;top:16px;border:0;border-radius:50%;width:40px;height:40px;background:#edf2f8;font-size:22px;cursor:pointer}#layanRealtimeHotfix .live{margin-top:20px;text-align:center;font-weight:800;color:#233b5c}@media(max-width:700px){#layanRealtimeHotfix .box{left:12px;right:12px;top:auto;bottom:12px;width:auto;height:55dvh;min-height:330px}}</style><div class="box"><button class="close" id="lhClose" type="button" aria-label="إغلاق">×</button><h2>ليان — جلسة صوتية مباشرة</h2><div class="status" id="lhStatus">جاري التحضير…</div><div class="live" id="lhLive">الميكروفون رح يشتغل بشكل مستمر</div><div class="msg" id="lhMsg">جاري إنشاء الاتصال…</div><button class="end" id="lhEnd" type="button">إنهاء المحادثة</button></div>';
 document.body.appendChild(r);
 r.querySelector('#lhClose').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
 r.querySelector('#lhEnd').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
 S.root=r;return r;
}
function set(status,msg){var r=overlay();r.classList.add('open');r.style.display='block';r.querySelector('#lhStatus').textContent=status;r.querySelector('#lhMsg').textContent=msg||''}
function looksLikeVoice(el){if(!el)return false;var x=el.closest&&el.closest('button,[role="button"],a,[onclick],.voiceChoice,.layanChoice,.layanQuickVoice,[data-voice],[data-action="voice"]');if(!x)x=el;var t=((x.innerText||x.textContent||'')+' '+(x.getAttribute&&x.getAttribute('aria-label')||'')+' '+(x.getAttribute&&x.getAttribute('title')||'')+' '+(x.className||'')+' '+(x.id||'')).toLowerCase();return /voice|audio|speak|talk|live|microphone|mic|صوت|صوتي|صوتية|محادثة صوت|دردشة صوت|تكلم|تحدث|ميكروفون/.test(t)}
function beginFromGesture(e){if(e&&e.type==='click'){e.preventDefault();e.stopPropagation();if(e.stopImmediatePropagation)e.stopImmediatePropagation()}var now=Date.now();if(now-S.lastTap<700)return;S.lastTap=now;if(!S.running&&!S.busy)start()}
function interceptVoiceClicks(){window.addEventListener('click',function(e){if(S.root&&S.root.contains(e.target))return;if(looksLikeVoice(e.target))beginFromGesture(e)},true)}
function bindVoiceButtons(){var nodes=document.querySelectorAll('button,a,[role="button"],.voiceChoice,.layanChoice,.layanQuickVoice,[data-voice],[data-action="voice"]');nodes.forEach(function(n){if(n.dataset&&n.dataset.layanVoiceBound)return;if(looksLikeVoice(n)){if(n.dataset)n.dataset.layanVoiceBound='1';n.addEventListener('click',function(e){beginFromGesture(e)},true)}})}
function sendSessionConfig(){if(!S.dc||S.dc.readyState!=='open')return;S.dc.send(JSON.stringify({type:'session.update',session:{instructions:'You are Layan, the live voice assistant for Company AI. Detect the visitor\'s language and dialect automatically and respond naturally in the same language and dialect when practical. Support all languages and regional dialects; do not restrict the visitor to a fixed Arabic dialect. If the visitor explicitly asks for a particular language or dialect, follow that preference. Be warm, concise and practical. Company AI owner approval is required before transfers, withdrawals, signing contracts, or other non-standard binding commitments. You may discuss services, qualify leads and prepare drafts, but never claim a sensitive commitment was finalized without owner approval.',audio:{input:{noise_reduction:{type:'near_field'},transcription:{model:'gpt-4o-transcribe'},turn_detection:{type:'server_vad',threshold:0.5,prefix_padding_ms:300,silence_duration_ms:650,create_response:true,interrupt_response:true}},output:{voice:'marin'}},output_modalities:['audio']}}))}
function onEvent(ev){try{var x=typeof ev==='string'?JSON.parse(ev):ev;if(!x||!x.type)return;console.log('Layan Realtime event',x.type);if(x.type==='session.created')set('تم الاتصال بليان','احكي بشكل طبيعي… الميكروفون شغّال.');else if(x.type==='session.updated')set('لايف — احكي مع ليان','الجلسة الصوتية جاهزة. احكي بشكل طبيعي.');else if(x.type==='input_audio_buffer.speech_started')set('ليان عم تسمعك','كمل كلامك… فيك تقاطعها بأي لحظة.');else if(x.type==='response.created'){S.answering=true;set('ليان عم ترد','فيك تقاطعها بأي لحظة.')}else if(x.type==='response.audio_transcript.delta')set('ليان عم تحكي',String(x.delta||''));else if(x.type==='response.audio_transcript.done')set('ليان عم تحكي',x.transcript||'');else if(x.type==='response.done'){S.answering=false;set('لايف — احكي مع ليان','المحادثة مستمرة والميكروفون شغّال.')}else if(x.type==='error'){console.error('Layan realtime server error',x);set('مشكلة بالاتصال الصوتي',x.error&&x.error.message?x.error.message:'تعذر إكمال الاتصال.')}}catch(e){console.warn('Realtime event parse error',e)}}
async function start(){if(S.running||S.busy)return;S.busy=true;S.running=true;set('جاري الاتصال…','عم نجهّز الميكروفون والاتصال الصوتي الآمن…');try{if(location.protocol!=='https:'&&location.hostname!=='localhost')throw Error('يجب فتح Company AI عبر HTTPS حتى يعمل الميكروفون');if(!window.RTCPeerConnection)throw Error('المتصفح لا يدعم WebRTC');if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)throw Error('Chrome لم يمنح الصفحة صلاحية الوصول للميكروفون. افتح الموقع مباشرة في Chrome وليس داخل نافذة ChatGPT.');set('طلب إذن الميكروفون…','اسمح للمتصفح باستخدام الميكروفون عندما تظهر نافذة الإذن.');var stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true,channelCount:1}});S.stream=stream;set('تم تشغيل الميكروفون…','جاري إنشاء اتصال ليان…');var pc=new RTCPeerConnection();S.pc=pc;stream.getTracks().forEach(function(track){pc.addTrack(track,stream)});var audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.style.display='none';document.body.appendChild(audio);S.audio=audio;pc.ontrack=function(e){if(e.streams&&e.streams[0]){audio.srcObject=e.streams[0];audio.play().catch(function(err){console.warn('Layan remote audio play blocked',err)})}};var dc=pc.createDataChannel('oai-events');S.dc=dc;dc.onopen=function(){sendSessionConfig();set('تم الاتصال بليان','احكي بشكل طبيعي… الميكروفون شغّال.')};dc.onmessage=function(e){onEvent(e.data)};dc.onerror=function(e){console.error('Layan data channel error',e);set('مشكلة بقناة الصوت','تعذر نقل أحداث المحادثة.')};pc.onconnectionstatechange=function(){console.log('Layan WebRTC state',pc.connectionState);if(pc.connectionState==='connected')set('لايف — احكي مع ليان','المحادثة الصوتية مفتوحة. احكي بشكل طبيعي.');if(pc.connectionState==='failed'||pc.connectionState==='disconnected')set('انقطع الاتصال الصوتي','الاتصال انقطع. احكي من جديد لإعادة المحاولة.')};var offer=await pc.createOffer();await pc.setLocalDescription(offer);await new Promise(function(resolve){if(pc.iceGatheringState==='complete')return resolve();function done(){if(pc.iceGatheringState==='complete'){pc.removeEventListener('icegatheringstatechange',done);resolve()}}pc.addEventListener('icegatheringstatechange',done);setTimeout(resolve,7000)});var local=pc.localDescription;if(!local||!local.sdp)throw Error('تعذر إنشاء SDP للاتصال الصوتي');var answerRes=await fetch('/api/voice-avatar/realtime-call',{method:'POST',headers:{'Content-Type':'application/sdp','Accept':'application/sdp'},body:local.sdp});var answer=await answerRes.text();if(!answerRes.ok)throw Error('خادم الصوت أعاد HTTP '+answerRes.status+': '+answer.slice(0,500));if(!answer.trim().startsWith('v='))throw Error('خادم الصوت لم يرجع SDP صالحاً');await pc.setRemoteDescription({type:'answer',sdp:answer});set('لايف — احكي مع ليان','المحادثة الصوتية مفتوحة. الميكروفون شغّال بشكل مستمر.')}catch(e){console.error('Layan realtime v17 error',e);set('تعذر تشغيل المحادثة الصوتية',e&&e.message?e.message:'خطأ غير معروف.');S.running=false;var why=String(e&&e.message||e);cleanup();fallbackVoice(why)}finally{S.busy=false}}

function fallbackVoice(reason){
 try{
  cleanup();
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR)throw Error('المتصفح لا يدعم التعرف على الكلام');
  var rec=new SR();
  rec.lang=(document.documentElement.lang||'ar-SA');
  rec.interimResults=false;
  rec.continuous=false;
  S.fallbackRec=rec;
  set('وضع الصوت البديل','ليان جاهزة للاستماع… احكي الآن.');
  rec.onresult=function(ev){
   var q='';
   for(var i=ev.resultIndex;i<ev.results.length;i++)q+=ev.results[i][0].transcript;
   q=q.trim();
   if(!q)return;
   set('ليان تحلل كلامك…',q);
   if(typeof window.answerLayan==='function'){
    Promise.resolve(window.answerLayan(q)).catch(function(){});
   }else{
    set('تم التقاط كلامك',q+'\\n\\nلم تتوفر خدمة الرد الصوتي المركزية.');
   }
  };
  rec.onerror=function(ev){
   set('تعذر التقاط الصوت','خطأ الميكروفون: '+(ev&&ev.error?ev.error:'غير معروف')+'\\n'+(reason||''));
   S.running=false;S.fallbackRec=null;
  };
  rec.onend=function(){S.fallbackRec=null;S.running=false;};
  rec.start();
  return true;
 }catch(e){
  set('تعذر تشغيل الصوت',String(e&&e.message||e));
  S.running=false;
  return false;
 }
}
function cleanup(){if(S.fallbackRec){try{S.fallbackRec.stop()}catch(_){}}S.fallbackRec=null;if(S.dc){try{S.dc.close()}catch(_){}}S.dc=null;if(S.pc){try{S.pc.close()}catch(_){}}S.pc=null;if(S.stream){S.stream.getTracks().forEach(function(t){try{t.stop()}catch(_){}})}S.stream=null;if(S.audio){try{S.audio.remove()}catch(_){}}S.audio=null}
function stop(){S.running=false;S.busy=false;S.answering=false;cleanup();if(S.root){S.root.classList.remove('open');S.root.style.display='none'}}
window.startLayanVoice=start;window.openLayanVoice=start;window.stopLayanVoice=stop;window.closeLayanVoice=stop;window.toggleLayanVoice=function(){S.running?stop():start()};interceptVoiceClicks();bindVoiceButtons();if(window.MutationObserver)new MutationObserver(bindVoiceButtons).observe(document.documentElement,{childList:true,subtree:true});setInterval(bindVoiceButtons,1500);})();
