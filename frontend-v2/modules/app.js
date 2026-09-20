import data from "../data/services.json" with {type:"json"};
import{detectLanguage,setDocumentLanguage,t,supportedLanguages}from"./language.js";
import{chat,resetChat,openVoice}from"./layan.js";
let lang=localStorage.getItem("company-ai-language")||detectLanguage();if(!supportedLanguages().includes(lang))lang="en";
const $=(s,r=document)=>r.querySelector(s),esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const text=o=>typeof o==="string"?o:(o?.[lang]||o?.en||"");
const icons={web:"M4 6h16M4 12h16M4 18h16",apps:"M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2",ai:"M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4",growth:"M4 18l5-6 4 3 7-9",commerce:"M4 5h16l-2 11H6L4 5M9 20h.01M17 20h.01",enterprise:"M5 20V7l7-4 7 4v13M9 20v-5h6v5"};
const icon=id=>'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="'+(icons[id]||icons.enterprise)+'"/></svg>';
function render(){
 setDocumentLanguage(lang);
 $("#app").innerHTML=`<header class="header"><div class="shell header-inner"><button class="brand" data-home><span class="brand-mark">CA</span><span class="brand-name">Company <span>AI</span></span></button><nav class="nav">${data.sections.map(s=>`<button data-section="${s.id}">${esc(text(s.title))}</button>`).join("")}<button data-chat>${esc(t(lang,"layan"))}</button></nav><select class="language" id="language">${supportedLanguages().map(x=>`<option value="${x}">${x==="ar"?"العربية":x==="en"?"English":x==="es"?"Español":x==="fr"?"Français":x==="de"?"Deutsch":x==="pt"?"Português":x.toUpperCase()}</option>`).join("")}</select></div></header><main><section class="hero"><div class="shell hero-grid"><div class="hero-copy"><div class="eyebrow">COMPANY AI</div><h1>${esc(t(lang,"hero"))}</h1><p class="hero-sub">${esc(t(lang,"heroSub"))}</p><div class="actions"><button class="btn primary" data-services>${esc(t(lang,"explore"))}</button><button class="btn secondary" data-chat>${esc(t(lang,"text"))}</button><button class="btn secondary" data-voice>${esc(t(lang,"voice"))}</button></div><form class="search" id="search"><input id="search-input" type="search" placeholder="${esc(t(lang,"search"))}" autocomplete="off"><button>${esc(t(lang,"explore"))}</button></form></div><div class="hero-visual"><img src="/assets/layan-office.webp?v=20260920-v3" alt="Layan in Company AI office" loading="eager" decoding="async" onerror="this.hidden=true;this.parentElement.classList.add('image-fallback')"><div class="hero-overlay"></div><div class="hero-caption"><span class="dot"></span> Layan • LIVE<small>${esc(t(lang,"online"))}</small></div></div></div></section><section class="service-section" id="services"><div class="shell"><div class="section-head"><div><div class="eyebrow">01</div><h2>${esc(t(lang,"services"))}</h2><p>${esc(t(lang,"heroSub"))}</p></div></div><div class="service-grid">${data.sections.map(s=>`<article class="service-card"><div class="service-mark">${icon(s.id)}</div><h3>${esc(text(s.title))}</h3><p>${esc(text(s.description))}</p><div class="card-foot"><span></span><button class="link-btn" data-section="${s.id}">${esc(t(lang,"details"))} →</button></div></article>`).join("")}</div></div></section><section class="shell chat-note"><div><strong>${esc(t(lang,"notSure"))}</strong><p>${esc(t(lang,"heroSub"))}</p></div><button class="btn primary" data-chat>${esc(t(lang,"layan"))}</button></section></main>`;
 $("#language").value=lang;bind();
}
function bind(){
 document.querySelectorAll("[data-home]").forEach(b=>b.onclick=()=>scrollTo({top:0,behavior:"smooth"}));
 document.querySelectorAll("[data-services]").forEach(b=>b.onclick=()=>$("#services").scrollIntoView({behavior:"smooth"}));
 document.querySelectorAll("[data-section]").forEach(b=>b.onclick=()=>openSection(b.dataset.section));
 document.querySelectorAll("[data-chat]").forEach(b=>b.onclick=()=>openChat());
 document.querySelectorAll("[data-voice]").forEach(b=>b.onclick=()=>{try{openVoice()}catch(e){toast(e.message)}});
 $("#language").onchange=e=>{lang=e.target.value;localStorage.setItem("company-ai-language",lang);render()};
 $("#search").onsubmit=e=>{e.preventDefault();search($("#search-input").value)};
}
function search(q){const n=String(q||"").trim().toLowerCase();if(!n)return $("#services").scrollIntoView({behavior:"smooth"});for(const s of data.sections){if((text(s.title)+" "+text(s.description)).toLowerCase().includes(n))return openSection(s.id);for(const i of s.items)if((text(i.title)+" "+text(i.description)).toLowerCase().includes(n))return openSection(s.id,i.id)}openChat(q)}
function openSection(id,focus){
 const s=data.sections.find(x=>x.id===id),d=$("#drawer");if(!s)return;
 d.innerHTML=`<div class="drawer-panel"><div class="drawer-head"><div><div class="eyebrow">${esc(text(s.title))}</div><h2>${esc(text(s.title))}</h2><p>${esc(text(s.description))}</p></div><button class="close" data-close>×</button></div><div class="drawer-body"><div class="option-grid">${s.items.map(i=>`<button class="option" data-item="${i.id}"><h3>${esc(text(i.title))}</h3><p>${esc(text(i.description))}</p><b>${esc(t(lang,"start"))} →</b></button>`).join("")}</div></div></div>`;
 d.classList.add("open");d.querySelector("[data-close]").onclick=closeDrawer;d.onclick=e=>{if(e.target===d)closeDrawer()};d.querySelectorAll("[data-item]").forEach(b=>b.onclick=()=>openItem(s,b.dataset.item));if(focus)openItem(s,focus);
}
function openItem(s,id){const i=s.items.find(x=>x.id===id);if(!i)return;const body=$("#drawer .drawer-body");body.innerHTML=`<div class="crumb"><button data-back>← ${esc(t(lang,"back"))}</button><span>${esc(text(s.title))}</span><strong>${esc(text(i.title))}</strong></div><article class="detail"><div class="service-mark">${icon(s.id)}</div><h2>${esc(text(i.title))}</h2><p>${esc(text(i.description))}</p><div class="actions"><button class="btn primary" data-start>${esc(t(lang,"start"))}</button><button class="btn secondary" data-ask>${esc(t(lang,"text"))}</button></div></article>`;body.querySelector("[data-back]").onclick=()=>openSection(s.id);body.querySelector("[data-start]").onclick=()=>{closeDrawer();openChat(text(i.title))};body.querySelector("[data-ask]").onclick=()=>{closeDrawer();openChat(text(i.title))}}
function closeDrawer(){const d=$("#drawer");d.classList.remove("open");d.setAttribute("aria-hidden","true")}
function ensureVoiceStage(){
 const id="layanVoiceStage";
 let s=document.getElementById(id);
 if(s)return s;
 s=document.createElement("section");
 s.id=id;s.className="layanVoiceStage";s.setAttribute("aria-hidden","true");
 s.innerHTML=`<div class="layanVoicePanel">
   <div class="layanVoiceTop"><div><strong>Layan</strong><small>LIVE • Company AI</small></div><button class="close layanClose" aria-label="Close">×</button></div>
   <div class="layanVoiceVisual"><img class="layanOfficeDedicated" src="/assets/layan-office.webp?v=20260920-v4" alt="Layan in Company AI office" loading="eager" decoding="async"><div class="layanVoiceGlow"></div><div class="layanVoiceOfficeBadge"><span class="dot"></span> LIVE</div></div>
   <div class="layanVoiceState" id="layanVoiceState">Layan is ready…</div>
   <div class="layanVoiceSub" id="layanVoiceSub">Speak naturally in your language.</div>
   <div class="layanVoiceText" id="layanVoiceText"></div>
   <button id="layanStart" class="btn primary layanStart">Start conversation</button>
 </div>`;
 document.body.appendChild(s);
 return s;
}
function openVoice(){ensureVoiceStage();if(typeof window.startLayanVoice!=="function")throw Error("Voice module is not ready");return window.startLayanVoice();}
function openChat(prefill=""){const c=$("#chat");resetChat();c.innerHTML=`<div class="chat-panel"><div class="chat-head"><div class="layan-id"><span class="dot"></span><div><strong>Layan</strong><small>${esc(t(lang,"online"))}</small></div></div><button class="close" data-close>×</button></div><div class="chat-messages" id="messages"><div class="msg ai">${esc(t(lang,"notSure"))}</div></div><form class="chat-form"><input id="chat-input" placeholder="${esc(t(lang,"type"))}" value="${esc(prefill)}"><button>${esc(t(lang,"send"))}</button></form></div>`;c.classList.add("open");c.querySelector("[data-close]").onclick=closeChat;c.onclick=e=>{if(e.target===c)closeChat()};c.querySelector("form").onsubmit=async e=>{e.preventDefault();const x=$("#chat-input"),m=x.value.trim();if(!m)return;add(m,"user");x.value="";try{const r=await chat(m,lang);add(r.reply,"ai")}catch(err){add(err.message,"ai")}};c.querySelector("#chat-input").focus()}
function add(v,k){const m=$("#messages"),x=document.createElement("div");x.className="msg "+k;x.textContent=v;m.appendChild(x);m.scrollTop=m.scrollHeight}
function closeChat(){const c=$("#chat");c.classList.remove("open");c.setAttribute("aria-hidden","true")}
function toast(v){const x=document.createElement("div");x.className="toast";x.textContent=v;document.body.append(x);x.classList.add("show");setTimeout(()=>x.remove(),2800)}
addEventListener("keydown",e=>{if(e.key==="Escape"){closeDrawer();closeChat()}});render();