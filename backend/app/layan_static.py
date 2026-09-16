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
  function cardText(el){return ((el.innerText||el.textContent||'')+' '+(el.getAttribute('aria-label')||'')).trim()}
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
    if(!el) return;
    var s=service(cardText(el));
    if(s && window.CompanyAIInteractive && window.CompanyAIInteractive.openService){
      e.preventDefault(); e.stopPropagation(); window.CompanyAIInteractive.openService(s);
    }
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
        return Response(content=content, media_type="application/javascript")
    except Exception:
        return FileResponse(_HOTFIX, media_type="application/javascript")


@router.get("/assets/layan-office.webp", include_in_schema=False)
def layan_office_asset():
    return Response(content=_LAYAN_FALLBACK_SVG, media_type="image/svg+xml")
