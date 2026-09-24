from pathlib import Path
import os, uuid
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent
WEB=ROOT/"company_ai_site"
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
API=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
app=FastAPI(title="Company AI",docs_url=None,redoc_url=None)

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

async def call_gemini(contents):
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None,"missing_key"
    payload={"systemInstruction":{"parts":[{"text":SYSTEM}]},"contents":contents,
             "generationConfig":{"maxOutputTokens":700,"temperature":0.55}}
    async with httpx.AsyncClient(timeout=45) as client:
        r=await client.post(API,headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=payload)
    if r.status_code>=400:
        print("Gemini error",r.status_code,r.text[:1000])
        return None,"provider_error"
    parts=r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[])
    text="".join(p.get("text","") for p in parts if p.get("text")).strip()
    return (text or None),(None if text else "empty")

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

