
from flask import Flask, request, jsonify, render_template_string, redirect, session, send_file
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, uuid, tempfile, html, threading, re, re, re, re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v13-final-secret")

KST = ZoneInfo("Asia/Seoul")
DATA_FILE = "data.json"
APP_VERSION = "v18.3"
SITE_TITLE = "월하 · 연가 · 연희 파티모집"
SITE_DESC = "월하 · 연가 · 연희 문파 파티모집, 파밍일정, 실시간 채팅"
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
            "farm_items": FARM_ITEMS,
            "app_version": APP_VERSION,
            "schema_version": 15
        },
        "users": [],
        "posts": [],
        "chat": []
    }


def migrate_data(d):
    """기존 data.json을 유지하면서 새 버전에 필요한 필드만 자동 추가."""
    d.setdefault("settings", {})
    d["settings"].setdefault("access_password", DEFAULT_ACCESS_PASSWORD)
    d["settings"].setdefault("admin_password", DEFAULT_ADMIN_PASSWORD)
    d["settings"].setdefault("notice", "")
    d["settings"].setdefault("farm_items", FARM_ITEMS)
    d["settings"]["app_version"] = APP_VERSION
    d["settings"]["schema_version"] = 15

    d.setdefault("users", [])
    for u in d.get("users", []):
        u.setdefault("id", new_id())
        u.setdefault("account", "")
        u.setdefault("status", "pending")
        u.setdefault("role", "member")
        u.setdefault("blocked", False)
        u.setdefault("chars", [])
        for c in u.get("chars", []):
            c.setdefault("id", new_id())
            c.setdefault("name", "")
            c.setdefault("job", "")
            c.setdefault("status", "pending")

    d.setdefault("posts", [])
    for p in d.get("posts", []):
        p.setdefault("id", new_id())
        p.setdefault("owner_uid", "")
        p.setdefault("owner_label", "")
        p.setdefault("category", "사냥")
        p.setdefault("place", "")
        p.setdefault("channel", "")
        p.setdefault("start_period", "")
        p.setdefault("start_date", "")
        p.setdefault("start_time", "")
        p.setdefault("end_period", "")
        p.setdefault("end_time", "")
        p.setdefault("memo", "")
        p.setdefault("slots", [])
        p.setdefault("participants", [])
        p.setdefault("closed", False)
        p.setdefault("closed_at", "")
        p.setdefault("party_chat", [])
        p.setdefault("created", text_now())
        p.setdefault("farm_status", "진행중")
        p.setdefault("farm_result", "")
        p.setdefault("farm_item", "")
        p.setdefault("sale_amount", "")
        p.setdefault("share_ids", [])
        p.setdefault("early_ids", [])
        p.setdefault("late_ids", [])
        p.setdefault("early_weight", "1.0")
        p.setdefault("late_weight", "0.88")
        p.setdefault("schedule_alerts_sent", [])

    d.setdefault("chat", [])
    for m in d.get("chat", []):
        m.setdefault("id", new_id())
        m.setdefault("uid", "")
        m.setdefault("label", "")
        m.setdefault("text", "")
        m.setdefault("time", time_now())
        m.setdefault("created_at", iso_now())

    d.setdefault("boss_timers", [])
    for b in d.get("boss_timers", []):
        b.setdefault("id", new_id())
        b.setdefault("name", "")
        b.setdefault("spawn_at", iso_now())
        b.setdefault("memo", "")
        b.setdefault("created_by", "")
        b.setdefault("created_label", "")
        b.setdefault("created_at", iso_now())
        b.setdefault("alerts_sent", [])
    return d

def read_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return default_data()
    return migrate_data(d)

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

    d.setdefault("boss_timers", [])
    boss_keep = []
    old_cut = kst_now() - timedelta(hours=2)
    for b in d.get("boss_timers", []):
        b.setdefault("id", new_id())
        b.setdefault("name", "")
        b.setdefault("spawn_at", iso_now())
        b.setdefault("memo", "")
        b.setdefault("created_by", "")
        b.setdefault("created_label", "")
        b.setdefault("created_at", iso_now())
        b.setdefault("alerts_sent", [])
        dt = parse_dt(b.get("spawn_at"))
        if not dt or dt >= old_cut:
            boss_keep.append(b)
    d["boss_timers"] = boss_keep
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


def member_job_html(d):
    groups = {}
    ids = set(ONLINE.keys())
    for u in d.get("users", []):
        if approved(u) and u.get("id") in ids:
            c = selected_char(u)
            job = c.get("job", "기타") if c else "기타"
            groups.setdefault(job, []).append(label(c) or u.get("account"))
    if not groups:
        return "<div class='member'>현재 온라인 문파원이 없습니다.</div>"
    rows = []
    for job in sorted(groups.keys()):
        names = ", ".join(e(x) for x in groups[job])
        rows.append(f"<details class='member'><summary><b>{e(job)}</b> {len(groups[job])}명</summary><div class='meta'>{names}</div></details>")
    return "".join(rows)

def boss_time_left_text(spawn_at):
    dt = parse_dt(spawn_at)
    if not dt:
        return "시간 오류"
    sec = int((dt - kst_now()).total_seconds())
    if sec <= 0:
        return "젠 시간"
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def boss_timers_html(d, admin_ok=False):
    now = kst_now()
    timers = sorted(d.get("boss_timers", []), key=lambda x: parse_dt(x.get("spawn_at")) or now + timedelta(days=365))
    cards = []
    for idx, b in enumerate(timers):
        bid = e(b.get("id"))
        dt = parse_dt(b.get("spawn_at"))
        time_text = dt.strftime("%m/%d %H:%M") if dt else e(b.get("spawn_at"))
        left = boss_time_left_text(b.get("spawn_at"))
        soon = " next-boss" if idx == 0 else ""
        memo = f"<div class='boss-memo'>📝 {e(b.get('memo'))}</div>" if b.get("memo") else ""
        delete_btn = f"""<form method='post' action='/boss/delete/{bid}' onsubmit="return confirm('보스 젠타임을 삭제할까요?')"><button class='mini danger'>삭제</button></form>""" if admin_ok else ""
        cards.append(f"""
        <div class='boss-card boss-timer{soon}' data-boss-id='{bid}' data-boss-name='{e(b.get('name'))}' data-spawn-at='{e(b.get('spawn_at'))}'>
          <div class='boss-left-box'>
            <div class='boss-title'>🔥 {e(b.get('name'))}</div>
            <div class='boss-time'>⏰ {time_text}</div>
            {memo}
          </div>
          <div class='boss-right-box'>
            <div class='boss-left-label'>남은시간</div>
            <div class='boss-left boss-count'>{left}</div>
            {delete_btn}
          </div>
        </div>
        """)
    if not cards:
        cards.append("<div class='empty-box'>등록된 보스 젠타임 없음</div>")
    form = ""
    test_buttons = ""
    if admin_ok:
        form = """
        <form method='post' action='/boss/add' class='boss-form better'>
          <div><label>보스명</label><input name='name' placeholder='해골왕' required></div>
          <div><label>젠시간</label><input name='spawn_at' type='datetime-local' required></div>
          <div><label>메모</label><input name='memo' placeholder='예: 1굴 / 준비물'></div>
          <button class='ok'>등록</button>
        </form>
        """
        test_buttons = """
        <div class='boss-test-row'>
          <button class='mini' onclick="testBossAlert('30분')">30분 테스트</button>
          <button class='mini' onclick="testBossAlert('15분')">15분 테스트</button>
          <button class='mini' onclick="testBossAlert('5분')">5분 테스트</button>
        </div>
        """
    return f"""
    <div class='mini-board boss-board'>
      <div class='board-head'><h2>⏰ 보스 젠타임</h2><span>가까운 젠 자동정렬</span></div>
      <div class='mini-note'>30분 전 / 15분 전 / 5분 전 알림</div>
      {form}
      {test_buttons}
      <div class='boss-list'>{''.join(cards)}</div>
    </div>
    """

def member_summary_html(d):
    ids = set(ONLINE.keys())
    online_users = [u for u in d.get("users", []) if approved(u) and u.get("id") in ids]
    total = len(online_users)
    jobs = {}
    names = []
    for u in online_users:
        c = selected_char(u)
        if c:
            jobs[c.get("job","기타")] = jobs.get(c.get("job","기타"), 0) + 1
            names.append(label(c))
        else:
            jobs["기타"] = jobs.get("기타", 0) + 1
            names.append(u.get("account"))
    job_badges = "".join(f"<span class='job-chip'>{e(k)} {v}</span>" for k,v in sorted(jobs.items())) or "<span class='job-chip'>온라인 없음</span>"
    names_text = ", ".join(e(x) for x in names[:8])
    if len(names) > 8:
        names_text += f" 외 {len(names)-8}명"
    return f"""
    <section class='online-compact'>
      <div class='online-main'>
        <span class='dot'></span>
        <div><b>문파원 접속</b><p>{total}명 온라인</p></div>
      </div>
      <div class='job-chips'>{job_badges}</div>
      <details class='online-detail'><summary>접속자 보기</summary><div class='meta'>{names_text or '현재 온라인 없음'}</div></details>
    </section>
    """




def post_start_dt(p):
    time_text = (p.get("start_time") or "").strip()
    if not time_text:
        return None
    date_value = (p.get("start_date") or today_date()).strip()
    try:
        return datetime.fromisoformat(f"{date_value}T{time_text}").replace(tzinfo=KST)
    except Exception:
        return None


def schedule_time_left_text(dt):
    if not dt:
        return "시간 미정"
    sec = int((dt - kst_now()).total_seconds())
    if sec <= 0:
        return "출발 시간"
    h = sec // 3600
    m = (sec % 3600) // 60
    return f"{h:02d}:{m:02d}"

def today_schedule_html(d):
    items = []
    now = kst_now()
    for p in d.get("posts", []):
        if p.get("category") != "파밍":
            continue
        if status_text(p) in ["마감", "정산완료"]:
            continue
        dt = post_start_dt(p)
        if not dt or dt < now - timedelta(hours=2) or dt > now + timedelta(hours=24):
            continue
        title = p.get("place") or p.get("category")
        items.append((dt, p, title))
    items.sort(key=lambda x: x[0])
    rows = []
    for dt, p, title in items[:8]:
        rows.append(f"""
        <div class='schedule-row post-schedule' data-post-id='{e(p.get('id'))}' data-post-title='{e(title)}' data-start-at='{e(dt.isoformat(timespec='seconds'))}'>
          <div><b>{e(title)}</b><span>{e(p.get('category'))} · {dt.strftime('%H:%M')}</span></div>
          <strong class='schedule-left'>{schedule_time_left_text(dt)}</strong>
        </div>
        """)
    if not rows:
        rows.append("<div class='empty-box small'>오늘 등록된 일정 없음</div>")
    return f"""
    <div class='mini-board schedule-board'>
      <div class='board-head'><h2>📅 오늘 일정</h2><span>자동 알림</span></div>
      <div class='mini-note'>파밍 출발시간 기준 30분 · 15분 · 5분 전 알림</div>
      <div class='schedule-list'>{''.join(rows)}</div>
    </div>
    """

def member_summary_html(d):
    ids = set(ONLINE.keys())
    online_users = [u for u in d.get("users", []) if approved(u) and u.get("id") in ids]
    total = len(online_users)
    jobs = {}
    names_by_job = {}
    for u in online_users:
        c = selected_char(u)
        job = c.get("job","기타") if c else "기타"
        nm = label(c) if c else u.get("account")
        jobs[job] = jobs.get(job, 0) + 1
        names_by_job.setdefault(job, []).append(nm)
    job_badges = "".join(f"<span class='job-chip'>{e(k)} {v}</span>" for k,v in sorted(jobs.items())) or "<span class='job-chip'>온라인 없음</span>"
    detail_rows = ""
    for job, names in sorted(names_by_job.items()):
        detail_rows += f"<div><b>{e(job)}</b> · {', '.join(e(n) for n in names)}</div>"
    return f"""
    <section class='online-compact slim-online'>
      <div class='online-main'>
        <span class='dot'></span>
        <div><b>문파원 접속</b><p>{total}명 온라인</p></div>
      </div>
      <div class='job-chips'>{job_badges}</div>
      <details class='online-detail'><summary>접속자 보기</summary><div class='meta'>{detail_rows or '현재 온라인 없음'}</div></details>
    </section>
    """

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


def chat_html(d):
    return chat_rows(d.get("chat", []), current_uid(), allow_delete=True)


def normalize_time_input(value):
    raw = (value or "").strip().replace("：", ":")
    s = re.sub(r"[^0-9:]", "", raw)
    if not s:
        return ""
    try:
        if ":" in s:
            hh, mm = s.split(":", 1)
            h = int(hh)
            m = int((mm + "00")[:2])
        elif len(s) <= 2:
            h = int(s); m = 0
        elif len(s) == 3:
            h = int(s[0]); m = int(s[1:3])
        else:
            h = int(s[:2]); m = int(s[2:4])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return ""
        return f"{h:02d}:{m:02d}"
    except Exception:
        return ""

def period_time_to_24(period, value):
    t = normalize_time_input(value)
    if not t:
        return ""
    h, m = map(int, t.split(":"))
    p = (period or "").strip()
    if p == "오후" and h < 12:
        h += 12
    elif p == "오전" and h == 12:
        h = 0
    return f"{h:02d}:{m:02d}"

def split_time12_from_24(value):
    t = normalize_time_input(value)
    if not t:
        return ("오전", "")
    h, m = map(int, t.split(":"))
    period = "오후" if h >= 12 else "오전"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return (period, f"{h12:02d}:{m:02d}")

def display_period_time(value):
    period, t = split_time12_from_24(value)
    return f"{period} {t}" if t else ""

def today_date():
    return kst_now().strftime("%Y-%m-%d")

def display_date(value):
    v = (value or "").strip()
    return v if v else today_date()


def post_time(p):
    d = display_date(p.get("start_date"))
    s = display_period_time(p.get("start_time"))
    t = display_period_time(p.get("end_time"))
    if s and t:
        return f"{d} · {s} ~ {t}"
    if s:
        return f"{d} · {s}"
    return f"{d} · 시간 미정"


def match_post_query(p, q):
    q = (q or "").strip().lower()
    if not q:
        return True
    texts = [
        p.get("owner_label",""), p.get("category",""), p.get("place",""),
        p.get("channel",""), p.get("memo","")
    ]
    for s in p.get("slots", []):
        texts += [s.get("job",""), s.get("label",""), s.get("external","")]
    for a in p.get("participants", []):
        texts.append(a.get("label",""))
    return q in " ".join(str(x).lower() for x in texts)

def sort_posts_for_view(posts):
    def key(p):
        st = status_text(p)
        closed = 1 if st in ["마감","정산완료"] else 0
        return (closed,)
    return sorted(posts, key=key)

def farming_stats_html(posts):
    farms = [p for p in posts if p.get("category") == "파밍"]
    total = len(farms)
    drops = sum(1 for p in farms if p.get("farm_result") == "득템")
    amount = 0
    for p in farms:
        try:
            amount += int(p.get("sale_amount") or 0)
        except Exception:
            pass
    return f"""
    <div class='mini-board farm-board compact-stat'>
      <div class='board-head'><h2>📊 파밍</h2><span>누적</span></div>
      <div class='tiny-stats'>
        <div><b>{total}</b><span>파밍</span></div>
        <div><b>{drops}</b><span>득템</span></div>
        <div><b>{amount_text(amount)}</b><span>판매</span></div>
      </div>
    </div>
    """


def joined_count(p):
    if p.get("category") == "사냥":
        return sum(1 for s in p.get("slots", []) if s.get("uid") or s.get("user_id") or s.get("char_id") or s.get("external"))
    return len(p.get("participants", []))

def max_count(p):
    if p.get("category") == "사냥":
        return max(1, len(p.get("slots", [])))
    if p.get("category") == "600퀘":
        return 10
    return max(1, len(p.get("participants", [])) or 0)

def render_posts(posts, u, farm_items, admin=False):
    out = []
    uid = u.get("id") if u else ""
    for p in posts:
        cat = p.get("category","")
        pid = p.get("id","")
        closed = status_text(p) in ["마감", "정산완료"] or p.get("closed")
        classes = "party-card closed-card" if closed else "party-card"
        out.append(f"<div class='{classes}'>")
        out.append("<div class='tags'>")
        out.append(f"<span class='tag ok'>{e(status_text(p))}</span>")
        out.append(f"<span class='tag'>{e(cat)}</span>")
        out.append(f"<span class='count-badge'>{joined_count(p)}/{max_count(p)}</span>")
        out.append("</div>")
        out.append(f"<h2>{e(p.get('place',''))}</h2>")
        out.append(f"<div class='meta'>📍 채널 {e(p.get('channel',''))} · ⏰ {e(post_time(p))}</div>")
        out.append(f"<div class='meta'>👑 {e(p.get('owner_label',''))} · {e(p.get('created',''))}</div>")
        if p.get("memo"):
            out.append(f"<div class='memo'>{e(p.get('memo'))}</div>")

        if cat == "사냥":
            slots = p.get("slots", [])
            for i, s in enumerate(slots):
                occupied = s.get("uid") or s.get("user_id") or s.get("char_id") or s.get("external")
                nm = s.get("label") or s.get("name") or s.get("external") or ""
                mine = (s.get("uid") == uid) or (s.get("user_id") == uid)
                out.append("<div class='slot'>")
                out.append(f"<div><b>{e(s.get('job',''))}</b><br>")
                if occupied:
                    out.append(f"<span class='ok-dot'></span> {e(nm)}")
                else:
                    out.append("<span class='empty-dot'></span> 모집중")
                out.append("</div><div class='slot-actions'>")
                if not closed:
                    if mine:
                        out.append(f"<a class='mini gray' href='/leave_slot/{e(pid)}/{i}'>취소</a>")
                    elif not occupied:
                        out.append(f"<a class='mini ok' href='/join_slot/{e(pid)}/{i}'>참여</a>")
                    if admin:
                        out.append(f"<a class='mini gray' href='/external_slot/{e(pid)}/{i}'>외부인</a>")
                out.append("</div></div>")
        else:
            out.append("<h3>참여자</h3>")
            parts = p.get("participants", [])
            if parts:
                out.append("<div class='participants'>")
                for part in parts:
                    nm = part.get("label") or part.get("name") or part.get("external") or ""
                    out.append(f"<span class='pill'>{e(nm)}</span>")
                out.append("</div>")
            else:
                out.append("<p class='meta'>아직 참여자가 없습니다.</p>")
            if not closed:
                out.append(f"<a class='big ok' href='/participate/{e(pid)}'>참여하기</a>")
                if admin:
                    out.append(f"<a class='big gray' href='/manual_participant/{e(pid)}'>수동 참여자 추가</a>")

        # 파밍 결과/정산 영역 유지
        if cat == "파밍":
            out.append("<div class='farm-box'>")
            out.append("<h3>파밍 결과</h3>")
            if admin or p.get("owner_uid") == uid:
                out.append(f"<form method='post' action='/farm_result/{e(pid)}'>")
                out.append("<select name='farm_result'>")
                for r in ["노득","득템"]:
                    sel = "selected" if p.get("farm_result")==r else ""
                    out.append(f"<option {sel}>{r}</option>")
                out.append("</select>")
                out.append(f"<select name='farm_item'>")
                for it in farm_items:
                    sel = "selected" if p.get("farm_item")==it else ""
                    out.append(f"<option {sel}>{e(it)}</option>")
                out.append("</select>")
                out.append(f"<input name='sale_amount' placeholder='판매금액' value='{e(p.get('sale_amount',''))}'>")
                out.append("<button class='mini ok'>결과/분배 저장</button>")
                out.append("</form>")
            else:
                out.append(f"<div class='meta'>{e(p.get('farm_result',''))} {e(p.get('farm_item',''))} {e(p.get('sale_amount',''))}</div>")
            out.append("</div>")

        out.append("<div class='actions'>")
        out.append(f"<a class='btn' href='/copy/{e(pid)}'>복사</a>")
        out.append(f"<a class='btn' href='/share/{e(pid)}'>카톡공유</a>")
        out.append(f"<a class='btn' href='/chat/{e(pid)}'>채팅 {len(p.get('party_chat', []))}</a>")
        if (p.get("owner_uid") == uid) or admin:
            out.append(f"<a class='btn ok' href='/close/{e(pid)}'>모집완료</a>")
            out.append(f"<a class='btn gray' href='/edit/{e(pid)}'>수정</a>")
            out.append(f"<a class='btn danger' href='/delete/{e(pid)}'>삭제</a>")
        out.append("</div>")
        out.append("</div>")
    return "".join(out) if out else "<div class='empty-box'>현재 모집글이 없습니다.</div>"

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
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form={"account":"","char_name":"","job":"검성"}, error="", site_title=SITE_TITLE, site_desc=SITE_DESC)
    form = {"account": request.form.get("account","").strip(), "char_name": request.form.get("char_name","").strip(), "job": request.form.get("job","검성")}
    if not form["account"] or not form["char_name"]:
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form=form, error="계정명과 캐릭터명을 입력해주세요.", site_title=SITE_TITLE, site_desc=SITE_DESC)
    if form["char_name"].lower() in all_char_names(d):
        return render_template_string(REGISTER, css=CSS, jobs=JOBS, form=form, error="이미 등록된 캐릭터명입니다.", site_title=SITE_TITLE, site_desc=SITE_DESC)
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
    all_posts = list(reversed(d["posts"]))
    posts = all_posts
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    posts = sort_posts_for_view(posts)
    open_count = sum(1 for p in posts if status_text(p) in ["모집중","진행중"])
    return render_template_string(MAIN, css=CSS, page="home", user=u, cats=CATEGORIES, cats_no_all=CATEGORIES[1:], filter_value=filt, post_list=render_posts(posts,u,d["settings"].get("farm_items", FARM_ITEMS), admin=is_admin_user(u)), global_chat=chat_html(d), open_count=open_count, member_html=member_html(d), member_job_html=member_job_html(d), member_summary=member_summary_html(d), schedule_html=today_schedule_html(d), farm_stats=farming_stats_html(all_posts), notice=d["settings"].get("notice",""), jobs=JOBS, places=PLACES, app_version=APP_VERSION, site_title=SITE_TITLE, site_desc=SITE_DESC)



def _join_hunting_slot(pid, idx):
    d = load()
    u = current_user(d)
    if not approved(u):
        return redirect("/")
    c = selected_char(u)
    if not c:
        return redirect("/chars")
    try:
        idx = int(idx)
    except Exception:
        return redirect("/")
    def fn(x):
        p = find_post(x, pid)
        if not p or p.get("category") != "사냥":
            return
        slots = p.get("slots", [])
        if idx < 0 or idx >= len(slots):
            return
        # 한 캐릭터는 사냥 글 안에서 한 자리만 참여
        for s in slots:
            if s.get("uid") == u.get("id") or s.get("user_id") == u.get("id") or s.get("char_id") == c.get("id"):
                s["uid"] = ""
                s["user_id"] = ""
                s["char_id"] = ""
                s["label"] = ""
                s["name"] = ""
                s["external"] = ""
                s["status"] = "모집중"
        s = slots[idx]
        if not (s.get("uid") or s.get("user_id") or s.get("char_id") or s.get("external")):
            s["uid"] = u.get("id")
            s["user_id"] = u.get("id")
            s["char_id"] = c.get("id")
            s["label"] = label(c)
            s["name"] = label(c)
            s["status"] = "참여"
    save(fn)
    return redirect("/")

@app.route("/join_slot/<pid>/<idx>")
def join_slot(pid, idx):
    return _join_hunting_slot(pid, idx)

@app.route("/slot_join/<pid>/<idx>")
def slot_join(pid, idx):
    return _join_hunting_slot(pid, idx)

@app.route("/join/<pid>/<idx>")
def join_pid_idx(pid, idx):
    return _join_hunting_slot(pid, idx)

@app.route("/leave_slot/<pid>/<idx>")
def leave_slot(pid, idx):
    d = load()
    u = current_user(d)
    c = selected_char(u) if u else None
    try:
        idx = int(idx)
    except Exception:
        return redirect("/")
    def fn(x):
        p = find_post(x, pid)
        if not p or p.get("category") != "사냥":
            return
        slots = p.get("slots", [])
        if idx < 0 or idx >= len(slots):
            return
        s = slots[idx]
        if s.get("uid") == u.get("id") or s.get("user_id") == u.get("id") or (c and s.get("char_id") == c.get("id")):
            s["uid"] = ""
            s["user_id"] = ""
            s["char_id"] = ""
            s["label"] = ""
            s["name"] = ""
            s["external"] = ""
            s["status"] = "모집중"
    save(fn)
    return redirect("/")

@app.route("/api/posts")
def api_posts():
    d = load()
    u = current_user(d)
    filt = request.args.get("filter","전체")
    posts = list(reversed(d["posts"]))
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    posts = sort_posts_for_view(posts)
    return render_posts(posts,u,d["settings"].get("farm_items", FARM_ITEMS), admin=is_admin_user(u))


@app.route("/new")
def new():
    d=load()
    u=current_user(d)
    if not approved(u):
        return redirect("/")
    return render_template_string(
        NEW,
        css=CSS,
        user=u,
        jobs=JOBS,
        places=PLACES,
        cats_no_all=CATEGORIES[1:],
        today=today_date(),
        app_version=APP_VERSION,
        site_title=SITE_TITLE,
        site_desc=SITE_DESC
    )

@app.route("/create", methods=["POST"])
def create():
    d=load()
    u=current_user(d)
    if not approved(u):
        return redirect("/")
    c=selected_char(u)
    if not c:
        return redirect("/")
    cat = request.form.get("category","사냥")
    if cat == "파밍" and not is_admin_user(u):
        return redirect("/")
    fixed_start_time = period_time_to_24(request.form.get("start_period",""), request.form.get("start_time",""))
    fixed_end_time = period_time_to_24(request.form.get("end_period",""), request.form.get("end_time",""))
    start_date = request.form.get("start_date","").strip() or today_date()
    slots = []
    if cat == "사냥":
        for i in range(10):
            job = request.form.get(f"slot_job_{i}","")
            if job:
                slots.append({"job":job,"uid":"","user_id":"","char_id":"","label":"","name":"","external":"","status":"모집중"})
    p = {
        "id": new_id(),
        "owner_uid": u["id"],
        "owner_label": label(c),
        "category": cat,
        "place": request.form.get(f"place_{cat}",""),
        "channel": digits(request.form.get("channel"),4),
        "start_date": start_date,
        "start_period": request.form.get("start_period",""),
        "start_time": fixed_start_time,
        "end_period": request.form.get("end_period",""),
        "end_time": fixed_end_time,
        "memo": request.form.get("memo","").strip(),
        "slots": slots,
        "participants": [],
        "closed": False,
        "closed_at": "",
        "party_chat": [],
        "created": text_now(),
        "farm_status": "진행중",
        "farm_result": "",
        "farm_item": "",
        "sale_amount": "",
        "share_ids": [],
        "early_ids": [],
        "late_ids": [],
        "early_weight": "1.0",
        "late_weight": "0.88",
        "schedule_alerts_sent": []
    }
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
        sp, st = split_time12_from_24(p.get("start_time"))
        ep, et = split_time12_from_24(p.get("end_time"))
        return render_template_string(
            MAIN,
            css=CSS,
            page="edit",
            post=p,
            user=u,
            chars=chars(u),
            cats_no_all=["사냥","600퀘","파밍"] if is_admin_user(u) else ["사냥","600퀘"],
            jobs=JOBS,
            places=PLACES,
            notice="",
            start_period=sp,
            start_time=st,
            end_period=ep,
            end_time=et,
            today=today_date(),
            app_version=APP_VERSION,
            site_title=SITE_TITLE,
            site_desc=SITE_DESC
        )
    def fn(x):
        pp = find_post(x, pid)
        if pp and pp.get("owner_uid") == u.get("id"):
            pp["channel"] = digits(request.form.get("channel"),4)
            pp["start_date"] = request.form.get("start_date","").strip() or today_date()
            pp["start_period"] = request.form.get("start_period","")
            pp["start_time"] = period_time_to_24(request.form.get("start_period",""), request.form.get("start_time",""))
            pp["end_period"] = request.form.get("end_period","")
            pp["end_time"] = period_time_to_24(request.form.get("end_period",""), request.form.get("end_time",""))
            pp["memo"] = request.form.get("memo","").strip()
    save(fn)
    return redirect("/")

@app.route("/chars")
def chars_page():
    d=load(); u=current_user(d)
    return render_template_string(MAIN, css=CSS, page="chars", user=u, jobs=JOBS, places=PLACES, cats_no_all=CATEGORIES[1:], notice="", app_version=APP_VERSION, site_title=SITE_TITLE, site_desc=SITE_DESC)

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
        posts.append({"id":p.get("id"),"owner":owner,"category":p.get("category"),"place":p.get("place"),"participant_count":len(participants),"participants_key":"|".join(participants),"chat_count":len(p.get("party_chat", [])),"status":status_text(p)})
    return jsonify({
        "ok": True,
        "now": iso_now(),
        "chat_count": len(d.get("chat", [])),
        "chat_last_id": d.get("chat", [{}])[-1].get("id", "") if d.get("chat") else "",
        "chat_last_text": d.get("chat", [{}])[-1].get("text", "") if d.get("chat") else "",
        "chat_last_label": d.get("chat", [{}])[-1].get("label", "") if d.get("chat") else "",
        "chat_last_uid": d.get("chat", [{}])[-1].get("uid", "") if d.get("chat") else "",
        "posts": posts,
        "boss_timers": [{"id": b.get("id"), "name": b.get("name"), "spawn_at": b.get("spawn_at"), "alerts_sent": b.get("alerts_sent", [])} for b in d.get("boss_timers", [])]
    })

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    touch(); return jsonify(ok=True, online=online_count())


@app.route("/boss/add", methods=["POST"])
def boss_add():
    d=load(); u=current_user(d)
    if not is_admin_user(u):
        return redirect("/")
    name = request.form.get("name","").strip()[:30]
    spawn_value = request.form.get("spawn_at","").strip()
    memo = request.form.get("memo","").strip()[:80]
    if not name or not spawn_value:
        return redirect("/")
    try:
        dt = datetime.fromisoformat(spawn_value).replace(tzinfo=KST)
    except Exception:
        return redirect("/")
    ch = selected_char(u)
    timer = {"id":new_id(),"name":name,"spawn_at":dt.isoformat(timespec="seconds"),"memo":memo,"created_by":u.get("id"),"created_label":label(ch) or u.get("account"),"created_at":iso_now(),"alerts_sent":[]}
    save(lambda x: x.setdefault("boss_timers", []).append(timer))
    return redirect("/")

@app.route("/boss/delete/<bid>", methods=["POST"])
def boss_delete(bid):
    d=load(); u=current_user(d)
    if not is_admin_user(u):
        return redirect("/")
    save(lambda x: x.update({"boss_timers": [b for b in x.get("boss_timers", []) if b.get("id") != bid]}))
    return redirect("/")

@app.route("/api/boss/mark_alert", methods=["POST"])
def boss_mark_alert():
    r=request.get_json(force=True)
    bid = r.get("id")
    mark = r.get("mark")
    if mark not in ["30", "15", "5"]:
        return jsonify(ok=False)
    def fn(x):
        for b in x.get("boss_timers", []):
            if b.get("id") == bid:
                b.setdefault("alerts_sent", [])
                if mark not in b["alerts_sent"]:
                    b["alerts_sent"].append(mark)
                    text = f"[보스알림] {b.get('name')} 젠 {'30분 전' if mark=='30' else '15분 전' if mark=='15' else '5분 전'}"
                    x.setdefault("chat", []).append({"id":new_id(),"uid":"system","label":"보스알림","text":text,"time":time_now(),"created_at":iso_now()})
                return
    save(fn)
    return jsonify(ok=True)


ADMIN = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>{{ site_title|default('월하 · 연가 · 연희 파티모집') }} 관리자</title><style>{{ css }}</style></head><body>
<div class='wrap'>
<header class='header'><h1>🛠 관리자</h1><div class='sub'>{{ app_version }}</div></header>
<section class='panel'>
<a class='btn gray' href='/'>← 메인</a>
<h2>가입 승인</h2>
{% if pending_users %}
  {% for u in pending_users %}
  <div class='slot'><div><b>{{ u.account }}</b><br><span class='meta'>{{ u.chars[0].name if u.chars else '' }} / {{ u.chars[0].job if u.chars else '' }}</span></div>
  <div><a class='mini ok' href='/admin/approve_user/{{ u.id }}'>승인</a></div></div>
  {% endfor %}
{% else %}<p class='meta'>대기 없음</p>{% endif %}
</section>

<section class='panel'>
<h2>캐릭터 승인</h2>
{% if pending_chars %}
  {% for item in pending_chars %}
  <div class='slot'><div><b>{{ item.char.name }}</b><br><span class='meta'>{{ item.char.job }} / {{ item.user.account }}</span></div>
  <div><a class='mini ok' href='/admin/approve_char/{{ item.user.id }}/{{ item.char.id }}'>승인</a></div></div>
  {% endfor %}
{% else %}<p class='meta'>대기 없음</p>{% endif %}
</section>

<section class='panel'>
<h2>권한 관리</h2>
{% for u in users %}
  <div class='slot'>
    <div><b>{{ u.account }}</b><br><span class='meta'>권한: {{ u.role|default('일반') }} · {{ u.status|default('') }}</span></div>
    <div>
      <a class='mini gray' href='/admin/role/{{ u.id }}/normal'>일반</a>
      <a class='mini ok' href='/admin/role/{{ u.id }}/admin'>관리자</a>
      <a class='mini' href='/admin/role/{{ u.id }}/super'>최고관리자</a>
    </div>
  </div>
{% endfor %}
</section>
</div></body></html>"""

@app.route("/admin")
def admin():
    d = load()
    u = current_user(d)
    if not is_admin_user(u):
        return redirect("/")
    pending_users = [x for x in d.get("users", []) if x.get("status") == "pending"]
    pending_chars = []
    for user in d.get("users", []):
        for ch in user.get("chars", []):
            if ch.get("status") == "pending":
                pending_chars.append({"user": user, "char": ch})
    return render_template_string(
        ADMIN,
        css=CSS,
        users=d.get("users", []),
        pending_users=pending_users,
        pending_chars=pending_chars,
        admin_ok=True,
        app_version=APP_VERSION,
        site_title=SITE_TITLE if "SITE_TITLE" in globals() else "월하 · 연가 · 연희 파티모집",
        site_desc=SITE_DESC if "SITE_DESC" in globals() else "월하 · 연가 · 연희 문파 파티모집"
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




@app.route("/admin/approve_user/<uid>")
def admin_approve_user(uid):
    u = current_user(load())
    if not is_admin_user(u):
        return redirect("/")
    def fn(d):
        for x in d.get("users", []):
            if x.get("id") == uid:
                x["status"] = "approved"
                for ch in x.get("chars", []):
                    if ch.get("status") == "pending":
                        ch["status"] = "approved"
    save(fn)
    return redirect("/admin")

@app.route("/admin/approve_char/<uid>/<cid>")
def admin_approve_char(uid, cid):
    u = current_user(load())
    if not is_admin_user(u):
        return redirect("/")
    def fn(d):
        for x in d.get("users", []):
            if x.get("id") == uid:
                for ch in x.get("chars", []):
                    if ch.get("id") == cid:
                        ch["status"] = "approved"
    save(fn)
    return redirect("/admin")

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



@app.route("/admin/backup")
def admin_backup():
    d=load(); actor=current_user(d)
    if not (is_admin_user(actor) or bootstrap_admin_ok(d)):
        return redirect("/admin")
    if not os.path.exists(DATA_FILE):
        write_data(d)
    filename = f"baram_party_backup_{kst_now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(DATA_FILE, as_attachment=True, download_name=filename, mimetype="application/json")

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



@app.route("/external_slot/<pid>/<idx>", methods=["GET","POST"])
def external_slot(pid, idx):
    d = load()
    u = current_user(d)
    if not is_admin_user(u):
        return redirect("/")
    try:
        idx = int(idx)
    except Exception:
        return redirect("/")
    if request.method == "GET":
        return """<form method='post'><input name='name' placeholder='외부인 이름'><button>저장</button></form>"""
    name = request.form.get("name","").strip()
    def fn(x):
        p = find_post(x, pid)
        if not p or p.get("category") != "사냥":
            return
        slots = p.get("slots", [])
        if 0 <= idx < len(slots):
            s = slots[idx]
            s["uid"] = ""; s["user_id"] = ""; s["char_id"] = ""
            s["label"] = name; s["name"] = name; s["external"] = name; s["status"] = "참여"
    save(fn)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","7777")), debug=False, threaded=True)
