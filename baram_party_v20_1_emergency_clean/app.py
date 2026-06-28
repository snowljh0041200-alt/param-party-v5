from flask import Flask, request, redirect, session, render_template_string, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, uuid, re, html

APP_VERSION = 'v20.1-emergency'
SITE_TITLE = '월하 · 연가 · 연희 파티모집'
DATA_FILE = os.environ.get('DATA_FILE', 'data.json')
KST = ZoneInfo('Asia/Seoul')
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','baram-v20-emergency-secret')

JOBS = ['검성','검신','검황','진선','도사','전사','도적','주술사','궁사','기타']
CATEGORIES = ['전체','사냥','600퀘','파밍']
PLACES = {'사냥':['도삭산 900층','흉노','선비','북방','기타'], '600퀘':['600퀘'], '파밍':['해골왕','흑룡','묵룡','진룡','기타']}
FARM_ITEMS = ['해뼈','흑룡','묵룡','진룡']

def now(): return datetime.now(KST)
def today(): return now().strftime('%Y-%m-%d')
def stamp(): return now().strftime('%m/%d %H:%M')
def nid(): return str(uuid.uuid4())
def esc(x): return html.escape(str(x or ''))
def digits(x,n=4): return re.sub(r'\D','',str(x or ''))[:n]

def clean_time(v):
    s=re.sub(r'[^0-9:]','',str(v or '').replace('：',':'))
    if not s: return ''
    try:
        if ':' in s:
            a,b=s.split(':',1); h=int(a); m=int((b+'00')[:2])
        elif len(s)<=2:
            h=int(s); m=0
        elif len(s)==3:
            h=int(s[0]); m=int(s[1:])
        else:
            h=int(s[:2]); m=int(s[2:4])
        if 0<=h<=23 and 0<=m<=59: return f'{h:02d}:{m:02d}'
    except Exception: pass
    return ''

def to24(period, val):
    t=clean_time(val)
    if not t: return ''
    h,m=map(int,t.split(':'))
    if period=='오후' and h<12: h+=12
    if period=='오전' and h==12: h=0
    return f'{h:02d}:{m:02d}'

def split12(v):
    t=clean_time(v)
    if not t: return '오전',''
    h,m=map(int,t.split(':'))
    p='오후' if h>=12 else '오전'
    h12=h%12 or 12
    return p, f'{h12:02d}:{m:02d}'

def show_time(v):
    p,t=split12(v)
    return f'{p} {t}' if t else '시간 미정'

def empty_data(): return {'users':[], 'posts':[], 'global_chat':[], 'settings':{'farm_items':FARM_ITEMS}}

def norm(d):
    d.setdefault('users',[]); d.setdefault('posts',[]); d.setdefault('global_chat',[]); d.setdefault('settings',{}); d['settings'].setdefault('farm_items',FARM_ITEMS)
    for u in d['users']:
        u.setdefault('id',nid()); u.setdefault('account',''); u.setdefault('status','pending'); u.setdefault('role','일반'); u.setdefault('chars',[])
        if 'selected_char_id' not in u and u['chars']: u['selected_char_id']=u['chars'][0].get('id')
        for c in u['chars']:
            c.setdefault('id',nid()); c.setdefault('name',''); c.setdefault('job','기타'); c.setdefault('status','pending')
    for p in d['posts']:
        p.setdefault('id',nid()); p.setdefault('category','사냥'); p.setdefault('place',''); p.setdefault('channel',''); p.setdefault('date',today())
        p.setdefault('start_time',''); p.setdefault('end_time',''); p.setdefault('memo',''); p.setdefault('owner_uid',''); p.setdefault('owner_label',''); p.setdefault('created',stamp()); p.setdefault('closed',False)
        p.setdefault('slots',[]); p.setdefault('participants',[]); p.setdefault('chat',[]); p.setdefault('farm_result',''); p.setdefault('farm_item',''); p.setdefault('sale_amount','')
        for s in p['slots']:
            s.setdefault('job',''); s.setdefault('uid',''); s.setdefault('char_id',''); s.setdefault('label',''); s.setdefault('external','')
    return d

def load():
    if not os.path.exists(DATA_FILE):
        d=empty_data(); save(d); return d
    try:
        with open(DATA_FILE,'r',encoding='utf-8') as f: return norm(json.load(f))
    except Exception:
        return empty_data()

def save(d):
    d=norm(d); tmp=DATA_FILE+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    os.replace(tmp, DATA_FILE)

def current_user(d=None):
    d=d or load(); uid=session.get('uid')
    for u in d['users']:
        if u.get('id')==uid: return u
    return None

def approved(u): return bool(u and u.get('status')=='approved')
def admin(u): return bool(u and u.get('role') in ['관리자','부문파장','문파장','최고관리자'])
def chars(u): return [c for c in (u or {}).get('chars',[]) if c.get('status')=='approved']
def sel_char(u):
    cs=chars(u)
    if not cs: return None
    sid=u.get('selected_char_id')
    return next((c for c in cs if c.get('id')==sid), cs[0])
def clabel(c): return f"{c.get('name','')}({c.get('job','')})" if c else ''
def find_post(d,pid): return next((p for p in d['posts'] if p.get('id')==pid), None)
def joined(p): return sum(1 for s in p['slots'] if s.get('uid') or s.get('external')) if p.get('category')=='사냥' else len(p.get('participants',[]))
def maxcnt(p): return len(p['slots']) if p.get('category')=='사냥' else (10 if p.get('category')=='600퀘' else max(0,len(p.get('participants',[]))))
def pdt(p):
    try: return datetime.fromisoformat(f"{p.get('date') or today()}T{p.get('start_time') or '00:00'}").replace(tzinfo=KST)
    except Exception: return now()

CSS='''<style>body{margin:0;background:#071023;color:#f5f8ff;font-family:Arial,"Malgun Gothic",sans-serif;font-weight:700}.wrap{max-width:1100px;margin:0 auto;padding:16px}.panel,.card{background:#111b34;border:1px solid #2e3d62;border-radius:20px;padding:16px;margin:14px 0}input,select,textarea{width:100%;padding:13px;margin:6px 0 12px;background:#081126;color:#fff;border:1px solid #344466;border-radius:12px;font-size:16px}.btn,button{display:inline-block;padding:10px 14px;border-radius:12px;background:#4d6bff;color:#fff;text-decoration:none;border:0;font-weight:900;margin:3px}.ok{background:#18bf66}.gray{background:#465373}.danger{background:#ef4444}.slot{display:flex;justify-content:space-between;background:#081126;border:1px solid #26365c;border-radius:14px;padding:12px;margin:8px 0}.tag{background:#24345f;border-radius:999px;padding:6px 10px;margin-right:4px}.notice{background:#3a3017;color:#ffe08a;border:1px solid #7f6a2b;border-radius:12px;padding:10px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.chat{height:320px;overflow:auto}.pill{display:inline-block;background:#22345e;border-radius:999px;padding:8px 12px;margin:4px}@media(max-width:850px){.grid{grid-template-columns:1fr}.slot{display:block}}</style>'''
HEAD='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>월하 · 연가 · 연희 파티모집</title>'''+CSS+'''<script>function fmt(v){v=(v||'').replace(/[^0-9]/g,'').slice(0,4);return v.length>=3?v.slice(0,v.length-2)+':'+v.slice(v.length-2):v}document.addEventListener('input',e=>{if(e.target.name=='start_time'||e.target.name=='end_time')e.target.value=fmt(e.target.value)});function mode(){let c=document.querySelector('[name=category]');if(!c)return;document.querySelectorAll('.place').forEach(x=>x.style.display=x.dataset.cat==c.value?'block':'none');let s=document.getElementById('slotsBox');if(s)s.style.display=c.value=='사냥'?'block':'none'}document.addEventListener('DOMContentLoaded',()=>{let c=document.querySelector('[name=category]');if(c){c.onchange=mode;mode()}});let n=0;function addSlot(){let j=document.getElementById('slotJob').value;let d=document.createElement('div');d.className='slot';d.innerHTML='<b>'+j+'</b><input type="hidden" name="slot_job_'+n+'" value="'+j+'"><button type="button" class="danger" onclick="this.parentElement.remove()">삭제</button>';document.getElementById('slots').appendChild(d);n++}</script></head><body><div class="wrap">'''
TAIL='</div></body></html>'

def need_login():
    d=load(); u=current_user(d)
    return d,u

@app.route('/')
def index():
    d,u=need_login()
    if not approved(u): return redirect('/register')
    cat=request.args.get('cat','전체')
    posts=d['posts'] if cat=='전체' else [p for p in d['posts'] if p.get('category')==cat]
    posts=sorted(posts,key=lambda p:(p.get('closed',False), pdt(p)))
    schedule=sorted([p for p in d['posts'] if p.get('category')=='파밍' and not p.get('closed')], key=pdt)[:8]
    out=[HEAD, f'<h1>⚔ {SITE_TITLE}</h1><p>버전 {APP_VERSION} · {esc(clabel(sel_char(u)))}</p><p><a class="btn ok" href="/new">+ 모집글</a><a class="btn gray" href="/chars">내 캐릭터</a>']
    if admin(u): out.append('<a class="btn gray" href="/admin">관리자</a>')
    out.append('<a class="btn gray" href="/logout">로그아웃</a></p><div class="panel">')
    for c in CATEGORIES: out.append(f'<a class="btn {"ok" if c==cat else "gray"}" href="/?cat={c}">{c}</a>')
    out.append('</div><div class="grid"><div class="panel"><h2>📅 오늘 일정</h2>')
    if schedule:
        for p in schedule: out.append(f'<div class="slot"><div><b>{esc(p["place"])}</b><br>{esc(p.get("date"))} · {show_time(p.get("start_time"))}</div><b>{show_time(p.get("start_time"))}</b></div>')
    else: out.append('<p>등록된 파밍 일정 없음</p>')
    out.append('</div><div class="panel"><h2>💬 통합채팅</h2><div class="chat">')
    for m in d['global_chat'][-30:]: out.append(f'<div class="notice"><b>{esc(m.get("name"))}</b><br>{esc(m.get("text"))}<br>{esc(m.get("time"))}</div>')
    out.append('</div><form method="post" action="/global_chat"><input name="text" placeholder="메시지"><button>전송</button></form></div></div><h2>📌 모집글</h2>')
    for p in posts: out.append(render_post(p,u,d))
    if not posts: out.append('<div class="panel">현재 모집글이 없습니다.</div>')
    out.append(TAIL); return ''.join(out)

def render_post(p,u,d):
    out=[f'<div class="card" style="opacity:{0.55 if p.get("closed") else 1}"><span class="tag">{esc("마감" if p.get("closed") else "모집중")}</span><span class="tag">{esc(p.get("category"))}</span><b style="float:right">{joined(p)}/{maxcnt(p)}</b><h2>{esc(p.get("place"))}</h2><p>📍 채널 {esc(p.get("channel"))} · ⏰ {esc(p.get("date"))} · {show_time(p.get("start_time"))} ~ {show_time(p.get("end_time"))}</p><p>👑 {esc(p.get("owner_label"))} · {esc(p.get("created"))}</p>']
    if p.get('memo'): out.append(f'<div class="notice">{esc(p.get("memo"))}</div>')
    if p.get('category')=='사냥':
        for i,s in enumerate(p.get('slots',[])):
            occ=s.get('uid') or s.get('external'); mine=s.get('uid')==(u or {}).get('id')
            out.append(f'<div class="slot"><div><b>{esc(s.get("job"))}</b><br>{esc(s.get("label") or s.get("external") or "모집중")}</div><div>')
            if not p.get('closed'):
                if mine: out.append(f'<a class="btn gray" href="/leave_slot/{p["id"]}/{i}">취소</a>')
                elif not occ: out.append(f'<a class="btn ok" href="/join_slot/{p["id"]}/{i}">참여</a>')
                if admin(u) and not occ: out.append(f'<a class="btn gray" href="/external_slot/{p["id"]}/{i}">외부인</a>')
            out.append('</div></div>')
    else:
        out.append('<h3>참여자</h3>')
        if p.get('participants'):
            for x in p['participants']: out.append(f'<span class="pill">{esc(x.get("label"))}</span>')
        else: out.append('<p>아직 참여자가 없습니다.</p>')
        if not p.get('closed'): out.append(f'<a class="btn ok" style="width:100%;text-align:center" href="/participate/{p["id"]}">참여하기</a>')
        if p.get('category')=='파밍' and (admin(u) or p.get('owner_uid')==u.get('id')):
            out.append(f'<form method="post" action="/farm_result/{p["id"]}"><h3>파밍 결과</h3><select name="farm_result"><option>노득</option><option {"selected" if p.get("farm_result")=="득템" else ""}>득템</option></select><select name="farm_item">')
            for it in d['settings']['farm_items']: out.append(f'<option {"selected" if p.get("farm_item")==it else ""}>{esc(it)}</option>')
            out.append(f'</select><input name="sale_amount" value="{esc(p.get("sale_amount"))}" placeholder="판매금액"><button class="ok">저장</button></form>')
    out.append(f'<p><a class="btn" href="/chat/{p["id"]}">채팅 {len(p.get("chat",[]))}</a>')
    if admin(u) or p.get('owner_uid')==u.get('id'): out.append(f'<a class="btn ok" href="/close/{p["id"]}">모집완료</a><a class="btn gray" href="/edit/{p["id"]}">수정</a><a class="btn danger" href="/delete/{p["id"]}">삭제</a>')
    out.append('</p></div>'); return ''.join(out)

@app.route('/register', methods=['GET','POST'])
def register():
    d=load()
    if request.method=='POST':
        account=request.form.get('account','').strip(); name=request.form.get('char_name','').strip(); job=request.form.get('job','검성')
        if not account or not name: return form_register('계정명과 캐릭터명을 입력하세요.')
        uid,cid=nid(),nid(); first=len(d['users'])==0
        d['users'].append({'id':uid,'account':account,'status':'approved' if first else 'pending','role':'최고관리자' if first else '일반','selected_char_id':cid,'chars':[{'id':cid,'name':name,'job':job,'status':'approved' if first else 'pending'}]})
        save(d); session['uid']=uid; return redirect('/')
    return form_register('')
def form_register(err):
    opts=''.join(f'<option>{j}</option>' for j in JOBS); msg=f'<div class="notice">{esc(err)}</div>' if err else ''
    return HEAD+f'<div class="panel"><h1>문파원 등록</h1><form method="post"><label>계정명</label><input name="account"><label>대표 캐릭터명</label><input name="char_name"><label>직업</label><select name="job">{opts}</select><button class="ok">승인 요청</button></form>{msg}</div>'+TAIL
@app.route('/logout')
def logout(): session.clear(); return redirect('/register')

@app.route('/new')
def new_post():
    d,u=need_login()
    if not approved(u): return redirect('/register')
    cats=['사냥','600퀘']+(['파밍'] if admin(u) else [])
    opts=''.join(f'<option>{c}</option>' for c in cats)
    places=''.join(f'<div class="place" data-cat="{cat}"><label>장소</label><select name="place_{cat}">'+''.join(f'<option>{p}</option>' for p in arr)+'</select></div>' for cat,arr in PLACES.items())
    jobs=''.join(f'<option>{j}</option>' for j in JOBS)
    return HEAD+f'<div class="panel"><a class="btn gray" href="/">← 메인</a><h1>모집글 올리기</h1><form method="post" action="/create"><label>종류</label><select name="category">{opts}</select>{places}<label>채널</label><input name="channel"><label>날짜</label><input type="date" name="date" value="{today()}"><label>시작시간</label><select name="start_period"><option>오전</option><option>오후</option></select><input name="start_time" placeholder="1107"><label>종료시간</label><select name="end_period"><option>오전</option><option>오후</option></select><input name="end_time" placeholder="1120"><label>메모</label><textarea name="memo"></textarea><div id="slotsBox" class="panel"><h2>사냥 직업 자리 추가</h2><select id="slotJob">{jobs}</select><button type="button" class="ok" onclick="addSlot()">추가</button><div id="slots"></div></div><button class="ok">등록</button></form></div>'+TAIL

@app.route('/create',methods=['POST'])
def create():
    d,u=need_login(); c=sel_char(u)
    if not c: return redirect('/chars')
    cat=request.form.get('category','사냥')
    if cat=='파밍' and not admin(u): return redirect('/')
    slots=[]
    if cat=='사냥':
        for i in range(20):
            job=request.form.get(f'slot_job_{i}')
            if job: slots.append({'job':job,'uid':'','char_id':'','label':'','external':''})
    p={'id':nid(),'category':cat,'place':request.form.get(f'place_{cat}',''),'channel':digits(request.form.get('channel')),'date':request.form.get('date') or today(),'start_time':to24(request.form.get('start_period'),request.form.get('start_time')),'end_time':to24(request.form.get('end_period'),request.form.get('end_time')),'memo':request.form.get('memo',''),'owner_uid':u['id'],'owner_label':clabel(c),'created':stamp(),'closed':False,'slots':slots,'participants':[],'chat':[],'farm_result':'','farm_item':'','sale_amount':''}
    d['posts'].append(p); save(d); return redirect('/')

@app.route('/join_slot/<pid>/<int:i>')
def join_slot(pid,i):
    d,u=need_login(); c=sel_char(u); p=find_post(d,pid)
    if c and p and p.get('category')=='사냥' and not p.get('closed'):
        for s in p['slots']:
            if s.get('uid')==u['id']: s.update({'uid':'','char_id':'','label':''})
        if 0<=i<len(p['slots']) and not p['slots'][i].get('uid') and not p['slots'][i].get('external'):
            p['slots'][i].update({'uid':u['id'],'char_id':c['id'],'label':clabel(c)})
        save(d)
    return redirect('/')
@app.route('/leave_slot/<pid>/<int:i>')
def leave_slot(pid,i):
    d,u=need_login(); p=find_post(d,pid)
    if p and 0<=i<len(p['slots']) and (p['slots'][i].get('uid')==u['id'] or admin(u)):
        p['slots'][i].update({'uid':'','char_id':'','label':'','external':''}); save(d)
    return redirect('/')
@app.route('/external_slot/<pid>/<int:i>',methods=['GET','POST'])
def external_slot(pid,i):
    d,u=need_login(); p=find_post(d,pid)
    if not admin(u): return redirect('/')
    if request.method=='POST':
        name=request.form.get('name','').strip()
        if p and name and 0<=i<len(p['slots']): p['slots'][i].update({'external':name,'label':name,'uid':'','char_id':''}); save(d)
        return redirect('/')
    return HEAD+f'<div class="panel"><form method="post"><input name="name" placeholder="외부인 이름"><button>저장</button></form></div>'+TAIL
@app.route('/participate/<pid>')
def participate(pid):
    d,u=need_login(); c=sel_char(u); p=find_post(d,pid)
    if c and p and p.get('category') in ['600퀘','파밍'] and not p.get('closed'):
        if p['category']!='600퀘' or len(p['participants'])<10:
            if not any(x.get('uid')==u['id'] for x in p['participants']): p['participants'].append({'uid':u['id'],'char_id':c['id'],'label':clabel(c)})
            save(d)
    return redirect('/')
@app.route('/close/<pid>')
def close(pid):
    d,u=need_login(); p=find_post(d,pid)
    if p and (p.get('owner_uid')==u['id'] or admin(u)): p['closed']=True; save(d)
    return redirect('/')
@app.route('/delete/<pid>')
def delete(pid):
    d,u=need_login(); d['posts']=[p for p in d['posts'] if not (p['id']==pid and (p.get('owner_uid')==u['id'] or admin(u)))]; save(d); return redirect('/')
@app.route('/edit/<pid>',methods=['GET','POST'])
def edit(pid):
    d,u=need_login(); p=find_post(d,pid)
    if not p or not (p.get('owner_uid')==u['id'] or admin(u)): return redirect('/')
    if request.method=='POST':
        p['channel']=digits(request.form.get('channel')); p['date']=request.form.get('date') or today(); p['start_time']=to24(request.form.get('start_period'),request.form.get('start_time')); p['end_time']=to24(request.form.get('end_period'),request.form.get('end_time')); p['memo']=request.form.get('memo',''); save(d); return redirect('/')
    sp,st=split12(p.get('start_time')); ep,et=split12(p.get('end_time'))
    return HEAD+f'<div class="panel"><form method="post"><label>채널</label><input name="channel" value="{esc(p.get("channel"))}"><label>날짜</label><input type="date" name="date" value="{esc(p.get("date") or today())}"><label>시작</label><select name="start_period"><option {"selected" if sp=="오전" else ""}>오전</option><option {"selected" if sp=="오후" else ""}>오후</option></select><input name="start_time" value="{st}"><label>종료</label><select name="end_period"><option {"selected" if ep=="오전" else ""}>오전</option><option {"selected" if ep=="오후" else ""}>오후</option></select><input name="end_time" value="{et}"><textarea name="memo">{esc(p.get("memo"))}</textarea><button>저장</button></form></div>'+TAIL
@app.route('/farm_result/<pid>',methods=['POST'])
def farm_result(pid):
    d,u=need_login(); p=find_post(d,pid)
    if p and (admin(u) or p.get('owner_uid')==u['id']): p.update({'farm_result':request.form.get('farm_result',''),'farm_item':request.form.get('farm_item',''),'sale_amount':request.form.get('sale_amount','')}); save(d)
    return redirect('/')
@app.route('/global_chat',methods=['POST'])
def global_chat():
    d,u=need_login(); c=sel_char(u); txt=request.form.get('text','').strip()
    if c and txt: d['global_chat'].append({'name':clabel(c),'text':txt,'time':stamp()}); d['global_chat']=d['global_chat'][-100:]; save(d)
    return redirect('/')
@app.route('/chat/<pid>',methods=['GET','POST'])
def chat(pid):
    d,u=need_login(); c=sel_char(u); p=find_post(d,pid)
    if not p: return redirect('/')
    if request.method=='POST':
        txt=request.form.get('text','').strip()
        if c and txt: p['chat'].append({'name':clabel(c),'text':txt,'time':stamp()}); save(d)
        return redirect(f'/chat/{pid}')
    out=[HEAD,'<div class="panel"><a class="btn gray" href="/">← 메인</a><h1>채팅</h1>']
    for m in p['chat']: out.append(f'<div class="notice"><b>{esc(m.get("name"))}</b><br>{esc(m.get("text"))}</div>')
    out.append('<form method="post"><input name="text"><button>전송</button></form></div>'+TAIL); return ''.join(out)
@app.route('/chars',methods=['GET','POST'])
def chars_page():
    d,u=need_login()
    if not approved(u): return redirect('/register')
    if request.method=='POST':
        name=request.form.get('name','').strip(); job=request.form.get('job','검성')
        if name: u['chars'].append({'id':nid(),'name':name,'job':job,'status':'pending'}); save(d)
        return redirect('/chars')
    opts=''.join(f'<option>{j}</option>' for j in JOBS); out=[HEAD,'<div class="panel"><a class="btn gray" href="/">← 메인</a><h1>내 캐릭터</h1>']
    for c in u['chars']: out.append(f'<div class="slot"><div><b>{esc(c["name"])}({esc(c["job"])})</b><br>{esc(c["status"])}</div><a class="btn ok" href="/select_char/{c["id"]}">선택</a></div>')
    out.append(f'<form method="post"><input name="name" placeholder="캐릭터명"><select name="job">{opts}</select><button>추가</button></form></div>'+TAIL); return ''.join(out)
@app.route('/select_char/<cid>')
def select_char(cid):
    d,u=need_login(); u['selected_char_id']=cid; save(d); return redirect('/chars')
@app.route('/admin')
def admin_page():
    d,u=need_login()
    if not admin(u): return redirect('/')
    out=[HEAD,'<div class="panel"><a class="btn gray" href="/">← 메인</a><h1>관리자</h1>']
    for x in d['users']:
        out.append(f'<div class="slot"><div><b>{esc(x.get("account"))}</b><br>{esc(x.get("status"))} / {esc(x.get("role"))}</div><div><a class="btn ok" href="/admin/approve/{x["id"]}">승인</a><a class="btn gray" href="/admin/role/{x["id"]}/관리자">관리자</a><a class="btn gray" href="/admin/role/{x["id"]}/최고관리자">최고</a></div></div>')
    out.append('</div>'+TAIL); return ''.join(out)
@app.route('/admin/approve/<uid>')
def admin_approve(uid):
    d,u=need_login()
    if not admin(u): return redirect('/')
    for x in d['users']:
        if x['id']==uid: x['status']='approved'; [c.update({'status':'approved'}) for c in x.get('chars',[])]
    save(d); return redirect('/admin')
@app.route('/admin/role/<uid>/<role>')
def admin_role(uid,role):
    d,u=need_login()
    if not admin(u): return redirect('/')
    for x in d['users']:
        if x['id']==uid: x['role']=role
    save(d); return redirect('/admin')
@app.route('/health')
def health(): return {'ok':True,'version':APP_VERSION}
if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT','7777')))
