from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def registry():
    return json.loads((ROOT/"launch-v1/data/agents.json").read_text(encoding="utf-8"))["agents"]
def public_registry():
    return [{"id":x["id"],"name":x["name"],"scope":x["scope"]} for x in registry()]
def get_agent(agent_id):
    return next((x for x in registry() if x["id"]==agent_id),None)
