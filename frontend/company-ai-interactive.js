/* Company AI — public interactive bridge v1
   Turns the existing visual homepage into a working interactive business surface.
*/
(function(){
  'use strict';
  if(window.__COMPANY_AI_INTERACTIVE__) return;
  window.__COMPANY_AI_INTERACTIVE__=true;

  var SERVICES=[
    ['web','تصميم مواقع','موقع شركة، متجر، صفحة هبوط أو منصة ويب كاملة.'],
    ['app','تطوير التطبيقات','تطبيق Android/iOS أو تطبيق أعمال مخصص.'],
    ['uiux','UI/UX','تصميم تجربة المستخدم والواجهات بشكل احترافي.'],
    ['marketing','التسويق الرقمي','خطة تسويق، محتوى، حملات واكتساب عملاء.'],
    ['seo','SEO','تحسين الظهور في Google وبناء نمو عضوي.'],
    ['ai','حلول الذكاء الاصطناعي','مساعدات AI، أتمتة، CRM وموظفون AI.'],
    ['security','الأمن السيبراني','تقييم أمني وحماية الأنظمة ضمن نطاق مصرح به.'],
    ['growth','النمو وتطوير الأعمال','تحليل السوق، العملاء، التسعير وخطة النمو.']
  ];

  function esc(s){return String(s||'').replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\\':'&quot;','"':'&quot;'}[c]})}
  function textOf(el){return ((el.innerText||el.textContent||'')+' '+(el.getAttribute&&el.getAttribute('aria-label')||'')+' '+(el.getAttribute&&el.getAttribute('title')||'')).trim()}
  function matchService(t){
    t=String(t||'').toLowerCase();
    if(/موقع|website|web design|تصميم مواقع/.test(t)) return SERVICES[0];
    if(/تطبيق|app development|application/.test(t)) return SERVICES[1];
    if(/ui|ux|واجهة|تجربة المستخدم/.test(t)) return SERVICES[2];
    if(/تسويق|marketing|campaign|حملة/.test(t)) return SERVICES[3];
    if(/seo|google|محركات البحث/.test(t)) return SERVICES[4];
    if(/ذكاء اصطناعي|ai|مساعد|موظف/.test(t)) return SERVICES[5];
    if(/أمن|security|cyber/.test(t)) return SERVICES[6];
    if(/نمو|growth|business development|تطوير أعمال/.test(t)) return SERVICES[7];
    return null;
  }
  function style(){
    if(document.getElementById('caiInteractiveStyle')) return;
    var s=document.createElement('style');s.id='caiInteractiveStyle';s.textContent=''+
      '#caiModal{position:fixed;inset:0;z-index:2147483000;display:none;align-items:center;justify-content:center;padding:16px;background:rgba(2,8,18,.78);backdrop-filter:blur(10px);font-family:Arial,Tahoma,sans-serif}'+
      '#caiModal.open{display:flex}#caiModal .caiBox{width:min(680px,100%);max-height:92dvh;overflow:auto;background:#f8fbff;color:#10213a;border-radius:24px;box-shadow:0 30px 100px rgba(0,0,0,.45);padding:22px}'+
      '#caiModal h2{margin:0 0 6px;font-size:27px}#caiModal p{color:#60738c;margin:0 0 16px;line-height:1.7}'+
      '#caiModal input,#caiModal textarea{width:100%;box-sizing:border-box;border:1px solid #d7e3f3;background:#fff;color:#172d49;border-radius:12px;padding:12px;margin:6px 0;font:inherit}#caiModal textarea{min-height:120px;resize:vertical}'+
      '#caiModal .caiActions{display:flex;gap:9px;margin-top:10px}#caiModal button{border:0;border-radius:12px;padding:12px 15px;font-weight:800;cursor:pointer}#caiModal .primary{background:linear-gradient(135deg,#2258e6,#7657ff);color:#fff;flex:1}#caiModal .secondary{background:#eaf1f8;color:#27415f}'+
      '#caiModal .caiStatus{margin-top:12px;min-height:24px;font-weight:700;color:#31506f}.caiGrid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin:14px 0}.caiTile{border:1px solid #d7e3f3;background:#fff;border-radius:14px;padding:13px;text-align:right;cursor:pointer;color:#17304e}.caiTile:hover{border-color:#77b8ff;box-shadow:0 7px 20px rgba(30,80,150,.1)}@media(max-width:600px){#caiModal .caiBox{border-radius:18px;padding:17px}.caiGrid{grid-template-columns:1fr}}';document.head.appendChild(s)
  }
  function modal(){
    style();var m=document.getElementById('caiModal');if(m)return m;
    m=document.createElement('div');m.id='caiModal';m.innerHTML='<div class="caiBox"><button id="caiClose" class="secondary" style="float:left" type="button">×</button><h2 id="caiTitle">Company AI</h2><p id="caiDesc"></p><div id="caiBody"></div><div class="caiActions"><button id="caiSend" class="primary" type="button">إرسال الطلب إلى Company AI</button><button id="caiCancel" class="secondary" type="button">إغلاق</button></div><div id="caiStatus" class="caiStatus"></div></div>';
    document.body.appendChild(m);m.addEventListener('click',function(e){if(e.target===m)close()});m.querySelector('#caiClose').onclick=close;m.querySelector('#caiCancel').onclick=close;return m;
  }
  function close(){var m=document.getElementById('caiModal');if(m)m.classList.remove('open')}
  function openService(s){
    var m=modal();m.dataset.service=s[0];m.classList.add('open');m.querySelector('#caiTitle').textContent=s[1];m.querySelector('#caiDesc').textContent=s[2]+' اكتب طلبك وسيتحوّل إلى طلب عميل داخل Company AI.';
    m.querySelector('#caiBody').innerHTML='<input id="caiName" placeholder="الاسم" autocomplete="name"><input id="caiEmail" placeholder="البريد الإلكتروني" type="email" autocomplete="email"><input id="caiCompany" placeholder="اسم الشركة (اختياري)"><textarea id="caiNeed" placeholder="اشرح المطلوب بالتفصيل"></textarea>';
    m.querySelector('#caiStatus').textContent='';m.querySelector('#caiSend').onclick=sendLead;
    setTimeout(function(){m.querySelector('#caiName').focus()},50)
  }
  async function sendLead(){
    var m=modal(),name=m.querySelector('#caiName').value.trim(),email=m.querySelector('#caiEmail').value.trim(),company=m.querySelector('#caiCompany').value.trim(),need=m.querySelector('#caiNeed').value.trim(),st=m.querySelector('#caiStatus');
    if(!name||!email||need.length<3){st.textContent='يرجى تعبئة الاسم والبريد ووصف المطلوب.';return}
    st.textContent='جاري إرسال الطلب…';
    try{
      var r=await fetch('/api/leads/public',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,email:email,company:company||null,country:null,language:(navigator.language||'ar').split('-')[0],need:'['+m.dataset.service+'] '+need,source:'website',budget:null})});
      var data=await r.json().catch(function(){return {}});
      if(!r.ok) throw Error(data.detail||('HTTP '+r.status));
      st.textContent='تم تسجيل الطلب بنجاح. فريق Company AI سيكمل المتابعة.';m.querySelector('#caiSend').disabled=true;
    }catch(e){st.textContent='تعذر الإرسال الآن: '+(e.message||'خطأ غير معروف')+' — يمكنك إعادة المحاولة.'}
  }
  function openAI(){
    var m=modal();m.dataset.service='ai';m.classList.add('open');m.querySelector('#caiTitle').textContent='تحدث مع Company AI';m.querySelector('#caiDesc').textContent='اكتب ما تريد بناءه أو تطويره، وسنحوّل طلبك إلى مسار عمل واضح.';m.querySelector('#caiBody').innerHTML='<textarea id="caiNeed" placeholder="مثلاً: أريد متجر إلكتروني مع CRM ومساعد AI…"></textarea>';m.querySelector('#caiStatus').textContent='';m.querySelector('#caiSend').onclick=async function(){var q=m.querySelector('#caiNeed').value.trim();if(q.length<2){m.querySelector('#caiStatus').textContent='اكتب طلبك أولاً.';return}m.querySelector('#caiStatus').textContent='جاري إرسال الطلب إلى العقل المركزي…';try{var r=await fetch('/api/central-ai/public-intake',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q,language:(navigator.language||'ar').split('-')[0],channel:'website'})});var d=await r.json().catch(function(){return {}});if(!r.ok)throw Error(d.detail||('HTTP '+r.status));m.querySelector('#caiStatus').textContent=d.message||d.reply||'تم استلام الطلب من Company AI.'}catch(e){m.querySelector('#caiStatus').textContent='تم فتح المسار، لكن الرد الآلي غير متاح حالياً. سجّل طلبك عبر نموذج الخدمة.'}};
  }
  function isVoice(t){return /صوت|voice|talk|speak|live|ميكروفون|محادثة صوت/.test(String(t||'').toLowerCase())}
  function wire(){
    document.addEventListener('click',function(e){
      var el=e.target&&e.target.closest?e.target.closest('button,a,[role="button"],.layanChoice,.choice,.chip'):null;if(!el)return;
      if(el.id==='caiClose'||el.id==='caiCancel'||el.closest('#caiModal'))return;
      var t=textOf(el),href=el.getAttribute('href')||'';
      if(isVoice(t)||el.classList.contains('voiceChoice')){if(window.startLayanVoice){e.preventDefault();e.stopPropagation();window.startLayanVoice()}return}
      var svc=matchService(t);if(svc){e.preventDefault();e.stopPropagation();openService(svc);return}
      if(/تحدث مع ليان|chat with layan|chat with ai|تحدث مع الذكاء|ابدأ مع ليان|ابدأ الآن|start/.test(t.toLowerCase())){e.preventDefault();e.stopPropagation();openAI();return}
      if(href==='#'||href==='javascript:void(0)'){e.preventDefault();}
    },true);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',wire);else wire();
  window.CompanyAIInteractive={openService:openService,openAI:openAI,close:close};
})();
