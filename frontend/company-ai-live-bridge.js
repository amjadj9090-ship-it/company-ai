(function(){
  'use strict';
  const API=(location.protocol==='file:'?'http://localhost:8000':'');
  const VERSION='20260916-05';
  window.COMPANY_AI_LIVE_BRIDGE_VERSION=VERSION;

  function setText(id,text){const e=document.getElementById(id);if(e)e.textContent=text;}
  function clean(s){return String(s||'').replace(/[<>]/g,'');}
  async function request(path,body){
    const r=await fetch(API+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
    let d={}; try{d=await r.json()}catch(_){d={detail:await r.text()}}
    if(!r.ok) throw new Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }

  // Real agent-builder workflow.
  window.buildAgent=async function(){
    const r=document.getElementById('agentResult');
    const name=document.getElementById('agentName')?.value.trim();
    const role=document.getElementById('agentRole')?.value.trim();
    const purpose=document.getElementById('agentPurpose')?.value.trim();
    const channel=document.getElementById('agentChannel')?.value||'website';
    const language=document.getElementById('agentLanguage')?.value||'ar';
    const autonomy=document.getElementById('agentAutonomy')?.value||'assisted';
    if(!name||!role||!purpose){if(r)r.textContent='أكمل اسم الوكيل ودوره والهدف أولاً.';return;}
    if(r)r.textContent='جاري إنشاء الوكيل واختباره فعلياً…';
    try{
      const d=await request('/api/agent-builder/builds',{name,role,purpose,channels:[channel],languages:[language],knowledge:[],tools:[],autonomy,personality:'professional',human_approval_required:true});
      const t=await request('/api/agent-builder/builds/'+d.id+'/test',{message:purpose,language,channel});
      if(r)r.innerHTML='<b>تم التنفيذ فعلياً ✓</b><br>رقم الوكيل: '+d.id+'<br>اختبار الوكيل: '+clean(t.status||'ok')+'<br>'+clean(t.response||'تم الاختبار بنجاح')+'<br><br>الوكيل مسجل ويحتاج مراجعة بشرية قبل إطلاقه.';
    }catch(e){if(r)r.textContent='فشل التنفيذ الفعلي: '+e.message;}
  };

  window.submitLead=async function(){
    const st=document.getElementById('leadStatus');
    const data={name:document.getElementById('name')?.value.trim(),email:document.getElementById('email')?.value.trim(),company:document.getElementById('company')?.value.trim(),country:document.getElementById('country')?.value.trim(),language:window.lang||'auto',need:document.getElementById('need')?.value.trim(),source:'website'};
    if(!data.name||!data.email||!data.need){if(st)st.textContent='يرجى تعبئة الاسم والبريد والحاجة.';return;}
    if(st)st.textContent='جاري تسجيل الطلب فعلياً…';
    try{const d=await request('/api/leads/public',data);if(st)st.textContent='تم تسجيل الطلب فعلياً ✓ — رقم الفرصة: '+d.lead_id;if(typeof window.syncLeadToCRM==='function')window.syncLeadToCRM(d,data);}
    catch(e){if(st)st.textContent='تعذر تسجيل الطلب: '+e.message;}
  };

  window.createSalesAgent=async function(){
    const name=document.getElementById('salesAgentName')?.value.trim(),purpose=document.getElementById('salesAgentPurpose')?.value.trim(),r=document.getElementById('salesAgentResult');
    if(!name||!purpose){if(r)r.textContent='أكمل الاسم والهدف.';return;}
    if(r)r.textContent='جاري إنشاء موظف المبيعات واختباره فعلياً…';
    try{
      const d=await request('/api/agent-builder/builds',{name,role:'موظف مبيعات AI',purpose,channels:['website'],languages:['ar','en'],knowledge:['products','pricing','faq'],tools:['CRM','lead_capture'],autonomy:'supervised',personality:'professional',human_approval_required:true});
      window.salesAgentId=d.id;
      const t=await request('/api/agent-builder/builds/'+d.id+'/test',{message:'أريد معرفة المنتج المناسب لشركتي.'});
      const o=await request('/api/sales-agent/'+d.id+'/operations');
      if(r)r.innerHTML='<b>تم إنشاء موظف المبيعات واختباره ✓</b><br>رقم الوكيل: '+d.id+'<br>الاختبار: '+clean(t.status||'ok')+'<br>'+clean(t.response||'تم الاختبار')+'<br><br>المعرفة: '+o.knowledge_items+' • الذاكرة: '+o.memory_items+' • الأدوات: '+o.tool_actions+' • التصعيد: '+o.escalation_rules;
      setText('salesOpsResult','موظف المبيعات جاهز. يمكنك الآن إضافة المعرفة والذاكرة وتشغيل الأدوات.');
    }catch(e){if(r)r.textContent='فشل التنفيذ الفعلي: '+e.message;}
  };

  // Universal service/section router. Cards without their own controls become real actions.
  const routes=[
    [/استشارة|consultation/, 'entrepreneurship', 'استشارة أولية مجانية: أريد فهم فكرتي والسوق ونموذج العمل والخطوة التالية.'],
    [/جدوى|feasibility/, 'entrepreneurship', 'أريد دراسة جدوى اقتصادية لمشروعي، مع السوق والاستثمار والتكاليف والإيرادات والمخاطر.'],
    [/startup|ريادة/, 'entrepreneurship', 'أريد بناء مشروع ناشئ من الفكرة حتى خطة التنفيذ والإطلاق.'],
    [/أمن سيبراني|cybersecurity|security/, 'cybersecurity', 'أريد خدمة أمن سيبراني دفاعية مصرح بها وفحصاً أمنياً لنطاق محدد.'],
    [/مراقبة|تشغيل مستمر|monitoring|operations/, 'monitoring_operations', 'أريد مراقبة وتشغيل مستمر للموقع أو النظام مع تنبيهات وأعطال ونسخ احتياطية.'],
    [/نمو الموقع|فحص الموقع|تقييم الموقع|website growth|website audit/, 'website_growth', 'أريد فحص موقعي وتحسين الأداء وتجربة المستخدم والتحويل وSEO.'],
    [/تطبيق|apps|app development/, 'app_development', 'أريد بناء تطبيق: أريد تحديد المستخدمين والوظائف والنطاق والخطة التقنية.'],
    [/موقع|تطوير المواقع|website/, 'digital_services', 'أريد بناء أو تطوير موقع إلكتروني مع تحديد الصفحات والوظائف والنمو.'],
    [/مبيعات|sales|موظف مبيعات/, 'sales_crm', 'أريد تحسين المبيعات والتقاط العملاء وتأهيلهم ومتابعتهم عبر CRM.'],
    [/خدمة العملاء|customer support|دعم/, 'customer_support', 'أريد تحسين خدمة العملاء والردود والتصعيد والمتابعة.'],
    [/تسويق|marketing|SEO|حملة|campaign/, 'marketing', 'أريد خطة تسويق رقمية واستقطاب عملاء وSEO وحملات قابلة للقياس.'],
    [/تحليل أعمال|analytics|Business Intelligence|BI/, 'central_brain', 'أريد تحليل أعمال ومؤشرات أداء وتوصيات مبنية على البيانات.'],
    [/أتمتة|automation|Workflow/, 'operations', 'أريد تحويل عملية متكررة إلى Workflow آلي مترابط مع الأنظمة والوكلاء.'],
    [/أكاديمية|academy|AI Agents|Prompting/, 'agent_builder', 'أريد تعلم الذكاء الاصطناعي ثم تطبيقه ببناء وكيل AI حقيقي.'],
    [/عضوية|membership/, 'central_brain', 'أريد معرفة عضوية Company AI وما الذي تشملُه من أدوات ودعم واستشارات.'],
    [/منتج|SaaS|Business OS|السوق/, 'digital_services', 'أريد شراء أو بناء منتج رقمي أو SaaS من منتجات Company AI.'],
  ];

  function routeFor(title){
    const t=String(title||'').trim().toLowerCase();
    for(const [rx,department,message] of routes) if(rx.test(t)) return {department,message,title};
    return {department:'central_brain',message:'أريد معرفة الحل المناسب للخدمة: '+title,title};
  }

  async function runCardAction(title,source){
    const route=routeFor(title);
    if(typeof window.openAI==='function') window.openAI();
    const goal=document.getElementById('goalInput');
    if(goal){goal.value=route.message;goal.focus();}
    setText('modalResult','تم ربط «'+title+'» مع مسار '+route.department+' في العقل المركزي. جاري فحص المسار…');
    try{
      const d=await request('/api/ai-employees/execute',{message:route.message,language:document.documentElement.lang||'ar',channel:'website',context:{source:'homepage',card_title:title,department_hint:route.department,authorized_testing:false}});
      const employee=d.employee||{},decision=d.decision||{},execution=d.execution||{};
      const approval=decision.required_approval?' يحتاج موافقة المالك قبل العمليات الحساسة.':' ضمن الصلاحيات القياسية.';
      setText('modalResult','✓ تم التوجيه فعلياً إلى «'+clean(employee.slug||route.department)+'». المسار: '+clean(decision.intent||'general')+' — الخطوة التالية: '+clean((decision.next_actions||[]).join(' → '))+approval);
      return d;
    }catch(e){
      setText('modalResult','تم فتح المسار «'+title+'»، لكن تعذر الاتصال بمحرك الوكلاء: '+e.message);
      return null;
    }
  }

  function bindCards(){
    document.querySelectorAll('#services .card,#capabilities .card,#entrepreneurship .cards > .card,#marketplace .cards > .card,#ai-employees .cards > .card,#academy .cards > .card,#business-audit .cards > .card,#membership .cards > .card,#growth .card').forEach(card=>{
      if(card.dataset.caiBound)return;
      if(card.querySelector('button,input,textarea,select,a'))return;
      card.dataset.caiBound='1';card.setAttribute('role','button');card.setAttribute('tabindex','0');
      const title=card.querySelector('h3,h2')?.textContent?.trim()||'الخدمة';
      const activate=()=>runCardAction(title,'card');
      card.addEventListener('click',activate);card.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}});
    });
    document.querySelectorAll('#sectors .chip').forEach(chip=>{
      if(chip.dataset.caiBound)return;chip.dataset.caiBound='1';chip.setAttribute('role','button');chip.setAttribute('tabindex','0');
      const activate=()=>runCardAction('حلول Company AI لقطاع '+chip.textContent.trim(),'sector');
      chip.addEventListener('click',activate);chip.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}});
    });
  }

  // Keep voice controls alive even when an older realtime hotfix is not loaded.
  window.openLayanVoice=window.openLayanVoice||function(){const s=document.getElementById('layanVoiceStage');if(!s)return; s.classList.add('open');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';setText('layanVoiceState','ليان جاهزة');setText('layanVoiceSub','اضغط «تحدث مع ليان» وابدأ كلامك.');};
  window.closeLayanVoice=window.closeLayanVoice||function(){const s=document.getElementById('layanVoiceStage');if(s)s.classList.remove('open');document.body.style.overflow='';try{if(window.speechSynthesis)window.speechSynthesis.cancel()}catch(_){};};
  window.demoLayanVoice=window.demoLayanVoice||function(){const text=(window.lang==='ar'?'مرحباً، أنا ليان. احكي لي شو بدك تنجز، وأنا بساعدك نحدد الحل والخطوة التالية.':'Hello, I am Layan. Tell me what you want to achieve and I will help define the right next step.');setText('layanVoiceText',text);setText('layanVoiceState','ليان تتحدث');const s=document.getElementById('layanVoiceStage');if(s)s.classList.add('speaking');if('speechSynthesis' in window){const u=new SpeechSynthesisUtterance(text);u.lang=(window.LAYAN_LANGS?.[window.lang]?.bcp)||'ar-SA';u.onend=()=>{if(s)s.classList.remove('speaking');setText('layanVoiceState','ليان جاهزة')};speechSynthesis.cancel();speechSynthesis.speak(u)}else if(s){setTimeout(()=>s.classList.remove('speaking'),1500)}};
  window.toggleLayanVoice=window.toggleLayanVoice||function(){
    const s=document.getElementById('layanVoiceStage'),b=document.getElementById('layanStart');if(!s)return;
    if(s.classList.contains('listening')){s.classList.remove('listening');if(b)b.textContent='🎙️ تحدث مع ليان';setText('layanVoiceState','ليان جاهزة');try{window.__layanRec?.stop()}catch(_){};return;}
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){setText('layanVoiceText','المتصفح لا يدعم التعرف على الكلام. يمكنك استخدام «تجربة رد ليان» أو الدردشة النصية.');return;}
    const rec=new SR();window.__layanRec=rec;rec.lang=(window.LAYAN_LANGS?.[window.lang]?.bcp)||'ar-SA';rec.interimResults=false;rec.continuous=false;
    rec.onstart=()=>{s.classList.add('listening');if(b)b.textContent='⏹ إيقاف الاستماع';setText('layanVoiceState','ليان تستمع…')};
    rec.onresult=e=>{const text=e.results?.[0]?.[0]?.transcript||'';setText('layanVoiceText',text);if(typeof window.runCardAction==='function'){};try{runCardAction('محادثة صوتية مع ليان: '+text,'voice')}catch(_){};};
    rec.onerror=e=>{s.classList.remove('listening');if(b)b.textContent='🎙️ تحدث مع ليان';setText('layanVoiceState','تعذر الاستماع');setText('layanVoiceSub','تأكد من إذن الميكروفون أو استخدم تجربة الرد.');console.warn(e)};
    rec.onend=()=>{s.classList.remove('listening');if(b)b.textContent='🎙️ تحدث مع ليان';setText('layanVoiceState','ليان جاهزة')};
    try{rec.start()}catch(e){setText('layanVoiceText','تعذر تشغيل الميكروفون: '+e.message)}
  };

  function boot(){bindCards();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
  window.addEventListener('load',()=>setTimeout(bindCards,250));
  window.addEventListener('unhandledrejection',e=>console.error('Company AI unhandled rejection',e.reason));
})();
