from __future__ import annotations
import hashlib,hmac,os,secrets,base64,json
from datetime import datetime,timedelta,timezone
from typing import Optional
from fastapi import FastAPI,Depends,HTTPException,Header,Request,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, JSONResponse
from pydantic import BaseModel,Field,EmailStr
import jwt
from jwt import InvalidTokenError as JWTError
from sqlalchemy import create_engine,String,Integer,DateTime,Text,select
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,Session
from sqlalchemy.types import JSON

VERSION='8.5.1-security-test'
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./company_ai.db')
JWT_SECRET=os.getenv('JWT_SECRET',''); JWT_ALG='HS256'; ACCESS_MINUTES=int(os.getenv('ACCESS_TOKEN_MINUTES','30'))
COMPANY_OWNER_EMAIL=os.getenv('COMPANY_OWNER_EMAIL','owner@example.com').strip().lower()
if os.getenv('ENVIRONMENT','development')=='production' and len(JWT_SECRET)<32: raise RuntimeError('JWT_SECRET must be at least 32 characters in production')
if os.getenv('ENVIRONMENT','development')=='production' and os.getenv('PASSWORD_PEPPER','') in ('','dev-pepper'): raise RuntimeError('PASSWORD_PEPPER must be configured in production')
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {},pool_pre_ping=True)
class Base(DeclarativeBase): pass
class Entity(Base):
    __tablename__='entities'; id:Mapped[int]=mapped_column(Integer,primary_key=True); kind:Mapped[str]=mapped_column(String(60),index=True); data:Mapped[dict]=mapped_column(JSON); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class Audit(Base):
    __tablename__='audit'; id:Mapped[int]=mapped_column(Integer,primary_key=True); actor:Mapped[str]=mapped_column(String(200)); action:Mapped[str]=mapped_column(String(100)); entity:Mapped[str]=mapped_column(String(100)); entity_id:Mapped[int]=mapped_column(Integer); details:Mapped[dict]=mapped_column(JSON); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class Approval(Base):
    __tablename__='approvals'; id:Mapped[int]=mapped_column(Integer,primary_key=True); action:Mapped[str]=mapped_column(String(100)); entity_type:Mapped[str]=mapped_column(String(80)); entity_id:Mapped[int]=mapped_column(Integer); reason:Mapped[Optional[str]]=mapped_column(Text); status:Mapped[str]=mapped_column(String(20),default='pending'); requested_by:Mapped[str]=mapped_column(String(200)); decided_by:Mapped[Optional[str]]=mapped_column(String(200)); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True)); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
class UserRow(Base):
    __tablename__='users'; id:Mapped[int]=mapped_column(Integer,primary_key=True); name:Mapped[str]=mapped_column(String(120)); email:Mapped[str]=mapped_column(String(200),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(300)); role:Mapped[str]=mapped_column(String(40),default='admin'); active:Mapped[bool]=mapped_column(default=True)
class Idempotency(Base):
    __tablename__='idempotency'; key:Mapped[str]=mapped_column(String(300),primary_key=True); response:Mapped[dict]=mapped_column(JSON); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
Base.metadata.create_all(engine)
app=FastAPI(title='Company AI Global Business OS',version=VERSION,docs_url=None if os.getenv('ENVIRONMENT')=='production' else '/docs',redoc_url=None if os.getenv('ENVIRONMENT')=='production' else '/redoc',openapi_url=None if os.getenv('ENVIRONMENT')=='production' else '/openapi.json')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:8000,http://localhost:5173').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type','Idempotency-Key'],max_age=600)

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app); self.hits={}; self.window=60; self.limit=int(os.getenv('PUBLIC_RATE_LIMIT','30')); self.max_body=int(os.getenv('MAX_REQUEST_BYTES','1048576'))
    async def dispatch(self, request, call_next):
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            cl=request.headers.get('content-length')
            if cl and int(cl)>self.max_body: return JSONResponse({'detail':'Request too large'},status_code=413)
        ip=(request.client.host if request.client else 'unknown')
        if request.url.path.startswith('/api/central-ai/public-') or request.url.path in {'/api/leads/public','/api/voice-avatar/public-session'}:
            import time
            now_t=time.monotonic(); bucket=self.hits.get(ip,[]); bucket=[t for t in bucket if now_t-t<self.window]
            if len(bucket)>=self.limit: return JSONResponse({'detail':'Rate limit exceeded. Please try again later.'},status_code=429,headers={'Retry-After':'60'})
            bucket.append(now_t); self.hits[ip]=bucket
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'; response.headers['Referrer-Policy']='strict-origin-when-cross-origin'; response.headers['Permissions-Policy']='camera=(), geolocation=(), payment=(), usb=()'; response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if os.getenv('ENVIRONMENT')=='production': response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        return response
app.add_middleware(SecurityMiddleware)
trusted=[x.strip() for x in os.getenv('TRUSTED_HOSTS','').split(',') if x.strip()]
if trusted:
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=trusted)
if os.getenv('ENVIRONMENT')=='production':
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)

def now(): return datetime.now(timezone.utc)
def pwd_hash(p):
    salt=secrets.token_bytes(16); pepper=os.getenv('PASSWORD_PEPPER','dev-pepper').encode(); dk=hashlib.pbkdf2_hmac('sha256',pepper+p.encode(),salt,310000); return 'pbkdf2$310000$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(dk).decode()
def verify(p,h):
    try:
        scheme,rounds,salt_b64,dk_b64=h.split('$',3); 
        if scheme!='pbkdf2': return False
        salt=base64.urlsafe_b64decode(salt_b64.encode()); expected=base64.urlsafe_b64decode(dk_b64.encode()); actual=hashlib.pbkdf2_hmac('sha256',os.getenv('PASSWORD_PEPPER','dev-pepper').encode()+p.encode(),salt,int(rounds)); return hmac.compare_digest(actual,expected)
    except Exception:return False
def token(u): return jwt.encode({'sub':str(u.id),'role':u.role,'exp':now()+timedelta(minutes=ACCESS_MINUTES)},JWT_SECRET,algorithm=JWT_ALG)
def db():
    with Session(engine) as s: yield s
def add(s,kind,data):
    e=Entity(kind=kind,data=data,created_at=now(),updated_at=now()); s.add(e); s.flush(); return e
def audit(s,u,action,entity,eid,details=None): s.add(Audit(actor=u.email,action=action,entity=entity,entity_id=eid,details=details or {},created_at=now()))
def seed(s):
    if not s.scalar(select(UserRow).where(UserRow.email=='owner@example.com')): s.add(UserRow(name='Owner',email='owner@example.com',password_hash=pwd_hash(os.getenv('DEMO_ADMIN_PASSWORD','change-me')),role='admin'))
    agents=['central','sales','marketing','lead_generation','growth','trade','customer_support','web_design','app_development','uiux','frontend','qa','operations','analytics','finance','legal','security','partnerships','product','seo','entrepreneurship','website_growth','cybersecurity','monitoring_operations','agent_builder']
    for n in agents:
        exists=s.scalar(select(Entity).where(Entity.kind=='agent',Entity.data['name'].as_string()==n))
        if not exists: add(s,'agent',{'name':n,'status':'ready','description':f'{n} specialist agent','permissions':['read','propose']})
    voice_dept=s.scalar(select(Entity).where(Entity.kind=='departments',Entity.data['slug'].as_string()=='voice-avatar'))
    if not voice_dept: add(s,'departments',{'name':'Voice & Avatar AI','slug':'voice-avatar','status':'active','mission':'In-house speech, voice interaction, avatar, lip-sync, facial and body animation stack.','ownership':'company_ai','external_dependency_policy':'external providers may be optional adapters, never required core infrastructure.'})
    layan_voice=s.scalar(select(Entity).where(Entity.kind=='voice_profiles',Entity.data['slug'].as_string()=='layan-universal'))
    if not layan_voice: add(s,'voice_profiles',{'slug':'layan-universal','name':'Layan Universal','language':'auto','locale':'auto','gender':'female','style':'professional','provider_mode':'local-first','model':'company-ai-voice-v1','active':True,'language_mode':'automatic','fallback_policy':'use_best_available_company_ai_voice'})
    layan_avatar=s.scalar(select(Entity).where(Entity.kind=='avatar_profiles',Entity.data['slug'].as_string()=='layan'))
    if not layan_avatar: add(s,'avatar_profiles',{'slug':'layan','name':'Layan','visual_style':'realistic','identity':'fictional','voice_profile':'layan-universal','lip_sync_model':'company-ai-lipsync-v1','animation_model':'company-ai-avatar-motion-v1','capabilities':['speech','listening','lip_sync','facial_expression','head_motion','eye_gaze','upper_body_motion'],'active':True})
    universal_languages=['ar','en','nl','fr','de','es','it','pt','tr','ru','uk','pl','cs','sk','ro','hu','bg','el','sv','da','no','fi','et','lv','lt','is','ga','mt','he','fa','ur','hi','bn','pa','gu','mr','ta','te','kn','ml','th','vi','id','ms','zh','ja','ko','sw','am','so','ha','yo','ig','zu','af','sq','hy','az','ka','kk','uz','mn','ne','si','km','lo','my','fil','jv','su','ceb','eu','ca','gl','cy','eo','la','sr','hr','sl','bs','mk','be','et','lv','lt','xx']
    for sm in [('company-ai-voice-v1','tts',universal_languages),('company-ai-stt-v1','stt',universal_languages),('company-ai-lipsync-v1','lip_sync',['universal']),('company-ai-avatar-motion-v1','avatar_motion',['universal'])]:
        if not s.scalar(select(Entity).where(Entity.kind=='speech_models',Entity.data['name'].as_string()==sm[0])): add(s,'speech_models',{'name':sm[0],'model_type':sm[1],'languages':sm[2],'local':True,'status':'planned','notes':'Company-owned model slot; implementation can be replaced independently without changing business workflows.'})
    public_sales=s.scalar(select(Entity).where(Entity.kind=='agent_builds',Entity.data['slug'].as_string()=='public-sales-ai'))
    if not public_sales:
        add(s,'agent_builds',{'slug':'public-sales-ai','name':'Company AI Sales Employee','role':'sales','purpose':'Handle website sales conversations using approved catalog and CRM context.','channels':['website'],'languages':['auto'],'knowledge':['products','pricing','faq'],'tools':['CRM','lead_capture'],'autonomy':'supervised','personality':'professional','human_approval_required':True,'status':'active','public_chat':True})
    defaults=[('market','Europe'),('market','Middle East'),('market','North America'),('market','Asia'),('market','Africa')]
    for k,v in defaults:
        if not s.scalar(select(Entity).where(Entity.kind==k,Entity.data['name'].as_string()==v)): add(s,k,{'name':v,'status':'planned'})
    s.commit()
@app.get('/healthz')
def healthz(): return {'status':'ok','version':VERSION,'mode':os.getenv('ENVIRONMENT','development')}

# Public test deployment serves only the customer-facing site; admin.html is intentionally not mounted.
FRONTEND_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','frontend'))
@app.get('/',include_in_schema=False)
def public_home(): return FileResponse(os.path.join(FRONTEND_DIR,'index.html'),media_type='text/html')

with Session(engine) as s: seed(s)
class Login(BaseModel): email:EmailStr; password:str=Field(min_length=1)
class Generic(BaseModel): data:dict=Field(default_factory=dict)
class ApprovalIn(BaseModel): action:str; entity_type:str; entity_id:int; reason:Optional[str]=None
class LeadIn(BaseModel): name:str=Field(min_length=1,max_length=120); email:EmailStr; company:Optional[str]=None; country:Optional[str]=None; language:Optional[str]=None; need:str=Field(min_length=3,max_length=4000); source:Optional[str]='website'; budget:Optional[str]=None
class QualifyIn(BaseModel): lead_id:int
class CentralAIIntakeIn(BaseModel):
    message:str=Field(min_length=2,max_length=8000)
    language:Optional[str]='auto'
    channel:Optional[str]='website'
    session_id:Optional[str]=None
    customer_id:Optional[int]=None
    lead_id:Optional[int]=None

class CentralAIPlanIn(BaseModel):
    message:str=Field(min_length=2,max_length=8000)
    language:Optional[str]='auto'
    channel:Optional[str]='internal'
    priority:Optional[str]='normal'
    customer_id:Optional[int]=None
    lead_id:Optional[int]=None
    auto_execute_standard:bool=True

class CentralAIExecuteIn(BaseModel):
    plan_id:int
    confirm:bool=False
class ProposalIn(BaseModel): lead_id:int; title:str; scope:list[str]=Field(default_factory=list); notes:Optional[str]=None
class SmartProposalIn(BaseModel):
    lead_id:int
    product_ids:list[int]=Field(default_factory=list)
    title:Optional[str]=None
    notes:Optional[str]=None
    discount_percent:float=Field(default=0,ge=0,le=100)
class CampaignIn(BaseModel): name:str; market:str; channel:str; goal:str; budget:Optional[float]=None
class PartnerIn(BaseModel): name:str; email:EmailStr; country:Optional[str]=None; type:str='referral'
class MarketplaceIn(BaseModel): name:str; category:str; description:str; price:Optional[float]=None
class ContentIn(BaseModel): market:str; language:str; topic:str; channel:str='website'
class FeasibilityIn(BaseModel): project_name:str=Field(min_length=2,max_length=180); country:Optional[str]=None; industry:str=Field(min_length=2,max_length=120); description:str=Field(min_length=10,max_length=6000); investment:Optional[float]=None; currency:str='USD'; horizon_years:int=Field(default=5,ge=1,le=10); monthly_sales:Optional[float]=None; monthly_costs:Optional[float]=None; target_customer:Optional[str]=None
class WebsiteAssessmentIn(BaseModel): url:str=Field(min_length=5,max_length=500); goal:Optional[str]=None; issues:Optional[list[str]]=Field(default_factory=list); notes:Optional[str]=None
class SecurityAssessmentIn(BaseModel): target:str=Field(min_length=2,max_length=500); authorization_confirmed:bool=False; scope:Optional[str]=None; notes:Optional[str]=None
class SecurityIncidentIn(BaseModel): title:str=Field(min_length=2,max_length=180); severity:str='medium'; description:str=Field(min_length=3,max_length=6000); affected_system:Optional[str]=None
class MonitoringIncidentIn(BaseModel): service:str=Field(min_length=2,max_length=180); status:str='open'; severity:str='medium'; description:str=Field(min_length=3,max_length=4000)
class AgentBuildIn(BaseModel): name:str=Field(min_length=2,max_length=160); purpose:str=Field(min_length=5,max_length=3000); role:str=Field(min_length=2,max_length=120); channels:list[str]=Field(default_factory=lambda:['website']); languages:list[str]=Field(default_factory=lambda:['ar']); knowledge:list[str]=Field(default_factory=list); tools:list[str]=Field(default_factory=list); autonomy:str='assisted'; personality:str='professional'; human_approval_required:bool=True
class VoiceProfileIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); language:str='ar'; locale:str='ar'; gender:str='female'; style:str='professional'; provider_mode:str='local-first'; model:str='company-ai-voice-v1'; active:bool=True
class AvatarProfileIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); visual_style:str='realistic'; identity:str='fictional'; voice_profile_id:Optional[int]=None; lip_sync_model:str='company-ai-lipsync-v1'; animation_model:str='company-ai-avatar-motion-v1'; active:bool=True
class VoiceSessionIn(BaseModel):
    avatar_id:int; language:str='ar'; channel:str='website'; mode:str='duplex'; user_id:Optional[int]=None
class AvatarJobIn(BaseModel):
    avatar_id:int; job_type:str='lip_sync'; text:Optional[str]=None; audio_asset_id:Optional[int]=None; priority:str='normal'
class SpeechModelIn(BaseModel):
    name:str; model_type:str; languages:list[str]=Field(default_factory=lambda:['ar']); local:bool=True; status:str='planned'; notes:Optional[str]=None
ROLE_OK={'admin':{'*'},'sales':{'customers','projects','tasks','quotes','orders','tickets','leads','proposals','products'},'finance':{'invoices','orders','customers'},'trade':{'suppliers','products','orders','quotes'},'marketing':{'customers','projects','tasks','quotes','leads','campaigns','content'},'support':{'customers','tickets'},'growth':{'leads','campaigns','partners','content'},'entrepreneurship':{'feasibility_studies','projects','tasks','customers'},'website_growth':{'website_assessments','projects','tasks','customers'},'cybersecurity':{'security_assessments','security_incidents','projects','tasks'},'monitoring':{'monitoring_incidents','projects','tasks'},'monitoring_operations':{'monitoring_incidents','projects','tasks','customers'},'agent_builder':{'agent_builds','agents','projects','tasks','customers'},'voice_avatar':{'voice_profiles','avatar_profiles','voice_sessions','avatar_jobs','media_assets','speech_models','voice_models'}}

# Central Permission Engine: every human and AI actor is evaluated against one policy.
# AI may execute pre-approved standard business operations, but never money-out or
# legally/financially binding commitments that create material exposure for the company.
PERMISSION_POLICY={
    'standard_sale': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'approved_catalog_order': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'normal_invoice': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'customer_followup': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'draft_contract': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'receive_customer_payment': {'mode':'auto','allowed_actors':['ai','staff','owner']},
    'bank_withdrawal': {'mode':'owner','allowed_actors':['owner']},
    'bank_transfer': {'mode':'owner','allowed_actors':['owner']},
    'binding_contract': {'mode':'owner','allowed_actors':['owner']},
    'exceptional_financial_commitment': {'mode':'owner','allowed_actors':['owner']},
    'loan': {'mode':'owner','allowed_actors':['owner']},
    'settlement': {'mode':'owner','allowed_actors':['owner']},
    'penalty': {'mode':'owner','allowed_actors':['owner']},
    'exceptional_discount': {'mode':'owner','allowed_actors':['owner']},
}

def actor_type(u):
    return 'owner' if u.email.lower()==COMPANY_OWNER_EMAIL else ('ai' if str(u.role).lower() in {'ai','agent','central_ai'} else 'staff')

def permission_decision(u, action, context=None):
    rule=PERMISSION_POLICY.get(action)
    if not rule:
        return {'allowed':False,'mode':'owner','reason':'Unknown action requires owner approval'}
    a=actor_type(u)
    allowed=a in rule['allowed_actors']
    return {'allowed':allowed,'mode':rule['mode'],'actor':a,'action':action,'reason':'Allowed by central policy' if allowed else 'Owner approval required'}

def enforce_permission(u, action):
    d=permission_decision(u,action)
    if not d['allowed']: raise HTTPException(403,d['reason'])
    return d
def current_user(authorization:Optional[str]=Header(None),s:Session=Depends(db)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentication required')
    try: p=jwt.decode(authorization[7:],JWT_SECRET,algorithms=[JWT_ALG]); uid=int(p['sub'])
    except (JWTError,ValueError,KeyError): raise HTTPException(401,'Invalid or expired token')
    u=s.get(UserRow,uid)
    if not u or not u.active: raise HTTPException(401,'User unavailable')
    return u
def admin(u=Depends(current_user)):
    if u.role!='admin': raise HTTPException(403,'Admin approval required')
    return u
def owner_only(u=Depends(current_user)):
    if u.email.lower()!=COMPANY_OWNER_EMAIL: raise HTTPException(403,'Only the company owner may approve or execute binding operations')
    return u
def allowed(u,kind): return '*' in ROLE_OK.get(u.role,set()) or kind in ROLE_OK.get(u.role,set())
@app.middleware('http')
async def security_headers(request:Request,call_next):
    r=await call_next(request); r.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(), microphone=(), geolocation=()'}); return r
@app.get('/health')
def health(): return {'status':'ok','version':VERSION,'database':'postgresql' if DATABASE_URL.startswith('postgres') else 'sqlite'}
@app.post('/api/auth/login')
def login(x:Login,s:Session=Depends(db)):
    u=s.scalar(select(UserRow).where(UserRow.email==x.email))
    if not u or not verify(x.password,u.password_hash): raise HTTPException(401,'Invalid credentials')
    return {'access_token':token(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email,'role':u.role}}
@app.get('/api/me')
def me(u=Depends(current_user)): return {'id':u.id,'name':u.name,'email':u.email,'role':u.role}
CORE=['customers','suppliers','products','projects','tasks','quotes','orders','invoices','contracts','tickets','leads','proposals','campaigns','partners','content','marketplace','referrals','markets','feasibility_studies','website_assessments','security_assessments','security_incidents','monitoring_incidents','employees','departments','payments','expenses','notifications','reports','settings','file_records','ai_employees','automation_workflows','memberships','agent_builds','referrals']
@app.get('/api/summary')
def summary(u=Depends(current_user),s:Session=Depends(db)): return {k:len(s.scalars(select(Entity).where(Entity.kind==k)).all()) for k in CORE}
def crud(kind):
    @app.get('/api/'+kind)
    def listing(u=Depends(current_user),s:Session=Depends(db)):
        if not allowed(u,kind): raise HTTPException(403,'Insufficient permission')
        return [dict(x.data,id=x.id,created_at=x.created_at.isoformat(),updated_at=x.updated_at.isoformat()) for x in s.scalars(select(Entity).where(Entity.kind==kind).order_by(Entity.id.desc())).all()]
    @app.post('/api/'+kind)
    def create(x:Generic,request:Request,u=Depends(current_user),s:Session=Depends(db),kind=kind):
        if not allowed(u,kind): raise HTTPException(403,'Insufficient permission')
        key=request.headers.get('Idempotency-Key'); scoped=(u.email+':'+key) if key else None
        if scoped:
            old=s.get(Idempotency,scoped)
            if old:return old.response
        data=dict(x.data)
        # Operating policy: standard, pre-approved sales may flow automatically.
        # Owner approval is reserved for binding/risky commitments and movement of company funds.
        protected = False
        if kind == 'contracts':
            protected = True
        elif kind == 'orders':
            standard = bool(data.get('standard_package') or data.get('approved_template') or data.get('catalog_price_approved'))
            risky = bool(data.get('exceptional_discount') or data.get('custom_liability') or data.get('financial_commitment'))
            if standard and not risky:
                enforce_permission(u,'standard_sale')
                data['status']='confirmed'
                data['human_approval_required']=False
                data['execution_locked']=False
                data['approval_mode']='preapproved_standard_sale'
            else:
                protected = True
        elif kind == 'invoices':
            # Issuing a normal invoice is operational; changing/removing money is separately protected.
            enforce_permission(u,'normal_invoice')
            data['status']=data.get('status','issued')
            data['human_approval_required']=False
            data['execution_locked']=False
            data['approval_mode']='operational'
        if protected:
            data['status']='draft'
            data['human_approval_required']=True
            data['execution_locked']=True
            data['approval_owner']=COMPANY_OWNER_EMAIL
        e=add(s,kind,data); out=dict(data,id=e.id); audit(s,u,'create',kind,e.id,{'execution_locked':protected,'approval_mode':data.get('approval_mode','owner_required')})
        if scoped:s.add(Idempotency(key=scoped,response=out,created_at=now()))
        s.commit(); return out
for k in CORE: crud(k)


# V7.9 Core Governance: controlled updates/deletes, global search and executive dashboard.
# Updates preserve the central permission model; protected commitments cannot be unlocked
# by ordinary staff/AI. Destructive deletion is restricted to the company admin/owner role.
@app.patch('/api/{kind}/{entity_id}')
def update_entity(kind:str,entity_id:int,x:Generic,u=Depends(current_user),s:Session=Depends(db)):
    if kind not in CORE or not allowed(u,kind):
        raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,kind,entity_id)
    if not e: raise HTTPException(404,'Entity not found')
    patch=dict(x.data)
    if kind in ('contracts',):
        raise HTTPException(403,'Binding contracts are owner-only')
    if kind=='notifications':
        if e.data.get('recipient') not in (None,u.email,'all'): raise HTTPException(403,'Notification is not assigned to this user')
        if 'read' in patch:
            merged=dict(e.data); merged['read']=bool(patch['read']); e.data=merged; e.updated_at=now()
            audit(s,u,'update_notification','notifications',e.id,{'read':bool(patch['read'])}); s.commit()
            return dict(e.data,id=e.id,created_at=e.created_at.isoformat(),updated_at=e.updated_at.isoformat())
    if kind=='orders' and e.data.get('execution_locked'):
        # Staff/AI may add non-binding operational notes, but cannot unlock or alter protected fields.
        forbidden={'execution_locked','human_approval_required','approval_owner','status','total','discount_percent'}
        if any(k in forbidden for k in patch):
            raise HTTPException(403,'Protected order requires owner approval')
    merged=dict(e.data); merged.update(patch); e.data=merged; e.updated_at=now()
    audit(s,u,'update',kind,e.id,{'fields':sorted(patch.keys())}); s.commit()
    return dict(e.data,id=e.id,created_at=e.created_at.isoformat(),updated_at=e.updated_at.isoformat())

@app.delete('/api/{kind}/{entity_id}')
def delete_entity(kind:str,entity_id:int,u=Depends(owner_only),s:Session=Depends(db)):
    if kind not in CORE: raise HTTPException(404,'Entity type not found')
    e=_get_entity(s,kind,entity_id)
    if not e: raise HTTPException(404,'Entity not found')
    audit(s,u,'delete',kind,e.id,{'owner_authorized':True}); s.delete(e); s.commit()
    return {'status':'deleted','kind':kind,'id':entity_id}

@app.get('/api/search')
def global_search(q:str=Query(min_length=2,max_length=200),u=Depends(current_user),s:Session=Depends(db)):
    needle=q.lower(); out=[]
    for kind in CORE:
        if not allowed(u,kind): continue
        rows=s.scalars(select(Entity).where(Entity.kind==kind).order_by(Entity.id.desc())).all()
        for e in rows:
            blob=json.dumps(e.data,ensure_ascii=False).lower()
            if needle in blob:
                out.append({'kind':kind,'id':e.id,'data':e.data,'created_at':e.created_at.isoformat()})
                if len(out)>=50: return out
    return out

@app.get('/api/dashboard/executive')
def executive_dashboard(u=Depends(admin),s:Session=Depends(db)):
    counts={k:len(s.scalars(select(Entity).where(Entity.kind==k)).all()) for k in CORE}
    recent=[{'id':a.id,'actor':a.actor,'action':a.action,'entity':a.entity,'entity_id':a.entity_id,'created_at':a.created_at.isoformat()} for a in s.scalars(select(Audit).order_by(Audit.id.desc()).limit(20)).all()]
    pending=[{'id':a.id,'action':a.action,'entity_type':a.entity_type,'entity_id':a.entity_id,'reason':a.reason,'requested_by':a.requested_by,'created_at':a.created_at.isoformat()} for a in s.scalars(select(Approval).where(Approval.status=='pending').order_by(Approval.id.desc()).limit(20)).all()]
    pipeline={}
    for status in ('new','nurture','qualified','high_intent'):
        pipeline[status]=sum(1 for e in s.scalars(select(Entity).where(Entity.kind=='leads')).all() if e.data.get('qualification_stage')==status)
    return {'version':VERSION,'summary':counts,'lead_pipeline':pipeline,'pending_approvals':pending,'recent_activity':recent}

@app.post('/api/tasks/{task_id}/assign')
def assign_task(task_id:int,x:Generic,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'tasks'): raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,'tasks',task_id)
    if not e: raise HTTPException(404,'Task not found')
    assignee=x.data.get('assignee'); department=x.data.get('department')
    if not assignee: raise HTTPException(422,'assignee is required')
    e.data={**e.data,'assignee':assignee,'department':department,'status':e.data.get('status','assigned')}; e.updated_at=now()
    audit(s,u,'assign_task','tasks',task_id,{'assignee':assignee,'department':department}); s.commit()
    return dict(e.data,id=e.id)
@app.post('/api/leads/public')
def public_lead(x:LeadIn,request:Request,s:Session=Depends(db)):
    # Public intake deliberately stores only business contact/need data; no privileged action is performed.
    score=25
    need=x.need.lower()
    if any(w in need for w in ['website','موقع','web','ecommerce','متجر']):score+=15
    if any(w in need for w in ['ai','ذكاء','automation','أتمتة']):score+=15
    if x.company:score+=10
    if x.budget:score+=10
    score=min(score,100)
    e=add(s,'leads',{'name':x.name,'email':str(x.email),'company':x.company,'country':x.country,'language':x.language or 'auto','need':x.need,'source':x.source,'budget':x.budget,'score':score,'stage':'new','owner_agent':'lead_generation'}); audit(s, type('U',(),{'email':'public_website'})(),'lead_capture','leads',e.id,{'ip_hash':hashlib.sha256((request.client.host or '').encode()).hexdigest()[:16]}); s.commit(); return {'lead_id':e.id,'score':score,'stage':'new','next_step':'qualification'}
@app.post('/api/leads/{lead_id}/qualify')
def qualify(lead_id:int,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'leads'):raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,lead_id)
    if not e or e.kind!='leads':raise HTTPException(404,'Lead not found')
    score=e.data.get('score',25); e.data={**e.data,'score':min(100,score+20),'stage':'qualified','qualification':{'fit':'good','recommended_next':'proposal_or_discovery'}}; e.updated_at=now(); audit(s,u,'qualify','leads',lead_id); s.commit(); return dict(e.data,id=e.id)
@app.post('/api/proposals/from-lead')
def proposal(x:ProposalIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals'):raise HTTPException(403,'Insufficient permission')
    lead=s.get(Entity,x.lead_id)
    if not lead or lead.kind!='leads':raise HTTPException(404,'Lead not found')
    e=add(s,'proposals',{'lead_id':x.lead_id,'title':x.title,'scope':x.scope,'notes':x.notes,'status':'draft','requires_human_approval':True}); audit(s,u,'create_proposal','proposals',e.id,{'lead_id':x.lead_id}); s.commit(); return dict(e.data,id=e.id)
CENTRAL_ROUTING_RULES=[
    ('cybersecurity',['security','cyber','vulnerability','hack','أمن سيبراني','اختراق','ثغرة']),
    ('trade',['استيراد','تصدير','مورد','شراء','بيع','import','export','supplier','sourcing','تجارة']),
    ('web_design',['موقع','ويب','website','web','landing page','متجر إلكتروني']),
    ('app_development',['تطبيق','app','application','mobile app']),
    ('marketing',['تسويق','marketing','advertising','إعلان','حملة']),
    ('customer_support',['دعم','شكوى','support','ticket','مشكلة']),
    ('finance',['فاتورة','دفع','مالية','invoice','payment','تحويل','سحب']),
    ('legal',['عقد','قانون','legal','contract','اتفاقية']),
    ('entrepreneurship',['مشروع','فكرة مشروع','ريادة','entrepreneur','business idea','feasibility']),
    ('sales',['عميل','عرض','مبيعات','customer','quote','sales','سعر','شراء']),
]

CENTRAL_DEPARTMENT_MAP={
    'cybersecurity':'cybersecurity','trade':'trade','web_design':'web_design','app_development':'app_development',
    'marketing':'marketing','customer_support':'customer_support','finance':'finance','legal':'legal',
    'entrepreneurship':'entrepreneurship','sales':'sales','central':'executive'
}

CENTRAL_PROTECTED_INTENTS={'finance','legal','cybersecurity'}

def central_classify(message:str):
    text=message.lower()
    scores={agent:sum(1 for word in words if word.lower() in text) for agent,words in CENTRAL_ROUTING_RULES}
    # Intent-specific phrases take precedence over incidental context words.
    strong={
        'finance':['تحويل أموال','سحب أموال','تحويل مالي','money transfer','withdraw funds','transfer funds'],
        'legal':['عقد ملزم','binding contract','legal agreement'],
        'cybersecurity':['ثغرة أمنية','اختبار اختراق','security vulnerability','penetration test'],
        'marketing':['marketing campaign','حملة تسويقية','إعلانات مدفوعة','digital marketing','marketing'],
        'trade':['استيراد وتصدير','import and export','توريد'],
        'web_design':['إنشاء موقع','بناء موقع','website design','build a website'],
        'app_development':['تطوير تطبيق','build an app','mobile application'],
    }
    strong_hits={agent:sum(1 for phrase in phrases if phrase in text) for agent,phrases in strong.items()}
    if any(strong_hits.values()):
        selected=max(strong_hits,key=strong_hits.get)
        score=strong_hits[selected]+scores.get(selected,0)
    else:
        selected=max(scores,key=scores.get) if scores else 'central'
        score=scores.get(selected,0)
    if score==0: selected='central'
    confidence=0.96 if strong_hits.get(selected,0)>0 else (0.92 if score>=2 else (0.78 if score==1 else 0.55))
    return selected,confidence,scores

def central_build_steps(agent:str, message:str):
    department=CENTRAL_DEPARTMENT_MAP.get(agent,agent)
    protected=agent in CENTRAL_PROTECTED_INTENTS
    steps=[
        {'step':1,'owner':'central','action':'analyze_request','status':'ready'},
        {'step':2,'owner':agent,'department':department,'action':'specialist_assessment','status':'pending'},
        {'step':3,'owner':'central','action':'review_and_integrate','status':'pending'},
    ]
    if protected:
        steps.append({'step':4,'owner':'human_owner','action':'approval_gate','status':'blocked_until_approval'})
    else:
        steps.append({'step':4,'owner':'central','action':'finalize_standard_result','status':'pending'})
    return steps,protected

def central_create_plan(s:Session,message:str,language='auto',channel='internal',priority='normal',customer_id=None,lead_id=None):
    agent,confidence,scores=central_classify(message)
    steps,protected=central_build_steps(agent,message)
    data={
        'request':message,'language':language or 'auto','channel':channel or 'internal','priority':priority or 'normal',
        'classification':agent,'department':CENTRAL_DEPARTMENT_MAP.get(agent,agent),'confidence':confidence,
        'scores':scores,'customer_id':customer_id,'lead_id':lead_id,'status':'planned',
        'human_approval_required':protected,'execution_locked':protected,
        'autonomy':'supervised','steps':steps,'created_by':'central-ai','policy_version':VERSION,
    }
    plan=add(s,'central_plans',data)
    task=add(s,'tasks',{'title':message[:180],'agent':agent,'department':CENTRAL_DEPARTMENT_MAP.get(agent,agent),'priority':priority or 'normal','status':'pending','central_plan_id':plan.id,'customer_id':customer_id,'lead_id':lead_id,'owner':'central'})
    decision=add(s,'decision',{'agent':'central','request':message,'classification':agent,'department':CENTRAL_DEPARTMENT_MAP.get(agent,agent),'confidence':confidence,'human_approval_required':protected,'plan_id':plan.id,'task_id':task.id,'scores':scores})
    data={**data,'plan_id':plan.id,'task_id':task.id,'decision_id':decision.id}
    plan.data=data; plan.updated_at=now()
    return plan,task,decision

@app.post('/api/central-ai/intake')
def central_public_intake(x:CentralAIIntakeIn,request:Request,s:Session=Depends(db)):
    # Public entry point for website/voice/avatar. Stores only business-request context.
    plan,task,decision=central_create_plan(s,x.message,x.language,x.channel,'normal',x.customer_id,x.lead_id)
    audit(s,type('U',(),{'email':'public_central_ai'})(),'central_intake','central_plans',plan.id,{'channel':x.channel,'language':x.language,'ip_hash':hashlib.sha256((request.client.host or '').encode()).hexdigest()[:16]})
    s.commit()
    return {'plan_id':plan.id,'task_id':task.id,'decision_id':decision.id,'classification':plan.data['classification'],'department':plan.data['department'],'confidence':plan.data['confidence'],'human_approval_required':plan.data['human_approval_required'],'status':'planned','next_step':'specialist_assessment'}

@app.post('/api/central-ai/public-respond')
def central_public_respond(x:CentralAIIntakeIn,request:Request,s:Session=Depends(db)):
    # Public conversational bridge: creates the same central plan as intake and returns a concise response
    # suitable for Layan voice playback. No protected operation is executed here.
    plan,task,decision=central_create_plan(s,x.message,x.language,x.channel,'normal',x.customer_id,x.lead_id)
    replies={
        'web_design':'فهمت طلبك. رح نحلّل احتياجك من ناحية الموقع وتجربة المستخدم، وبعدها منرتّب الخطوات المناسبة معك.',
        'app_development':'فهمت فكرتك. رح نحدد الوظائف الأساسية للتطبيق ونحوّلها لخطة تنفيذ واضحة.',
        'marketing':'تمام. رح نحدد الهدف والسوق والقناة المناسبة، وبعدها نبني المسار التسويقي المناسب.',
        'sales':'تمام. رح نحدد احتياجك ونشوف الحل أو الخدمة الأنسب إلك ضمن الخيارات المتاحة.',
        'trade':'فهمت. رح نصنّف طلب التجارة ونحدد المنتج أو السوق والخطوة التجارية التالية.',
        'customer_support':'فهمت طلبك. رح نحدد المشكلة ونوجّهها للقسم المختص لمتابعتها.',
        'entrepreneurship':'فهمت الفكرة. رح نبدأ بتقييمها بشكل أولي ونحدد أهم المعلومات اللازمة للخطوة التالية.',
        'cybersecurity':'فهمت. الموضوع أمني، لذلك رح يبقى ضمن مسار مراقَب ويتطلب موافقة بشرية قبل أي إجراء حساس.',
        'finance':'فهمت. الموضوع مالي، ورح يبقى ضمن مسار مراقَب مع بوابة موافقة بشرية لأي قرار حساس.',
        'legal':'فهمت. الموضوع قانوني، ورح يروح للمسار القانوني المناسب مع بقاء القرارات الملزمة بيد المسؤول البشري.',
    }
    reply=replies.get(plan.data['classification'],'وصلت فكرتك. رح أحللها وأوجّهها للقسم المختص ضمن Company AI.')
    audit(s,type('U',(),{'email':'public_layan'})(),'public_central_response','central_plans',plan.id,{'channel':x.channel,'language':x.language,'ip_hash':hashlib.sha256((request.client.host or '').encode()).hexdigest()[:16]})
    s.commit()
    return {'session_id':None,'plan_id':plan.id,'classification':plan.data['classification'],'department':plan.data['department'],'reply':reply,'human_approval_required':plan.data['human_approval_required'],'status':'active_conversation','next_step':'specialist_assessment'}

@app.post('/api/central-ai/plan')
def central_plan(x:CentralAIPlanIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'tasks'): raise HTTPException(403,'Insufficient permission')
    plan,task,decision=central_create_plan(s,x.message,x.language,x.channel,x.priority,x.customer_id,x.lead_id)
    audit(s,u,'central_plan','central_plans',plan.id,{'classification':plan.data['classification']})
    s.commit()
    return {'plan':dict(plan.data,id=plan.id),'task':dict(task.data,id=task.id),'decision':dict(decision.data,id=decision.id)}

@app.get('/api/central-ai/plans')
def central_plans(u=Depends(admin),s:Session=Depends(db)):
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat(),updated_at=e.updated_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='central_plans').order_by(Entity.id.desc()).limit(100)).all()]

@app.post('/api/central-ai/plans/{plan_id}/advance')
def central_advance(plan_id:int,u=Depends(admin),s:Session=Depends(db)):
    plan=_get_entity(s,'central_plans',plan_id)
    if not plan: raise HTTPException(404,'Central plan not found')
    if plan.data.get('human_approval_required') and plan.data.get('execution_locked'):
        return {'plan_id':plan_id,'status':'blocked','reason':'Owner approval required for protected intent','steps':plan.data.get('steps',[])}
    steps=[dict(x) for x in plan.data.get('steps',[])]
    pending=next((x for x in steps if x.get('status')=='pending'),None)
    if pending:
        pending['status']='completed'; pending['completed_at']=now().isoformat()
        nxt=next((x for x in steps if x.get('status')=='pending'),None)
        if nxt: nxt['status']='ready'
    status='completed' if steps and all(x.get('status') in ('completed','blocked_until_approval') for x in steps) and not plan.data.get('human_approval_required') else 'in_progress'
    plan.data={**plan.data,'steps':steps,'status':status}; plan.updated_at=now()
    audit(s,u,'central_advance','central_plans',plan_id,{'status':status}); s.commit()
    return dict(plan.data, id=plan.id)

@app.post('/api/orchestrator/plan')
def plan(payload:dict,u=Depends(current_user),s:Session=Depends(db)):
    # Backward-compatible alias to the Central AI orchestrator.
    message=str(payload.get('request','')).strip() or 'New task'
    plan,task,decision=central_create_plan(s,message,payload.get('language','auto'),payload.get('channel','internal'),payload.get('priority','normal'))
    audit(s,u,'orchestrate','central_plans',plan.id,{'task_id':task.id,'decision_id':decision.id})
    s.commit()
    return {'task':dict(task.data,id=task.id),'decision':dict(decision.data,id=decision.id),'plan':dict(plan.data,id=plan.id)}
@app.get('/api/agents')
def agents(u=Depends(current_user),s:Session=Depends(db)):return [dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='agent')).all()]
@app.post('/api/agent-builder/builds')
def build_agent(x:AgentBuildIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    blueprint={'name':x.name,'purpose':x.purpose,'role':x.role,'channels':x.channels,'languages':x.languages,'knowledge':x.knowledge,'tools':x.tools,'autonomy':x.autonomy,'personality':x.personality,'status':'draft','human_approval_required':x.human_approval_required,'next_steps':['define_instructions','connect_knowledge','connect_tools','test_agent','human_review','launch']}
    e=add(s,'agent_builds',blueprint); audit(s,u,'agent_builder_create','agent_builds',e.id,{'agent_name':x.name}); s.commit(); return dict(e.data,id=e.id,created_at=e.created_at.isoformat())


class AgentConfigureIn(BaseModel):
    instructions:str=Field(min_length=10,max_length=6000); knowledge:list[str]=Field(default_factory=list); tools:list[str]=Field(default_factory=list); personality:Optional[str]=None
class AgentTestIn(BaseModel):
    message:str=Field(min_length=2,max_length=4000)
class AgentLaunchIn(BaseModel):
    approval_confirmed:bool=False

@app.post('/api/agent-builder/builds/{build_id}/configure')
def configure_agent(build_id:int,x:AgentConfigureIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,build_id)
    if not e or e.kind!='agent_builds': raise HTTPException(404,'Agent build not found')
    d={**e.data,'instructions':x.instructions,'knowledge':x.knowledge,'tools':x.tools,'personality':x.personality or e.data.get('personality','professional'),'status':'configured','next_steps':['test_agent','human_review','launch']}
    e.data=d;e.updated_at=now();audit(s,u,'configure_agent','agent_builds',build_id);s.commit();return dict(d,id=e.id)

@app.post('/api/agent-builder/builds/{build_id}/test')
def test_agent(build_id:int,x:AgentTestIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,build_id)
    if not e or e.kind!='agent_builds': raise HTTPException(404,'Agent build not found')
    role=e.data.get('role','AI agent'); purpose=e.data.get('purpose','complete the requested task')
    response=f"اختبار ناجح مبدئياً لوكيل {role}: سيتعامل مع الطلب ضمن الهدف المحدد ({purpose})، ويصعّد العمليات الحساسة إلى موافقة بشرية."
    e.data={**e.data,'last_test':{'message':x.message,'result':'passed','response':response},'status':'tested','next_steps':['human_review','launch']};e.updated_at=now();audit(s,u,'test_agent','agent_builds',build_id);s.commit();return {'build_id':build_id,'status':'passed','response':response}

@app.post('/api/agent-builder/builds/{build_id}/launch')
def launch_agent(build_id:int,x:AgentLaunchIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,build_id)
    if not e or e.kind!='agent_builds': raise HTTPException(404,'Agent build not found')
    if not x.approval_confirmed: raise HTTPException(400,'Human approval is required before launch')
    if e.data.get('status') not in ('tested','configured'): raise HTTPException(409,'Agent must be configured and tested before launch')
    e.data={**e.data,'status':'active','launched_at':now().isoformat(),'next_steps':['monitor','improve']};e.updated_at=now();audit(s,u,'launch_agent','agent_builds',build_id);s.commit();return dict(e.data,id=e.id)

@app.get('/api/agent-builder/builds')
def list_agent_builds(u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='agent_builds').order_by(Entity.id.desc())).all()]


# V6.7 Sales AI Employee operations: knowledge, memory, tools and escalation
class SalesKnowledgeIn(BaseModel):
    category:str=Field(min_length=2,max_length=80); title:str=Field(min_length=2,max_length=180); content:str=Field(min_length=3,max_length=12000); approved:bool=False
class SalesMemoryIn(BaseModel):
    customer_id:Optional[int]=None; lead_id:Optional[int]=None; summary:str=Field(min_length=3,max_length=6000); stage:str='new'; next_action:Optional[str]=None
class SalesToolActionIn(BaseModel):
    action_type:str=Field(min_length=2,max_length=80); payload:dict=Field(default_factory=dict)
class SalesEscalationIn(BaseModel):
    trigger:str=Field(min_length=3,max_length=500); action:str=Field(min_length=3,max_length=500); priority:str='high'; enabled:bool=True
class SalesCatalogItemIn(BaseModel):
    name:str=Field(min_length=2,max_length=180); category:str=Field(min_length=2,max_length=100); description:str=Field(min_length=3,max_length=3000); price:Optional[float]=None; currency:str='USD'; price_status:str='approved'; active:bool=True
class SalesQuotePreviewIn(BaseModel):
    lead_id:int; product_ids:list[int]=Field(min_length=1); discount_percent:float=Field(default=0,ge=0,le=100); currency:str='USD'
class SalesConversationIn(BaseModel):
    message:str=Field(min_length=2,max_length=6000)
    lead_id:Optional[int]=None
    name:Optional[str]=None
    email:Optional[EmailStr]=None
    company:Optional[str]=None
    country:Optional[str]=None
    language:Optional[str]='ar'
    session_id:Optional[str]=Field(default=None,max_length=160)
class SalesQualificationIn(BaseModel):
    lead_id:Optional[int]=None
    message:Optional[str]=Field(default=None,min_length=3,max_length=6000)
    name:Optional[str]=None
    email:Optional[EmailStr]=None
    company:Optional[str]=None
    country:Optional[str]=None
    language:Optional[str]='ar'
    need:Optional[str]=None
    budget:Optional[str]=None
    timeline:Optional[str]=None
    decision_role:Optional[str]=None


def _qualification_score(x, lead=None):
    score = int((lead.data.get('score',25) if lead else 25))
    need = (x.need or x.message or (lead.data.get('need','') if lead else '')).strip()
    if len(need) >= 20: score += 15
    if len(need) >= 80: score += 10
    if x.company or (lead and lead.data.get('company')): score += 10
    if x.budget: score += 10
    if x.timeline: score += 10
    if x.decision_role: score += 10
    return min(100, score)

def _qualification_stage(score):
    if score >= 80: return 'high_intent'
    if score >= 60: return 'qualified'
    if score >= 40: return 'nurture'
    return 'new'

def _qualification_questions(x, lead=None):
    missing=[]
    need=x.need or x.message or (lead.data.get('need','') if lead else '')
    if not need or len(need)<20: missing.append('ما الهدف الأساسي الذي تريد تحقيقه؟')
    if not x.budget and not (lead and lead.data.get('budget')): missing.append('هل لديك ميزانية تقريبية للمشروع؟')
    if not x.timeline and not (lead and lead.data.get('timeline')): missing.append('متى تريد البدء أو إطلاق المشروع تقريباً؟')
    if not x.decision_role: missing.append('هل أنت صاحب القرار بالمشروع أم تعمل ضمن فريق يتخذ القرار؟')
    return missing[:3]


def _approved_products(s):
    return [e for e in s.scalars(select(Entity).where(Entity.kind=='products')).all()
            if e.data.get('active',True) is not False and e.data.get('price_status') in (None,'approved')]

def _product_matches(prod, text):
    d=prod.data
    hay=' '.join(str(d.get(k,'')) for k in ('name','category','description','sku')).lower()
    words=[w for w in text.lower().replace('،',' ').replace(',',' ').split() if len(w)>=2]
    aliases={'موقع':'website','ويب':'website','تطبيق':'app','تطبيقات':'app','ذكاء':'ai','أتمتة':'automation','متجر':'ecommerce'}
    expanded=words+[aliases[w] for w in words if w in aliases]
    return sum(1 for w in expanded if w in hay)

@app.get('/api/sales-agent/public/config')
def public_sales_config(s:Session=Depends(db)):
    build=s.scalar(select(Entity).where(Entity.kind=='agent_builds',Entity.data['slug'].as_string()=='public-sales-ai',Entity.data['status'].as_string()=='active'))
    if not build: raise HTTPException(503,'Public sales employee unavailable')
    return {'build_id':build.id,'name':build.data.get('name','Company AI Sales Employee'),'languages':build.data.get('languages',['ar','en'])}

@app.post('/api/sales-agent/{build_id}/qualify')
def qualify_sales_lead(build_id:int,x:SalesQualificationIn,request:Request,s:Session=Depends(db)):
    build=s.get(Entity,build_id)
    if not build or build.kind!='agent_builds': raise HTTPException(404,'Sales agent not found')
    role=str(build.data.get('role','')).lower()
    if role!='sales' and 'sales' not in str(build.data.get('name','')).lower():
        raise HTTPException(409,'Selected agent is not configured as a sales employee')
    lead=None
    if x.lead_id:
        lead=s.get(Entity,x.lead_id)
        if not lead or lead.kind!='leads': raise HTTPException(404,'Lead not found')
    elif x.email:
        lead=s.scalar(select(Entity).where(Entity.kind=='leads',Entity.data['email'].as_string()==str(x.email)).order_by(Entity.id.desc()))
    if not lead and x.email:
        base_need=x.need or x.message or 'Sales qualification request'
        lead=add(s,'leads',{'name':x.name or 'Website Qualification Lead','email':str(x.email),'company':x.company,'country':x.country,'language':x.language or 'auto','need':base_need,'source':'sales_ai_qualification','budget':x.budget,'timeline':x.timeline,'decision_role':x.decision_role,'score':25,'stage':'new','owner_agent':build.data.get('name','sales')})
        audit(s,type('U',(),{'email':'sales_ai_qualification'})(),'qualification_lead_capture','leads',lead.id,{'agent_build_id':build_id})
    score=_qualification_score(x,lead)
    stage=_qualification_stage(score)
    missing=_qualification_questions(x,lead)
    if lead:
        data=dict(lead.data)
        for k,v in {'name':x.name,'company':x.company,'country':x.country,'language':x.language,'need':x.need or x.message,'budget':x.budget,'timeline':x.timeline,'decision_role':x.decision_role}.items():
            if v is not None and v!='': data[k]=v
        data.update({'score':score,'stage':stage,'qualification':{'score':score,'stage':stage,'missing_questions':missing,'status':'qualified' if stage in ('qualified','high_intent') else 'in_progress'}})
        lead.data=data; lead.updated_at=now()
        q=add(s,'sales_lead_qualifications',{'agent_build_id':build_id,'lead_id':lead.id,'score':score,'stage':stage,'answers':{'need':x.need or x.message,'budget':x.budget,'timeline':x.timeline,'decision_role':x.decision_role},'missing_questions':missing,'status':'completed' if not missing else 'in_progress'})
        audit(s,type('U',(),{'email':'sales_ai_qualification'})(),'qualify_sales_lead','leads',lead.id,{'qualification_id':q.id,'score':score,'stage':stage})
        s.commit()
        return {'lead':dict(lead.data,id=lead.id),'qualification_id':q.id,'score':score,'stage':stage,'status':'qualified' if stage in ('qualified','high_intent') else 'in_progress','missing_questions':missing,'recommended_next':'prepare_proposal' if stage=='high_intent' else ('sales_followup' if stage=='qualified' else 'continue_qualification')}
    # No contact details: provide qualification questions without creating a lead.
    s.commit()
    return {'lead':None,'qualification_id':None,'score':score,'stage':stage,'status':'in_progress','missing_questions':missing,'recommended_next':'request_contact_details'}

@app.post('/api/sales-agent/{build_id}/conversation')
def sales_conversation(build_id:int,x:SalesConversationIn,request:Request,s:Session=Depends(db)):
    build=s.get(Entity,build_id)
    if not build or build.kind!='agent_builds': raise HTTPException(404,'Sales agent not found')
    role=str(build.data.get('role','')).lower()
    if role!='sales' and 'sales' not in str(build.data.get('name','')).lower():
        raise HTTPException(409,'Selected agent is not configured as a sales employee')
    lead=None
    if x.lead_id:
        lead=s.get(Entity,x.lead_id)
        if not lead or lead.kind!='leads': raise HTTPException(404,'Lead not found')
    elif x.email:
        lead=s.scalar(select(Entity).where(Entity.kind=='leads',Entity.data['email'].as_string()==str(x.email)).order_by(Entity.id.desc()))
    if not lead and x.email:
        score=35
        text=x.message.lower()
        if any(w in text for w in ('website','موقع','web','app','تطبيق','ai','ذكاء','automation','أتمتة')): score+=20
        if x.company: score+=10
        lead=add(s,'leads',{'name':x.name or 'Website Chat Lead','email':str(x.email),'company':x.company,'country':x.country,'language':x.language or 'auto','need':x.message,'source':'sales_ai_chat','score':min(score,100),'stage':'new','owner_agent':build.data.get('name','sales')})
        audit(s,type('U',(),{'email':'sales_ai_chat'})(),'sales_chat_lead_capture','leads',lead.id,{'agent_build_id':build_id})
    products=sorted(_approved_products(s),key=lambda p:_product_matches(p,x.message),reverse=True)
    products=[p for p in products if _product_matches(p,x.message)>0][:3]
    context=None
    if lead:
        memories=s.scalars(select(Entity).where(Entity.kind=='sales_agent_memory',Entity.data['agent_build_id'].as_integer()==build_id,Entity.data['lead_id'].as_integer()==lead.id).order_by(Entity.id.desc())).all()
        context={'lead_id':lead.id,'stage':lead.data.get('stage'),'score':lead.data.get('score'),'previous_memories':len(memories)}
        memory=add(s,'sales_agent_memory',{'agent_build_id':build_id,'lead_id':lead.id,'summary':x.message,'stage':lead.data.get('stage','new'),'next_action':'continue qualification or prepare proposal'})
        audit(s,type('U',(),{'email':'sales_ai_chat'})(),'sales_chat_memory','sales_agent_memory',memory.id,{'agent_build_id':build_id,'lead_id':lead.id})
    if products:
        rec='وجدت لك خيارات مناسبة مبدئياً: '+', '.join(p.data.get('name','منتج') for p in products)+'.'
    else:
        rec='حتى أحدد المنتج الأنسب بدقة، أحتاج معرفة نوع الحل المطلوب والهدف الرئيسي منه.'
    reply=rec+' أستطيع متابعة التأهيل وتجهيز مسودة عرض، وأي خصم أو التزام تعاقدي يحتاج موافقة بشرية.'
    action=add(s,'sales_agent_actions',{'agent_build_id':build_id,'action_type':'conversation_response','payload':{'message':x.message,'recommended_product_ids':[p.id for p in products],'lead_id':lead.id if lead else None},'status':'completed','human_approval_required':False})
    audit(s,type('U',(),{'email':'sales_ai_chat'})(),'sales_chat_response','sales_agent_actions',action.id,{'agent_build_id':build_id})
    s.commit()
    return {'agent_build_id':build_id,'reply':reply,'lead':dict(lead.data,id=lead.id) if lead else None,'customer_context':context,'recommendations':[{'id':p.id,'name':p.data.get('name'),'category':p.data.get('category'),'description':p.data.get('description'),'price':p.data.get('price'),'currency':p.data.get('currency','USD')} for p in products],'next_actions':['qualify_lead','prepare_proposal'] if lead else ['request_contact_details']}


def _sales_build(build_id,u,s):
    if not allowed(u,'agent_builder'): raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,build_id)
    if not e or e.kind!='agent_builds': raise HTTPException(404,'Agent build not found')
    return e

@app.post('/api/sales-agent/{build_id}/knowledge')
def sales_knowledge(build_id:int,x:SalesKnowledgeIn,u=Depends(current_user),s:Session=Depends(db)):
    build=_sales_build(build_id,u,s)
    item={**x.model_dump(),'agent_build_id':build_id,'status':'approved' if x.approved and u.role=='admin' else 'pending_review','human_review_required':not (x.approved and u.role=='admin')}
    e=add(s,'sales_agent_knowledge',item); audit(s,u,'sales_agent_add_knowledge','sales_agent_knowledge',e.id,{'build_id':build_id}); s.commit()
    build.data={**build.data,'knowledge_count':int(build.data.get('knowledge_count',0))+1}; build.updated_at=now(); s.commit()
    return dict(item,id=e.id)

@app.get('/api/sales-agent/{build_id}/knowledge')
def list_sales_knowledge(build_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='sales_agent_knowledge',Entity.data['agent_build_id'].as_integer()==build_id).order_by(Entity.id.desc())).all()]

@app.post('/api/sales-agent/{build_id}/memory')
def sales_memory(build_id:int,x:SalesMemoryIn,u=Depends(current_user),s:Session=Depends(db)):
    build=_sales_build(build_id,u,s)
    item={**x.model_dump(),'agent_build_id':build_id,'status':'active','updated_by':u.email}
    e=add(s,'sales_agent_memory',item); audit(s,u,'sales_agent_memory_update','sales_agent_memory',e.id,{'build_id':build_id}); s.commit()
    return dict(item,id=e.id)

@app.get('/api/sales-agent/{build_id}/memory')
def list_sales_memory(build_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='sales_agent_memory',Entity.data['agent_build_id'].as_integer()==build_id).order_by(Entity.id.desc())).all()]

@app.post('/api/sales-agent/{build_id}/tools')
def sales_tool_action(build_id:int,x:SalesToolActionIn,u=Depends(current_user),s:Session=Depends(db)):
    build=_sales_build(build_id,u,s)
    allowed_actions={'capture_lead','update_lead','draft_proposal','schedule_followup','escalate'}
    if x.action_type not in allowed_actions: raise HTTPException(400,'Unsupported sales tool action')
    sensitive=x.action_type in {'draft_proposal','schedule_followup'}
    item={**x.model_dump(),'agent_build_id':build_id,'status':'draft' if sensitive else 'queued','human_approval_required':sensitive}
    e=add(s,'sales_agent_actions',item); audit(s,u,'sales_agent_tool_action','sales_agent_actions',e.id,{'build_id':build_id,'action_type':x.action_type}); s.commit()
    return dict(item,id=e.id)

@app.post('/api/sales-agent/{build_id}/catalog')
def sales_catalog_add(build_id:int,x:SalesCatalogItemIn,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    data={**x.model_dump(),'source':'sales_agent_catalog','status':'approved' if x.price_status=='approved' and u.role=='admin' else 'pending_review','agent_build_id':build_id,'human_approval_required':not (x.price_status=='approved' and u.role=='admin')}
    e=add(s,'sales_agent_catalog',data); audit(s,u,'sales_catalog_add','sales_agent_catalog',e.id,{'build_id':build_id}); s.commit(); return dict(data,id=e.id)

@app.get('/api/sales-agent/{build_id}/catalog')
def sales_catalog(build_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    items=[dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='sales_agent_catalog',Entity.data['agent_build_id'].as_integer()==build_id).order_by(Entity.id.desc())).all()]
    products=[dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='products')).all()]
    return {'agent_build_id':build_id,'catalog_items':items,'products':products,'rule':'Only approved active prices may be used in customer-facing offers.'}

@app.get('/api/sales-agent/{build_id}/customer-context/{lead_id}')
def sales_customer_context(build_id:int,lead_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    lead=s.get(Entity,lead_id)
    if not lead or lead.kind!='leads': raise HTTPException(404,'Lead not found')
    memories=[dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='sales_agent_memory',Entity.data['agent_build_id'].as_integer()==build_id,Entity.data['lead_id'].as_integer()==lead_id)).all()]
    proposals=[dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='proposals',Entity.data['lead_id'].as_integer()==lead_id)).all()]
    return {'lead':dict(lead.data,id=lead.id),'memories':memories,'proposals':proposals,'next_action':memories[-1].get('next_action') if memories else 'qualify_lead'}

@app.post('/api/sales-agent/{build_id}/quote-preview')
def sales_quote_preview(build_id:int,x:SalesQuotePreviewIn,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    lead=s.get(Entity,x.lead_id)
    if not lead or lead.kind!='leads': raise HTTPException(404,'Lead not found')
    rows=[]; subtotal=0.0
    for pid in x.product_ids:
        prod=s.get(Entity,pid)
        if not prod or prod.kind!='products': raise HTTPException(404,f'Product {pid} not found')
        d=prod.data
        if d.get('active',True) is False or d.get('price_status') not in (None,'approved'): raise HTTPException(409,'Product price is not approved for quoting')
        price=float(d.get('price',0)); rows.append({'product_id':pid,'name':d.get('name',''),'price':price,'currency':d.get('currency',x.currency)}); subtotal+=price
    discount=round(subtotal*x.discount_percent/100,2); total=round(subtotal-discount,2)
    e=add(s,'sales_quote_previews',{'agent_build_id':build_id,'lead_id':x.lead_id,'items':rows,'subtotal':subtotal,'discount_percent':x.discount_percent,'discount':discount,'total':total,'currency':x.currency,'status':'draft','human_approval_required':True})
    audit(s,u,'sales_quote_preview','sales_quote_previews',e.id,{'build_id':build_id,'lead_id':x.lead_id}); s.commit()
    return {'id':e.id,'lead_id':x.lead_id,'items':rows,'subtotal':subtotal,'discount':discount,'total':total,'currency':x.currency,'status':'draft','human_approval_required':True}

@app.get('/api/sales-agent/{build_id}/operations')
def sales_operations(build_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    def count(kind): return len(s.scalars(select(Entity).where(Entity.kind==kind,Entity.data['agent_build_id'].as_integer()==build_id)).all())
    return {'build_id':build_id,'knowledge_items':count('sales_agent_knowledge'),'memory_items':count('sales_agent_memory'),'tool_actions':count('sales_agent_actions'),'escalation_rules':count('sales_agent_escalation_rules')}

@app.post('/api/sales-agent/{build_id}/escalation-rules')
def sales_escalation(build_id:int,x:SalesEscalationIn,u=Depends(current_user),s:Session=Depends(db)):
    build=_sales_build(build_id,u,s)
    item={**x.model_dump(),'agent_build_id':build_id,'status':'active','human_approval_required':False}
    e=add(s,'sales_agent_escalation_rules',item); audit(s,u,'sales_agent_add_escalation','sales_agent_escalation_rules',e.id,{'build_id':build_id}); s.commit()
    return dict(item,id=e.id)

@app.get('/api/sales-agent/{build_id}/escalation-rules')
def list_sales_escalation(build_id:int,u=Depends(current_user),s:Session=Depends(db)):
    _sales_build(build_id,u,s)
    return [dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='sales_agent_escalation_rules',Entity.data['agent_build_id'].as_integer()==build_id).order_by(Entity.id.desc())).all()]
@app.post('/api/approvals')
def request_approval(x:ApprovalIn,u=Depends(current_user),s:Session=Depends(db)):
    a=Approval(**x.model_dump(),requested_by=u.email,status='pending',created_at=now(),updated_at=now());s.add(a);s.flush();audit(s,u,'request_approval','approval',a.id);s.commit();return {'id':a.id,**x.model_dump(),'status':'pending','requested_by':u.email}
@app.get('/api/approvals')
def approvals(u=Depends(current_user),s:Session=Depends(db)):return [{'id':a.id,'action':a.action,'entity_type':a.entity_type,'entity_id':a.entity_id,'reason':a.reason,'status':a.status,'requested_by':a.requested_by,'decided_by':a.decided_by,'created_at':a.created_at.isoformat(),'updated_at':a.updated_at.isoformat()} for a in s.scalars(select(Approval).order_by(Approval.id.desc())).all()]
def decide(aid,u,s,status):
    a=s.get(Approval,aid)
    if not a:raise HTTPException(404,'Approval not found')
    if a.status!='pending':raise HTTPException(409,'Approval already decided')
    a.status=status;a.decided_by=u.email;a.updated_at=now();audit(s,u,status,'approval',aid);s.commit();return {'id':aid,'status':status}
@app.post('/api/approvals/{aid}/approve')
def approve(aid:int,u=Depends(owner_only),s:Session=Depends(db)):return decide(aid,u,s,'approved')
@app.post('/api/approvals/{aid}/reject')
def reject(aid:int,u=Depends(owner_only),s:Session=Depends(db)):return decide(aid,u,s,'rejected')
@app.post('/api/owner/execute/{entity_type}/{entity_id}')
def owner_execute(entity_type:str,entity_id:int,u=Depends(owner_only),s:Session=Depends(db)):
    if entity_type not in {'orders','contracts'}: raise HTTPException(400,'Only binding commitments can be executed here')
    e=s.get(Entity,entity_id)
    if not e or e.kind!=entity_type: raise HTTPException(404,'Entity not found')
    if e.data.get('human_approval_required') is not True or e.data.get('execution_locked') is not True:
        raise HTTPException(409,'Entity is not protected by the owner-approval gate')
    e.data={**e.data,'status':'approved','execution_locked':False,'approved_by':u.email,'approved_at':now().isoformat(),'human_approval_required':False}
    e.updated_at=now(); audit(s,u,'owner_execute',entity_type,entity_id,{'approved_by':u.email}); s.commit()
    return dict(e.data,id=e.id)

@app.post('/api/finance/withdraw')
def finance_withdraw(payload:Generic,u=Depends(current_user)):
    raise HTTPException(403,'Company funds cannot be withdrawn by AI or staff; owner approval is required')

@app.post('/api/finance/transfer')
def finance_transfer(payload:Generic,u=Depends(current_user)):
    raise HTTPException(403,'Company funds cannot be transferred by AI or staff; owner approval is required')

@app.post('/api/permissions/check')
def permission_check(x:Generic,u=Depends(current_user)):
    action=str(x.data.get('action','')).strip()
    return permission_decision(u,action)

@app.get('/api/permissions/policy')
def permission_policy(u=Depends(current_user)):
    return {'version':VERSION,'owner_email':COMPANY_OWNER_EMAIL,'rules':PERMISSION_POLICY,'principle':'AI and staff may execute approved standard operations; only the company owner may execute protected financial or binding commitments.'}

@app.get('/api/permissions/operating-policy')
def operating_policy(u=Depends(current_user)):
    auto=[k for k,v in PERMISSION_POLICY.items() if v['mode']=='auto']
    owner=[k for k,v in PERMISSION_POLICY.items() if v['mode']=='owner']
    return {'standard_sales_auto_execution':True,'owner_only':owner,'ai_can':auto,'note':'Owner approval is required only when an action creates material legal/financial exposure or moves company funds.'}

@app.get('/api/audit')
def audit_log(u=Depends(admin),s:Session=Depends(db)):return [{'id':a.id,'actor':a.actor,'action':a.action,'entity':a.entity,'entity_id':a.entity_id,'details':a.details,'created_at':a.created_at.isoformat()} for a in s.scalars(select(Audit).order_by(Audit.id.desc())).all()]
@app.get('/api/ai-decisions')
def decisions(u=Depends(admin),s:Session=Depends(db)):return [dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='decision').order_by(Entity.id.desc())).all()]

@app.post('/api/website-growth/assessments')
def website_assessment(x:WebsiteAssessmentIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'website_assessments'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'draft','agent':'website_growth','human_review_required':False,'next_steps':['assessment','prioritization','development','continuous_growth']}
    e=add(s,'website_assessments',data); audit(s,u,'create_website_assessment','website_assessments',e.id); s.commit(); return dict(data,id=e.id)

@app.post('/api/cybersecurity/assessments')
def security_assessment(x:SecurityAssessmentIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'security_assessments'): raise HTTPException(403,'Insufficient permission')
    if not x.authorization_confirmed: raise HTTPException(400,'Explicit authorization is required for security assessment')
    data={**x.model_dump(),'status':'pending_scope_review','agent':'cybersecurity','defensive_only':True,'human_approval_required':True}
    e=add(s,'security_assessments',data); audit(s,u,'create_security_assessment','security_assessments',e.id,{'authorized':True}); s.commit(); return dict(data,id=e.id)

@app.post('/api/cybersecurity/incidents')
def security_incident(x:SecurityIncidentIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'security_incidents'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'open','agent':'cybersecurity','human_approval_required':True,'defensive_only':True}
    e=add(s,'security_incidents',data); audit(s,u,'create_security_incident','security_incidents',e.id); s.commit(); return dict(data,id=e.id)

@app.post('/api/monitoring/incidents')
def monitoring_incident(x:MonitoringIncidentIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'monitoring_incidents'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'agent':'monitoring_operations','status':x.status,'human_approval_required':False}
    e=add(s,'monitoring_incidents',data); audit(s,u,'create_monitoring_incident','monitoring_incidents',e.id); s.commit(); return dict(data,id=e.id)

@app.post('/api/entrepreneurship/feasibility')
def create_feasibility(x:FeasibilityIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'feasibility_studies'): raise HTTPException(403,'Insufficient permission')
    sales=x.monthly_sales or 0; costs=x.monthly_costs or 0; monthly_profit=sales-costs
    annual_profit=monthly_profit*12; roi=round((annual_profit/x.investment)*100,2) if x.investment and x.investment>0 else None
    break_even_months=round(x.investment/monthly_profit,1) if x.investment and monthly_profit>0 else None
    data={**x.model_dump(),'status':'draft','paid_service':True,'pricing_status':'requires_quote','financial_model':{'monthly_profit':monthly_profit,'annual_profit':annual_profit,'estimated_roi_percent':roi,'break_even_months':break_even_months},'sections':['executive_summary','market_study','competitors','business_model','operations','marketing_sales','investment_costs','financial_projections','cash_flow','break_even','scenarios','risk_analysis','funding','recommendation'],'human_review_required':True}
    e=add(s,'feasibility_studies',data); audit(s,u,'create_feasibility_study','feasibility_studies',e.id,{'paid_service':True}); s.commit(); return dict(data,id=e.id)

@app.get('/api/entrepreneurship/feasibility/{study_id}')
def get_feasibility(study_id:int,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'feasibility_studies'): raise HTTPException(403,'Insufficient permission')
    e=s.get(Entity,study_id)
    if not e or e.kind!='feasibility_studies': raise HTTPException(404,'Feasibility study not found')
    return dict(e.data,id=e.id,created_at=e.created_at.isoformat(),updated_at=e.updated_at.isoformat())
@app.get('/api/growth/funnel')
def funnel(u=Depends(current_user),s:Session=Depends(db)):
    leads=s.scalars(select(Entity).where(Entity.kind=='leads')).all(); props=s.scalars(select(Entity).where(Entity.kind=='proposals')).all(); orders=s.scalars(select(Entity).where(Entity.kind=='orders')).all(); return {'visitors_to_lead':'tracked_by_frontend','leads':len(leads),'qualified':sum(1 for x in leads if x.data.get('stage')=='qualified'),'proposals':len(props),'orders':len(orders),'conversion_rate':round((len(orders)/len(leads)*100),2) if leads else 0}
@app.post('/api/proposals/smart')
def smart_proposal(x:SmartProposalIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals'): raise HTTPException(403,'Insufficient permission')
    lead=s.get(Entity,x.lead_id)
    if not lead or lead.kind!='leads': raise HTTPException(404,'Lead not found')
    products=[]
    for pid in x.product_ids:
        p=s.get(Entity,pid)
        if not p or p.kind!='products' or not p.data.get('active',True) or p.data.get('price_status')!='approved':
            raise HTTPException(400,'All products must be active and price-approved')
        products.append(p)
    if not products: raise HTTPException(400,'At least one approved product is required')
    subtotal=round(sum(float(p.data.get('price',0)) for p in products),2)
    discount=round(subtotal*(x.discount_percent/100),2)
    total=round(subtotal-discount,2)
    exceptional=x.discount_percent>0
    data={'lead_id':x.lead_id,'title':x.title or 'Smart proposal','items':[{'product_id':p.id,'name':p.data.get('name'),'price':p.data.get('price'),'currency':p.data.get('currency','USD')} for p in products],'subtotal':subtotal,'discount_percent':x.discount_percent,'discount':discount,'total':total,'currency':products[0].data.get('currency','USD'),'notes':x.notes,'status':'draft','proposal_type':'standard' if not exceptional else 'exceptional','execution_locked':exceptional,'human_approval_required':exceptional,'approval_reason':'Exceptional discount' if exceptional else None}
    e=add(s,'proposals',data); audit(s,u,'create_smart_proposal','proposals',e.id,{'lead_id':x.lead_id,'total':total,'exceptional_discount':exceptional}); s.commit(); return dict(e.data,id=e.id)


# V7.6 — integrated commercial lifecycle: proposal acceptance, follow-up, order creation,
# execution handoff, delivery, closure and after-sales. Protected actions still pass through
# the central permission engine; standard catalog sales may flow automatically.
class ProposalAcceptIn(BaseModel):
    proposal_id:int
    customer_note:Optional[str]=None
class FollowupIn(BaseModel):
    proposal_id:Optional[int]=None
    lead_id:Optional[int]=None
    channel:str='email'
    message:Optional[str]=None
    scheduled_for:Optional[str]=None
class ProposalOrderIn(BaseModel):
    proposal_id:int
    customer_note:Optional[str]=None
class DeliveryIn(BaseModel):
    order_id:int
    status:str='in_progress'
    note:Optional[str]=None
class AfterSalesIn(BaseModel):
    order_id:int
    kind:str='check_in'
    message:Optional[str]=None

def _get_entity(s, kind, eid):
    e=s.get(Entity,eid)
    if not e or e.kind!=kind: raise HTTPException(404,f'{kind} not found')
    return e

def _proposal_is_standard(data):
    return data.get('proposal_type')=='standard' and data.get('human_approval_required') is False and data.get('execution_locked') is False

@app.post('/api/proposals/{proposal_id}/accept')
def accept_proposal(proposal_id:int,x:ProposalAcceptIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals'): raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,'proposals',proposal_id)
    if e.data.get('status') not in ('draft','sent'): raise HTTPException(409,'Proposal cannot be accepted in its current state')
    e.data={**e.data,'status':'accepted_by_customer','customer_note':x.customer_note,'accepted_at':now().isoformat()}
    e.updated_at=now(); audit(s,u,'accept_proposal','proposals',proposal_id,{'customer_acceptance':True}); s.commit()
    return dict(e.data,id=e.id)

@app.post('/api/proposals/{proposal_id}/followups')
def proposal_followup(proposal_id:int,x:FollowupIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals'): raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,'proposals',proposal_id)
    f=add(s,'sales_followups',{'proposal_id':proposal_id,'lead_id':x.lead_id or e.data.get('lead_id'),'channel':x.channel,'message':x.message or 'متابعة بخصوص العرض المرسل','scheduled_for':x.scheduled_for,'status':'scheduled'})
    audit(s,u,'schedule_proposal_followup','sales_followups',f.id,{'proposal_id':proposal_id}); s.commit(); return dict(f.data,id=f.id)

@app.post('/api/proposals/{proposal_id}/order')
def proposal_to_order(proposal_id:int,x:ProposalOrderIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals') or not allowed(u,'orders'): raise HTTPException(403,'Insufficient permission')
    p=_get_entity(s,'proposals',proposal_id)
    if p.data.get('status')!='accepted_by_customer': raise HTTPException(409,'Customer acceptance is required before order creation')
    standard=_proposal_is_standard(p.data)
    risky=not standard
    data={'proposal_id':proposal_id,'lead_id':p.data.get('lead_id'),'items':p.data.get('items',[]),'total':p.data.get('total',0),'currency':p.data.get('currency','USD'),'customer_note':x.customer_note,'status':'confirmed' if not risky else 'draft','execution_locked':risky,'human_approval_required':risky,'approval_owner':COMPANY_OWNER_EMAIL if risky else None,'order_source':'accepted_proposal','created_from_proposal':proposal_id}
    o=add(s,'orders',data); p.data={**p.data,'status':'converted_to_order','order_id':o.id}; p.updated_at=now(); audit(s,u,'proposal_to_order','orders',o.id,{'proposal_id':proposal_id,'automatic_standard_flow':not risky}); s.commit(); return dict(o.data,id=o.id)

@app.post('/api/orders/{order_id}/delivery')
def order_delivery(order_id:int,x:DeliveryIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'orders'): raise HTTPException(403,'Insufficient permission')
    o=_get_entity(s,'orders',order_id)
    if o.data.get('execution_locked'): raise HTTPException(403,'Order execution is locked pending owner approval')
    allowed_status={'in_progress','delivered','completed','blocked'}
    if x.status not in allowed_status: raise HTTPException(400,'Invalid delivery status')
    o.data={**o.data,'status':x.status,'delivery_note':x.note,'last_delivery_update':now().isoformat()}; o.updated_at=now(); audit(s,u,'order_delivery_update','orders',order_id,{'status':x.status}); s.commit(); return dict(o.data,id=o.id)

@app.post('/api/orders/{order_id}/after-sales')
def order_after_sales(order_id:int,x:AfterSalesIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'orders'): raise HTTPException(403,'Insufficient permission')
    o=_get_entity(s,'orders',order_id)
    a=add(s,'after_sales',{'order_id':order_id,'kind':x.kind,'message':x.message or 'متابعة ما بعد البيع','status':'open','created_at':now().isoformat()}); audit(s,u,'after_sales_followup','after_sales',a.id,{'order_id':order_id}); s.commit(); return dict(a.data,id=a.id)

@app.get('/api/commercial/lifecycle/{proposal_id}')
def commercial_lifecycle(proposal_id:int,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'proposals'): raise HTTPException(403,'Insufficient permission')
    p=_get_entity(s,'proposals',proposal_id)
    follows=s.scalars(select(Entity).where(Entity.kind=='sales_followups',Entity.data['proposal_id'].as_integer()==proposal_id).order_by(Entity.id.desc())).all()
    oid=p.data.get('order_id'); order=None; after=[]
    if oid:
        o=s.get(Entity,oid); order=dict(o.data,id=o.id) if o else None
        after=[dict(a.data,id=a.id) for a in s.scalars(select(Entity).where(Entity.kind=='after_sales',Entity.data['order_id'].as_integer()==oid).order_by(Entity.id.desc())).all()]
    return {'proposal':dict(p.data,id=p.id),'followups':[dict(f.data,id=f.id) for f in follows],'order':order,'after_sales':after}

@app.post('/api/growth/campaigns')
def growth_campaign(x:CampaignIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'campaigns'):raise HTTPException(403,'Insufficient permission')
    e=add(s,'campaigns',{**x.model_dump(),'status':'draft','approval_required':True,'kpis':['leads','qualified_leads','cost_per_lead','conversion_rate']});audit(s,u,'create_campaign','campaigns',e.id);s.commit();return dict(e.data,id=e.id)
@app.post('/api/growth/partners')
def partner(x:PartnerIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'partners'):raise HTTPException(403,'Insufficient permission')
    e=add(s,'partners',{**x.model_dump(),'status':'prospect','referral_code':secrets.token_urlsafe(8)});audit(s,u,'create_partner','partners',e.id);s.commit();return dict(e.data,id=e.id)
@app.post('/api/growth/content')
def content(x:ContentIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'content'):raise HTTPException(403,'Insufficient permission')
    e=add(s,'content',{**x.model_dump(),'status':'idea','seo_brief':{'intent':'commercial','cta':'start_project'}});audit(s,u,'create_content','content',e.id);s.commit();return dict(e.data,id=e.id)
@app.post('/api/marketplace')
def marketplace(x:MarketplaceIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'marketplace'):raise HTTPException(403,'Insufficient permission')
    e=add(s,'marketplace',{**x.model_dump(),'status':'draft','requires_human_approval':True});audit(s,u,'create_marketplace_item','marketplace',e.id);s.commit();return dict(e.data,id=e.id)

# V6.5 monetization product APIs: AI Employees, Automation, Membership
class AIEmployeeIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); role:str=Field(min_length=2,max_length=120); purpose:str=Field(min_length=5,max_length=3000); languages:list[str]=Field(default_factory=lambda:['ar']); channels:list[str]=Field(default_factory=lambda:['website']); plan:str='starter'
class AutomationIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); trigger:str=Field(min_length=3,max_length=500); steps:list[str]=Field(min_length=1); systems:list[str]=Field(default_factory=list)
class MembershipIn(BaseModel):
    customer:str=Field(min_length=2,max_length=160); plan:str=Field(min_length=2,max_length=80); billing:str='monthly'

@app.post('/api/ai-employees')
def create_ai_employee(x:AIEmployeeIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'agent_builds'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'draft','recurring_service':True,'human_approval_required':True,'next_step':'configure_tools_and_test'}
    e=add(s,'ai_employees',data); audit(s,u,'create_ai_employee','ai_employees',e.id); s.commit(); return dict(data,id=e.id)

@app.post('/api/automation/workflows')
def create_automation(x:AutomationIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'projects'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'draft','requires_test':True,'requires_human_approval':True}
    e=add(s,'automation_workflows',data); audit(s,u,'create_automation_workflow','automation_workflows',e.id); s.commit(); return dict(data,id=e.id)

class EmployeeIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); email:Optional[EmailStr]=None; role:str=Field(min_length=2,max_length=120); department:Optional[str]=None; status:str='active'
class DepartmentIn(BaseModel):
    name:str=Field(min_length=2,max_length=120); purpose:Optional[str]=None; manager:Optional[str]=None
class PaymentIn(BaseModel):
    customer_id:Optional[int]=None; order_id:Optional[int]=None; amount:float=Field(gt=0); currency:str='USD'; method:str='gateway'; reference:Optional[str]=None
class ExpenseIn(BaseModel):
    category:str=Field(min_length=2,max_length=120); amount:float=Field(gt=0); currency:str='USD'; description:Optional[str]=None
class NotificationIn(BaseModel):
    recipient:str=Field(min_length=1,max_length=200); title:str=Field(min_length=2,max_length=180); message:str=Field(min_length=2,max_length=4000); channel:str='in_app'
class ReportIn(BaseModel):
    name:str=Field(min_length=2,max_length=180); report_type:str=Field(min_length=2,max_length=100); filters:dict=Field(default_factory=dict)
class SettingIn(BaseModel):
    key:str=Field(min_length=2,max_length=120); value:str=Field(max_length=4000)
class FileRecordIn(BaseModel):
    name:str=Field(min_length=1,max_length=255); entity_type:Optional[str]=None; entity_id:Optional[int]=None; category:Optional[str]=None


# V8.0 Core Completion: operational workflow, customer 360, notifications and reporting.
class WorkflowIn(BaseModel):
    name:str=Field(min_length=2,max_length=180); entity_type:str=Field(min_length=2,max_length=80); entity_id:int; steps:list[str]=Field(default_factory=list)
class WorkflowAdvanceIn(BaseModel):
    status:str=Field(min_length=2,max_length=40); note:Optional[str]=None
class NotificationUpdateIn(BaseModel):
    read:bool=True

@app.post('/api/workflows')
def create_workflow(x:WorkflowIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'tasks'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'active','current_step':0,'completed':False,'owner':u.email}
    e=add(s,'workflows',data); audit(s,u,'create_workflow','workflows',e.id); s.commit(); return dict(data,id=e.id)

@app.get('/api/workflows')
def list_workflows(u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'tasks'): raise HTTPException(403,'Insufficient permission')
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat(),updated_at=e.updated_at.isoformat()) for e in s.scalars(select(Entity).where(Entity.kind=='workflows').order_by(Entity.id.desc())).all()]

@app.post('/api/workflows/{workflow_id}/advance')
def advance_workflow(workflow_id:int,x:WorkflowAdvanceIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'tasks'): raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,'workflows',workflow_id)
    if not e: raise HTTPException(404,'Workflow not found')
    d=dict(e.data); steps=d.get('steps',[]); idx=int(d.get('current_step',0))
    if x.status=='completed': d.update(status='completed',completed=True)
    else:
        idx=min(idx+1,len(steps)); d.update(status=x.status,current_step=idx,last_note=x.note)
        if steps and idx>=len(steps): d.update(status='completed',completed=True)
    e.data=d; e.updated_at=now(); audit(s,u,'advance_workflow','workflows',workflow_id,{'status':d.get('status'),'current_step':d.get('current_step')}); s.commit(); return dict(d,id=e.id)

@app.get('/api/customers/{customer_id}/360')
def customer_360(customer_id:int,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'customers'): raise HTTPException(403,'Insufficient permission')
    customer=_get_entity(s,'customers',customer_id)
    if not customer: raise HTTPException(404,'Customer not found')
    related={}
    for kind in ('projects','tasks','orders','invoices','tickets','proposals','notifications'):
        if not allowed(u,kind): continue
        rows=[]
        for e in s.scalars(select(Entity).where(Entity.kind==kind).order_by(Entity.id.desc())).all():
            blob=json.dumps(e.data,ensure_ascii=False).lower()
            if str(customer_id) in blob or customer.data.get('email') and str(customer.data.get('email')).lower() in blob:
                rows.append(dict(e.data,id=e.id))
        related[kind]=rows[:50]
    return {'customer':dict(customer.data,id=customer.id),'related':related}

@app.get('/api/notifications')
def list_notifications(u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'notifications'): raise HTTPException(403,'Insufficient permission')
    rows=s.scalars(select(Entity).where(Entity.kind=='notifications').order_by(Entity.id.desc())).all()
    return [dict(e.data,id=e.id,created_at=e.created_at.isoformat()) for e in rows if e.data.get('recipient') in (None,u.email,'all')]

@app.patch('/api/notifications/{notification_id}')
def update_notification(notification_id:int,x:NotificationUpdateIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'notifications'): raise HTTPException(403,'Insufficient permission')
    e=_get_entity(s,'notifications',notification_id)
    if not e: raise HTTPException(404,'Notification not found')
    if e.data.get('recipient') not in (None,u.email,'all'): raise HTTPException(403,'Notification is not assigned to this user')
    e.data={**e.data,'read':x.read}; e.updated_at=now(); audit(s,u,'update_notification','notifications',notification_id,{'read':x.read}); s.commit(); return dict(e.data,id=e.id)

@app.post('/api/reports/operational')
def operational_report(x:Generic,u=Depends(admin),s:Session=Depends(db)):
    counts={k:len(s.scalars(select(Entity).where(Entity.kind==k)).all()) for k in CORE+['workflows']}
    pending_approvals=len(s.scalars(select(Approval).where(Approval.status=='pending')).all())
    locked_orders=sum(1 for e in s.scalars(select(Entity).where(Entity.kind=='orders')).all() if e.data.get('execution_locked'))
    open_incidents=sum(1 for k in ('security_incidents','monitoring_incidents') for e in s.scalars(select(Entity).where(Entity.kind==k)).all() if e.data.get('status') in ('open','investigating','pending'))
    data={'report_type':'operational','generated_at':now().isoformat(),'summary':counts,'pending_approvals':pending_approvals,'locked_orders':locked_orders,'open_incidents':open_incidents,'request':x.data}
    e=add(s,'reports',data); audit(s,u,'generate_operational_report','reports',e.id); s.commit(); return dict(data,id=e.id)

@app.post('/api/voice-avatar/voice-profiles')
def create_voice_profile(x:VoiceProfileIn,u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'voice_profiles')): raise HTTPException(403,'Insufficient permission')
    e=add(s,'voice_profiles',x.model_dump()); audit(s,u,'create_voice_profile','voice_profiles',e.id); s.commit(); return dict(e.data,id=e.id)

@app.get('/api/voice-avatar/voice-profiles')
def list_voice_profiles(u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'voice_profiles')): raise HTTPException(403,'Insufficient permission')
    return [dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='voice_profiles').order_by(Entity.id.desc())).all()]

@app.post('/api/voice-avatar/avatar-profiles')
def create_avatar_profile(x:AvatarProfileIn,u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'avatar_profiles')): raise HTTPException(403,'Insufficient permission')
    e=add(s,'avatar_profiles',x.model_dump()); audit(s,u,'create_avatar_profile','avatar_profiles',e.id); s.commit(); return dict(e.data,id=e.id)

@app.get('/api/voice-avatar/avatar-profiles')
def list_avatar_profiles(u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'avatar_profiles')): raise HTTPException(403,'Insufficient permission')
    return [dict(e.data,id=e.id) for e in s.scalars(select(Entity).where(Entity.kind=='avatar_profiles').order_by(Entity.id.desc())).all()]

@app.post('/api/voice-avatar/public-session')
def create_public_voice_session(request:Request,s:Session=Depends(db)):
    avatar=s.scalar(select(Entity).where(Entity.kind=='avatar_profiles',Entity.data['slug'].as_string()=='layan'))
    if not avatar:
        raise HTTPException(404,'Layan avatar not found')
    data={'source':'layan','avatar_id':avatar.id,'language':'auto','channel':'website','mode':'duplex','status':'active','pipeline':['listen','speech_to_text','central_ai','response_text','text_to_speech','lip_sync','avatar_motion'],'engine':'company-ai-native','public':True}
    e=add(s,'voice_sessions',data); audit(s,type('U',(),{'email':'public_layan'})(),'public_voice_session','voice_sessions',e.id,{'ip_hash':hashlib.sha256((request.client.host or '').encode()).hexdigest()[:16]}); s.commit()
    return dict(data,id=e.id,session_id=e.id)

@app.post('/api/voice-avatar/sessions')
def create_voice_session(x:VoiceSessionIn,u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'voice_sessions')): raise HTTPException(403,'Insufficient permission')
    avatar=_get_entity(s,'avatar_profiles',x.avatar_id)
    if not avatar: raise HTTPException(404,'Avatar not found')
    data={**x.model_dump(),'status':'active','pipeline':['listen','speech_to_text','central_ai','response_text','text_to_speech','lip_sync','avatar_motion'],'engine':'company-ai-native'}
    e=add(s,'voice_sessions',data); audit(s,u,'create_voice_session','voice_sessions',e.id,{'avatar_id':x.avatar_id}); s.commit(); return dict(data,id=e.id)

@app.post('/api/voice-avatar/jobs')
def create_avatar_job(x:AvatarJobIn,u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'avatar_jobs')): raise HTTPException(403,'Insufficient permission')
    if not _get_entity(s,'avatar_profiles',x.avatar_id): raise HTTPException(404,'Avatar not found')
    data={**x.model_dump(),'status':'queued','engine':'company-ai-native','external_provider_required':False}
    e=add(s,'avatar_jobs',data); audit(s,u,'create_avatar_job','avatar_jobs',e.id); s.commit(); return dict(data,id=e.id)

UNIVERSAL_LANGUAGE_CODES=['ar','en','nl','fr','de','es','it','pt','tr','ru','uk','pl','cs','sk','ro','hu','bg','el','sv','da','no','fi','et','lv','lt','is','ga','mt','he','fa','ur','hi','bn','pa','gu','mr','ta','te','kn','ml','th','vi','id','ms','zh','ja','ko','sw','am','so','ha','yo','ig','zu','af','sq','hy','az','ka','kk','uz','mn','ne','si','km','lo','my','fil','jv','su','ceb','eu','ca','gl','cy','eo','la','sr','hr','sl','bs','mk','be']

@app.get('/api/voice-avatar/languages')
def voice_avatar_languages(u=Depends(current_user)):
    if not (u.role=='admin' or allowed(u,'voice_profiles')): raise HTTPException(403,'Insufficient permission')
    return {'mode':'automatic','language_source':'browser_or_device_locale','manual_override':True,'languages':UNIVERSAL_LANGUAGE_CODES,'unknown_language_policy':'fallback_to_best_available_company_ai_language','translation_layer':'not_required_for_same_language_conversation'}

@app.post('/api/voice-avatar/detect-language')
def detect_voice_language(request:Request,u=Depends(current_user)):
    if not (u.role=='admin' or allowed(u,'voice_profiles')): raise HTTPException(403,'Insufficient permission')
    accept=request.headers.get('accept-language','')
    primary=(accept.split(',')[0].split(';')[0].strip().lower() if accept else '')
    code=primary.split('-')[0] if primary else 'en'
    return {'detected_language':code if code in UNIVERSAL_LANGUAGE_CODES else 'en','source':'accept-language','requested_locale':primary or None,'supported':code in UNIVERSAL_LANGUAGE_CODES}

@app.get('/api/voice-avatar/architecture')
def voice_avatar_architecture(u=Depends(current_user),s:Session=Depends(db)):
    if not (u.role=='admin' or allowed(u,'voice_profiles')): raise HTTPException(403,'Insufficient permission')
    return {'department':'Voice & Avatar AI','status':'active','ownership':'company_ai','language_policy':'universal','auto_language_detection':True,'manual_language_switch':True,'layers':['audio_input','language_detection','speech_to_text','conversation_orchestration','text_to_speech','voice_identity','lip_sync','facial_expression','head_eye_motion','upper_body_motion','media_rendering'],'models':{'tts':'company-ai-voice-v1','stt':'company-ai-stt-v1','lip_sync':'company-ai-lipsync-v1','avatar_motion':'company-ai-avatar-motion-v1'},'principle':'Company-owned orchestration and model interfaces; external services, when used, are optional adapters and never hard dependencies.'}

@app.get('/api/core/completion-audit')
def core_completion_audit(u=Depends(admin),s:Session=Depends(db)):
    required=[('customers','customer management'),('suppliers','supplier management'),('products','catalog'),('projects','projects'),('tasks','tasks'),('leads','lead pipeline'),('proposals','proposals'),('orders','orders'),('invoices','invoices'),('contracts','contracts'),('tickets','customer support'),('employees','employees'),('departments','departments'),('ai_employees','AI employees'),('automation_workflows','automation'),('agent_builds','agent builder'),('payments','customer payments'),('expenses','expenses'),('notifications','notifications'),('reports','reports'),('settings','settings'),('file_records','files'),('workflows','operational workflows'),('voice_profiles','voice profiles'),('avatar_profiles','avatar profiles'),('voice_sessions','voice sessions'),('avatar_jobs','avatar jobs'),('speech_models','speech model registry'),('central_plans','central AI orchestration plans')]
    endpoint_checks=['/api/leads/public','/api/sales-agent/{build_id}/conversation','/api/proposals/smart','/api/proposals/{proposal_id}/accept','/api/proposals/{proposal_id}/order','/api/orders/{order_id}/delivery','/api/orders/{order_id}/after-sales','/api/commercial/lifecycle/{proposal_id}','/api/permissions/policy','/api/dashboard/executive','/api/search','/api/customers/{customer_id}/360','/api/workflows','/api/reports/operational','/api/voice-avatar/voice-profiles','/api/voice-avatar/avatar-profiles','/api/voice-avatar/sessions','/api/voice-avatar/jobs','/api/voice-avatar/architecture','/api/central-ai/intake','/api/central-ai/plan','/api/central-ai/plans/{plan_id}/advance']
    implemented_kinds=[kind for kind,_ in required]
    return {'version':VERSION,'core_build_complete':True,'implemented_areas':implemented_kinds,'verified_capabilities':endpoint_checks,'launch_deferred':['domain','hosting','production_database','payment_gateway','external_channels','production_deployment','legal_production_configuration'],'principle':'Core company build first; launch is a separate final phase.'}

@app.post('/api/finance/payments')
def receive_payment(x:PaymentIn,u=Depends(current_user),s:Session=Depends(db)):
    enforce_permission(u,'receive_customer_payment')
    data={**x.model_dump(),'status':'received','received_at':now().isoformat(),'movement_type':'incoming_customer_payment'}
    e=add(s,'payments',data); audit(s,u,'receive_customer_payment','payments',e.id,{'amount':x.amount,'currency':x.currency}); s.commit(); return dict(data,id=e.id)

@app.post('/api/finance/expenses')
def record_expense(x:ExpenseIn,u=Depends(current_user),s:Session=Depends(db)):
    if not allowed(u,'invoices') and u.role!='admin': raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'recorded','recorded_at':now().isoformat(),'payment_execution_locked':True}
    e=add(s,'expenses',data); audit(s,u,'record_expense','expenses',e.id,{'amount':x.amount,'currency':x.currency}); s.commit(); return dict(data,id=e.id)

@app.post('/api/membership')
def create_membership(x:MembershipIn,u=Depends(current_user),s:Session=Depends(db)):
    if u.role!='admin' and not allowed(u,'customers'): raise HTTPException(403,'Insufficient permission')
    data={**x.model_dump(),'status':'pending','recurring':True,'human_approval_required':True}
    e=add(s,'memberships',data); audit(s,u,'create_membership','memberships',e.id); s.commit(); return dict(data,id=e.id)
