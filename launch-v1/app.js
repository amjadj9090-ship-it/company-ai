(()=>{"use strict";
const S={catalog:null,lang:localStorage.getItem("launch-language")||"ar",history:[]};
const $=s=>document.querySelector(s),grid=$("#serviceGrid"),nav=$("#mainNav"),drawer=$("#drawer"),drawerContent=$("#drawerContent"),modal=$("#chatModal"),messages=$("#chatMessages"),input=$("#chatInput"),voice=$("#voiceButton"),language=$("#language");
const esc=v=>String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function boot(){const r=await fetch("/launch-v1/data/services.json",{cache:"no-store"});if(!r.ok)throw Error("catalog");S.catalog=await r.json();render();bindLayanButtons()}
function render(){nav.innerHTML=S.catalog.sections.map(x=>'<button type="button" data-section="'+x.id+'">'+x.icon+" "+esc(x.title)+"</button>").join("");renderCards(S.catalog.sections)}
function renderCards(list){grid.innerHTML=list.map(x=>'<article class="service-card"><div class="service-icon">'+x.icon+'</div><h3>'+esc(x.title)+'</h3><p>'+esc(x.desc)+'</p><button type="button" data-open="'+x.id+'">عرض التفاصيل ←</button></article>').join("")||"<p>ما لقينا خدمة مطابقة.</p>"}
function openService(id){const x=S.catalog.sections.find(v=>v.id===id);if(!x)return;drawerContent.innerHTML='<span class="eyebrow">SERVICE</span><h2>'+x.icon+" "+esc(x.title)+'</h2><p>'+esc(x.desc)+'</p><div class="detail-list">'+x.items.map(i=>'<button class="detail-item" type="button" data-detail="'+x.id+":"+i.id+'"><strong>'+esc(i.title)+'</strong><span>'+esc(i.desc)+'</span></button>').join("")+'</div>';drawer.setAttribute("aria-hidden","false")}
function openDetail(key){const [sid,iid]=key.split(":"),x=S.catalog.sections.find(v=>v.id===sid),i=x?.items.find(v=>v.id===iid);if(!i)return;drawerContent.innerHTML='<span class="eyebrow">SERVICE DETAIL</span><h2>'+esc(i.title)+'</h2><p>'+esc(i.desc)+'</p><div class="detail-box"><strong>الخدمة مرتبطة الآن بمسار ليان وCompany AI</strong><span>عند البدء، نرسل طلب الخدمة إلى مسار التخطيط المركزي ثم تتابع ليان معك التفاصيل. لا يوجد اعتماد على صفحة قديمة أو مسار قديم.</span></div><div class="detail-actions"><button class="primary" type="button" data-start="'+esc(i.title)+'">ابدأ هذه الخدمة مع ليان</button><button class="secondary" type="button" data-plan="'+esc(i.title)+'">حلّل طلبي أولاً</button></div>'}
function closeDrawer(){drawer.setAttribute("aria-hidden","true")}
function openChat(prefill=""){modal.setAttribute("aria-hidden","false");if(prefill)input.value=prefill;setTimeout(()=>input.focus(),60)}
function closeChat(){stopVoice();modal.setAttribute("aria-hidden","true")}
function add(text,role){const e=document.createElement("div");e.className="bubble "+role;e.textContent=text;messages.appendChild(e);messages.scrollTop=messages.scrollHeight}
let wakeLock=null;
async function keepScreenAwake(){
  if(!("wakeLock" in navigator))return;
  try{if(wakeLock&&wakeLock.released===false)return;wakeLock=await navigator.wakeLock.request("screen");wakeLock.addEventListener("release",()=>{wakeLock=null})}catch(_){}
}
async function releaseScreenWake(){try{if(wakeLock){await wakeLock.release()}}catch(_){}wakeLock=null}
function speak(text){if(!speechSynthesis)return;const u=new SpeechSynthesisUtterance(text);u.lang=S.lang==="ar"?"ar-SA":S.lang;u.rate=.96;speechSynthesis.cancel();u.onend=()=>{if(voiceSession){setTimeout(()=>{keepScreenAwake();startListening()},250)}};speechSynthesis.speak(u)}
document.addEventListener("visibilitychange",()=>{if(voiceSession&&document.visibilityState==="visible")keepScreenAwake()});
async function chat(text,fromVoice=false){
  add(text,"user");input.value="";clearVoiceTimer();
  if(fromVoice&&rec){try{rec.stop()}catch(_){ }rec=null}
  const t=document.createElement("div");t.className="bubble assistant";t.textContent=S.lang==="ar"?"عم فكّر…":"Thinking…";messages.appendChild(t);
  try{
    const r=await fetch("/launch-api/chat",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({message:text,language:S.lang,history:S.history})});
    const d=await r.json();
    if(!r.ok){
      t.textContent=d.reply||"محرك ليان غير متاح حالياً.";
      stopVoice();
      return;
    }
    const reply=d.reply||"ليان ما قدرت تكمل الطلب حالياً.";
    t.textContent=reply;
    S.history.push({role:"user",content:text},{role:"assistant",content:reply});S.history=S.history.slice(-12);
    speak(reply);
  }catch(_){
    t.textContent="تعذر الاتصال بليان حالياً. لم يتم تنفيذ أي إجراء خارجي.";
    stopVoice();
  }
}
async function analyzeService(title){try{const r=await fetch("/launch-api/company/plan",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({message:"أريد البدء بخدمة: "+title,language:S.lang,history:S.history})});const d=await r.json();add("الخدمة: "+title,"user");add("تم ربط الطلب بمسار Company AI المركزي. "+(d.summary||"ليان ستتابع معك التفاصيل."),"assistant")}catch(_){add("تعذر تحليل الخدمة حالياً، ولم يتم تنفيذ أي إجراء خارجي.","assistant")}}
let rec=null,voiceSession=false,pendingVoiceText="",silenceTimer=null,audioRecorder=null,audioChunks=[],audioStream=null,audioContext=null,audioSource=null,audioAnalyser=null,audioFrame=null,audioStarted=false,audioSilenceSince=0;
const VOICE_SILENCE_MS=2600;
function clearVoiceTimer(){if(silenceTimer){clearTimeout(silenceTimer);silenceTimer=null}}
function submitVoice(){
  const text=pendingVoiceText.trim();
  pendingVoiceText="";clearVoiceTimer();
  if(!text||!voiceSession)return;
  if(rec){try{rec.stop()}catch(_){ }rec=null}
  chat(text,true);
}
function startVoice(){
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){startAudioFallback();return}
  if(voiceSession){stopVoice();return}
  voiceSession=true;pendingVoiceText="";clearVoiceTimer();
  voice.textContent="⏹️ إنهاء الاتصال مع ليان";add("🎙️ ليان تستمع الآن…","assistant");keepScreenAwake();startListening();
}
function startListening(){
  if(!voiceSession||rec)return;
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){startAudioFallback();return}
  rec=new SR();rec.lang=S.lang==="ar"?"ar-SA":S.lang;
  rec.interimResults=true;rec.continuous=false;rec.maxAlternatives=1;
  rec.onstart=()=>{add("👂 الاستماع مفتوح… احكي براحتك.","assistant")};
  rec.onresult=e=>{
    let finalText="";
    let interimText="";
    for(let i=e.resultIndex;i<e.results.length;i++){
      const r=e.results[i];const t=r[0]?.transcript?.trim();if(!t)continue;
      if(r.isFinal) finalText+=(finalText?" ":"")+t;
      else interimText+=(interimText?" ":"")+t;
    }
    if(finalText) pendingVoiceText+=(pendingVoiceText?" ":"")+finalText;
    clearVoiceTimer();
    if(pendingVoiceText) silenceTimer=setTimeout(submitVoice,VOICE_SILENCE_MS);
    else if(interimText) silenceTimer=setTimeout(()=>{if(interimText&&!pendingVoiceText){pendingVoiceText=interimText;submitVoice()}},VOICE_SILENCE_MS);
  };
  rec.onerror=e=>{
    rec=null;clearVoiceTimer();
    if(e.error==="not-allowed"||e.error==="service-not-allowed"){
      stopVoice();add("لم يتم السماح للميكروفون. اسمح به من الهاتف ثم اضغط الاتصال مرة ثانية.","assistant");
    } else if(e.error!=="aborted"){
      add("🎙️ سأستخدم الاستماع الصوتي المباشر بدلاً من التعرف النصي…","assistant");
      startAudioFallback();
    }
  };
  rec.onend=()=>{
    rec=null;
    if(voiceSession&&pendingVoiceText)silenceTimer=setTimeout(submitVoice,VOICE_SILENCE_MS);
  };
  try{rec.start()}catch(_){rec=null;startAudioFallback()}
}
function cleanupAudio(){
  if(audioFrame)cancelAnimationFrame(audioFrame);audioFrame=null;
  try{audioRecorder?.stop()}catch(_){}
  audioRecorder=null;
  if(audioStream)audioStream.getTracks().forEach(t=>t.stop());audioStream=null;
  try{audioSource?.disconnect()}catch(_){}
  try{audioAnalyser?.disconnect()}catch(_){}
  try{audioContext?.close()}catch(_){}
  audioSource=null;audioAnalyser=null;audioContext=null;audioChunks=[];audioStarted=false;audioSilenceSince=0;
}
function startAudioFallback(){
  if(!voiceSession||audioRecorder)return;
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){
    stopVoice();add("هذا المتصفح لا يوفّر تسجيل الصوت المطلوب. جرّب Chrome على الهاتف أو استخدم الدردشة النصية.","assistant");return;
  }
  navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}}).then(stream=>{
    if(!voiceSession){stream.getTracks().forEach(t=>t.stop());return}
    audioStream=stream;audioChunks=[];audioStarted=false;audioSilenceSince=0;
    const mime=MediaRecorder.isTypeSupported("audio/webm;codecs=opus")?"audio/webm;codecs=opus":(MediaRecorder.isTypeSupported("audio/webm")?"audio/webm":"audio/mp4");
    audioRecorder=new MediaRecorder(stream,{mimeType:mime});
    audioRecorder.ondataavailable=e=>{if(e.data.size)audioChunks.push(e.data)};
    audioRecorder.onstop=()=>{const blob=new Blob(audioChunks,{type:mime});cleanupAudio();if(blob.size>5000&&voiceSession)chatAudio(blob);else if(voiceSession){add("ما التقطت كلام واضح. احكي مرة ثانية.","assistant");setTimeout(startAudioFallback,250)}};
    audioRecorder.start(250);
    add("👂 الاستماع المباشر مفتوح… احكي براحتك.","assistant");
    audioContext=new (window.AudioContext||window.webkitAudioContext)();
    audioSource=audioContext.createMediaStreamSource(stream);audioAnalyser=audioContext.createAnalyser();audioAnalyser.fftSize=2048;audioSource.connect(audioAnalyser);
    const data=new Uint8Array(audioAnalyser.fftSize);
    const tick=()=>{
      if(!audioRecorder)return;
      audioAnalyser.getByteTimeDomainData(data);
      let sum=0;for(let i=0;i<data.length;i++){const v=(data[i]-128)/128;sum+=v*v}
      const rms=Math.sqrt(sum/data.length);
      const now=performance.now();
      if(rms>0.025){audioStarted=true;audioSilenceSince=0}
      else if(audioStarted){if(!audioSilenceSince)audioSilenceSince=now;if(now-audioSilenceSince>=VOICE_SILENCE_MS){try{audioRecorder.stop()}catch(_){}}}
      if(audioRecorder&&now>audioRecorder._startedAt+30000){try{audioRecorder.stop()}catch(_){}} 
      audioFrame=requestAnimationFrame(tick);
    };
    audioRecorder._startedAt=performance.now();tick();
  }).catch(()=>{stopVoice();add("لم أستطع الوصول إلى الميكروفون. اسمح بالميكروفون من الهاتف ثم جرّب مرة ثانية.","assistant")});
}
async function chatAudio(blob){
  add("🎙️ (رسالة صوتية)","user");
  const t=document.createElement("div");t.className="bubble assistant";t.textContent=S.lang==="ar"?"عم بفهم كلامك…":"Understanding…";messages.appendChild(t);messages.scrollTop=messages.scrollHeight;
  try{
    const buf=await blob.arrayBuffer();let binary="";const bytes=new Uint8Array(buf);const chunk=0x8000;
    for(let i=0;i<bytes.length;i+=chunk)binary+=String.fromCharCode(...bytes.subarray(i,i+chunk));
    const audioBase64=btoa(binary);
    const r=await fetch("/launch-api/chat-audio",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({audio_base64:audioBase64,mime_type:blob.type||"audio/webm",language:S.lang,history:S.history})});
    const d=await r.json();
    if(!r.ok){t.textContent=d.reply||"محرك ليان غير متاح حالياً.";stopVoice();return}
    const reply=d.reply||"ليان ما قدرت تكمل الطلب حالياً.";t.textContent=reply;
    S.history.push({role:"user",content:"[voice message]"},{role:"assistant",content:reply});S.history=S.history.slice(-12);
    speak(reply);
  }catch(_){t.textContent="تعذر معالجة الصوت حالياً. لم يتم تنفيذ أي إجراء خارجي.";stopVoice()}
}
function stopVoice(){
  voiceSession=false;clearVoiceTimer();pendingVoiceText="";
  if(rec){try{rec.abort()}catch(_){ }rec=null}
  cleanupAudio();
  if(speechSynthesis)speechSynthesis.cancel();
  releaseScreenWake();
  if(voice)voice.textContent="🎙️ ابدأ الاتصال الصوتي مع ليان";
}
function setLang(v){S.lang=v;document.documentElement.lang=v;document.documentElement.dir=v==="ar"?"rtl":"ltr";language.value=v;localStorage.setItem("launch-language",v)}
function bindLayanButtons(){const hv=$("#heroVoice");if(hv)hv.onclick=()=>{openChat();setTimeout(startVoice,120)};const tb=$("#textOnlyButton");if(tb)tb.onclick=()=>openChat()}
document.addEventListener("click",e=>{const sec=e.target.closest("[data-section]"),op=e.target.closest("[data-open]"),de=e.target.closest("[data-detail]"),cl=e.target.closest("[data-close]"),cc=e.target.closest("[data-close-chat]"),st=e.target.closest("[data-start]"),pl=e.target.closest("[data-plan]");if(sec)openService(sec.dataset.section);if(op)openService(op.dataset.open);if(de)openDetail(de.dataset.detail);if(cl)closeDrawer();if(cc)closeChat();if(st){const title=st.dataset.start;closeDrawer();openChat("أريد البدء بخدمة: "+title)}if(pl){const title=pl.dataset.plan;closeDrawer();openChat("أريد تحليل طلبي لخدمة: "+title);setTimeout(()=>analyzeService(title),100)}});
$("#browseServices").onclick=()=>$("#services").scrollIntoView({behavior:"smooth"});$("#heroChat").onclick=openChat;$("#openChat").onclick=openChat;voice.onclick=startVoice;
$("#serviceSearch").oninput=e=>{const q=e.target.value.trim().toLowerCase();renderCards(!q?S.catalog.sections:S.catalog.sections.filter(x=>(x.title+" "+x.desc+" "+x.items.map(i=>i.title+" "+i.desc).join(" ")).toLowerCase().includes(q)))};
$("#chatForm").onsubmit=e=>{e.preventDefault();const v=input.value.trim();if(v)chat(v)};language.onchange=e=>setLang(e.target.value);setLang(S.lang);
boot().catch(()=>grid.innerHTML="<p>تعذر تحميل كتالوج الخدمات الجديد.</p>");
})();