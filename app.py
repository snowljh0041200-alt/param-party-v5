
from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime
from zoneinfo import ZoneInfo
import os,json,uuid,re
APP_VERSION='v20.0'; SITE_TITLE='월하 · 연가 · 연희 파티모집'; DATA_FILE=os.environ.get('DATA_FILE','data/data.json'); KST=ZoneInfo('Asia/Seoul')
app=Flask(__name__); app.secret_key=os.environ.get('SECRET_KEY','baram-party-v20-secret')
JOBS=['검성','검신','검황','진선','도사','전사','도적','주술사','궁사','기타']; CATEGORIES=['전체','사냥','600퀘','파밍']
PLACES={'사냥':['도삭산 900층','흉노','선비','북방','일본','기타'],'600퀘':['600퀘','기타'],'파밍':['해골왕','흑룡','묵룡','진룡','기타']}
def now(): return datetime.now(KST)
def today(): return now().strftime('%Y-%m-%d')
def text_now(): return now().strftime('%m/%d %H:%M')
def new_id(): return str(uuid.uuid4())
def digits(v,n=4): return re.sub(r'\D','',str(v or ''))[:n]
def clean_time(v):
    s=re.sub(r'[^0-9:]','',str(v or '').replace('：',':'))
    if not s: return ''
    try:
        if ':' in s:
            a,b=s.split(':',1); h=int(a); m=int((b+'00')[:2])
        elif len(s)<=2: h=int(s); m=0
        elif len(s)==3: h=int(s[0]); m=int(s[1:])
        else: h=int(s[:2]); m=int(s[2:4])
        return f'{h:02d}:{m:02d}' if 0<=h<=23 and 0<=m<=59 else ''
    except Exception: return ''
def to_24(period,value):
    t=clean_time(value)
    if not t: return ''
    h,m=map(int,t.split(':'))
    if period=='오후' and h<12: h+=12
    if period=='오전' and h==12: h=0
    return f'{h:02d}:{m:02d}'
def split_12(value):
    t=clean_time(value)
    if not t: return '오전',''
    h,m=map(int,t.split(':')); p='오후' if h>=12 else '오전'; h12=h%12 or 12
    return p,f'{h12:02d}:{m:02d}'
def show_time(v):
    p,t=split_12(v); return f'{p} {t}' if t else '시간 미정'
def parse_dt(p):
    try: return datetime.fromisoformat(f"{p.get('date') or today()}T{p.get('start_time') or '00:00'}").replace(tzinfo=KST)
    except Exception: return now()
def empty_data(): return {'users':[],'posts':[],'global_chat':[],'settings':{'farm_items':['해뼈','흑룡','묵룡','진룡']}}
def normalize(d):
    d.setdefault('users',[]); d.setdefault('posts',[]); d.setdefault('global_chat',[]); d.setdefault('settings',{}).setdefault('farm_items',['해뼈','흑룡','묵룡','진룡'])
    for u in d['users']:
        u.setdefault('id',new_id()); u.setdefault('account',''); u.setdefault('status','pending'); u.setdefault('role','일반'); u.setdefault('chars',[])
        if 'selected_char_id' not in u and u['chars']: u['selected_char_id']=u['chars'][0].get('id')
        for c in u['chars']:
            c.setdefault('id',new_id()); c.setdefault('name',''); c.setdefault('job','기타'); c.setdefault('status','pending')
    for p in d['posts']:
        p.setdefault('id',new_id()); p.setdefault('category','사냥'); p.setdefault('place',''); p.setdefault('channel',''); p.setdefault('date',p.get('start_date',today()))
        p.setdefault('start_time',''); p.setdefault('end_time',''); p.setdefault('memo',''); p.setdefault('owner_uid',''); p.setdefault('owner_label',''); p.setdefault('created',text_now()); p.setdefault('closed',False)
        p.setdefault('slots',[]); p.setdefault('participants',[]); p.setdefault('chat',[]); p.setdefault('farm_result',''); p.setdefault('farm_item',''); p.setdefault('sale_amount','')
        for s in p['slots']:
            s.setdefault('job',''); s.setdefault('uid',''); s.setdefault('char_id',''); s.setdefault('label',''); s.setdefault('external','')
    return d
def load_data():
    path=Path(DATA_FILE); path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        d=empty_data(); save_data(d); return d
    try:
        with open(path,'r',encoding='utf-8') as f: return normalize(json.load(f))
    except Exception: return empty_data()
def save_data(d):
    d=normalize(d); path=Path(DATA_FILE); path.parent.mkdir(parents=True,exist_ok=True); tmp=str(path)+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    os.replace(tmp,path)
def current_user(d=None):
    d=d or load_data(); uid=session.get('uid')
    return next((u for u in d['users'] if u.get('id')==uid),None)
def approved(u): return bool(u and u.get('status')=='approved')
def is_admin(u): return bool(u and u.get('role') in ['관리자','부문파장','문파장','최고관리자'])
def selected_char(u):
    cs=[c for c in (u or {}).get('chars',[]) if c.get('status')=='approved']
    if not cs: return None
    return next((c for c in cs if c.get('id')==u.get('selected_char_id')),cs[0])
def label_char(c): return f"{c.get('name','')}({c.get('job','')})" if c else ''
def find_post(d,pid): return next((p for p in d['posts'] if p.get('id')==pid),None)
def post_status(p): return '마감' if p.get('closed') else '모집중'
def joined_count(p): return sum(1 for s in p.get('slots',[]) if s.get('uid') or s.get('external')) if p.get('category')=='사냥' else len(p.get('participants',[]))
def max_count(p): return len(p.get('slots',[])) if p.get('category')=='사냥' else (10 if p.get('category')=='600퀘' else max(len(p.get('participants',[])),0))
@app.context_processor
def inject(): return dict(app_version=APP_VERSION,site_title=SITE_TITLE,jobs=JOBS,categories=CATEGORIES,places=PLACES,show_time=show_time,parse_dt=parse_dt,post_status=post_status,joined_count=joined_count,max_count=max_count,is_admin=is_admin,selected_char=selected_char,label_char=label_char,today=today)
@app.route('/')
def index():
    d=load_data(); u=current_user(d)
    if not approved(u): return redirect('/register')
    cat=request.args.get('cat','전체'); posts=d['posts'] if cat=='전체' else [p for p in d['posts'] if p.get('category')==cat]
    posts=sorted(posts,key=lambda p:(p.get('closed',False),parse_dt(p))); schedule=sorted([p for p in d['posts'] if p.get('category')=='파밍' and not p.get('closed')],key=parse_dt)[:8]
    return render_template('index.html',d=d,u=u,cat=cat,posts=posts,schedule=schedule)
@app.route('/register',methods=['GET','POST'])
def register():
    d=load_data()
    if request.method=='POST':
        account=request.form.get('account','').strip(); name=request.form.get('char_name','').strip(); job=request.form.get('job','검성')
        if not account or not name: return render_template('register.html',error='계정명과 캐릭터명을 입력하세요.',form=request.form)
        uid,cid=new_id(),new_id(); first=len(d['users'])==0
        d['users'].append({'id':uid,'account':account,'status':'approved' if first else 'pending','role':'최고관리자' if first else '일반','selected_char_id':cid,'chars':[{'id':cid,'name':name,'job':job,'status':'approved' if first else 'pending'}]})
        save_data(d); session['uid']=uid; return redirect('/')
    return render_template('register.html',error='',form={})
@app.route('/logout')
def logout(): session.clear(); return redirect('/register')
@app.route('/chars',methods=['GET','POST'])
def chars_page():
    d=load_data(); u=current_user(d)
    if not approved(u): return redirect('/register')
    if request.method=='POST':
        name=request.form.get('name','').strip(); job=request.form.get('job','검성')
        if name: u['chars'].append({'id':new_id(),'name':name,'job':job,'status':'pending'}); save_data(d)
        return redirect('/chars')
    return render_template('chars.html',u=u)
@app.route('/select_char/<cid>')
def select_char(cid):
    d=load_data(); u=current_user(d)
    if u: u['selected_char_id']=cid; save_data(d)
    return redirect('/chars')
@app.route('/new')
def new_post():
    d=load_data(); u=current_user(d)
    if not approved(u): return redirect('/register')
    cats=['사냥','600퀘']+(['파밍'] if is_admin(u) else [])
    return render_template('new.html',u=u,cats=cats)
@app.route('/create',methods=['POST'])
def create_post():
    d=load_data(); u=current_user(d)
    if not approved(u): return redirect('/register')
    c=selected_char(u); cat=request.form.get('category','사냥')
    if not c: return redirect('/chars')
    if cat=='파밍' and not is_admin(u): return redirect('/')
    slots=[]
    if cat=='사냥':
        for i in range(20):
            job=request.form.get(f'slot_job_{i}')
            if job: slots.append({'job':job,'uid':'','char_id':'','label':'','external':''})
    p={'id':new_id(),'category':cat,'place':request.form.get(f'place_{cat}',''),'channel':digits(request.form.get('channel'),4),'date':request.form.get('date') or today(),'start_time':to_24(request.form.get('start_period'),request.form.get('start_time')),'end_time':to_24(request.form.get('end_period'),request.form.get('end_time')),'memo':request.form.get('memo','').strip(),'owner_uid':u['id'],'owner_label':label_char(c),'created':text_now(),'closed':False,'slots':slots,'participants':[],'chat':[],'farm_result':'','farm_item':'','sale_amount':''}
    d['posts'].append(p); save_data(d); return redirect('/')
@app.route('/join_slot/<pid>/<int:idx>')
def join_slot(pid,idx):
    d=load_data(); u=current_user(d); c=selected_char(u)
    if not c: return redirect('/')
    p=find_post(d,pid)
    if not p or p.get('category')!='사냥' or p.get('closed'): return redirect('/')
    for s in p['slots']:
        if s.get('uid')==u['id']: s.update({'uid':'','char_id':'','label':''})
    if 0<=idx<len(p['slots']):
        s=p['slots'][idx]
        if not s.get('uid') and not s.get('external'): s.update({'uid':u['id'],'char_id':c['id'],'label':label_char(c)})
    save_data(d); return redirect('/')
@app.route('/leave_slot/<pid>/<int:idx>')
def leave_slot(pid,idx):
    d=load_data(); u=current_user(d); p=find_post(d,pid)
    if p and p.get('category')=='사냥' and 0<=idx<len(p['slots']):
        s=p['slots'][idx]
        if s.get('uid')==u['id'] or is_admin(u): s.update({'uid':'','char_id':'','label':'','external':''}); save_data(d)
    return redirect('/')
@app.route('/external_slot/<pid>/<int:idx>',methods=['GET','POST'])
def external_slot(pid,idx):
    d=load_data(); u=current_user(d)
    if not is_admin(u): return redirect('/')
    p=find_post(d,pid)
    if not p: return redirect('/')
    if request.method=='POST':
        name=request.form.get('name','').strip()
        if name and 0<=idx<len(p['slots']): p['slots'][idx].update({'uid':'','char_id':'','label':name,'external':name}); save_data(d)
        return redirect('/')
    return render_template('simple_form.html',title='외부인 추가',field='name',placeholder='외부인 이름')
@app.route('/participate/<pid>')
def participate(pid):
    d=load_data(); u=current_user(d); c=selected_char(u)
    if not c: return redirect('/')
    p=find_post(d,pid)
    if not p or p.get('closed') or p.get('category') not in ['600퀘','파밍']: return redirect('/')
    if p['category']=='600퀘' and len(p['participants'])>=10: return redirect('/')
    if not any(x.get('uid')==u['id'] for x in p['participants']): p['participants'].append({'uid':u['id'],'char_id':c['id'],'label':label_char(c)}); save_data(d)
    return redirect('/')
@app.route('/edit/<pid>',methods=['GET','POST'])
def edit_post(pid):
    d=load_data(); u=current_user(d); p=find_post(d,pid)
    if not p or not (p.get('owner_uid')==u.get('id') or is_admin(u)): return redirect('/')
    if request.method=='POST':
        p['channel']=digits(request.form.get('channel'),4); p['date']=request.form.get('date') or today(); p['start_time']=to_24(request.form.get('start_period'),request.form.get('start_time')); p['end_time']=to_24(request.form.get('end_period'),request.form.get('end_time')); p['memo']=request.form.get('memo','').strip(); save_data(d); return redirect('/')
    sp,st=split_12(p.get('start_time')); ep,et=split_12(p.get('end_time')); return render_template('edit.html',p=p,sp=sp,st=st,ep=ep,et=et)
@app.route('/close/<pid>')
def close_post(pid):
    d=load_data(); u=current_user(d); p=find_post(d,pid)
    if p and (p.get('owner_uid')==u.get('id') or is_admin(u)): p['closed']=True; save_data(d)
    return redirect('/')
@app.route('/delete/<pid>')
def delete_post(pid):
    d=load_data(); u=current_user(d); d['posts']=[p for p in d['posts'] if not (p['id']==pid and (p.get('owner_uid')==u.get('id') or is_admin(u)))]; save_data(d); return redirect('/')
@app.route('/farm_result/<pid>',methods=['POST'])
def farm_result(pid):
    d=load_data(); u=current_user(d); p=find_post(d,pid)
    if p and p.get('category')=='파밍' and (p.get('owner_uid')==u.get('id') or is_admin(u)): p['farm_result']=request.form.get('farm_result',''); p['farm_item']=request.form.get('farm_item',''); p['sale_amount']=request.form.get('sale_amount',''); save_data(d)
    return redirect('/')
@app.route('/global_chat',methods=['POST'])
def global_chat():
    d=load_data(); u=current_user(d); c=selected_char(u); text=request.form.get('text','').strip()
    if text and c: d['global_chat'].append({'name':label_char(c),'text':text,'time':text_now()}); d['global_chat']=d['global_chat'][-100:]; save_data(d)
    return redirect('/')
@app.route('/chat/<pid>',methods=['GET','POST'])
def party_chat(pid):
    d=load_data(); u=current_user(d); c=selected_char(u); p=find_post(d,pid)
    if not p: return redirect('/')
    if request.method=='POST':
        text=request.form.get('text','').strip()
        if text and c: p['chat'].append({'name':label_char(c),'text':text,'time':text_now()}); save_data(d)
        return redirect(f'/chat/{pid}')
    return render_template('chat.html',p=p)
@app.route('/admin')
def admin():
    d=load_data(); u=current_user(d)
    if not is_admin(u): return redirect('/')
    pending_users=[x for x in d['users'] if x.get('status')=='pending']; pending_chars=[]
    for user in d['users']:
        for ch in user['chars']:
            if ch.get('status')=='pending': pending_chars.append({'user':user,'char':ch})
    return render_template('admin.html',users=d['users'],pending_users=pending_users,pending_chars=pending_chars)
@app.route('/admin/approve_user/<uid>')
def approve_user(uid):
    d=load_data(); u=current_user(d)
    if not is_admin(u): return redirect('/')
    for x in d['users']:
        if x['id']==uid: x['status']='approved'; [c.update({'status':'approved'}) for c in x['chars']]
    save_data(d); return redirect('/admin')
@app.route('/admin/approve_char/<uid>/<cid>')
def approve_char(uid,cid):
    d=load_data(); u=current_user(d)
    if not is_admin(u): return redirect('/')
    for x in d['users']:
        if x['id']==uid:
            for c in x['chars']:
                if c['id']==cid: c['status']='approved'
    save_data(d); return redirect('/admin')
@app.route('/admin/role/<uid>/<role>')
def set_role(uid,role):
    d=load_data(); u=current_user(d)
    if not is_admin(u): return redirect('/')
    if role not in ['일반','관리자','부문파장','문파장','최고관리자']: return redirect('/admin')
    for x in d['users']:
        if x['id']==uid: x['role']=role
    save_data(d); return redirect('/admin')
@app.route('/health')
def health(): return jsonify({'ok':True,'version':APP_VERSION})
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','7777')))
