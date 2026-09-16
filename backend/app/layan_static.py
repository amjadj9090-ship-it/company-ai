from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

router = APIRouter()

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
_HOTFIX = _FRONTEND / "layan-realtime-hotfix.js"
_INTERACTIVE = _FRONTEND / "company-ai-interactive.js"

# Keep the public Layan asset URL alive even when the binary portrait asset is
# not present in the deployment bundle. This prevents a broken-image failure
# in the realtime overlay and gives the voice UI a deterministic visual base.
_LAYAN_FALLBACK_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 900 1200\"><defs><linearGradient id=\"bg\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#17324f\"/><stop offset=\"1\" stop-color=\"#06101d\"/></linearGradient><linearGradient id=\"dress\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\"><stop stop-color=\"#eef5ff\"/><stop offset=\"1\" stop-color=\"#b9c8dc\"/></linearGradient></defs><rect width=\"900\" height=\"1200\" fill=\"url(#bg)\"/><circle cx=\"450\" cy=\"380\" r=\"145\" fill=\"#d9b39b\"/><path d=\"M300 385c15-190 285-220 300 0-45-60-78-92-150-98-72 6-105 38-150 98z\" fill=\"#34251f\"/><path d=\"M315 555c35-78 90-118 135-118s100 40 135 118l90 500H225z\" fill=\"url(#dress)\"/><circle cx=\"395\" cy=\"375\" r=\"10\" fill=\"#172235\"/><circle cx=\"505\" cy=\"375\" r=\"10\" fill=\"#172235\"/><path d=\"M410 445c28 18 52 18 80 0\" fill=\"none\" stroke=\"#8b5f55\" stroke-width=\"7\" stroke-linecap=\"round\"/><text x=\"450\" y=\"1110\" text-anchor=\"middle\" fill=\"#dcecff\" font-family=\"Arial,sans-serif\" font-size=\"34\" font-weight=\"700\">LAYAN · COMPANY AI</text></svg>"""

_SERVICE_CARD_PATCH = r'''
(function(){
  'use strict';
  if(window.__COMPANY_AI_SERVICE_CARDS__) return;
  window.__COMPANY_AI_SERVICE_CARDS__=true;
  function esc(v){return String(v||'').replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\\':'\\\\','"':'&quot;'}[c]||c})}
  function service(text){
    var t=String(text||'').toLowerCase();
    if(/موقع|website|web design|تصميم مواقع/.test(t)) return ['web','تصميم مواقع','موقع شركة، متجر، صفحة هبوط أو منصة ويب كاملة.'];
    if(/تطبيق|app development|application/.test(t)) return ['app','تطوير التطبيقات','تطبيق Android/iOS أو تطبيق أعمال مخصص.'];
    if(/ui|ux|واجهة|تجربة المستخدم/.test(t)) return ['uiux','UI/UX','تصميم تجربة المستخدم والواجهات بشكل احترافي.'];
    if(/تسويق|marketing|campaign|حملة/.test(t)) return ['marketing','التسويق الرقمي','خطة تسويق، محتوى، حملات واكتساب عملاء.'];
    if(/seo|google|محركات البحث/.test(t)) return ['seo','SEO','تحسين الظهور في Google وبناء نمو عضوي.'];
    if(/ذكاء اصطناعي|ai|مساعد|موظف/.test(t)) return ['ai','حلول الذكاء الاصطناعي','مساعدات AI، أتمتة، CRM وموظفون AI.'];
    if(/أمن|security|cyber/.test(t)) return ['security','الأمن السيبراني','تقييم أمني وحماية الأنظمة ضمن نطاق مصرح به.'];
    if(/نمو|growth|business development|تطوير أعمال/.test(t)) return ['growth','النمو وتطوير الأعمال','تحليل السوق، العملاء، التسعير وخطة النمو.'];
    return null;
  }
  function ensureStyle(){
    if(document.getElementById('caiCardStyle')) return;
    var s=document.createElement('style');s.id='caiCardStyle';s.textContent='#caiCardModal{position:fixed;inset:0;z-index:2147483647;display:none;align-items:center;justify-content:center;padding:16px;background:rgba(2,8,18,.82);font-family:Arial,Tahoma,sans-serif}#caiCardModal.open{display:flex}#caiCardModal .box{width:min(650px,100%);max-height:92dvh;overflow:auto;background:#f8fbff;color:#10213a;border-radius:22px;padding:20px;box-shadow:0 30px 100px rgba(0,0,0,.5)}#caiCardModal h2{margin:0 0 6px}#caiCardModal p{color:#60738c;line-height:1.7}#caiCardModal input,#caiCardModal textarea{width:100%;box-sizing:border-box;border:1px solid #d7e3f3;border-radius:11px;padding:12px;margin:6px 0;font:inherit}#caiCardModal textarea{min-height:120px}#caiCardModal .actions{display:flex;gap:8px;margin-top:10px}#caiCardModal button{border:0;border-radius:11px;padding:12px 15px;font-weight:800;cursor:pointer}.caiPrimary{background:linear-gradient(135deg,#2258e6,#7657ff);color:#fff;flex:1}.caiSecondary{background:#eaf1f8;color:#27415f}.caiStatus{margin-top:10px;font-weight:700;color:#31506f}';document.head.appendChild(s)
  }
  function open(s){
    ensureStyle();
    var m=document.getElementById('caiCardModal');
    if(!m){m=document.createElement('div');m.id='caiCardModal';m.innerHTML='<div class="box"><button class="caiSecondary" id="caiCardClose" type="button">×</button><h2 id="caiCardTitle"></h2><p id="caiCardDesc"></p><input id="caiCardName" placeholder="الاسم" autocomplete="name"><input id="caiCardEmail" placeholder="البريد الإلكتروني" type="email" autocomplete="email"><input id="caiCardCompany" placeholder="اسم الشركة (اختياري)"><textarea id="caiCardNeed" placeholder="اشرح المطلوب بالتفصيل"></textarea><div class="actions"><button class="caiPrimary" id="caiCardSend" type="button">إرسال الطلب</button><button class="caiSecondary" id="caiCardCancel" type="button">إغلاق</button></div><div class="caiStatus" id="caiCardStatus"></div></div>';document.body.appendChild(m);m.querySelector('#caiCardClose').onclick=close;m.querySelector('#caiCardCancel').onclick=close;m.addEventListener('click',function(e){if(e.target===m)close()})}
    m.dataset.service=s[0];m.querySelector('#caiCardTitle').textContent=s[1];m.querySelector('#caiCardDesc').textContent=s[2]+' اكتب طلبك وسيتحول مباشرة إلى فرصة داخل Company AI.';m.querySelector('#caiCardStatus').textContent='';m.querySelector('#caiCardSend').disabled=false;m.querySelector('#caiCardSend').onclick=send;m.classList.add('open');setTimeout(function(){m.querySelector('#caiCardName').focus()},30)
  }
  function close(){var m=document.getElementById('caiCardModal');if(m)m.classList.remove('open')}
  async function send(){
    var m=document.getElementById('caiCardModal'),name=m.querySelector('#caiCardName').value.trim(),email=m.querySelector('#caiCardEmail').value.trim(),company=m.querySelector('#caiCardCompany').value.trim(),need=m.querySelector('#caiCardNeed').value.trim(),st=m.querySelector('#caiCardStatus');
    if(!name||!email||need.length<3){st.textContent='يرجى تعبئة الاسم والبريد ووصف المطلوب.';return}
    st.textContent='جاري إرسال الطلب…';
    try{var r=await fetch('/api/leads/public',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,email:email,company:company||null,country:null,language:(navigator.language||'ar').split('-')[0],need:'['+m.dataset.service+'] '+need,source:'website',budget:null})});var d=await r.json().catch(function(){return{}});if(!r.ok)throw Error(d.detail||('HTTP '+r.status));st.textContent='تم تسجيل الطلب بنجاح. فريق Company AI سيكمل المتابعة.';m.querySelector('#caiCardSend').disabled=true}catch(e){st.textContent='تعذر الإرسال الآن: '+(e.message||'خطأ غير معروف')}
  }
  document.addEventListener('click',function(e){
    var el=e.target&&e.target.closest?e.target.closest('#services .card'):null;
    if(!el)return;
    var s=service((el.innerText||el.textContent||'').trim());
    if(s){e.preventDefault();e.stopImmediatePropagation();open(s)}
  },true);
})();
'''

@router.get("/layan-realtime-hotfix.js", include_in_schema=False)
def layan_realtime_hotfix():
    # The homepage already loads this URL. Bundle the public interaction bridge
    # here as well so the existing production index becomes functional without
    # changing the large HTML asset or risking duplicate script tags.
    try:
        content = (
            _HOTFIX.read_text(encoding="utf-8")
            + "\n"
            + _INTERACTIVE.read_text(encoding="utf-8")
            + "\n"
            + _SERVICE_CARD_PATCH
        )
        return Response(content=content, media_type="application/javascript", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})
    except Exception:
        return FileResponse(_HOTFIX, media_type="application/javascript", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})


@router.get("/assets/layan-office.webp", include_in_schema=False)
def layan_office_asset():
    return Response(content=_LAYAN_FALLBACK_SVG, media_type="image/svg+xml")
