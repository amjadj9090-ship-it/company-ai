import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
os.environ['JWT_SECRET']='test-secret-key-32-characters-long-123456';os.environ['PASSWORD_PEPPER']='test-pepper';os.environ['DEMO_ADMIN_PASSWORD']='change-me'
from fastapi.testclient import TestClient
from app.main import app, permission_decision
c=TestClient(app)
def login():
 r=c.post('/api/auth/login',json={'email':'owner@example.com','password':'change-me'}); assert r.status_code==200; return {'Authorization':'Bearer '+r.json()['access_token']}
def test_health(): assert c.get('/health').status_code==200
def test_auth_summary_agents():
 h=login(); assert c.get('/api/summary',headers=h).status_code==200; assert len(c.get('/api/agents',headers=h).json())>=15
def test_public_lead_and_funnel():
 r=c.post('/api/leads/public',json={'name':'Test Client','email':'client@example.com','company':'Acme','country':'DE','language':'en','need':'We need a website and AI automation','source':'organic'}); assert r.status_code==200; lid=r.json()['lead_id']; h=login(); assert c.post(f'/api/leads/{lid}/qualify',headers=h).status_code==200; assert c.get('/api/growth/funnel',headers=h).json()['qualified']==1
def test_proposal_and_approval():
 h=login(); lead=c.post('/api/leads/public',json={'name':'B','email':'b@example.com','need':'mobile app'}).json()['lead_id']; p=c.post('/api/proposals/from-lead',headers=h,json={'lead_id':lead,'title':'App build','scope':['iOS','Android']}); assert p.status_code==200; a=c.post('/api/approvals',headers=h,json={'action':'publish_proposal','entity_type':'proposals','entity_id':p.json()['id']}).json(); assert c.post(f"/api/approvals/{a['id']}/approve",headers=h).status_code==200
def test_growth_modules():
 h=login(); assert c.post('/api/growth/campaigns',headers=h,json={'name':'EU launch','market':'Europe','channel':'SEO','goal':'lead generation'}).status_code==200; assert c.post('/api/growth/partners',headers=h,json={'name':'Partner','email':'p@example.com'}).status_code==200; assert c.post('/api/growth/content',headers=h,json={'market':'Europe','language':'en','topic':'AI automation'}).status_code==200; assert c.post('/api/marketplace',headers=h,json={'name':'AI Business Audit','category':'AI','description':'Business audit'}).status_code==200
def test_idempotency():
 h=login(); key='same-key-v5'; a=c.post('/api/customers',headers={**h,'Idempotency-Key':key},json={'data':{'name':'Same'}}); b=c.post('/api/customers',headers={**h,'Idempotency-Key':key},json={'data':{'name':'Different'}}); assert a.status_code==b.status_code==200; assert a.json()['id']==b.json()['id']


def test_entrepreneurship_feasibility_paid_service():
 h=login(); r=c.post('/api/entrepreneurship/feasibility',headers=h,json={'project_name':'Digital Startup','country':'NL','industry':'Technology','description':'A subscription software business for small companies','investment':50000,'currency':'EUR','horizon_years':5,'monthly_sales':12000,'monthly_costs':7000,'target_customer':'SMEs'}); assert r.status_code==200; d=r.json(); assert d['paid_service'] is True; assert d['financial_model']['monthly_profit']==5000; assert d['financial_model']['break_even_months']==10.0

def test_agent_product_lifecycle():
 h=login(); a=c.post('/api/agent-builder/builds',headers=h,json={'name':'AI Sales Employee','role':'sales','purpose':'Qualify leads and support sales conversations','channels':['website'],'languages':['ar','en']}); assert a.status_code==200; aid=a.json()['id']
 r=c.post(f'/api/agent-builder/builds/{aid}/configure',headers=h,json={'instructions':'Be helpful, qualify leads, never make binding commitments.','knowledge':['products','pricing'],'tools':['CRM']}); assert r.status_code==200 and r.json()['status']=='configured'
 t=c.post(f'/api/agent-builder/builds/{aid}/test',headers=h,json={'message':'I need help choosing a product'}); assert t.status_code==200 and t.json()['status']=='passed'
 l=c.post(f'/api/agent-builder/builds/{aid}/launch',headers=h,json={'approval_confirmed':True}); assert l.status_code==200 and l.json()['status']=='active'

def test_sales_employee_operations():
    h=login()
    a=c.post('/api/agent-builder/builds',headers=h,json={'name':'Sales Ops AI','role':'sales','purpose':'Qualify leads and support sales conversations','channels':['website'],'languages':['ar','en']}); assert a.status_code==200; aid=a.json()['id']
    k=c.post(f'/api/sales-agent/{aid}/knowledge',headers=h,json={'category':'products','title':'Website packages','content':'Approved package descriptions and scope.'}); assert k.status_code==200 and k.json()['status']=='pending_review'
    m=c.post(f'/api/sales-agent/{aid}/memory',headers=h,json={'lead_id':1,'summary':'Customer wants a multilingual company website.','stage':'qualified','next_action':'prepare initial proposal'}); assert m.status_code==200
    t=c.post(f'/api/sales-agent/{aid}/tools',headers=h,json={'action_type':'capture_lead','payload':{'source':'website'}}); assert t.status_code==200 and t.json()['status']=='queued'
    p=c.post(f'/api/sales-agent/{aid}/tools',headers=h,json={'action_type':'draft_proposal','payload':{'scope':['website']}}); assert p.status_code==200 and p.json()['human_approval_required'] is True
    e=c.post(f'/api/sales-agent/{aid}/escalation-rules',headers=h,json={'trigger':'Customer asks for a binding discount','action':'Escalate to human sales manager'}); assert e.status_code==200
    ops=c.get(f'/api/sales-agent/{aid}/operations',headers=h).json(); assert ops['knowledge_items']==1 and ops['memory_items']==1 and ops['tool_actions']==2 and ops['escalation_rules']==1

def test_sales_crm_product_integration():
    h=login()
    a=c.post('/api/agent-builder/builds',headers=h,json={'name':'Sales CRM AI','role':'sales','purpose':'Use approved products and CRM context to assist sales','channels':['website'],'languages':['ar','en']}); assert a.status_code==200; aid=a.json()['id']
    prod=c.post('/api/products',headers=h,json={'data':{'name':'Website Pro','category':'web','description':'Business website package','price':1500,'currency':'USD','price_status':'approved','active':True}}); assert prod.status_code==200; pid=prod.json()['id']
    lead=c.post('/api/leads/public',json={'name':'CRM Client','email':'crm@example.com','company':'CRM Co','need':'website'}).json()['lead_id']
    mem=c.post(f'/api/sales-agent/{aid}/memory',headers=h,json={'lead_id':lead,'summary':'Interested in Website Pro','stage':'qualified','next_action':'prepare proposal'}); assert mem.status_code==200
    ctx=c.get(f'/api/sales-agent/{aid}/customer-context/{lead}',headers=h); assert ctx.status_code==200 and ctx.json()['lead']['id']==lead and len(ctx.json()['memories'])==1
    cat=c.get(f'/api/sales-agent/{aid}/catalog',headers=h); assert cat.status_code==200 and any(x['id']==pid for x in cat.json()['products'])
    q=c.post(f'/api/sales-agent/{aid}/quote-preview',headers=h,json={'lead_id':lead,'product_ids':[pid],'discount_percent':0}); assert q.status_code==200 and q.json()['total']==1500 and q.json()['human_approval_required'] is True

def test_sales_conversation_intelligence():
    h=login()
    a=c.post('/api/agent-builder/builds',headers=h,json={'name':'Sales Conversation AI','role':'sales','purpose':'Handle customer sales conversations using CRM and approved catalog','channels':['website'],'languages':['ar','en']})
    assert a.status_code==200; aid=a.json()['id']
    p=c.post('/api/products',headers=h,json={'data':{'name':'AI Website Pro','category':'website','description':'Multilingual business website with AI automation','price':2500,'currency':'USD','price_status':'approved','active':True}})
    assert p.status_code==200
    r=c.post(f'/api/sales-agent/{aid}/conversation',json={'name':'Chat Client','email':'chat@example.com','company':'Chat Co','message':'أريد موقع شركة متعدد اللغات مع AI وأتمتة'})
    assert r.status_code==200; d=r.json(); assert d['lead']['email']=='chat@example.com'; assert d['recommendations'][0]['name']=='AI Website Pro'; assert 'qualify_lead' in d['next_actions']


def test_public_sales_chat():
    cfg=c.get('/api/sales-agent/public/config'); assert cfg.status_code==200; aid=cfg.json()['build_id']
    r=c.post(f'/api/sales-agent/{aid}/conversation',json={'message':'أريد موقع شركة مع الذكاء الاصطناعي','language':'nl'})
    assert r.status_code==200; d=r.json(); assert d['agent_build_id']==aid; assert d['recommendations'] is not None; assert 'خصم' in d['reply']

def test_sales_ai_lead_qualification():
    h=login()
    a=c.post('/api/agent-builder/builds',headers=h,json={'name':'Qualification AI','role':'sales','purpose':'Qualify sales leads','channels':['website'],'languages':['ar','en']})
    assert a.status_code==200; aid=a.json()['id']
    r=c.post(f'/api/sales-agent/{aid}/qualify',json={'name':'Qualified Client','email':'qualified@example.com','company':'Qualified Co','need':'نريد بناء موقع شركة متعدد اللغات مع أتمتة للمتابعة','budget':'5000 USD','timeline':'خلال شهر','decision_role':'owner','language':'nl'})
    assert r.status_code==200
    d=r.json(); assert d['stage']=='high_intent'; assert d['score']>=80; assert d['missing_questions']==[]; assert d['recommended_next']=='prepare_proposal'

def test_owner_only_binding_operations():
    h=login()
    o=c.post('/api/orders',headers=h,json={'data':{'customer_id':1,'items':[{'name':'Website'}],'total':1500}})
    assert o.status_code==200
    od=o.json(); assert od['status']=='draft' and od['execution_locked'] is True and od['approval_owner']=='owner@example.com'
    a=c.post('/api/approvals',headers=h,json={'action':'execute_order','entity_type':'orders','entity_id':od['id'],'reason':'Customer accepted proposal'}); assert a.status_code==200
    assert c.post(f"/api/approvals/{a.json()['id']}/approve",headers=h).status_code==200
    ex=c.post(f"/api/owner/execute/orders/{od['id']}",headers=h); assert ex.status_code==200
    assert ex.json()['status']=='approved' and ex.json()['execution_locked'] is False


def test_standard_sale_can_flow_without_owner_approval():
    h=login()
    r=c.post('/api/orders',headers=h,json={'data':{'standard_package':True,'catalog_price_approved':True,'product':'Website Starter','total':1000}})
    assert r.status_code==200 and r.json()['status']=='confirmed' and r.json()['execution_locked'] is False

def test_exceptional_order_is_owner_locked():
    h=login()
    r=c.post('/api/orders',headers=h,json={'data':{'custom_liability':True,'total':9000}})
    assert r.status_code==200 and r.json()['status']=='draft' and r.json()['execution_locked'] is True and r.json()['human_approval_required'] is True

def test_contract_is_owner_locked():
    h=login()
    r=c.post('/api/contracts',headers=h,json={'data':{'customer':'C','value':5000}})
    assert r.status_code==200 and r.json()['execution_locked'] is True

def test_ai_cannot_withdraw_or_transfer_company_funds():
    h=login()
    assert c.post('/api/finance/withdraw',headers=h,json={'amount':100}).status_code==403
    assert c.post('/api/finance/transfer',headers=h,json={'amount':100}).status_code==403


def test_central_permission_engine_policy():
    h=login()
    r=c.post('/api/permissions/check',headers=h,json={'data':{'action':'standard_sale'}})
    assert r.status_code==200 and r.json()['allowed'] is True and r.json()['mode']=='auto'
    r=c.post('/api/permissions/check',headers=h,json={'data':{'action':'bank_withdrawal'}})
    assert r.status_code==200 and r.json()['allowed'] is True and r.json()['mode']=='owner'
    class Staff: email='staff@example.com'; role='sales'
    staff_bank=permission_decision(Staff(),'bank_withdrawal')
    staff_sale=permission_decision(Staff(),'standard_sale')
    assert staff_bank['allowed'] is False and staff_bank['mode']=='owner'
    assert staff_sale['allowed'] is True and staff_sale['mode']=='auto'
    p=c.get('/api/permissions/policy',headers=h)
    assert p.status_code==200 and 'bank_transfer' in p.json()['rules'] and 'standard_sale' in p.json()['rules']

def test_owner_only_exceptional_discount():
    h=login()
    r=c.post('/api/orders',headers=h,json={'data':{'standard_package':True,'catalog_price_approved':True,'exceptional_discount':True,'total':700}})
    assert r.status_code==200 and r.json()['execution_locked'] is True and r.json()['human_approval_required'] is True


def test_smart_proposal_standard_and_exceptional():
    h=login()
    prod=c.post('/api/products',headers=h,json={'data':{'name':'Starter Website','category':'website','description':'Approved website package','price':1000,'currency':'USD','price_status':'approved','active':True}}); assert prod.status_code==200
    pid=prod.json()['id']
    lead=c.post('/api/leads/public',json={'name':'Proposal Client','email':'proposal@example.com','need':'website'}).json()['lead_id']
    r=c.post('/api/proposals/smart',headers=h,json={'lead_id':lead,'product_ids':[pid]}); assert r.status_code==200
    d=r.json(); assert d['total']==1000 and d['proposal_type']=='standard' and d['execution_locked'] is False and d['human_approval_required'] is False
    r=c.post('/api/proposals/smart',headers=h,json={'lead_id':lead,'product_ids':[pid],'discount_percent':10}); assert r.status_code==200
    d=r.json(); assert d['total']==900 and d['proposal_type']=='exceptional' and d['execution_locked'] is True and d['human_approval_required'] is True

def test_commercial_lifecycle_standard_proposal_to_order():
    h=login()
    prod=c.post('/api/products',headers=h,json={'data':{'name':'Lifecycle Website','category':'website','description':'Approved package','price':1200,'currency':'USD','price_status':'approved','active':True}}); assert prod.status_code==200
    pid=prod.json()['id']
    lead=c.post('/api/leads/public',json={'name':'Lifecycle Client','email':'life@example.com','need':'website'}).json()['lead_id']
    p=c.post('/api/proposals/smart',headers=h,json={'lead_id':lead,'product_ids':[pid]}); assert p.status_code==200; proposal_id=p.json()['id']
    a=c.post(f'/api/proposals/{proposal_id}/accept',headers=h,json={'proposal_id':proposal_id,'customer_note':'موافق'}); assert a.status_code==200 and a.json()['status']=='accepted_by_customer'
    o=c.post(f'/api/proposals/{proposal_id}/order',headers=h,json={'proposal_id':proposal_id}); assert o.status_code==200 and o.json()['status']=='confirmed' and o.json()['execution_locked'] is False
    d=c.post(f"/api/orders/{o.json()['id']}/delivery",headers=h,json={'order_id':o.json()['id'],'status':'in_progress'}); assert d.status_code==200
    af=c.post(f"/api/orders/{o.json()['id']}/after-sales",headers=h,json={'order_id':o.json()['id'],'kind':'check_in'}); assert af.status_code==200
    lc=c.get(f'/api/commercial/lifecycle/{proposal_id}',headers=h); assert lc.status_code==200 and lc.json()['order']['id']==o.json()['id'] and len(lc.json()['after_sales'])==1


def test_proposal_followup_is_recorded():
    h=login()
    lead=c.post('/api/leads/public',json={'name':'Follow Client','email':'follow@example.com','need':'marketing'}).json()['lead_id']
    p=c.post('/api/proposals/from-lead',headers=h,json={'lead_id':lead,'title':'Follow proposal','scope':['marketing']}); assert p.status_code==200
    f=c.post(f"/api/proposals/{p.json()['id']}/followups",headers=h,json={'proposal_id':p.json()['id'],'channel':'email','message':'متابعة'}); assert f.status_code==200 and f.json()['status']=='scheduled'


def test_exceptional_proposal_cannot_auto_convert_without_owner_gate():
    h=login()
    prod=c.post('/api/products',headers=h,json={'data':{'name':'Premium','category':'website','description':'Premium package','price':3000,'currency':'USD','price_status':'approved','active':True}}); assert prod.status_code==200
    lead=c.post('/api/leads/public',json={'name':'Risk Client','email':'risk@example.com','need':'website'}).json()['lead_id']
    p=c.post('/api/proposals/smart',headers=h,json={'lead_id':lead,'product_ids':[prod.json()['id']],'discount_percent':10}); assert p.status_code==200
    pid=p.json()['id']; c.post(f'/api/proposals/{pid}/accept',headers=h,json={'proposal_id':pid})
    o=c.post(f'/api/proposals/{pid}/order',headers=h,json={'proposal_id':pid}); assert o.status_code==200 and o.json()['execution_locked'] is True and o.json()['human_approval_required'] is True
    blocked=c.post(f"/api/orders/{o.json()['id']}/delivery",headers=h,json={'order_id':o.json()['id'],'status':'in_progress'}); assert blocked.status_code==403

def test_core_operations_records_and_payment_boundary():
    client=c; admin_headers=login()
    r=client.post('/api/employees',json={'data':{'name':'Core Employee','role':'operations'}} ,headers=admin_headers); assert r.status_code==200
    r=client.post('/api/departments',json={'data':{'name':'Operations'}} ,headers=admin_headers); assert r.status_code==200
    r=client.post('/api/finance/payments',json={'amount':250,'currency':'USD','method':'gateway'},headers=admin_headers); assert r.status_code==200; assert r.json()['status']=='received'
    r=client.post('/api/finance/withdraw',json={'amount':100},headers=admin_headers); assert r.status_code in (401,403)

def test_core_summary_includes_operational_entities():
    client=c; admin_headers=login()
    r=client.get('/api/summary',headers=admin_headers); assert r.status_code==200
    data=r.json()
    for k in ['employees','departments','payments','expenses','notifications','reports','settings','file_records']:
        assert k in data

def test_core_governance_update_delete_and_search():
    h=login()
    r=c.post('/api/customers',headers=h,json={'data':{'name':'Governance Customer','country':'Syria'}}); assert r.status_code==200
    cid=r.json()['id']
    r=c.patch(f'/api/customers/{cid}',headers=h,json={'data':{'status':'active'}}); assert r.status_code==200 and r.json()['status']=='active'
    r=c.get('/api/search?q=Governance',headers=h); assert r.status_code==200 and any(x['id']==cid for x in r.json())
    r=c.delete(f'/api/customers/{cid}',headers=h); assert r.status_code==200

def test_protected_order_cannot_be_unlocked_by_admin_update():
    h=login()
    lead=c.post('/api/leads/public',json={'name':'Locked Buyer','email':'lockedbuyer2@example.com','need':'protected order test'}).json()['lead_id']
    prod=c.post('/api/products',headers=h,json={'data':{'name':'Protected Product','price':500,'currency':'USD','active':True,'approved':True,'price_status':'approved'}}).json()['id']
    p=c.post('/api/proposals/smart',headers=h,json={'lead_id':lead,'product_ids':[prod],'discount_percent':10}).json()['id']
    c.post(f'/api/proposals/{p}/accept',headers=h,json={'proposal_id':p})
    o=c.post(f'/api/proposals/{p}/order',headers=h,json={'proposal_id':p}).json()['id']
    r=c.patch(f'/api/orders/{o}',headers=h,json={'data':{'execution_locked':False,'status':'confirmed'}}); assert r.status_code==403

def test_executive_dashboard_and_task_assignment():
    h=login()
    r=c.get('/api/dashboard/executive',headers=h); assert r.status_code==200; assert 'lead_pipeline' in r.json(); assert 'recent_activity' in r.json()
    t=c.post('/api/tasks',headers=h,json={'data':{'title':'Assign me'}}).json()['id']
    r=c.post(f'/api/tasks/{t}/assign',headers=h,json={'data':{'assignee':'sales-ai','department':'sales'}}); assert r.status_code==200 and r.json()['assignee']=='sales-ai'

def test_v8_operational_workflow_customer360_notifications_and_report():
    h=login()
    cust=c.post('/api/customers',headers=h,json={'data':{'name':'V8 Client','email':'v8client@example.com'}}).json()['id']
    c.post('/api/tasks',headers=h,json={'data':{'title':'V8 task','customer_id':cust}})
    wf=c.post('/api/workflows',headers=h,json={'name':'Customer delivery','entity_type':'customers','entity_id':cust,'steps':['prepare','deliver']}); assert wf.status_code==200
    wid=wf.json()['id']
    adv=c.post(f'/api/workflows/{wid}/advance',headers=h,json={'status':'in_progress','note':'started'}); assert adv.status_code==200 and adv.json()['current_step']==1
    n=c.post('/api/notifications',headers=h,json={'data':{'recipient':'owner@example.com','message':'V8 test'}}); assert n.status_code==200
    nid=n.json()['id']
    r=c.patch(f'/api/notifications/{nid}',headers=h,json={'data':{'read':True}}); assert r.status_code==200 and r.json()['read'] is True
    c360=c.get(f'/api/customers/{cust}/360',headers=h); assert c360.status_code==200 and c360.json()['customer']['name']=='V8 Client'
    rep=c.post('/api/reports/operational',headers=h,json={'data':{'scope':'core'}}); assert rep.status_code==200 and rep.json()['report_type']=='operational'

def test_v8_core_completion_audit():
    h=login()
    r=c.get('/api/core/completion-audit',headers=h); assert r.status_code==200
    d=r.json(); assert d['core_build_complete'] is True
    assert '/api/customers/{customer_id}/360' in d['verified_capabilities']
    assert 'domain' in d['launch_deferred']

def test_v8_1_voice_avatar_department_and_layan_pipeline():
    h=login()
    arch=c.get('/api/voice-avatar/architecture',headers=h); assert arch.status_code==200
    d=arch.json(); assert d['ownership']=='company_ai'; assert 'text_to_speech' in d['layers']; assert d['models']['tts']=='company-ai-voice-v1' and d['language_policy']=='universal' and d['auto_language_detection'] is True
    voices=c.get('/api/voice-avatar/voice-profiles',headers=h); assert voices.status_code==200 and any(v.get('slug')=='layan-universal' for v in voices.json())
    avatars=c.get('/api/voice-avatar/avatar-profiles',headers=h); assert avatars.status_code==200
    layan=next(v for v in avatars.json() if v.get('slug')=='layan')
    session=c.post('/api/voice-avatar/sessions',headers=h,json={'avatar_id':layan['id'],'language':'nl','channel':'website','mode':'duplex'}); assert session.status_code==200
    assert session.json()['engine']=='company-ai-native' and session.json()['pipeline'][0]=='listen'
    job=c.post('/api/voice-avatar/jobs',headers=h,json={'avatar_id':layan['id'],'job_type':'lip_sync','text':'Hallo, ik ben Layan'}); assert job.status_code==200
    assert job.json()['external_provider_required'] is False and job.json()['status']=='queued'
    audit=c.get('/api/core/completion-audit',headers=h).json(); assert 'voice_profiles' in audit['implemented_areas']; assert '/api/voice-avatar/architecture' in audit['verified_capabilities']

def test_v8_3_central_ai_public_intake_routes_and_creates_plan():
    r=c.post('/api/central-ai/intake',json={'message':'أريد إنشاء موقع احترافي لشركتي','language':'ar','channel':'website'})
    assert r.status_code==200
    d=r.json(); assert d['classification']=='web_design'; assert d['department']=='web_design'
    assert d['human_approval_required'] is False
    h=login(); plans=c.get('/api/central-ai/plans',headers=h); assert plans.status_code==200
    assert any(p['id']==d['plan_id'] and p['task_id']==d['task_id'] for p in plans.json())


def test_v8_3_central_ai_protected_intent_hits_owner_gate():
    r=c.post('/api/central-ai/intake',json={'message':'أريد تحويل أموال الشركة إلى حساب مورد','language':'ar','channel':'website'})
    assert r.status_code==200
    d=r.json(); assert d['classification']=='finance'; assert d['human_approval_required'] is True
    h=login(); r=c.post(f"/api/central-ai/plans/{d['plan_id']}/advance",headers=h)
    assert r.status_code==200 and r.json()['status']=='blocked'


def test_v8_3_orchestrator_alias_uses_central_ai():
    h=login(); r=c.post('/api/orchestrator/plan',headers=h,json={'request':'I need marketing for my new website','language':'en'})
    assert r.status_code==200
    d=r.json(); assert d['plan']['classification']=='marketing'; assert d['task']['agent']=='marketing'; assert d['decision']['agent']=='central'


def test_v8_3_completion_audit_includes_central_ai():
    h=login(); r=c.get('/api/core/completion-audit',headers=h); assert r.status_code==200
    d=r.json(); assert d['version']=='8.5.1-security-test'; assert 'central_plans' in d['implemented_areas']; assert '/api/central-ai/intake' in d['verified_capabilities']

def test_v8_5_public_layan_real_session_bridge():
    c=TestClient(app)
    r=c.post('/api/voice-avatar/public-session'); assert r.status_code==200
    d=r.json(); assert d['public'] is True; assert d['engine']=='company-ai-native'; assert d['avatar_id']
    r=c.post('/api/central-ai/public-respond',json={'message':'أريد تصميم موقع لشركتي','language':'ar','channel':'website'})
    assert r.status_code==200
    d=r.json(); assert d['classification']=='web_design'; assert d['reply']; assert d['status']=='active_conversation'


def test_security_headers_and_health():
    r=c.get('/healthz'); assert r.status_code==200
    assert r.headers['x-content-type-options']=='nosniff'
    assert r.headers['x-frame-options']=='DENY'
    assert 'default-src' in r.headers['content-security-policy']

def test_public_admin_page_not_exposed():
    r=c.get('/admin.html'); assert r.status_code==404

def test_public_rate_limit_and_protected_routes():
    for _ in range(31):
        r=c.post('/api/voice-avatar/public-session')
    assert r.status_code==429
    assert c.post('/api/finance/withdraw',json={'amount':1,'currency':'USD'}).status_code in (401,403,422)
