
from flask import Flask, request, jsonify, render_template_string, redirect, session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, uuid, tempfile, html, threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v12-final-secret")

KST = ZoneInfo("Asia/Seoul")
DATA_FILE = "data.json"
LOCK = threading.Lock()

DEFAULT_ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "moon")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")

POST_AUTO_DELETE_HOURS = 1
ONLINE_SECONDS = 90
GLOBAL_CHAT_LIMIT = 100
GLOBAL_CHAT_RETENTION_HOURS = 24
GLOBAL_CHAT_DELETE_MINUTES = 5

ONLINE_USERS = {}

JOBS = [
    "검성","검황","검제","전사","검객",
    "태성","귀검","진검","도적","자객",
    "현자","현인","현사","주술사","술사",
    "진선","진인","명인","도사","도인"
]
FILTERS = ["전체", "사냥", "파밍", "600퀘"]
PLACES = {
    "사냥": ["도삭산 900층", "흉노족", "선비족"],
    "파밍": ["해골왕", "어금니"],
    "600퀘": ["800층 600퀘", "900층 600퀘", "선비족 600퀘"]
}
DEFAULT_FARMING_ITEMS = {
    "해골왕": ["해뼈"],
    "어금니": ["흑룡 어금니", "묵룡 어금니", "진룡 어금니", "감룡 어금니"]
}

def now():
    return datetime.now(KST)

def now_iso():
    return now().isoformat(timespec="seconds")

def now_text():
    return now().strftime("%m/%d %H:%M")

def chat_time():
    return now().strftime("%H:%M")

def parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        return dt
    except Exception:
        return None

def esc(value):
    return html.escape(str(value or ""), quote=True)

def only_digits(value, limit=None):
    s = "".join(ch for ch in str(value or "") if ch.isdigit())
    return s[:limit] if limit else s

def default_data():
    return {
        "settings": {
            "access_password": DEFAULT_ACCESS_PASSWORD,
            "admin_password": DEFAULT_ADMIN_PASSWORD,
            "notice": "",
            "farming_items": DEFAULT_FARMING_ITEMS
        },
        "users": [],
        "posts": [],
        "global_chat": []
    }

def read_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_data()
    data.setdefault("settings", {})
    data["settings"].setdefault("access_password", DEFAULT_ACCESS_PASSWORD)
    data["settings"].setdefault("admin_password", DEFAULT_ADMIN_PASSWORD)
    data["settings"].setdefault("notice", "")
    data["settings"].setdefault("farming_items", DEFAULT_FARMING_ITEMS)
    data.setdefault("users", [])
    data.setdefault("posts", [])
    data.setdefault("global_chat", [])
    return data

def write_data(data):
    fd, tmp = tempfile.mkstemp(prefix="baram_party_", suffix=".json", dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def cleanup_data(data):
    # 사냥/600퀘 마감글만 자동 삭제. 파밍은 영구 보관.
    cutoff_post = now() - timedelta(hours=POST_AUTO_DELETE_HOURS)
    keep_posts = []
    for post in data.get("posts", []):
        post.setdefault("category", "사냥")
        post.setdefault("farming_participants", [])
        post.setdefault("farming_share_ids", [])
        post.setdefault("party_chat", [])
        closed_at = parse_dt(post.get("closed_at"))
        if post.get("category") != "파밍" and post.get("closed") and closed_at and closed_at <= cutoff_post:
            continue
        post["party_chat"] = post.get("party_chat", [])[-100:]
        keep_posts.append(post)
    data["posts"] = keep_posts

    # 통합채팅 24시간 / 최근 100개
    cutoff_chat = now() - timedelta(hours=GLOBAL_CHAT_RETENTION_HOURS)
    keep_chat = []
    for msg in data.get("global_chat", []):
        msg.setdefault("id", str(uuid.uuid4()))
        created_at = parse_dt(msg.get("created_at"))
        if created_at is None:
            msg["created_at"] = now_iso()
            keep_chat.append(msg)
        elif created_at >= cutoff_chat:
            keep_chat.append(msg)
    data["global_chat"] = keep_chat[-GLOBAL_CHAT_LIMIT:]
    return data

def load_data():
    with LOCK:
        data = cleanup_data(read_data())
        write_data(data)
        return data

def mutate(fn):
    with LOCK:
        data = cleanup_data(read_data())
        result = fn(data)
        write_data(data)
        return result

def current_uid():
    return session.get("uid")

def find_user(data, uid):
    for user in data.get("users", []):
        if user.get("id") == uid:
            return user
    return None

def current_user(data):
    uid = current_uid()
    return find_user(data, uid) if uid else None

def approved_user(user):
    return bool(user and user.get("status") == "approved" and not user.get("blocked"))

def approved_chars(user):
    return [c for c in (user or {}).get("chars", []) if c.get("status") == "approved"]

def selected_char(user):
    chars = approved_chars(user)
    if not chars:
        return None
    selected_id = user.get("selected_char_id")
    for c in chars:
        if c.get("id") == selected_id:
            return c
    return chars[0]

def char_label(ch):
    if not ch:
        return ""
    return f"{ch.get('name','')}({ch.get('job','')})"

def all_char_names(data):
    names = set()
    for user in data.get("users", []):
        for ch in user.get("chars", []):
            names.add(str(ch.get("name", "")).strip().lower())
    return names

def user_has_char(user, char_id):
    for ch in approved_chars(user):
        if ch.get("id") == char_id:
            return ch
    return None

def can_enter_site(data):
    user = current_user(data)
    return bool(session.get("access_ok")) or approved_user(user)

def touch_online():
    key = current_uid() or session.get("guest_id")
    if not key:
        key = str(uuid.uuid4())
        session["guest_id"] = key
    ONLINE_USERS[key] = now()

def online_count():
    cutoff = now() - timedelta(seconds=ONLINE_SECONDS)
    for key, last in list(ONLINE_USERS.items()):
        try:
            if last.tzinfo is None:
                last = last.replace(tzinfo=KST)
            if last < cutoff:
                ONLINE_USERS.pop(key, None)
        except Exception:
            ONLINE_USERS.pop(key, None)
    return max(1, len(ONLINE_USERS))

def find_post(data, post_id):
    for post in data.get("posts", []):
        if post.get("id") == post_id:
            return post
    return None

def filled_total(post):
    if post.get("category") == "파밍":
        total = len(post.get("farming_participants", []))
        return total, total
    slots = post.get("slots", [])
    filled = sum(1 for s in slots if s.get("char_id") or s.get("external_label"))
    return filled, len(slots)

def post_is_full(post):
    if post.get("category") == "파밍":
        return False
    filled, total = filled_total(post)
    return total > 0 and filled >= total

def ensure_closed_if_full(post):
    if post_is_full(post) and not post.get("closed"):
        post["closed"] = True
        post["closed_at"] = now_iso()

def post_status(post):
    if post.get("category") == "파밍":
        return post.get("farming_status", "진행중")
    return "마감" if post.get("closed") or post_is_full(post) else "모집중"

def post_time_text(post):
    start = (post.get("start_period", "") + " " + post.get("start_time", "")).strip()
    end = (post.get("end_period", "") + " " + post.get("end_time", "")).strip()
    if start and end:
        return f"{start} ~ {end}"
    return start or end or "시간 미정"

def closed_left_text(post):
    if post.get("category") == "파밍":
        return ""
    if not post.get("closed"):
        return ""
    closed_at = parse_dt(post.get("closed_at"))
    if not closed_at:
        return "1시간 뒤 자동삭제"
    left = int(((closed_at + timedelta(hours=POST_AUTO_DELETE_HOURS)) - now()).total_seconds() // 60)
    if left <= 0:
        return "곧 자동삭제"
    return f"{left}분 뒤 자동삭제"

def can_party_chat(post, user):
    if not approved_user(user):
        return False
    if post.get("owner_uid") == user.get("id"):
        return True
    if post.get("category") == "파밍":
        return any(p.get("uid") == user.get("id") for p in post.get("farming_participants", []))
    return any(slot.get("uid") == user.get("id") for slot in post.get("slots", []))

def money_text(value):
    try:
        return f"{int(value):,}전"
    except Exception:
        return "0전"

def farming_calc(post):
    amount = int(post.get("sale_amount") or 0)
    share_ids = set(post.get("farming_share_ids", []))
    participants = [p for p in post.get("farming_participants", []) if p.get("id") in share_ids]
    count = len(participants)
    if amount <= 0 or count <= 0:
        return {"amount": amount, "count": count, "share": 0}
    return {"amount": amount, "count": count, "share": int(amount / count)}

def farming_status_badge(status):
    if status == "정산완료":
        return "✅ 정산완료"
    if status == "결과입력완료":
        return "🔵 결과입력완료"
    return "🟡 진행중"

def render_chat_rows(chats, uid, allow_delete=True):
    if not chats:
        return "<div class='msg'>아직 메시지가 없습니다.</div>"
    rows = []
    delete_deadline = now() - timedelta(minutes=GLOBAL_CHAT_DELETE_MINUTES)
    for msg in chats[-GLOBAL_CHAT_LIMIT:]:
        mine = " mine" if msg.get("uid") == uid else ""
        meta = f"{esc(msg.get('label'))} · {esc(msg.get('time'))}"
        delete_btn = ""
        created_at = parse_dt(msg.get("created_at"))
        if allow_delete and msg.get("uid") == uid and msg.get("id") and created_at and created_at >= delete_deadline:
            delete_btn = f"<button type='button' class='mini danger' onclick=\"deleteGlobalChat('{esc(msg.get('id'))}')\">삭제</button>"
        rows.append(f"<div class='msg{mine}'><div class='msg-meta'>{meta} {delete_btn}</div><div>{esc(msg.get('text'))}</div></div>")
    return "\n".join(rows)

def render_posts(posts, user, admin=False, farming_items=None):
    farming_items = farming_items or DEFAULT_FARMING_ITEMS
    if not posts:
        return "<div class='empty'>현재 모집글이 없습니다.</div>"

    uid = user.get("id") if user else ""
    html_rows = []
    for post in posts:
        pid = esc(post.get("id"))
        category = post.get("category", "사냥")
        status = post_status(post)
        filled, total = filled_total(post)

        if category == "파밍":
            participants = "|".join(p.get("uid", "") for p in post.get("farming_participants", []) if p.get("uid"))
        else:
            participants = "|".join(s.get("uid", "") for s in post.get("slots", []) if s.get("uid"))

        copy_lines = [
            f"[{category}] {post.get('place')}",
            f"채널 {post.get('channel') or '미정'}",
            post_time_text(post),
            f"작성자 {post.get('owner_label')}"
        ]

        body_html = ""
        owner_flag = "1" if post.get("owner_uid") == uid else "0"
        owner_or_admin = owner_flag == "1" or admin

        if category == "파밍":
            fp = post.get("farming_participants", [])
            share_ids = set(post.get("farming_share_ids", []))
            participant_rows = []
            for p in fp:
                checked = "checked" if p.get("id") in share_ids else ""
                participant_rows.append(
                    f"<label class='check-row'><input type='checkbox' name='share_ids' value='{esc(p.get('id'))}' {checked}> {esc(p.get('label'))}</label>"
                )
                copy_lines.append(f"참여 - {p.get('label')}")

            joined = any(p.get("uid") == uid for p in fp)
            join_btn = ""
            if not post.get("farming_status") == "정산완료":
                if joined:
                    join_btn = f"<button type='button' class='gray' onclick=\"leaveFarming('{pid}')\">참여취소</button>"
                else:
                    join_btn = f"<button type='button' class='ok' onclick=\"joinFarming('{pid}')\">참여하기</button>"

            result_html = ""
            if post.get("farming_result"):
                calc = farming_calc(post)
                if post.get("farming_result") == "득템":
                    result_html = f"""
                    <div class='notice'>
                    결과: <b>득템</b><br>
                    아이템: <b>{esc(post.get('farming_item'))}</b><br>
                    판매금액: <b>{money_text(post.get('sale_amount'))}</b><br>
                    분배대상: <b>{calc['count']}명</b><br>
                    1인당 분배금: <b>{money_text(calc['share'])}</b>
                    </div>
                    """
                else:
                    result_html = "<div class='notice'>결과: <b>노득</b></div>"

            manage_html = ""
            if owner_or_admin:
                items = farming_items.get(post.get("place"), DEFAULT_FARMING_ITEMS.get(post.get("place"), ["기타"]))
                item_options = "".join([f"<option {'selected' if x==post.get('farming_item') else ''}>{esc(x)}</option>" for x in items])
                participant_check_html = "".join(participant_rows) if participant_rows else "<p class='meta'>참여자가 없습니다.</p>"
                is_drop = post.get("farming_result") == "득템"
                drop_style = "" if is_drop else "display:none"
                result_select_id = "farmResult_" + post.get("id", "")
                drop_box_id = "farmDrop_" + post.get("id", "")
                manage_html = f"""
                <div class='farm-manage owner-only'>
                  <form method='post' action='/farming/result/{pid}'>
                    <label>파밍 결과</label>
                    <select name='farming_result' id='{result_select_id}' onchange="toggleFarmResultBox('{result_select_id}','{drop_box_id}')">
                      <option {'selected' if post.get('farming_result')=='노득' else ''}>노득</option>
                      <option {'selected' if post.get('farming_result')=='득템' else ''}>득템</option>
                    </select>
                    <div id='{drop_box_id}' style='{drop_style}'>
                      <label>득템 아이템</label>
                      <select name='farming_item'>{item_options}</select>
                      <label>판매금액</label>
                      <input name='sale_amount' inputmode='numeric' value='{esc(post.get('sale_amount'))}' placeholder='예: 26000000'>
                      <label>분배 대상자 체크</label>
                      <div class='check-box'>{participant_check_html}</div>
                    </div>
                    <button type='submit'>결과/분배 저장</button>
                  </form>
                  <form method='post' action='/farming/settle/{pid}' onsubmit="return confirm('정산완료 처리할까요?')">
                    <button class='ok' style='width:100%;margin-top:8px'>정산완료</button>
                  </form>
                </div>
                """

            part_list = "".join([f"<div class='member'>🟢 {esc(p.get('label'))}</div>" for p in fp]) or "<p class='meta'>아직 참여자가 없습니다.</p>"
            body_html = f"""
            <div class='notice'>{farming_status_badge(post.get('farming_status','진행중'))}</div>
            {result_html}
            <h3>참여자</h3>
            <div>{part_list}</div>
            <div class='actions farm-actions'>{join_btn}</div>
            {manage_html}
            """
        else:
            slot_rows = []
            for slot in post.get("slots", []):
                sid = esc(slot.get("id"))
                job = esc(slot.get("job"))
                label = esc(slot.get("char_label") or slot.get("external_label"))
                is_external = bool(slot.get("external_label"))
                copy_lines.append(f"{slot.get('job')} - {label or '모집중'}")
                if label:
                    mark = "🟡" if is_external else "✅"
                    mine_or_owner = slot.get("uid") == uid or owner_or_admin
                    leave_btn = f"<button type='button' class='mini danger' onclick=\"leaveSlot('{pid}','{sid}')\">비우기</button>" if mine_or_owner else ""
                    slot_rows.append(f"<div class='slot filled'><div><b>{job}</b><br><span>{mark} {label}</span></div>{leave_btn}</div>")
                else:
                    disabled = "disabled" if post.get("closed") else ""
                    external_btn = f"<button type='button' class='mini gray' onclick=\"addExternal('{pid}','{sid}')\">외부인</button>" if owner_or_admin else ""
                    slot_rows.append(f"<div class='slot'><div><b>{job}</b><br><span>⭕ 모집중</span></div><div>{external_btn}<button type='button' class='mini ok' {disabled} onclick=\"joinSlot('{pid}','{sid}','{job}')\">참여</button></div></div>")
            body_html = f"<div class='slots'>{''.join(slot_rows)}</div>"

        memo = f"<div class='memo'>📝 {esc(post.get('memo'))}</div>" if post.get("memo") else ""
        left = closed_left_text(post)
        left_html = f"<div class='left-time'>{esc(left)}</div>" if left else ""
        copy_text = esc("\n".join(copy_lines))
        count_text = f"{filled}" if category == "파밍" else f"{filled}/{total}"

        html_rows.append(f"""
        <article class='party-card post' data-post-id='{pid}' data-owner='{owner_flag}' data-participants='{esc(participants)}'>
          <div class='post-head'>
            <div>
              <span class='pill {"done" if status in ["마감","정산완료"] else "open"}'>{esc(status)}</span>
              <span class='pill type'>{esc(category)}</span>
            </div>
            <b class='count'>{count_text}</b>
          </div>
          <h2>{esc(post.get("place"))}</h2>
          <div class='meta'>📍 채널 <b>{esc(post.get("channel") or "미정")}</b> · ⏰ {esc(post_time_text(post))}</div>
          <div class='meta'>👑 {esc(post.get("owner_label"))} · {esc(post.get("created"))}</div>
          {memo}{left_html}
          {body_html}
          <div class='actions'>
            <button type='button' onclick="copyPost(`{copy_text}`)">복사</button>
            <button type='button' onclick="shareKakao(`{copy_text}`)">카톡공유</button>
            <button type='button' onclick="openPartyChat('{pid}')">채팅 {len(post.get("party_chat", []))}</button>
            <a class='btn gray owner-only' href='/edit/{pid}'>수정</a>
            <button type='button' class='owner-only danger' onclick="deletePost('{pid}')">삭제</button>
          </div>
        </article>
        """)
    return "\n".join(html_rows)

def member_html(data):
    rows = []
    online_ids = set(ONLINE_USERS.keys())
    for user in data.get("users", []):
        if user.get("status") != "approved" or user.get("blocked"):
            continue
        ch = selected_char(user)
        label = char_label(ch) if ch else user.get("account")
        mark = "🟢" if user.get("id") in online_ids else "⚫"
        rows.append(f"<div class='member'>{mark} {esc(label)}</div>")
    return "".join(rows) if rows else "<div class='member'>승인된 문파원이 없습니다.</div>"

CSS = """
*{box-sizing:border-box}body{margin:0;color:#eef2ff;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',Arial,sans-serif;background:#0b1020}body:before{content:'';position:fixed;inset:0;background:radial-gradient(circle at 20% 0%,#263c77 0,#111a34 38%,#090d18 78%);z-index:-1}.wrap{max-width:1040px;margin:0 auto;padding:18px 14px 100px}.header{padding:12px 0 16px;border-bottom:1px solid rgba(255,255,255,.11)}h1{font-size:28px;margin:0;letter-spacing:-.8px}.sub{color:#aeb8d7;font-size:13px;margin-top:4px}.panel,.party-card{background:rgba(20,27,48,.88);border:1px solid rgba(150,165,210,.22);box-shadow:0 18px 50px rgba(0,0,0,.32);border-radius:24px;padding:16px;margin:14px 0;backdrop-filter:blur(12px)}.top-actions{display:flex;gap:8px;flex-wrap:wrap}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.stat{background:rgba(7,11,22,.57);border:1px solid rgba(255,255,255,.10);border-radius:18px;text-align:center;padding:14px 8px}.stat b{font-size:28px;display:block}.stat span{font-size:12px;color:#aeb8d7}button,.btn{border:0;border-radius:15px;background:linear-gradient(180deg,#6a86ff,#4163ff);color:#fff;font-weight:900;padding:12px 15px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;min-height:44px;box-shadow:0 8px 22px rgba(35,80,255,.24);cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}button.gray,.btn.gray{background:linear-gradient(180deg,#4c5571,#363d55);box-shadow:none}button.danger,.danger{background:linear-gradient(180deg,#ff6666,#ce4040);box-shadow:none}button.ok{background:linear-gradient(180deg,#2bd176,#169851)}input,select,textarea{width:100%;background:#0d1325;color:#f4f6ff;border:1px solid rgba(170,185,230,.25);border-radius:15px;padding:13px;margin:6px 0 13px;font-size:16px;outline:none}label{font-size:13px;color:#bac4de;font-weight:900}.tabs{display:flex;gap:8px;overflow-x:auto;padding:4px 0}.tabs a{white-space:nowrap;color:#dce4ff;background:rgba(10,15,30,.55);border:1px solid rgba(255,255,255,.12);text-decoration:none;border-radius:999px;padding:9px 14px;font-weight:900;font-size:14px}.tabs a.on{background:linear-gradient(180deg,#6a86ff,#4163ff);border-color:#8ca0ff}.empty{border:1px dashed rgba(255,255,255,.25);border-radius:22px;padding:46px;text-align:center;color:#c2c9dd;background:rgba(20,27,48,.55)}.post-head{display:flex;justify-content:space-between;align-items:center}.pill{display:inline-flex;border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;margin-right:4px}.pill.open{background:#123f2a;color:#9dffc4}.pill.done{background:#4d2020;color:#ffd1d1}.pill.type{background:#242c48;color:#ccd6ff}.count{font-size:18px;background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:7px 12px}h2{font-size:24px;margin:12px 0 5px}.meta{color:#b5bfd9;font-size:14px;line-height:1.6}.memo{color:#ffd16a;font-size:14px;margin-top:5px}.left-time{color:#ffb3b3;font-size:13px;font-weight:900}.slot{display:flex;justify-content:space-between;align-items:center;background:rgba(8,12,24,.62);border:1px solid rgba(255,255,255,.12);border-radius:17px;padding:12px;margin:9px 0}.slot.filled{background:rgba(18,55,33,.58);border-color:rgba(73,190,112,.35)}.actions{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:12px}.farm-actions{grid-template-columns:1fr}.owner-only{display:none!important}.post[data-owner='1'] .owner-only{display:inline-flex!important}.hidden{display:none!important}.time-row{display:grid;grid-template-columns:90px 1fr;gap:8px}.quick{display:grid;grid-template-columns:1fr auto;gap:8px}.mini{font-size:13px;padding:8px 10px;min-height:34px}.notice,.alarm-guide{background:linear-gradient(180deg,rgba(255,211,106,.18),rgba(255,211,106,.08));border:1px solid rgba(255,211,106,.30);color:#ffe5a3;border-radius:18px;padding:12px;margin-top:12px;font-size:13px;line-height:1.45}.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#1e2845;border:1px solid #53648f;border-radius:999px;padding:10px 16px;opacity:0;transition:.2s;z-index:999;font-weight:900}.toast.show{opacity:1}.modal{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;z-index:100}.modal.show{display:flex}.chat-panel{width:100%;max-width:880px;margin:0 auto;border-radius:22px 22px 0 0}.chat-list{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;height:340px;overflow-y:auto;padding:10px}.msg{background:#202a47;border-radius:13px;padding:9px 11px;margin:7px 0}.msg.mine{background:#173d27;border:1px solid #2e7146}.msg-meta{font-size:12px;color:#a8b2cc;display:flex;justify-content:space-between;gap:8px;align-items:center}.chat-form{display:grid;grid-template-columns:1fr 74px;gap:7px;margin-top:9px}.chat-form input{margin:0}.member-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.member{background:rgba(8,12,24,.55);border:1px solid rgba(255,255,255,.10);border-radius:14px;padding:10px;margin:6px 0}.choice-list{display:grid;gap:8px}.choice-list button{width:100%;justify-content:flex-start;background:linear-gradient(180deg,#4c5571,#363d55)}.check-box{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:10px;margin-bottom:10px}.check-row{display:block;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}.check-row input{width:auto;margin-right:8px}.farm-manage{display:block!important;margin-top:12px}@media(max-width:680px){.wrap{padding:12px 10px 90px}h1{font-size:22px}.summary{grid-template-columns:repeat(3,1fr);gap:7px}.stat{padding:10px 4px}.stat b{font-size:21px}.actions{grid-template-columns:1fr 1fr}.top-actions>*{flex:1}.panel,.party-card{border-radius:20px;padding:13px}button,.btn{font-size:14px;padding:10px 11px}}
"""

GATE_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>문파 입장</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>🔐 문파 전용 파티모집</h1><div class='sub'>월하 · 연가 · 연희 파티모집</div></header>
<section class='panel'><h2>입장 비밀번호</h2><p class='meta'>문파원만 이용할 수 있습니다.</p>
<form method='post' action='/gate'><input name='password' type='password' placeholder='문파 비밀번호' autofocus><button style='width:100%'>입장</button></form>
{% if error %}<div class='notice'>비밀번호가 맞지 않습니다.</div>{% endif %}
</section></div></body></html>
"""

REGISTER_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>가입</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>👤 문파원 등록</h1><div class='sub'>처음 한 번만 등록하면 됩니다.</div></header>
<section class='panel'><form method='post' action='/register'>
<label>계정명</label><input name='account' required placeholder='예: 역인'>
<label>대표 캐릭터명</label><input name='char_name' required placeholder='예: 역인'>
<label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select>
<button style='width:100%'>승인 요청</button></form>
<p class='meta'>관리자 승인 후 사이트 이용이 가능합니다.</p>{% if error %}<div class='notice'>{{ error }}</div>{% endif %}
</section></div></body></html>
"""

WAIT_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>승인 대기</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>⏳ 승인 대기중</h1><div class='sub'>관리자가 승인하면 이용할 수 있습니다.</div></header>
<section class='panel'><p>{{ user.account if user else "승인 대기중" }} 계정이 승인 대기중입니다.</p><form method='post' action='/logout'><button class='gray'>로그아웃</button></form></section></div></body></html>
"""

MAIN_PAGE = """
<!doctype html>
<html lang='ko'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>월하 · 연가 · 연희 파티모집</title><style>{{ css }}</style></head>
<body>
<div class='wrap'>
<header class='header'><h1>⚔️ 월하 · 연가 · 연희 파티모집</h1><div class='sub'>Made by 역인(진선)</div></header>
{% if notice %}<div class='notice'>📢 {{ notice }}</div>{% endif %}

{% if page=='home' %}
<section class='panel'>
<div class='top-actions'>
<a class='btn' href='/new'>+ 모집글</a>
<a class='btn gray' href='/chars'>내 캐릭터</a>
<button type='button' class='gray' onclick='openGlobalChat()'>통합채팅</button>
<button type='button' class='gray' onclick='toggleAlarm()' id='alarmBtn'>🔔 알림 ON</button>
</div>
<div class='summary'><div class='stat'><b>{{ open_count }}</b><span>모집중</span></div><div class='stat'><b id='onlineCount'>1</b><span>접속중</span></div><div class='stat'><b id='myCount'>0</b><span>내 참여</span></div></div>
<div class='alarm-guide'>🔔 알림은 사이트가 열려있는 동안에만 동작합니다. 새 모집글, 참여, 채팅을 알려드립니다.</div>
<div class='tabs'>{% for f in filters %}<a class='{% if filter_value==f %}on{% endif %}' href='/?filter={{ f }}'>{{ f }}</a>{% endfor %}</div>
</section>
<section class='panel'><h2>문파원 접속 현황</h2><div class='member-grid'>{{ member_html|safe }}</div></section>
<div id='postList'>{{ post_list|safe }}</div>
{% endif %}

{% if page in ['new','edit'] %}
<section class='panel'><h2>{% if page=='edit' %}모집글 수정{% else %}모집글 올리기{% endif %}</h2>
<form method='post' action='{% if page=="edit" %}/edit/{{ post.id }}{% else %}/create{% endif %}' onsubmit='return prepareSubmit()'>
<label>작성 캐릭터</label><select name='owner_char_id'>{% for c in chars %}<option value='{{ c.id }}'>{{ c.name }}({{ c.job }})</option>{% endfor %}</select>
<label>종류</label><select name='category' id='typeSelect' onchange='updatePlaces();toggleSlotBox()'>{% for t in filters_no_all %}<option>{{ t }}</option>{% endfor %}</select>
<label>장소</label>{% for cat, vals in places.items() %}<select name='place_{{ cat }}' id='place_{{ cat }}' class='place-select {% if cat!="사냥" %}hidden{% endif %}'>{% for p in vals %}<option>{{ p }}</option>{% endfor %}</select>{% endfor %}
<label>채널 4자리</label><input name='channel' id='channelInput' maxlength='4' inputmode='numeric' placeholder='예: 3385' oninput='numbersOnly(this)'>
<label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' placeholder='예: 09:00'></div>
<label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option selected>오후</option></select><input name='end_time' placeholder='예: 11:00'></div>
<label>메모</label><textarea name='memo' rows='2'></textarea>
<div class='panel' id='slotPanel'><label>모집 자리 추가</label><div class='quick'><select id='slotJob'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slotsBox'></div></div>
<div class='notice hidden' id='farmNotice'>파밍방은 직업 자리 없이 생성됩니다. 참여자는 참여 버튼으로 들어옵니다.</div>
<button style='width:100%' type='submit'>저장</button><a class='btn gray' style='width:100%;margin-top:8px' href='/'>취소</a>
</form></section>
{% endif %}

{% if page=='chars' %}
<section class='panel'><a class='btn gray' href='/' style='margin-bottom:10px'>← 메인으로</a><h2>내 캐릭터</h2><p class='meta'>새 캐릭터는 관리자 승인 후 사용할 수 있습니다.</p>
<form method='post' action='/chars/add'><label>캐릭터명</label><input name='name' required><label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button style='width:100%'>캐릭터 추가 요청</button></form></section>
<section class='panel'><h2>등록 캐릭터</h2>{% for c in user.chars %}<div class='member'>{{ c.name }}({{ c.job }}) · {{ c.status }} {% if c.status=='approved' %}<form method='post' action='/chars/select/{{ c.id }}' style='display:inline'><button class='mini'>대표선택</button></form>{% endif %}</div>{% endfor %}<a class='btn gray' href='/' style='width:100%;margin-top:10px'>메인으로 돌아가기</a></section>
{% endif %}
</div>

<div id='globalModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>💬 통합채팅</b><button type='button' class='mini gray' onclick='closeGlobalChat()'>닫기</button></div><div class='alarm-guide'>최근 100개 메시지만 유지됩니다. 24시간이 지난 메시지는 자동 삭제됩니다. 본인이 작성한 메시지는 5분 이내 삭제 가능합니다.</div><div id='globalChatList' class='chat-list'></div><div class='chat-form'><input id='globalChatText' placeholder='메시지' maxlength='150'><button type='button' onclick='sendGlobalChat()'>전송</button></div></div></div>
<div id='partyModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>💬 채팅</b><button type='button' class='mini gray' onclick='closePartyChat()'>닫기</button></div><div id='partyChatList' class='chat-list'></div><div class='chat-form'><input id='partyChatText' placeholder='메시지' maxlength='150'><button type='button' onclick='sendPartyChat()'>전송</button></div></div></div>
<div id='charPickModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'><b>참여 캐릭터 선택</b><button type='button' class='mini gray' onclick='closeCharPick()'>닫기</button></div><div id='charPickList' class='choice-list'></div></div></div>
<div id='toast' class='toast'></div>

<script>
const CURRENT_USER_ID="{{ user.id if user else '' }}";let globalOpen=false;let partyId=null;let knownPosts=new Set();let firstLoad=true;
function qs(id){return document.getElementById(id)}function toast(m){const t=qs('toast');if(!t){alert(m);return}t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1600)}
function numbersOnly(el){el.value=(el.value||'').replace(/[^0-9]/g,'').slice(0,4)}function prepareSubmit(){const cat=qs('typeSelect')?.value;const ch=qs('channelInput');if(ch){numbersOnly(ch);if(ch.value.length!==4){alert('채널은 숫자 4자리로 입력해줘.');ch.focus();return false}}if(cat!=='파밍'&&document.querySelectorAll('#slotsBox input[name="slots"]').length===0){alert('모집 자리를 하나 이상 추가해줘.');return false}return true}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function updatePlaces(){const t=qs('typeSelect');if(!t)return;document.querySelectorAll('.place-select').forEach(x=>x.classList.add('hidden'));const target=qs('place_'+t.value);if(target)target.classList.remove('hidden')}
function toggleSlotBox(){const cat=qs('typeSelect')?.value;const panel=qs('slotPanel');const note=qs('farmNotice');if(!panel||!note)return;if(cat==='파밍'){panel.classList.add('hidden');note.classList.remove('hidden')}else{panel.classList.remove('hidden');note.classList.add('hidden')}}
function toggleFarmResultBox(selectId,boxId){const s=qs(selectId);const b=qs(boxId);if(!s||!b)return;b.style.display=(s.value==='득템')?'block':'none'}
function addSlot(){const job=qs('slotJob')?.value;const box=qs('slotsBox');if(!job||!box)return;const d=document.createElement('div');d.className='slot';d.innerHTML='<div><b>'+escapeHtml(job)+'</b><br><span>빈자리</span></div><button type="button" class="mini danger" onclick="this.parentElement.remove()">삭제</button><input type="hidden" name="slots" value="'+escapeHtml(job)+'">';box.appendChild(d)}
function copyPost(text){if(navigator.clipboard){navigator.clipboard.writeText(text).then(()=>toast('복사됨')).catch(()=>alert(text))}else alert(text)}
function shareKakao(text){const shareText='월하 · 연가 · 연희 파티모집\\n\\n'+text+'\\n\\n'+location.origin;if(navigator.share){navigator.share({title:'파티모집',text:shareText,url:location.origin}).catch(()=>copyPost(shareText))}else{copyPost(shareText);toast('공유문구가 복사됐습니다. 카톡에 붙여넣어 주세요.')}}
function refresh(){if(location.pathname!='/')return;fetch('/api/posts'+location.search,{cache:'no-store'}).then(r=>r.text()).then(h=>{const list=qs('postList');if(list)list.innerHTML=h;scanAlarms();countMine()}).catch(()=>{})}
function countMine(){let c=0;document.querySelectorAll('.post').forEach(p=>{if(p.dataset.owner==='1'||(CURRENT_USER_ID&&(p.dataset.participants||'').includes(CURRENT_USER_ID)))c++});const m=qs('myCount');if(m)m.textContent=c}
function doJoin(pid,sid,cid){fetch('/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid,char_id:cid})}).then(()=>{toast('참여됨');closeCharPick();refresh()})}
function closeCharPick(){const m=qs('charPickModal');if(m)m.classList.remove('show')}
function joinSlot(pid,sid,job){fetch('/api/mychars?job='+encodeURIComponent(job),{cache:'no-store'}).then(r=>r.json()).then(d=>{const chars=d.chars||[];if(!chars.length){toast('승인된 해당 직업 캐릭터가 없습니다.');return}if(chars.length===1){doJoin(pid,sid,chars[0].id);return}const box=qs('charPickList');box.innerHTML='';chars.forEach(c=>{const b=document.createElement('button');b.type='button';b.textContent=c.label+' 으로 참여';b.onclick=()=>doJoin(pid,sid,c.id);box.appendChild(b)});qs('charPickModal').classList.add('show')}).catch(()=>toast('참여 처리 중 오류'))}
function joinFarming(pid){fetch('/api/mychars',{cache:'no-store'}).then(r=>r.json()).then(d=>{const chars=d.chars||[];if(!chars.length){toast('승인된 캐릭터가 없습니다.');return}if(chars.length===1){doJoinFarming(pid,chars[0].id);return}const box=qs('charPickList');box.innerHTML='';chars.forEach(c=>{const b=document.createElement('button');b.type='button';b.textContent=c.label+' 으로 참여';b.onclick=()=>doJoinFarming(pid,c.id);box.appendChild(b)});qs('charPickModal').classList.add('show')})}
function doJoinFarming(pid,cid){fetch('/farming/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,char_id:cid})}).then(()=>{toast('참여됨');closeCharPick();refresh()})}
function leaveFarming(pid){if(!confirm('파밍 참여를 취소할까?'))return;fetch('/farming/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid})}).then(()=>refresh())}
function addExternal(pid,sid){const name=prompt('외부인 닉네임을 입력해줘');if(!name)return;fetch('/external',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid,name:name})}).then(()=>refresh())}
function leaveSlot(pid,sid){if(!confirm('비울까?'))return;fetch('/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid})}).then(()=>refresh())}
function deletePost(pid){if(!confirm('정말 삭제하시겠습니까?'))return;fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid})}).then(r=>r.json()).then(x=>{toast(x.ok?'삭제됨':(x.reason||'삭제 실패'));refresh()})}
function openGlobalChat(){globalOpen=true;qs('globalModal').classList.add('show');refreshGlobalChat()}function closeGlobalChat(){globalOpen=false;qs('globalModal').classList.remove('show')}
function refreshGlobalChat(){if(!globalOpen)return;fetch('/api/global_chat',{cache:'no-store'}).then(r=>r.text()).then(h=>{const b=qs('globalChatList');if(b){b.innerHTML=h;b.scrollTop=b.scrollHeight}}).catch(()=>{})}
function sendGlobalChat(){const i=qs('globalChatText');if(!i||!i.value.trim())return;fetch('/global_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:i.value.trim()})}).then(r=>r.json()).then(x=>{if(!x.ok){toast(x.reason||'전송 실패');return}i.value='';refreshGlobalChat()})}
function deleteGlobalChat(mid){if(!confirm('이 메시지를 삭제할까요?'))return;fetch('/global_chat/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:mid})}).then(r=>r.json()).then(x=>{toast(x.ok?'삭제됨':(x.reason||'삭제 실패'));refreshGlobalChat()})}
function openPartyChat(pid){partyId=pid;qs('partyModal').classList.add('show');refreshPartyChat()}function closePartyChat(){partyId=null;qs('partyModal').classList.remove('show')}
function refreshPartyChat(){if(!partyId)return;fetch('/api/party_chat/'+partyId,{cache:'no-store'}).then(r=>r.text()).then(h=>{const b=qs('partyChatList');if(b){b.innerHTML=h;b.scrollTop=b.scrollHeight}}).catch(()=>{})}
function sendPartyChat(){const i=qs('partyChatText');if(!partyId||!i||!i.value.trim())return;fetch('/party_chat/'+partyId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:i.value.trim()})}).then(r=>r.json()).then(x=>{if(!x.ok){toast(x.reason||'전송 실패');return}i.value='';refreshPartyChat();refresh()})}
function alarmOn(){return localStorage.getItem('baram_alarm_off')!=='1'}function updateAlarmBtn(){const b=qs('alarmBtn');if(b)b.textContent=alarmOn()?'🔔 알림 ON':'🔕 알림 OFF'}function toggleAlarm(){localStorage.setItem('baram_alarm_off',alarmOn()?'1':'0');updateAlarmBtn();toast(alarmOn()?'알림 켜짐':'알림 꺼짐')}
function scanAlarms(){document.querySelectorAll('.post').forEach(p=>{const id=p.dataset.postId;if(id&&!knownPosts.has(id)){if(!firstLoad&&alarmOn())toast('새 모집글이 올라왔습니다.');knownPosts.add(id)}});firstLoad=false}
function heartbeat(){fetch('/api/heartbeat',{method:'POST'}).then(r=>r.json()).then(x=>{const o=qs('onlineCount');if(o)o.textContent=x.online||1}).catch(()=>{})}
document.addEventListener('DOMContentLoaded',()=>{const g=qs('globalChatText');if(g)g.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();sendGlobalChat()}});const p=qs('partyChatText');if(p)p.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();sendPartyChat()}});updatePlaces();toggleSlotBox();updateAlarmBtn();heartbeat();scanAlarms();countMine()});
setInterval(refresh,2500);setInterval(refreshGlobalChat,1600);setInterval(refreshPartyChat,1600);setInterval(heartbeat,15000);
</script>
</body></html>
"""

ADMIN_PAGE = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>관리자</title><style>{{ css }}</style></head>
<body><div class='wrap'><header class='header'><h1>🔒 관리자</h1><div class='sub'>문파 관리 페이지</div></header><a class='btn gray' href='/'>메인</a>
{% if not admin_ok %}
<section class='panel'><form method='post' action='/admin/login'><label>관리자 비밀번호</label><input name='password' type='password' autofocus><button>로그인</button></form><p class='meta'>기본 비밀번호는 1234입니다. 로그인 후 변경하세요.</p></section>
{% else %}
<section class='panel'><div class='top-actions'><form method='post' action='/admin/logout'><button class='gray'>로그아웃</button></form><form method='post' action='/admin/clear_closed'><button>마감글 정리</button></form><form method='post' action='/admin/clear_global_chat'><button class='danger'>통합채팅 전체삭제</button></form></div></section>
<section class='panel'><h2>문파 설정</h2><form method='post' action='/admin/settings'><label>문파 입장 비밀번호 변경</label><input name='access_password' placeholder='새 입장 비밀번호'><label>관리자 비밀번호 변경</label><input name='admin_password' placeholder='새 관리자 비밀번호'><button>저장</button></form></section>
<section class='panel'><h2>공지</h2><form method='post' action='/admin/notice'><textarea name='notice' rows='3'>{{ notice }}</textarea><button>공지 저장</button></form></section>
<section class='panel'><h2>가입 승인</h2>{% for u in pending_users %}<div class='member'><b>{{ u.account }}</b> / {% for c in u.chars %}{{ c.name }}({{ c.job }}) {% endfor %}<form method='post' action='/admin/user/{{ u.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/user/{{ u.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p class='meta'>대기 없음</p>{% endfor %}</section>
<section class='panel'><h2>캐릭터 승인</h2>{% for item in pending_chars %}<div class='member'><b>{{ item.user.account }}</b> / {{ item.char.name }}({{ item.char.job }})<form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p class='meta'>대기 없음</p>{% endfor %}</section>
<section class='panel'><h2>파밍 아이템 설정</h2><form method='post' action='/admin/farming_items'><label>해골왕</label><input name='items_해골왕' value='{{ farming_items.get("해골왕", [])|join(", ") }}'><label>어금니</label><input name='items_어금니' value='{{ farming_items.get("어금니", [])|join(", ") }}'><button>저장</button></form></section>
<section class='panel'><h2>회원 관리</h2>{% for u in users %}<div class='member'><b>{{ u.account }}</b> · {{ u.status }}{% if u.blocked %} · 차단됨{% endif %}<br>{% for c in u.chars %}{{ c.name }}({{ c.job }}) - {{ c.status }}<br>{% endfor %}<form method='post' action='/admin/user/{{ u.id }}/toggle_block'><button class='mini danger'>차단/해제</button></form></div>{% else %}<p class='meta'>회원 없음</p>{% endfor %}</section>
<section class='panel'><h2>모집글 관리</h2>{% for p in posts %}<div class='member'><b>{{ p.place }}</b> / {{ p.category }} / {{ p.owner_label }} / {{ p.created }}<form method='post' action='/admin/delete_post/{{ p.id }}'><button class='mini danger'>삭제</button></form></div>{% else %}<p class='meta'>글 없음</p>{% endfor %}</section>
{% endif %}
</div></body></html>
"""

@app.before_request
def guard():
    if request.path in ["/gate", "/register", "/wait", "/logout", "/health", "/manifest.json", "/sw.js"] or request.path.startswith("/admin"):
        return
    data = load_data()
    if not can_enter_site(data):
        return redirect("/gate")
    user = current_user(data)
    if not user:
        return redirect("/register")
    if not approved_user(user):
        return redirect("/wait")
    touch_online()

@app.route("/health")
def health():
    return jsonify(ok=True, time=now_text(), online=online_count())

@app.route("/gate", methods=["GET", "POST"])
def gate():
    data0 = load_data()
    if request.method == "GET" and approved_user(current_user(data0)):
        return redirect("/")
    error = False
    if request.method == "POST":
        data = load_data()
        if request.form.get("password", "") == data["settings"].get("access_password"):
            session["access_ok"] = True
            return redirect("/")
        error = True
    return render_template_string(GATE_PAGE, css=CSS, error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    data = load_data()
    existing_user = current_user(data)
    if request.method == "GET" and approved_user(existing_user):
        return redirect("/")
    if request.method == "GET" and existing_user and existing_user.get("status") == "pending":
        return redirect("/wait")
    if request.method == "POST":
        account = request.form.get("account", "").strip()
        char_name = request.form.get("char_name", "").strip()
        job = request.form.get("job", "").strip()
        if not account or not char_name:
            return render_template_string(REGISTER_PAGE, css=CSS, jobs=JOBS, error="입력값을 확인해주세요.")
        if char_name.lower() in all_char_names(data):
            return render_template_string(REGISTER_PAGE, css=CSS, jobs=JOBS, error="이미 등록된 캐릭터명입니다.")
        uid = str(uuid.uuid4())
        cid = str(uuid.uuid4())
        user = {
            "id": uid,
            "account": account,
            "status": "pending",
            "blocked": False,
            "selected_char_id": cid,
            "created": now_text(),
            "chars": [{"id": cid, "name": char_name, "job": job, "status": "pending"}]
        }
        mutate(lambda d: d["users"].append(user))
        session["uid"] = uid
        session["access_ok"] = True
        return redirect("/wait")
    return render_template_string(REGISTER_PAGE, css=CSS, jobs=JOBS, error="")

@app.route("/wait")
def wait():
    data = load_data()
    user = current_user(data)
    if approved_user(user):
        return redirect("/")
    return render_template_string(WAIT_PAGE, css=CSS, user=user)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/gate")

@app.route("/")
def home():
    data = load_data()
    user = current_user(data)
    touch_online()
    filt = request.args.get("filter", "전체")
    posts = list(reversed(data.get("posts", [])))
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    open_count = sum(1 for p in posts if post_status(p) in ["모집중", "진행중"])
    return render_template_string(
        MAIN_PAGE, css=CSS, page="home", user=user, filters=FILTERS, filters_no_all=["사냥","파밍","600퀘"], filter_value=filt,
        post_list=render_posts(posts, user, farming_items=data["settings"].get("farming_items", DEFAULT_FARMING_ITEMS)), open_count=open_count, member_html=member_html(data),
        notice=data["settings"].get("notice", ""), jobs=JOBS, places=PLACES
    )

@app.route("/api/posts")
def api_posts():
    data = load_data()
    user = current_user(data)
    filt = request.args.get("filter", "전체")
    posts = list(reversed(data.get("posts", [])))
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    return render_posts(posts, user, farming_items=data["settings"].get("farming_items", DEFAULT_FARMING_ITEMS))

@app.route("/new")
def new_post_page():
    data = load_data()
    user = current_user(data)
    chars = approved_chars(user)
    if not chars:
        return redirect("/chars")
    return render_template_string(MAIN_PAGE, css=CSS, page="new", post=None, chars=chars, user=user, jobs=JOBS, places=PLACES, notice="", filters_no_all=["사냥","파밍","600퀘"])

@app.route("/create", methods=["POST"])
def create_post():
    data = load_data()
    user = current_user(data)
    owner_char = user_has_char(user, request.form.get("owner_char_id"))
    if not owner_char:
        return redirect("/chars")
    category = request.form.get("category", "사냥")
    place = request.form.get(f"place_{category}", "")
    slots = []
    if category != "파밍":
        slots = [{"id": str(uuid.uuid4()), "job": job, "char_id": "", "uid": "", "char_label": "", "external_label": ""} for job in request.form.getlist("slots")]
    post = {
        "id": str(uuid.uuid4()),
        "owner_uid": user["id"],
        "owner_char_id": owner_char["id"],
        "owner_label": char_label(owner_char),
        "category": category,
        "place": place,
        "channel": only_digits(request.form.get("channel", ""), 4),
        "start_period": request.form.get("start_period", ""),
        "start_time": request.form.get("start_time", "").strip(),
        "end_period": request.form.get("end_period", ""),
        "end_time": request.form.get("end_time", "").strip(),
        "memo": request.form.get("memo", "").strip(),
        "slots": slots,
        "closed": False,
        "closed_at": "",
        "party_chat": [],
        "created": now_text(),
        "farming_status": "진행중",
        "farming_result": "",
        "farming_item": "",
        "sale_amount": "",
        "farming_participants": [],
        "farming_share_ids": []
    }
    ensure_closed_if_full(post)
    mutate(lambda d: d["posts"].append(post))
    return redirect("/")

@app.route("/edit/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    data = load_data()
    user = current_user(data)
    post = find_post(data, post_id)
    if not post or post.get("owner_uid") != user.get("id"):
        return redirect("/")
    if request.method == "GET":
        return render_template_string(MAIN_PAGE, css=CSS, page="edit", post=post, chars=approved_chars(user), user=user, jobs=JOBS, places=PLACES, notice="", filters_no_all=["사냥","파밍","600퀘"])
    def fn(d):
        p = find_post(d, post_id)
        if p:
            p["channel"] = only_digits(request.form.get("channel", ""), 4)
            p["memo"] = request.form.get("memo", "").strip()
    mutate(fn)
    return redirect("/")

@app.route("/chars")
def chars_page():
    data = load_data()
    user = current_user(data)
    return render_template_string(MAIN_PAGE, css=CSS, page="chars", user=user, jobs=JOBS, notice="", places=PLACES, filters_no_all=["사냥","파밍","600퀘"])

@app.route("/chars/add", methods=["POST"])
def add_char():
    data = load_data()
    user = current_user(data)
    name = request.form.get("name", "").strip()
    job = request.form.get("job", "").strip()
    if name and name.lower() not in all_char_names(data):
        def fn(d):
            u = find_user(d, user["id"])
            if u:
                u["chars"].append({"id": str(uuid.uuid4()), "name": name, "job": job, "status": "pending"})
        mutate(fn)
    return redirect("/chars")

@app.route("/chars/select/<char_id>", methods=["POST"])
def select_char(char_id):
    data = load_data()
    user = current_user(data)
    if user_has_char(user, char_id):
        mutate(lambda d: find_user(d, user["id"]).update({"selected_char_id": char_id}))
    return redirect("/chars")

@app.route("/api/mychars")
def api_mychars():
    data = load_data()
    user = current_user(data)
    job = request.args.get("job", "")
    chars = approved_chars(user)
    if job:
        chars = [c for c in chars if c.get("job") == job]
    return jsonify(chars=[{"id": c["id"], "label": char_label(c)} for c in chars])

@app.route("/join", methods=["POST"])
def join_slot():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    ch = user_has_char(user, req.get("char_id"))
    if not ch:
        return jsonify(ok=False, reason="캐릭터 없음")
    def fn(d):
        post = find_post(d, req.get("post_id"))
        if not post or post.get("closed") or post.get("category") == "파밍":
            return
        if any(slot.get("char_id") == ch["id"] for slot in post.get("slots", [])):
            return
        for slot in post.get("slots", []):
            if slot.get("id") == req.get("slot_id") and not slot.get("char_id") and not slot.get("external_label"):
                slot["char_id"] = ch["id"]
                slot["uid"] = user["id"]
                slot["char_label"] = char_label(ch)
                ensure_closed_if_full(post)
                return
    mutate(fn)
    return jsonify(ok=True)

@app.route("/leave", methods=["POST"])
def leave_slot():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    def fn(d):
        post = find_post(d, req.get("post_id"))
        if not post:
            return
        owner = post.get("owner_uid") == user.get("id")
        for slot in post.get("slots", []):
            if slot.get("id") == req.get("slot_id") and (owner or slot.get("uid") == user.get("id")):
                slot["char_id"] = ""
                slot["uid"] = ""
                slot["char_label"] = ""
                slot["external_label"] = ""
                post["closed"] = False
                post["closed_at"] = ""
                return
    mutate(fn)
    return jsonify(ok=True)

@app.route("/external", methods=["POST"])
def external_slot():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    name = (req.get("name") or "").strip()[:20]
    if not name:
        return jsonify(ok=False)
    def fn(d):
        post = find_post(d, req.get("post_id"))
        if not post or post.get("owner_uid") != user.get("id") or post.get("category") == "파밍":
            return
        for slot in post.get("slots", []):
            if slot.get("id") == req.get("slot_id") and not slot.get("char_id") and not slot.get("external_label"):
                slot["external_label"] = name + "(외부)"
                ensure_closed_if_full(post)
                return
    mutate(fn)
    return jsonify(ok=True)

@app.route("/farming/join", methods=["POST"])
def farming_join():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    ch = user_has_char(user, req.get("char_id"))
    if not ch:
        return jsonify(ok=False, reason="캐릭터 없음")
    def fn(d):
        post = find_post(d, req.get("post_id"))
        if not post or post.get("category") != "파밍" or post.get("farming_status") == "정산완료":
            return
        if any(p.get("uid") == user["id"] for p in post.get("farming_participants", [])):
            return
        pid = str(uuid.uuid4())
        post.setdefault("farming_participants", []).append({"id": pid, "uid": user["id"], "char_id": ch["id"], "label": char_label(ch)})
        post.setdefault("farming_share_ids", []).append(pid)
    mutate(fn)
    return jsonify(ok=True)

@app.route("/farming/leave", methods=["POST"])
def farming_leave():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    def fn(d):
        post = find_post(d, req.get("post_id"))
        if not post or post.get("category") != "파밍" or post.get("farming_status") == "정산완료":
            return
        remove_ids = [p.get("id") for p in post.get("farming_participants", []) if p.get("uid") == user["id"]]
        post["farming_participants"] = [p for p in post.get("farming_participants", []) if p.get("uid") != user["id"]]
        post["farming_share_ids"] = [x for x in post.get("farming_share_ids", []) if x not in remove_ids]
    mutate(fn)
    return jsonify(ok=True)

@app.route("/farming/result/<post_id>", methods=["POST"])
def farming_result(post_id):
    data = load_data()
    user = current_user(data)
    def fn(d):
        post = find_post(d, post_id)
        if not post or post.get("category") != "파밍" or post.get("owner_uid") != user.get("id"):
            return
        result = request.form.get("farming_result", "노득")
        post["farming_result"] = result
        if result == "득템":
            post["farming_item"] = request.form.get("farming_item", "")
            post["sale_amount"] = only_digits(request.form.get("sale_amount", ""))
            post["farming_share_ids"] = request.form.getlist("share_ids")
        else:
            post["farming_item"] = ""
            post["sale_amount"] = ""
            post["farming_share_ids"] = []
        post["farming_status"] = "결과입력완료"
    mutate(fn)
    return redirect("/")

@app.route("/farming/settle/<post_id>", methods=["POST"])
def farming_settle(post_id):
    data = load_data()
    user = current_user(data)
    def fn(d):
        post = find_post(d, post_id)
        if post and post.get("category") == "파밍" and post.get("owner_uid") == user.get("id"):
            post["farming_status"] = "정산완료"
    mutate(fn)
    return redirect("/")

@app.route("/delete", methods=["POST"])
def delete_post():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    result = {"ok": False, "reason": "작성자만 삭제 가능"}
    def fn(d):
        keep = []
        for post in d.get("posts", []):
            if post.get("id") == req.get("post_id") and post.get("owner_uid") == user.get("id"):
                result["ok"] = True
                continue
            keep.append(post)
        d["posts"] = keep
    mutate(fn)
    return jsonify(result)

@app.route("/api/global_chat")
def api_global_chat():
    data = load_data()
    user = current_user(data)
    return render_chat_rows(data.get("global_chat", []), user.get("id"))

@app.route("/global_chat", methods=["POST"])
def global_chat_send():
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    ch = selected_char(user)
    text = (req.get("text") or "").strip()[:150]
    if not approved_user(user) or not ch or not text:
        return jsonify(ok=False, reason="채팅 불가")
    msg = {"id": str(uuid.uuid4()), "uid": user["id"], "label": char_label(ch), "text": text, "time": chat_time(), "created_at": now_iso()}
    mutate(lambda d: d["global_chat"].append(msg))
    return jsonify(ok=True)

@app.route("/global_chat/delete", methods=["POST"])
def global_chat_delete():
    req = request.get_json(force=True)
    msg_id = req.get("id", "")
    data = load_data()
    user = current_user(data)
    if not approved_user(user) or not msg_id:
        return jsonify(ok=False, reason="권한 없음")
    deadline = now() - timedelta(minutes=GLOBAL_CHAT_DELETE_MINUTES)
    result = {"ok": False, "reason": "삭제 가능 시간이 지났습니다."}
    def fn(d):
        keep = []
        for msg in d.get("global_chat", []):
            if msg.get("id") == msg_id and msg.get("uid") == user.get("id"):
                created_at = parse_dt(msg.get("created_at"))
                if created_at and created_at >= deadline:
                    result["ok"] = True
                    result["reason"] = "삭제됨"
                    continue
            keep.append(msg)
        d["global_chat"] = keep
    mutate(fn)
    return jsonify(result)

@app.route("/api/party_chat/<post_id>")
def api_party_chat(post_id):
    data = load_data()
    user = current_user(data)
    post = find_post(data, post_id)
    if not post or not can_party_chat(post, user):
        return "<div class='msg'>참여자만 이용 가능합니다.</div>"
    return render_chat_rows(post.get("party_chat", []), user.get("id"), allow_delete=False)

@app.route("/party_chat/<post_id>", methods=["POST"])
def party_chat_send(post_id):
    req = request.get_json(force=True)
    data = load_data()
    user = current_user(data)
    post = find_post(data, post_id)
    ch = selected_char(user)
    text = (req.get("text") or "").strip()[:150]
    if not post or not can_party_chat(post, user) or not ch or not text:
        return jsonify(ok=False, reason="참여자만 이용 가능")
    msg = {"id": str(uuid.uuid4()), "uid": user["id"], "label": char_label(ch), "text": text, "time": chat_time(), "created_at": now_iso()}
    mutate(lambda d: find_post(d, post_id).setdefault("party_chat", []).append(msg))
    return jsonify(ok=True)

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    touch_online()
    return jsonify(ok=True, online=online_count())

@app.route("/admin")
def admin():
    data = load_data()
    pending_users = [u for u in data["users"] if u.get("status") == "pending"]
    pending_chars = []
    for user in data["users"]:
        if user.get("status") == "approved":
            for ch in user.get("chars", []):
                if ch.get("status") == "pending":
                    pending_chars.append({"user": user, "char": ch})
    return render_template_string(
        ADMIN_PAGE, css=CSS, admin_ok=bool(session.get("admin_ok")),
        posts=list(reversed(data["posts"])), notice=data["settings"].get("notice", ""),
        pending_users=pending_users, pending_chars=pending_chars, users=data["users"],
        farming_items=data["settings"].get("farming_items", DEFAULT_FARMING_ITEMS)
    )

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = load_data()
    if request.form.get("password") == data["settings"].get("admin_password"):
        session["admin_ok"] = True
    return redirect("/admin")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_ok", None)
    return redirect("/admin")

@app.route("/admin/settings", methods=["POST"])
def admin_settings():
    if not session.get("admin_ok"):
        return redirect("/admin")
    access_pw = request.form.get("access_password", "").strip()
    admin_pw = request.form.get("admin_password", "").strip()
    def fn(d):
        if access_pw:
            d["settings"]["access_password"] = access_pw
        if admin_pw:
            d["settings"]["admin_password"] = admin_pw
    mutate(fn)
    return redirect("/admin")

@app.route("/admin/notice", methods=["POST"])
def admin_notice():
    if not session.get("admin_ok"):
        return redirect("/admin")
    mutate(lambda d: d["settings"].update({"notice": request.form.get("notice", "").strip()[:300]}))
    return redirect("/admin")

@app.route("/admin/farming_items", methods=["POST"])
def admin_farming_items():
    if not session.get("admin_ok"):
        return redirect("/admin")
    def parse_items(name):
        return [x.strip() for x in request.form.get(name, "").split(",") if x.strip()]
    items = {
        "해골왕": parse_items("items_해골왕") or ["해뼈"],
        "어금니": parse_items("items_어금니") or ["흑룡 어금니", "묵룡 어금니", "진룡 어금니", "감룡 어금니"]
    }
    mutate(lambda d: d["settings"].update({"farming_items": items}))
    return redirect("/admin")

@app.route("/admin/user/<uid>/<action>", methods=["POST"])
def admin_user_action(uid, action):
    if not session.get("admin_ok"):
        return redirect("/admin")
    def fn(d):
        user = find_user(d, uid)
        if not user:
            return
        if action == "approve":
            user["status"] = "approved"
            for ch in user.get("chars", []):
                if ch.get("status") == "pending":
                    ch["status"] = "approved"
        elif action == "reject":
            user["status"] = "rejected"
        elif action == "toggle_block":
            user["blocked"] = not user.get("blocked", False)
    mutate(fn)
    return redirect("/admin")

@app.route("/admin/char/<uid>/<char_id>/<action>", methods=["POST"])
def admin_char_action(uid, char_id, action):
    if not session.get("admin_ok"):
        return redirect("/admin")
    def fn(d):
        user = find_user(d, uid)
        if not user:
            return
        for ch in user.get("chars", []):
            if ch.get("id") == char_id:
                ch["status"] = "approved" if action == "approve" else "rejected"
    mutate(fn)
    return redirect("/admin")

@app.route("/admin/delete_post/<post_id>", methods=["POST"])
def admin_delete_post(post_id):
    if not session.get("admin_ok"):
        return redirect("/admin")
    mutate(lambda d: d.update({"posts": [p for p in d.get("posts", []) if p.get("id") != post_id]}))
    return redirect("/admin")

@app.route("/admin/clear_closed", methods=["POST"])
def admin_clear_closed():
    if not session.get("admin_ok"):
        return redirect("/admin")
    mutate(lambda d: d.update({"posts": [p for p in d.get("posts", []) if not p.get("closed")]}))
    return redirect("/admin")

@app.route("/admin/clear_global_chat", methods=["POST"])
def admin_clear_global_chat():
    if not session.get("admin_ok"):
        return redirect("/admin")
    mutate(lambda d: d.update({"global_chat": []}))
    return redirect("/admin")

@app.route("/manifest.json")
def manifest():
    return jsonify({"name": "월하 연가 연희 파티모집", "short_name": "파티모집", "start_url": "/", "display": "standalone", "background_color": "#0b1020", "theme_color": "#0b1020", "icons": []})

@app.route("/sw.js")
def sw():
    return app.response_class("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());", mimetype="application/javascript")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7777")), debug=False, threaded=True)
