
from flask import Flask, request, jsonify, render_template_string, redirect, session, send_file
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os, json, uuid, tempfile, html, threading

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v13-final-secret")

KST = ZoneInfo("Asia/Seoul")
DATA_FILE = "data.json"
APP_VERSION = "v16.0"
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
    date_text = (p.get("start_period") or "").strip()
    today = kst_now().strftime("%Y-%m-%d")
    date_value = date_text if re.match(r"^\d{4}-\d{2}-\d{2}$", date_text) else today
    try:
        dt = datetime.fromisoformat(f"{date_value}T{time_text}").replace(tzinfo=KST)
        if dt < kst_now() - timedelta(hours=2):
            dt = dt + timedelta(days=1)
        return dt
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
        if p.get("category") not in ["파밍", "600퀘"]:
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
      <div class='mini-note'>파밍/600퀘 출발시간 기준 30분 · 15분 · 5분 전 알림</div>
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

def post_time(p):
    s = (p.get("start_period","") + " " + p.get("start_time","")).strip()
    t = (p.get("end_period","") + " " + p.get("end_time","")).strip()
    if s and t:
        return f"{s} ~ {t}"
    return s or t or "시간 미정"


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
        <article class='party-card post {"closed-card" if st in ["마감","정산완료"] else ""}' data-post-id='{pid}' data-owner='{"1" if owner else "0"}' data-participants='{e(data_part)}'>
          <div class='post-head'><div><span class='pill {"done big-done" if st in ["마감","정산완료"] else "open"}'>{e(st)}</span><span class='pill type'>{e(cat)}</span></div><b class='count'>{cnt_text}</b></div>
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
*{box-sizing:border-box}body{margin:0;color:#eef2ff;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic',Arial,sans-serif;background:#0b1020}body:before{content:'';position:fixed;inset:0;background:radial-gradient(circle at 20% 0%,#263c77 0,#111a34 38%,#090d18 78%);z-index:-1}.wrap{max-width:1040px;margin:0 auto;padding:18px 14px 100px}.header{padding:12px 0 16px;border-bottom:1px solid rgba(255,255,255,.11)}h1{font-size:28px;margin:0}.sub{color:#aeb8d7;font-size:13px;margin-top:4px}.panel,.party-card{background:rgba(20,27,48,.88);border:1px solid rgba(150,165,210,.22);box-shadow:0 18px 50px rgba(0,0,0,.32);border-radius:24px;padding:16px;margin:14px 0}.top-actions{display:flex;gap:8px;flex-wrap:wrap}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.stat{background:rgba(7,11,22,.57);border:1px solid rgba(255,255,255,.10);border-radius:18px;text-align:center;padding:14px 8px}.stat b{font-size:28px;display:block}.stat span{font-size:12px;color:#aeb8d7}button,.btn{border:0;border-radius:15px;background:linear-gradient(180deg,#6a86ff,#4163ff);color:#fff;font-weight:900;padding:12px 15px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;min-height:44px;cursor:pointer}button.gray,.btn.gray{background:linear-gradient(180deg,#4c5571,#363d55)}button.danger,.danger{background:linear-gradient(180deg,#ff6666,#ce4040)}button.ok{background:linear-gradient(180deg,#2bd176,#169851)}input,select,textarea{width:100%;background:#0d1325;color:#f4f6ff;border:1px solid rgba(170,185,230,.25);border-radius:15px;padding:13px;margin:6px 0 13px;font-size:16px}label{font-size:13px;color:#bac4de;font-weight:900}.tabs{display:flex;gap:8px;overflow-x:auto;padding:4px 0}.tabs a{white-space:nowrap;color:#dce4ff;background:rgba(10,15,30,.55);border:1px solid rgba(255,255,255,.12);text-decoration:none;border-radius:999px;padding:9px 14px;font-weight:900;font-size:14px}.tabs a.on{background:linear-gradient(180deg,#6a86ff,#4163ff)}.empty{border:1px dashed rgba(255,255,255,.25);border-radius:22px;padding:46px;text-align:center;color:#c2c9dd}.post-head{display:flex;justify-content:space-between;align-items:center}.pill{display:inline-flex;border-radius:999px;padding:6px 10px;font-weight:900;font-size:12px;margin-right:4px}.pill.open{background:#123f2a;color:#9dffc4}.pill.done{background:#4d2020;color:#ffd1d1}.pill.big-done{font-size:16px;padding:10px 18px;background:linear-gradient(180deg,#777,#444);color:#fff;border:2px solid rgba(255,255,255,.25);box-shadow:0 0 0 2px rgba(0,0,0,.15) inset}.closed-card{background:rgba(54,58,70,.82)!important;border-color:rgba(190,195,210,.18)!important;filter:grayscale(.45);opacity:.78}.closed-card h2,.closed-card .meta,.closed-card .memo{color:#c8ccd8!important}.closed-card .slot{background:rgba(40,43,52,.72)!important;border-color:rgba(210,210,220,.13)!important}.closed-card .slot.filled{background:rgba(44,52,45,.66)!important}.closed-card .count{background:#3a3d48;color:#e0e0e0}.closed-card:before{content:'마감';display:block;text-align:center;font-weight:900;font-size:18px;letter-spacing:4px;color:#fff;background:linear-gradient(90deg,#555,#777,#555);border-radius:16px;padding:8px;margin-bottom:10px}.pill.type{background:#242c48;color:#ccd6ff}.count{font-size:18px;background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:7px 12px}h2{font-size:24px;margin:12px 0 5px}.meta{color:#b5bfd9;font-size:14px;line-height:1.6}.memo{color:#ffd16a;font-size:14px;margin-top:5px}.left-time{color:#ffb3b3;font-size:13px;font-weight:900}.slot{display:flex;justify-content:space-between;align-items:center;background:rgba(8,12,24,.62);border:1px solid rgba(255,255,255,.12);border-radius:17px;padding:12px;margin:9px 0}.slot.filled{background:rgba(18,55,33,.58);border-color:rgba(73,190,112,.35)}.actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(86px,1fr));gap:8px;margin-top:12px}.simple-action{grid-template-columns:1fr}.owner-only{display:none!important}.post[data-owner='1'] .owner-only{display:inline-flex!important}.hidden{display:none!important}.time-row{display:grid;grid-template-columns:90px 1fr;gap:8px}.quick{display:grid;grid-template-columns:1fr auto;gap:8px}.farm-stats .summary{margin-top:8px}.post{scroll-margin-top:16px}.mini{font-size:13px;padding:8px 10px;min-height:34px}.notice,.alarm-guide{background:linear-gradient(180deg,rgba(255,211,106,.18),rgba(255,211,106,.08));border:1px solid rgba(255,211,106,.30);color:#ffe5a3;border-radius:18px;padding:12px;margin-top:12px;font-size:13px;line-height:1.45}.toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#1e2845;border:1px solid #53648f;border-radius:999px;padding:10px 16px;opacity:0;transition:.2s;z-index:999;font-weight:900}.toast.show{opacity:1}.modal{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;z-index:100}.modal.show{display:flex}.chat-panel{width:100%;max-width:880px;margin:0 auto;border-radius:22px 22px 0 0}.chat-list{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;height:340px;overflow-y:auto;padding:10px}.msg{background:#202a47;border-radius:13px;padding:9px 11px;margin:7px 0}.msg.mine{background:#173d27;border:1px solid #2e7146}.msg-meta{font-size:12px;color:#a8b2cc;display:flex;justify-content:space-between}.chat-form{display:grid;grid-template-columns:1fr 74px;gap:7px;margin-top:9px}.chat-form input{margin:0}.member-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.member{background:rgba(8,12,24,.55);border:1px solid rgba(255,255,255,.10);border-radius:14px;padding:10px;margin:6px 0}.boss-form{display:grid;grid-template-columns:1fr 150px 120px 1fr 120px;gap:8px;align-items:end}.boss-form input{margin:0}.boss-timer{border-color:rgba(255,211,106,.35);background:rgba(70,52,18,.38)}details.member summary{cursor:pointer;font-weight:900}.choice-list{display:grid;gap:8px}.choice-list button{width:100%;justify-content:flex-start;background:linear-gradient(180deg,#4c5571,#363d55)}.check-box{background:#0d1325;border:1px solid rgba(255,255,255,.12);border-radius:16px;padding:10px;margin-bottom:10px}.check-row{display:block;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}.check-row input{width:auto;margin-right:8px}.farm-manage{display:block!important;margin-top:12px}.dashboard-pair{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}.mini-board{background:rgba(15,22,40,.72);border:1px solid rgba(255,255,255,.12);border-radius:22px;padding:16px;box-shadow:0 12px 30px rgba(0,0,0,.18)}.mini-board h2{margin:0 0 10px;font-size:22px}.mini-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.mini-stats div{background:rgba(8,12,24,.55);border-radius:14px;padding:12px;text-align:center}.mini-stats b{display:block;font-size:26px}.mini-stats span{font-size:12px;color:var(--muted)}.mini-note{background:rgba(255,211,106,.15);border:1px solid rgba(255,211,106,.25);border-radius:12px;padding:8px;margin:8px 0;color:#ffe7a1;font-weight:800}.boss-form.compact{display:grid;grid-template-columns:1fr 1.25fr 1fr 80px;gap:8px;margin:8px 0}.boss-form.compact input{margin:0}.boss-list{display:grid;gap:8px}.boss-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;background:rgba(70,52,18,.38);border:1px solid rgba(255,211,106,.35);border-radius:14px;padding:10px}.boss-row span{font-size:12px;color:var(--muted)}.boss-row .boss-left{font-size:18px;color:#ffe7a1}
.online-compact{display:grid;grid-template-columns:220px 1fr 180px;gap:12px;align-items:center;background:linear-gradient(180deg,rgba(22,34,60,.92),rgba(15,24,43,.86));border:1px solid rgba(255,255,255,.12);border-radius:24px;padding:16px;margin:14px 0;box-shadow:0 18px 36px rgba(0,0,0,.18)}
.online-main{display:flex;gap:12px;align-items:center}.online-main .dot{width:18px;height:18px;border-radius:50%;background:#63ff88;box-shadow:0 0 18px rgba(99,255,136,.75)}.online-main b{font-size:20px}.online-main p{margin:2px 0 0;color:var(--muted)}
.job-chips{display:flex;flex-wrap:wrap;gap:8px}.job-chip{background:rgba(79,139,255,.18);border:1px solid rgba(79,139,255,.28);border-radius:999px;padding:8px 12px;font-weight:900}
.online-detail{background:rgba(8,12,24,.45);border-radius:14px;padding:10px}.online-detail summary{cursor:pointer;font-weight:900}

.dashboard-pair{display:grid;grid-template-columns:1.15fr .85fr;gap:16px;margin:16px 0}.mini-board{background:linear-gradient(180deg,rgba(24,35,61,.96),rgba(16,24,43,.92));border:1px solid rgba(255,255,255,.14);border-radius:26px;padding:18px;box-shadow:0 18px 42px rgba(0,0,0,.22)}.board-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}.board-head h2{margin:0;font-size:24px}.board-head span{color:var(--muted);font-size:13px;font-weight:900}.mini-note{background:linear-gradient(90deg,rgba(255,211,106,.22),rgba(255,211,106,.10));border:1px solid rgba(255,211,106,.28);border-radius:14px;padding:10px 12px;margin:10px 0;color:#ffe7a1;font-weight:900}
.boss-form.better{display:grid;grid-template-columns:1fr 1.3fr 1fr 110px;gap:10px;align-items:end;margin:12px 0}.boss-form.better label{font-size:13px;color:var(--muted);font-weight:900}.boss-form.better input{height:48px;font-size:16px;margin:4px 0 0}.boss-form.better button{height:50px;font-size:16px}
.boss-test-row{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 12px}.boss-test-row button{background:rgba(79,139,255,.22)}
.boss-list{display:grid;gap:10px}.boss-card{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;background:rgba(8,12,24,.48);border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:14px}.boss-card.next-boss{background:linear-gradient(90deg,rgba(255,115,66,.25),rgba(255,211,106,.16));border-color:rgba(255,211,106,.45)}.boss-title{font-size:20px;font-weight:1000}.boss-time{color:#dbe6ff;margin-top:5px;font-weight:900}.boss-memo{margin-top:6px;color:#ffe7a1;font-size:13px}.boss-right-box{text-align:right}.boss-left-label{font-size:12px;color:var(--muted);font-weight:900}.boss-count{font-size:24px;color:#ffe7a1;font-weight:1000}.empty-box{text-align:center;color:var(--muted);padding:22px;border:1px dashed rgba(255,255,255,.18);border-radius:18px}

.mini-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.mini-stats div{background:rgba(8,12,24,.55);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:18px 10px;text-align:center}.mini-stats b{display:block;font-size:34px}.mini-stats span{font-size:13px;color:var(--muted);font-weight:900}.total-money{margin-top:14px;border-radius:16px;background:linear-gradient(90deg,rgba(255,211,106,.22),rgba(255,211,106,.08));border:1px solid rgba(255,211,106,.28);padding:14px;color:#ffe7a1;font-weight:900}.total-money b{font-size:18px}


.voice-panel{max-width:520px}.voice-box{display:grid;gap:12px;margin-top:12px}.check-line{display:flex;align-items:center;gap:10px;background:rgba(8,12,24,.45);border:1px solid rgba(255,255,255,.10);padding:12px;border-radius:14px;font-weight:900}.check-line input{width:20px;height:20px}.voice-box input[type=range]{width:100%;accent-color:#66a3ff}


.game-alert{position:fixed;right:24px;top:24px;z-index:9999;display:none;max-width:min(440px,calc(100vw - 32px))}
.game-alert.show{display:block;animation:popAlert .25s ease-out}
.game-alert-card{display:grid;grid-template-columns:64px 1fr auto;gap:14px;align-items:center;background:linear-gradient(135deg,rgba(255,80,54,.96),rgba(255,174,54,.94));color:#fff;border:2px solid rgba(255,255,255,.35);border-radius:26px;padding:18px;box-shadow:0 24px 70px rgba(0,0,0,.45)}
.game-alert-icon{font-size:44px;filter:drop-shadow(0 4px 10px rgba(0,0,0,.25))}
.game-alert-title{font-size:24px;font-weight:1000;letter-spacing:-.5px}
.game-alert-body{font-size:18px;font-weight:900;opacity:.95;margin-top:4px}
#gameModeBtn.ok{background:linear-gradient(180deg,#ff8a3d,#df5b26);color:white;border-color:rgba(255,255,255,.28)}
@keyframes popAlert{from{transform:translateY(-12px) scale(.96);opacity:0}to{transform:none;opacity:1}}


/* v16.0 schedule + realtime chat dashboard */
.summary{display:none!important}
.top-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.slim-online{display:grid;grid-template-columns:190px 1fr 150px;gap:12px;align-items:center;background:linear-gradient(180deg,rgba(22,34,60,.92),rgba(15,24,43,.86));border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:13px 15px;margin:12px 0;box-shadow:0 14px 30px rgba(0,0,0,.16)}
.slim-online .online-main{display:flex;gap:12px;align-items:center}.slim-online .dot{width:16px;height:16px;border-radius:50%;background:#63ff88;box-shadow:0 0 16px rgba(99,255,136,.7)}.slim-online p{margin:2px 0 0;color:var(--muted);font-size:13px}.job-chips{display:flex;flex-wrap:wrap;gap:8px}.job-chip{background:rgba(79,139,255,.18);border:1px solid rgba(79,139,255,.28);border-radius:999px;padding:7px 11px;font-weight:900;font-size:13px}.online-detail{background:rgba(8,12,24,.45);border-radius:14px;padding:10px}.online-detail summary{cursor:pointer;font-weight:900}
.dashboard-pair{display:grid;grid-template-columns:1.15fr .85fr;gap:16px;margin:12px 0 16px}.mini-board{background:linear-gradient(180deg,rgba(24,35,61,.96),rgba(16,24,43,.92));border:1px solid rgba(255,255,255,.14);border-radius:24px;padding:16px;box-shadow:0 18px 42px rgba(0,0,0,.20)}.board-head{display:flex;align-items:center;justify-content:space-between;gap:10px}.board-head h2{margin:0;font-size:22px}.board-head span{color:var(--muted);font-weight:900;font-size:13px}.mini-note{background:linear-gradient(90deg,rgba(255,211,106,.22),rgba(255,211,106,.10));border:1px solid rgba(255,211,106,.28);border-radius:14px;padding:9px 11px;margin:10px 0;color:#ffe7a1;font-weight:900}
.schedule-list{display:grid;gap:8px}.schedule-row{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px;background:rgba(8,12,24,.48);border:1px solid rgba(255,255,255,.10);border-radius:15px;padding:11px}.schedule-row span{display:block;color:var(--muted);font-size:12px;margin-top:3px}.schedule-left{font-size:20px;color:#ffe7a1}.empty-box.small{padding:14px;text-align:center;color:var(--muted);border:1px dashed rgba(255,255,255,.18);border-radius:14px}
.tiny-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.tiny-stats div{background:rgba(8,12,24,.55);border-radius:15px;padding:12px;text-align:center}.tiny-stats b{display:block;font-size:22px}.tiny-stats span{font-size:12px;color:var(--muted);font-weight:900}
.main-grid{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;align-items:start}.section-head,.chat-inline-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:6px 0 10px}.section-head h2,.chat-inline-head h2{margin:0;font-size:24px}.section-head span,.chat-inline-head span{color:var(--muted);font-size:13px;font-weight:900}
.side-chat{position:sticky;top:12px;background:linear-gradient(180deg,rgba(24,35,61,.96),rgba(16,24,43,.92));border:1px solid rgba(255,255,255,.14);border-radius:24px;padding:15px;box-shadow:0 18px 42px rgba(0,0,0,.22)}
.inline-chat-list{height:520px;max-height:58vh;overflow:auto;background:rgba(8,12,24,.46);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:12px}.inline-chat-input{margin-top:10px}.inline-chat-input input{height:46px;margin:0}.inline-chat-input button{height:46px}
@media(max-width:1100px){.main-grid{grid-template-columns:1fr}.side-chat{position:relative;top:auto}.inline-chat-list{height:320px}.dashboard-pair{grid-template-columns:1fr}.slim-online{grid-template-columns:1fr}}

@media(max-width:680px){.main-grid{gap:10px}.section-head h2,.chat-inline-head h2{font-size:21px}.side-chat{padding:13px;border-radius:20px}.inline-chat-list{height:280px}.dashboard-pair{gap:10px}.game-alert{left:12px;right:12px;top:12px;max-width:none}.game-alert-card{grid-template-columns:48px 1fr;gap:10px}.game-alert-card button{grid-column:1/3}.game-alert-icon{font-size:36px}.game-alert-title{font-size:21px}.game-alert-body{font-size:16px}.online-compact{grid-template-columns:1fr}.dashboard-pair{grid-template-columns:1fr}.boss-form.better{grid-template-columns:1fr}.boss-form.better button{width:100%}.board-head{align-items:flex-start;flex-direction:column}.boss-card{grid-template-columns:1fr}.boss-right-box{text-align:left}.mini-stats b{font-size:28px}.dashboard-pair{grid-template-columns:1fr}.boss-form.compact{grid-template-columns:1fr}.mini-board h2{font-size:20px}.boss-form{grid-template-columns:1fr}.boss-form button{width:100%}.tabs{padding-bottom:8px}.slot{align-items:flex-start;gap:8px}.post-head{gap:8px}.chat-list{height:55vh}.pill.big-done{font-size:15px;padding:9px 15px}.closed-card:before{font-size:16px;padding:7px}.wrap{padding:12px 10px 90px}h1{font-size:22px}.summary{grid-template-columns:repeat(3,1fr);gap:7px}.stat{padding:10px 4px}.stat b{font-size:21px}.actions{grid-template-columns:1fr 1fr}.top-actions>*{flex:1}.panel,.party-card{border-radius:20px;padding:13px}button,.btn{font-size:14px;padding:10px 11px}}
"""

GATE = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>입장</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>🔐 문파 전용</h1><div class='sub'>월하 · 연가 · 연희 파티모집</div></header><section class='panel'><h2>입장 비밀번호</h2><form method='post'><input name='password' type='password' placeholder='문파 비밀번호'><button style='width:100%'>입장</button></form>{% if error %}<div class='notice'>비밀번호가 맞지 않습니다.</div>{% endif %}</section></div></body></html>"""

REGISTER = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>등록</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>👤 문파원 등록</h1><div class='sub'>처음 한 번만 등록하면 됩니다.</div></header><section class='panel'><form method='post'><label>계정명</label><input name='account' value='{{ form.account }}' placeholder='예: 역인' required><label>대표 캐릭터명</label><input name='char_name' value='{{ form.char_name }}' placeholder='예: 역인' required><label>직업/차수</label><select name='job'>{% for job in jobs %}<option {% if form.job==job %}selected{% endif %}>{{ job }}</option>{% endfor %}</select><button style='width:100%'>승인 요청</button></form>{% if error %}<div class='notice'>{{ error }}</div>{% endif %}<p class='meta'>관리자 승인 후 이용 가능합니다.</p></section></div></body></html>"""

WAIT = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>대기</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>⏳ 승인 대기중</h1></header><section class='panel'><p>{{ user.account if user else "승인 대기중" }} 계정이 승인 대기중입니다.</p><div class='top-actions'><a class='btn' href='/admin'>관리자 페이지</a><form method='post' action='/logout'><button class='gray'>로그아웃</button></form></div><p class='meta'>최초 세팅이면 관리자 페이지에서 기존 관리자 비밀번호로 임시 관리자 모드에 들어가 승인할 수 있습니다.</p></section></div></body></html>"""

MAIN = """
<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>파티모집</title><style>{{ css }}</style></head><body>
<div class='wrap'><header class='header'><h1>⚔️ 월하 · 연가 · 연희 파티모집</h1><div class='sub'>Made by 역인(진선) · {{ app_version|default('v15.0') }}</div></header>{% if notice %}<div class='notice'>📢 {{ notice }}</div>{% endif %}
{% if page=='home' %}
<section class='panel'><div class='top-actions'><a class='btn' href='/new'>+ 모집글</a><a class='btn gray' href='/chars'>내 캐릭터</a><button class='gray' onclick='toggleAlarm()' id='alarmBtn'>🔔 알림 ON</button><button class='gray' onclick='openAlarmCheck()'>알림점검</button><button class='gray' onclick='openVoiceSettings()'>음성설정</button><button class='gray' onclick='toggleGameMode()' id='gameModeBtn'>🎮 게임모드 OFF</button><button class='gray' onclick='toggleClosedPosts()' id='closedToggleBtn'>마감숨김</button></div><div class='alarm-guide'>🔔 알림은 사이트가 열려있는 동안 동작합니다. 알림점검에서 권한과 테스트 알림을 확인하세요.</div>
<div class='tabs'>{% for f in cats %}<a class='{% if f==filter_value %}on{% endif %}' href='/?filter={{ f }}'>{{ f }}</a>{% endfor %}</div></section>{{ member_summary|safe }}
<section class='dashboard-pair'>{{ schedule_html|safe }}{{ farm_stats|safe }}</section>
<section class='main-grid'>
  <main class='recruit-area'>
    <div class='section-head'><h2>📌 모집글</h2><span>모집중 우선 표시</span></div>
    <div id='postList'>{{ post_list|safe }}</div>
  </main>
  <aside class='side-chat'>
    <div class='chat-inline-head'><h2>💬 통합채팅</h2><span>실시간</span></div>
    <div id='globalChatInline' class='chat-list inline-chat-list'>{{ global_chat|safe }}</div>
    <div class='quick inline-chat-input'><input id='globalChatText' placeholder='메시지 입력'><button onclick='sendGlobalChat()'>전송</button></div>
  </aside>
</section>
{% endif %}
{% if page=='new' or page=='edit' %}
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h2>{% if page=='edit' %}수정{% else %}모집글 올리기{% endif %}</h2><form method='post' action='{% if page=="edit" %}/edit/{{ post.id }}{% else %}/create{% endif %}' onsubmit='return prepareSubmit()'><label>작성 캐릭터</label><select name='owner_char_id'>{% for c in chars %}<option value='{{ c.id }}'>{{ c.name }}({{ c.job }})</option>{% endfor %}</select><label>종류</label><select name='category' id='typeSelect' onchange='updatePlaces();toggleSlotBox()'>{% for c in cats_no_all %}<option {% if post and post.category==c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><label>장소</label>{% for cat, vals in places.items() %}<select name='place_{{ cat }}' id='place_{{ cat }}' class='place-select hidden'>{% for p in vals %}<option {% if post and post.place==p %}selected{% endif %}>{{ p }}</option>{% endfor %}</select>{% endfor %}<label>채널 4자리</label><input name='channel' id='channelInput' maxlength='4' inputmode='numeric' value='{{ post.channel if post else "" }}' placeholder='예: 3385' oninput='numbersOnly(this)'><label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' value='{{ post.start_time if post else "" }}' placeholder='예: 09:00'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option selected>오후</option></select><input name='end_time' value='{{ post.end_time if post else "" }}' placeholder='예: 11:00'></div><label>메모</label><textarea name='memo'>{{ post.memo if post else "" }}</textarea><div class='panel' id='slotPanel'><label>사냥 직업 자리 추가</label><div class='quick'><select id='slotJob'>{% for j in jobs %}<option>{{ j }}</option>{% endfor %}</select><button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slotsBox'></div></div><div class='notice hidden' id='simpleNotice'>600퀘는 참여 버튼 방식입니다. 파밍은 관리자/부문파장만 생성할 수 있습니다.</div><button style='width:100%'>저장</button></form></section>
{% endif %}
{% if page=='chars' %}
<section class='panel'><a class='btn gray' href='/'>← 메인</a><h2>내 캐릭터</h2><form method='post' action='/chars/add'><label>캐릭터명</label><input name='name' required><label>직업/차수</label><select name='job'>{% for job in jobs %}<option>{{ job }}</option>{% endfor %}</select><button style='width:100%'>캐릭터 추가 요청</button></form></section><section class='panel'><h2>등록 캐릭터</h2>{% for c in user.chars %}<div class='member'>{{ c.name }}({{ c.job }}) · {{ c.status }} {% if c.status=='approved' %}<form method='post' action='/chars/select/{{ c.id }}' style='display:inline'><button class='mini'>대표선택</button></form>{% endif %}</div>{% endfor %}</section>
{% endif %}
</div>
<div id='globalModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>💬 통합채팅</b><button class='mini gray' onclick='closeGlobalChat()'>닫기</button></div><div class='alarm-guide'>최근 100개 유지 · 24시간 자동삭제 · 본인 5분 이내 삭제 가능</div><div id='globalChatListOld' class='chat-list'></div><div class='chat-form'><input id='globalChatTextOld' placeholder='메시지'><button onclick='sendGlobalChat()'>전송</button></div></div></div>
<div id='partyModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>💬 채팅</b><button class='mini gray' onclick='closePartyChat()'>닫기</button></div><div id='partyChatList' class='chat-list'></div><div class='chat-form'><input id='partyChatText' placeholder='메시지'><button onclick='sendPartyChat()'>전송</button></div></div></div>
<div id='charPickModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between'><b>참여 캐릭터 선택</b><button class='mini gray' onclick='closeCharPick()'>닫기</button></div><div id='charPickList' class='choice-list'></div></div></div>
<div id='alarmModal' class='modal'><div class='panel chat-panel'><div style='display:flex;justify-content:space-between;align-items:center'><b>🔔 알림 점검</b><button class='mini gray' onclick='closeAlarmCheck()'>닫기</button></div><div id='alarmStatusBox' class='alarm-guide'>상태 확인중...</div><div class='top-actions'><button class='ok' onclick='requestAlarmPermission()'>권한 요청</button><button onclick='sendTestNotification()'>테스트 알림</button><button class='gray' onclick='refreshAlarmStatus()'>새로고침</button></div><div class='notice'>알림은 사이트 탭이 열려 있어야 동작합니다. 주소창 왼쪽 사이트 설정에서 알림이 차단되어 있으면 허용으로 바꿔주세요.</div></div></div>

<div id='voiceModal' class='modal'><div class='panel chat-panel voice-panel'>
  <div style='display:flex;justify-content:space-between;align-items:center'><b>🔊 음성 알림 설정</b><button class='mini gray' onclick='closeVoiceSettings()'>닫기</button></div>
  <div class='voice-box'>
    <label class='check-line'><input type='checkbox' id='voiceEnabled' onchange='saveVoiceSettings()'> 음성 알림 사용</label>
    <label class='check-line'><input type='checkbox' id='voiceMuted' onchange='saveVoiceSettings()'> 음소거</label>
    <label>음량 <span id='voiceVolumeText'>70%</span></label>
    <input type='range' id='voiceVolume' min='0' max='100' value='70' oninput='saveVoiceSettings()'>
    <div class='top-actions'>
      <button class='ok' onclick='testVoiceAlert()'>테스트 음성</button>
      <button class='gray' onclick='stopVoiceAlert()'>음성 중지</button>
    </div>
    <div class='notice'>브라우저 정책 때문에 처음 한 번은 버튼을 눌러야 음성이 정상 재생됩니다. 설정은 각 문파원 기기에 따로 저장됩니다.</div>
  </div>
</div></div>

<div id='gameAlertOverlay' class='game-alert'>
  <div class='game-alert-card'>
    <div class='game-alert-icon'>🔥</div>
    <div>
      <div id='gameAlertTitle' class='game-alert-title'>보스 알림</div>
      <div id='gameAlertBody' class='game-alert-body'>젠타임 알림</div>
    </div>
    <button class='mini gray' onclick='closeGameAlert()'>닫기</button>
  </div>
</div>
<div id='toast' class='toast'></div>
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
function refresh(){if(location.pathname!='/')return;if(isEditingPost())return;fetch('/api/posts'+location.search,{cache:'no-store'}).then(r=>r.text()).then(h=>{qs('postList').innerHTML=h;scanAlarms();countMine();applyClosedVisibility()}).catch(()=>{})}
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
  updateAlarmBtn();updateGameModeBtn();loadVoiceSettings();updateGameModeBtn();
  if(!turningOff && 'Notification' in window && Notification.permission==='default'){
    Notification.requestPermission().then(()=>toast('알림이 켜졌습니다.'));
  }else{
    toast(turningOff?'알림 꺼짐':'알림 켜짐');
  }
}
function alarmStatusText(){
  if(!('Notification' in window))return '미지원: 이 브라우저는 알림을 지원하지 않습니다.';
  if(Notification.permission==='granted')return '허용: 브라우저 알림을 받을 수 있습니다.';
  if(Notification.permission==='denied')return '차단: 브라우저/사이트 설정에서 알림을 허용으로 바꿔야 합니다.';
  return '미설정: 권한 요청 버튼을 눌러 허용해주세요.';
}
function refreshAlarmStatus(){const b=qs('alarmStatusBox');if(b)b.textContent=alarmStatusText();}
function openAlarmCheck(){const m=qs('alarmModal');if(m){m.classList.add('show');refreshAlarmStatus();}}
function closeAlarmCheck(){const m=qs('alarmModal');if(m)m.classList.remove('show');}
function requestAlarmPermission(){
  if(!('Notification' in window)){toast('이 브라우저는 알림 미지원');refreshAlarmStatus();return}
  Notification.requestPermission().then(()=>{refreshAlarmStatus();toast('알림 권한 상태 확인됨')});
}
function sendTestNotification(){notifyUser('테스트 알림','알림이 정상 동작합니다.');refreshAlarmStatus();}
function closedHidden(){return localStorage.getItem('baram_hide_closed')==='1'}
function applyClosedVisibility(){document.querySelectorAll('.closed-card').forEach(x=>x.style.display=closedHidden()?'none':'');const b=qs('closedToggleBtn');if(b)b.textContent=closedHidden()?'마감표시':'마감숨김'}
function toggleClosedPosts(){localStorage.setItem('baram_hide_closed',closedHidden()?'0':'1');applyClosedVisibility()}

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



function voiceOn(){return localStorage.getItem('baram_voice_on')==='1'}
function voiceMuted(){return localStorage.getItem('baram_voice_muted')==='1'}
function voiceVolume(){let v=parseInt(localStorage.getItem('baram_voice_volume')||'70');return Math.max(0,Math.min(100,v))}
function loadVoiceSettings(){
  const en=qs('voiceEnabled'), mu=qs('voiceMuted'), vol=qs('voiceVolume'), txt=qs('voiceVolumeText');
  if(en)en.checked=voiceOn();
  if(mu)mu.checked=voiceMuted();
  if(vol)vol.value=voiceVolume();
  if(txt)txt.textContent=voiceVolume()+'%';
}
function saveVoiceSettings(){
  const en=qs('voiceEnabled'), mu=qs('voiceMuted'), vol=qs('voiceVolume'), txt=qs('voiceVolumeText');
  if(en)localStorage.setItem('baram_voice_on',en.checked?'1':'0');
  if(mu)localStorage.setItem('baram_voice_muted',mu.checked?'1':'0');
  if(vol)localStorage.setItem('baram_voice_volume',vol.value);
  if(txt)txt.textContent=voiceVolume()+'%';
}
function openVoiceSettings(){const m=qs('voiceModal');if(m){loadVoiceSettings();m.classList.add('show')}}
function closeVoiceSettings(){const m=qs('voiceModal');if(m)m.classList.remove('show')}
function stopVoiceAlert(){try{window.speechSynthesis.cancel()}catch(e){}}
function speakVoice(text, repeat){
  if(!voiceOn()||voiceMuted())return;
  if(!('speechSynthesis' in window))return;
  try{
    window.speechSynthesis.cancel();
    const times=repeat||1;
    let i=0;
    const run=()=>{
      if(i>=times)return;
      const u=new SpeechSynthesisUtterance(text);
      u.lang='ko-KR';
      u.rate=1.0;
      u.pitch=1.0;
      u.volume=voiceVolume()/100;
      u.onend=()=>{i++; if(i<times)setTimeout(run,700)};
      window.speechSynthesis.speak(u);
    };
    run();
  }catch(e){}
}
function testVoiceAlert(){
  localStorage.setItem('baram_voice_on','1');
  loadVoiceSettings();
  speakVoice('해골왕 젠까지 5분 남았습니다.',1);
  toast('테스트 음성 재생');
}

function testBossAlert(minText){
  bossFullAlert('보스 젠 테스트','해골왕',minText,1);
  toast('보스 젠 '+minText+' 전 테스트 알림 전송');
}


function gameModeOn(){return localStorage.getItem('baram_game_mode')==='1'}
function updateGameModeBtn(){
  const b=qs('gameModeBtn');
  if(b)b.textContent=gameModeOn()?'🎮 게임모드 ON':'🎮 게임모드 OFF';
  if(b)b.classList.toggle('ok',gameModeOn());
}
function toggleGameMode(){
  const on=!gameModeOn();
  localStorage.setItem('baram_game_mode',on?'1':'0');
  if(on){
    localStorage.setItem('baram_alarm_off','0');
    localStorage.setItem('baram_voice_on','1');
    localStorage.setItem('baram_voice_muted','0');
    if('Notification' in window && Notification.permission==='default')Notification.requestPermission();
    toast('게임모드 ON');
  }else{
    toast('게임모드 OFF');
  }
  updateAlarmBtn();
  loadVoiceSettings();
  updateGameModeBtn();
}
function showGameAlert(title, body){
  if(!gameModeOn())return;
  const o=qs('gameAlertOverlay'), t=qs('gameAlertTitle'), b=qs('gameAlertBody');
  if(t)t.textContent=title;
  if(b)b.textContent=body||'';
  if(o){
    o.classList.add('show');
    clearTimeout(window.__gameAlertTimer);
    window.__gameAlertTimer=setTimeout(()=>o.classList.remove('show'),9000);
  }
}
function closeGameAlert(){const o=qs('gameAlertOverlay');if(o)o.classList.remove('show')}
function bossFullAlert(title, name, minutesText, repeat){
  notifyUser(title,name);
  showGameAlert(title, name+' 젠 '+minutesText+' 전');
  speakVoice(name+' 젠까지 '+minutesText+' 남았습니다.',repeat||1);
}


function updatePostSchedules(){
  const now=Date.now();
  document.querySelectorAll('.post-schedule').forEach(row=>{
    const id=row.dataset.postId,title=row.dataset.postTitle||'일정',at=new Date(row.dataset.startAt).getTime(),left=at-now;
    const el=row.querySelector('.schedule-left'); if(el)el.textContent=formatLeft?formatLeft(left):'';
    if(!bossLocalSent[id])bossLocalSent[id]={};
    if(left<=30*60*1000&&left>29*60*1000&&!bossLocalSent[id]['30']){bossLocalSent[id]['30']=true;bossFullAlert('일정 30분 전',title,'30분',1)}
    if(left<=15*60*1000&&left>14*60*1000&&!bossLocalSent[id]['15']){bossLocalSent[id]['15']=true;bossFullAlert('일정 15분 전',title,'15분',1)}
    if(left<=5*60*1000&&left>4*60*1000&&!bossLocalSent[id]['5']){bossLocalSent[id]['5']=true;bossFullAlert('일정 5분 전',title,'5분',3)}
  });
}

function formatLeft(ms){if(ms<=0)return '젠 시간';const sec=Math.floor(ms/1000),h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;return String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0')}
function markBossAlert(id,mark){fetch('/api/boss/mark_alert',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,mark:mark})}).catch(()=>{})}
let bossLocalSent={};
function updateBossTimers(){const now=Date.now();document.querySelectorAll('.boss-timer').forEach(card=>{const id=card.dataset.bossId,name=card.dataset.bossName||'보스',at=new Date(card.dataset.spawnAt).getTime(),left=at-now;const el=card.querySelector('.boss-left');if(el)el.textContent=formatLeft(left);if(!bossLocalSent[id])bossLocalSent[id]={};if(left<=30*60*1000&&left>29*60*1000&&!bossLocalSent[id]['30']){bossLocalSent[id]['30']=true;bossFullAlert('보스 젠 30분 전',name,'30분',1);markBossAlert(id,'30')}if(left<=15*60*1000&&left>14*60*1000&&!bossLocalSent[id]['15']){bossLocalSent[id]['15']=true;bossFullAlert('보스 젠 15분 전',name,'15분',1);markBossAlert(id,'15')}if(left<=5*60*1000&&left>4*60*1000&&!bossLocalSent[id]['5']){bossLocalSent[id]['5']=true;bossFullAlert('보스 젠 5분 전',name,'5분',3);markBossAlert(id,'5')}})}

function heartbeat(){fetch('/api/heartbeat',{method:'POST'}).then(r=>r.json()).then(x=>{if(qs('onlineCount'))qs('onlineCount').textContent=x.online||1}).catch(()=>{})}
document.addEventListener('DOMContentLoaded',()=>{updatePlaces();toggleSlotBox();updateAlarmBtn();refreshAlarmStatus();heartbeat();updateBossTimers();updatePostSchedules();scanAlarms();applyClosedVisibility();pollEvents();countMine();['globalChatText','partyChatText'].forEach(id=>{const i=qs(id);if(i)i.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();id==='globalChatText'?sendGlobalChat():sendPartyChat()}})})});
setInterval(refresh,2500);setInterval(refreshGlobalChat,1600);setInterval(refreshPartyChat,1600);setInterval(heartbeat,15000);setInterval(updateBossTimers,1000);setInterval(updatePostSchedules,1000);setInterval(pollEvents,2500);
</script></body></html>
"""

ADMIN = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>관리자</title><style>{{ css }}</style></head><body><div class='wrap'><header class='header'><h1>🔒 관리자</h1></header><a class='btn gray' href='/'>메인</a>{% if admin_msg %}<div class='notice'>{{ admin_msg }}</div>{% endif %}<section class='panel'><b>현재 로그인</b><br>{{ current_label }}</section>{% if not admin_ok %}<section class='panel'><form method='post' action='/admin/login'><label>최초 최고관리자 비밀번호</label><input name='password' type='password'><button>현재 계정을 임시 관리자 접속 / 최고관리자 등록</button></form><p class='meta'>먼저 메인 사이트에서 본인 문파원 계정으로 로그인되어 있어야 합니다. 로그인 계정이 없으면 최고관리자로 지정할 대상이 없습니다.</p></section>{% else %}<section class='panel'><div class='top-actions'><form method='post' action='/admin/logout'><button class='gray'>로그아웃</button></form><form method='post' action='/admin/clear_closed'><button>마감글 정리</button></form><form method='post' action='/admin/clear_chat'><button class='danger'>통합채팅 삭제</button></form><a class='btn ok' href='/admin/backup'>데이터 백업</a></div></section><section class='panel'><h2>문파 설정</h2><form method='post' action='/admin/settings'><label>입장 비밀번호</label><input name='access_password'><label>관리자 비밀번호</label><input name='admin_password'><button>저장</button></form></section><section class='panel'><h2>공지</h2><form method='post' action='/admin/notice'><textarea name='notice'>{{ notice }}</textarea><button>저장</button></form></section><section class='panel'><h2>파밍 아이템</h2><form method='post' action='/admin/farm_items'><label>해골왕</label><input name='items_해골왕' value='{{ farm_items.get("해골왕", [])|join(", ") }}'><label>어금니</label><input name='items_어금니' value='{{ farm_items.get("어금니", [])|join(", ") }}'><button>저장</button></form></section><section class='panel'><h2>가입 승인</h2>{% for u in pending_users %}<div class='member'><b>{{ u.account }}</b> / {% for c in u.chars %}{{ c.name }}({{ c.job }}) {% endfor %}<form method='post' action='/admin/user/{{ u.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/user/{{ u.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p>대기 없음</p>{% endfor %}</section><section class='panel'><h2>캐릭터 승인</h2>{% for item in pending_chars %}<div class='member'><b>{{ item.user.account }}</b> / {{ item.char.name }}({{ item.char.job }})<form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/approve' style='display:inline'><button class='mini ok'>승인</button></form><form method='post' action='/admin/char/{{ item.user.id }}/{{ item.char.id }}/reject' style='display:inline'><button class='mini danger'>거부</button></form></div>{% else %}<p>대기 없음</p>{% endfor %}</section><section class='panel'><h2>권한 관리</h2>{% for u in users %}<div class='member'><b>{{ u.account }}</b> · 권한: {{ {'member':'일반','admin':'관리자/부문파장','super':'최고관리자'}.get(u.role|default('member'), u.role|default('member')) }} · {{ u.status }}{% if u.blocked %} · 차단{% endif %}<br>{% for c in u.chars %}{{ c.name }}({{ c.job }}) - {{ c.status }}<br>{% endfor %}{% if super_ok %}<form method='post' action='/admin/role/{{ u.id }}/member' style='display:inline'><button class='mini gray'>일반</button></form><form method='post' action='/admin/role/{{ u.id }}/admin' style='display:inline'><button class='mini ok'>관리자</button></form><form method='post' action='/admin/role/{{ u.id }}/super' style='display:inline'><button class='mini'>최고관리자</button></form>{% endif %}<form method='post' action='/admin/user/{{ u.id }}/toggle_block' style='display:inline'><button class='mini danger'>차단/해제</button></form>{% if super_ok %}<form method='post' action='/admin/delete_user/{{ u.id }}' style='display:inline' onsubmit="return confirm('정말 이 회원을 삭제할까요?')"><button class='mini danger'>회원삭제</button></form>{% endif %}</div>{% endfor %}</section><section class='panel'><h2>글 관리</h2>{% for p in posts %}<div class='member'><b>{{ p.place }}</b> / {{ p.category }} / {{ p.owner_label }}<form method='post' action='/admin/delete_post/{{ p.id }}'><button class='mini danger'>삭제</button></form></div>{% endfor %}</section>{% endif %}</div></body></html>"""

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
    all_posts = list(reversed(d["posts"]))
    posts = all_posts
    if filt != "전체":
        posts = [p for p in posts if p.get("category") == filt]
    posts = sort_posts_for_view(posts)
    open_count = sum(1 for p in posts if status_text(p) in ["모집중","진행중"])
    return render_template_string(MAIN, css=CSS, page="home", user=u, cats=CATEGORIES, cats_no_all=CATEGORIES[1:], filter_value=filt, post_list=render_posts(posts,u,d["settings"].get("farm_items", FARM_ITEMS), admin=is_admin_user(u)), global_chat=chat_html(d), open_count=open_count, member_html=member_html(d), member_job_html=member_job_html(d), member_summary=member_summary_html(d), schedule_html=today_schedule_html(d), farm_stats=farming_stats_html(all_posts), notice=d["settings"].get("notice",""), jobs=JOBS, places=PLACES, app_version=APP_VERSION)

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
def new_page():
    d = load()
    u = current_user(d)
    if not chars(u):
        return redirect("/chars")
    allowed_categories = ["사냥", "600퀘", "파밍"] if is_admin_user(u) else ["사냥", "600퀘"]
    return render_template_string(MAIN, css=CSS, page="new", post=None, chars=chars(u), user=u, cats_no_all=allowed_categories, jobs=JOBS, places=PLACES, notice="", app_version=APP_VERSION)

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
        return render_template_string(MAIN, css=CSS, page="edit", post=p, chars=chars(u), user=u, cats_no_all=allowed_categories, jobs=JOBS, places=PLACES, notice="", app_version=APP_VERSION)
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
    return render_template_string(MAIN, css=CSS, page="chars", user=u, jobs=JOBS, places=PLACES, cats_no_all=CATEGORIES[1:], notice="", app_version=APP_VERSION)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","7777")), debug=False, threaded=True)
