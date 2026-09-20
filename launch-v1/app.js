(() => {
"use strict";
const catalog=[
 {id:"web",icon:"🌐",title:"تصميم المواقع",desc:"مواقع احترافية للشركات والأنشطة والخدمات والمتاجر.",items:["موقع شركة","موقع نشاط تجاري","متجر إلكتروني","موقع خدمات وحجوزات","Landing Page","تطوير موقع موجود"]},
 {id:"apps",icon:"📱",title:"تصميم التطبيقات",desc:"تطبيقات Android وiPhone وتطبيقات الويب والأنظمة الخاصة.",items:["Android / APK","iPhone / iOS","Web Apps","تطبيقات الشركات"]},
 {id:"ai",icon:"🤖",title:"الذكاء الاصطناعي والأتمتة",desc:"مساعدون ووكلاء وأنظمة ذكية تقلل العمل اليدوي.",items:["مساعد AI","وكلاء AI","أتمتة العمليات","دمج AI مع الأنظمة"]},
 {id:"growth",icon:"📣",title:"التسويق والنمو",desc:"حلول تساعد الشركة على الوصول للعملاء وتحويل الاهتمام إلى طلبات.",items:["استراتيجية التسويق","جذب العملاء","إدارة الحملات","تحسين التحويل"]},
 {id:"commerce",icon:"🛒",title:"التجارة الإلكترونية",desc:"بناء وتشغيل تجارب بيع رقمية منظمة وقابلة للتوسع.",items:["متجر جديد","تحسين متجر","الدفع والطلبات","إدارة المنتجات"]},
 {id:"enterprise",icon:"🏢",title:"حلول الشركات والأنظمة",desc:"أنظمة داخلية ولوحات تحكم وربط أدوات الشركة معاً.",items:["CRM","لوحات تحكم","أنظمة داخلية","تكاملات API"]}
];
const $=s=>document.querySelector(s), grid=$("#serviceGrid"), nav=$("#mainNav"), drawer=$("#drawer"), drawerContent=$("#drawerContent"), modal=$("#chatModal"), messages=$("#chatMessages"), input=$("#chatInput");
function renderNav(){nav.innerHTML=catalog.map(x=>`<button data-section="${x.id}">${x.icon} ${x.title}</button>`).join("");}
function renderCards(list=catalog){grid.innerHTML=list.map(x=>`<article class="service-card"><div class="service-icon">${x.icon}</div><h3>${x.title}</h3><p>${x.desc}</p><button data-open="${x.id}">عرض التفاصيل ←</button></article>`).join("")||"<p>ما لقينا خدمة مطابقة للبحث.</p>";}
function openService(id){const x=catalog.find(v=>v.id===id);if(!x)return;drawerContent.innerHTML=`<span class="eyebrow">SERVICE</span><h2>${x.icon} ${x.title}</h2><p>${x.desc}</p><div class="detail-list">${x.items.map((i,n)=>`<button class="detail-item" data-detail="${id}:${n}"><strong>${i}</strong><span>عرض التفاصيل والخيارات</span></button>`).join("")}</div>`;drawer.setAttribute("aria-hidden","false");}
function closeDrawer(){drawer.setAttribute("aria-hidden","true")}
function openChat(){modal.setAttribute("aria-hidden","false");setTimeout(()=>input.focus(),80)}
function closeChat(){modal.setAttribute("aria-hidden","true")}
function addMessage(text,who){const el=document.createElement("div");el.className="bubble "+who;el.textContent=text;messages.appendChild(el);messages.scrollTop=messages.scrollHeight}
async function sendChat(text){addMessage(text,"user");input.value="";const thinking=document.createElement("div");thinking.className="bubble assistant";thinking.textContent="عم فكّر بالطلب…";messages.appendChild(thinking);try{const r=await fetch("/launch-api/chat",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({message:text,language:document.documentElement.lang||"ar"})});const d=await r.json();thinking.textContent=d.reply||"حالياً ما قدرت أوصل لمحرك ليان."; }catch(e){thinking.textContent="ليان غير متاحة حالياً. الواجهة شغالة، ونكمل ربط المحرك من المسار الجديد.";}}
$("#browseServices").onclick=()=>$("#services").scrollIntoView({behavior:"smooth"});
$("#heroChat").onclick=openChat;$("#openChat").onclick=openChat;
document.addEventListener("click",e=>{const section=e.target.closest("[data-section]"),open=e.target.closest("[data-open]"),close=e.target.closest("[data-close]"),closeChatBtn=e.target.closest("[data-close-chat]");if(section)openService(section.dataset.section);if(open)openService(open.dataset.open);if(close)closeDrawer();if(closeChatBtn)closeChat();});
$("#serviceSearch").addEventListener("input",e=>{const q=e.target.value.trim().toLowerCase();renderCards(!q?catalog:catalog.filter(x=>(x.title+" "+x.desc+" "+x.items.join(" ")).toLowerCase().includes(q)));});
$("#chatForm").onsubmit=e=>{e.preventDefault();const v=input.value.trim();if(v)sendChat(v)};
$("#voiceButton").onclick=()=>alert("المسار الصوتي الجديد سيُربط بواجهة الصوت المستقلة الخاصة بهذا المشروع، بدون تحميل JavaScript من النسخة القديمة.");
$("#language").onchange=e=>{document.documentElement.lang=e.target.value;document.documentElement.dir=e.target.value==="ar"?"rtl":"ltr";localStorage.setItem("launch-language",e.target.value)};
document.documentElement.lang=localStorage.getItem("launch-language")||"ar";document.documentElement.dir=document.documentElement.lang==="ar"?"rtl":"ltr";$("#language").value=document.documentElement.lang;
renderNav();renderCards();
})();