
from flask import Flask, request, redirect, session, render_template_string
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, uuid, re, html

APP_VERSION = "v21.4"
APP_TITLE = "월하 · 연가 · 연희 파티모집"
KST = ZoneInfo("Asia/Seoul")
DATA_PATH = Path(os.environ.get("DATA_PATH", "data.json"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v21-secret")

JOBS = ["전사","검객","검제","검황","검성","도적","자객","진검","귀검","태성","주술사","술사","현사","현인","현자","도사","도인","명인","진인","진선","기타"]
JOB_GROUPS = {
    "전사 계열": ["전사","검객","검제","검황","검성"],
    "도적 계열": ["도적","자객","진검","귀검","태성"],
    "주술사 계열": ["주술사","술사","현사","현인","현자"],
    "도사 계열": ["도사","도인","명인","진인","진선"],
    "기타": ["기타"],
}
CATEGORIES = ["전체","사냥","600퀘","파밍"]
PLACES = {
    "사냥": ["도삭산 900층", "흉노", "선비", "북방", "기타"],
    "600퀘": ["600퀘", "기타"],
    "파밍": ["해골왕", "흑룡", "묵룡", "진룡", "기타"],
}

CSS = """
:root{
  --bg:#060b18;
  --bg2:#0a1224;
  --panel:#111b34;
  --panel2:#0c152b;
  --line:#2b3d66;
  --line2:#3e5aa0;
  --text:#f5f8ff;
  --muted:#9fb0d1;
  --blue:#5d78ff;
  --green:#19c46f;
  --red:#ef4444;
  --gold:#f6d36b;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:
    radial-gradient(circle at top left, rgba(93,120,255,.18), transparent 34%),
    radial-gradient(circle at top right, rgba(25,196,111,.10), transparent 28%),
    linear-gradient(180deg,#060b18,#081126 55%,#050914);
  color:var(--text);
  font-family:Arial,'Malgun Gothic',sans-serif;
  font-weight:700;
}
.wrap{max-width:1180px;margin:0 auto;padding:18px}
.header{
  padding:22px 18px;
  margin:0 0 16px;
  border:1px solid var(--line);
  border-radius:24px;
  background:linear-gradient(135deg,rgba(93,120,255,.22),rgba(17,27,52,.92));
  box-shadow:0 18px 40px rgba(0,0,0,.28);
}
.header h1{margin:0;font-size:30px;letter-spacing:-.5px}
.sub,.meta{color:var(--muted);font-size:14px}
.panel,.card{
  background:linear-gradient(180deg,rgba(17,27,52,.96),rgba(10,18,36,.96));
  border:1px solid var(--line);
  border-radius:22px;
  padding:18px;
  margin:14px 0;
  box-shadow:0 14px 32px rgba(0,0,0,.24);
}
.card{position:relative;overflow:hidden}
.card:before{
  content:"";
  position:absolute;
  left:0;top:0;bottom:0;width:5px;
  background:linear-gradient(180deg,var(--blue),var(--green));
}
.card h2,.panel h2{margin-top:8px}
input,select,textarea{
  width:100%;
  background:#081126;
  border:1px solid #344466;
  color:var(--text);
  border-radius:14px;
  padding:13px;
  font-size:16px;
  font-weight:800;
  outline:none;
}
input:focus,select:focus,textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(93,120,255,.16)}
label{display:block;margin:12px 0 6px;color:#c9d7ff}
.btn,button{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  background:linear-gradient(180deg,#647dff,#4d66ee);
  color:#fff;
  border:0;
  border-radius:14px;
  padding:11px 15px;
  text-decoration:none;
  font-weight:900;
  cursor:pointer;
  box-shadow:0 8px 18px rgba(0,0,0,.22);
}
.btn:hover,button:hover{filter:brightness(1.08)}
.ok{background:linear-gradient(180deg,#22d983,#16b966)!important}
.danger{background:linear-gradient(180deg,#ff5b5b,#e23d3d)!important}
.gray{background:linear-gradient(180deg,#586783,#43506c)!important}
.toolbar{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
.slot{
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  background:rgba(8,17,38,.92);
  border:1px solid #26365c;
  border-radius:17px;
  padding:13px;
  margin:10px 0;
}
.slot b{font-size:16px}
.mini{padding:8px 12px;border-radius:12px;font-size:14px}
.tag{
  display:inline-flex;
  align-items:center;
  background:#24345f;
  border:1px solid rgba(255,255,255,.05);
  border-radius:999px;
  padding:7px 11px;
  margin-right:5px;
  font-size:13px;
}
.tag.ok{background:rgba(25,196,111,.22);border-color:rgba(25,196,111,.35)}
.count{
  float:right;
  border:1px solid var(--line2);
  background:rgba(93,120,255,.12);
  border-radius:999px;
  padding:8px 13px;
  color:#dbe5ff;
}
.notice{
  background:rgba(246,211,107,.13);
  border:1px solid rgba(246,211,107,.28);
  color:#ffe7a1;
  border-radius:14px;
  padding:12px;
  margin:12px 0;
}
.closed{opacity:.55;filter:grayscale(.35)}
.time-row{display:grid;grid-template-columns:95px 1fr;gap:8px}
.dash{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.chatbox{
  height:280px;
  overflow:auto;
  background:#081126;
  border:1px solid #26365c;
  border-radius:16px;
  padding:12px;
}
.chatmsg{background:#1a2748;border-radius:12px;padding:10px;margin:8px 0}
.pill{display:inline-flex;background:#22345e;border-radius:999px;padding:8px 12px;margin:4px}
.full{width:100%;margin-top:10px}
.empty{text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:16px;padding:24px}
.place{animation:fadeIn .15s ease}
select optgroup{background:#142141;color:#9fbbff;font-weight:900}
select option{background:#081126;color:#f5f8ff}
#slotJob,select[name='job']{border-color:#5d78ff;box-shadow:0 0 0 2px rgba(93,120,255,.13)}
@keyframes fadeIn{from{opacity:.25;transform:translateY(3px)}to{opacity:1;transform:none}}
@media(max-width:800px){
  .wrap{padding:10px}
  .dash{grid-template-columns:1fr}
  .header h1{font-size:24px}
  .slot{flex-direction:column;align-items:flex-start}
  .time-row{grid-template-columns:88px 1fr}
  .toolbar .btn,.toolbar button{flex:1}
}
"""

def now():
    return datetime.now(KST)

def today():
    return now().strftime("%Y-%m-%d")

def now_text():
    return now().strftime("%m/%d %H:%M")

def nid():
    return str(uuid.uuid4())

def h(x):
    return html.escape(str(x or ""))


def job_select(name="job", selected="", element_id=""):
    id_attr = f" id='{h(element_id)}'" if element_id else ""
    out = [f"<select name='{h(name)}'{id_attr}>"]
    for group, jobs in JOB_GROUPS.items():
        out.append(f"<optgroup label='{h(group)}'>")
        for job in jobs:
            sel = " selected" if job == selected else ""
            out.append(f"<option value='{h(job)}'{sel}>{h(job)}</option>")
        out.append("</optgroup>")
    out.append("</select>")
    return "".join(out)

def digits(x, n=4):
    return re.sub(r"\D", "", str(x or ""))[:n]

def clean_time(x):
    s = re.sub(r"[^0-9:]", "", str(x or "").replace("：", ":"))
    if not s:
        return ""
    try:
        if ":" in s:
            a, b = s.split(":", 1)
            hh, mm = int(a), int((b + "00")[:2])
        elif len(s) <= 2:
            hh, mm = int(s), 0
        elif len(s) == 3:
            hh, mm = int(s[0]), int(s[1:])
        else:
            hh, mm = int(s[:2]), int(s[2:4])
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return f"{hh:02d}:{mm:02d}"
    except Exception:
        return ""
    return ""

def to24(period, value):
    t = clean_time(value)
    if not t:
        return ""
    hh, mm = map(int, t.split(":"))
    if period == "오후" and hh < 12:
        hh += 12
    if period == "오전" and hh == 12:
        hh = 0
    return f"{hh:02d}:{mm:02d}"

def split12(value):
    t = clean_time(value)
    if not t:
        return "오전", ""
    hh, mm = map(int, t.split(":"))
    p = "오후" if hh >= 12 else "오전"
    h12 = hh % 12 or 12
    return p, f"{h12:02d}:{mm:02d}"

def show_time(value):
    p, t = split12(value)
    return f"{p} {t}" if t else "시간 미정"

def empty_data():
    return {"users": [], "posts": [], "global_chat": [], "settings": {"farm_items": ["해뼈","흑룡","묵룡","진룡"]}}

def normalize(d):
    d.setdefault("users", [])
    d.setdefault("posts", [])
    d.setdefault("global_chat", [])
    d.setdefault("settings", {}).setdefault("farm_items", ["해뼈","흑룡","묵룡","진룡"])
    for u in d["users"]:
        u.setdefault("id", nid())
        u.setdefault("account", "")
        u.setdefault("status", "pending")
        u.setdefault("role", "일반")
        u.setdefault("chars", [])
        for c in u["chars"]:
            c.setdefault("id", nid())
            c.setdefault("name", "")
            c.setdefault("job", "기타")
            c.setdefault("status", "pending")
        if "selected_char_id" not in u and u["chars"]:
            u["selected_char_id"] = u["chars"][0]["id"]
    for p in d["posts"]:
        p.setdefault("id", nid())
        p.setdefault("category", "사냥")
        p.setdefault("place", "")
        p.setdefault("channel", "")
        p.setdefault("date", today())
        p.setdefault("start_time", "")
        p.setdefault("end_time", "")
        p.setdefault("memo", "")
        p.setdefault("owner_uid", "")
        p.setdefault("owner_label", "")
        p.setdefault("created", now_text())
        p.setdefault("closed", False)
        p.setdefault("slots", [])
        p.setdefault("participants", [])
        p.setdefault("chat", [])
        p.setdefault("farm_result", "")
        p.setdefault("farm_item", "")
        p.setdefault("sale_amount", "")
        for s in p["slots"]:
            s.setdefault("job", "")
            s.setdefault("uid", "")
            s.setdefault("label", "")
            s.setdefault("external", "")
    return d

def load():
    if not DATA_PATH.exists():
        d = empty_data()
        save(d)
        return d
    try:
        return normalize(json.loads(DATA_PATH.read_text(encoding="utf-8")))
    except Exception:
        return empty_data()

def save(d):
    d = normalize(d)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True) if DATA_PATH.parent != Path(".") else None
    tmp = DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_PATH)

def cur_user(d=None):
    d = d or load()
    uid = session.get("uid")
    for u in d["users"]:
        if u["id"] == uid:
            return u
    return None

def approved(u):
    return bool(u and u.get("status") == "approved")

def is_admin(u):
    return bool(u and u.get("role") in ["관리자","부문파장","문파장","최고관리자"])

def selected_char(u):
    if not u:
        return None
    cs = [c for c in u.get("chars", []) if c.get("status") == "approved"]
    if not cs:
        return None
    sid = u.get("selected_char_id")
    for c in cs:
        if c["id"] == sid:
            return c
    return cs[0]

def char_label(c):
    return f"{c.get('name','')}({c.get('job','')})" if c else ""

def find_post(d, pid):
    for p in d["posts"]:
        if p["id"] == pid:
            return p
    return None

def joined_count(p):
    if p["category"] == "사냥":
        return sum(1 for s in p["slots"] if s.get("uid") or s.get("external"))
    return len(p["participants"])

def max_count(p):
    if p["category"] == "사냥":
        return len(p["slots"])
    if p["category"] == "600퀘":
        return 10
    return max(len(p["participants"]), 0)

BASE_HEAD = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{{ title }}</title><style>{{ css }}</style></head><body><div class='wrap'>"""
BASE_TAIL = """</div><script>
let slotN=0;
function qs(s){return document.querySelector(s)}
function fmt(v){v=(v||'').replace(/[^0-9]/g,'').slice(0,4);return v.length>=3?v.slice(0,v.length-2)+':'+v.slice(v.length-2):v}
function addSlot(){let j=(qs('#slotJob')||document.querySelector("select[name='slotJob']"))?.value,b=qs('#slots');if(!j||!b)return;let d=document.createElement('div');d.className='slot';d.innerHTML='<b>'+j+'</b><input type=hidden name=slot_job_'+slotN+' value=\"'+j+'\"><button type=button class=\"danger mini\" onclick=\"this.parentElement.remove()\">삭제</button>';b.appendChild(d);slotN++}
function mode(){let c=qs('#cat')?.value;document.querySelectorAll('.place').forEach(x=>x.style.display=x.dataset.cat==c?'':'none');let s=qs('#slotsBox');if(s)s.style.display=c=='사냥'?'':'none'}
document.addEventListener('DOMContentLoaded',()=>{let c=qs('#cat');if(c){c.onchange=mode;mode()}document.querySelectorAll('input[name=start_time],input[name=end_time]').forEach(i=>i.oninput=()=>i.value=fmt(i.value))});
</script></body></html>"""

def render(page, **kw):
    kw.setdefault("title", APP_TITLE)
    kw.setdefault("css", CSS)
    kw.update(dict(app_version=APP_VERSION, jobs=JOBS, job_select=job_select, categories=CATEGORIES, places=PLACES, show_time=show_time, joined_count=joined_count, max_count=max_count, is_admin=is_admin, selected_char=selected_char, char_label=char_label, today=today))
    return render_template_string(BASE_HEAD + page + BASE_TAIL, **kw)

@app.route("/")
def index():
    d = load()
    u = cur_user(d)
    if not approved(u):
        return redirect("/register")
    cat = request.args.get("cat", "전체")
    posts = d["posts"]
    if cat != "전체":
        posts = [p for p in posts if p["category"] == cat]
    sched = [p for p in d["posts"] if p["category"] == "파밍" and not p.get("closed")]
    return render(T_INDEX, d=d, u=u, c=selected_char(u), cat=cat, posts=posts, sched=sched)

T_INDEX = """
<header class='header'><h1>⚔ 월하 · 연가 · 연희 파티모집</h1><div class='sub'>{{ app_version }} · {{ char_label(c) }}</div></header>
<div class='toolbar'><a class='btn ok' href='/new'>+ 모집글</a><a class='btn gray' href='/chars'>내 캐릭터</a>{% if is_admin(u) %}<a class='btn gray' href='/admin'>관리자</a>{% endif %}<a class='btn gray' href='/logout'>로그아웃</a></div>
<section class='panel'><div class='toolbar'>{% for x in categories %}<a class='btn {{ "ok" if x==cat else "gray" }} mini' href='/?cat={{x}}'>{{x}}</a>{% endfor %}</div></section>
<div class='dash'>
<section class='panel'><h2>📅 오늘 일정</h2><div class='notice'>파밍 30분 · 15분 · 5분 전 알림 기준</div>{% for p in sched %}<div class='slot'><div><b>{{p.place}}</b><br><span class='meta'>{{p.date}} · {{show_time(p.start_time)}}</span></div></div>{% else %}<div class='empty'>등록된 파밍 일정 없음</div>{% endfor %}</section>
<section class='panel'><h2>💬 통합채팅</h2><div class='chatbox'>{% for m in d.global_chat[-30:] %}<div class='chatmsg'><b>{{m.name}}</b><br>{{m.text}}<br><span class='meta'>{{m.time}}</span></div>{% else %}<div class='empty'>메시지 없음</div>{% endfor %}</div><form class='toolbar' method='post' action='/global_chat'><input name='text' placeholder='메시지'><button>전송</button></form></section>
</div>
<h2>📌 모집글</h2>
{% for p in posts %}
<section class='card {{ "closed" if p.closed else "" }}'>
<span class='tag ok'>{{ "마감" if p.closed else "모집중" }}</span><span class='tag'>{{p.category}}</span><span class='count'>{{joined_count(p)}}/{{max_count(p)}}</span>
<h2>{{p.place}}</h2><div class='meta'>📍 채널 {{p.channel}} · ⏰ {{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}}</div><div class='meta'>👑 {{p.owner_label}} · {{p.created}}</div>
{% if p.memo %}<div class='notice'>{{p.memo}}</div>{% endif %}
{% if p.category == "사냥" %}
  {% for s in p.slots %}
  <div class='slot'><div><b>{{s.job}}</b><br>{{s.label or s.external or "모집중"}}</div><div class='toolbar'>{% if not p.closed %}{% if s.uid==u.id %}<a class='btn mini gray' href='/leave_slot/{{p.id}}/{{loop.index0}}'>취소</a>{% elif not s.uid and not s.external %}<a class='btn mini ok' href='/join_slot/{{p.id}}/{{loop.index0}}'>참여</a>{% if is_admin(u) %}<a class='btn mini gray' href='/external_slot/{{p.id}}/{{loop.index0}}'>외부인</a>{% endif %}{% endif %}{% endif %}</div></div>
  {% endfor %}
{% else %}
  <h3>참여자</h3>{% for a in p.participants %}<span class='pill'>{{a.label}}</span>{% else %}<p class='meta'>아직 참여자 없음</p>{% endfor %}
  {% if not p.closed %}<a class='btn ok full' href='/participate/{{p.id}}'>참여하기</a>{% endif %}
{% endif %}
<div class='toolbar'>{% if p.owner_uid==u.id or is_admin(u) %}<a class='btn ok' href='/close/{{p.id}}'>모집완료</a><a class='btn gray' href='/edit/{{p.id}}'>수정</a><a class='btn danger' href='/delete/{{p.id}}'>삭제</a>{% endif %}<a class='btn gray' href='/chat/{{p.id}}'>채팅 {{p.chat|length}}</a></div>
</section>
{% else %}<div class='empty'>모집글 없음</div>{% endfor %}
"""

@app.route("/register", methods=["GET","POST"])
def register():
    d = load()
    if request.method == "POST":
        acc = request.form.get("account","").strip()
        name = request.form.get("char_name","").strip()
        job = request.form.get("job","검성")
        if not acc or not name:
            return render(T_REGISTER, error="계정명과 캐릭터명을 입력하세요.", form=request.form)
        uid, cid = nid(), nid()
        first = len(d["users"]) == 0
        d["users"].append({"id":uid,"account":acc,"status":"approved" if first else "pending","role":"최고관리자" if first else "일반","selected_char_id":cid,"chars":[{"id":cid,"name":name,"job":job,"status":"approved" if first else "pending"}]})
        save(d)
        session["uid"] = uid
        return redirect("/")
    return render(T_REGISTER, error="", form={})

T_REGISTER = """
<section class='panel'><h1>👤 문파원 등록</h1><form method='post'><label>계정명</label><input name='account' value='{{form.get("account","")}}'><label>대표 캐릭터명</label><input name='char_name' value='{{form.get("char_name","")}}'><label>직업</label>{{ job_select('job')|safe }}<button class='ok full'>승인 요청</button></form>{% if error %}<div class='notice'>{{error}}</div>{% endif %}</section>
"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/register")

@app.route("/new")
def new_post():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/register")
    cats = ["사냥","600퀘"] + (["파밍"] if is_admin(u) else [])
    return render(T_NEW, cats=cats)

T_NEW = """
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>모집글 올리기</h1><form method='post' action='/create'><label>종류</label><select name='category' id='cat'>{% for c in cats %}<option>{{c}}</option>{% endfor %}</select>{% for cat, arr in places.items() %}<div class='place' data-cat='{{cat}}'><label>장소</label><select name='place_{{cat}}'>{% for p in arr %}<option>{{p}}</option>{% endfor %}</select></div>{% endfor %}<label>채널</label><input name='channel' maxlength='4'><label>날짜</label><input name='date' type='date' value='{{today()}}'><label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' maxlength='5' placeholder='1107'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option>오후</option></select><input name='end_time' maxlength='5' placeholder='1120'></div><label>메모</label><textarea name='memo'></textarea><section class='panel' id='slotsBox'><h2>사냥 직업 자리 추가</h2><div class='notice'>직업 선택 후 추가를 누르면 모집 자리가 생성됩니다.</div><div class='notice'>전사/도적/주술사/도사 계열 1~4차 기준입니다. 과 는 제외했습니다.</div><div class='toolbar'>{{ job_select('slotJob', '', 'slotJob')|safe }}<button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slots'></div></section><div class='notice'>600퀘/파밍은 참여 버튼 방식입니다.</div><button class='ok full'>등록</button></form></section>
"""

@app.route("/create", methods=["POST"])
def create():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/register")
    c=selected_char(u)
    cat=request.form.get("category","사냥")
    if cat=="파밍" and not is_admin(u): return redirect("/")
    slots=[]
    if cat=="사냥":
        for i in range(20):
            job=request.form.get(f"slot_job_{i}")
            if job: slots.append({"job":job,"uid":"","label":"","external":""})
    d["posts"].append({"id":nid(),"category":cat,"place":request.form.get(f"place_{cat}",""),"channel":digits(request.form.get("channel"),4),"date":request.form.get("date") or today(),"start_time":to24(request.form.get("start_period"),request.form.get("start_time")),"end_time":to24(request.form.get("end_period"),request.form.get("end_time")),"memo":request.form.get("memo",""),"owner_uid":u["id"],"owner_label":char_label(c),"created":now_text(),"closed":False,"slots":slots,"participants":[],"chat":[]})
    save(d); return redirect("/")

@app.route("/join_slot/<pid>/<int:i>")
def join_slot(pid,i):
    d=load(); u=cur_user(d); c=selected_char(u)
    p=find_post(d,pid)
    if p and c and p["category"]=="사냥" and not p.get("closed"):
        for s in p["slots"]:
            if s.get("uid")==u["id"]: s.update({"uid":"","label":""})
        if 0<=i<len(p["slots"]) and not p["slots"][i].get("uid") and not p["slots"][i].get("external"):
            p["slots"][i].update({"uid":u["id"],"label":char_label(c)})
        save(d)
    return redirect("/")

@app.route("/leave_slot/<pid>/<int:i>")
def leave_slot(pid,i):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if p and 0<=i<len(p["slots"]) and (p["slots"][i].get("uid")==u["id"] or is_admin(u)):
        p["slots"][i].update({"uid":"","label":"","external":""}); save(d)
    return redirect("/")

@app.route("/external_slot/<pid>/<int:i>", methods=["GET","POST"])
def external_slot(pid,i):
    d=load(); u=cur_user(d)
    if not is_admin(u): return redirect("/")
    if request.method=="POST":
        p=find_post(d,pid); name=request.form.get("name","").strip()
        if p and 0<=i<len(p["slots"]):
            p["slots"][i].update({"uid":"","label":name,"external":name}); save(d)
        return redirect("/")
    return render("<section class='panel'><h1>외부인 추가</h1><form method='post'><input name='name'><button class='ok full'>저장</button></form></section>")

@app.route("/participate/<pid>")
def participate(pid):
    d=load(); u=cur_user(d); c=selected_char(u); p=find_post(d,pid)
    if p and c and p["category"] in ["600퀘","파밍"] and not p.get("closed"):
        if p["category"]!="600퀘" or len(p["participants"])<10:
            if not any(a.get("uid")==u["id"] for a in p["participants"]):
                p["participants"].append({"uid":u["id"],"label":char_label(c)}); save(d)
    return redirect("/")

@app.route("/edit/<pid>", methods=["GET","POST"])
def edit(pid):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if not p or not (p["owner_uid"]==u["id"] or is_admin(u)): return redirect("/")
    if request.method=="POST":
        p["channel"]=digits(request.form.get("channel"),4); p["date"]=request.form.get("date") or today(); p["start_time"]=to24(request.form.get("start_period"),request.form.get("start_time")); p["end_time"]=to24(request.form.get("end_period"),request.form.get("end_time")); p["memo"]=request.form.get("memo",""); save(d); return redirect("/")
    sp,st=split12(p.get("start_time")); ep,et=split12(p.get("end_time"))
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>수정</h1><form method='post'><label>채널</label><input name='channel' value='{{p.channel}}'><label>날짜</label><input name='date' type='date' value='{{p.date}}'><label>시작시간</label><div class='time-row'><select name='start_period'><option {% if sp=='오전' %}selected{% endif %}>오전</option><option {% if sp=='오후' %}selected{% endif %}>오후</option></select><input name='start_time' value='{{st}}'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option {% if ep=='오전' %}selected{% endif %}>오전</option><option {% if ep=='오후' %}selected{% endif %}>오후</option></select><input name='end_time' value='{{et}}'></div><label>메모</label><textarea name='memo'>{{p.memo}}</textarea><button class='ok full'>저장</button></form></section>", p=p,sp=sp,st=st,ep=ep,et=et)

@app.route("/close/<pid>")
def close(pid):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if p and (p["owner_uid"]==u["id"] or is_admin(u)): p["closed"]=True; save(d)
    return redirect("/")

@app.route("/delete/<pid>")
def delete(pid):
    d=load(); u=cur_user(d)
    d["posts"]=[p for p in d["posts"] if not (p["id"]==pid and (p["owner_uid"]==u["id"] or is_admin(u)))]
    save(d); return redirect("/")

@app.route("/global_chat", methods=["POST"])
def global_chat():
    d=load(); u=cur_user(d); c=selected_char(u); txt=request.form.get("text","").strip()
    if txt and c:
        d["global_chat"].append({"name":char_label(c),"text":txt,"time":now_text()}); d["global_chat"]=d["global_chat"][-100:]; save(d)
    return redirect("/")

@app.route("/chat/<pid>", methods=["GET","POST"])
def chat(pid):
    d=load(); u=cur_user(d); c=selected_char(u); p=find_post(d,pid)
    if not p: return redirect("/")
    if request.method=="POST":
        txt=request.form.get("text","").strip()
        if txt and c: p["chat"].append({"name":char_label(c),"text":txt,"time":now_text()}); save(d)
        return redirect(f"/chat/{pid}")
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>채팅</h1><div class='chatbox'>{% for m in p.chat %}<div class='chatmsg'><b>{{m.name}}</b><br>{{m.text}}</div>{% else %}<div class='empty'>메시지 없음</div>{% endfor %}</div><form method='post' class='toolbar'><input name='text'><button>전송</button></form></section>", p=p)

@app.route("/chars", methods=["GET","POST"])
def chars():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/register")
    if request.method=="POST":
        name=request.form.get("name","").strip(); job=request.form.get("job","검성")
        if name: u["chars"].append({"id":nid(),"name":name,"job":job,"status":"pending"}); save(d)
        return redirect("/chars")
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>내 캐릭터</h1>{% for c in u.chars %}<div class='slot'><div><b>{{c.name}}({{c.job}})</b><br>{{c.status}}</div>{% if c.status=='approved' %}<a class='btn mini ok' href='/select_char/{{c.id}}'>선택</a>{% endif %}</div>{% endfor %}<form method='post'><h2>추가</h2><input name='name'>{{ job_select('job')|safe }}<button class='ok'>추가</button></form></section>", u=u)

@app.route("/select_char/<cid>")
def select_char(cid):
    d=load(); u=cur_user(d)
    if u: u["selected_char_id"]=cid; save(d)
    return redirect("/chars")

@app.route("/admin")
def admin():
    d=load(); u=cur_user(d)
    if not is_admin(u): return redirect("/")
    pending=[x for x in d["users"] if x["status"]=="pending"]
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>관리자</h1><h2>가입 승인</h2>{% for x in pending %}<div class='slot'><b>{{x.account}}</b><a class='btn mini ok' href='/admin/approve/{{x.id}}'>승인</a></div>{% else %}<p class='meta'>대기 없음</p>{% endfor %}<h2>권한</h2>{% for x in users %}<div class='slot'><div><b>{{x.account}}</b><br>{{x.status}} / {{x.role}}</div><div class='toolbar'><a class='btn mini gray' href='/admin/role/{{x.id}}/일반'>일반</a><a class='btn mini gray' href='/admin/role/{{x.id}}/관리자'>관리자</a><a class='btn mini gray' href='/admin/role/{{x.id}}/최고관리자'>최고</a></div></div>{% endfor %}</section>", users=d["users"], pending=pending)

@app.route("/admin/approve/<uid>")
def approve(uid):
    d=load(); u=cur_user(d)
    if is_admin(u):
        for x in d["users"]:
            if x["id"]==uid:
                x["status"]="approved"
                for c in x["chars"]: c["status"]="approved"
        save(d)
    return redirect("/admin")

@app.route("/admin/role/<uid>/<role>")
def role(uid,role):
    d=load(); u=cur_user(d)
    if is_admin(u):
        for x in d["users"]:
            if x["id"]==uid: x["role"]=role
        save(d)
    return redirect("/admin")

@app.route("/health")
def health():
    return {"ok": True, "version": APP_VERSION}

if __name__ == "__main__":
    port = int(os.environ.get("PORT","7777"))
    app.run(host="0.0.0.0", port=port)
