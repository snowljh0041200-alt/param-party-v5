
from flask import Flask, request, jsonify, render_template_string, redirect, session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, os, uuid, tempfile, threading, html

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v10-secret")
DATA_FILE = "data.json"
LOCK = threading.Lock()
AUTO_DELETE_HOURS = 1
GLOBAL_CHAT_RETENTION_HOURS = 24
GLOBAL_CHAT_LIMIT = 100
GLOBAL_CHAT_DELETE_MINUTES = 5
DEFAULT_ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "moon")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")
ONLINE_USERS = {}
KST = ZoneInfo("Asia/Seoul")

JOBS = ["검성","태성","현자","진선","검황","귀검","현인","진인","전사","도적","주술사","도사","검객","자객","술사","도인","검제","진검","현사","명인"]
FILTERS = ["전체", "사냥", "파밍", "600퀘"]
PLACES = {"사냥":["도삭산 900층","흉노족","선비족"],"파밍":["해골왕","어금니"],"600퀘":["800층 600퀘","900층 600퀘","선비족 600퀘"]}

def esc(v): return html.escape(str(v or ""), quote=True)
def now_text(): return datetime.now(KST).strftime("%m/%d %H:%M")
def now_iso(): return datetime.now(KST).isoformat(timespec="seconds")
def chat_time(): return datetime.now(KST).strftime("%H:%M")
def parse_iso(v):
    try: return datetime.fromisoformat(v) if v else None
    except Exception: return None
def clean_channel(v): return "".join([c for c in str(v or "") if c.isdigit()])[:4]
def default_data():
    return {"settings":{"access_password":DEFAULT_ACCESS_PASSWORD,"admin_password":DEFAULT_ADMIN_PASSWORD,"notice":""},"users":[],"posts":[],"global_chat":[]}

def load_raw():
    if not os.path.exists(DATA_FILE): return default_data()
    try:
        with open(DATA_FILE,"r",encoding="utf-8") as f: data=json.load(f)
    except Exception:
        return default_data()
    data.setdefault("settings",{})
    data["settings"].setdefault("access_password",DEFAULT_ACCESS_PASSWORD)
    data["settings"].setdefault("admin_password",DEFAULT_ADMIN_PASSWORD)
    data["settings"].setdefault("notice","")
    data.setdefault("users",[]); data.setdefault("posts",[]); data.setdefault("global_chat",[])
    return data

def save_raw(data):
    fd,tmp=tempfile.mkstemp(prefix="baram_v10_",suffix=".json",dir=".")
    with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    os.replace(tmp,DATA_FILE)

def cleanup(data):
    cutoff=datetime.now(KST)-timedelta(hours=AUTO_DELETE_HOURS)
    kept=[]
    for p in data.get("posts",[]):
        ca=parse_iso(p.get("closed_at",""))
        if p.get("closed") and ca and ca<=cutoff: continue
        p["party_chat"]=p.get("party_chat",[])[-120:]
        kept.append(p)
    data["posts"]=kept
    cutoff_chat = datetime.now(KST) - timedelta(hours=GLOBAL_CHAT_RETENTION_HOURS)
    fresh_chat = []
    for msg in data.get("global_chat", []):
        msg_dt = parse_iso(msg.get("created_at", ""))
        if msg_dt is None or msg_dt >= cutoff_chat:
            fresh_chat.append(msg)
    data["global_chat"] = fresh_chat[-GLOBAL_CHAT_LIMIT:]
    return data

def load_data():
    with LOCK:
        d=cleanup(load_raw()); save_raw(d); return d
def mutate(fn):
    with LOCK:
        d=cleanup(load_raw()); r=fn(d); save_raw(d); return r

def current_uid(): return session.get("uid")
def find_user(data,uid):
    for u in data.get("users",[]):
        if u.get("id")==uid: return u
    return None
def current_user(data): return find_user(data,current_uid()) if current_uid() else None
def approved_user(u): return bool(u and u.get("status")=="approved" and not u.get("blocked"))
def can_enter_site(data): return bool(session.get("access_ok")) or approved_user(current_user(data))
def char_label(c): return f"{c.get('name','')}({c.get('job','')})"
def approved_chars(u): return [c for c in (u or {}).get("chars",[]) if c.get("status")=="approved"]
def selected_char(u):
    chars=approved_chars(u)
    if not chars: return None
    for c in chars:
        if c.get("id")==u.get("selected_char_id"): return c
    return chars[0]
def touch_online():
    key=current_uid() or session.get("guest_id") or str(uuid.uuid4())
    session["guest_id"]=key
    ONLINE_USERS[key]=datetime.now(KST)
def online_count():
    cutoff = datetime.now(KST) - timedelta(seconds=80)
    for k, v in list(ONLINE_USERS.items()):
        try:
            if getattr(v, "tzinfo", None) is None:
                v = v.replace(tzinfo=KST)
            if v < cutoff:
                ONLINE_USERS.pop(k, None)
        except Exception:
            ONLINE_USERS.pop(k, None)
    return max(1, len(ONLINE_USERS))

def find_post(data,pid):
    for p in data.get("posts",[]):
        if p.get("id")==pid: return p
    return None
def filled_total(p):
    slots=p.get("slots",[])
    return sum(1 for s in slots if s.get("char_id")), len(slots)
def is_full(p):
    f,t=filled_total(p); return t>0 and f>=t
def ensure_closed(p):
    if is_full(p) and not p.get("closed"):
        p["closed"]=True; p["closed_at"]=now_iso()
def post_status(p): return "마감" if p.get("closed") or is_full(p) else "모집중"
def post_time(p):
    a=(p.get("start_period","")+" "+p.get("start_time","")).strip()
    b=(p.get("end_period","")+" "+p.get("end_time","")).strip()
    return f"{a} ~ {b}" if a and b else (a or b or "시간 미정")
def closed_left(p):
    if not p.get("closed"): return ""
    dt=parse_iso(p.get("closed_at",""))
    if not dt: return "1시간 뒤 자동삭제"
    left=int(((dt+timedelta(hours=AUTO_DELETE_HOURS))-datetime.now(KST)).total_seconds()//60)
    return "곧 삭제" if left<=0 else f"{left}분 뒤 자동삭제"
def user_has_char(u,cid):
    for c in approved_chars(u):
        if c.get("id")==cid: return c
    return None
def all_char_names(data):
    names=set()
    for u in data.get("users",[]):
        for c in u.get("chars",[]): names.add(c.get("name","").strip().lower())
    return names
def can_party_chat(p,u):
    if not approved_user(u): return False
    return p.get("owner_uid")==u.get("id") or any(s.get("uid")==u.get("id") for s in p.get("slots",[]))
def render_chat_rows(chats,uid):
    if not chats: return "<div class='msg'>아직 메시지가 없습니다.</div>"
    rows = []
    delete_deadline = datetime.now(KST) - timedelta(minutes=GLOBAL_CHAT_DELETE_MINUTES)
    for c in chats[-GLOBAL_CHAT_LIMIT:]:
        mine = " mine" if c.get("uid") == uid else ""
        msg_id = esc(c.get("id", ""))
        created_at = parse_iso(c.get("created_at", ""))
        delete_btn = ""
        if msg_id and c.get("uid") == uid and created_at and created_at >= delete_deadline:
            delete_btn = f"<button class='mini danger' onclick=\"deleteGlobalChat('{msg_id}')\">삭제</button>"
        rows.append(f"<div class='msg{mine}'><div class='msg-meta'>{esc(c.get('label'))} · {esc(c.get('time'))} {delete_btn}</div><div>{esc(c.get('text'))}</div></div>")
    return "\n".join(rows)

def render_posts(posts,user):
    if not posts: return '<div class="empty">현재 모집글이 없습니다.</div>'
    out=[]; uid=user.get("id") if user else ""
    for p in posts:
        pid=esc(p.get("id")); status=post_status(p); f,t=filled_total(p)
        participants="|".join([s.get("uid","") for s in p.get("slots",[]) if s.get("uid")])
        chat_count=len(p.get("party_chat",[])); slot_html=[]
        copy=[f"[{p.get('category')}] {p.get('place')}",f"채널 {p.get('channel') or '미정'}",post_time(p),f"작성자 {p.get('owner_label')}"]
        for s in p.get("slots",[]):
            sid=esc(s.get("id")); job=esc(s.get("job")); char=esc(s.get("char_label")); copy.append(f"{s.get('job')} - {s.get('char_label') or '모집중'}")
            if char:
                slot_html.append(f"<div class='slot filled'><div><b>{job}</b><br><span>✅ {char}</span></div><button class='mini danger' onclick=\"leaveSlot('{pid}','{sid}')\">비우기</button></div>")
            else:
                slot_html.append(f"<div class='slot'><div><b>{job}</b><br><span>⭕ 모집중</span></div><button class='mini ok' onclick=\"joinSlot('{pid}','{sid}','{job}')\">참여</button></div>")
        memo=f"<div class='memo'>📝 {esc(p.get('memo'))}</div>" if p.get("memo") else ""
        left=f"<div class='left-time'>{esc(closed_left(p))}</div>" if closed_left(p) else ""
        copy_text=esc("\\n".join(copy)); owner="1" if p.get("owner_uid")==uid else "0"
        out.append(f"""
        <article class="party-card post" data-post-id="{pid}" data-owner="{owner}" data-participants="{esc(participants)}">
          <div class="post-head"><div><span class="pill {'done' if status=='마감' else 'open'}">{status}</span><span class="pill type">{esc(p.get('category'))}</span></div><b class="count">{f}/{t}</b></div>
          <h2>{esc(p.get('place'))}</h2>
          <div class="meta">📍 채널 <b>{esc(p.get('channel') or '미정')}</b> · ⏰ {esc(post_time(p))}</div>
          <div class="meta">👑 {esc(p.get('owner_label'))} · {esc(p.get('created'))}</div>
          {memo}{left}
          <div class="slots">{''.join(slot_html)}</div>
          <div class="actions"><button type="button" onclick="copyPost(`{copy_text}`)">복사</button><button type="button" onclick="shareKakao(`{copy_text}`)">카톡공유</button><button type="button" onclick="openPartyChat('{pid}')">파티채팅 {chat_count}</button><button type="button" class="owner-only danger" onclick="deletePost('{pid}')">삭제</button></div>
        </article>""")
    return "\n".join(out)

BASE_CSS = """
*{box-sizing:border-box}body{margin:0;color:#eef2ff;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',Arial,sans-serif;background:#0b1020}body:before{content:'';position:fixed;inset:0;background:radial-gradient(circle at 20% 0%,#253b75 0,#111a34 36%,#090d18 76%);z-index:-2}.wrap{max-width:1040px;margin:0 auto;padding:18px 16px 100px}.header{padding:12px 0 16px;border-bottom:1px solid rgba(255,255,255,.10)}h1{font-size:28px;margin:0;letter-spacing:-.8px}.sub{color:#aeb8d7;font-size:13px;margin-top:4px}.panel,.party-card{background:rgba(20,27,48,.86);border:1px solid rgba(150,165,210,.22);box-shadow:0 18px 50px rgba(0,0,0,.30);border-radius:24px;padding:16px;margin:14px 0;backdrop-filter:blur(12px)}.top-actions{display:flex;gap:8px;flex-wrap:wrap}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.stat{background:rgba(7,11,22,.55);border:1px solid rgba(255,255,255,.10);border-radius:18px;text-align:center;padding:14px 8px}.stat b{font-size:28px;display:block}.stat span{font-size:12px;color:#aeb8d7}button,.btn{border:0;border-radius:15px;background:linear-gradient(180deg,#6a86ff,#4163ff);color:#fff;font-weight:900;padding:12px 15px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;min-height:44px;box-shadow:0 8px 22px rgba(35,80,255,.24);cursor:pointer}button.gray,.btn.gray{background:linear-gradient(180deg,#4c5571,#363d55);box-shadow:none}button.danger,.danger{background:linear-gradient(180deg,#ff6666,#ce4040);box-shadow:none}button.ok{background:linear-gradient(180deg,#2bd176,#169851)}input,select,textarea{width:100%;background:#0d1325;color:#f4f6ff;border:1px solid rgba(170,185,230,.25);border-radius:15px;padding:13px;margin:6px 0 13px;font-size:16px;outline:none}label{font-size:13px;color:#bac4de;font-weight:900}.tabs{display:flex;gap:8px;overflow-x:auto;padding:4px 0}.tabs a{white-space:nowrap;color:#dce4ff;background:rgba(10,15,30,.55);border:1px solid rgba(255,255,255,.12);text-decoration:none;border-radius:999px;padding:9px 14px;font-weight:900;font-size:14px}.tabs a.on{background:linear-gradient(180deg,#6a86ff,#4163ff);border-color:#8ca0ff}.empty{border:1px dashed rgba(255,255,255,.25);border-radius:22px;padding:46px;text-align:center;color:#c2c9dd;background:rgba(20,27,48,.55)}.post-head{display:flex;justify-content:space-between;align-items:center}.pill{display:inline-flex;border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;margin-right:4px}.pill.open{background:#123f2a;color:#9dffc4}.pill.done{background:#4d2020;color:#ffd1d1}.pill.type{background:#242c48;color:#ccd6ff}.count{font-size:18px;background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:7px 12px}h2{font-size:24px;margin:12px 0 5px}.meta{color:#b5bfd9;font-size:14px;line-height:1.6}.memo{color:#ffd16a;font-size:14px;margin-top:5px}.left-time{color:#ffb3b3;font-size:13px;font-weight:900}.slot{display:flex;justify-content:space-between;align-items:center;background:rgba(8,12,24,.62);border:1px solid rgba(255,255,255,.12);border-radius:17px;padding:12px;margin:9px 0}.slot.filled{background:rgba(18,55,33,.58);border-color:rgba(73,190,112,.35)}.actions{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}.owner-only{display:none!important}.post[data-owner='1'] .owner-only{display:inline-flex!important}.hidden{display:none!important}.time-row{display:grid;grid-template-columns:90px 1fr;gap:8px}.quick{display:grid;grid-template-columns:1fr auto;gap:8px}.mini{font-size:13px;padding:8px 10px;min-height:34px}.notice,.alarm-guide{background:linear-gradient(180deg,rgba(255,211,106,.18),rgba(255,211,106,.08));border:1px solid rgba(255,211,106,.30);color:#ffe5a3;border-radius:18px;padding:12px;margin-top:12px;font-size:13px;line-height:1.45}.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#1e2845;border:1px solid #53648f;border-radius:999px;padding:10px 16px;opacity:0;transition:.2s;z-index:999;font-weight:900}.toast.show{opacity:1}.modal{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;z-index:100}.modal.show{display:flex}.chat-panel{width:100%;max-width:880px;margin:0 auto;border-radius:22px 22px 0 0}.chat-list{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;height:340px;overflow-y:auto;padding:10px}.msg{background:#202a47;border-radius:13px;padding:9px 11px;margin:7px 0}.msg.mine{background:#173d27;border:1px solid #2e7146}.msg-meta{font-size:12px;color:#a8b2cc}.chat-form{display:grid;grid-template-columns:1fr 74px;gap:7px;margin-top:9px}.chat-form input{margin:0}.member-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.member{background:rgba(8,12,24,.55);border:1px solid rgba(255,255,255,.10);border-radius:14px;padding:10px}.choice-list{display:grid;gap:8px}.choice-list button{width:100%;justify-content:flex-start;background:linear-gradient(180deg,#4c5571,#363d55)}@media(max-width:680px){.wrap{padding:12px 10px 90px}h1{font-size:22px}.summary{grid-template-columns:repeat(3,1fr);gap:7px}.stat{padding:10px 4px}.stat b{font-size:21px}.actions{grid-template-columns:1fr 1fr}.top-actions>*{flex:1}.panel,.party-card{border-radius:20px;padding:13px}button,.btn{font-size:14px;padding:10px 11px}}
"""

GATE_
REGISTER_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>가입</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>👤 문파원 등록</h1><div class='sub'>처음 한 번만 등록하면 됩니다.</div></header>
<section class='panel'>
<form method='post' action='/register'>
<label>계정명</label><input name='account' required placeholder='예: 역인'>
<label>대표 캐릭터명</label><input name='char_name' required placeholder='예: 역인'>
<label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select>
<button style='width:100%'>승인 요청</button>
</form>
<p class='meta'>관리자 승인 후 사이트 이용이 가능합니다.</p>
{% if error %}<div class='notice'>{{ error }}</div>{% endif %}
</section></div></body></html>
"""


WAIT_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>승인 대기</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>⏳ 승인 대기중</h1><div class='sub'>관리자가 승인하면 이용할 수 있습니다.</div></header>
<section class='panel'><p>{{ user.account if user else "승인 대기중" }} 계정이 승인 대기중입니다.</p>
<form method='post' action='/logout'><button class='gray'>로그아웃</button></form></section></div></body></html>
"""

PAGE = """
<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>월하 · 연가 · 연희 파티모집</title>
<style>{{ css }}</style>
</head>
<body>
<div class='wrap'>
  <header class='header'>
    <h1>⚔️ 월하 · 연가 · 연희 파티모집</h1>
    <div class='sub'>Made by 역인(진선)</div>
  </header>

  {% if notice %}<div class='notice'>📢 {{ notice }}</div>{% endif %}

  {% if page=='home' %}
  <section class='panel'>
    <div class='top-actions'>
      <a class='btn' href='/new'>+ 모집글</a>
      <a class='btn gray' href='/chars'>내 캐릭터</a>
      <button type='button' class='gray' onclick='openGlobalChat()'>통합채팅</button>
      <button type='button' class='gray' onclick='toggleAlarm()' id='alarmBtn'>🔔 알림 ON</button>
    </div>
    <div class='summary'>
      <div class='stat'><b>{{ open_count }}</b><span>모집중</span></div>
      <div class='stat'><b id='onlineCount'>1</b><span>접속중</span></div>
      <div class='stat'><b id='myCount'>0</b><span>내 참여</span></div>
    </div>
    <div class='alarm-guide'>🔔 알림은 사이트가 열려있는 동안에만 동작합니다. 새 모집글, 참여, 채팅을 알려드립니다.</div>
    <div class='tabs'>
      {% for f in filters %}
      <a class='{% if filter_value==f %}on{% endif %}' href='/?filter={{ f }}'>{{ f }}</a>
      {% endfor %}
    </div>
  </section>
  <section class='panel'><h2>문파원 접속 현황</h2><div class='member-grid'>{{ member_html|safe }}</div></section>
  <div id='postList'>{{ post_list|safe }}</div>
  {% endif %}

  {% if page in ['new','edit'] %}
  <section class='panel'>
    <h2>{% if page=='edit' %}모집글 수정{% else %}모집글 올리기{% endif %}</h2>
    <form method='post' action='{% if page=="edit" %}/edit/{{ post.id }}{% else %}/create{% endif %}' onsubmit='return prepareSubmit()'>
      <label>작성 캐릭터</label>
      <select name='owner_char_id'>
        {% for c in chars %}<option value='{{ c.id }}'>{{ c.name }}({{ c.job }})</option>{% endfor %}
      </select>

      <label>종류</label>
      <select name='category' id='typeSelect' onchange='updatePlaces()'>
        {% for t in ['사냥','파밍','600퀘'] %}<option>{{ t }}</option>{% endfor %}
      </select>

      <label>장소</label>
      {% for cat, vals in places.items() %}
      <select name='place_{{ cat }}' id='place_{{ cat }}' class='place-select {% if cat!="사냥" %}hidden{% endif %}'>
        {% for p in vals %}<option>{{ p }}</option>{% endfor %}
      </select>
      {% endfor %}

      <label>채널 4자리</label>
      <input name='channel' id='channelInput' maxlength='4' inputmode='numeric' placeholder='예: 3385' oninput='numbersOnly(this)'>

      <label>시작시간</label>
      <div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' placeholder='예: 09:00'></div>

      <label>종료시간</label>
      <div class='time-row'><select name='end_period'><option>오전</option><option selected>오후</option></select><input name='end_time' placeholder='예: 11:00'></div>

      <label>메모</label>
      <textarea name='memo' rows='2'></textarea>

      <div class='panel'>
        <label>모집 자리 추가</label>
        <div class='quick'>
          <select id='slotJob'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select>
          <button type='button' class='ok' onclick='addSlot()'>추가</button>
        </div>
        <div id='slotsBox'></div>
      </div>

      <button style='width:100%' type='submit'>저장</button>
      <a class='btn gray' style='width:100%;margin-top:8px' href='/'>취소</a>
    </form>
  </section>
  {% endif %}

  {% if page=='chars' %}
  <section class='panel'>
    <h2>내 캐릭터</h2>
    <p class='meta'>새 캐릭터는 관리자 승인 후 사용할 수 있습니다.</p>
    <form method='post' action='/chars/add'>
      <label>캐릭터명</label><input name='name' required>
      <label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select>
      <button style='width:100%'>캐릭터 추가 요청</button>
    </form>
  </section>
  <section class='panel'>
    <h2>등록 캐릭터</h2>
    {% for c in user.chars %}
    <div class='member'>{{ c.name }}({{ c.job }}) · {{ c.status }} {% if c.status=='approved' %}<form method='post' action='/chars/select/{{ c.id }}' style='display:inline'><button class='mini'>대표선택</button></form>{% endif %}</div>
    {% endfor %}
  </section>
  {% endif %}
</div>

<div id='globalModal' class='modal'>
  <div class='panel chat-panel'>
    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>💬 통합채팅</b><button type='button' class='mini gray' onclick='closeGlobalChat()'>닫기</button></div>
    <div class='alarm-guide'>최근 100개 메시지만 유지됩니다. 24시간이 지난 메시지는 자동 삭제됩니다. 본인이 작성한 메시지는 5분 이내 삭제 가능합니다.</div>
    <div id='globalChatList' class='chat-list'></div>
    <div class='chat-form'><input id='globalChatText' placeholder='메시지' maxlength='150'><button type='button' onclick='sendGlobalChat()'>전송</button></div>
  </div>
</div>

<div id='partyModal' class='modal'>
  <div class='panel chat-panel'>
    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>💬 파티채팅</b><button type='button' class='mini gray' onclick='closePartyChat()'>닫기</button></div>
    <div id='partyChatList' class='chat-list'></div>
    <div class='chat-form'><input id='partyChatText' placeholder='메시지' maxlength='150'><button type='button' onclick='sendPartyChat()'>전송</button></div>
  </div>
</div>

<div id='charPickModal' class='modal'>
  <div class='panel chat-panel'>
    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>참여 캐릭터 선택</b><button type='button' class='mini gray' onclick='closeCharPick()'>닫기</button></div>
    <div id='charPickList' class='choice-list'></div>
  </div>
</div>

<div id='toast' class='toast'></div>

<script>
const CURRENT_USER_ID = "{{ user.id if user else '' }}";
let globalOpen = false;
let partyId = null;
let knownPosts = new Set();
let firstLoad = true;

function qs(id){ return document.getElementById(id); }
function toast(msg){
  const t = qs("toast");
  if(!t){ alert(msg); return; }
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(function(){ t.classList.remove("show"); }, 1600);
}
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; });
}
function numbersOnly(el){ el.value = (el.value || "").replace(/[^0-9]/g, "").slice(0,4); }
function prepareSubmit(){
  const ch = qs("channelInput");
  if(ch){
    numbersOnly(ch);
    if(ch.value.length !== 4){
      alert("채널은 숫자 4자리로 입력해줘.");
      ch.focus();
      return false;
    }
  }
  return true;
}
function updatePlaces(){
  const t = qs("typeSelect");
  if(!t) return;
  document.querySelectorAll(".place-select").forEach(function(x){ x.classList.add("hidden"); });
  const target = qs("place_" + t.value);
  if(target) target.classList.remove("hidden");
}
function addSlot(){
  const jobSelect = qs("slotJob");
  const box = qs("slotsBox");
  if(!jobSelect || !box) return;
  const job = jobSelect.value;
  const d = document.createElement("div");
  d.className = "slot";
  d.innerHTML = "<div><b>"+escapeHtml(job)+"</b><br><span>빈자리</span></div><button type='button' class='mini danger' onclick='this.parentElement.remove()'>삭제</button><input type='hidden' name='slots' value='"+escapeHtml(job)+"'>";
  box.appendChild(d);
}
function copyPost(text){
  if(navigator.clipboard){
    navigator.clipboard.writeText(text).then(function(){ toast("복사됨"); }).catch(function(){ alert(text); });
  } else {
    alert(text);
  }
}
function shareKakao(text){
  const shareText = "월하 · 연가 · 연희 파티모집\\n\\n" + text + "\\n\\n" + location.origin;
  if(navigator.share){
    navigator.share({title:"파티모집", text:shareText, url:location.origin}).catch(function(){ copyPost(shareText); });
  } else {
    copyPost(shareText);
    toast("공유문구가 복사됐습니다. 카톡에 붙여넣어 주세요.");
  }
}
function refresh(){
  if(location.pathname !== "/") return;
  fetch("/api/posts" + location.search, {cache:"no-store"}).then(function(r){ return r.text(); }).then(function(html){
    const list = qs("postList");
    if(list) list.innerHTML = html;
    scanAlarms();
    countMine();
  }).catch(function(){});
}
function countMine(){
  let c = 0;
  document.querySelectorAll(".post").forEach(function(p){
    if(p.dataset.owner === "1" || (CURRENT_USER_ID && (p.dataset.participants || "").indexOf(CURRENT_USER_ID) >= 0)) c++;
  });
  const m = qs("myCount");
  if(m) m.textContent = c;
}
function doJoin(pid, sid, cid){
  fetch("/join", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({post_id:pid, slot_id:sid, char_id:cid})})
    .then(function(){ toast("참여됨"); closeCharPick(); refresh(); });
}
function closeCharPick(){
  const m = qs("charPickModal");
  if(m) m.classList.remove("show");
}
function joinSlot(pid, sid, job){
  fetch("/api/mychars?job=" + encodeURIComponent(job), {cache:"no-store"}).then(function(r){ return r.json(); }).then(function(data){
    const chars = data.chars || [];
    if(chars.length === 0){ toast("승인된 해당 직업 캐릭터가 없습니다."); return; }
    if(chars.length === 1){ doJoin(pid, sid, chars[0].id); return; }
    const box = qs("charPickList");
    if(!box) return;
    box.innerHTML = "";
    chars.forEach(function(c){
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = c.label + " 으로 참여";
      b.onclick = function(){ doJoin(pid, sid, c.id); };
      box.appendChild(b);
    });
    qs("charPickModal").classList.add("show");
  }).catch(function(){ toast("참여 처리 중 오류"); });
}
function leaveSlot(pid, sid){
  if(!confirm("비울까?")) return;
  fetch("/leave", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({post_id:pid, slot_id:sid})}).then(function(){ refresh(); });
}
function deletePost(pid){
  if(!confirm("정말 삭제하시겠습니까?")) return;
  fetch("/delete", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({post_id:pid})})
    .then(function(r){ return r.json(); }).then(function(x){ toast(x.ok ? "삭제됨" : (x.reason || "삭제 실패")); refresh(); });
}
function openGlobalChat(){
  globalOpen = true;
  const m = qs("globalModal");
  if(m) m.classList.add("show");
  refreshGlobalChat();
}
function closeGlobalChat(){
  globalOpen = false;
  const m = qs("globalModal");
  if(m) m.classList.remove("show");
}
function refreshGlobalChat(){
  if(!globalOpen) return;
  fetch("/api/global_chat", {cache:"no-store"}).then(function(r){ return r.text(); }).then(function(html){
    const box = qs("globalChatList");
    if(box){ box.innerHTML = html; box.scrollTop = box.scrollHeight; }
  }).catch(function(){});
}
function sendGlobalChat(){
  const input = qs("globalChatText");
  if(!input || !input.value.trim()) return;
  fetch("/global_chat", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:input.value.trim()})})
    .then(function(r){ return r.json(); }).then(function(x){
      if(!x.ok){ toast(x.reason || "전송 실패"); return; }
      input.value = "";
      refreshGlobalChat();
    });
}
function deleteGlobalChat(mid){
  if(!confirm("이 메시지를 삭제할까요?")) return;
  fetch("/global_chat/delete", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({id:mid})})
    .then(function(r){ return r.json(); }).then(function(x){ toast(x.ok ? "삭제됨" : (x.reason || "삭제 실패")); refreshGlobalChat(); });
}
function openPartyChat(pid){
  partyId = pid;
  const m = qs("partyModal");
  if(m) m.classList.add("show");
  refreshPartyChat();
}
function closePartyChat(){
  partyId = null;
  const m = qs("partyModal");
  if(m) m.classList.remove("show");
}
function refreshPartyChat(){
  if(!partyId) return;
  fetch("/api/party_chat/" + partyId, {cache:"no-store"}).then(function(r){ return r.text(); }).then(function(html){
    const box = qs("partyChatList");
    if(box){ box.innerHTML = html; box.scrollTop = box.scrollHeight; }
  }).catch(function(){});
}
function sendPartyChat(){
  const input = qs("partyChatText");
  if(!partyId || !input || !input.value.trim()) return;
  fetch("/party_chat/" + partyId, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:input.value.trim()})})
    .then(function(r){ return r.json(); }).then(function(x){
      if(!x.ok){ toast(x.reason || "전송 실패"); return; }
      input.value = "";
      refreshPartyChat();
      refresh();
    });
}
function alarmOn(){ return localStorage.getItem("baram_alarm_off") !== "1"; }
function updateAlarmBtn(){
  const b = qs("alarmBtn");
  if(b) b.textContent = alarmOn() ? "🔔 알림 ON" : "🔕 알림 OFF";
}
function toggleAlarm(){
  localStorage.setItem("baram_alarm_off", alarmOn() ? "1" : "0");
  updateAlarmBtn();
  toast(alarmOn() ? "알림 켜짐" : "알림 꺼짐");
}
function scanAlarms(){
  document.querySelectorAll(".post").forEach(function(p){
    const id = p.dataset.postId;
    if(id && !knownPosts.has(id)){
      if(!firstLoad && alarmOn()) toast("새 모집글이 올라왔습니다.");
      knownPosts.add(id);
    }
  });
  firstLoad = false;
}
function heartbeat(){
  fetch("/api/heartbeat", {method:"POST"}).then(function(r){ return r.json(); }).then(function(x){
    const o = qs("onlineCount");
    if(o) o.textContent = x.online || 1;
  }).catch(function(){});
}
document.addEventListener("DOMContentLoaded", function(){
  const g = qs("globalChatText");
  if(g) g.addEventListener("keydown", function(e){ if(e.key === "Enter"){ e.preventDefault(); sendGlobalChat(); }});
  const p = qs("partyChatText");
  if(p) p.addEventListener("keydown", function(e){ if(e.key === "Enter"){ e.preventDefault(); sendPartyChat(); }});
  updatePlaces();
  updateAlarmBtn();
  heartbeat();
  scanAlarms();
  countMine();
});
setInterval(refresh, 2500);
setInterval(refreshGlobalChat, 1600);
setInterval(refreshPartyChat, 1600);
setInterval(heartbeat, 15000);
</script>
</body>
</html>
"""

ADMIN_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>관리자</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>🔒 관리자</h1><div class='sub'>문파 관리 페이지</div></header><a class='btn gray' href='/'>메인</a>{% if not admin_ok %}<section class='panel'><form method='post' action='/admin/login'><label>관리자 비밀번호</label><input name='password' type='password' autofocus><button>로그인</button></form><p class='meta'>관리자만 접근 가능한 페이지입니다.</p></section>{% else %}<section class='panel'><div class='top-actions'><form method='post' action='/admin/logout'><button class='gray'>로그아웃</button></form><form method='post' action='/admin/clear_closed'><button>마감글 정리</button></form><form method='post' action='/admin/clear_global_chat'><button class='danger'>통합채팅 전체삭제</button></form></div></section><section class='panel'><h2>문파 설정</h2><form method='post' action='/admin/settings'><label>문파 입장 비밀번호 변경</label><input name='access_password' placeholder='새 입장 비밀번호'><label>관리자 비밀번호 변경</label><input name='admin_password' placeholder='새 관리자 비밀번호'><button>저장</button></form></section><section class='panel'><h2>공지</h2><form method='post' action='/admin/notice'><textarea name='notice' rows='3'>{{ notice }}</textarea><button>공지 저장</button></form></section><section class='panel'><h2>가입 승인</h2>{% for u in pending_users %}<div class='member'><b>{{ u.account }}</b> / {% for c in u.chars %}{{ c.name }}({{ c.job }}) {% endfor %}<form method='post' action='/admin/user/{{ u.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/user/{{ u.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p class='meta'>대기 없음</p>{% endfor %}</section><section class='panel'><h2>캐릭터 승인</h2>{% for item in pending_chars %}<div class='member'><b>{{ item.user.account }}</b> / {{ item.char.name }}({{ item.char.job }})<form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p class='meta'>대기 없음</p>{% endfor %}</section><section class='panel'><h2>회원 관리</h2>{% for u in users %}<div class='member'><b>{{ u.account }}</b> · {{ u.status }}{% if u.blocked %} · 차단됨{% endif %}<br>{% for c in u.chars %}{{ c.name }}({{ c.job }}) - {{ c.status }}<br>{% endfor %}<form method='post' action='/admin/user/{{ u.id }}/toggle_block'><button class='mini danger'>차단/해제</button></form></div>{% endfor %}</section><section class='panel'><h2>모집글 관리</h2>{% for p in posts %}<div class='member'><b>{{ p.place }}</b> / {{ p.channel }} / {{ p.owner_label }} / {{ p.created }}<form method='post' action='/admin/delete_post/{{ p.id }}'><button class='mini danger'>삭제</button></form></div>{% else %}<p class='meta'>글 없음</p>{% endfor %}</section>{% endif %}</div></body></html>
"""

def member_html(data):
    rows=[]; online=set(ONLINE_USERS.keys())
    for u in data.get("users",[]):
        if u.get("status")!="approved" or u.get("blocked"): continue
        ch=selected_char(u); label=char_label(ch) if ch else u.get("account")
        rows.append(f"<div class='member'>{'🟢' if u.get('id') in online else '⚫'} {esc(label)}</div>")
    return "".join(rows) if rows else "<div class='member'>승인된 문파원이 없습니다.</div>"

@app.before_request
def before():
    if request.path.startswith("/static") or request.path in ["/gate","/admin/login","/manifest.json","/sw.js"]: return
    if request.path.startswith("/admin"): return
    data=load_data()
    if not can_enter_site(data): return redirect("/gate")
    user=current_user(data)
    if not user and request.path!="/register": return redirect("/register")
    if user and not approved_user(user) and request.path not in ["/wait","/logout"]: return redirect("/wait")
    touch_online()

@app.route("/gate",methods=["GET","POST"])
def gate():
    error=False
    if request.method=="POST":
        if request.form.get("password","")==load_data()["settings"].get("access_password"):
            session["access_ok"]=True; return redirect("/")
        error=True
    return render_template_string(GATE_PAGE,css=BASE_CSS,error=error)

@app.route("/register",methods=["GET","POST"])
def register():
    data=load_data()
    if request.method=="POST":
        account=request.form.get("account","").strip(); char_name=request.form.get("char_name","").strip(); job=request.form.get("job","")
        if not account or not char_name: return render_template_string(REGISTER_PAGE,css=BASE_CSS,jobs=JOBS,error="입력값을 확인해주세요.")
        if char_name.lower() in all_char_names(data): return render_template_string(REGISTER_PAGE,css=BASE_CSS,jobs=JOBS,error="이미 등록된 캐릭터명입니다.")
        uid=str(uuid.uuid4()); cid=str(uuid.uuid4())
        user={"id":uid,"account":account,"status":"pending","blocked":False,"selected_char_id":cid,"created":now_text(),"chars":[{"id":cid,"name":char_name,"job":job,"status":"pending"}]}
        mutate(lambda d:d["users"].append(user)); session["uid"]=uid; session["access_ok"]=True; return redirect("/wait")
    return render_template_string(REGISTER_PAGE,css=BASE_CSS,jobs=JOBS,error="")

@app.route("/wait")
def wait(): return render_template_string(WAIT_PAGE,css=BASE_CSS,user=current_user(load_data()))
@app.route("/logout",methods=["POST"])
def logout(): session.clear(); return redirect("/gate")

@app.route("/")
def home():
    data=load_data(); user=current_user(data); filt=request.args.get("filter","전체")
    posts=list(reversed(data.get("posts",[])))
    if filt!="전체": posts=[p for p in posts if p.get("category")==filt]
    open_count=sum(1 for p in posts if post_status(p)=="모집중")
    return render_template_string(PAGE,css=BASE_CSS,page="home",filters=FILTERS,filter_value=filt,post_list=render_posts(posts,user),open_count=open_count,member_html=member_html(data),notice=data["settings"].get("notice",""),jobs=JOBS,places=PLACES,user=user)

@app.route("/api/posts")
def api_posts():
    data=load_data(); user=current_user(data); filt=request.args.get("filter","전체")
    posts=list(reversed(data.get("posts",[])))
    if filt!="전체": posts=[p for p in posts if p.get("category")==filt]
    return render_posts(posts,user)

@app.route("/new")
def new():
    user=current_user(load_data()); chars=approved_chars(user)
    if not chars: return redirect("/chars")
    return render_template_string(PAGE,css=BASE_CSS,page="new",post=None,chars=chars,jobs=JOBS,places=PLACES,notice="",user=user)

@app.route("/create",methods=["POST"])
def create():
    user=current_user(load_data()); owner_char=user_has_char(user,request.form.get("owner_char_id"))
    if not owner_char: return redirect("/chars")
    category=request.form.get("category","사냥"); slots=[{"id":str(uuid.uuid4()),"job":j,"char_id":"","uid":"","char_label":""} for j in request.form.getlist("slots")]
    post={"id":str(uuid.uuid4()),"owner_uid":user["id"],"owner_char_id":owner_char["id"],"owner_label":char_label(owner_char),"category":category,"place":request.form.get(f"place_{category}",""),"channel":clean_channel(request.form.get("channel","")),"start_period":request.form.get("start_period",""),"start_time":request.form.get("start_time","").strip(),"end_period":request.form.get("end_period",""),"end_time":request.form.get("end_time","").strip(),"memo":request.form.get("memo","").strip(),"slots":slots,"closed":False,"closed_at":"","party_chat":[],"created":now_text()}
    mutate(lambda d:d["posts"].append(post)); return redirect("/")

@app.route("/edit/<post_id>",methods=["GET","POST"])
def edit(post_id):
    data=load_data(); user=current_user(data); post=find_post(data,post_id)
    if not post or post.get("owner_uid")!=user.get("id"): return redirect("/")
    if request.method=="GET": return render_template_string(PAGE,css=BASE_CSS,page="edit",post=post,chars=approved_chars(user),jobs=JOBS,places=PLACES,notice="",user=user)
    mutate(lambda d: find_post(d,post_id).update({"channel":clean_channel(request.form.get("channel","")),"memo":request.form.get("memo","").strip()}))
    return redirect("/")

@app.route("/chars")
def chars_page():
    user=current_user(load_data()); return render_template_string(PAGE,css=BASE_CSS,page="chars",user=user,jobs=JOBS,notice="")
@app.route("/chars/add",methods=["POST"])
def chars_add():
    data=load_data(); user=current_user(data); name=request.form.get("name","").strip(); job=request.form.get("job","")
    if name and name.lower() not in all_char_names(data):
        mutate(lambda d: find_user(d,user["id"])["chars"].append({"id":str(uuid.uuid4()),"name":name,"job":job,"status":"pending"}))
    return redirect("/chars")
@app.route("/chars/select/<cid>",methods=["POST"])
def chars_select(cid):
    user=current_user(load_data())
    if user_has_char(user,cid): mutate(lambda d: find_user(d,user["id"]).update({"selected_char_id":cid}))
    return redirect("/chars")

@app.route("/api/mychars")
def api_mychars():
    user=current_user(load_data()); job=request.args.get("job",""); chars=approved_chars(user)
    if job: chars=[c for c in chars if c.get("job")==job]
    return jsonify(chars=[{"id":c["id"],"label":char_label(c)} for c in chars])

@app.route("/join",methods=["POST"])
def join():
    req=request.get_json(force=True); data=load_data(); user=current_user(data); ch=user_has_char(user,req.get("char_id"))
    if not ch: return jsonify(ok=False)
    def fn(d):
        p=find_post(d,req.get("post_id"))
        if not p or p.get("closed"): return
        for s in p.get("slots",[]):
            if s.get("id")==req.get("slot_id") and not s.get("char_id"):
                s["char_id"]=ch["id"]; s["uid"]=user["id"]; s["char_label"]=char_label(ch); ensure_closed(p); return
    mutate(fn); return jsonify(ok=True)

@app.route("/leave",methods=["POST"])
def leave():
    req=request.get_json(force=True); user=current_user(load_data())
    def fn(d):
        p=find_post(d,req.get("post_id"))
        if not p: return
        owner=p.get("owner_uid")==user["id"]
        for s in p.get("slots",[]):
            if s.get("id")==req.get("slot_id") and (owner or s.get("uid")==user["id"]):
                s["char_id"]=""; s["uid"]=""; s["char_label"]=""; p["closed"]=False; p["closed_at"]=""; return
    mutate(fn); return jsonify(ok=True)

@app.route("/delete",methods=["POST"])
def delete():
    req=request.get_json(force=True); user=current_user(load_data()); result={"ok":False,"reason":"작성자만 삭제 가능"}
    def fn(d):
        kept=[]
        for p in d.get("posts",[]):
            if p.get("id")==req.get("post_id") and p.get("owner_uid")==user["id"]: result["ok"]=True; continue
            kept.append(p)
        d["posts"]=kept
    mutate(fn); return jsonify(result)

@app.route("/api/global_chat")
def api_global_chat():
    data=load_data(); user=current_user(data); return render_chat_rows(data.get("global_chat",[]),user["id"])
@app.route("/global_chat",methods=["POST"])
def global_chat():
    req=request.get_json(force=True); data=load_data(); user=current_user(data); ch=selected_char(user); text=(req.get("text") or "").strip()[:150]
    if not ch or not text: return jsonify(ok=False,reason="채팅 불가")
    mutate(lambda d:d["global_chat"].append({"id":str(uuid.uuid4()),"uid":user["id"],"label":char_label(ch),"text":text,"time":chat_time(),"created_at":now_iso()}))
    return jsonify(ok=True)

@app.route("/global_chat/delete", methods=["POST"])
def global_chat_delete():
    req=request.get_json(force=True)
    msg_id=req.get("id","")
    if not msg_id: return jsonify(ok=False,reason="메시지 정보 없음")
    data=load_data(); user=current_user(data)
    if not approved_user(user): return jsonify(ok=False,reason="권한 없음")
    result={"ok":False,"reason":"삭제 가능 시간이 지났습니다."}
    deadline=datetime.now(KST)-timedelta(minutes=GLOBAL_CHAT_DELETE_MINUTES)
    def fn(d):
        kept=[]
        for msg in d.get("global_chat",[]):
            if msg.get("id")==msg_id and msg.get("uid")==user["id"]:
                created_at=parse_iso(msg.get("created_at",""))
                if created_at and created_at>=deadline:
                    result["ok"]=True; result["reason"]="삭제됨"; continue
            kept.append(msg)
        d["global_chat"]=kept
    mutate(fn)
    return jsonify(result)

@app.route("/api/party_chat/<pid>")
def api_party_chat(pid):
    data=load_data(); user=current_user(data); p=find_post(data,pid)
    if not p or not can_party_chat(p,user): return "<div class='msg'>참여자만 이용 가능합니다.</div>"
    return render_chat_rows(p.get("party_chat",[]),user["id"])
@app.route("/party_chat/<pid>",methods=["POST"])
def party_chat(pid):
    req=request.get_json(force=True); data=load_data(); user=current_user(data); p=find_post(data,pid); ch=selected_char(user); text=(req.get("text") or "").strip()[:150]
    if not p or not can_party_chat(p,user) or not ch or not text: return jsonify(ok=False,reason="참여자만 이용 가능")
    mutate(lambda d: find_post(d,pid).setdefault("party_chat",[]).append({"uid":user["id"],"label":char_label(ch),"text":text,"time":chat_time()}))
    return jsonify(ok=True)
@app.route("/api/heartbeat",methods=["POST"])
def heartbeat(): touch_online(); return jsonify(ok=True,online=online_count())

@app.route("/admin")
def admin():
    data=load_data()
    pending_users=[u for u in data["users"] if u.get("status")=="pending"]
    pending_chars=[{"user":u,"char":c} for u in data["users"] if u.get("status")=="approved" for c in u.get("chars",[]) if c.get("status")=="pending"]
    return render_template_string(ADMIN_PAGE,css=BASE_CSS,admin_ok=bool(session.get("admin_ok")),posts=list(reversed(data["posts"])),notice=data["settings"].get("notice",""),online=online_count(),pending_users=pending_users,pending_chars=pending_chars,users=data["users"])
@app.route("/admin/login",methods=["POST"])
def admin_login():
    if request.form.get("password")==load_data()["settings"].get("admin_password"): session["admin_ok"]=True
    return redirect("/admin")
@app.route("/admin/logout",methods=["POST"])
def admin_logout(): session.pop("admin_ok",None); return redirect("/admin")
@app.route("/admin/settings",methods=["POST"])
def admin_settings():
    if not session.get("admin_ok"): return redirect("/admin")
    access_pw=request.form.get("access_password","").strip(); admin_pw=request.form.get("admin_password","").strip()
    def fn(d):
        if access_pw: d["settings"]["access_password"]=access_pw
        if admin_pw: d["settings"]["admin_password"]=admin_pw
    mutate(fn); return redirect("/admin")
@app.route("/admin/notice",methods=["POST"])
def admin_notice():
    if not session.get("admin_ok"): return redirect("/admin")
    mutate(lambda d:d["settings"].update({"notice":request.form.get("notice","").strip()[:300]})); return redirect("/admin")
@app.route("/admin/user/<uid>/<action>",methods=["POST"])
def admin_user_action(uid,action):
    if not session.get("admin_ok"): return redirect("/admin")
    def fn(d):
        u=find_user(d,uid)
        if not u: return
        if action=="approve":
            u["status"]="approved"
            for c in u.get("chars",[]):
                if c.get("status")=="pending": c["status"]="approved"
        elif action=="reject": u["status"]="rejected"
        elif action=="toggle_block": u["blocked"]=not u.get("blocked",False)
    mutate(fn); return redirect("/admin")
@app.route("/admin/char/<uid>/<cid>/<action>",methods=["POST"])
def admin_char_action(uid,cid,action):
    if not session.get("admin_ok"): return redirect("/admin")
    def fn(d):
        u=find_user(d,uid)
        if not u: return
        for c in u.get("chars",[]):
            if c.get("id")==cid: c["status"]="approved" if action=="approve" else "rejected"
    mutate(fn); return redirect("/admin")
@app.route("/admin/delete_post/<pid>",methods=["POST"])
def admin_delete_post(pid):
    if not session.get("admin_ok"): return redirect("/admin")
    mutate(lambda d:d.update({"posts":[p for p in d.get("posts",[]) if p.get("id")!=pid]})); return redirect("/admin")

@app.route("/admin/clear_global_chat",methods=["POST"])
def admin_clear_global_chat():
    if not session.get("admin_ok"): return redirect("/admin")
    mutate(lambda d:d.update({"global_chat":[]}))
    return redirect("/admin")

@app.route("/admin/clear_closed",methods=["POST"])
def admin_clear_closed():
    if not session.get("admin_ok"): return redirect("/admin")
    mutate(lambda d:d.update({"posts":[p for p in d.get("posts",[]) if not p.get("closed")]})); return redirect("/admin")
@app.route("/health")
def health(): return jsonify(ok=True, time=now_text(), online=online_count())

@app.route("/manifest.json")
def manifest(): return jsonify({"name":"월하 연가 연희 파티모집","short_name":"파티모집","start_url":"/","display":"standalone","background_color":"#0b1020","theme_color":"#0b1020","icons":[]})
@app.route("/sw.js")
def sw(): return app.response_class("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());",mimetype="application/javascript")
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","7777")),debug=False,threaded=True)
