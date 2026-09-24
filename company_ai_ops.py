from __future__ import annotations
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import uuid

AGENTS = {
    "sales_crm": {"name":"Sales & CRM Agent","capabilities":["lead_capture","lead_qualification","follow_up"]},
    "web_development": {"name":"Web Development Agent","capabilities":["website_scope","technical_plan","qa"]},
    "app_development": {"name":"App Development Agent","capabilities":["app_scope","technical_plan","qa"]},
    "marketing": {"name":"Marketing & Growth Agent","capabilities":["campaigns","seo","conversion"]},
    "automation": {"name":"Automation Agent","capabilities":["workflow_design","integrations","automation"]},
    "finance_legal": {"name":"Finance & Legal Gate","capabilities":["approval_preparation","contract_review"]},
    "cybersecurity": {"name":"Security Agent","capabilities":["defensive_review","security_scope"]},
    "monitoring_operations": {"name":"Operations Agent","capabilities":["monitoring","incident_triage","backups"]},
}

class CompanyOps:
    def __init__(self):
        self.leads: dict[str,dict[str,Any]]={}
        self.tasks: dict[str,dict[str,Any]]={}
        self._lock=Lock()

    def create_lead(self, data:dict[str,Any], department:str="sales_crm"):
        now=datetime.now(timezone.utc).isoformat()
        lead_id="lead_"+uuid.uuid4().hex[:12]
        lead={"lead_id":lead_id,"created_at":now,"updated_at":now,"status":"new",
              "name":data["name"],"contact":data["contact"],"service":data.get("service",""),
              "message":data.get("message",""),"department":department,
              "next_action":"qualify_lead"}
        with self._lock:self.leads[lead_id]=lead
        return lead

    def list_leads(self,status:str|None=None):
        with self._lock:
            values=list(self.leads.values())
        return [x for x in values if not status or x["status"]==status]

    def create_task(self, title:str, department:str, *, lead_id:str|None=None,
                    approval_required:bool=False, next_actions:tuple[str,...]=()):
        task_id="task_"+uuid.uuid4().hex[:12]
        agent=AGENTS.get(department, {"name":"Central AI","capabilities":["general_business_routing"]})
        task={
            "task_id":task_id,
            "title":title,
            "department":department,
            "agent":agent["name"],
            "lead_id":lead_id,
            "status":"awaiting_approval" if approval_required else "queued",
            "approval_required":approval_required,
            "next_actions":list(next_actions),
            "handoff_ready":not approval_required,
            "created_at":datetime.now(timezone.utc).isoformat()
        }
        with self._lock:self.tasks[task_id]=task
        return task

    def mark_handoff_ready(self, task_id:str):
        with self._lock:
            task=self.tasks.get(task_id)
            if not task:
                return None
            if task["approval_required"]:
                task["handoff_ready"]=False
                task["status"]="awaiting_approval"
                return task
            task["handoff_ready"]=True
            task["status"]="ready_for_specialist"
            task["updated_at"]=datetime.now(timezone.utc).isoformat()
            return task

    def list_tasks(self,status:str|None=None):
        with self._lock:
            values=list(self.tasks.values())
        return [x for x in values if not status or x["status"]==status]

ops=CompanyOps()
