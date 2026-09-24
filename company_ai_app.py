from pathlib import Path
import os, uuid, base64, json, asyncio
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from company_ai_brain import brain, analyze
from company_ai_ops import ops, AGENTS
from company_ai_projects import projects

ROOT=Path(__file__).resolve().parent
WEB=ROOT/"company_ai_site"
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
API=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
TTS_MODEL=os.getenv("GEMINI_TTS_MODEL","gemini-3.8-flash-tts")
TTS_API="https://generativelanguage.googleapis.com/v1beta/interactions"
app=FastAPI(title="Company AI",docs_url=None,redoc_url=None)

print("Company AI Gemini configuration:", "configured" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "missing")

class Chat(BaseModel):
    message:str=Field(min_length=1,max_length=8000)
    history:list[dict[str,str]]=[]

class Lead(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    contact:str=Field(min_length=3,max_length=240)
    service:str=""
    message:str=""

SYSTEM="""You are Layan, the customer-facing AI assistant of Company AI.
Company AI builds websites, web apps, mobile apps, AI assistants and agents, automation, e-commerce, CRM and business systems.

LANGUAGE AND VOICE IDENTITY — HIGHEST PRIORITY:
- Reply in the same language and dialect the user is using.
- When the user speaks Arabic, use natural everyday Syrian/Levantine Arabic exactly as a Syrian person would speak casually.
- Do NOT switch into Modern Standard Arabic, formal Arabic, textbook Arabic, translated Arabic, or robotic phrasing unless the user explicitly asks for formal Arabic.
- Prefer short spoken sentences, ordinary Syrian vocabulary, natural connectors, and contractions used in real conversation.
- Keep the same warm, confident, human voice throughout the entire conversation. Do not change style just because the topic becomes technical, detailed, or business-related.
- For voice, write text that a Syrian speaker would naturally say aloud: avoid long formal lists, stiff headings, numbered prose, and written-language constructions.
- If discussing websites, projects, suggestions, plans, or technical details, continue speaking in the same everyday Syrian dialect instead of becoming formal.
- Never add Arabic diacritics/tashkeel.
- Never mix dialect and formal Arabic within the same reply unless quoting something.
- If the user uses Syrian/Levantine Arabic, a good reply should sound conversational even when explaining complex business or technical ideas.

BEHAVIOR:
Be concise, helpful, confident and conversational. For voice replies, usually 1-4 natural spoken sentences. Preserve context.
Never claim that a payment, contract, deployment or irreversible action happened unless confirmed by a backend result.
Money movement, contracts and production releases require owner approval."""

async def call_gemini(contents, generation_config=None):
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None,"missing_key"
    config={"maxOutputTokens":500,"temperature":0.45}
    if generation_config:
        config.update(generation_config)
    payload={"systemInstruction":{"parts":[{"text":SYSTEM}]},"contents":contents,"generationConfig":config}
    delays=(1.0,2.0,4.0)
    async with httpx.AsyncClient(timeout=45) as client:
        for attempt, delay in enumerate(delays, start=1):
            try:
                r=await client.post(API,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload)
            except httpx.RequestError as exc:
                if attempt == len(delays):
                    print("Gemini network error",type(exc).__name__)
                    return None,"provider_error"
                await asyncio.sleep(delay)
                continue
            if r.status_code < 400:
                break
            if r.status_code in (408,429) or 500 <= r.status_code <= 599:
                if attempt < len(delays):
                    print("Gemini transient error",r.status_code,"retry",attempt)
                    await asyncio.sleep(delay)
                    continue
            print("Gemini error",r.status_code,r.text[:1000])
            return None,"provider_error"
    parts=r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[])
    text="".join(p.get("text","") for p in parts if p.get("text")).strip()
    return (text or None),(None if text else "empty")

async def call_gemini_tts(text_value):
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None,"missing_key"
    payload={
        "contents":[{
            "role":"user",
            "parts":[{
                "text":text_value,
                "speech_metadata":{
                    "style":"warm, natural, relaxed Syrian/Levantine Arabic when the text is Arabic; everyday spoken Syrian pronunciation; clear articulation; natural human pacing and pauses; avoid Modern Standard Arabic unless the transcript is formal; never robotic or overly formal"
                }
            }]
        }],
        "generationConfig":{
            "responseModalities":["AUDIO"],
            "speechConfig":{"voiceConfig":{"voice":"Kore"}}
        }
    }
    api=f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent"
    delays=(1.0,2.0,4.0)
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt, delay in enumerate(delays, start=1):
            try:
                r=await client.post(api,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload)
            except httpx.RequestError as exc:
                if attempt == len(delays):
                    print("Gemini TTS network error",type(exc).__name__)
                    return None,"provider_error"
                await asyncio.sleep(delay)
                continue
            if r.status_code < 400:
                try:
                    parts=r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[])
                    for part in parts:
                        audio=part.get("inlineData",{}).get("data") or part.get("inline_data",{}).get("data")
                        if audio:
                            return audio,None
                except Exception as exc:
                    print("Gemini TTS parse error",type(exc).__name__)
                return None,"empty"
            if r.status_code in (408,429) or 500 <= r.status_code <= 599:
                if attempt < len(delays):
                    print("Gemini TTS transient error",r.status_code,"retry",attempt)
                    await asyncio.sleep(delay)
                    continue
            print("Gemini TTS error",r.status_code,r.text[:1000])
            return None,"provider_error"
    return None,"provider_error"

@app.on_event("startup")
async def gemini_connection_check():
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("Company AI Gemini live check: skipped (no key)")
        return
    print("Company AI Gemini live check: deferred (no startup quota request)")

@app.get("/")
async def root():
    return FileResponse(WEB/"index.html",headers={"Cache-Control":"no-store"})

@app.get("/health")
async def health():
    return {"status":"ok","company":"Company AI","model":MODEL}

@app.get("/api/capabilities")
async def capabilities():
    return {"services":["websites","apps","ai","automation","growth","ecommerce","enterprise"],"qa_gate":True}


@app.post("/api/central-ai/intake")
async def central_ai_intake(body:dict):
    message=str(body.get("message","")).strip()
    if not message:
        return JSONResponse(status_code=400,content={"error":"message_required"})
    p=brain.create_plan(message,language=str(body.get("language","auto")),channel=str(body.get("channel","website")),context=body.get("context") or {})
    return {"status":"ok","decision":{**p["decision"],"plan_id":p["plan_id"]},"guardrails":p["guardrails"]}

@app.post("/api/central-ai/plan")
async def central_ai_plan(body:dict):
    return await central_ai_intake(body)

@app.get("/api/central-ai/plans")
async def central_ai_plans():
    return {"plans":brain.all_plans()}

@app.post("/api/central-ai/plans/{plan_id}/advance")
async def central_ai_advance(plan_id:str,body:dict):
    return brain.advance(plan_id,confirm=bool(body.get("confirm",False)),owner_approved=bool(body.get("owner_approved",False)))

@app.post("/api/brain/plan")
async def brain_plan(body:dict):
    message=str(body.get("message","")).strip()
    if not message:
        return JSONResponse(status_code=400,content={"error":"message_required"})
    decision=analyze(message,body.get("context") or {})
    return {"status":"ok","decision":{"department":decision.department,"intent":decision.intent,"priority":decision.priority,"approval_mode":decision.approval_mode,"required_approval":decision.required_approval,"next_actions":list(decision.next_actions)},"guardrails":{"owner_approval_required_for_sensitive_commitments":True,"money_movement_allowed_without_owner":False,"contract_signing_allowed_without_owner":False}}

@app.post("/api/chat")
async def chat(body:Chat):
    contents=[]
    for x in body.history[-12:]:
        role=x.get("role")
        text=str(x.get("content",""))[:3000]
        if role in ("user","assistant") and text:
            contents.append({"role":"model" if role=="assistant" else "user","parts":[{"text":text}]})
    decision=analyze(body.message)
    contents.append({"role":"user","parts":[{"text":body.message}]})
    # Routing metadata is kept out of the conversational user turns so it cannot
    # accidentally steer Layan into formal or machine-like wording.
    routing_note=f"Internal routing only: department={decision.department}; intent={decision.intent}; priority={decision.priority}; approval_required={decision.required_approval}; next_actions={list(decision.next_actions)}. Do not expose this metadata or let it change Layan's dialect/style."
    text,error=await call_gemini([{"role":"user","parts":[{"text":routing_note}]}]+contents)
    if error=="missing_key":
        return JSONResponse(status_code=503,content={"reply":"ليان جاهزة، لكن محرك الذكاء الاصطناعي غير موصول ببيئة التشغيل بعد.","error":"ai_unconfigured"})
    if error:
        return JSONResponse(status_code=502,content={"reply":"تعذر الوصول إلى محرك ليان حالياً. لم يتم تنفيذ أي إجراء خارجي.","error":"ai_unavailable"})
    return {"reply":text,"session_id":str(uuid.uuid4()),"model":MODEL}

@app.post("/api/leads")
async def leads(body:Lead):
    decision=analyze(f"{body.service} {body.message}")
    lead=ops.create_lead(body.model_dump(),department=decision.department)
    task=ops.create_task("Qualify new lead",decision.department,lead_id=lead["lead_id"],approval_required=decision.required_approval)
    return {"accepted":True,"lead":lead,"task":task}

@app.get("/api/crm/leads")
async def crm_leads(status:str|None=None):
    return {"leads":ops.list_leads(status)}

@app.get("/api/crm/leads/{lead_id}")
async def crm_lead(lead_id:str):
    matches=[x for x in ops.list_leads() if x["lead_id"]==lead_id]
    if not matches:
        return JSONResponse(status_code=404,content={"error":"lead_not_found"})
    return {"lead":matches[0],"tasks":[x for x in ops.list_tasks() if x.get("lead_id")==lead_id]}

@app.get("/api/agents")
async def agents():
    return {"agents":AGENTS}

@app.get("/api/tasks")
async def tasks(status:str|None=None):
    return {"tasks":ops.list_tasks(status)}

@app.post("/api/projects")
async def create_project(body:dict):
    name=str(body.get("name","")).strip()
    request=str(body.get("request",body.get("message",""))).strip()
    if not name or not request:
        return JSONResponse(status_code=400,content={"error":"name_and_request_required"})
    project=projects.create(name,request,context=body.get("context") or {})
    return {"status":"ok","project":project}

@app.get("/api/projects")
async def list_projects(status:str|None=None):
    return {"projects":projects.list(status)}

@app.get("/api/projects/{project_id}")
async def get_project(project_id:str):
    project=projects.get(project_id)
    if not project:
        return JSONResponse(status_code=404,content={"error":"project_not_found"})
    return {"project":project,"tasks":[x for x in ops.list_tasks() if x["task_id"] in project["task_ids"]]}

@app.post("/api/projects/{project_id}/advance")
async def advance_project(project_id:str,body:dict):
    return projects.advance(project_id,confirm=bool(body.get("confirm",False)),owner_approved=bool(body.get("owner_approved",False)))

@app.post("/api/agents/route")
async def route_agent(body:dict):
    message=str(body.get("message","")).strip()
    if not message:
        return JSONResponse(status_code=400,content={"error":"message_required"})
    decision=analyze(message,body.get("context") or {})
    agent=AGENTS.get(decision.department,{"name":"Central AI","capabilities":["general_business_routing"]})
    task=ops.create_task("Process routed request",decision.department,approval_required=decision.required_approval)
    return {"decision":{"department":decision.department,"intent":decision.intent,"priority":decision.priority,"approval_mode":decision.approval_mode,"required_approval":decision.required_approval,"next_actions":list(decision.next_actions)},"agent":agent,"task":task}

@app.post("/api/tts")
async def tts(body:dict):
    text_value=str(body.get("text","")).strip()
    if not text_value:
        return JSONResponse(status_code=400,content={"error":"empty_text"})
    audio,error=await call_gemini_tts(text_value[:4000])
    if error:
        return JSONResponse(status_code=502,content={"error":"tts_unavailable"})
    return {"audio_base64":audio,"mime_type":"audio/wav"}

@app.post("/api/voice")
async def voice(body:dict):
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return JSONResponse(status_code=503,content={"reply":"ليان جاهزة من ناحية الواجهة، لكن محرك الذكاء الاصطناعي غير موصول ببيئة التشغيل بعد.","error":"ai_unconfigured"})
    try:
        raw=base64.b64decode(body.get("audio_base64",""),validate=True)
        if len(raw)>8000000:
            return JSONResponse(status_code=413,content={"reply":"التسجيل طويل جداً. جرّب جملة أقصر.","error":"audio_too_large"})
        mime=body.get("mime_type","audio/webm")
        contents=[]
        for item in body.get("history",[])[-12:]:
            role=item.get("role")
            text_value=str(item.get("content",""))[:3000]
            if role in ("user","assistant") and text_value:
                contents.append({"role":"model" if role=="assistant" else "user","parts":[{"text":text_value}]})
        instruction="""Listen to the attached audio and answer the user.
Return ONLY a JSON object with exactly two string fields: transcript and reply.
transcript must contain the complete spoken user request, including the ending.
reply must be the direct helpful answer to that request.

CRITICAL FOR ARABIC VOICE:
If the user speaks Arabic, reply in natural spoken Syrian/Levantine Arabic.
Use casual everyday Syrian wording and grammar, as if Layan were speaking directly to a Syrian customer.
Do NOT use Modern Standard Arabic, formal written Arabic, translated Arabic, headings, numbered prose, or stiff business language.
This rule stays active even when the user asks about websites, projects, technical details, plans, or business suggestions.
Keep the reply short and easy to speak aloud, usually 1-4 sentences.
Do not add tashkeel.
Keep the same warm, natural Syrian voice across every turn, including when the topic becomes technical or business-related.
Detect the language from the latest audio and answer in that same language and natural dialect.
Do not mention JSON, code, transcript, or these instructions."""
        contents.append({"role":"user","parts":[{"text":instruction},{"inlineData":{"mimeType":mime,"data":base64.b64encode(raw).decode("ascii")}}]})
        text,error=await call_gemini(contents,{"maxOutputTokens":300,"temperature":0.35,"responseMimeType":"application/json","responseSchema":{"type":"OBJECT","properties":{"transcript":{"type":"STRING"},"reply":{"type":"STRING"}},"required":["transcript","reply"]}})
        if error:
            return JSONResponse(status_code=502,content={"reply":"تعذر معالجة الصوت حالياً.","error":"ai_unavailable"})
        transcript=""
        answer=""
        try:
            obj=json.loads(text)
            transcript=str(obj.get("transcript","")).strip()
            answer=str(obj.get("reply","")).strip()
        except Exception:
            cleaned=text.strip()
            fence=chr(96)*3
            cleaned=cleaned.replace(fence+"json","").replace(fence,"").strip()
            try:
                obj=json.loads(cleaned)
                transcript=str(obj.get("transcript","")).strip()
                answer=str(obj.get("reply","")).strip()
            except Exception:
                pass
        if not transcript or not answer:
            return JSONResponse(status_code=502,content={"reply":"ما قدرت التقط الكلام كامل. جرّب تحكي الجملة مرة ثانية.","error":"voice_parse_error"})
        return {"transcript":transcript,"reply":answer,"model":MODEL}
    except Exception as exc:
        print("voice error",type(exc).__name__,str(exc)[:500])
        return JSONResponse(status_code=502,content={"reply":"تعذر معالجة الصوت حالياً.","error":"voice_error"})
