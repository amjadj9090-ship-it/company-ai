/* Company AI — Layan Realtime v12 — native WebRTC, server-proxied handshake */
(function(){
'use strict';
var S={pc:null,stream:null,audio:null,dc:null,root:null,running:false,busy:false};
var API='https://company-ai-0mya.onrender.com';
function overlay(){
 if(S.root)return S.root;
 var r=document.createElement('div');r.id='layanRealtimeHotfix';
 r.innerHTML='<style>#layanRealtimeHotfix{position:fixed;inset:0;z-index:2147483647;display:none;background:#07111d url("assets/layan-office.webp") center/cover no-repeat;font-family:Arial,Tahoma,sans-serif}#layanRealtimeHotfix.open{display:block}#layanRealtimeHotfix:before{content:"";position:absolute;inset:0;background:rgba(2,8,16,.25)}#layanRealtimeHotfix .box{position:absolute;right:24px;top:24px;bottom:24px;width:min(410px,calc(100vw - 48px));background:rgba(250,252,255,.98);border-radius:24px;padding:24px;box-sizing:border-box;display:flex;flex-direction:column;box-shadow:0 20px 70px rgba(0,0,0,.45)}#layanRealtimeHotfix h2{margin:0;color:#10213a;padding-right:42px}#layanRealtimeHotfix .status{margin-top:7px;color:#65768d}#layanRealtimeHotfix .msg{margin-top:22px;background:#fff;border:1px solid #dbe5f2;border-radius:16px;padding:16px;min-height:90px;line-height:1.7;color:#263b55;white-space:pre-wrap}#layanRealtimeHotfix .end{margin-top:auto;border:0;border-radius:14px;padding:15px;background:#b52243;color:#fff;font-weight:800;font-size:16px;cursor:pointer}#layanRealtimeHotfix .close{position:absolute;right:16px;top:16px;border:0;border-radius:50%;width:40px;height:40px;background:#edf2f8;font-size:22px;cursor:pointer}#layanRealtimeHotfix .live{margin-top:20px;text-align:center;font-weight:800;color:#233b5c}@media(max-width:700px){#layanRealtimeHotfix .box{left:12px;right:12px;top:auto;bottom:12px;width:auto;height:55dvh;min-height:330px}}</style><div class="box"><button class="close" id="lhClose" type="button" aria-label="إغلاق">×</button><h2>ليان — جلسة صوتية مباشرة</h2><div class="status" id="lhStatus">جاري التحضير…</div><div class="live" id="lhLive">الميكروفون رح يشتغل بشكل مستمر</div><div class="msg" id="lhMsg">جاري إنشاء الاتصال…</div><button class="end" id="lhEnd" type="button">إنهاء المحادثة</button></div>';
 document.body.appendChild(r);
 r.querySelector('#lhClose').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
 r.querySelector('#lhEnd').addEventListener('click',function(e){e.preventDefault();e.stopPropagation();stop()});
 S.root=r;return r;
}
function set(status,msg){var r=overlay();r.classList.add('open');r.style.display='block';r.querySelector('#lhStatus').textContent=status;r.querySelector('#lhMsg').textContent=msg||''}
function looksLikeVoice(el){if(!el)return false;var x=el.closest&&el.closest('button,[role="button"],a,[onclick],.voiceChoice,.layanChoice.voiceChoice,.layanQuickVoice');if(!x)return false;var t=((x.innerText||x.textContent||'')+' '+(x.getAttribute('aria-label')||'')+' '+(x.getAttribute('title')||'')+' '+(x.className||'')).toLowerCase();return /voice|audio|speak|talk|live|صوت|صوتي|صوتية|محادثة صوت|دردشة صوت|تكلم|تحدث/.test(t)}
function interceptVoiceClicks(){['pointerdown','pointerup','mousedown','mouseup','touchstart','touchend','click'].forEach(function(type){window.addEventListener(type,function(e){if(S.root&&S.root.contains(e.target))return;if(looksLikeVoice(e.target)){e.preventDefault();e.stopPropagation();if(e.stopImmediatePropagation)e.stopImmediatePropagation();if(type==='pointerdown'||type==='mousedown'||type==='touchstart')start()}},true)})}
function onEvent(ev){try{var x=typeof ev==='string'?JSON.parse(ev):ev;if(!x||!x.type)return;console.log('Layan Realtime event',x.type);if(x.type==='session.created'){set('تم الاتصال بليان','احكي بشكل طبيعي… الميكروفون شغّال.')}else if(x.type==='input_audio_buffer.speech_started'){set('ليان عم تسمعك','كمل كلامك…')}else if(x.type==='response.created'){set('ليان عم ترد','فيك تقاطعها بأي لحظة.')}else if(x.type==='response.done'){set('لايف — احكي مع ليان','المحادثة مستمرة والميكروفون شغّال.')}else if(x.type==='input_audio_buffer.speech_stopped'){set('ليان عم تفهم كلامك','لحظة…')}else if(x.type==='error'){console.error('Layan realtime server error',x);set('مشكلة بالاتصال الصوتي',x.error&&x.error.message?x.error.message:'تعذر إكمال الاتصال.')}}catch(e){console.warn('Realtime event parse error',e)}}
async function start(){if(S.running||S.busy)return;S.busy=true;S.running=true;set('جاري الاتصال…','عم نجهّز اتصال WebRTC آمن…');try{
 if(!window.RTCPeerConnection)throw Error('المتصفح لا يدعم WebRTC');
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)throw Error('المتصفح لا يسمح بالوصول إلى الميكروفون');
 var stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});S.stream=stream;
 var pc=new RTCPeerConnection();S.pc=pc;
 stream.getTracks().forEach(function(track){pc.addTrack(track,stream)});
 var audio=document.createElement('audio');audio.autoplay=true;audio.playsInline=true;audio.style.display='none';document.body.appendChild(audio);S.audio=audio;
 pc.ontrack=function(e){if(e.streams&&e.streams[0]){audio.srcObject=e.streams[0];audio.play().catch(function(){})}};
 var dc=pc.createDataChannel('oai-events');S.dc=dc;dc.onopen=function(){set('تم الاتصال بليان','احكي بشكل طبيعي… الميكروفون شغّال.')};dc.onmessage=function(e){onEvent(e.data)};dc.onerror=function(e){console.error('Layan data channel error',e);set('مشكلة بقناة الصوت','تعذر نقل أحداث المحادثة.')};
 pc.onconnectionstatechange=function(){console.log('Layan WebRTC state',pc.connectionState);if(pc.connectionState==='connected')set('لايف — احكي مع ليان','المحادثة الصوتية مفتوحة. احكي بشكل طبيعي.');if(pc.connectionState==='failed'||pc.connectionState==='disconnected')set('انقطع الاتصال الصوتي','الاتصال انقطع. احكي من جديد لإعادة المحاولة.')};
 var offer=await pc.createOffer();await pc.setLocalDescription(offer);await new Promise(function(resolve){if(pc.iceGatheringState==='complete')return resolve();function done(){if(pc.iceGatheringState==='complete'){pc.removeEventListener('icegatheringstatechange',done);resolve()}}pc.addEventListener('icegatheringstatechange',done);setTimeout(resolve,7000)});
 if(!pc.localDescription||!pc.localDescription.sdp)throw Error('تعذر إنشاء SDP للاتصال الصوتي');
 var answerRes=await fetch(API+'/api/voice-avatar/realtime-call',{method:'POST',headers:{'Content-Type':'application/sdp','Accept':'application/sdp'},body:pc.localDescription.sdp});
 var answer=await answerRes.text();if(!answerRes.ok)throw Error('خادم الصوت أعاد HTTP '+answerRes.status+': '+answer.slice(0,220));
 if(!answer.trim().startsWith('v='))throw Error('خادم الصوت لم يرجّع SDP صالحاً');
 await pc.setRemoteDescription({type:'answer',sdp:answer});
 set('لايف — احكي مع ليان','المحادثة الصوتية مفتوحة. الميكروفون شغّال بشكل مستمر.');
 }catch(e){console.error('Layan realtime v12 error',e);set('تعذر تشغيل المحادثة الصوتية',e&&e.message?e.message:'خطأ غير معروف.');S.running=false;cleanup()}finally{S.busy=false}}
function cleanup(){if(S.dc){try{S.dc.close()}catch(_){}}S.dc=null;if(S.pc){try{S.pc.close()}catch(_){}}S.pc=null;if(S.stream){S.stream.getTracks().forEach(function(t){try{t.stop()}catch(_){}})}S.stream=null;if(S.audio){try{S.audio.remove()}catch(_){}}S.audio=null}
function stop(){S.running=false;S.busy=false;cleanup();if(S.root)S.root.classList.remove('open');if(S.root)S.root.style.display='none'}
window.startLayanVoice=start;window.openLayanVoice=start;window.stopLayanVoice=stop;window.closeLayanVoice=stop;window.toggleLayanVoice=function(){S.running?stop():start()};interceptVoiceClicks();
})();
