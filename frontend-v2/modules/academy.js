const ACADEMY_FALLBACK={name:"Company AI Academy",mission:"A structured AI learning path inside Company AI, from foundations to building real AI systems.",progression:["understand","apply","create"],tracks:[]};

async function loadAcademy(){
  const r=await fetch("/api/academy/catalog",{cache:"no-store"});
  if(!r.ok) throw new Error("Academy catalog unavailable");
  return r.json();
}

const academyLabels={
  ar:{title:"أكاديمية الذكاء الاصطناعي",sub:"تعلّم الذكاء الاصطناعي من الأساسيات إلى بناء الأنظمة الحقيقية.",progress:"افهم → طبّق → أنشئ",open:"استكشف الأكاديمية",lessons:"درس",project:"مشروع عملي",start:"ابدأ المسار",quality:"معايير التعلم"},
  en:{title:"AI Academy",sub:"Learn AI from foundations to building real-world AI systems.",progress:"Understand → Apply → Create",open:"Explore the Academy",lessons:"lessons",project:"Practical project",start:"Start track",quality:"Learning standards"}
};
const academyText=(k,language)=>academyLabels[language]?.[k]||academyLabels.en[k];

export async function openAcademy({lang,$,esc,closeDrawer,openChat}){
  const d=$("#drawer");
  d.innerHTML='<div class="drawer-panel"><div class="drawer-body academy-loading">Loading AI Academy…</div></div>';
  d.classList.add("open");
  try{
    const a=await loadAcademy();
    d.innerHTML=`<div class="drawer-panel academy-panel">
      <div class="drawer-head"><div><div class="eyebrow">COMPANY AI ACADEMY</div><h2>${esc(academyText("title",lang))}</h2><p>${esc(academyText("sub",lang))}</p></div><button class="close" data-close>×</button></div>
      <div class="drawer-body">
        <div class="academy-intro"><strong>${esc(academyText("progress",lang))}</strong><span>${esc(a.mission)}</span></div>
        <div class="academy-tracks">${a.tracks.map(track=>`<section class="academy-track">
          <div class="academy-track-head"><span class="academy-level">${esc(track.level)}</span><div><h3>${esc(track.title)}</h3><p>${esc(track.description)}</p></div></div>
          <div class="academy-courses">${track.courses.map(c=>`<article class="academy-course">
            <h4>${esc(c.title)}</h4><div class="academy-meta">${c.lessons} ${esc(academyText("lessons",lang))}</div><p><b>${esc(academyText("project",lang))}:</b> ${esc(c.project)}</p>
            <button class="link-btn academy-course-btn" data-course="${esc(c.id)}">${esc(academyText("start",lang))} →</button>
          </article>`).join("")}</div>
        </section>`).join("")}</div>
        <section class="academy-quality"><h3>${esc(academyText("quality",lang))}</h3><ul>${a.quality_rules.map(x=>`<li>${esc(x)}</li>`).join("")}</ul><small>${esc(a.framework_note)}</small></section>
      </div>
    </div>`;
    d.querySelector("[data-close]").onclick=closeDrawer;
    d.onclick=e=>{if(e.target===d)closeDrawer()};
    d.querySelectorAll("[data-course]").forEach(b=>b.onclick=()=>openChat(b.closest(".academy-course").querySelector("h4").textContent));
  }catch(e){d.querySelector(".drawer-body").innerHTML=`<div class="detail"><h2>AI Academy</h2><p>${esc(e.message)}</p></div>`}
}
window.openAcademy=openAcademy;
