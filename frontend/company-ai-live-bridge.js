(function(){
  'use strict';
  const API=(location.protocol==='file:'?'http://localhost:8000':'');
  const VERSION='20260916-04';
  window.COMPANY_AI_LIVE_BRIDGE_VERSION=VERSION;
  function setText(id,text){const e=document.getElementById(id);if(e)e.textContent=text;}
  async function request(path,body){
    const r=await fetch(API+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
    let d={}; try{d=await r.json()}catch(_){d={detail:await r.text()}}
    if(!r.ok) throw new Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }
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
      if(r)r.innerHTML='<b>تم التنفيذ فعلياً ✓</b><br>رقم الوكيل: '+d.id+'<br>اختبار الوكيل: '+(t.status||'ok')+'<br>'+String(t.response||'تم الاختبار بنجاح').replace(/[<>]/g,'')+'<br><br>الوكيل الآن مسجل في النظام ويحتاج مراجعة بشرية قبل إطلاقه.';
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
    const name=document.getElementById('salesAgentName')?.value.trim();
    const purpose=document.getElementById('salesAgentPurpose')?.value.trim();
    const r=document.getElementById('salesAgentResult');
    if(!name||!purpose){if(r)r.textContent='أكمل الاسم والهدف.';return;}
    if(r)r.textContent='جاري إنشاء موظف المبيعات واختباره فعلياً…';
    try{
      const d=await request('/api/agent-builder/builds',{name,role:'موظف مبيعات AI',purpose,channels:['website'],languages:['ar','en'],knowledge:['products','pricing','faq'],tools:['CRM','lead_capture'],autonomy:'supervised',personality:'professional',human_approval_required:true});
      window.salesAgentId=d.id;
      const t=await request('/api/agent-builder/builds/'+d.id+'/test',{message:'أريد معرفة المنتج المناسب لشركتي.'});
      const o=await request('/api/sales-agent/'+d.id+'/operations');
      if(r)r.innerHTML='<b>تم إنشاء موظف المبيعات واختباره ✓</b><br>رقم الوكيل: '+d.id+'<br>الاختبار: '+(t.status||'ok')+'<br>'+String(t.response||'تم الاختبار').replace(/[<>]/g,'')+'<br><br>المعرفة: '+o.knowledge_items+' • الذاكرة: '+o.memory_items+' • الأدوات: '+o.tool_actions+' • التصعيد: '+o.escalation_rules;
      setText('salesOpsResult','موظف المبيعات جاهز. يمكنك الآن إضافة المعرفة والذاكرة وتشغيل الأدوات.');
    }catch(e){if(r)r.textContent='فشل التنفيذ الفعلي: '+e.message;}
  };
  function bindServiceCards(){
    document.querySelectorAll('#services .card').forEach((card)=>{
      if(card.dataset.caiBound)return; card.dataset.caiBound='1'; card.setAttribute('role','button'); card.setAttribute('tabindex','0');
      const title=card.querySelector('h3')?.textContent?.trim()||'الخدمة';
      const activate=()=>{if(typeof window.openAI==='function')window.openAI();const g=document.getElementById('goalInput');if(g){g.value='أريد معرفة الحل المناسب لخدمة: '+title;g.focus();}setText('modalResult','تم اختيار «'+title+'». اضغط «تحليل» لتحديد الحل والخطوة التالية.');};
      card.addEventListener('click',activate);card.addEventListener('keydown',(e)=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}});
    });
  }
  function boot(){bindServiceCards();try{if(typeof window.refreshCentralDashboard==='function')window.refreshCentralDashboard();}catch(_){} }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
  window.addEventListener('unhandledrejection',e=>{console.error('Company AI unhandled rejection',e.reason);});
})();
