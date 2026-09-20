from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os, httpx

app=FastAPI(title="Company AI Launch V1", docs_url=None, redoc_url=None)
app.mount("/launch-v1", StaticFiles(directory="launch-v1"), name="launch-v1")
app.mount("/assets", StaticFiles(directory="assets"), name="launch-assets")

class ChatIn(BaseModel):
    message:str
    language:str="ar"

@app.get("/")
async def root():
    return FileResponse("launch-v1/index.html", headers={"Cache-Control":"no-store"})

@app.post("/launch-api/chat")
async def chat(body:ChatIn):
    key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return {"reply":"ليان جاهزة، لكن محرك الذكاء الاصطناعي للمشروع الجديد لم تُضف له مفتاح التشغيل بعد."}
    prompt=f"Reply to the user in the same language as requested ({body.language}). Be concise, natural and helpful. User: {body.message}"
    url="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r=await client.post(url,params={"key":key},json={"contents":[{"parts":[{"text":prompt}]}]})
            r.raise_for_status()
            data=r.json()
            reply=data["candidates"][0]["content"]["parts"][0]["text"]
            return {"reply":reply}
    except Exception:
        return {"reply":"صار خلل مؤقت بالاتصال بمحرك ليان. الواجهة نفسها مستقلة وما تأثرت."}
