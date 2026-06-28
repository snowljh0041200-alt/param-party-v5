
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json, os, uuid, tempfile, threading, html

app = Flask(__name__)

DATA_FILE = "data.json"
LOCK = threading.Lock()
AUTO_DELETE_HOURS = 1
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")
ONLINE_USERS = {}

HUNTING = ["도삭산 900층", "흉노족", "선비족"]
FARMING = ["해골왕", "어금니"]
QUEST600 = ["800층 600퀘", "900층 600퀘", "선비족 600퀘"]
FILTERS = ["전체", "사냥", "파밍", "600퀘", "도삭산 900층", "흉노족", "선비족", "해골왕", "어금니"]
JOBS = [
    "전사","검객","검제","검황","검성",
    "도적","자객","진검","귀검","태성",
    "주술사","술사","현사","현인","현자",
    "도사","도인","명인","진인","진선"
]

def esc(v):
    return html.escape(str(v or ""), quote=True)

def now_text():
    return datetime.now().strftime("%m/%d %H:%M")

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def parse_iso(v):
    try:
        return datetime.fromisoformat(v) if v else None
    except Exception:
        return None

def load_raw():
    if not os.path.exists(DATA_FILE):
        return {"posts": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("posts", [])
            return data
    except Exception:
        return {"posts": []}

def save_raw(data):
    fd, tmp = tempfile.mkstemp(prefix="baram_", suffix=".json", dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def cleanup(data):
    cutoff = datetime.now() - timedelta(hours=AUTO_DELETE_HOURS)
    kept = []
    for post in data.get("posts", []):
        closed_at = parse_iso(post.get("closed_at", ""))
        if post.get("closed") and closed_at and closed_at <= cutoff:
            continue
        post["chats"] = post.get("chats", [])[-100:]
        kept.append(post)
    data["posts"] = kept
    return data

def load_data():
    with LOCK:
        data = cleanup(load_raw())
        save_raw(data)
        return data

def mutate(fn):
    with LOCK:
        data = cleanup(load_raw())
        result = fn(data)
        save_raw(data)
        return result

def find_post(data, post_id):
    for post in data.get("posts", []):
        if post.get("id") == post_id:
            return post
    return None

def filled_total(post):
    slots = post.get("slots", [])
    filled = sum(1 for s in slots if s.get("char"))
    return filled, len(slots)

def is_full(post):
    f, t = filled_total(post)
    return t > 0 and f >= t

def ensure_closed(post):
    if is_full(post) and not post.get("closed"):
        post["closed"] = True
        post["closed_at"] = now_iso()

def post_status(post):
    return "모집완료" if post.get("closed") or is_full(post) else "모집중"

def post_time(post):
    start = (post.get("start_period", "") + " " + post.get("start_time", "")).strip()
    end = (post.get("end_period", "") + " " + post.get("end_time", "")).strip()
    if start and end:
        return f"{start} ~ {end}"
    return start or end or "시간 미정"

def closed_left(post):
    if not post.get("closed"):
        return ""
    closed_at = parse_iso(post.get("closed_at", ""))
    if not closed_at:
        return "1시간 뒤 자동삭제"
    left = int(((closed_at + timedelta(hours=AUTO_DELETE_HOURS)) - datetime.now()).total_seconds() // 60)
    return "곧 삭제" if left <= 0 else f"{left}분 뒤 자동삭제"

def can_chat(post, client_id):
    if not client_id:
        return False
    if post.get("owner_id") == client_id:
        return True
    return any(s.get("participant_id") == client_id for s in post.get("slots", []))

def can_manage(post, client_id, admin_pw=""):
    if post.get("owner_id") == client_id:
        return True
    if admin_pw and admin_pw == ADMIN_PASSWORD:
        return True
    return False

def place_select(post_type, form):
    if post_type == "사냥":
        return form.get("place_hunting", "")
    if post_type == "파밍":
        return form.get("place_farming", "")
    return form.get("place_quest", "")

def update_post_from_form(post, form):
    post_type = form.get("type", "사냥")
    post.update({
        "owner": form.get("owner", "").strip(),
        "owner_id": form.get("owner_id", "").strip() or post.get("owner_id", ""),
        "type": post_type,
        "place": place_select(post_type, form),
        "channel": "".join([c for c in form.get("channel", "") if c.isdigit()])[:4],
        "start_period": form.get("start_period", ""),
        "start_time": form.get("start_time", "").strip(),
        "end_period": form.get("end_period", ""),
        "end_time": form.get("end_time", "").strip(),
        "memo": form.get("memo", "").strip(),
    })
    jobs = form.getlist("slots")
    chars = form.getlist("slot_chars")
    participant_ids = form.getlist("slot_participant_ids")
    slots = []
    for i, job in enumerate(jobs):
        slots.append({
            "id": str(uuid.uuid4()),
            "job": job,
            "char": chars[i] if i < len(chars) else "",
            "participant_id": participant_ids[i] if i < len(participant_ids) else "",
        })
    post["slots"] = slots
    if is_full(post):
        ensure_closed(post)
    else:
        post["closed"] = False
        post["closed_at"] = ""

def render_posts(posts):
    if not posts:
        return '<div class="empty">현재 모집글이 없습니다.</div>'
    html_parts = []
    for post in posts:
        pid = esc(post.get("id"))
        owner_id = esc(post.get("owner_id"))
        participant_ids = "|".join([s.get("participant_id", "") for s in post.get("slots", []) if s.get("participant_id")])
        filled, total = filled_total(post)
        status = post_status(post)
        chat_count = len(post.get("chats", []))
        slot_rows = []
        copy_lines = [f"[{post.get('type','')}] {post.get('place','')}", f"채널 {post.get('channel') or '미정'}", post_time(post)]
        for slot in post.get("slots", []):
            sid = esc(slot.get("id"))
            job = esc(slot.get("job"))
            char = esc(slot.get("char"))
            part_id = esc(slot.get("participant_id"))
            copy_lines.append(f"{slot.get('job')} - {slot.get('char') or '모집중'}")
            if char:
                slot_rows.append(f'''<div class="slot filled" data-participant-id="{part_id}"><div><b>{job}</b><br><span>✅ {char}</span></div><button class="small danger participant-action" onclick="leaveSlot('{pid}','{sid}')">비우기</button></div>''')
            else:
                slot_rows.append(f'''<div class="slot"><div><b>{job}</b><br><span>⭕ 모집중</span></div><button class="small ok" onclick="joinSlot('{pid}','{sid}','{job}')">참여</button></div>''')
        left = closed_left(post)
        left_html = f'<div class="left-time">{esc(left)}</div>' if left else ""
        memo_html = f'<div class="memo">메모: {esc(post.get("memo"))}</div>' if post.get("memo") else ""
        copy_text = esc("\\n".join(copy_lines))
        html_parts.append(f'''
        <div class="card post" data-post-id="{pid}" data-owner-id="{owner_id}" data-participant-ids="{esc(participant_ids)}" data-chat-count="{chat_count}" data-filled="{filled}">
            <div class="top">
                <span class="badge {'done' if status == '모집완료' else 'open'}">{status}</span>
                <span class="count">{filled}/{total}</span>
            </div>
            <h2>{esc(post.get("place"))}</h2>
            <div class="meta">채널 {esc(post.get("channel") or "미정")} · {esc(post_time(post))}</div>
            <div class="meta">작성자 {esc(post.get("owner"))} · {esc(post.get("created"))}</div>
            {memo_html}
            {left_html}
            <div class="slots">{''.join(slot_rows)}</div>
            <div class="actions">
                <button onclick="copyPost(`{copy_text}`)">복사</button>
                <button class="party-action" onclick="openChat('{pid}')">채팅 {chat_count}</button>
                <a class="owner-action btn" href="/edit/{pid}">수정</a>
                <button class="owner-action" onclick="closePost('{pid}')">마감</button>
                <button class="owner-action danger" onclick="deletePost('{pid}')">삭제</button>
                <button class="admin danger" onclick="adminDeletePost('{pid}')">관리자 삭제</button>
            </div>
        </div>
        ''')
    return "\n".join(html_parts)

PAGE = r'''
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>월하 · 연가 · 연희 파티모집 v6.1</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,#202847 0,#10121a 42%,#090b10 100%);color:#f2f3f7;font-family:-apple-system,BlinkMacSystemFont,"Malgun Gothic",Arial,sans-serif}
.wrap{max-width:820px;margin:0 auto;padding:14px 14px 90px}
.header{position:sticky;top:0;background:rgba(16,18,26,.92);backdrop-filter:blur(10px);padding:12px 0 10px;border-bottom:1px solid rgba(255,255,255,.08);z-index:5}
h1{font-size:22px;margin:0}.sub{color:#a8acba;font-size:13px}
.card{background:linear-gradient(180deg,#202437,#171a26);border:1px solid #39415b;border-radius:20px;padding:15px;margin:12px 0;box-shadow:0 10px 28px rgba(0,0,0,.28)}
.empty{background:#1b1e2b;border:1px dashed #48506b;border-radius:18px;padding:40px;text-align:center;color:#a8acba}
.row{display:flex;gap:8px;flex-wrap:wrap}
button,.btn{border:0;border-radius:14px;background:linear-gradient(180deg,#5876ff,#3e5dea);color:white;font-weight:900;padding:11px 13px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;min-height:42px;box-shadow:0 5px 14px rgba(0,0,0,.22)}
button.gray,.btn.gray{background:linear-gradient(180deg,#464d67,#34394e)}button.danger,.danger{background:linear-gradient(180deg,#e45a5a,#c94141)}button.ok{background:linear-gradient(180deg,#2dc76b,#1d9a51)}button.small{font-size:13px;padding:8px 10px;min-height:34px}
input,select,textarea{width:100%;background:#11131b;color:#f2f3f7;border:1px solid #444b63;border-radius:13px;padding:12px;margin:6px 0 12px;font-size:16px}
label{font-size:13px;color:#a8acba;font-weight:900}
.tabs{display:flex;gap:7px;overflow-x:auto;padding:10px 0}.tabs a{white-space:nowrap;color:#dce1ff;background:#171a25;border:1px solid #32384d;text-decoration:none;border-radius:999px;padding:8px 12px;font-weight:900;font-size:14px}.tabs a.on{background:#4b6bff;color:white}
.summary{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:10px}.box{background:#11131b;border:1px solid #30364b;border-radius:14px;text-align:center;padding:10px}.box b{font-size:22px;display:block}
.top{display:flex;justify-content:space-between;align-items:center}.badge{padding:5px 10px;border-radius:999px;font-size:13px;font-weight:900}.badge.open{background:#123f28;color:#a9ffc8}.badge.done{background:#4b1d1d;color:#ffd0d0}.count{background:#11131b;border:1px solid #30364b;border-radius:999px;padding:5px 10px;font-weight:900}
h2{margin:10px 0 5px;font-size:22px}.meta{color:#a8acba;font-size:14px;line-height:1.5}.memo{color:#ffd36b;font-size:14px;margin-top:4px}.left-time{color:#ffb3b3;font-size:13px;font-weight:900}
.slot{display:flex;justify-content:space-between;align-items:center;background:#121522;border:1px solid #38405a;border-radius:15px;padding:11px;margin:8px 0}.slot.filled{background:#152218;border-color:#285637}
.actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-top:10px}
.owner-action,.participant-action,.party-action{display:none!important}.owner-action.show,.participant-action.show,.party-action.show{display:inline-flex!important}
.hidden{display:none!important}.time-row{display:grid;grid-template-columns:82px 1fr;gap:8px}.quick{display:grid;grid-template-columns:1fr auto;gap:8px}
.fab{position:fixed;right:18px;bottom:18px;border-radius:50%;width:58px;height:58px;font-size:30px}.alarm{position:fixed;left:14px;bottom:22px;z-index:40;background:#31364a}
.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#252b3d;border:1px solid #56607d;border-radius:999px;padding:10px 16px;opacity:0;transition:.2s;z-index:999;font-weight:900}.toast.show{opacity:1}
.my-only .post:not(.mine){display:none}.modal{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;z-index:100}.modal.show{display:flex}.panel{width:100%;max-width:820px;margin:0 auto;background:#161925;border:1px solid #30364b;border-radius:20px 20px 0 0;padding:14px}
.chat-list{background:#10121a;border:1px solid #30364b;border-radius:14px;height:330px;overflow-y:auto;padding:10px}.msg{background:#222638;border-radius:12px;padding:8px 10px;margin:6px 0}.msg.mine{background:#173822;border:1px solid #2e7146}.msg-meta{font-size:12px;color:#a8acba}.chat-form{display:grid;grid-template-columns:90px 1fr 70px;gap:7px;margin-top:8px}.chat-form input{margin:0}
@media(max-width:560px){.actions{grid-template-columns:1fr 1fr}.chat-form{grid-template-columns:1fr}.row>*{flex:1}.summary{grid-template-columns:1fr 1fr 1fr}.box{padding:8px 5px}.box b{font-size:20px}}
</style>
</head>
<body>
<div class="wrap">
<div class="header"><h1>🏹 월하 · 연가 · 연희 파티모집 v6.1</h1><div class="sub">파티모집 v6.1 · 현재 접속인원 표시</div></div>
{% if page == "home" %}
<div class="card"><div class="row"><a class="btn" href="/new">+ 구인글</a><a class="btn gray" href="/profile">내 캐릭터</a><button class="gray" onclick="toggleMy()">내 참여/내 글</button></div><div class="summary"><div class="box"><b>{{ open_count }}</b><span>모집중</span></div><div class="box"><b id="onlineCount">1</b><span>접속중</span></div><div class="box"><b id="myCount">0</b><span>내 글/참여</span></div></div><div class="tabs">{% for f in filters %}<a class="{% if filter_value == f %}on{% endif %}" href="/?filter={{ f }}">{{ f }}</a>{% endfor %}</div></div>
<div id="postList">{{ post_list|safe }}</div><a class="btn fab" href="/new">+</a>
{% endif %}
{% if page in ["new","edit"] %}
<div class="card"><h2>{% if page == "edit" %}모집글 수정{% else %}구인글 올리기{% endif %}</h2>
<form method="post" action="{% if page == 'edit' %}/edit/{{ post.id }}{% else %}/create{% endif %}" onsubmit="return prepareSubmit()">
<input type="hidden" name="owner_id" id="ownerIdInput"><label>작성자 닉네임</label><input name="owner" required placeholder="예: 역인" value="{{ post.owner if post else '' }}">
<label>종류</label><select name="type" id="typeSelect" onchange="updatePlaces()">{% for t in ["사냥","파밍","600퀘"] %}<option {% if post and post.type == t %}selected{% endif %}>{{ t }}</option>{% endfor %}</select>
<label>장소</label><select name="place_hunting" id="place_사냥" class="place-select">{% for p in hunting %}<option {% if post and post.place == p %}selected{% endif %}>{{ p }}</option>{% endfor %}</select><select name="place_farming" id="place_파밍" class="place-select hidden">{% for p in farming %}<option {% if post and post.place == p %}selected{% endif %}>{{ p }}</option>{% endfor %}</select><select name="place_quest" id="place_600퀘" class="place-select hidden">{% for p in quest600 %}<option {% if post and post.place == p %}selected{% endif %}>{{ p }}</option>{% endfor %}</select>
<label>채널 4자리</label><input name="channel" id="channelInput" maxlength="4" inputmode="numeric" pattern="[0-9]*" placeholder="예: 3385" value="{{ post.channel if post else '' }}" oninput="this.value=this.value.replace(/[^0-9]/g,\'\').slice(0,4)">
<label>시작시간</label><div class="time-row"><select name="start_period"><option {% if post and post.start_period == "오전" %}selected{% endif %}>오전</option><option {% if post and post.start_period == "오후" %}selected{% endif %}>오후</option></select><input name="start_time" placeholder="예: 09:00" value="{{ post.start_time if post else '' }}"></div>
<label>종료시간</label><div class="time-row"><select name="end_period"><option {% if post and post.end_period == "오전" %}selected{% endif %}>오전</option><option {% if not post or post.end_period == "오후" %}selected{% endif %}>오후</option></select><input name="end_time" placeholder="예: 11:00" value="{{ post.end_time if post else '' }}"></div>
<label>메모</label><textarea name="memo" rows="2">{{ post.memo if post else '' }}</textarea>
<div class="card"><label>모집 자리 추가</label><div class="quick"><select id="slotJob">{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button type="button" class="ok" onclick="addSlot()">추가</button></div><div id="slotsBox">{% if post %}{% for s in post.slots %}<div class="slot"><div><b>{{ s.job }}</b><br><span>{{ s.char }}</span></div><button type="button" class="small danger" onclick="this.parentElement.remove()">삭제</button><input type="hidden" name="slots" value="{{ s.job }}"><input type="hidden" name="slot_chars" value="{{ s.char }}"><input type="hidden" name="slot_participant_ids" value="{{ s.participant_id }}"></div>{% endfor %}{% endif %}</div></div>
<button style="width:100%" type="submit">저장하기</button><a class="btn gray" style="width:100%;margin-top:8px" href="/">취소</a>
</form></div>
{% endif %}
{% if page == "profile" %}
<div class="card"><h2>내 캐릭터</h2><label>캐릭터명</label><input id="charName" placeholder="예: 역인"><label>직업/차수</label><select id="charJob">{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button onclick="saveChar()" style="width:100%">캐릭터 추가</button><a class="btn gray" style="width:100%;margin-top:8px" href="/">메인으로</a><div id="charList"></div></div>
{% endif %}
</div>
<button id="alarmBtn" class="alarm" onclick="toggleAlarm()">🔔 알림 ON</button>
<div id="chatModal" class="modal" onclick="if(event.target.id==='chatModal')closeChat()"><div class="panel"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><b>💬 파티채팅</b><button class="small gray" onclick="closeChat()">닫기</button></div><div id="chatList" class="chat-list"></div><div class="chat-form"><input id="chatName" placeholder="닉네임" maxlength="12"><input id="chatText" placeholder="메시지" maxlength="120" onkeydown="if(event.key==='Enter')sendChat()"><button onclick="sendChat()">전송</button></div></div></div>
<div id="toast" class="toast"></div>
<script>
function id(){let v=localStorage.getItem("baram_client_id");if(!v){v=(crypto&&crypto.randomUUID)?crypto.randomUUID():"id_"+Date.now()+"_"+Math.random();localStorage.setItem("baram_client_id",v)}return v}
function toast(m){let t=document.getElementById("toast");t.textContent=m;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),1600)}
function prepareSubmit(){document.getElementById("ownerIdInput").value=id();let ch=document.getElementById("channelInput");ch.value=(ch.value||"").replace(/[^0-9]/g,"").slice(0,4);if(ch.value.length!==4){alert("채널은 숫자 4자리로 입력해줘.");ch.focus();return false}return true}
function updatePlaces(){let t=document.getElementById("typeSelect");if(!t)return;document.querySelectorAll(".place-select").forEach(x=>x.classList.add("hidden"));let x=document.getElementById("place_"+t.value);if(x)x.classList.remove("hidden")}
function addSlot(){let j=document.getElementById("slotJob").value;let box=document.getElementById("slotsBox");let d=document.createElement("div");d.className="slot";d.innerHTML="<div><b>"+j+"</b><br><span>빈자리</span></div><button type='button' class='small danger' onclick='this.parentElement.remove()'>삭제</button><input type='hidden' name='slots' value='"+j+"'><input type='hidden' name='slot_chars' value=''><input type='hidden' name='slot_participant_ids' value=''>";box.appendChild(d)}
function chars(){return JSON.parse(localStorage.getItem("baram_chars")||"[]")}
function setChars(v){localStorage.setItem("baram_chars",JSON.stringify(v));renderChars()}
function saveChar(){let n=document.getElementById("charName").value.trim();let j=document.getElementById("charJob").value;if(!n)return alert("캐릭터명 입력");let c=chars();c.push({name:n,job:j});setChars(c);document.getElementById("charName").value="";toast("저장됨")}
function delChar(i){let c=chars();c.splice(i,1);setChars(c)}
function renderChars(){let b=document.getElementById("charList");if(!b)return;let c=chars();b.innerHTML=c.length?c.map((x,i)=>"<div class='slot'><div><b>"+x.name+"</b><br>"+x.job+"</div><button class='small danger' onclick='delChar("+i+")'>삭제</button></div>").join(""):"<div class='card'>등록된 캐릭터 없음</div>"}
function apply(){let cid=id();document.querySelectorAll(".post").forEach(p=>{let owner=p.dataset.ownerId===cid;let parts=(p.dataset.participantIds||"").split("|").filter(Boolean);let inParty=owner||parts.includes(cid);p.classList.toggle("mine",inParty);p.querySelectorAll(".owner-action").forEach(b=>b.classList.toggle("show",owner));p.querySelectorAll(".party-action").forEach(b=>b.classList.toggle("show",inParty));p.querySelectorAll(".slot").forEach(s=>{let can=owner||(s.dataset.participantId===cid);s.querySelectorAll(".participant-action").forEach(b=>b.classList.toggle("show",can))})});let mc=document.getElementById("myCount");if(mc)mc.textContent=document.querySelectorAll(".post.mine").length}
function toggleMy(){document.body.classList.toggle("my-only");apply()}
function refresh(){if(location.pathname!=="/")return;fetch("/api/posts"+location.search).then(r=>r.text()).then(h=>{document.getElementById("postList").innerHTML=h;apply()})}
function copyPost(t){navigator.clipboard?navigator.clipboard.writeText(t).then(()=>toast("복사됨")):alert(t)}
function joinSlot(pid,sid,job){let m=chars().filter(c=>c.job===job);let name=m.length===1?m[0].name:prompt(job+" 참여 캐릭터명");if(!name)return;fetch("/join",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({post_id:pid,slot_id:sid,char:name,participant_id:id()})}).then(()=>{toast("참여됨");refresh()})}
function leaveSlot(pid,sid){if(!confirm("비울까?"))return;fetch("/leave",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({post_id:pid,slot_id:sid,client_id:id()})}).then(()=>refresh())}
function closePost(pid){if(!confirm("마감할까?"))return;fetch("/close",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({post_id:pid,owner_id:id(),admin_pw:""})}).then(r=>r.json()).then(x=>{toast(x.ok?"마감됨":x.reason);refresh()})}
function deletePost(pid){if(!confirm("삭제할까?"))return;fetch("/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({post_id:pid,owner_id:id(),admin_pw:""})}).then(r=>r.json()).then(x=>{toast(x.ok?"삭제됨":x.reason);refresh()})}
function adminDeletePost(pid){let pw=prompt("관리자 비밀번호");if(!pw)return;fetch("/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({post_id:pid,owner_id:id(),admin_pw:pw})}).then(r=>r.json()).then(x=>{toast(x.ok?"관리삭제됨":x.reason);refresh()})}
let currentChat=null;
function openChat(pid){currentChat=pid;document.getElementById("chatModal").classList.add("show");let n=localStorage.getItem("baram_chat_name");if(n)document.getElementById("chatName").value=n;refreshChat()}
function closeChat(){currentChat=null;document.getElementById("chatModal").classList.remove("show")}
function refreshChat(){if(!currentChat)return;fetch("/api/chat/"+currentChat+"?client_id="+encodeURIComponent(id())).then(r=>r.text()).then(h=>{let b=document.getElementById("chatList");b.innerHTML=h;b.scrollTop=b.scrollHeight})}
function sendChat(){if(!currentChat)return;let n=document.getElementById("chatName");let t=document.getElementById("chatText");if(!t.value.trim())return;if(n.value.trim())localStorage.setItem("baram_chat_name",n.value.trim());fetch("/chat/"+currentChat,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({client_id:id(),name:n.value.trim()||"익명",text:t.value.trim()})}).then(r=>r.json()).then(x=>{if(!x.ok)return toast("참여자만 이용 가능");t.value="";refreshChat();refresh()})}
function alarmOn(){return localStorage.getItem("baram_alarm_off")!=="1"}function toggleAlarm(){localStorage.setItem("baram_alarm_off",alarmOn()?"1":"0");document.getElementById("alarmBtn").textContent=alarmOn()?"🔔 알림 ON":"🔕 알림 OFF"}document.getElementById("alarmBtn").textContent=alarmOn()?"🔔 알림 ON":"🔕 알림 OFF";
function heartbeat(){fetch("/api/heartbeat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({client_id:id()})}).then(r=>r.json()).then(x=>{let o=document.getElementById("onlineCount");if(o)o.textContent=x.online||1}).catch(()=>{})}
setInterval(refresh,2500);setInterval(refreshChat,1800);setInterval(heartbeat,15000);renderChars();updatePlaces();apply();heartbeat();
</script>
</body>
</html>
'''

@app.route("/")
def home():
    filt = request.args.get("filter", "전체")
    data = load_data()
    posts = list(reversed(data.get("posts", [])))
    if filt != "전체":
        posts = [p for p in posts if p.get("type") == filt or p.get("place") == filt]
    open_count = sum(1 for p in posts if post_status(p) == "모집중")
    return render_template_string(PAGE, page="home", filters=FILTERS, filter_value=filt, post_list=render_posts(posts), open_count=open_count, jobs=JOBS, hunting=HUNTING, farming=FARMING, quest600=QUEST600)

@app.route("/api/posts")
def api_posts():
    filt = request.args.get("filter", "전체")
    data = load_data()
    posts = list(reversed(data.get("posts", [])))
    if filt != "전체":
        posts = [p for p in posts if p.get("type") == filt or p.get("place") == filt]
    return render_posts(posts)

@app.route("/new")
def new():
    return render_template_string(PAGE, page="new", post=None, jobs=JOBS, hunting=HUNTING, farming=FARMING, quest600=QUEST600)

@app.route("/profile")
def profile():
    return render_template_string(PAGE, page="profile", jobs=JOBS)

@app.route("/create", methods=["POST"])
def create():
    def fn(data):
        post = {"id": str(uuid.uuid4()), "created": now_text(), "closed": False, "closed_at": "", "chats": []}
        update_post_from_form(post, request.form)
        data["posts"].append(post)
    mutate(fn)
    return '<script>location.href="/"</script>'

@app.route("/edit/<post_id>", methods=["GET", "POST"])
def edit(post_id):
    if request.method == "GET":
        post = find_post(load_data(), post_id)
        if not post:
            return "not found", 404
        return render_template_string(PAGE, page="edit", post=post, jobs=JOBS, hunting=HUNTING, farming=FARMING, quest600=QUEST600)
    def fn(data):
        post = find_post(data, post_id)
        if post and can_manage(post, request.form.get("owner_id", "")):
            update_post_from_form(post, request.form)
    mutate(fn)
    return '<script>location.href="/"</script>'

@app.route("/join", methods=["POST"])
def join():
    req = request.get_json(force=True)
    def fn(data):
        post = find_post(data, req.get("post_id"))
        if not post or post.get("closed"):
            return
        cid = (req.get("participant_id") or "").strip()
        char = (req.get("char") or "").strip()
        if not cid or not char:
            return
        if any(s.get("participant_id") == cid or s.get("char") == char for s in post.get("slots", [])):
            return
        for slot in post.get("slots", []):
            if slot.get("id") == req.get("slot_id") and not slot.get("char"):
                slot["char"] = char
                slot["participant_id"] = cid
                ensure_closed(post)
                return
    mutate(fn)
    return jsonify(ok=True)

@app.route("/leave", methods=["POST"])
def leave():
    req = request.get_json(force=True)
    cid = req.get("client_id", "")
    def fn(data):
        post = find_post(data, req.get("post_id"))
        if not post:
            return
        owner = post.get("owner_id") == cid
        for slot in post.get("slots", []):
            if slot.get("id") == req.get("slot_id") and (owner or slot.get("participant_id") == cid):
                slot["char"] = ""
                slot["participant_id"] = ""
                post["closed"] = False
                post["closed_at"] = ""
                return
    mutate(fn)
    return jsonify(ok=True)

@app.route("/close", methods=["POST"])
def close():
    req = request.get_json(force=True)
    result = {"ok": False, "reason": "작성자 또는 관리자만 가능"}
    def fn(data):
        post = find_post(data, req.get("post_id"))
        if post and can_manage(post, req.get("owner_id", ""), req.get("admin_pw", "")):
            post["closed"] = True
            post["closed_at"] = now_iso()
            result["ok"] = True
            result["reason"] = "마감됨"
    mutate(fn)
    return jsonify(result)

@app.route("/delete", methods=["POST"])
def delete():
    req = request.get_json(force=True)
    result = {"ok": False, "reason": "작성자 또는 관리자만 가능"}
    def fn(data):
        post_id = req.get("post_id")
        owner_id = req.get("owner_id", "")
        admin_pw = req.get("admin_pw", "")
        kept = []
        for post in data.get("posts", []):
            if post.get("id") == post_id and can_manage(post, owner_id, admin_pw):
                result["ok"] = True
                result["reason"] = "삭제됨"
                continue
            kept.append(post)
        data["posts"] = kept
    mutate(fn)
    return jsonify(result)

@app.route("/api/chat/<post_id>")
def api_chat(post_id):
    cid = request.args.get("client_id", "")
    post = find_post(load_data(), post_id)
    if not post:
        return '<div class="msg">글이 없습니다.</div>'
    if not can_chat(post, cid):
        return '<div class="msg">참여자만 이용 가능합니다.</div>'
    chats = post.get("chats", [])[-80:]
    if not chats:
        return '<div class="msg">아직 메시지가 없습니다.</div>'
    rows = []
    for c in chats:
        mine = " mine" if c.get("client_id") == cid else ""
        rows.append(f'<div class="msg{mine}"><div class="msg-meta">{esc(c.get("name"))} · {esc(c.get("time"))}</div><div>{esc(c.get("text"))}</div></div>')
    return "\n".join(rows)

@app.route("/chat/<post_id>", methods=["POST"])
def chat(post_id):
    req = request.get_json(force=True)
    cid = (req.get("client_id") or "").strip()
    text = (req.get("text") or "").strip()[:120]
    name = (req.get("name") or "익명").strip()[:12]
    result = {"ok": False}
    if not text:
        return jsonify(result)
    def fn(data):
        post = find_post(data, post_id)
        if post and can_chat(post, cid):
            post.setdefault("chats", []).append({"client_id": cid, "name": name, "text": text, "time": datetime.now().strftime("%H:%M")})
            post["chats"] = post["chats"][-100:]
            result["ok"] = True
    mutate(fn)
    return jsonify(result)


@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    req = request.get_json(force=True, silent=True) or {}
    client_id = (req.get("client_id") or "").strip()
    if client_id:
        ONLINE_USERS[client_id] = datetime.now()
    cutoff = datetime.now() - timedelta(seconds=70)
    for key, last_seen in list(ONLINE_USERS.items()):
        if last_seen < cutoff:
            ONLINE_USERS.pop(key, None)
    return jsonify(ok=True, online=max(1, len(ONLINE_USERS)))

@app.route("/api/online")
def online():
    cutoff = datetime.now() - timedelta(seconds=70)
    for key, last_seen in list(ONLINE_USERS.items()):
        if last_seen < cutoff:
            ONLINE_USERS.pop(key, None)
    return jsonify(online=max(1, len(ONLINE_USERS)))

@app.route("/manifest.json")
def manifest():
    return jsonify({"name": "월하 · 연가 · 연희 파티모집 v6.1", "short_name": "파티모집", "start_url": "/", "display": "standalone", "background_color": "#10121a", "theme_color": "#10121a", "icons": []})

@app.route("/sw.js")
def sw():
    return app.response_class("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());", mimetype="application/javascript")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7777")), debug=False, threaded=True)
