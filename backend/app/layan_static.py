from pathlib import Path
import base64

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

router = APIRouter()

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
_HOTFIX = _FRONTEND / "layan-realtime-hotfix.js"
_INTERACTIVE = _FRONTEND / "company-ai-interactive.js"

_LAYAN_FALLBACK_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 900 1200\"><rect width=\"900\" height=\"1200\" fill=\"#10253d\"/><circle cx=\"450\" cy=\"380\" r=\"145\" fill=\"#d9b39b\"/><path d=\"M300 385c15-190 285-220 300 0-45-60-78-92-150-98-72 6-105 38-150 98z\" fill=\"#34251f\"/><path d=\"M315 555c35-78 90-118 135-118s100 40 135 118l90 500H225z\" fill=\"#dbe7f5\"/><circle cx=\"395\" cy=\"375\" r=\"10\" fill=\"#172235\"/><circle cx=\"505\" cy=\"375\" r=\"10\" fill=\"#172235\"/><text x=\"450\" y=\"1110\" text-anchor=\"middle\" fill=\"#dcecff\" font-family=\"Arial,sans-serif\" font-size=\"34\" font-weight=\"700\">LAYAN · COMPANY AI</text></svg>"""

_SERVICE_CARD_PATCH = r'''
(function(){
  'use strict';
  if(window.__COMPANY_AI_SERVICE_CARDS__) return;
  window.__COMPANY_AI_SERVICE_CARDS__=true;
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
  document.addEventListener('click',function(e){
    var el=e.target&&e.target.closest?e.target.closest('#services .card'):null;
    if(!el)return;
    var s=service((el.innerText||el.textContent||'').trim());
    if(!s)return;
    e.preventDefault();e.stopImmediatePropagation();
    if(window.CompanyAIInteractive&&typeof window.CompanyAIInteractive.openService==='function'){
      window.CompanyAIInteractive.openService(s);return;
    }
    if(typeof window.openAI==='function'){
      window.openAI();
      setTimeout(function(){var i=document.getElementById('goalInput');if(i){i.value='أريد خدمة: '+s[1]+' — '+s[2];i.focus();}},50);
    }
  },true);
})();
'''

@router.get("/", include_in_schema=False)
def public_home():
    html = (_FRONTEND / "index.html").read_text(encoding="utf-8")
    html = html.replace("/layan-realtime-hotfix.js?v=20260915-01", "/layan-realtime-hotfix.js?v=20260916-02")
    fallback = r'''<script>(function(){function wire(){document.querySelectorAll('#services .card').forEach(function(card){if(card.dataset.caiFallbackBound==='1')return;card.dataset.caiFallbackBound='1';card.style.cursor='pointer';card.setAttribute('role','button');card.addEventListener('click',function(e){if(e.target&&e.target.closest&&e.target.closest('button,a,input,textarea,select'))return;var title=(card.querySelector('h3')||{}).textContent||'خدمة Company AI';var desc=(card.querySelector('p')||{}).textContent||'';if(typeof window.openAI==='function'){window.openAI();setTimeout(function(){var input=document.getElementById('goalInput');if(input){input.value='أريد خدمة: '+title.trim()+' — '+desc.trim();input.focus();}},60)}else{location.hash='#contact'}},false)})}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',wire);else wire();if(window.MutationObserver)new MutationObserver(wire).observe(document.documentElement,{childList:true,subtree:true})})();</script>'''
    html = html.replace("</body>", fallback + "</body>")
    return Response(content=html, media_type="text/html", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})

@router.get("/layan-realtime-hotfix.js", include_in_schema=False)
def layan_realtime_hotfix():
    try:
        content = _HOTFIX.read_text(encoding="utf-8") + "\n" + _INTERACTIVE.read_text(encoding="utf-8") + "\n" + _SERVICE_CARD_PATCH
        return Response(content=content, media_type="application/javascript", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})
    except Exception:
        return FileResponse(_HOTFIX, media_type="application/javascript", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})

@router.get("/assets/layan-office.webp", include_in_schema=False)
def layan_office_asset():
    """Serve the approved repository WebP asset instead of the legacy fallback."""
    try:
        asset = _FRONTEND.parent / "assets" / "layan-office.webp"
        return Response(content=asset.read_bytes(), media_type="image/webp", headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache"})
    except Exception:
        return Response(content=_LAYAN_FALLBACK_SVG, media_type="image/svg+xml")
