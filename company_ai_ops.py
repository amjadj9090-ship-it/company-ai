from __future__ import annotations
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import json
import os
import uuid

AGENTS = {
    "sales_crm": {"name":"Sales & CRM Agent","capabilities":["lead_capture","lead_qualification","follow_up"]},
    "web_development": {"name":"Web Development Agent","capabilities":["website_scope","technical_plan","qa"]},
    "website_growth": {"name":"Website Growth Agent","capabilities":["site_audit","conversion","optimization"]},
    "app_development": {"name":"App Development Agent","capabilities":["app_scope","technical_plan","qa"]},
    "marketing": {"name":"Marketing & Growth Agent","capabilities":["campaigns","seo","conversion"]},
    "automation": {"name":"Automation Agent","capabilities":["workflow_design","integrations","automation"]},
    "finance_legal": {"name":"Finance & Legal Gate","capabilities":["approval_preparation","contract_review"]},
    "cybersecurity": {"name":"Security Agent","capabilities":["defensive_review","security_scope"]},
    "monitoring_operations": {"name":"Operations Agent","capabilities":["monitoring","incident_triage","backups"]},
    "entrepreneurship": {"name":"Entrepreneurship Agent","capabilities":["idea_qualification","market_analysis","roadmap"]},
}

class CompanyOps:
    def __init__(self):
        self.leads: dict[str,dict[str,Any]]={}
        self.tasks: dict[str,dict[str,Any]]={}
        self._lock=Lock()
        self._db_url=os.getenv("DATABASE_URL","").strip()
        self._db_ready=False

    def _db(self):
        if not self._db_url:
            return None
        try:
            import psycopg
            from psycopg.rows import dict_row
            db_url=self._db_url
            if "sslmode=" not in db_url:
                db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
            conn=psycopg.connect(db_url, connect_timeout=10, row_factory=dict_row)
            self._ensure_schema(conn)
            return conn
        except Exception:
            return None

    def _ensure_schema(self, conn):
        if self._db_ready:
            return
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS company_ai_leads (
                    lead_id TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    status TEXT NOT NULL,
                    name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    service TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL,
                    next_action TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS company_ai_tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    department TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    lead_id TEXT NULL,
                    status TEXT NOT NULL,
                    approval_required BOOLEAN NOT NULL DEFAULT FALSE,
                    next_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
                    handoff_ready BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NULL
                )
            """)
        conn.commit()
        self._db_ready=True

    def create_lead(self, data:dict[str,Any], department:str="sales_crm"):
        now=datetime.now(timezone.utc)
        lead_id="lead_"+uuid.uuid4().hex[:12]
        lead={"lead_id":lead_id,"created_at":now.isoformat(),"updated_at":now.isoformat(),"status":"new",
              "name":data["name"],"contact":data["contact"],"service":data.get("service",""),
              "message":data.get("message",""),"department":department,
              "next_action":"qualify_lead"}
        conn=self._db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""INSERT INTO company_ai_leads
                        (lead_id,created_at,updated_at,status,name,contact,service,message,department,next_action)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (lead_id,now,now,"new",lead["name"],lead["contact"],lead["service"],lead["message"],department,"qualify_lead"))
                conn.commit()
                conn.close()
                return lead
            except Exception:
                conn.rollback(); conn.close()
        with self._lock:self.leads[lead_id]=lead
        return lead

    def list_leads(self,status:str|None=None):
        conn=self._db()
        if conn:
            try:
                with conn.cursor() as cur:
                    if status:
                        cur.execute("SELECT * FROM company_ai_leads WHERE status=%s ORDER BY created_at DESC",(status,))
                    else:
                        cur.execute("SELECT * FROM company_ai_leads ORDER BY created_at DESC")
                    rows=cur.fetchall()
                conn.close()
                return [dict(x) for x in rows]
            except Exception:
                conn.rollback(); conn.close()
        with self._lock:
            values=list(self.leads.values())
        return [x for x in values if not status or x["status"]==status]

    def create_task(self, title:str, department:str, *, lead_id:str|None=None,
                    approval_required:bool=False, next_actions:tuple[str,...]=()):
        task_id="task_"+uuid.uuid4().hex[:12]
        agent=AGENTS.get(department, {"name":"Central AI","capabilities":["general_business_routing"]})
        now=datetime.now(timezone.utc)
        task={
            "task_id":task_id,"title":title,"department":department,"agent":agent["name"],
            "lead_id":lead_id,"status":"awaiting_approval" if approval_required else "queued",
            "approval_required":approval_required,"next_actions":list(next_actions),
            "handoff_ready":not approval_required,"created_at":now.isoformat()
        }
        conn=self._db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""INSERT INTO company_ai_tasks
                        (task_id,title,department,agent,lead_id,status,approval_required,next_actions,handoff_ready,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                        (task_id,title,department,agent["name"],lead_id,task["status"],approval_required,
                         json.dumps(list(next_actions)),not approval_required,now))
                conn.commit(); conn.close()
                return task
            except Exception:
                conn.rollback(); conn.close()
        with self._lock:self.tasks[task_id]=task
        return task

    def mark_handoff_ready(self, task_id:str):
        conn=self._db()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM company_ai_tasks WHERE task_id=%s",(task_id,))
                    task=cur.fetchone()
                    if not task:
                        conn.close(); return None
                    if task["approval_required"]:
                        cur.execute("UPDATE company_ai_tasks SET handoff_ready=FALSE,status='awaiting_approval',updated_at=%s WHERE task_id=%s",(datetime.now(timezone.utc),task_id))
                    else:
                        cur.execute("UPDATE company_ai_tasks SET handoff_ready=TRUE,status='ready_for_specialist',updated_at=%s WHERE task_id=%s",(datetime.now(timezone.utc),task_id))
                    conn.commit()
                    cur.execute("SELECT * FROM company_ai_tasks WHERE task_id=%s",(task_id,))
                    row=cur.fetchone()
                conn.close()
                if row:
                    row["next_actions"]=row.get("next_actions") or []
                    return dict(row)
            except Exception:
                conn.rollback(); conn.close()
        with self._lock:
            task=self.tasks.get(task_id)
            if not task:return None
            if task["approval_required"]:
                task["handoff_ready"]=False; task["status"]="awaiting_approval"; return task
            task["handoff_ready"]=True; task["status"]="ready_for_specialist"
            task["updated_at"]=datetime.now(timezone.utc).isoformat(); return task

    def list_tasks(self,status:str|None=None):
        conn=self._db()
        if conn:
            try:
                with conn.cursor() as cur:
                    if status:
                        cur.execute("SELECT * FROM company_ai_tasks WHERE status=%s ORDER BY created_at DESC",(status,))
                    else:
                        cur.execute("SELECT * FROM company_ai_tasks ORDER BY created_at DESC")
                    rows=cur.fetchall()
                conn.close()
                result=[]
                for row in rows:
                    row=dict(row)
                    row["next_actions"]=row.get("next_actions") or []
                    result.append(row)
                return result
            except Exception:
                conn.rollback(); conn.close()
        with self._lock:
            values=list(self.tasks.values())
        return [x for x in values if not status or x["status"]==status]

ops=CompanyOps()
