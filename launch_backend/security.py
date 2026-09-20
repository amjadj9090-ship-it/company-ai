from fastapi import HTTPException
SENSITIVE={"money_movement","contract","irreversible_production_change","security_exception"}
def enforce_approval(required):
    if required:
        raise HTTPException(status_code=409,detail={"code":"approval_required","approval":required})
def can_agent(agent,permission):
    return permission in set(agent.get("permissions",[]))
