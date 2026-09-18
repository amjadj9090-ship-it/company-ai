from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
import os
import re
import urllib.error
import urllib.request
import base64
import io
import wave

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(tags=["public-ui"])


def _main():
    from . import main
    return main


def _now():
    return datetime.now(timezone.utc)


def _add(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    main = _main()
    with main.Session(main.engine) as s:
        row = main.Entity(kind=kind, data=data, created_at=_now(), updated_at=_now())
        s.add(row); s.commit(); s.refresh(row)
        return {"id": row.id, **row.data}


def _get(kind: str, entity_id: int):
    main = _main()
    with main.Session(main.engine) as s:
        row = s.get(main.Entity, entity_id)
        if not row or row.kind != kind:
            raise HTTPException(404, f"{kind} record not found")
        return row


class AgentBuild(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    role: str = "AI employee"
    purpose: str = Field(min_length=3, max_length=6000)
    channels: list[str] = Field(default_factory=lambda: ["website"])
    languages: list[str] = Field(default_factory=lambda: ["auto"])
    knowledge: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    autonomy: str = "supervised"
    personality: str = "professional"
    human_approval_required: bool = True

class Conversation(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    email: str | None = None
    language: str = "auto"
    channel: str = "website"
    assistant: str = "layan"
    history: list[dict[str, Any]] = Field(default_factory=list)


class SpeechIn(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    language: str = "auto"
\nclass Qualification(BaseModel):
    lead_id: int
    message: str = Field(min_length=1, max_length=8000)
    budget: str | None = None
    timeline: str | None = None
    decision_role: str | None = None
    language: str = "auto"

class KnowledgeIn(BaseModel):
    category: str = "products"
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    approved: bool = False

class MemoryIn(BaseModel):
    summary: str = Field(min_length=1, max_length=5000)
    stage: str = "qualified"
    next_action: str = "متابعة مع العميل"

class ToolIn(BaseModel):
    action_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)

class EscalationIn(BaseModel):
    trigger: str
    action: str
    priority: str = "high"
    enabled: bool = True

class SmartProposal(BaseModel):
    lead_id: int
    product_ids: list[int] = Field(default_factory=list)
    title: str | None = None
    notes: str | None = None
    discount_percent: float = Field(default=0, ge=0, le=100)

class ProposalAction(BaseModel):
    proposal_id: int


@router.post("/api/agent-builder/builds")
def create_agent_build(payload: AgentBuild):
    data = payload.model_dump(); data.update({"status":"ready","created_via":"public-ui","created_at":_now().isoformat()})
    return _add("agent_builds", data)

@router.post("/api/agent-builder/builds/{build_id}/test")
def test_agent_build(build_id: int, payload: dict[str, Any]):
    row = _get("agent_builds", build_id)
    message = str(payload.get("message", "اختبار موظف الذكاء الاصطناعي")).strip()
    from .central_brain import plan
    decision = plan(message, {})
    return {"status":"passed","build_id":build_id,"response":"تم اختبار مسار الوكيل بنجاح: "+message,"decision":{"department":decision.department,"intent":decision.intent},"human_approval_required":bool(row.data.get("human_approval_required",True))}

@router.get("/api/sales-agent/public/config")
def public_sales_config():
    main = _main()
    with main.Session(main.engine) as s:
        rows = s.scalars(select(main.Entity).where(main.Entity.kind == "agent_builds")).all()
        row = next((r for r in rows if r.data.get("slug") == "public-sales-ai" or r.data.get("public_chat")), None)
        if not row:
            row = main.Entity(kind="agent_builds",data={"slug":"public-sales-ai","name":"Company AI Sales Employee","role":"sales","public_chat":True,"status":"active"},created_at=_now(),updated_at=_now()); s.add(row); s.commit(); s.refresh(row)
        return {"status":"ok","build_id":row.id,**row.data}

@router.get("/api/sales-agent/{agent_id}/operations")
def sales_operations(agent_id: int):
    _get("agent_builds", agent_id); main=_main(); counts={}
    with main.Session(main.engine) as s:
        for kind in ("sales_knowledge","sales_memory","sales_tool_actions","sales_escalation_rules"):
            counts[kind]=len(s.scalars(select(main.Entity).where(main.Entity.kind==kind,main.Entity.data["agent_id"].as_integer()==agent_id)).all())
    return {"knowledge_items":counts["sales_knowledge"],"memory_items":counts["sales_memory"],"tool_actions":counts["sales_tool_actions"],"escalation_rules":counts["sales_escalation_rules"]}

@router.post("/api/sales-agent/{agent_id}/conversation")
def sales_conversation(agent_id:int,payload:Conversation):
    _get("agent_builds",agent_id)
    message=payload.message.strip()
    language=_detect_language(message, payload.language)
    reply=_gemini_reply(message, language, payload.channel, payload.history[-10:])
    lead=None
    if payload.email:
        try:
            main=_main()
            with main.Session(main.engine) as s:
                lead=main.Entity(kind="crm_lead",data={"name":"Website visitor","email":payload.email,"source":"website-sales-agent","service":None,"stage":"new","owner":"sales","message":message},created_at=_now(),updated_at=_now())
                s.add(lead); s.commit(); s.refresh(lead); lead={"id":lead.id,**lead.data}
        except Exception: lead=None
    return {"status":"ok","reply":reply,"language":language,"engine":"gemini","lead":lead,"recommendations":[{"name":"Website Starter"},{"name":"Website Pro"},{"name":"Business App"}]}

def _detect_language(message: str, requested: str | None) -> str:
    requested=(requested or "").strip().lower()
    if requested and requested not in {"auto","null","undefined"}: return requested.split("-")[0]
    if re.search(r"[\\u0600-\\u06ff]", message): return "ar"
    if re.search(r"[\\u3040-\\u30ff]", message): return "ja"
    if re.search(r"[\\uac00-\\ud7af]", message): return "ko"
    if re.search(r"[\\u4e00-\\u9fff]", message): return "zh"
    if re.search(r"[\\u0400-\\u04ff]", message): return "ru"
    if re.search(r"[\\u00c0-\\u024f]", message): return "fr"
    return "en"

def _gemini_reply(message: str, language: str, channel: str, history: list[Any]) -> str:
    api_key=os.getenv("GEMINI_API_KEY","").strip()
    if not api_key: raise HTTPException(status_code=503, detail="Gemini AI service is not configured: GEMINI_API_KEY is missing.")
    model=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite").strip() or "gemini-2.5-flash-lite"
    system=("You are Layan, the central AI assistant for Company AI. Understand the user's actual intent and context. "
            "Reply naturally as a real conversational assistant, not like a translation or template. Preserve context and answer directly. "
            "LANGUAGE/DIALECT RULE: identify the language and dialect/register used by the user from the current message and conversation. "
            "Reply entirely in that same language and, when the user is using a recognizable dialect, stay entirely in that dialect. "
            "For Arabic, this is strict: if the user speaks Levantine/Shami Arabic, answer in natural Levantine/Shami Arabic only. "
            "Do not mix Levantine with Modern Standard Arabic. Do not insert formal MSA phrases into a Shami reply unless the user explicitly uses MSA or asks for it. "
            "Likewise, do not mix Gulf, Egyptian, Iraqi, Maghrebi, or other Arabic dialects. If the user speaks MSA, answer in MSA; if the user speaks another language, answer fully in that language. "
            "Keep grammar, vocabulary, sentence flow, and conversational tone consistent from start to finish. Avoid canned, translated-sounding, robotic phrasing. "
            "Never claim money transfer, withdrawal, payment, contract signing, or protected commitment was completed without owner approval. "
            "For protected requests, explain approval is required and offer a draft/next step. "
            f"Detected language: {language}. Channel: {channel}.")
    contents=[]
    for item in history:
        if not isinstance(item,dict): continue
        role="model" if item.get("role") in {"assistant","model"} else "user"
        txt=str(item.get("text") or item.get("content") or "").strip()
        if txt: contents.append({"role":role,"parts":[{"text":txt[:8000]}]})
    contents.append({"role":"user","parts":[{"text":message}]})
    payload={"systemInstruction":{"parts":[{"text":system}]},"contents":contents}
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req=urllib.request.Request(url,data=json.dumps(payload).encode("utf-8"),method="POST",headers={"x-goog-api-key":api_key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=30) as response: data=json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502,detail=f"Gemini provider error: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=504,detail="Gemini provider timeout.") from exc
    parts=((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    reply="".join(str(p.get("text","")) for p in parts if isinstance(p,dict)).strip()
    if not reply: raise HTTPException(status_code=502,detail="Gemini returned an empty response.")
    return reply


@router.post("/api/sales-agent/{agent_id}/speech")
def sales_speech(agent_id: int, payload: SpeechIn):
    _get("agent_builds", agent_id)
    api_key=os.getenv("GEMINI_API_KEY","").strip()
    if not api_key: raise HTTPException(status_code=503, detail="Gemini AI service is not configured: GEMINI_API_KEY is missing.")
    language=_detect_language(payload.text, payload.language)
    model=os.getenv("GEMINI_TTS_MODEL","gemini-2.5-flash-preview-tts").strip() or "gemini-2.5-flash-preview-tts"
    voice=os.getenv("GEMINI_TTS_VOICE","Aoede").strip() or "Aoede"
    if language=="ar":
        prompt=("Speak this reply as Layan, a warm professional female assistant in natural Levantine/Shami Arabic. "
                "Keep the spoken Arabic conversational and locally natural, without switching into Modern Standard Arabic. "
                "Use a calm, confident, human office-conversation pace. Do not read instructions aloud.\n\n")
    else:
        prompt=("Speak this reply as Layan, a warm professional female assistant. Match the language of the text exactly, "
                "with a natural conversational office tone, clear pacing, and no robotic or announcer style. Do not read instructions aloud.\n\n")
    request_payload={
        "model":model,
        "input":prompt+payload.text.strip(),
        "response_format":{"type":"audio"},
        "generation_config":{"speech_config":[{"voice":voice}]},
    }
    url="https://generativelanguage.googleapis.com/v1beta/interactions"
    req=urllib.request.Request(url,data=json.dumps(request_payload).encode("utf-8"),method="POST",headers={"x-goog-api-key":api_key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=30) as response: data=json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502,detail=f"Gemini TTS provider error: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=504,detail="Gemini TTS provider timeout.") from exc
    raw=((data.get("output_audio") or {}).get("data") or "").strip()
    if not raw: raise HTTPException(status_code=502,detail="Gemini TTS returned no audio.")
    try:
        pcm=base64.b64decode(raw)
        buf=io.BytesIO()
        with wave.open(buf,"wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000); wf.writeframes(pcm)
        audio_b64=base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        raise HTTPException(status_code=502,detail="Gemini TTS audio format was invalid.") from exc
    return {"status":"ok","language":language,"engine":"gemini-tts","model":model,"voice":voice,"audio_base64":audio_b64}

@router.post("/api/sales-agent/{agent_id}/qualify")
def qualify(agent_id:int,payload:Qualification):
    _get("agent_builds",agent_id); answers=sum(bool(x and str(x).strip()) for x in (payload.budget,payload.timeline,payload.decision_role)); score=min(100,40+answers*20); stage="high_intent" if score>=80 else ("qualified" if score>=60 else "needs_followup")
    return {"status":"ok","lead_id":payload.lead_id,"score":score,"stage":stage,"missing_questions":["الميزانية","الموعد","دور اتخاذ القرار"][answers:]}

@router.post("/api/sales-agent/{agent_id}/knowledge")
def add_knowledge(agent_id:int,payload:KnowledgeIn):
    _get("agent_builds",agent_id); return _add("sales_knowledge",{**payload.model_dump(),"agent_id":agent_id,"status":"approved" if payload.approved else "pending_review"})

@router.post("/api/sales-agent/{agent_id}/memory")
def add_memory(agent_id:int,payload:MemoryIn):
    _get("agent_builds",agent_id); return _add("sales_memory",{**payload.model_dump(),"agent_id":agent_id})

@router.post("/api/sales-agent/{agent_id}/tools")
def run_tool(agent_id:int,payload:ToolIn):
    _get("agent_builds",agent_id); sensitive=any(x in payload.action_type.lower() for x in ("transfer","withdraw","contract","discount"))
    return _add("sales_tool_actions",{**payload.model_dump(),"agent_id":agent_id,"status":"approval_required" if sensitive else "recorded","human_approval_required":sensitive})

@router.post("/api/sales-agent/{agent_id}/escalation-rules")
def add_escalation(agent_id:int,payload:EscalationIn):
    _get("agent_builds",agent_id); return _add("sales_escalation_rules",{**payload.model_dump(),"agent_id":agent_id})

@router.post("/api/proposals/smart")
def smart_proposal(payload:SmartProposal):
    main=_main()
    if payload.discount_percent>0: return {"status":"approval_required","executed":False,"human_approval_required":True,"reason":"Any non-standard discount requires owner approval."}
    total=0.0; selected=[]
    with main.Session(main.engine) as s:
        for pid in payload.product_ids:
            row=s.get(main.Entity,pid)
            if row and row.kind=="products":
                price=float(row.data.get("price",0) or 0); total+=price; selected.append({"id":pid,"name":row.data.get("name",f"Product {pid}"),"price":price})
    if not selected: raise HTTPException(400,"No valid product IDs were found")
    data={"lead_id":payload.lead_id,"title":payload.title or "Company AI Proposal","notes":payload.notes,"product_ids":payload.product_ids,"items":selected,"total":round(total,2),"currency":"USD","status":"draft","human_approval_required":False,"created_at":_now().isoformat()}
    return _add("proposals",data)

@router.post("/api/proposals/{proposal_id}/accept")
def proposal_accept(proposal_id:int,payload:ProposalAction):
    if proposal_id!=payload.proposal_id: raise HTTPException(400,"proposal_id mismatch")
    main=_main()
    with main.Session(main.engine) as s:
        row=s.get(main.Entity,proposal_id)
        if not row or row.kind!="proposals": raise HTTPException(404,"Proposal not found")
        row.data={**row.data,"status":"accepted_by_customer","accepted_at":_now().isoformat()}; row.updated_at=_now(); s.commit()
    return {"proposal_id":proposal_id,"status":"accepted_by_customer"}

@router.post("/api/proposals/{proposal_id}/followups")
def proposal_followup(proposal_id:int,payload:dict[str,Any]):
    _get("proposals",proposal_id); return _add("proposal_followups",{"proposal_id":proposal_id,**payload,"status":"scheduled","created_at":_now().isoformat()})

@router.post("/api/proposals/{proposal_id}/order")
def proposal_order(proposal_id:int,payload:ProposalAction):
    if proposal_id!=payload.proposal_id: raise HTTPException(400,"proposal_id mismatch")
    main=_main()
    with main.Session(main.engine) as s:
        proposal=s.get(main.Entity,proposal_id)
        if not proposal or proposal.kind!="proposals": raise HTTPException(404,"Proposal not found")
        if proposal.data.get("status")!="accepted_by_customer": raise HTTPException(409,"Customer acceptance is required")
        existing=next((x for x in s.scalars(select(main.Entity).where(main.Entity.kind=="orders")).all() if x.data.get("proposal_id")==proposal_id),None)
        if existing:return {"id":existing.id,**existing.data}
        order=main.Entity(kind="orders",data={"proposal_id":proposal_id,"lead_id":proposal.data.get("lead_id"),"status":"confirmed","payment_status":"unpaid","execution_locked":bool(proposal.data.get("human_approval_required"))},created_at=_now(),updated_at=_now()); s.add(order); s.commit(); s.refresh(order)
        return {"id":order.id,**order.data}
