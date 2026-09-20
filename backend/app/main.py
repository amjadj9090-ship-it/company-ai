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
from .realtime_routes import router as layan_realtime_router
import jwt
from jwt import InvalidTokenError as JWTError
from sqlalchemy import create_engine,String,Integer,DateTime,Text,select
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,Session
from sqlalchemy.types import JSON

VERSION='8.5.1-security-test'
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./company_ai.db').strip()
JWT_SECRET=os.getenv('JWT_SECRET',''); JWT_ALG='HS256'; ACCESS_MINUTES=int(os.getenv('ACCESS_TOKEN_MINUTES','30'))
ENVIRONMENT=os.getenv('ENVIRONMENT','development').strip().lower()
COMPANY_OWNER_EMAIL=os.getenv('COMPANY_OWNER_EMAIL','owner@example.com').strip().lower()
if ENVIRONMENT=='production' and not DATABASE_URL.lower().startswith(('postgresql://','postgres://')): raise RuntimeError('Production DATABASE_URL must point to PostgreSQL')
if ENVIRONMENT=='production' and len(JWT_SECRET)<32: raise RuntimeError('JWT_SECRET must be at least 32 characters in production')
if ENVIRONMENT=='production' and os.getenv('PASSWORD_PEPPER','') in ('','dev-pepper'): raise RuntimeError('PASSWORD_PEPPER must be configured in production')
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
default_origins='' if ENVIRONMENT=='production' else 'http://localhost:8000,http://localhost:5173'
origins=[x.strip() for x in os.getenv('CORS_ORIGINS',default_origins).split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Authorization','Content-Type','Idempotency-Key'],max_age=600)
class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app): super().__init__(app); self.hits={}; self.window=60; self.limit=int(os.getenv('PUBLIC_RATE_LIMIT','30')); self.max_body=int(os.getenv('MAX_REQUEST_BYTES','1048576'))
    async def dispatch(self, request, call_next):
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            cl=request.headers.get('content-length')
            if cl and int(cl)>self.max_body: return JSONResponse({'detail':'Request too large'},status_code=413)
        ip=(request.client.host if request.client else 'unknown')
        if request.url.path.startswith('/api/central-ai/public-') or request.url.path in {'/api/leads/public','/api/voice-avatar/public-session'}:
            import time; now_t=time.monotonic(); bucket=[t for t in self.hits.get(ip,[]) if now_t-t<self.window]
            if len(bucket)>=self.limit: return JSONResponse({'detail':'Rate limit exceeded. Please try again later.'},status_code=429,headers={'Retry-After':'60'})
            bucket.append(now_t); self.hits[ip]=bucket
        response=await call_next(request); response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'; response.headers['Referrer-Policy']='strict-origin-when-cross-origin'; response.headers['Permissions-Policy']='camera=(), geolocation=(), microphone=(self), payment=(), usb=()'; response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";
        if request.url.path == '/': response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'; response.headers['Pragma']='no-cache'
        if os.getenv('ENVIRONMENT')=='production': response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        return response
app.add_middleware(SecurityMiddleware)
trusted=[x.strip() for x in os.getenv('TRUSTED_HOSTS','').split(',') if x.strip()]
if trusted:
    from starlette.middleware.trustedhost import TrustedHostMiddleware; app.add_middleware(TrustedHostMiddleware,allowed_hosts=trusted)
if os.getenv('ENVIRONMENT')=='production':
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware; app.add_middleware(HTTPSRedirectMiddleware)
def now(): return datetime.now(timezone.utc)
def pwd_hash(p):
    salt=secrets.token_bytes(16); pepper=os.getenv('PASSWORD_PEPPER','dev-pepper').encode(); dk=hashlib.pbkdf2_hmac('sha256',pepper+p.encode(),salt,310000); return 'pbkdf2$310000$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(dk).decode()
def verify(p,h):
    try:
        scheme,rounds,salt_b64,dk_b64=h.split('$',3)
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
    owner_email=COMPANY_OWNER_EMAIL
    owner_password=os.getenv('DEMO_ADMIN_PASSWORD','')
    owner=s.scalar(select(UserRow).where(UserRow.email==owner_email))
    if not owner:
        if ENVIRONMENT=='production' and (owner_email=='owner@example.com' or len(owner_password)<16 or owner_password=='change-me'):
            raise RuntimeError('Production owner credentials must be configured before first owner creation')
        s.add(UserRow(name='Owner',email=owner_email,password_hash=pwd_hash(owner_password),role='admin',active=True))
    else:
        owner.name=owner.name or 'Owner'; owner.role='admin'; owner.active=True
        if owner_password and owner_password!='change-me' and not verify(owner_password,owner.password_hash): owner.password_hash=pwd_hash(owner_password)
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
    if not public_sales: add(s,'agent_builds',{'slug':'public-sales-ai','name':'Company AI Sales Employee','role':'sales','purpose':'Handle website sales conversations using approved catalog and CRM context.','channels':['website'],'languages':['auto'],'knowledge':['products','pricing','faq'],'tools':['CRM','lead_capture'],'autonomy':'supervised','personality':'professional','human_approval_required':True,'status':'active','public_chat':True})
    defaults=[('market','Europe'),('market','Middle East'),('market','North America'),('market','Asia'),('market','Africa')]
    for k,v in defaults:
        if not s.scalar(select(Entity).where(Entity.kind==k,Entity.data['name'].as_string()==v)): add(s,k,{'name':v,'status':'planned'})
    s.commit()
@app.get('/healthz')
def healthz():
    return {'status':'ok','version':VERSION,'mode':os.getenv('ENVIRONMENT','development'),'database':'postgresql' if DATABASE_URL.lower().startswith(('postgresql://','postgres://')) else 'sqlite'}
FRONTEND_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','frontend'))
PUBLIC_FRONTEND_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','frontend-v2'))
ASSETS_DIR=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','assets'))
app.mount('/assets', StaticFiles(directory=ASSETS_DIR), name='assets')
app.mount('/frontend-assets', StaticFiles(directory=FRONTEND_DIR), name='frontend-assets')
app.mount('/frontend-v2', StaticFiles(directory=PUBLIC_FRONTEND_DIR), name='frontend-v2')
@app.get('/layan-realtime-hotfix.js',include_in_schema=False)
def layan_realtime_hotfix(): return FileResponse(os.path.join(FRONTEND_DIR,'layan-realtime-hotfix.js'),media_type='application/javascript')
@app.get('/',include_in_schema=False)
def public_home(): return FileResponse(os.path.join(PUBLIC_FRONTEND_DIR,'index.html'),media_type='text/html')
with Session(engine) as s: seed(s)
class Login(BaseModel): email:EmailStr; password:str=Field(min_length=1)
class Generic(BaseModel): data:dict=Field(default_factory=dict)
class ApprovalIn(BaseModel): action:str; entity_type:str; entity_id:int; reason:Optional[str]=None
class LeadIn(BaseModel): name:str=Field(min_length=1,max_length=120); email:EmailStr; company:Optional[str]=None; country:Optional[str]=None; language:Optional[str]=None; need:str=Field(min_length=3,max_length=4000); source:Optional[str]='website'; budget:Optional[str]=None
class QualifyIn(BaseModel): lead_id:int
class CentralAIIntakeIn(BaseModel): message:str=Field(min_length=2,max_length=8000); language:Optional[str]='auto'; channel:Optional[str]='website'; session_id:Optional[str]=None; customer_id:Optional[int]=None; lead_id:Optional[int]=None
class CentralAIPlanIn(BaseModel): message:str=Field(min_length=2,max_length=8000); language:Optional[str]='auto'; channel:Optional[str]='internal'; priority:Optional[str]='normal'; customer_id:Optional[int]=None; lead_id:Optional[int]=None; auto_execute_standard:bool=True
class CentralAIExecuteIn(BaseModel): plan_id:int; confirm:bool=False
class ProposalIn(BaseModel): lead_id:int; title:str; scope:list[str]=Field(default_factory=list); notes:Optional[str]=None
class SmartProposalIn(BaseModel): lead_id:int; product_ids:list[int]=Field(default_factory=list); title:Optional[str]=None; notes:Optional[str]=None; discount_percent:float=Field(default=0,ge=0,le=100)
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
class VoiceProfileIn(BaseModel): name:str=Field(min_length=2,max_length=160); language:str='ar'; locale:str='ar'; gender:str='female'; style:str='professional'; provider_mode:str='local-first'; model:str='company-ai-voice-v1'; active:bool=True
class AvatarProfileIn(BaseModel): name:str=Field(min_length=2,max_length=160); visual_style:str='realistic'; identity:str='fictional'; voice_profile_id:Optional[int]=None; lip_sync_model:str='company-ai-lipsync-v1'; animation_model:str='company-ai-avatar-motion-v1'; active:bool=True
class VoiceSessionIn(BaseModel): avatar_id:int; language:str='ar'; channel:str='website'; mode:str='duplex'; user_id:Optional[int]=None
class AvatarJobIn(BaseModel): avatar_id:int; job_type:str='lip_sync'; text:Optional[str]=None; audio_asset_id:Optional[int]=None; priority:str='normal'
class SpeechModelIn(BaseModel): name:str; model_type:str; languages:list[str]=Field(default_factory=lambda:['ar']); local:bool=True; status:str='planned'; notes:Optional[str]=None

class SalesConversationIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    language: Optional[str] = 'auto'
    history: list[dict] = Field(default_factory=list, max_length=6)


def _layan_local_reply(message: str, language: str = 'auto') -> str:
    return 'فهمت عليك. خدمة الذكاء المركزي غير متاحة حالياً، لذلك لن أعطيك جواباً عشوائياً. جرّب الطلب مرة أخرى بعد عودة الخدمة.'


def _layan_gemini_reply(message: str, language: str = 'auto', history: list[dict] | None = None) -> str | None:
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        return None
    contents = []
    for item in (history or [])[-6:]:
        role = 'model' if item.get('role') in {'assistant', 'model'} else 'user'
        text_value = str(item.get('text') or item.get('content') or '').strip()
        if text_value:
            contents.append({'role': role, 'parts': [{'text': text_value[:2000]}]})
    contents.append({'role': 'user', 'parts': [{'text': message.strip()}]})
    system = (
        'أنت ليان، المساعدة الصوتية والعقل الحواري في Company AI. '
        'افهمي كل رسالة بحسب معناها وسياق المحادثة، ولا تستخدمي قوالب ثابتة أو تكرري جواباً عاماً. '
        'تحدثي بالعربية الشامية الطبيعية عندما يكون المستخدم عربياً، وبنفس لغة المستخدم عند استخدام لغة أخرى. '
        'أجيبي مباشرة وباختصار مفيد، واطلبي توضيحاً فقط عندما يكون ضرورياً. '
        'إذا كان الطلب يحتاج عملاً داخل Company AI، حددي المطلوب والخطوة التالية بوضوح، ولا تدّعي تنفيذ أي إجراء لم يُنفذ فعلياً. '
        'يمكنك التخطيط واقتراح الإجراءات، لكن تحويل الأموال أو السحب أو توقيع عقد أو أي التزام مالي/قانوني ملزم يحتاج موافقة المالك. '
        'اعتبري سجل المحادثة السابق جزءاً من السياق ولا تعيدي السؤال عن معلومات موجودة فيه.'
    )
    payload = {
        'system_instruction': {'parts': [{'text': system}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.65, 'maxOutputTokens': 320}
    }
    try:
        import urllib.request
        req = urllib.request.Request(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        reply = ''.join(str(p.get('text', '')) for p in parts).strip()
        return reply or None
    except Exception as exc:
        print(f'Layan Gemini reply unavailable: {type(exc).__name__}: {exc}')
        return None


@app.get('/api/sales-agent/public/config')
def public_sales_config(s: Session = Depends(db)):
    row = s.scalar(select(Entity).where(
        Entity.kind == 'agent_builds',
        Entity.data['slug'].as_string() == 'public-sales-ai'
    ))
    if not row:
        raise HTTPException(status_code=404, detail='Public sales agent is not configured')
    return {
        'build_id': str(row.id),
        'slug': 'public-sales-ai',
        'name': row.data.get('name', 'Company AI Sales Employee'),
        'status': row.data.get('status', 'active')
    }


@app.post('/api/sales-agent/{agent_id}/conversation')
def public_sales_conversation(agent_id: str, x: SalesConversationIn, s: Session = Depends(db)):
    row = s.get(Entity, int(agent_id)) if agent_id.isdigit() else s.scalar(
        select(Entity).where(
            Entity.kind == 'agent_builds',
            Entity.data['slug'].as_string() == agent_id
        )
    )
    if not row or row.kind != 'agent_builds' or row.data.get('slug') != 'public-sales-ai':
        raise HTTPException(status_code=404, detail='Sales agent not found')
    reply = _layan_gemini_reply(
        x.message,
        x.language or 'auto',
        x.history
    )
    source = 'gemini-free-tier'
    if not reply:
        reply = _layan_local_reply(x.message, x.language or 'auto')
        source = 'service-unavailable-fallback'
    s.add(Audit(
        actor='layan-public',
        action='conversation_message',
        entity='agent_builds',
        entity_id=row.id,
        details={
            'message': x.message[:1000],
            'language': x.language or 'auto',
            'history_turns': len(x.history),
            'reply': reply[:2000],
            'source': source
        },
        created_at=now()
    ))
    s.commit()
    return {
        'reply': reply,
        'agent_id': str(row.id),
        'language': x.language or 'auto',
        'source': source
    }



ROLE_OK={'admin':{'*'},'sales':{'customers','projects','tasks','quotes','orders','tickets','leads','proposals','products'},'finance':{'invoices','orders','customers'},'trade':{'suppliers','products','orders','quotes'},'marketing':{'customers','projects','tasks','quotes','leads','campaigns','content'},'support':{'customers','tickets'},'growth':{'leads','campaigns','partners','content'},'entrepreneurship':{'feasibility_studies','projects','tasks','customers'},'website_growth':{'website_assessments','projects','tasks','customers'},'cybersecurity':{'security_assessments','security_incidents','projects','tasks'},'monitoring':{'monitoring_incidents','projects','tasks'},'monitoring_operations':{'monitoring_incidents','projects','tasks','customers'},'agent_builder':{'agent_builds','agents','projects','tasks','customers'},'voice_avatar':{'voice_profiles','avatar_profiles','voice_sessions','avatar_jobs','media_assets','speech_models','voice_models'}}
PERMISSION_POLICY={'standard_sale': {'mode':'auto','allowed_actors':['ai','staff','owner']},'approved_catalog_order': {'mode':'auto','allowed_actors':['ai','staff','owner']},'normal_invoice': {'mode':'auto','allowed_actors':['ai','staff','owner']},'customer_followup': {'mode':'auto','allowed_actors':['ai','staff','owner']},'draft_contract': {'mode':'auto','allowed_actors':['ai','staff','owner']},'receive_customer_payment': {'mode':'auto','allowed_actors':['ai','staff','owner']},'bank_withdrawal': {'mode':'owner','allowed_actors':['owner']},'bank_transfer': {'mode':'owner','allowed_actors':['owner']},'binding_contract': {'mode':'owner','allowed_actors':['owner']},'exceptional_financial_commitment': {'mode':'owner','allowed_actors':['owner']},'loan': {'mode':'owner','allowed_actors':['owner']},'settlement': {'mode':'owner','allowed_actors':['owner']},'penalty': {'mode':'owner','allowed_actors':['owner']},'exceptional_discount': {'mode':'owner','allowed_actors':['owner']}}
def actor_type(u): return 'owner' if u.email.lower()==COMPANY_OWNER_EMAIL else ('ai' if str(u.role).lower() in {'ai','agent','central_ai'} else 'staff')
def permission_decision(u, action, context=None):
    rule=PERMISSION_POLICY.get(action)
    if not rule: return {'allowed':False,'mode':'owner','reason':'Unknown action requires owner approval'}
    a=actor_type(u); allowed=a in rule['allowed_actors']; return {'allowed':allowed,'mode':rule['mode'],'actor':a,'action':action,'reason':'Allowed by central policy' if allowed else 'Owner approval required'}
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
    r=await call_next(request); r.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(), microphone=(self), geolocation=()'}); return r
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
        data=dict(x.data); protected=False
        if kind == 'contracts': protected=True
        elif kind == 'orders':
            standard=bool(data.get('standard_package') or data.get('approved_template') or data.get('catalog_price_approved')); risky=bool(data.get('exceptional_discount') or data.get('custom_liability') or data.get('financial_commitment'))
            if standard and not risky: enforce_permission(u,'standard_sale'); data['status']='confirmed'; data['human_approval_required']=False; data['execution_locked']=False; data['approval_mode']='preapproved_standard_sale'
            else: protected=True
        elif kind == 'invoices':
            enforce_permission(u,'normal_invoice'); data['status']=data.get('status','issued'); data['human_approval_required']=False; data['execution_locked']=False; data['approval_mode']='operational'
        if protected:
            data['status']='draft'; data['human_approval_required']=True; data['execution_locked']=True
