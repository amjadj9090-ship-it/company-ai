from pathlib import Path
import json, re
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"launch-v1"/"data"
def load(name): return json.loads((DATA/name).read_text(encoding="utf-8"))
def normalize(text): return re.sub(r"\s+"," ",text or "").strip().lower()
def route_request(text):
    t=normalize(text); routing=load("routing.json")
    scores=[]
    for rule in routing["rules"]:
        score=sum(1 for k in rule["keywords"] if normalize(k) in t)
        if score:scores.append((score,rule["agent"],rule["id"]))
    scores.sort(reverse=True)
    return {"agent":scores[0][1] if scores else "orchestrator","service":scores[0][2] if scores else None,"confidence":scores[0][0] if scores else 0}
def approvals_required(text):
    t=normalize(text); out=[]
    for rule in load("routing.json")["escalations"]:
        if any(normalize(k) in t for k in rule["keywords"]): out.append(rule["approval"])
    return sorted(set(out))
def plan(text):
    return {"route":route_request(text),"approvals":approvals_required(text),"status":"needs_approval" if approvals_required(text) else "ready_for_agent"}
