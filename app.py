
from flask import Flask, request, jsonify, render_template_string, redirect, session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, uuid, tempfile, html, threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v13-final-secret")

KST = ZoneInfo("Asia/Seoul")
DATA_FILE = "data.json"
LOCK = threading.Lock()

DEFAULT_ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "moon")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")

ONLINE_SECONDS = 90
CHAT_LIMIT = 100
CHAT_RETENTION_HOURS = 24
CHAT_DELETE_MINUTES = 5
AUTO_DELETE_HOURS = 1
QUEST_MAX_PARTICIPANTS = 10
ONLINE = {}

JOBS = ["검성","검황","검제","전사","검객","태성","귀검","진검","도적","자객","현자","현인","현사","주술사","술사","진선","진인","명인","도사","도인"]
CATEGORIES = ["전체", "사냥", "600퀘", "파밍"]
PLACES = {
    "사냥": ["도삭산 900층", "흉노족", "선비족"],
    "600퀘": ["800층 600퀘", "900층 600퀘", "선비족 600퀘"],
    "파밍": ["해골왕", "어금니"]
}
FARM_ITEMS = {
    "해골왕": ["해뼈"],
    "어금니": ["흑룡 어금니", "묵룡 어금니", "진룡 어금니", "감룡 어금니"]
}

def kst_now():
    return datetime.now(KST)

def iso_now():
    return kst_now().isoformat(timespec="seconds")

def text_now():
    return kst_now().strftime("%m/%d %H:%M")

def time_now():
    return kst_now().strftime("%H:%M")

def parse_dt(s):
    try:
        if not s:
            return None
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=KST)
    except Exception:
        return None

def e(x):
    return html.escape(str(x or ""), quote=True)

def digits(x, limit=None):
    v = "".join(c for c in str(x or "") if c.isdigit())
    return v[:limit] if limit else v

def new_id():
    return str(uuid.uuid4())

def default_data():
    return {
        "settings": {
            "access_password": DEFAULT_ACCESS_PASSWORD,
            "admin_password": DEFAULT_ADMIN_PASSWORD,
            "notice": "",
            "farm_items": FARM_ITEMS
        },
        "users": [],
        "posts": [],
        "chat": []
    }

def read_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return default_data()
    d.setdefault("settings", {})
    d["settings"].setdefault("access_password", DEFAULT_ACCESS_PASSWORD)
    d["settings"].setdefault("admin_password", DEFAULT_ADMIN_PASSWORD)
    d["settings"].setdefault("notice", "")
    d["settings"].setdefault("farm_items", FARM_ITEMS)
    d.setdefault("users", [])
    for u in d.get("users", []):
        u.setdefault("role", "member")
    d.setdefault("posts", [])
    d.setdefault("chat", [])
    return d

def write_data(d):
    fd, tmp = tempfile.mkstemp(prefix="baram_", suffix=".json", dir=".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def clean_data(d):
    cutoff = kst_now() - timedelta(hours=AUTO_DELETE_HOURS)
    posts = []
    for p in d.get("posts", []):
        p.setdefault("category", "사냥")
        p.setdefault("slots", [])
        p.setdefault("participants", [])
        p.setdefault("party_chat", [])
        p.setdefault("farm_status", "진행중")
        p.setdefault("farm_result", "")
        p.setdefault("farm_item", "")
        p.setdefault("sale_amount", "")
        p.setdefault("share_ids", [])
        p.setdefault("early_ids", [])
        p.setdefault("late_ids", [])
        p.setdefault("early_weight", p.get("early_weight", "1.0"))
        p.setdefault("late_weight", p.get("late_weight", "0.88"))
        p.setdefault("late_percent", p.get("late_percent", "15"))
        p.setdefault("late_share", "")
        closed_at = parse_dt(p.get("closed_at"))
        if p.get("category") in ["사냥","600퀘"] and p.get("closed") and closed_at and closed_at <= cutoff:
            continue
        p["party_chat"] = p.get("party_chat", [])[-CHAT_LIMIT:]
        posts.append(p)
    d["posts"] = posts

    chat_cut = kst_now() - timedelta(hours=CHAT_RETENTION_HOURS)
    chat = []
    for m in d.get("chat", []):
        m.setdefault("id", new_id())
        dt = parse_dt(m.get("created_at"))
        if dt is None:
            m["created_at"] = iso_now()
            chat.append(m)
        elif dt >= chat_cut:
            chat.append(m)
    d["chat"] = chat[-CHAT_LIMIT:]
    return d

def load():
    with LOCK:
        d = clean_data(read_data())
        write_data(d)
        return d

def save(fn):
    with LOCK:
        d = clean_data(read_data())
        r = fn(d)
        write_data(d)
        return r

def current_uid():
    return session.get("uid")

def find_user(d, uid):
    for u in d["users"]:
        if u.get("id") == uid:
            return u
    return None

def current_user(d):
    uid = current_uid()
    return find_user(d, uid) if uid else None

def approved(u):
    return bool(u and u.get("status") == "approved" and not u.get("blocked"))

def role_of(u):
    return (u or {}).get("role", "member")

def is_admin_user(u):
    return approved(u) and role_of(u) in ["admin", "super"]

def is_super_user(u):
    return approved(u) and role_of(u) == "super"

def super_count(d):
    return sum(1 for u in d.get("users", []) if approved(u) and role_of(u) == "super")

def bootstrap_admin_ok(d):
    # 최고관리자가 아직 0명일 때만 기존 관리자 비밀번호 세션을 임시 허용
    return super_count(d) == 0 and session.get("legacy_admin_ok")

def chars(u):
    return [c for c in (u or {}).get("chars", []) if c.get("status") == "approved"]

def selected_char(u):
    cs = chars(u)
    if not cs:
        return None
    sid = u.get("selected_char_id")
    for c in cs:
        if c.get("id") == sid:
            return c
    return cs[0]

def label(c):
    return f"{c.get('name','')}({c.get('job','')})" if c else ""

def all_char_names(d):
    out = set()
    for u in d["users"]:
        for c in u.get("chars", []):
            out.add(str(c.get("name","")).strip().lower())
    return out

def has_char(u, cid):
    for c in chars(u):
        if c.get("id") == cid:
            return c
    return None

def find_post(d, pid):
    for p in d["posts"]:
        if p.get("id") == pid:
            return p
    return None

def touch():
    key = current_uid() or session.get("guest_id")
    if not key:
        key = new_id()
        session["guest_id"] = key
    ONLINE[key] = kst_now()

def online_count():
    cut = kst_now() - timedelta(seconds=ONLINE_SECONDS)
    for k, v in list(ONLINE.items()):
        try:
            if v.tzinfo is None:
                v = v.replace(tzinfo=KST)
            if v < cut:
                ONLINE.pop(k, None)
        except Exception:
            ONLINE.pop(k, None)
    return max(1, len(ONLINE))

def can_enter(d):
    return bool(session.get("access_ok")) or approved(current_user(d))

def normal_filled(p):
    filled = sum(1 for s in p.get("slots", []) if s.get("uid") or s.get("external"))
    total = len(p.get("slots", []))
    return filled, total

def participant_count(p):
    return len(p.get("participants", []))

def status_text(p):
    if p.get("category") == "사냥":
        f, t = normal_filled(p)
        if p.get("closed") or (t and f >= t):
            return "마감"
        return "모집중"
    if p.get("category") == "600퀘":
        if p.get("closed") or len(p.get("participants", [])) >= QUEST_MAX_PARTICIPANTS:
            return "마감"
        return "모집중"
    if p.get("category") == "파밍":
        return p.get("farm_status", "진행중")
    return "모집중"

def amount_text(v):
    try:
        return f"{int(v):,}전"
    except Exception:
        return "0전"

def farm_calc(p):
    amt = int(p.get("sale_amount") or 0)
    late_ids = set(p.get("late_ids", []))
    early_ids = set(p.get("early_ids", [])) - late_ids
    # 이전 데이터 호환: share_ids만 있으면 전부 선집합으로 처리
    if not early_ids and not late_ids and p.get("share_ids"):
        early_ids = set(p.get("share_ids", []))

    early = [x for x in p.get("participants", []) if x.get("id") in early_ids]
    late = [x for x in p.get("participants", []) if x.get("id") in late_ids]
    early_count = len(early)
    late_count = len(late)

    def to_float(value, default):
        try:
            return float(str(value).strip())
        except Exception:
            return default

    early_weight_raw = str(p.get("early_weight") or "1.0").strip()
    late_weight_raw = str(p.get("late_weight") or "0.88").strip()
    early_weight = max(0.0, to_float(early_weight_raw, 1.0))
    late_weight = max(0.0, to_float(late_weight_raw, 0.88))

    total_weight = early_count * early_weight + late_count * late_weight
    if amt <= 0 or total_weight <= 0:
        return {
            "amount": amt,
            "early_count": early_count,
            "late_count": late_count,
            "early_share": 0,
            "late_share": 0,
            "early_total": 0,
            "late_total": 0,
            "early_weight": early_weight_raw,
            "late_weight": late_weight_raw,
            "unit_share": 0,
            "total_weight": total_weight
        }

    unit_share = amt / total_weight
    early_share = int(unit_share * early_weight)
    late_share = int(unit_share * late_weight)
    early_total = early_share * early_count
    late_total = late_share * late_count

    return {
        "amount": amt,
        "early_count": early_count,
        "late_count": late_count,
        "early_share": early_share,
        "late_share": late_share,
        "early_total": early_total,
        "late_total": late_total,
        "early_weight": early_weight_raw,
        "late_weight": late_weight_raw,
        "unit_share": int(unit_share),
        "total_weight": total_weight
    }

def can_chat(p, u):
    if not approved(u):
        return False
    if p.get("owner_uid") == u.get("id"):
        return True
    if p.get("category") == "사냥":
        return any(s.get("uid") == u.get("id") for s in p.get("slots", []))
    return any(x.get("uid") == u.get("id") for x in p.get("participants", []))

def member_html(d):
    ids = set(ONLINE.keys())
    rows = []
    for u in d["users"]:
        if approved(u):
            c = selected_char(u)
            rows.append(f"<div class='member'>{'🟢' if u.get('id') in ids else '⚫'} {e(label(c) or u.get('account'))}</div>")
    return "".join(rows) or "<div class='member'>승인된 문파원이 없습니다.</div>"

def chat_rows(rows, uid, allow_delete=True):
    if not rows:
        return "<div class='msg'>아직 메시지가 없습니다.</div>"
    cut = kst_now() - timedelta(minutes=CHAT_DELETE_MINUTES)
    out = []
    for m in rows[-CHAT_LIMIT:]:
        mine = " mine" if m.get("uid") == uid else ""
        btn = ""
        dt = parse_dt(m.get("created_at"))
        if allow_delete and mine and dt and dt >= cut:
            btn = f"<button class='mini danger' onclick=\"deleteGlobalChat('{e(m.get('id'))}')\">삭제</button>"
        out.append(f"<div class='msg{mine}'><div class='msg-meta'>{e(m.get('label'))} · {e(m.get('time'))} {btn}</div><div>{e(m.get('text'))}</div></div>")
    return "".join(out)

def post_time(p):
    s = (p.get("start_period","") + " " + p.get("start_time","")).strip()
    t = (p.get("end_period","") + " " + p.get("end_time","")).strip()
    if s and t:
        return f"{s} ~ {t}"
    return s or t or "시간 미정"

def render_posts(posts, u, farm_items=None, admin=False):
    farm_items = farm_items or FARM_ITEMS
    if not posts:
        return "<div class='empty'>현재 모집글이 없습니다.</div>"
    uid = u.get("id") if u else ""
    out = []
    for p in posts:
        pid = e(p.get("id"))
        cat = p.get("category")
        owner = p.get("owner_uid") == uid
        owner_admin = owner or admin
        st = status_text(p)
        data_part = ""
        if cat == "사냥":
            data_part = "|".join(s.get("uid","") for s in p.get("slots", []) if s.get("uid"))
            f, total = normal_filled(p)
            cnt_text = f"{f}/{total}"
        else:
            data_part = "|".join(x.get("uid","") for x in p.get("participants", []) if x.get("uid"))
            cnt_text = f"{participant_count(p)}/{QUEST_MAX_PARTICIPANTS}" if cat == "600퀘" else str(participant_count(p))

        copy_lines = [f"[{cat}] {p.get('place')}", f"채널 {p.get('channel') or '미정'}", post_time(p), f"작성자 {p.get('owner_label')}"]

        if cat == "사냥":
            rows = []
            for s in p.get("slots", []):
                sid = e(s.get("id"))
                job = e(s.get("job"))
                who = e(s.get("label") or s.get("external"))
                if who:
                    mark = "🟡" if s.get("external") else "✅"
                    clear_btn = f"<button class='mini danger' onclick=\"leaveSlot('{pid}','{sid}')\">비우기</button>" if owner_admin or s.get("uid") == uid else ""
                    rows.append(f"<div class='slot filled'><div><b>{job}</b><br>{mark} {who}</div>{clear_btn}</div>")
                    copy_lines.append(f"{s.get('job')} - {who}")
                else:
                    ext = f"<button class='mini gray' onclick=\"addExternal('{pid}','{sid}')\">외부인</button>" if owner_admin else ""
                    rows.append(f"<div class='slot'><div><b>{job}</b><br>⭕ 모집중</div><div>{ext}<button class='mini ok' onclick=\"joinSlot('{pid}','{sid}','{job}')\">참여</button></div></div>")
                    copy_lines.append(f"{s.get('job')} - 모집중")
            body = "<div class='slots'>" + "".join(rows) + "</div>"
        else:
            ps = p.get("participants", [])
            joined = any(x.get("uid") == uid for x in ps)
            part_items = []
            for x in ps:
                remove_btn = f"<button class='mini danger' onclick=\"removeSimple('{pid}','{e(x.get('id'))}')\">삭제</button>" if owner_admin else ""
                part_items.append(f"<div class='member'>🟢 {e(x.get('label'))} {remove_btn}</div>")
            part_html = "".join(part_items) or "<p class='meta'>아직 참여자가 없습니다.</p>"
            for x in ps:
                copy_lines.append(f"참여 - {x.get('label')}")
            if cat == "파밍" and p.get("farm_result") == "득템":
                ctmp = farm_calc(p)
                copy_lines.append(f"득템 : {p.get('farm_item')} ({amount_text(p.get('sale_amount'))})")
                copy_lines.append(f"지분 : 선집합 {ctmp['early_weight']} / 후집합 {ctmp['late_weight']}")
                copy_lines.append(f"선집합인원 : {ctmp['early_count']}명 / 인당 {amount_text(ctmp['early_share'])}")
                copy_lines.append(f"후집합인원 : {ctmp['late_count']}명 / 인당 {amount_text(ctmp['late_share'])}")
            join_btn = ""
            simple_closed = (cat == "600퀘" and (p.get("closed") or participant_count(p) >= QUEST_MAX_PARTICIPANTS))
            if cat == "파밍" and p.get("farm_status") == "정산완료":
                join_btn = ""
            elif simple_closed and not joined:
                join_btn = "<button class='gray' disabled>모집완료</button>"
            else:
                join_btn = f"<button class='gray' onclick=\"leaveSimple('{pid}')\">참여취소</button>" if joined else f"<button class='ok' onclick=\"joinSimple('{pid}')\">참여하기</button>"

            result = ""
            manage = ""
            if cat == "파밍":
                badge = {"진행중":"🟡 진행중", "결과입력완료":"🔵 결과입력완료", "정산완료":"✅ 정산완료"}.get(p.get("farm_status"), "🟡 진행중")
                result += f"<div class='notice'>{badge}</div>"
                if p.get("farm_result") == "득템":
                    c = farm_calc(p)
                    result += f"<div class='notice'>결과: <b>득템</b><br>아이템: <b>{e(p.get('farm_item'))}</b><br>판매금액: <b>{amount_text(p.get('sale_amount'))}</b><br>지분: 선집합 <b>{e(c['early_weight'])}</b> / 후집합 <b>{e(c['late_weight'])}</b><br><br>선집합 총액: <b>{amount_text(c['early_total'])}</b><br>선집합: <b>{c['early_count']}명</b> / 인당 <b>{amount_text(c['early_share'])}</b><br><br>후집합 총액: <b>{amount_text(c['late_total'])}</b><br>후집합: <b>{c['late_count']}명</b> / 인당 <b>{amount_text(c['late_share'])}</b></div>"
                elif p.get("farm_result") == "노득":
                    result += "<div class='notice'>결과: <b>노득</b></div>"
                if owner_admin:
                    items = farm_items.get(p.get("place"), FARM_ITEMS.get(p.get("place"), ["기타"]))
                    opts = "".join(f"<option {'selected' if x==p.get('farm_item') else ''}>{e(x)}</option>" for x in items)
                    early_ids = set(p.get("early_ids", []) or p.get("share_ids", []))
                    late_ids = set(p.get("late_ids", []))
                    early_checks = "".join(f"<label class='check-row'><input type='checkbox' name='early_ids' value='{e(x.get('id'))}' {'checked' if x.get('id') in early_ids else ''}> {e(x.get('label'))}</label>" for x in ps) or "<p class='meta'>참여자가 없습니다.</p>"
                    late_checks = "".join(f"<label class='check-row'><input type='checkbox' name='late_ids' value='{e(x.get('id'))}' {'checked' if x.get('id') in late_ids else ''}> {e(x.get('label'))}</label>" for x in ps) or "<p class='meta'>참여자가 없습니다.</p>"
                    res_id = "res_" + p.get("id")
                    box_id = "drop_" + p.get("id")
                    display = "block" if p.get("farm_result") == "득템" else "none"
                    manage = f"""
                    <div class='farm-manage'>
                    <form method='post' action='/farming/result/{pid}'>
                    <label>파밍 결과</label>
                    <select id='{res_id}' name='farm_result' onchange="toggleFarmResultBox('{res_id}','{box_id}')">
                    <option {'selected' if p.get('farm_result')=='노득' else ''}>노득</option>
                    <option {'selected' if p.get('farm_result')=='득템' else ''}>득템</option>
                    </select>
                    <div id='{box_id}' style='display:{display}'>
                    <label>득템 아이템</label><select name='farm_item'>{opts}</select>
                    <label>판매금액</label><input name='sale_amount' value='{e(p.get('sale_amount'))}' inputmode='numeric' placeholder='예: 26000000'>
                    <label>선집합 체크</label><div class='check-box'>{early_checks}</div>
                    <label>후집합 체크</label><div class='check-box'>{late_checks}</div>
                    <label>선집합 지분</label><input name='early_weight' value='{e(p.get('early_weight', '1.0'))}' inputmode='decimal' placeholder='기본 1.0'>
                    <label>후집합 지분</label><input name='late_weight' value='{e(p.get('late_weight', '0.88'))}' inputmode='decimal' placeholder='예: 0.88 / 0.85 / 0.9'>
                    </div>
                    <button class='ok'>결과/분배 저장</button>
                    </form>
                    <form method='post' action='/farming/settle/{pid}' onsubmit="return confirm('정산완료 처리할까요?')"><button class='ok' style='width:100%;margin-top:8px'>정산완료</button></form>
                    </div>
                    """
            manual_btn = f"<button class='gray' onclick=\"addSimpleManual('{pid}')\">수동 참여자 추가</button>" if owner_admin else ""
            body = result + "<h3>참여자</h3>" + part_html + f"<div class='actions simple-action'>{join_btn}{manual_btn}</div>" + manage

        memo = f"<div class='memo'>📝 {e(p.get('memo'))}</div>" if p.get("memo") else ""
        left = ""
        if cat in ["사냥","600퀘"] and p.get("closed"):
            dt = parse_dt(p.get("closed_at"))
            if dt:
                mins = int(((dt + timedelta(hours=AUTO_DELETE_HOURS)) - kst_now()).total_seconds() // 60)
                left = f"<div class='left-time'>{max(0, mins)}분 뒤 자동삭제</div>"
        copy_text = e("\n".join(copy_lines))
        owner_buttons = ""
        if owner_admin:
            complete_btn = ""
            if cat in ["사냥", "600퀘"] and not p.get("closed"):
                complete_btn = f"<button class='ok' onclick=\"completePost('{pid}')\">모집완료</button>"
            owner_buttons = complete_btn + f"<a class='btn gray' href='/edit/{pid}'>수정</a><button class='danger' onclick=\"deletePost('{pid}')\">삭제</button>"
        out.append(f"""
        <article class='party-card post' data-post-id='{pid}' data-owner='{"1" if owner else "0"}' data-participants='{e(data_part)}'>
          <div class='post-head'><div><span class='pill {"done" if st in ["마감","정산완료"] else "open"}'>{e(st)}</span><span class='pill type'>{e(cat)}</span></div><b class='count'>{cnt_text}</b></div>
          <h2>{e(p.get('place'))}</h2>
          <div class='meta'>📍 채널 <b>{e(p.get('channel') or '미정')}</b> · ⏰ {e(post_time(p))}</div>
          <div class='meta'>👑 {e(p.get('owner_label'))} · {e(p.get('created'))}</div>
          {memo}{left}{body}
          <div class='actions'>
          <button onclick="copyPost(`{copy_text}`)">복사</button>
          <button onclick="shareKakao(`{copy_text}`)">카톡공유</button>
          <button onclick="openPartyChat('{pid}')">채팅 {len(p.get("party_chat", []))}</button>
          {owner_buttons}
          </div>
        </article>
        """)
    return "".join(out)

CSS = """
*{box-sizing:border-box}body{margin:0;color:#eef2ff;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',Arial,sans-serif;background:#0b1020}body:before{content:'';position:fixed;inset:0;background:radial-gradient(circle at 20% 0%,#263c77 0,#111a34 38%,#090d18 78%);z-index:-1}.wrap{max-width:1040px;margin:0 auto;padding:18px 14px 100px}.header{padding:12px 0 16px;border-bottom:1px solid rgba(255,255,255,.11)}h1{font-size:28px;margin:0}.sub{color:#aeb8d7;font-size:13px;margin-top:4px}.panel,.party-card{background:rgba(20,27,48,.88);border:1px solid rgba(150,165,210,.22);box-shadow:0 18px 50px rgba(0,0,0,.32);border-radius:24px;padding:16px;margin:14px 0}.top-actions{display:flex;gap:8px;flex-wrap:wrap}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.stat{background:rgba(7,11,22,.57);border:1px solid rgba(255,255,255,.10);border-radius:18px;text-align:center;padding:14px 8px}.stat b{font-size:28px;display:block}.stat span{font-size:12px;color:#aeb8d7}button,.btn{border:0;border-radius:15px;background:linear-gradient(180deg,#6a86ff,#4163ff);color:#fff;font-weight:900;padding:12px 15px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;min-height:44px;cursor:pointer}button.gray,.btn.gray{background:linear-gradient(180deg,#4c5571,#363d55)}button.danger,.danger{background:linear-gradient(180deg,#ff6666,#ce4040)}button.ok{background:linear-gradient(180deg,#2bd176,#169851)}input,select,textarea{width:100%;background:#0d1325;color:#f4f6ff;border:1px solid rgba(170,185,230,.25);border-radius:15px;padding:13px;margin:6px 0 13px;font-size:16px}label{font-size:13px;color:#bac4de;font-weight:900}.tabs{display:flex;gap:8px;overflow-x:auto;padding:4px 0}.tabs a{white-space:nowrap;color:#dce4ff;background:rgba(10,15,30,.55);border:1px solid rgba(255,255,255,.12);text-decoration:none;border-radius:999px;padding:9px 14px;font-weight:900;font-size:14px}.tabs a.on{background:linear-gradient(180deg,#6a86ff,#4163ff)}.empty{border:1px dashed rgba(255,255,255,.25);border-radius:22px;padding:46px;text-align:center;color:#c2c9dd}.post-head{display:flex;justify-content:space-between;align-items:center}.pill{display:inline-flex;border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;margin-right:4px}.pill.open{background:#123f2a;color:#9dffc4}.pill.done{background:#4d2020;color:#ffd1d1}.pill.type{background:#242c48;color:#ccd6ff}.count{font-size:18px;background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:7px 12px}h2{font-size:24px;margin:12px 0 5px}.meta{color:#b5bfd9;font-size:14px;line-height:1.6}.memo{color:#ffd16a;font-size:14px;margin-top:5px}.left-time{color:#ffb3b3;font-size:13px;font-weight:900}.slot{display:flex;justify-content:space-between;align-items:center;background:rgba(8,12,24,.62);border:1px solid rgba(255,255,255,.12);border-radius:17px;padding:12px;margin:9px 0}.slot.filled{background:rgba(18,55,33,.58);border-color:rgba(73,190,112,.35)}.actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(86px,1fr));gap:8px;margin-top:12px}.simple-action{grid-template-columns:1fr}.owner-only{display:none!important}.post[data-owner='1'] .owner-only{display:inline-flex!important}.hidden{display:none!important}.time-row{display:grid;grid-template-columns:90px 1fr;gap:8px}.quick{display:grid;grid-template-columns:1fr auto;gap:8px}.mini{font-size:13px;padding:8px 10px;min-height:34px}.notice,.alarm-guide{background:linear-gradient(180deg,rgba(255,211,106,.18),rgba(255,211,106,.08));border:1px solid rgba(255,211,106,.30);color:#ffe5a3;border-radius:18px;padding:12px;margin-top:12px;font-size:13px;line-height:1.45}.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#1e2845;border:1px solid #53648f;border-radius:999px;padding:10px 16px;opacity:0;transition:.2s;z-index:999;font-weight:900}.toast.show{opacity:1}.modal{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;z-index:100}.modal.show{display:flex}.chat-panel{width:100%;max-width:880px;margin:0 auto;border-radius:22px 22px 0 0}.chat-list{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;height:340px;overflow-y:auto;padding:10px}.msg{background:#202a47;border-radius:13px;padding:9px 11px;margin:7px 0}.msg.mine{background:#173d27;border:1px solid #2e7146}.msg-meta{font-size:12px;color:#a8b2cc;display:flex;justify-content:space-between}.chat-form{display:grid;grid-template-columns:1fr 74px;gap:7px;margin-top:9px}.chat-form input{margin:0}.member-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.member{background:rgba(8,12,24,.55);border:1px solid rgba(255,255,255,.10);border-radius:14px;padding:10px;margin:6px 0}.choice-list{display:grid;gap:8px}.choice-list button{width:100%;justify-content:flex-start;background:linear-gradient(180deg,#4c5571,#363d55)}.check-box{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:10px;margin-bottom:10px}.check-row{display:block;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}.check-row input{width:auto;margin-right:8px}.farm-manage{display:block!important;margin-top:12px}@media(max-width:680px){.wrap{padding:12px 10px 90px}h1{font-size:22px}.summary{grid-template-columns:repeat(3,1fr);gap:7px}.stat{padding:10px 4px}.stat b{font-size:21px}.actions{grid-template-columns:1fr 1fr}.top-actions>*{flex:1}.panel,.party-card{border-radius:20px;padding:13px}button,.btn{font-size:14px;padding:10px 11px}}
"""

GATE = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>입장</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>🔐 문파 전용</h1><div class='sub'>월하 · 연가 · 연희 파티모집</div></header><section class='panel'><h2>입장 비밀번호</h2><form method='post'><input name='password' type='password' placeholder='문파 비밀번호'><button style='width:100%'>입장</button></form>{% if error %}<div class='notice'>비밀번호가 맞지 않습니다.</div>{% endif %}</section></div></body></html>"""

REGISTER = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>등록</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>👤 문파원 등록</h1><div class='sub'>처음 한 번만 등록하면 됩니다.</div></header><section class='panel'><form method='post'><label>계정명</label><input name='account' value='{{ form.account }}' placeholder='예: 역인' required><label>대표 캐릭터명</label><input name='char_name' value='{{ form.char_name }}' placeholder='예: 역인' required><label>직업/차수</label><select name='job'>{% for job in jobs %}<option {% if form.job==job %}selected{% endif %}>{{ job }}</option>{% endfor %}</select><button style='width:100%'>승인 요청</button></form>{% if error %}<div class='notice'>{{ error }}</div>{% endif %}<p class='meta'>관리자 승인 후 이용 가능합니다.</p></section></div></body></html>"""

WAIT = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>대기</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>⏳ 승인 대기중</h1></header><section class='panel'><p>{{ user.account if user else "승인 대기중" }} 계정이 승인 대기중입니다.</p><div class='top-actions'><a class='btn' href='/admin'>관리자 페이지</a><form method='post' action='/logout'><button class='gray'>로그아웃</button></form></div><p class='meta'>최초 세팅이면 관리자 페이지에서 기존 관리자 비밀번호로 임시 관리자 모드에 들어가 승인할 수 있습니다.</p></section></div></body></html>"""

MAIN = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>파티모집</title><style>{{ css }}</style></head><body>
<div class='wrap'><header class='header'><h1>⚔️ 월하 · 연가 · 연희 파티모집</h1><div class='sub'>Made by 역인(진선)</div></header>{% if notice %}<div class='notice'>📢 {{ notice }}</div>{% endif %}
{% if page=='home' %}
<section class='panel'><div class='top-actions'><a class='btn' href='/new'>+ 모집글</a><a class='btn gray' href='/chars'>내 캐릭터</a><button class='gray' onclick='openGlobalChat()'>통합채팅</button><button class='gray' onclick='toggleAlarm()' id='alarmBtn'>🔔 알림 ON</button></div><div class='summary'><div class='stat'><b>{{ open_count }}</b><span>모집중</span></div><div class='stat'><b id='onlineCount'>1</b><span>접속중</span></div><div class='stat'><b id='myCount'>0</b><span>내 참여</span></div></div><div class='alarm-guide'>🔔 알림은 사이트가 열려있는 동안 동작합니다. 버튼을 눌러 브라우저 알림 권한을 허용하면 새 모집글/참여/채팅 알림을 받을 수 있습니다.</div><div class='tabs'>{% for f in cats %}<a class='{% if f==filter_value %}on{% endif %}' href='/?filter={{ f }}'>{{ f }}</a>{% endfor %}</div></section><section class='panel'><h2>문파원 접속 현황</h2><div class='member-grid'>{{ member_html|safe }}</div></section><div id='postList'>{{ post_list|safe }}</div>
{% endif %}
{% if page=='new' or page=='edit' %}
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h2>{% if page=='edit' %}수정{% else %}모집글 올리기{% endif %}</h2><form method='post' action='{% if page=="edit" %}/edit/{{ post.id }}{% else %}/create{% endif %}' onsubmit='return prepareSubmit()'><label>작성 캐릭터</label><select name='owner_char_id'>{% for c in chars %}<option value='{{ c.id }}'>{{ c.name }}({{ c.job }})</option>{% endfor %}</select><label>종류</label><select name='category' id='typeSelect' onchange='updatePlaces();toggleSlotBox()'>{% for c in cats_no_all %}<option {% if post and post.category==c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><label>장소</label>{% for cat, vals in places.items() %}<select name='place_{{ cat }}' id='place_{{ cat }}' class='place-select hidden'>{% for p in vals %}<option {% if post and post.place==p %}selected{% endif %}>{{ p }}</option>{% endfor %}</select>{% endfor %}<label>채널 4자리</label><input name='channel' id='channelInput' maxlength='4' inputmode='numeric' value='{{ post.channel if post else "" }}' placeholder='예: 3385' oninput='numbersOnly(this)'><label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' value='{{ post.start_time if post else "" }}' placeholder='예: 09:00'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option selected>오후</option></select><input name='end_time' value='{{ post.end_time if post else "" }}' placeholder='예: 11:00'></div><label>메모</label><textarea name='memo'>{{ post.memo if post else "" }}</textarea><div class='panel' id='slotPanel'><label>사냥 직업 자리 추가</label><div class='quick'><select id='slotJob'>{% for j in jobs %}<option>{{ j }}</option>{% endfor %}</select><button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slotsBox'></div></div><div class='notice hidden' id='simpleNotice'>600퀘는 참여 버튼 방식입니다. 파밍은 관리자/부문파장만 생성할 수 있습니다.</div><button style='width:100%'>저장</button></form></section>
{% endif %}
{% if page=='chars' %}
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h2>내 캐릭터</h2><form method='post' action='/chars/add'><label>캐릭터명</label><input name='name' required><label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button style='width:100%'>캐릭터 추가 요청</button></form></section><section class='panel'><h2>등록 캐릭터</h2>{% for c in user.chars %}<div class='member'>{{ c.name }}({{ c.job }}) · {{ c.status }} {% if c.status=='approved' %}<form method='post' action='/chars/select/{{ c.id }}' style='display:inline'><button class='mini'>대표선택</button></form>{% endif %}</div>{% endfor %}</section>
{% endif %}
</div>
<div id='globalModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>💬 통합채팅</b><button class='mini gray' onclick='closeGlobalChat()'>닫기</button></div><div class='alarm-guide'>최근 100개 유지 · 24시간 자동삭제 · 본인 5분 이내 삭제 가능</div><div id='globalChatList' class='chat-list'></div><div class='chat-form'><input id='globalChatText' placeholder='메시지'><button onclick='sendGlobalChat()'>전송</button></div></div></div>
<div id='partyModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>💬 채팅</b><button class='mini gray' onclick='closePartyChat()'>닫기</button></div><div id='partyChatList' class='chat-list'></div><div class='chat-form'><input id='partyChatText' placeholder='메시지'><button onclick='sendPartyChat()'>전송</button></div></div></div>
<div id='charPickModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>참여 캐릭터 선택</b><button class='mini gray' onclick='closeCharPick()'>닫기</button></div><div id='charPickList' class='choice-list'></div></div></div><div id='toast' class='toast'></div>
<script>
const CURRENT_USER_ID="{{ user.id if user else '' }}";let globalOpen=false;let partyId=null;let knownPosts=new Set();let firstLoad=true;
function qs(id){return document.getElementById(id)}function toast(m){const t=qs('toast');if(!t){alert(m);return}t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),1600)}
function numbersOnly(el){el.value=(el.value||'').replace(/[^0-9]/g,'').slice(0,4)}function prepareSubmit(){const cat=qs('typeSelect')?.value;const ch=qs('channelInput');if(ch){numbersOnly(ch);if(ch.value.length!==4){alert('채널은 숫자 4자리로 입력해줘.');return false}}if(cat==='사냥'&&document.querySelectorAll('#slotsBox input[name="slots"]').length===0&&location.pathname==='/new'){alert('사냥은 모집 자리를 하나 이상 추가해줘.');return false}return true}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function updatePlaces(){const cat=qs('typeSelect')?.value;document.querySelectorAll('.place-select').forEach(x=>x.classList.add('hidden'));const t=qs('place_'+cat);if(t)t.classList.remove('hidden')}
function toggleSlotBox(){const cat=qs('typeSelect')?.value;const p=qs('slotPanel'), n=qs('simpleNotice');if(!p||!n)return;if(cat==='사냥'){p.classList.remove('hidden');n.classList.add('hidden')}else{p.classList.add('hidden');n.classList.remove('hidden')}}
function addSlot(){const job=qs('slotJob')?.value, box=qs('slotsBox');if(!job||!box)return;const d=document.createElement('div');d.className='slot';d.innerHTML='<div><b>'+escapeHtml(job)+'</b><br>빈자리</div><button type="button" class="mini danger" onclick="this.parentElement.remove()">삭제</button><input type="hidden" name="slots" value="'+escapeHtml(job)+'">';box.appendChild(d)}
function toggleFarmResultBox(sid,bid){const s=qs(sid),b=qs(bid);if(s&&b)b.style.display=s.value==='득템'?'block':'none'}
function copyPost(t){navigator.clipboard?navigator.clipboard.writeText(t).then(()=>toast('복사됨')):alert(t)}
function shareKakao(t){const txt='월하 · 연가 · 연희 파티모집\\n\\n'+t+'\\n\\n'+location.origin;if(navigator.share)navigator.share({title:'파티모집',text:txt,url:location.origin}).catch(()=>copyPost(txt));else{copyPost(txt);toast('공유문구 복사됨')}}
function isEditingPost(){const a=document.activeElement;if(!a)return false;if(a.closest&&a.closest('.farm-manage'))return true;if(['INPUT','SELECT','TEXTAREA'].includes(a.tagName)&&a.closest&&a.closest('.post'))return true;return false}
function refresh(){if(location.pathname!='/')return;if(isEditingPost())return;fetch('/api/posts'+location.search,{cache:'no-store'}).then(r=>r.text()).then(h=>{qs('postList').innerHTML=h;scanAlarms();countMine()}).catch(()=>{})}
function countMine(){let c=0;document.querySelectorAll('.post').forEach(p=>{if(p.dataset.owner==='1'||(CURRENT_USER_ID&&(p.dataset.participants||'').includes(CURRENT_USER_ID)))c++});if(qs('myCount'))qs('myCount').textContent=c}
function closeCharPick(){qs('charPickModal').classList.remove('show')}
function chooseChar(cb, job){fetch('/api/mychars'+(job?'?job='+encodeURIComponent(job):''),{cache:'no-store'}).then(r=>r.json()).then(d=>{const cs=d.chars||[];if(!cs.length){toast('사용 가능한 캐릭터가 없습니다.');return}if(cs.length===1){cb(cs[0].id);return}const box=qs('charPickList');box.innerHTML='';cs.forEach(c=>{const b=document.createElement('button');b.textContent=c.label+' 으로 참여';b.onclick=()=>{cb(c.id);closeCharPick()};box.appendChild(b)});qs('charPickModal').classList.add('show')})}
function joinSlot(pid,sid,job){chooseChar(cid=>fetch('/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid,char_id:cid})}).then(()=>refresh()), job)}
function joinSimple(pid){chooseChar(cid=>fetch('/simple/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,char_id:cid})}).then(()=>refresh()))}
function leaveSimple(pid){if(!confirm('참여를 취소할까?'))return;fetch('/simple/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid})}).then(()=>refresh())}
function removeSimple(pid,participantId){if(!confirm('이 참여자를 목록에서 뺄까?'))return;fetch('/simple/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,participant_id:participantId})}).then(()=>refresh())}
function addSimpleManual(pid){const name=prompt('수동으로 추가할 참여자 이름을 입력해줘');if(!name)return;fetch('/simple/add_manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,name:name})}).then(()=>refresh())}
function addExternal(pid,sid){const name=prompt('외부인 닉네임');if(!name)return;fetch('/external',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid,name:name})}).then(()=>refresh())}
function leaveSlot(pid,sid){if(!confirm('비울까?'))return;fetch('/leave',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,slot_id:sid})}).then(()=>refresh())}
function deletePost(pid){if(!confirm('삭제할까?'))return;fetch('/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid})}).then(r=>r.json()).then(x=>{toast(x.ok?'삭제됨':x.reason||'삭제 실패');refresh()})}
function completePost(pid){if(!confirm('모집완료 처리할까?'))return;fetch('/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid})}).then(r=>r.json()).then(x=>{toast(x.ok?'모집완료됨':x.reason||'실패');refresh()})}
function openGlobalChat(){globalOpen=true;qs('globalModal').classList.add('show');refreshGlobalChat()}function closeGlobalChat(){globalOpen=false;qs('globalModal').classList.remove('show')}
function refreshGlobalChat(){if(!globalOpen)return;fetch('/api/global_chat',{cache:'no-store'}).then(r=>r.text()).then(h=>{const b=qs('globalChatList');b.innerHTML=h;b.scrollTop=b.scrollHeight})}
function sendGlobalChat(){const i=qs('globalChatText');if(!i.value.trim())return;fetch('/global_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:i.value.trim()})}).then(r=>r.json()).then(x=>{if(!x.ok)toast(x.reason||'실패');else{i.value='';refreshGlobalChat()}})}
function deleteGlobalChat(id){fetch('/global_chat/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})}).then(()=>refreshGlobalChat())}
function openPartyChat(pid){partyId=pid;qs('partyModal').classList.add('show');refreshPartyChat()}function closePartyChat(){partyId=null;qs('partyModal').classList.remove('show')}
function refreshPartyChat(){if(!partyId)return;fetch('/api/party_chat/'+partyId,{cache:'no-store'}).then(r=>r.text()).then(h=>{const b=qs('partyChatList');b.innerHTML=h;b.scrollTop=b.scrollHeight})}
function sendPartyChat(){const i=qs('partyChatText');if(!partyId||!i.value.trim())return;fetch('/party_chat/'+partyId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:i.value.trim()})}).then(r=>r.json()).then(x=>{if(!x.ok)toast(x.reason||'실패');else{i.value='';refreshPartyChat();refresh()}})}
function alarmOn(){return localStorage.getItem('baram_alarm_off')!=='1'}
function updateAlarmBtn(){if(qs('alarmBtn'))qs('alarmBtn').textContent=alarmOn()?'🔔 알림 ON':'🔕 알림 OFF'}
function notifyUser(title, body){
  if(!alarmOn())return;
  toast(title + (body ? ' - ' + body : ''));
  try{
    if('Notification' in window && Notification.permission==='granted'){
      new Notification(title,{body:body||'',silent:false});
    }
  }catch(e){}
}
function toggleAlarm(){
  const turningOff=alarmOn();
  localStorage.setItem('baram_alarm_off',turningOff?'1':'0');
  updateAlarmBtn();
  if(!turningOff && 'Notification' in window && Notification.permission==='default'){
    Notification.requestPermission().then(()=>toast('알림이 켜졌습니다.'));
  }else{
    toast(turningOff?'알림 꺼짐':'알림 켜짐');
  }
}
function scanAlarms(){document.querySelectorAll('.post').forEach(p=>{const id=p.dataset.postId;if(id&&!knownPosts.has(id)){if(!firstLoad&&alarmOn())notifyUser('새 모집글','새 글이 올라왔습니다.');knownPosts.add(id)}});firstLoad=false}
let eventState=null;
function pollEvents(){
  if(location.pathname!='/')return;
  fetch('/api/events',{cache:'no-store'}).then(r=>r.json()).then(ev=>{
    if(!ev.ok)return;
    if(!eventState){eventState=ev;return;}
    const oldPosts={};(eventState.posts||[]).forEach(p=>oldPosts[p.id]=p);
    const newPosts={};(ev.posts||[]).forEach(p=>newPosts[p.id]=p);
    (ev.posts||[]).forEach(p=>{
      const old=oldPosts[p.id];
      if(!old){
        notifyUser('새 모집글', (p.category||'')+' '+(p.place||''));
        return;
      }
      if(p.owner && p.participant_count>old.participant_count){
        notifyUser('참여 알림', (p.place||'모집글')+'에 참여자가 추가됐습니다.');
      }
      if(p.owner && p.chat_count>old.chat_count){
        notifyUser('파티채팅 알림', (p.place||'모집글')+'에 새 채팅이 있습니다.');
      }
    });
    if(ev.chat_count>eventState.chat_count && ev.chat_last_uid!==CURRENT_USER_ID){
      notifyUser('통합채팅', (ev.chat_last_label||'문파원')+': '+(ev.chat_last_text||'새 메시지'));
    }
    eventState=ev;
  }).catch(()=>{});
}
function heartbeat(){fetch('/api/heartbeat',{method:'POST'}).then(r=>r.json()).then(x=>{if(qs('onlineCount'))qs('onlineCount').textContent=x.online||1}).catch(()=>{})}
document.addEventListener('DOMContentLoaded',()=>{updatePlaces();toggleSlotBox();updateAlarmBtn();heartbeat();scanAlarms();pollEvents();countMine();['globalChatText','partyChatText'].forEach(id=>{const i=qs(id);if(i)i.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();id==='globalChatText'?sendGlobalChat():sendPartyChat()}})})});
setInterval(refresh,2500);setInterval(refreshGlobalChat,1600);setInterval(refreshPartyChat,1600);setInterval(heartbeat,15000);setInterval(pollEvents,2500);
</script></body></html>
"""

ADMIN = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>관리자</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>🔒 관리자</h1></header><a class='btn gray' href='/'>메인</a>{% if admin_msg %}<div class='notice'>{{ admin_msg }}</div>{% endif %}<section class='panel'><b>현재 로그인</b><br>{{ current_label }}</section>{% if not admin_ok %}<section class='panel'><form method='post' action='/admin/login'><label>최초 최고관리자 비밀번호</label><input name='password' type='password'><button>현재 계정을 임시 관리자 접속 / 최고관리자 등록</button></form><p class='meta'>먼저 메인 사이트에서 본인 문파원 계정으로 로그인되어 있어야 합니다. 로그인 계정이 없으면 최고관리자로 지정할 대상이 없습니다.</p></section>{% else %}<section class='panel'><div class='top-actions'><form method='post' action='/admin/logout'><button class='gray'>로그아웃</button></form><form method='post' action='/admin/clear_closed'><button>마감글 정리</button></form><form method='post' action='/admin/clear_chat'><button class='danger'>통합채팅 삭제</button></form></div></section><section class='panel'><h2>문파 설정</h2><form method='post' action='/admin/settings'><label>입장 비밀번호</label><input name='access_password'><label>관리자 비밀번호</label><input name='admin_password'><button>저장</button></form></section><section class='panel'><h2>공지</h2><form method='post' action='/admin/notice'><textarea name='notice'>{{ notice }}</textarea><button>저장</button></form></section><section class='panel'><h2>파밍 아이템</h2><form method='post' action='/admin/farm_items'><label>해골왕</label><input name='items_해골왕' value='{{ farm_items.get("해골왕", [])|join(", ") }}'><label>어금니</label><input name='items_어금니' value='{{ farm_items.get("어금니", [])|join(", ") }}'><button>저장</button></form></section><section class='panel'><h2>가입 승인</h2>{% for u in pending_users %}<div class='member'><b>{{ u.account }}</b> / {% for c in u.chars %}{{ c.name }}({{ c.job }}) {% endfor %}<form method='post' action='/admin/user/{{ u.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/user/{{ u.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p>대기 없음</p>{% endfor %}</section><section class='panel'><h2>캐릭터 승인</h2>{% for item in pending_chars %}<div class='member'><b>{{ item.user.account }}</b> / {{ item.char.name }}({{ item.char.job }})<form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p>대기 없음</p>{% endfor %}</section><section class='panel'><h2>권한 관리</h2>{% for u in users %}<div class='member'><b>{{ u.account }}</b> · 권한: {{ {'member':'일반','admin':'관리자/부문파장','super':'최고관리자'}.get(u.role|default('member'), u.role|default('member')) }} · {{ u.status }}{% if u.blocked %} · 차단{% endif %}<br>{% for c in u.chars %}{{ c.name }}({{ c.job }}) - {{ c.status }}<br>{% endfor %}{% if super_ok %}<form method='post' action='/admin/role/{{ u.id }}/member' style='display:inline'><button class='mini gray'>일반</button></form><form method='post' action='/admin/role/{{ u.id }}/admin' style='display:inline'><button class='mini ok'>관리자</button></form><form method='post' action='/admin/role/{{ u.id }}/super' style='display:inline'><button class='mini'>최고관리자</button></form>{% endif %}<form method='post' action='/admin/user/{{ u.id }}/toggle_block' style='display:inline'><button class='mini danger'>차단/해제</button></form>{% if super_ok %}<form method='post' action='/admin/delete_user/{{ u.id }}' style='display:inline' onsubmit="return confirm('정말 이 회원을 삭제할까요?')"><button class='mini danger'>회원삭제</button></form>{% endif %}</div>{% endfor %}</section><section class='panel'><h2>글 관리</h2>{% for p in posts %}<div class='member'><b>{{ p.place }}</b> / {{ p.category }} / {{ p.owner_label }}<form method='post' action='/admin/delete_post/{{ p.id }}'><button class='mini danger'>삭제</button></form></div>{% endfor %}</section>{% endif %}</div></body></html>"""

@app.before_request
def gate_guard():
    if request.path in ["/gate","/register","/wait","/logout","/health","/manifest.json","/sw.js"] or request.path.startswith("/admin"):
        return
    d = load()
    if not can_enter(d):
        return redirect("/gate")
    u = current_user(d)
    if not u:
        return redirect("/register")
    if not approved(u):
        return redirect("/wait")
    touch()

@app.route("/health")
def health():
    return jsonify(ok=True, online=online_count(), time=text_now())

@app.route("/gate", methods=["GET","POST"])
def gate():
    d = load()
    if request.method == "GET" and approved(current_user(d)):
        return redirect("/")
    err = False
    if request.method == "POST":
        if request.form.get("password") == d["settings"].get("access_password"):
            session["access_ok"] = True
            return redirect("/")
        err = True
    return render_template_string(GATE, css=CSS, error=err)

@app.route("/register", methods=["GET","POST"])
def register():
    d = load()
    u = current_user(d)
    if request.method == "GET":
        if approved(u):
            return redirect("/")
        if u and u.get("status") == "pending":
            return redirect("/wait")
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form={"account":"","char_name":"","job":"검성"}, error="")
    form = {"account": request.form.get("account","").strip(), "char_name": request.form.get("char_name","").strip(), "job": request.form.get("job","검성")}
    if not form["account"] or not form["char_name"]:
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form=form, error="계정명과 캐릭터명을 입력해주세요.")
    if form["char_name"].lower() in all_char_names(d):
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form=form, error="이미 등록된 캐릭터명입니다.")
    uid, cid = new_id(), new_id()
    nu = {"id":uid,"account":form["account"],"status":"pending","role":"member","blocked":False,"selected_char_id":cid,"created":text_now(),"chars":[{"id":cid,"name":form["char_name"],"job":form["job"],"status":"pending"}]}
    save(lambda x: x["users"].append(nu))
    session["uid"] = uid
    session["access_ok"] = True
    return redirect("/wait")

@app.route("/wait")
def wait():
    d = load()
    u = current_user(d)
    if approved(u):
        return redirect("/")
    return render_template_string(WAIT, css=CSS, user=u)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/gate")

@app.route("/")
def home():
    d = load()
    u = current_user(d)
    touch()
    filt = request.args.get("filter","전체")
    posts = list(reversed(d["posts"]))
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    open_count = sum(1 for p in posts if status_text(p) in ["모집중","진행중"])
    return render_template_string(MAIN, css=CSS, page="home", user=u, cats=CATEGORIES, cats_no_all=CATEGORIES[1:], filter_value=filt, post_list=render_posts(posts,u,d["settings"].get("farm_items", FARM_ITEMS), admin=is_admin_user(u)), open_count=open_count, member_html=member_html(d), notice=d["settings"].get("notice",""), jobs=JOBS, places=PLACES)

@app.route("/api/posts")
def api_posts():
    d = load()
    u = current_user(d)
    filt = request.args.get("filter","전체")
    posts = list(reversed(d["posts"]))
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    return render_posts(posts,u,d["settings"].get("farm_items", FARM_ITEMS), admin=is_admin_user(u))

@app.route("/new")
def new_page():
    d = load()
    u = current_user(d)
    if not chars(u):
        return redirect("/chars")
    allowed_categories = ["사냥", "600퀘", "파밍"] if is_admin_user(u) else ["사냥", "600퀘"]
    return render_template_string(MAIN, css=CSS, page="new", post=None, chars=chars(u), user=u, cats_no_all=allowed_categories, jobs=JOBS, places=PLACES, notice="")

@app.route("/create", methods=["POST"])
def create():
    d = load()
    u = current_user(d)
    c = has_char(u, request.form.get("owner_char_id"))
    if not c:
        return redirect("/chars")
    cat = request.form.get("category","사냥")
    if cat == "파밍" and not is_admin_user(u):
        return redirect("/")
    slots = []
    if cat == "사냥":
        slots = [{"id":new_id(),"job":j,"uid":"","char_id":"","label":"","external":""} for j in request.form.getlist("slots")]
    p = {"id":new_id(),"owner_uid":u["id"],"owner_label":label(c),"category":cat,"place":request.form.get(f"place_{cat}",""),"channel":digits(request.form.get("channel"),4),"start_period":request.form.get("start_period",""),"start_time":request.form.get("start_time","").strip(),"end_period":request.form.get("end_period",""),"end_time":request.form.get("end_time","").strip(),"memo":request.form.get("memo","").strip(),"slots":slots,"participants":[],"closed":False,"closed_at":"","party_chat":[],"created":text_now(),"farm_status":"진행중","farm_result":"","farm_item":"","sale_amount":"","share_ids":[]}
    save(lambda x: x["posts"].append(p))
    return redirect("/")

@app.route("/edit/<pid>", methods=["GET","POST"])
def edit(pid):
    d = load()
    u = current_user(d)
    p = find_post(d, pid)
    if not p or p.get("owner_uid") != u.get("id"):
        return redirect("/")
    if request.method == "GET":
        allowed_categories = ["사냥", "600퀘", "파밍"] if is_admin_user(u) else ["사냥", "600퀘"]
        return render_template_string(MAIN, css=CSS, page="edit", post=p, chars=chars(u), user=u, cats_no_all=allowed_categories, jobs=JOBS, places=PLACES, notice="")
    def fn(x):
        pp = find_post(x, pid)
        if pp and pp.get("owner_uid") == u.get("id"):
            pp["channel"] = digits(request.form.get("channel"),4)
            pp["start_time"] = request.form.get("start_time","").strip()
            pp["end_time"] = request.form.get("end_time","").strip()
            pp["memo"] = request.form.get("memo","").strip()
    save(fn)
    return redirect("/")

@app.route("/chars")
def chars_page():
    d=load(); u=current_user(d)
    return render_template_string(MAIN, css=CSS, page="chars", user=u, jobs=JOBS, places=PLACES, cats_no_all=CATEGORIES[1:], notice="")

@app.route("/chars/add", methods=["POST"])
def char_add():
    d=load(); u=current_user(d)
    name=request.form.get("name","").strip(); job=request.form.get("job","")
    if name and name.lower() not in all_char_names(d):
        save(lambda x: find_user(x,u["id"])["chars"].append({"id":new_id(),"name":name,"job":job,"status":"pending"}))
    return redirect("/chars")

@app.route("/chars/select/<cid>", methods=["POST"])
def char_select(cid):
    d=load(); u=current_user(d)
    if has_char(u,cid):
        save(lambda x: find_user(x,u["id"]).update({"selected_char_id":cid}))
    return redirect("/chars")

@app.route("/api/mychars")
def mychars():
    d=load(); u=current_user(d); job=request.args.get("job","")
    cs=chars(u)
    if job:
        cs=[c for c in cs if c.get("job")==job]
    return jsonify(chars=[{"id":c["id"],"label":label(c)} for c in cs])

@app.route("/join", methods=["POST"])
def join():
    r=request.get_json(force=True); d=load(); u=current_user(d); c=has_char(u,r.get("char_id"))
    if not c: return jsonify(ok=False)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("category")!="사냥": return
        for s in p["slots"]:
            if s.get("id")==r.get("slot_id") and not s.get("uid") and not s.get("external"):
                s.update({"uid":u["id"],"char_id":c["id"],"label":label(c)})
                if normal_filled(p)[0] >= normal_filled(p)[1]:
                    p["closed"]=True; p["closed_at"]=iso_now()
                return
    save(fn); return jsonify(ok=True)

@app.route("/leave", methods=["POST"])
def leave():
    r=request.get_json(force=True); d=load(); u=current_user(d)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p: return
        owner=p.get("owner_uid")==u.get("id")
        for s in p.get("slots",[]):
            if s.get("id")==r.get("slot_id") and (owner or s.get("uid")==u.get("id")):
                s.update({"uid":"","char_id":"","label":"","external":""}); p["closed"]=False; p["closed_at"]=""
    save(fn); return jsonify(ok=True)

@app.route("/external", methods=["POST"])
def external():
    r=request.get_json(force=True); d=load(); u=current_user(d); name=(r.get("name") or "").strip()[:20]
    if not name: return jsonify(ok=False)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("owner_uid")!=u.get("id") or p.get("category")!="사냥": return
        for s in p["slots"]:
            if s.get("id")==r.get("slot_id") and not s.get("uid") and not s.get("external"):
                s["external"]=name+"(외부)"
                if normal_filled(p)[0] >= normal_filled(p)[1]:
                    p["closed"]=True; p["closed_at"]=iso_now()
    save(fn); return jsonify(ok=True)

@app.route("/simple/join", methods=["POST"])
def simple_join():
    r=request.get_json(force=True); d=load(); u=current_user(d); c=has_char(u,r.get("char_id"))
    if not c: return jsonify(ok=False)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("category") not in ["600퀘","파밍"]: return
        if p.get("category")=="600퀘" and (p.get("closed") or len(p.get("participants", [])) >= QUEST_MAX_PARTICIPANTS): return
        if p.get("category")=="파밍" and p.get("farm_status")=="정산완료": return
        if any(a.get("uid")==u["id"] for a in p["participants"]): return
        pid=new_id()
        p["participants"].append({"id":pid,"uid":u["id"],"char_id":c["id"],"label":label(c)})
        if p.get("category")=="600퀘" and len(p.get("participants", [])) >= QUEST_MAX_PARTICIPANTS:
            p["closed"]=True; p["closed_at"]=iso_now()
        if p.get("category")=="파밍":
            p.setdefault("share_ids",[]).append(pid)
            p.setdefault("early_ids",[]).append(pid)
            p.setdefault("early_ids",[]).append(pid)
    save(fn); return jsonify(ok=True)

@app.route("/simple/leave", methods=["POST"])
def simple_leave():
    r=request.get_json(force=True); d=load(); u=current_user(d)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("category") not in ["600퀘","파밍"]: return
        if p.get("category")=="파밍" and p.get("farm_status")=="정산완료": return
        rem=[a.get("id") for a in p["participants"] if a.get("uid")==u["id"]]
        p["participants"]=[a for a in p["participants"] if a.get("uid")!=u["id"]]
        p["share_ids"]=[i for i in p.get("share_ids",[]) if i not in rem]
        p["early_ids"]=[i for i in p.get("early_ids",[]) if i not in rem]
        p["late_ids"]=[i for i in p.get("late_ids",[]) if i not in rem]
    save(fn); return jsonify(ok=True)


@app.route("/simple/remove", methods=["POST"])
def simple_remove():
    r=request.get_json(force=True); d=load(); u=current_user(d)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("category") not in ["600퀘","파밍"] or (p.get("owner_uid")!=u.get("id") and not is_admin_user(u)):
            return
        rid=r.get("participant_id")
        p["participants"]=[a for a in p.get("participants",[]) if a.get("id")!=rid]
        p["share_ids"]=[i for i in p.get("share_ids",[]) if i!=rid]
        p["early_ids"]=[i for i in p.get("early_ids",[]) if i!=rid]
        p["late_ids"]=[i for i in p.get("late_ids",[]) if i!=rid]
    save(fn); return jsonify(ok=True)

@app.route("/simple/add_manual", methods=["POST"])
def simple_add_manual():
    r=request.get_json(force=True); d=load(); u=current_user(d)
    name=(r.get("name") or "").strip()[:24]
    if not name:
        return jsonify(ok=False)
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or p.get("category") not in ["600퀘","파밍"] or (p.get("owner_uid")!=u.get("id") and not is_admin_user(u)):
            return
        if p.get("category")=="600퀘" and (p.get("closed") or len(p.get("participants", [])) >= QUEST_MAX_PARTICIPANTS):
            return
        pid=new_id()
        p.setdefault("participants",[]).append({"id":pid,"uid":"","char_id":"","label":name+"(수동)"})
        if p.get("category")=="600퀘" and len(p.get("participants", [])) >= QUEST_MAX_PARTICIPANTS:
            p["closed"]=True; p["closed_at"]=iso_now()
        if p.get("category")=="파밍":
            p.setdefault("share_ids",[]).append(pid)
            p.setdefault("early_ids",[]).append(pid)
            p.setdefault("early_ids",[]).append(pid)
    save(fn); return jsonify(ok=True)

@app.route("/farming/result/<pid>", methods=["POST"])
def farming_result(pid):
    d=load(); u=current_user(d)
    def fn(x):
        p=find_post(x,pid)
        if not p or p.get("category")!="파밍" or (p.get("owner_uid")!=u.get("id") and not is_admin_user(u)): return
        res=request.form.get("farm_result","노득")
        p["farm_result"]=res
        if res=="득템":
            p["farm_item"]=request.form.get("farm_item","")
            p["sale_amount"]=digits(request.form.get("sale_amount",""))
            late_ids = request.form.getlist("late_ids")
            early_ids = [x for x in request.form.getlist("early_ids") if x not in late_ids]
            p["early_ids"]=early_ids
            p["late_ids"]=late_ids
            p["early_weight"]="".join(ch for ch in request.form.get("early_weight","1.0") if ch.isdigit() or ch==".") or "1.0"
            p["late_weight"]="".join(ch for ch in request.form.get("late_weight","0.88") if ch.isdigit() or ch==".") or "0.88"
            # 예전 호환용
            p["share_ids"]=list(dict.fromkeys(p.get("early_ids", []) + p.get("late_ids", [])))
        else:
            p["farm_item"]=""; p["sale_amount"]=""; p["share_ids"]=[]; p["early_ids"]=[]; p["late_ids"]=[]; p["early_weight"]="1.0"; p["late_weight"]="0.88"; p["late_percent"]="15"; p["late_share"]=""
        p["farm_status"]="결과입력완료"
    save(fn); return redirect("/")

@app.route("/farming/settle/<pid>", methods=["POST"])
def farming_settle(pid):
    d=load(); u=current_user(d)
    save(lambda x: (find_post(x,pid) or {}).update({"farm_status":"정산완료"}) if (find_post(x,pid) and (find_post(x,pid).get("owner_uid")==u.get("id") or is_admin_user(u))) else None)
    return redirect("/")


@app.route("/complete", methods=["POST"])
def complete_post():
    r=request.get_json(force=True); d=load(); u=current_user(d); result={"ok":False,"reason":"작성자만 가능"}
    def fn(x):
        p=find_post(x,r.get("post_id"))
        if not p or (p.get("owner_uid")!=u.get("id") and not is_admin_user(u)) or p.get("category") not in ["사냥","600퀘"]:
            return
        p["closed"]=True
        p["closed_at"]=iso_now()
        result["ok"]=True
    save(fn); return jsonify(result)

@app.route("/delete", methods=["POST"])
def delete():
    r=request.get_json(force=True); d=load(); u=current_user(d); result={"ok":False,"reason":"작성자만 삭제 가능"}
    def fn(x):
        new=[]
        for p in x["posts"]:
            if p.get("id")==r.get("post_id") and (p.get("owner_uid")==u.get("id") or is_admin_user(u)):
                result["ok"]=True
            else:
                new.append(p)
        x["posts"]=new
    save(fn); return jsonify(result)

@app.route("/api/global_chat")
def api_global_chat():
    d=load(); u=current_user(d)
    return chat_rows(d["chat"], u.get("id"))

@app.route("/global_chat", methods=["POST"])
def global_chat():
    r=request.get_json(force=True); d=load(); u=current_user(d); c=selected_char(u); txt=(r.get("text") or "").strip()[:150]
    if not txt or not c: return jsonify(ok=False, reason="채팅 불가")
    msg={"id":new_id(),"uid":u["id"],"label":label(c),"text":txt,"time":time_now(),"created_at":iso_now()}
    save(lambda x: x["chat"].append(msg)); return jsonify(ok=True)

@app.route("/global_chat/delete", methods=["POST"])
def global_chat_delete():
    r=request.get_json(force=True); d=load(); u=current_user(d); mid=r.get("id")
    cut=kst_now()-timedelta(minutes=CHAT_DELETE_MINUTES)
    def fn(x):
        x["chat"]=[m for m in x["chat"] if not (m.get("id")==mid and m.get("uid")==u.get("id") and parse_dt(m.get("created_at")) and parse_dt(m.get("created_at"))>=cut)]
    save(fn); return jsonify(ok=True)

@app.route("/api/party_chat/<pid>")
def party_chat_api(pid):
    d=load(); u=current_user(d); p=find_post(d,pid)
    if not p or not can_chat(p,u):
        return "<div class='msg'>참여자만 이용 가능합니다.</div>"
    return chat_rows(p.get("party_chat",[]), u.get("id"), False)

@app.route("/party_chat/<pid>", methods=["POST"])
def party_chat_send(pid):
    r=request.get_json(force=True); d=load(); u=current_user(d); p=find_post(d,pid); c=selected_char(u); txt=(r.get("text") or "").strip()[:150]
    if not p or not can_chat(p,u) or not c or not txt:
        return jsonify(ok=False, reason="참여자만 이용 가능")
    msg={"id":new_id(),"uid":u["id"],"label":label(c),"text":txt,"time":time_now(),"created_at":iso_now()}
    save(lambda x: find_post(x,pid).setdefault("party_chat",[]).append(msg)); return jsonify(ok=True)


@app.route("/api/events")
def api_events():
    d=load()
    u=current_user(d)
    uid = u.get("id") if u else ""
    posts=[]
    for p in d.get("posts", []):
        owner = p.get("owner_uid") == uid
        if p.get("category") == "사냥":
            participants = [s.get("uid") or s.get("external") or "" for s in p.get("slots", []) if s.get("uid") or s.get("external")]
        else:
            participants = [x.get("uid") or x.get("label") or "" for x in p.get("participants", [])]
        posts.append({
            "id": p.get("id"),
            "owner": owner,
            "category": p.get("category"),
            "place": p.get("place"),
            "participant_count": len(participants),
            "participants_key": "|".join(participants),
            "chat_count": len(p.get("party_chat", [])),
            "status": status_text(p)
        })
    return jsonify({
        "ok": True,
        "now": iso_now(),
        "chat_count": len(d.get("chat", [])),
        "chat_last_id": d.get("chat", [{}])[-1].get("id", "") if d.get("chat") else "",
        "chat_last_text": d.get("chat", [{}])[-1].get("text", "") if d.get("chat") else "",
        "chat_last_label": d.get("chat", [{}])[-1].get("label", "") if d.get("chat") else "",
        "chat_last_uid": d.get("chat", [{}])[-1].get("uid", "") if d.get("chat") else "",
        "posts": posts
    })

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    touch(); return jsonify(ok=True, online=online_count())

@app.route("/admin")
def admin():
    d=load()
    u=current_user(d)
    admin_ok = is_admin_user(u) or bootstrap_admin_ok(d)
    pending=[x for x in d["users"] if x.get("status")=="pending"]
    pc=[]
    for x in d["users"]:
        if x.get("status")=="approved":
            for c in x.get("chars",[]):
                if c.get("status")=="pending":
                    pc.append({"user":x,"char":c})
    admin_msg = session.pop("admin_msg", "")
    current_label = "로그인된 회원 없음"
    if u:
        current_label = f"{u.get('account')} / 권한: {role_of(u)} / 상태: {u.get('status')}"
    if bootstrap_admin_ok(d):
        current_label += " / 임시 관리자 모드"
    return render_template_string(
        ADMIN, css=CSS, admin_ok=admin_ok,
        super_ok=(is_super_user(u) or bootstrap_admin_ok(d)),
        pending_users=pending, pending_chars=pc, users=d["users"],
        posts=list(reversed(d["posts"])), notice=d["settings"].get("notice",""),
        farm_items=d["settings"].get("farm_items",FARM_ITEMS),
        admin_msg=admin_msg, current_label=current_label
    )

@app.route("/admin/login", methods=["POST"])
def admin_login():
    d=load()
    u=current_user(d)
    if request.form.get("password") != d["settings"].get("admin_password"):
        session["admin_msg"] = "관리자 비밀번호가 맞지 않습니다."
        return redirect("/admin")

    if super_count(d) == 0:
        session["legacy_admin_ok"] = True
        if approved(u):
            def fn(x):
                uu=find_user(x,u["id"])
                if uu:
                    uu["role"]="super"
            save(fn)
            session["admin_msg"] = "현재 로그인 계정이 최고관리자로 등록되었습니다."
        else:
            session["admin_msg"] = "임시 관리자 모드입니다. 먼저 가입 승인 후, 본인 계정으로 다시 로그인해서 최고관리자로 지정하세요."
        return redirect("/admin")

    if not approved(u):
        session["admin_msg"] = "관리자 권한이 있는 회원 계정으로 로그인해야 합니다."
        return redirect("/admin")
    if not is_admin_user(u):
        session["admin_msg"] = "현재 계정에는 관리자 권한이 없습니다."
        return redirect("/admin")
    session["admin_msg"] = "관리자 권한으로 접속했습니다."
    return redirect("/admin")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("legacy_admin_ok", None)
    return redirect("/")

@app.route("/admin/settings", methods=["POST"])
def admin_settings():
    d=load(); actor=current_user(d)
    if not (is_super_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    ap=request.form.get("access_password","").strip(); ad=request.form.get("admin_password","").strip()
    def fn(d):
        if ap: d["settings"]["access_password"]=ap
        if ad: d["settings"]["admin_password"]=ad
    save(fn); return redirect("/admin")

@app.route("/admin/notice", methods=["POST"])
def admin_notice():
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    save(lambda d: d["settings"].update({"notice":request.form.get("notice","").strip()[:300]})); return redirect("/admin")

@app.route("/admin/farm_items", methods=["POST"])
def admin_farm_items():
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    def parse(n): return [x.strip() for x in request.form.get(n,"").split(",") if x.strip()]
    items={"해골왕":parse("items_해골왕") or ["해뼈"],"어금니":parse("items_어금니") or ["흑룡 어금니","묵룡 어금니","진룡 어금니","감룡 어금니"]}
    save(lambda d: d["settings"].update({"farm_items":items})); return redirect("/admin")


@app.route("/admin/role/<uid>/<role>", methods=["POST"])
def admin_role(uid, role):
    d=load(); actor=current_user(d)
    if not (is_super_user(actor) or bootstrap_admin_ok(d)):
        return redirect("/admin")
    if role not in ["member","admin","super"]:
        return redirect("/admin")
    def fn(x):
        target=find_user(x, uid)
        if not target or not approved(target):
            return
        if role != "super" and target.get("role") == "super" and super_count(x) <= 1:
            session["admin_msg"] = "마지막 최고관리자는 해제할 수 없습니다."
            return
        target["role"] = role
    save(fn)
    session["admin_msg"] = "권한이 변경되었습니다."
    return redirect("/admin")

@app.route("/admin/user/<uid>/<action>", methods=["POST"])
def admin_user(uid,action):
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    def fn(d):
        u=find_user(d,uid)
        if not u: return
        if action=="approve":
            u["status"]="approved"
            u.setdefault("role","member")
            for c in u.get("chars",[]):
                if c.get("status")=="pending": c["status"]="approved"
        elif action=="reject": u["status"]="rejected"
        elif action=="toggle_block": u["blocked"]=not u.get("blocked",False)
    save(fn); return redirect("/admin")

@app.route("/admin/char/<uid>/<cid>/<action>", methods=["POST"])
def admin_char(uid,cid,action):
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    def fn(d):
        u=find_user(d,uid)
        if not u: return
        for c in u.get("chars",[]):
            if c.get("id")==cid: c["status"]="approved" if action=="approve" else "rejected"
    save(fn); return redirect("/admin")


@app.route("/admin/delete_user/<uid>", methods=["POST"])
def admin_delete_user(uid):
    d=load(); actor=current_user(d)
    if not is_super_user(actor):
        return redirect("/admin")
    def fn(x):
        target=find_user(x, uid)
        if not target:
            return
        # 마지막 최고관리자는 삭제 불가
        if target.get("role") == "super" and super_count(x) <= 1:
            session["admin_msg"] = "마지막 최고관리자는 삭제할 수 없습니다."
            return
        x["users"] = [u for u in x.get("users", []) if u.get("id") != uid]
        session["admin_msg"] = "회원이 삭제되었습니다."
    save(fn)
    return redirect("/admin")

@app.route("/admin/delete_post/<pid>", methods=["POST"])
def admin_delete_post(pid):
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    save(lambda d: d.update({"posts":[p for p in d["posts"] if p.get("id")!=pid]})); return redirect("/admin")

@app.route("/admin/clear_closed", methods=["POST"])
def admin_clear_closed():
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    save(lambda d: d.update({"posts":[p for p in d["posts"] if not (p.get("category") in ["사냥","600퀘"] and p.get("closed"))]})); return redirect("/admin")

@app.route("/admin/clear_chat", methods=["POST"])
def admin_clear_chat():
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)): return redirect("/admin")
    save(lambda d: d.update({"chat":[]})); return redirect("/admin")

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"월하 연가 연희 파티모집","short_name":"파티모집","start_url":"/","display":"standalone","background_color":"#0b1020","theme_color":"#0b1020","icons":[]})

@app.route("/sw.js")
def sw():
    return app.response_class("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());", mimetype="application/javascript")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","7777")), debug=False, threaded=True)
