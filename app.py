
from flask import Flask, request, redirect, session, render_template_string
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, uuid, re, html

APP_VERSION = "v22.2"
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
  --bg:#050914;
  --bg-soft:#091225;
  --panel:#101a31;
  --panel-2:#0b1326;
  --card:#0e1930;
  --line:#263a64;
  --line-soft:#1d2d4d;
  --text:#f4f7ff;
  --muted:#96a7c8;
  --blue:#5874ff;
  --blue2:#3d5df0;
  --green:#19c46f;
  --green2:#0ea85a;
  --red:#ef4444;
  --gray:#43506d;
  --gold:#f4d47a;
}
*{box-sizing:border-box}
body{
  margin:0;
  color:var(--text);
  background:
    radial-gradient(circle at 15% 0%, rgba(88,116,255,.14), transparent 28%),
    radial-gradient(circle at 90% 10%, rgba(25,196,111,.09), transparent 24%),
    linear-gradient(180deg,#050914 0%,#071023 55%,#050914 100%);
  font-family:Arial,'Malgun Gothic',sans-serif;
  font-weight:700;
}
.wrap{max-width:1240px;margin:0 auto;padding:16px}
.header{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:16px;
  padding:18px 4px 14px;
  border-bottom:1px solid rgba(255,255,255,.08);
  margin-bottom:14px;
}
.header h1{margin:0;font-size:28px;letter-spacing:-.7px}
.sub,.meta{color:var(--muted);font-size:13px}
.panel,.card{
  background:linear-gradient(180deg,rgba(16,26,49,.96),rgba(9,18,37,.96));
  border:1px solid var(--line-soft);
  border-radius:20px;
  padding:16px;
  margin:12px 0;
  box-shadow:0 14px 34px rgba(0,0,0,.24);
}
.card{
  position:relative;
  overflow:hidden;
  transition:.15s ease;
}
.card:hover{border-color:#3c5590;transform:translateY(-1px)}
.card:before{
  content:"";
  position:absolute;
  left:0;top:0;bottom:0;width:4px;
  background:linear-gradient(180deg,var(--blue),var(--green));
}
.card h2{margin:10px 0 7px;font-size:25px;letter-spacing:-.6px}
.panel h2{margin:0 0 10px;font-size:20px}
input,select,textarea{
  width:100%;
  background:#081126;
  border:1px solid #304466;
  color:var(--text);
  border-radius:13px;
  padding:12px 13px;
  font-size:15px;
  font-weight:800;
  outline:none;
}
input:focus,select:focus,textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(88,116,255,.15)}
label{display:block;margin:12px 0 6px;color:#c5d4ff;font-size:14px}
.btn,button{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  gap:6px;
  color:#fff;
  border:1px solid rgba(255,255,255,.08);
  border-radius:13px;
  padding:10px 14px;
  background:linear-gradient(180deg,var(--blue),var(--blue2));
  text-decoration:none;
  font-weight:900;
  cursor:pointer;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 8px 18px rgba(0,0,0,.22);
}
.btn:hover,button:hover{filter:brightness(1.08)}
.ok{background:linear-gradient(180deg,#24d985,var(--green2))!important}
.danger{background:linear-gradient(180deg,#ff5b5b,#df3636)!important}
.gray{background:linear-gradient(180deg,#56637e,#3d4863)!important}
.mini{padding:8px 11px;border-radius:11px;font-size:13px}
.full{width:100%;margin-top:10px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.app-shell{
  display:grid;
  grid-template-columns:minmax(0,1fr) 360px;
  gap:16px;
  align-items:start;
}
.left-stack{min-width:0}
.side-stack{position:sticky;top:12px}
.summary-grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:10px;
  margin:12px 0;
}
.summary-card{
  background:linear-gradient(180deg,rgba(15,27,53,.96),rgba(7,16,34,.96));
  border:1px solid var(--line-soft);
  border-radius:18px;
  padding:15px;
}
.summary-card strong{display:block;font-size:26px;margin-top:6px}
.summary-card span{color:var(--muted);font-size:13px}
.quickbar{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:10px;
  margin:12px 0;
}
.category-bar{display:flex;gap:8px;flex-wrap:wrap}
.slot{
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  background:rgba(8,17,38,.88);
  border:1px solid #23375f;
  border-radius:16px;
  padding:13px;
  margin:9px 0;
}
.slot b{font-size:16px}
.slot .meta{margin-top:3px}
.tag{
  display:inline-flex;
  align-items:center;
  background:#203156;
  border:1px solid rgba(255,255,255,.05);
  border-radius:999px;
  padding:6px 10px;
  margin-right:5px;
  font-size:12px;
}
.tag.ok{background:rgba(25,196,111,.18);border-color:rgba(25,196,111,.32);color:#9ff5c7}
.count{
  float:right;
  border:1px solid #3d5693;
  background:rgba(88,116,255,.12);
  border-radius:999px;
  padding:8px 12px;
  color:#dce5ff;
  font-weight:900;
}
.notice{
  background:rgba(244,212,122,.12);
  border:1px solid rgba(244,212,122,.25);
  color:#ffe5a0;
  border-radius:13px;
  padding:11px;
  margin:10px 0;
}
.closed{opacity:.55;filter:grayscale(.35)}
.time-row{display:grid;grid-template-columns:95px 1fr;gap:8px}
.chatbox{
  height:440px;
  overflow:auto;
  background:#081126;
  border:1px solid #23375f;
  border-radius:16px;
  padding:10px;
}
.chatmsg{background:#182744;border-radius:12px;padding:10px;margin:8px 0}
.chatmsg b{color:#dce5ff}
.pill{
  display:inline-flex;
  align-items:center;
  gap:5px;
  background:#22345e;
  border:1px solid rgba(255,255,255,.05);
  border-radius:999px;
  padding:7px 10px;
  margin:4px;
}
.empty{
  text-align:center;
  color:var(--muted);
  border:1px dashed var(--line);
  border-radius:16px;
  padding:22px;
}
.online-panel{padding:14px 16px}
.online-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
.online-head h2{margin:0;font-size:18px}
.online-list{display:flex;gap:7px;flex-wrap:wrap}
.online-pill{background:rgba(25,196,111,.14);border:1px solid rgba(25,196,111,.3)}
.online-pill small{margin-left:5px;color:var(--gold);font-size:11px}
.schedule-row{
  display:flex;
  justify-content:space-between;
  gap:10px;
  background:#081126;
  border:1px solid #23375f;
  border-radius:14px;
  padding:11px;
  margin:8px 0;
}
.actions{
  display:flex;
  gap:7px;
  flex-wrap:wrap;
  margin-top:12px;
}
.place{animation:fadeIn .12s ease}
select optgroup{background:#142141;color:#9fbbff;font-weight:900}
select option{background:#081126;color:#f5f8ff}
#slotJob,select[name='job']{border-color:#5874ff;box-shadow:0 0 0 2px rgba(88,116,255,.12)}
@keyframes fadeIn{from{opacity:.3;transform:translateY(3px)}to{opacity:1;transform:none}}

.closed{opacity:.62!important;filter:grayscale(.45)!important;background:linear-gradient(180deg,rgba(71,79,99,.72),rgba(37,44,60,.72))!important}
.closed-tag{background:rgba(239,68,68,.22)!important;border-color:rgba(239,68,68,.5)!important;color:#ffb4b4!important;font-weight:900}
.remain{color:#ffe189}
.farm-box{margin-top:12px;padding:12px;border:1px solid #263a64;border-radius:16px;background:rgba(8,17,38,.55)}
.farm-tools{margin-top:8px}

.farm-head{display:flex;justify-content:space-between;align-items:center;gap:10px}
.farm-head h3{margin:0}
.farm-summary{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
.farm-summary span{background:#081126;border:1px solid #23375f;border-radius:12px;padding:10px;color:#9fb0d1}
.farm-summary b{display:block;color:#fff;margin-top:4px}
.farm-dist{background:rgba(244,212,122,.12);border:1px solid rgba(244,212,122,.24);border-radius:12px;padding:10px;color:#ffe5a0;margin:8px 0}
.farm-form{display:grid;grid-template-columns:120px 1fr 1fr 86px;gap:8px;margin-top:10px}
.farm-form button{width:100%}
@media(max-width:720px){.farm-form{grid-template-columns:1fr}.farm-summary{grid-template-columns:1fr}}
@media(max-width:980px){
  .app-shell{grid-template-columns:1fr}
  .side-stack{position:static}
  .summary-grid{grid-template-columns:1fr 1fr 1fr}
  .chatbox{height:300px}
}
@media(max-width:720px){
  .wrap{padding:10px}
  .header{display:block}
  .header h1{font-size:23px}
  .summary-grid{grid-template-columns:1fr}
  .quickbar{display:block}
  .category-bar{margin-top:10px}
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
        u.setdefault("last_seen", "")
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


def touch_online():
    d = load()
    if farm_alert_tick(d):
        save(d)
    u = cur_user(d)
    if not u:
        return
    u["last_seen"] = now().isoformat(timespec="seconds")
    save(d)

def online_users(d):
    result = []
    cutoff = now().timestamp() - 300
    for u in d.get("users", []):
        if u.get("status") != "approved":
            continue
        last = u.get("last_seen", "")
        try:
            ts = datetime.fromisoformat(last).timestamp()
        except Exception:
            ts = 0
        if ts >= cutoff:
            c = selected_char(u)
            result.append({
                "account": u.get("account",""),
                "label": char_label(c) if c else u.get("account",""),
                "role": u.get("role","일반")
            })
    return result

@app.before_request
def update_last_seen():
    if request.endpoint in ["health"]:
        return
    try:
        d = load()
        u = cur_user(d)
        if u and u.get("status") == "approved":
            u["last_seen"] = now().isoformat(timespec="seconds")
            save(d)
    except Exception:
        pass



def base_line(job):
    warrior = ["전사","검객","검제","검황","검성"]
    rogue = ["도적","자객","진검","귀검","태성"]
    mage = ["주술사","술사","현사","현인","현자"]
    priest = ["도사","도인","명인","진인","진선"]
    for group in [warrior, rogue, mage, priest]:
        if job in group:
            return group[0]
    return job

def compatible_job(slot_job, char_job):
    # 같은 계열만 참여 가능. 예: 검성 자리에는 전사 계열만 가능, 진선 자리에는 도사 계열만 가능
    return base_line(slot_job) == base_line(char_job)

def approved_chars(u):
    return [c for c in (u or {}).get("chars", []) if c.get("status") == "approved"]

def post_datetime(p):
    try:
        return datetime.fromisoformat(f"{p.get('date') or today()}T{p.get('start_time') or '00:00'}").replace(tzinfo=KST)
    except Exception:
        return now()

def remaining_text(p):
    dt = post_datetime(p)
    diff = dt - now()
    minutes = int(diff.total_seconds() // 60)
    if minutes > 0:
        return f"{minutes}분 남음"
    if minutes > -60:
        return "진행중"
    return "종료"

def farm_alert_tick(d):
    changed = False
    for p in d.get("posts", []):
        if p.get("category") != "파밍" or p.get("closed"):
            continue
        sent = p.setdefault("alert_sent", [])
        dt = post_datetime(p)
        left = int((dt - now()).total_seconds() // 60)
        for target in [30, 15, 5]:
            key = str(target)
            if left <= target and left >= target - 1 and key not in sent:
                msg = f"🔔 {p.get('place','파밍')} 젠 {target}분 전입니다. 채널 {p.get('channel','')}"
                d.setdefault("global_chat", []).append({"name":"알림","text":msg,"time":now_text()})
                d["global_chat"] = d["global_chat"][-100:]
                sent.append(key)
                changed = True
    return changed

def farm_distribution(p):
    try:
        amount = int(re.sub(r"[^0-9]", "", str(p.get("sale_amount","") or "0")))
    except Exception:
        amount = 0
    early = p.get("early_ids", [])
    late = p.get("late_ids", [])
    early_w = float(p.get("early_weight", "1.0") or "1.0")
    late_w = float(p.get("late_weight", "0.88") or "0.88")
    total_w = len(early) * early_w + len(late) * late_w
    if amount <= 0 or total_w <= 0:
        return {"early_each":0, "late_each":0, "amount":amount}
    return {
        "early_each": int(amount * early_w / total_w),
        "late_each": int(amount * late_w / total_w),
        "amount": amount
    }


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
    kw.update(dict(app_version=APP_VERSION, jobs=JOBS, job_select=job_select, categories=CATEGORIES, places=PLACES, show_time=show_time, farm_distribution=farm_distribution, remaining_text=remaining_text, approved_chars=approved_chars, compatible_job=compatible_job, joined_count=joined_count, max_count=max_count, is_admin=is_admin, selected_char=selected_char, char_label=char_label, today=today))
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
    return render(T_INDEX, d=d, u=u, c=selected_char(u), cat=cat, posts=posts, sched=sched, online=online_users(d))

T_INDEX = """
<header class='header'>
  <div>
    <h1>⚔ 월하 · 연가 · 연희</h1>
    <div class='sub'>{{ app_version }} · {{ char_label(c) }}</div>
  </div>
  <div class='toolbar'>
    <a class='btn ok' href='/new'>＋ 모집글 작성</a>
    <a class='btn gray' href='/chars'>내 캐릭터</a>
    {% if is_admin(u) %}<a class='btn gray' href='/admin'>관리자</a>{% endif %}
    <a class='btn gray' href='/logout'>로그아웃</a>
  </div>
</header>

<div class='summary-grid'>
  <div class='summary-card'><span>오늘 파밍</span><strong>{{ sched|length }}</strong></div>
  <div class='summary-card'><span>진행중 모집</span><strong>{{ posts|selectattr('closed','equalto',False)|list|length }}</strong></div>
  <div class='summary-card'><span>내 캐릭터</span><strong>{{ u.chars|selectattr('status','equalto','approved')|list|length }}</strong></div>
</div>

<div class='app-shell'>
  <main class='left-stack'>
    <div class='quickbar'>
      <h2>📌 모집글</h2>
      <div class='category-bar'>
        {% for x in categories %}
          <a class='btn {{ "ok" if x==cat else "gray" }} mini' href='/?cat={{x}}'>{{x}}</a>
        {% endfor %}
      </div>
    </div>

    {% for p in posts %}
    <section class='card {{ "closed" if p.closed else "" }}'>
      <span class='tag {{ "closed-tag" if p.closed else "ok" }}'>{{ "마감" if p.closed else "모집중" }}</span>
      <span class='tag'>{{p.category}}</span>
      <span class='count'>{{joined_count(p)}}/{{max_count(p)}}</span>
      <h2>{{p.place}}</h2>
      <div class='meta'>📍 {{p.channel}}채널 · ⏰ {{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}}{% if p.category=="파밍" %} · <b class='remain'>{{ remaining_text(p) }}</b>{% endif %}</div>
      <div class='meta'>👑 {{p.owner_label}} · {{p.created}}</div>
      {% if p.memo %}<div class='notice'>{{p.memo}}</div>{% endif %}

      {% if p.category == "사냥" %}
        {% for s in p.slots %}
        <div class='slot'>
          <div>
            <b>{{s.job}}</b>
            <div class='meta'>{{s.label or s.external or "모집중"}}</div>
          </div>
          <div class='toolbar'>
            {% if not p.closed %}
              {% if s.uid==u.id %}
                <a class='btn mini gray' href='/leave_slot/{{p.id}}/{{loop.index0}}'>취소</a>
              {% elif not s.uid and not s.external %}
                <a class='btn mini ok' href='/choose_slot/{{p.id}}/{{loop.index0}}'>참여</a>
                {% if is_admin(u) %}<a class='btn mini gray' href='/external_slot/{{p.id}}/{{loop.index0}}'>외부</a>{% endif %}
              {% endif %}
            {% endif %}
          </div>
        </div>
        {% endfor %}
      {% else %}
        <h3>참여자</h3>
        {% for a in p.participants %}
          <span class='pill'>{{a.label}}</span>
        {% else %}
          <p class='meta'>아직 참여자 없음</p>
        {% endfor %}
        {% if not p.closed %}<a class='btn ok full' href='/choose_participant/{{p.id}}'>참여하기</a>{% endif %}

        {% if p.category == "파밍" %}
          <div class='farm-box'>
            <div class='farm-head'>
              <h3>파밍 정산</h3>
              <span class='tag'>{{ p.farm_result or "미등록" }}</span>
            </div>
            <div class='farm-summary'>
              <span>아이템 <b>{{ p.farm_item or "-" }}</b></span>
              <span>판매 <b>{{ p.sale_amount or "0" }}</b></span>
            </div>
            {% set dist = farm_distribution(p) %}
            {% if dist.amount > 0 %}
              <div class='farm-dist'>선집합 {{ dist.early_each }}전 · 후집합 {{ dist.late_each }}전</div>
            {% endif %}
            {% if p.owner_uid==u.id or is_admin(u) %}
              <form class='farm-form' method='post' action='/farm_result/{{p.id}}'>
                <select name='farm_result'>
                  <option {% if p.farm_result=="노득" %}selected{% endif %}>노득</option>
                  <option {% if p.farm_result=="득템" %}selected{% endif %}>득템</option>
                </select>
                <input name='farm_item' value='{{p.farm_item}}' placeholder='아이템명'>
                <input name='sale_amount' value='{{p.sale_amount}}' placeholder='판매금액'>
                <button class='ok'>저장</button>
              </form>
              <div class='toolbar farm-tools'>
                <a class='btn gray mini' href='/farm_group/{{p.id}}/early'>선집합</a>
                <a class='btn gray mini' href='/farm_group/{{p.id}}/late'>후집합</a>
              </div>
            {% endif %}
          </div>
        {% endif %}
      {% endif %}

      <div class='actions'>
        <a class='btn gray' href='/chat/{{p.id}}'>채팅 {{p.chat|length }}</a>
        {% if p.owner_uid==u.id or is_admin(u) %}
          <a class='btn ok' href='/close/{{p.id}}'>모집완료</a>
          <a class='btn gray' href='/edit/{{p.id}}'>수정</a>
          <a class='btn danger' href='/delete/{{p.id}}'>삭제</a>
        {% endif %}
      </div>
    </section>
    {% else %}
      <div class='empty'>모집글 없음</div>
    {% endfor %}
  </main>

  <aside class='side-stack'>
    <section class='panel online-panel'>
      <div class='online-head'>
        <h2>🟢 접속중 {{ online|length if online is defined else 1 }}명</h2>
        <span class='meta'>최근 5분</span>
      </div>
      {% if online is defined and online %}
        <div class='online-list'>
        {% for o in online %}
          <span class='pill online-pill'>{{ o.label }}{% if o.role != '일반' %}<small>{{ o.role }}</small>{% endif %}</span>
        {% endfor %}
        </div>
      {% else %}
        <span class='pill online-pill'>{{ char_label(c) }}</span>
      {% endif %}
    </section>

    <section class='panel'>
      <h2>📅 오늘 일정</h2>
      {% for p in sched %}
        <div class='schedule-row'>
          <div><b>{{p.place}}</b><br><span class='meta'>{{p.date}} · {{ remaining_text(p) }}</span></div>
          <strong>{{show_time(p.start_time)}}</strong>
        </div>
      {% else %}
        <div class='empty'>등록된 파밍 일정 없음</div>
      {% endfor %}
    </section>

    <section class='panel'>
      <h2>💬 통합채팅</h2>
      <div class='chatbox'>
        {% for m in d.global_chat[-30:] %}
          <div class='chatmsg'><b>{{m.name}}</b><br>{{m.text}}<br><span class='meta'>{{m.time}}</span></div>
        {% else %}
          <div class='empty'>메시지 없음</div>
        {% endfor %}
      </div>
      <form class='toolbar' method='post' action='/global_chat'>
        <input name='text' placeholder='메시지'>
        <button>전송</button>
      </form>
    </section>
  </aside>
</div>
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
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h1>모집글 올리기</h1><form method='post' action='/create'><label>종류</label><select name='category' id='cat'>{% for c in cats %}<option>{{c}}</option>{% endfor %}</select>{% for cat, arr in places.items() %}<div class='place' data-cat='{{cat}}'><label>장소</label><select name='place_{{cat}}'>{% for p in arr %}<option>{{p}}</option>{% endfor %}</select></div>{% endfor %}<label>채널</label><input name='channel' maxlength='4'><label>날짜</label><input name='date' type='date' value='{{today()}}'><label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' maxlength='5' placeholder='1107'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option>오후</option></select><input name='end_time' maxlength='5' placeholder='1120'></div><label>메모</label><textarea name='memo'></textarea><section class='panel' id='slotsBox'><h2>사냥 직업 자리 추가</h2><div class='toolbar'>{{ job_select('slotJob', '', 'slotJob')|safe }}<button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slots'></div></section><button class='ok full'>등록</button></form></section>
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


@app.route("/choose_slot/<pid>/<int:i>", methods=["GET","POST"])
def choose_slot(pid, i):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if not approved(u) or not p or p.get("category")!="사냥" or p.get("closed"):
        return redirect("/")
    if not (0 <= i < len(p.get("slots", []))):
        return redirect("/")
    slot = p["slots"][i]
    options = [c for c in approved_chars(u) if compatible_job(slot.get("job",""), c.get("job",""))]
    if request.method == "POST":
        cid = request.form.get("char_id","")
        chosen = None
        for c in options:
            if c.get("id") == cid:
                chosen = c
        if chosen and not slot.get("uid") and not slot.get("external"):
            for s in p["slots"]:
                if s.get("uid")==u["id"]:
                    s.update({"uid":"","label":""})
            slot.update({"uid":u["id"],"label":char_label(chosen),"char_id":chosen.get("id","")})
            save(d)
        return redirect("/")
    return render("""
<section class='panel'>
<a class='btn gray' href='/'>← 메인</a>
<h1>참여 캐릭터 선택</h1>
<div class='notice'>{{slot.job}} 자리에는 같은 계열 캐릭터만 참여할 수 있습니다.</div>
<form method='post'>
{% for c in options %}
<label class='slot'><span><b>{{c.name}}({{c.job}})</b></span><input type='radio' name='char_id' value='{{c.id}}' required></label>
{% else %}
<div class='empty'>참여 가능한 캐릭터가 없습니다.</div>
{% endfor %}
{% if options %}<button class='ok full'>참여하기</button>{% endif %}
</form>
</section>
""", slot=slot, options=options)

@app.route("/choose_participant/<pid>", methods=["GET","POST"])
def choose_participant(pid):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if not approved(u) or not p or p.get("category") not in ["600퀘","파밍"] or p.get("closed"):
        return redirect("/")
    options = approved_chars(u)
    if request.method == "POST":
        cid = request.form.get("char_id","")
        chosen = None
        for c in options:
            if c.get("id") == cid:
                chosen = c
        if chosen:
            if p.get("category")!="600퀘" or len(p.get("participants",[])) < 10:
                if not any(a.get("uid")==u["id"] and a.get("char_id")==chosen.get("id") for a in p["participants"]):
                    p["participants"].append({"uid":u["id"],"char_id":chosen.get("id"),"label":char_label(chosen)})
                    save(d)
        return redirect("/")
    return render("""
<section class='panel'>
<a class='btn gray' href='/'>← 메인</a>
<h1>참여 캐릭터 선택</h1>
<form method='post'>
{% for c in options %}
<label class='slot'><span><b>{{c.name}}({{c.job}})</b></span><input type='radio' name='char_id' value='{{c.id}}' required></label>
{% else %}
<div class='empty'>승인된 캐릭터가 없습니다.</div>
{% endfor %}
{% if options %}<button class='ok full'>참여하기</button>{% endif %}
</form>
</section>
""", options=options)

@app.route("/farm_group/<pid>/<group>", methods=["GET","POST"])
def farm_group(pid, group):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if not p or p.get("category")!="파밍" or not (is_admin(u) or p.get("owner_uid")==u.get("id")):
        return redirect("/")
    if group not in ["early","late"]:
        return redirect("/")
    key = "early_ids" if group=="early" else "late_ids"
    if request.method == "POST":
        ids = request.form.getlist("member")
        p[key] = ids
        save(d)
        return redirect("/")
    members = p.get("participants", [])
    checked = set(p.get(key, []))
    title = "선집합 체크" if group=="early" else "후집합 체크"
    return render("""
<section class='panel'>
<a class='btn gray' href='/'>← 메인</a>
<h1>{{title}}</h1>
<form method='post'>
{% for m in members %}
<label class='slot'><span><b>{{m.label}}</b></span><input type='checkbox' name='member' value='{{m.char_id or m.uid}}' {% if (m.char_id or m.uid) in checked %}checked{% endif %}></label>
{% else %}
<div class='empty'>참여자가 없습니다.</div>
{% endfor %}
<button class='ok full'>저장</button>
</form>
</section>
""", title=title, members=members, checked=checked)

@app.route("/join_slot/<pid>/<int:i>")
def join_slot(pid,i):
    d=load(); u=cur_user(d); c=selected_char(u)
    p=find_post(d,pid)
    if p and c and p["category"]=="사냥" and not p.get("closed") and 0<=i<len(p["slots"]):
        if not compatible_job(p["slots"][i].get("job",""), c.get("job","")):
            return redirect(f"/choose_slot/{pid}/{i}")
        for s in p["slots"]:
            if s.get("uid")==u["id"]: s.update({"uid":"","label":"","char_id":""})
        if not p["slots"][i].get("uid") and not p["slots"][i].get("external"):
            p["slots"][i].update({"uid":u["id"],"label":char_label(c),"char_id":c.get("id","")})
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
    return redirect(f"/choose_participant/{pid}")

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



@app.route("/farm_result/<pid>", methods=["POST"])
def farm_result(pid):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or p.get("category") != "파밍":
        return redirect("/")
    if not (is_admin(u) or p.get("owner_uid") == (u or {}).get("id")):
        return redirect("/")
    p["farm_result"] = request.form.get("farm_result", "").strip()
    p["farm_item"] = request.form.get("farm_item", "").strip()
    p["sale_amount"] = digits(request.form.get("sale_amount", ""), 20)
    p.setdefault("early_ids", [])
    p.setdefault("late_ids", [])
    p.setdefault("early_weight", "1.0")
    p.setdefault("late_weight", "0.88")
    save(d)
    return redirect("/")

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
