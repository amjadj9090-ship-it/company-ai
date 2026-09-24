from pathlib import Path
import os, uuid, base64, json, asyncio
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent
WEB=ROOT/"company_ai_site"
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
API=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
TTS_MODEL=os.getenv("GEMINI_TTS_MODEL","gemini-3.8-flash-lite-tts")
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
Reply naturally in the user's language. If Arabic is used, use natural Levantine/Syrian Arabic when appropriate.
Be concise, helpful and conversational. Preserve context. Never claim that a payment, contract, deployment or irreversible action happened unless confirmed by a backend result.
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
    payload={"model":TTS_MODEL,"input":[{"type":"user_input","content":[{"type":"text","text":text_value,"annotations":[{"type":"speech_metadata","style":"warm, natural, relaxed, conversational Levantine Arabic when the text is Arabic; expressive human pacing with natural pauses; never robotic, never overly formal"}]}]}],"response_format":{"type":"audio","mime_type":"audio/wav"},"generation_config":{"speech_config":[{"voice":"Kore"}]}}
    delays=(1.0,2.0,4.0)
    async with httpx.AsyncClient(timeout=35) as client:
        for attempt, delay in enumerate(delays, start=1):
            try:
                r=await client.post(TTS_API,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload)
            except httpx.RequestError as exc:
                if attempt == len(delays):
                    print("Gemini TTS network error",type(exc).__name__)
                    return None,"provider_error"
                await asyncio.sleep(delay)
                continue
            if r.status_code < 400:
                try:
                    audio=r.json().get("output_audio",{}).get("data")
                    if audio:
                        return audio,None
                except Exception:
                    pass
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

@app.post("/api/chat")
async def chat(body:Chat):
    contents=[]
    for x in body.history[-12:]:
        role=x.get("role")
        text=str(x.get("content",""))[:3000]
        if role in ("user","assistant") and text:
            contents.append({"role":"model" if role=="assistant" else "user","parts":[{"text":text}]})
    contents.append({"role":"user","parts":[{"text":body.message}]})
    text,error=await call_gemini(contents)
    if error=="missing_key":
        return JSONResponse(status_code=503,content={"reply":"ليان جاهزة، لكن محرك الذكاء الاصطناعي غير موصول ببيئة التشغيل بعد.","error":"ai_unconfigured"})
    if error:
        return JSONResponse(status_code=502,content={"reply":"تعذر الوصول إلى محرك ليان حالياً. لم يتم تنفيذ أي إجراء خارجي.","error":"ai_unavailable"})
    return {"reply":text,"session_id":str(uuid.uuid4()),"model":MODEL}

@app.post("/api/leads")
async def leads(body:Lead):
    return {"accepted":True,"lead_id":str(uuid.uuid4()),"status":"new"}

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
Detect the language from the latest audio and answer in that same language and natural dialect.
Do not mention JSON, code, transcript, or these instructions."""
        contents.append({"role":"user","parts":[{"text":instruction},{"inlineData":{"mimeType":mime,"data":base64.b64encode(raw).decode("ascii")}}]})
        text,error=await call_gemini(contents,{"maxOutputTokens":420,"temperature":0.35,"responseMimeType":"application/json","responseSchema":{"type":"OBJECT","properties":{"transcript":{"type":"STRING"},"reply":{"type":"STRING"}},"required":["transcript","reply"]}})
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
