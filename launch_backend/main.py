from launch_backend.orchestrator import plan
from launch_backend.agents import public_registry
from launch_backend.schemas import PlanIn
from fastapi import APIRouter
router=APIRouter(prefix="/launch-api")
@router.get("/company/agents")
async def company_agents(): return {"agents":public_registry()}
@router.post("/company/plan")
async def company_plan(body:PlanIn): return plan(body.message)
