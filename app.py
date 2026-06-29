
from flask import Flask, request, redirect, session, render_template_string
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
import json
import uuid
import re
import html
import hashlib
import secrets
import time
import random
import string

APP_VERSION = "v31.7-final"
APP_TITLE = "월하 · 연가 · 연희 파티모집"
KST = ZoneInfo("Asia/Seoul")
DATA_PATH = Path(os.environ.get("DATA_PATH", "data.json"))

app = Flask(__name__)

def auto_link_text(value):
    text = html.escape(str(value or ""))
    text = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer" class="memo-link">\1</a>',
        text
    )
    return text.replace("\n", "<br>")

try:
    app.jinja_env.filters["autolink"] = auto_link_text
except Exception:
    pass

app.secret_key = os.environ.get("SECRET_KEY", "baram-party-v21-secret")

JOBS = ["전사","검객","검제","검황","검성","도적","자객","진검","귀검","태성","주술사","술사","현사","현인","현자","도사","도인","명인","진인","진선","기타"]
JOB_GROUPS = {
    "전사 계열": ["전사","검객","검제","검황","검성"],
    "도적 계열": ["도적","자객","진검","귀검","태성"],
    "주술사 계열": ["주술사","술사","현사","현인","현자"],
    "도사 계열": ["도사","도인","명인","진인","진선"],
    "기타": ["기타"],
}
CATEGORIES = ["전체","사냥","파밍","600퀘","승급지원"]
PLACES = {
    "사냥": ["도삭산900", "흉노", "선비", "기타"],
    "파밍": ["어금니", "해골왕", "기타"],
    "600퀘": ["선비족", "도삭산 800층", "도삭산 900층"],
    "승급지원": ["1차 승급", "2차 승급", "3차 승급", "4차 승급", "기타"],
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

.choice-card{display:flex;align-items:center;gap:12px;background:#081126;border:1px solid #263a64;border-radius:15px;padding:14px;margin:10px 0;cursor:pointer}
.choice-card input{width:auto;accent-color:#19c46f;transform:scale(1.15)}
.choice-card span{font-size:17px;color:#fff}
.choice-card:has(input:checked){border-color:#19c46f;box-shadow:0 0 0 3px rgba(25,196,111,.14)}
.farm-dist{font-weight:900}
.closed .closed-tag,.closed-tag{font-size:13px}

.group-badge{margin-left:6px;padding:3px 7px;border-radius:999px;background:rgba(244,212,122,.16);border:1px solid rgba(244,212,122,.3);color:#ffe5a0;font-size:11px}
.remain{background:rgba(244,212,122,.12);border:1px solid rgba(244,212,122,.25);border-radius:999px;padding:3px 8px}
@media(max-width:720px){.header .toolbar{margin-top:12px}.nav-btn{flex:1}.farm-form{grid-template-columns:1fr}.farm-summary{grid-template-columns:1fr}}

.alarm-panel{background:linear-gradient(180deg,rgba(16,26,49,.98),rgba(8,17,38,.98));border-color:#334a7c}
.alarm-row{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:8px 0}
.switch-line{display:flex;align-items:center;gap:8px;margin:0;color:#e7eeff}
.switch-line input{width:auto;accent-color:#19c46f}
.volume-label{display:flex;justify-content:space-between;color:#9fb0d1;font-size:13px;margin:10px 0 6px}
input[type='range']{padding:0;height:6px;accent-color:#19c46f}
.summary-card{position:relative;overflow:hidden}
.summary-card:after{content:"";position:absolute;right:-30px;top:-30px;width:90px;height:90px;border-radius:50%;background:rgba(88,116,255,.10)}
.card{border-color:#2c426f}
.card h2{font-size:26px}
.actions .btn{min-width:72px}
.farm-box{background:linear-gradient(180deg,rgba(8,17,38,.82),rgba(8,17,38,.58))}


.modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.58);backdrop-filter:blur(5px);z-index:1000;align-items:center;justify-content:center;padding:18px}
.modal-backdrop.show{display:flex}
.settings-modal{width:min(520px,100%);background:linear-gradient(180deg,#101b34,#081126);border:1px solid #38548d;border-radius:22px;padding:18px;box-shadow:0 30px 80px rgba(0,0,0,.55)}
.modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.modal-head h2{margin:0}
.setting-card{display:flex;justify-content:space-between;align-items:center;gap:14px;background:rgba(8,17,38,.88);border:1px solid #263a64;border-radius:16px;padding:14px;margin:10px 0}
.setting-card.vertical{display:block}
.toggle input{display:none}
.toggle span{display:block;width:54px;height:30px;border-radius:999px;background:#45506c;position:relative;box-shadow:inset 0 2px 6px rgba(0,0,0,.35)}
.toggle span:before{content:"";position:absolute;width:24px;height:24px;left:3px;top:3px;border-radius:50%;background:#fff;transition:.15s}
.toggle input:checked+span{background:#19c46f}
.toggle input:checked+span:before{left:27px}
.farm-form{grid-template-columns:110px minmax(130px,1fr) minmax(130px,1fr) 95px 95px 76px!important}

.admin-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}
.admin-card{background:#081126;border:1px solid #263a64;border-radius:15px;padding:13px}
.admin-card span{color:#9fb0d1;font-size:13px}
.admin-card strong{display:block;font-size:24px;margin-top:5px}
.admin-form{display:grid;grid-template-columns:1fr 100px;gap:8px}
.danger-zone{padding:12px;border:1px solid rgba(239,68,68,.35);border-radius:15px;background:rgba(239,68,68,.08)}
@media(max-width:720px){.admin-grid{grid-template-columns:1fr 1fr}.admin-form{grid-template-columns:1fr}}


.nav-btn{min-height:50px;padding:0 18px;border-radius:15px;font-size:15px;letter-spacing:-.3px}
.nav-btn.primary{background:linear-gradient(180deg,#27df8b,#13b864)!important;border-color:rgba(88,255,170,.28)!important}
.header .toolbar{background:rgba(8,17,38,.42);border:1px solid rgba(255,255,255,.06);border-radius:18px;padding:6px}
.category-bar{background:rgba(8,17,38,.58);border:1px solid rgba(255,255,255,.06);border-radius:17px;padding:6px}
.tab-chip{min-width:62px;min-height:38px;padding:0 14px!important;border-radius:13px!important;box-shadow:none!important}
.tab-chip.ok{background:linear-gradient(180deg,#24d985,#0fad61)!important;border-color:rgba(88,255,170,.22)!important}
.tab-chip.gray{background:rgba(77,91,124,.86)!important;border-color:rgba(255,255,255,.08)!important}
.btn.gray{background:linear-gradient(180deg,#5a6680,#404b66)!important}
.btn{transition:transform .12s ease, filter .12s ease, border-color .12s ease}
.btn:hover{transform:translateY(-1px)}
.admin-action-title{color:#ffe5a0;margin:8px 0 10px;font-size:14px}
.danger-zone .toolbar{margin-bottom:12px}
.admin-console h2{margin-top:24px;padding-top:14px;border-top:1px solid rgba(255,255,255,.06)}


.btn{
  position:relative;
  overflow:hidden;
  border:1px solid rgba(255,255,255,.11)!important;
  text-shadow:0 1px 0 rgba(0,0,0,.18);
}
.btn:before{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(180deg,rgba(255,255,255,.18),transparent 42%);
  pointer-events:none;
}
.btn.ok,.btn.primary,button.ok{
  background:linear-gradient(180deg,#2bea94 0%,#16bd68 52%,#0f9f55 100%)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.22),0 10px 22px rgba(16,189,104,.22)!important;
}
.btn.gray,button.gray{
  background:linear-gradient(180deg,#65728f 0%,#4b5874 55%,#39445f 100%)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.17),0 10px 22px rgba(0,0,0,.22)!important;
}
.btn.danger{
  background:linear-gradient(180deg,#ff6969 0%,#e94343 55%,#c92e2e 100%)!important;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 10px 22px rgba(239,68,68,.2)!important;
}
.tab-chip{
  font-size:14px!important;
  font-weight:900!important;
}
.admin-post-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 12px}
.admin-post-section{
  background:rgba(8,17,38,.45);
  border:1px solid rgba(255,255,255,.07);
  border-radius:18px;
  padding:14px;
  margin:12px 0;
}
.admin-post-section h3{margin:0 0 10px}
.admin-post-row{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  background:#081126;
  border:1px solid #263a64;
  border-radius:15px;
  padding:12px;
  margin:8px 0;
}
@media(max-width:720px){.admin-post-row{flex-direction:column;align-items:flex-start}}


/* v23 slim premium buttons */
.btn,button{
  min-height:40px;
  padding:0 15px;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.10)!important;
  font-size:14px;
  font-weight:900;
  letter-spacing:-.25px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.14),
    0 8px 18px rgba(0,0,0,.18)!important;
}
.btn:before,button:before{
  background:linear-gradient(180deg,rgba(255,255,255,.13),transparent 48%);
}
.nav-btn{
  min-height:44px!important;
  padding:0 17px!important;
  border-radius:13px!important;
}
.nav-btn.primary{
  background:linear-gradient(180deg,#25d985 0%,#13b465 100%)!important;
  box-shadow:0 10px 24px rgba(19,180,101,.18)!important;
}
.header .toolbar{
  padding:5px!important;
  gap:6px!important;
  background:rgba(8,17,38,.34)!important;
  border:1px solid rgba(255,255,255,.055)!important;
  border-radius:16px!important;
}
.category-bar{
  padding:4px!important;
  gap:4px!important;
  border-radius:14px!important;
  background:rgba(8,17,38,.48)!important;
}
.tab-chip{
  min-width:56px!important;
  min-height:34px!important;
  padding:0 13px!important;
  border-radius:11px!important;
  font-size:13px!important;
  background:transparent!important;
  border:1px solid transparent!important;
  box-shadow:none!important;
  color:#aebddd!important;
}
.tab-chip.ok{
  color:#fff!important;
  background:linear-gradient(180deg,#22d47e,#12aa5e)!important;
  border-color:rgba(73,255,162,.18)!important;
  box-shadow:0 8px 18px rgba(18,170,94,.16)!important;
}
.tab-chip.gray:hover{
  background:rgba(255,255,255,.055)!important;
  color:#fff!important;
}
.btn.gray,button.gray{
  background:linear-gradient(180deg,#53607a,#3e4963)!important;
}
.btn.danger{
  background:linear-gradient(180deg,#f45b5b,#d83b3b)!important;
}
.btn.ok,button.ok{
  background:linear-gradient(180deg,#24d985,#10ad5d)!important;
}
.actions{
  gap:6px!important;
}
.actions .btn{
  min-width:64px;
}
.summary-card{
  padding:13px 15px!important;
  border-radius:17px!important;
}
.summary-card strong{
  font-size:24px!important;
}
.card,.panel{
  border-radius:19px!important;
}
.card h2{
  font-size:24px!important;
}
.admin-post-tabs{
  background:rgba(8,17,38,.45);
  border:1px solid rgba(255,255,255,.06);
  border-radius:14px;
  padding:5px;
  width:max-content;
  max-width:100%;
}
@media(max-width:720px){
  .nav-btn{min-height:42px!important}
  .tab-chip{flex:1}
  .admin-post-tabs{width:100%}
}


/* v23.1 unified slim controls */
.btn,button,.mini,.nav-btn,.tab-chip{
  min-height:38px!important;
  padding:0 14px!important;
  border-radius:12px!important;
  font-size:14px!important;
  line-height:1!important;
}
.mini{
  min-height:34px!important;
  padding:0 11px!important;
  font-size:13px!important;
}
.full{
  min-height:42px!important;
}
input,select,textarea{
  border-radius:12px!important;
}
.pending-panel{
  max-width:520px;
  margin:70px auto;
  text-align:center;
}
.pending-icon{
  font-size:42px;
  margin-bottom:8px;
}
.pending-actions{
  justify-content:center;
  margin-top:16px;
}
.slot .toolbar .btn{
  min-width:58px;
}
.farm-form .btn,.farm-form button{
  min-height:40px!important;
}
.admin-console .btn{
  min-height:36px!important;
}


.auth-panel{max-width:520px;margin:70px auto;text-align:center}
.auth-logo{width:62px;height:62px;margin:0 auto 12px;border-radius:20px;background:linear-gradient(180deg,#24d985,#0fa65a);display:flex;align-items:center;justify-content:center;font-size:34px;box-shadow:0 18px 38px rgba(16,189,104,.22)}
.auth-actions{display:grid;gap:10px;margin-top:18px}
.auth-bottom{justify-content:center;margin-top:14px}
#global-chat{scroll-margin-top:16px}
#globalChatInput{min-width:0}
#globalChatForm{margin-top:10px}


button:disabled,.btn[disabled]{
  opacity:.55;
  cursor:not-allowed;
  filter:grayscale(.35);
}


.btn[disabled],button[disabled]{opacity:.55;cursor:not-allowed}
.slot .tag.ok{margin-right:4px}


/* v26 final polish */
:root{
  --shadow-soft:0 14px 34px rgba(0,0,0,.22);
  --shadow-hover:0 18px 44px rgba(0,0,0,.30);
}
body{letter-spacing:-.2px}
.header{
  border-radius:22px!important;
  padding:18px 18px!important;
  background:linear-gradient(135deg,rgba(88,116,255,.13),rgba(25,196,111,.055)),rgba(8,17,38,.38)!important;
  border:1px solid rgba(255,255,255,.07)!important;
  box-shadow:var(--shadow-soft)!important;
}
.header h1{font-size:27px!important;font-weight:950!important}
.panel,.card{border:1px solid rgba(255,255,255,.075)!important;box-shadow:var(--shadow-soft)!important}
.card{transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease,background .16s ease}
.card:hover{transform:translateY(-2px);box-shadow:var(--shadow-hover)!important;border-color:rgba(88,116,255,.28)!important}
.card:before{width:3px!important;opacity:.88}
.card.closed:before{background:linear-gradient(180deg,#7d879e,#4d566c)!important}
.card h2{margin:12px 0 8px!important;line-height:1.18!important}
.meta{line-height:1.45}
.summary-grid{gap:12px!important}
.summary-card{background:linear-gradient(180deg,rgba(16,26,49,.94),rgba(8,17,38,.94))!important;border:1px solid rgba(255,255,255,.075)!important}
.summary-card span{display:flex;align-items:center;gap:6px}
.summary-card strong{letter-spacing:-.8px}
.btn,button{user-select:none;white-space:nowrap}
.btn:active,button:active{transform:translateY(1px) scale(.99)!important}
.slot{transition:border-color .14s ease,background .14s ease}
.slot:hover{border-color:rgba(88,116,255,.22);background:rgba(10,22,48,.92)}
.slot b{letter-spacing:-.3px}
.tag{font-weight:900!important}
.count{font-size:13px!important}
.notice{line-height:1.45}
.chatbox{scroll-behavior:smooth}
.chatmsg{border:1px solid rgba(255,255,255,.04)}
.pill{font-size:13px}
.empty{background:rgba(8,17,38,.28)}
input,select,textarea{transition:border-color .14s ease,box-shadow .14s ease,background .14s ease}
input::placeholder,textarea::placeholder{color:#667694}
.auth-panel,.pending-panel{animation:fadeUp .22s ease both}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.toast{
  position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);
  background:linear-gradient(180deg,#152341,#0b1429);border:1px solid rgba(88,116,255,.32);
  color:#f4f7ff;border-radius:999px;padding:12px 18px;box-shadow:0 18px 50px rgba(0,0,0,.38);
  z-index:2000;opacity:0;transition:.2s ease;pointer-events:none;font-weight:900;
}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.choice-card{transition:.14s ease}
.choice-card:hover{border-color:rgba(25,196,111,.35)}
.admin-console{max-width:1120px;margin-left:auto;margin-right:auto}
.admin-card,.admin-post-row{transition:.14s ease}
.admin-post-row:hover,.admin-card:hover{border-color:rgba(88,116,255,.25)}
.schedule-row strong,.remain{color:#ffe28a!important}
.group-badge{white-space:nowrap}

.copy-btn{
  background:linear-gradient(180deg,#6b7896,#4b5874)!important;
}


.auto-delete-tag{
  background:rgba(244,212,122,.14)!important;
  border-color:rgba(244,212,122,.32)!important;
  color:#ffe5a0!important;
}
.closed .actions .btn.ok{
  display:none;
}


/* service stable notice */
.summary-grid,.summary-card,.mini-stats{
  display:none!important;
}
.clan-notice-card{
  margin:0 0 18px 0!important;
  border-color:rgba(244,212,122,.26)!important;
  background:linear-gradient(180deg,rgba(31,36,51,.96),rgba(10,18,36,.96))!important;
}
.clan-notice-head{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:10px;
  margin-bottom:10px;
}
.clan-notice-head h2{
  margin:0!important;
  font-size:20px!important;
}
.clan-notice-preview,.clan-notice-full{
  white-space:pre-wrap;
  line-height:1.62;
  color:#eef4ff;
  background:rgba(8,17,38,.58);
  border:1px solid rgba(255,255,255,.06);
  border-radius:15px;
  padding:13px;
  font-size:14px;
}
.clan-notice-full{display:none}
.clan-notice-card.expanded .clan-notice-preview{display:none}
.clan-notice-card.expanded .clan-notice-full{display:block}
.clan-notice-card button{margin-top:10px}
.admin-notice-box form.notice-edit-form{
  display:grid!important;
  grid-template-columns:1fr!important;
  gap:10px!important;
}
.admin-notice-box label{
  color:#c8d6f5;
  font-weight:900;
}
.admin-notice-box input,.admin-notice-box textarea{
  width:100%!important;
  box-sizing:border-box!important;
}
.admin-notice-box textarea{
  min-height:280px;
  resize:vertical;
  line-height:1.55;
}
@media(max-width:720px){
  .clan-notice-head h2{font-size:18px!important}
}


/* v26.14 final recruit button placement */
.recruit-head{
  display:flex!important;
  flex-direction:column!important;
  gap:12px!important;
  align-items:stretch!important;
}
.recruit-title-row{
  display:flex!important;
  align-items:center!important;
  justify-content:space-between!important;
  gap:12px!important;
}
.recruit-title-row h2{
  margin:0!important;
}
.recruit-write-btn{
  padding:10px 18px!important;
  border-radius:14px!important;
  font-weight:950!important;
  box-shadow:0 10px 26px rgba(25,196,111,.22)!important;
}
@media(max-width:720px){
  .recruit-title-row{
    align-items:stretch!important;
  }
  .recruit-write-btn{
    padding:9px 14px!important;
  }
}


/* v26.16 member manage polish */
.actions .btn + .btn{
  margin-left:4px;
}
.notice{
  line-height:1.5;
}


/* v26.17 edit member panel */
.edit-member-panel{
  margin-top:16px!important;
}
.edit-slots{
  display:grid;
  gap:10px;
}
.edit-slot-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:13px;
  border:1px solid rgba(88,116,255,.22);
  border-radius:15px;
  background:rgba(8,17,38,.62);
}
.choice-line{
  display:block;
  padding:12px;
  margin:8px 0;
  border:1px solid rgba(88,116,255,.22);
  border-radius:13px;
  background:rgba(8,17,38,.62);
  font-weight:900;
}
@media(max-width:720px){
  .edit-slot-row{
    align-items:stretch;
    flex-direction:column;
  }
}


/* v26.19 force edit member panel */
.edit-member-panel{margin-top:18px!important}
.edit-slots{display:grid;gap:10px}
.edit-slot-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:13px;
  border:1px solid rgba(88,116,255,.22);
  border-radius:15px;
  background:rgba(8,17,38,.62);
}
.choice-line{
  display:block;
  padding:12px;
  margin:8px 0;
  border:1px solid rgba(88,116,255,.22);
  border-radius:13px;
  background:rgba(8,17,38,.62);
  font-weight:900;
}
@media(max-width:720px){
  .edit-slot-row{align-items:stretch;flex-direction:column}
}


/* v26.20 edit job slot panel */
.edit-job-panel{margin-top:18px!important}
.edit-slots{display:grid;gap:10px}
.edit-slot-row{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:13px;
  border:1px solid rgba(88,116,255,.22);
  border-radius:15px;
  background:rgba(8,17,38,.62);
}
.job-add-form{
  margin-top:14px;
  padding-top:14px;
  border-top:1px solid rgba(255,255,255,.08);
}
@media(max-width:720px){
  .edit-slot-row{align-items:stretch;flex-direction:column}
}


/* v26.21 edit flow and notification polish */
.edit-bottom-nav{
  margin:12px 0 0 0!important;
}


/* v26.22 popup alert polish */
#toastWrap{
  position:fixed;
  top:18px;
  right:18px;
  z-index:9999;
  display:grid;
  gap:8px;
  max-width:360px;
}
.toast{
  opacity:0;
  transform:translateY(-8px);
  transition:.2s ease;
  background:linear-gradient(180deg,#1d2b4f,#101b35);
  border:1px solid rgba(255,255,255,.14);
  border-radius:14px;
  color:#fff;
  padding:12px 14px;
  box-shadow:0 18px 48px rgba(0,0,0,.38);
  font-weight:900;
  line-height:1.45;
}
.toast.show{
  opacity:1;
  transform:translateY(0);
}
@media(max-width:720px){
  #toastWrap{left:12px;right:12px;top:12px;max-width:none}
}


/* v26.23 toast only status fix */
#toastWrap{
  position:fixed;
  top:18px;
  right:18px;
  z-index:9999;
  display:grid;
  gap:8px;
  max-width:360px;
}
.toast{
  opacity:0;
  transform:translateY(-8px);
  transition:.2s ease;
  background:linear-gradient(180deg,#1d2b4f,#101b35);
  border:1px solid rgba(255,255,255,.14);
  border-radius:14px;
  color:#fff;
  padding:12px 14px;
  box-shadow:0 18px 48px rgba(0,0,0,.38);
  font-weight:900;
  line-height:1.45;
}
.toast.show{
  opacity:1;
  transform:translateY(0);
}
@media(max-width:720px){
  #toastWrap{left:12px;right:12px;top:12px;max-width:none}
}


/* v26.24 reliable toast */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  z-index:99999!important;
  display:grid!important;
  gap:8px!important;
  max-width:380px!important;
  pointer-events:none!important;
}
.toast{
  opacity:0;
  transform:translateY(-10px);
  transition:.22s ease;
  background:linear-gradient(180deg,#263861,#111d38)!important;
  border:1px solid rgba(255,255,255,.18)!important;
  border-radius:15px!important;
  color:#fff!important;
  padding:13px 15px!important;
  box-shadow:0 20px 60px rgba(0,0,0,.45)!important;
  font-weight:950!important;
  line-height:1.45!important;
  white-space:pre-wrap!important;
}
.toast.show{
  opacity:1!important;
  transform:translateY(0)!important;
}
@media(max-width:720px){
  #toastWrap{left:12px!important;right:12px!important;top:12px!important;max-width:none!important}
}


/* v26.25 direct toast */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  z-index:99999!important;
  display:grid!important;
  gap:8px!important;
  max-width:380px!important;
  pointer-events:none!important;
}
.toast{
  opacity:0;
  transform:translateY(-10px);
  transition:.22s ease;
  background:linear-gradient(180deg,#263861,#111d38)!important;
  border:1px solid rgba(255,255,255,.18)!important;
  border-radius:15px!important;
  color:#fff!important;
  padding:13px 15px!important;
  box-shadow:0 20px 60px rgba(0,0,0,.45)!important;
  font-weight:950!important;
  line-height:1.45!important;
  white-space:pre-wrap!important;
}
.toast.show{
  opacity:1!important;
  transform:translateY(0)!important;
}
@media(max-width:720px){
  #toastWrap{left:12px!important;right:12px!important;top:12px!important;max-width:none!important}
}


/* v27 stable toast */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  z-index:99999!important;
  display:grid!important;
  gap:8px!important;
  max-width:380px!important;
  pointer-events:none!important;
}
.toast{
  opacity:0;
  transform:translateY(-10px);
  transition:.22s ease;
  background:linear-gradient(180deg,#263861,#111d38)!important;
  border:1px solid rgba(255,255,255,.18)!important;
  border-radius:15px!important;
  color:#fff!important;
  padding:13px 15px!important;
  box-shadow:0 20px 60px rgba(0,0,0,.45)!important;
  font-weight:950!important;
  line-height:1.45!important;
  white-space:pre-wrap!important;
}
.toast.show{
  opacity:1!important;
  transform:translateY(0)!important;
}
@media(max-width:720px){
  #toastWrap{left:12px!important;right:12px!important;top:12px!important;max-width:none!important}
}


/* v27.1 toast test button */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  z-index:999999!important;
  display:grid!important;
  gap:8px!important;
  max-width:390px!important;
  pointer-events:none!important;
}
.toast{
  opacity:0!important;
  transform:translateY(-10px)!important;
  transition:.22s ease!important;
  background:linear-gradient(180deg,#263861,#111d38)!important;
  border:1px solid rgba(255,255,255,.20)!important;
  border-radius:15px!important;
  color:#fff!important;
  padding:13px 15px!important;
  box-shadow:0 20px 60px rgba(0,0,0,.48)!important;
  font-weight:950!important;
  line-height:1.45!important;
  white-space:pre-wrap!important;
}
.toast.show{
  opacity:1!important;
  transform:translateY(0)!important;
}
.toast-test-box{
  margin-top:14px;
  padding:14px;
  border:1px solid rgba(88,116,255,.22);
  border-radius:16px;
  background:rgba(8,17,38,.55);
}
.toast-test-box p{
  margin:6px 0 10px;
  color:#9fb0d1;
  font-size:13px;
}


/* v28.3 final notification css */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  left:auto!important;
  bottom:auto!important;
  z-index:9999999!important;
  display:grid!important;
  gap:8px!important;
  max-width:390px!important;
  pointer-events:none!important;
}
#toastWrap .toast,
.toast.v28-toast{
  position:relative!important;
  left:auto!important;
  right:auto!important;
  top:auto!important;
  bottom:auto!important;
  opacity:0!important;
  transform:translateY(-10px)!important;
  transition:.22s ease!important;
  background:linear-gradient(180deg,#263861,#111d38)!important;
  border:1px solid rgba(255,255,255,.22)!important;
  border-radius:15px!important;
  color:#fff!important;
  padding:13px 15px!important;
  box-shadow:0 20px 60px rgba(0,0,0,.48)!important;
  font-weight:950!important;
  line-height:1.45!important;
  white-space:pre-wrap!important;
  text-align:left!important;
  pointer-events:none!important;
}
#toastWrap .toast.show,
.toast.v28-toast.show{
  opacity:1!important;
  transform:translateY(0)!important;
}
.toast-test-box{
  margin-top:14px!important;
  padding:14px!important;
  border:1px solid rgba(88,116,255,.22)!important;
  border-radius:16px!important;
  background:rgba(8,17,38,.55)!important;
}
.toast-test-box .meta{
  margin:6px 0 10px!important;
}
@media(max-width:720px){
  #toastWrap{left:12px!important;right:12px!important;top:12px!important;max-width:none!important}
}


/* v28.4 toast duplicate guard css */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  left:auto!important;
  bottom:auto!important;
  z-index:9999999!important;
  display:grid!important;
  gap:8px!important;
  max-width:390px!important;
  pointer-events:none!important;
}
#toastWrap .toast,
.toast.v28-toast{
  position:relative!important;
  left:auto!important;
  right:auto!important;
  top:auto!important;
  bottom:auto!important;
}


/* v28.5 single toast css */
#toastWrap{
  position:fixed!important;
  top:18px!important;
  right:18px!important;
  left:auto!important;
  bottom:auto!important;
  z-index:9999999!important;
  display:grid!important;
  gap:8px!important;
  max-width:390px!important;
  pointer-events:none!important;
}
#toastWrap .toast,
.toast.v28-toast{
  position:relative!important;
  left:auto!important;
  right:auto!important;
  top:auto!important;
  bottom:auto!important;
}


/* v28.6 memo link */
.memo-link{
  color:#ffe082!important;
  text-decoration:underline!important;
  font-weight:900!important;
  word-break:break-all!important;
}


/* v29.0 promotion UI final */
.post-card[data-category="승급지원"] .settle-box,
.post-card[data-category="승급지원"] .settlement-box,
.post-card[data-category="승급지원"] .farming-settle,
.post-card[data-category="승급지원"] .farm-settle,
.post-card[data-category="승급지원"] .settle-panel,
.post-card[data-category="승급지원"] [data-section="settle"],
.post-card[data-category="승급지원"] .settle,
.post-card[data-category="승급지원"] .calc-box{
  display:none!important;
}

/* 승급지원 인원 배지 숨김 */
.post-card[data-category="승급지원"] .capacity-badge,
.post-card[data-category="승급지원"] .count-badge,
.post-card[data-category="승급지원"] .people-count,
.post-card[data-category="승급지원"] .member-count{
  display:none!important;
}

@media(max-width:980px){.app-shell{gap:12px!important}.side-stack{display:flex;flex-direction:column}}
@media(max-width:720px){
  .header{padding:16px 14px!important}
  .header h1{font-size:22px!important}
  .summary-grid{gap:8px!important}
  .summary-card{padding:12px!important}
  .card,.panel{padding:14px!important;border-radius:17px!important}
  .card h2{font-size:21px!important}
  .actions .btn{flex:1}
  .chatbox{height:260px!important}
  .auth-panel,.pending-panel{margin:36px auto!important}
}

@media(max-width:980px){.farm-form{grid-template-columns:1fr 1fr!important}}
@media(max-width:720px){.farm-form{grid-template-columns:1fr!important}}
.btn{letter-spacing:-.2px}
.panel,.card{backdrop-filter:saturate(1.1)}

@media(max-width:980px){
  .app-shell{grid-template-columns:1fr}
  .side-stack{position:static}
  .summary-grid{grid-template-columns:1fr 1fr 1fr}
  .chatbox{height:300px}
}

.choice-card{display:flex;align-items:center;gap:12px;background:#081126;border:1px solid #263a64;border-radius:15px;padding:14px;margin:10px 0;cursor:pointer}
.choice-card input{width:auto;accent-color:#19c46f;transform:scale(1.15)}
.choice-card span{font-size:17px;color:#fff}
.choice-card:has(input:checked){border-color:#19c46f;box-shadow:0 0 0 3px rgba(25,196,111,.14)}
.farm-dist{font-weight:900}
.closed .closed-tag,.closed-tag{font-size:13px}

.group-badge{margin-left:6px;padding:3px 7px;border-radius:999px;background:rgba(244,212,122,.16);border:1px solid rgba(244,212,122,.3);color:#ffe5a0;font-size:11px}
.remain{background:rgba(244,212,122,.12);border:1px solid rgba(244,212,122,.25);border-radius:999px;padding:3px 8px}
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


GATE_HTML = """
<section class='panel auth-panel'>
  <div class='auth-logo'>⚔</div>
  <h1>월하 · 연가 · 연희</h1>
  <p class='meta'>문파 파티모집 보드</p>
  <div class='auth-actions'>
    <a class='btn ok full' href='/login'>로그인</a>
    <a class='btn gray full' href='/register'>문파원 등록</a>
  </div>
</section>
"""


LOGIN_HTML = """
<section class='panel auth-panel'>
  <div class='auth-logo'>⚔</div>
  <h1>로그인</h1>
  <form method='post'>
    <label>계정명</label>
    <input name='account' value='{{form.get("account","")}}' placeholder='계정명'>
    <label>비밀번호</label>
    <input name='pin' type='password' inputmode='numeric' maxlength='6' placeholder='숫자 6자리'>
    <button class='ok full'>로그인</button>
  </form>
  {% if error %}<div class='notice'>{{error}}</div>{% endif %}
  <div class='toolbar auth-bottom'>
    <a class='btn gray' href='/register'>문파원 등록</a>
  </div>
</section>
"""


REGISTER_HTML = """
<section class='panel auth-panel'>
  <div class='auth-logo'>⚔</div>
  <h1>문파원 등록</h1>
  <form method='post'>
    <label>계정명</label>
    <input name='account' value='{{form.get("account","")}}' placeholder='로그인에 사용할 계정명'>
    <label>비밀번호 숫자 6자리</label>
    <input name='pin' type='password' inputmode='numeric' maxlength='6' placeholder='숫자 6자리'>
    <label>비밀번호 확인</label>
    <input name='pin_confirm' type='password' inputmode='numeric' maxlength='6' placeholder='다시 입력'>
    <label>대표 캐릭터명</label>
    <input name='char_name' value='{{form.get("char_name","")}}'>
    <label>직업</label>
    {{ job_select('job')|safe }}
    <label>관리자 비밀번호 <span class='meta'>(관리자만 입력)</span></label>
    <input name='admin_password' type='password' placeholder='일반 문파원은 비워두세요'>
    <button class='ok full'>승인 요청</button>
  </form>
  {% if error %}<div class='notice'>{{error}}</div>{% endif %}
  <div class='toolbar auth-bottom'><a class='btn gray' href='/login'>이미 계정이 있나요? 로그인</a></div>
</section>
"""


PENDING_HTML = """
<section class='panel pending-panel'>
  <div class='pending-icon'>⏳</div>
  <h1>승인 요청중</h1>
  <p class='meta'>관리자 승인 후 이용할 수 있습니다.</p>
  <div class='notice'>문파 관리자에게 가입 승인을 요청해 주세요.</div>
  <div class='toolbar pending-actions'>
    <a class='btn gray' href='/logout'>로그아웃</a><a class='btn gray nav-btn' href='/toast_test'>토스트테스트</a>
    <a class='btn gray' href='/login'>로그인</a>
  </div>
</section>
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
    return {"users": [], "posts": [], "global_chat": [], "alerts": [], "chrome_alerts": [], "settings": {"farm_items": ["해뼈","흑룡","묵룡","진룡"], "admin_password": os.environ.get("ADMIN_PASSWORD", "1234"), "notice": {"title":"공성 관련 협의 사항 안내","text":"📢 [공성 관련 협의 사항 안내]\n\n🔹 적용 대상 : 주작·현무·백호\n※ 청룡 공성은 제외됩니다.\n\n🔹 진행 방식\n모든 쪽문을 막은 상태로 진행\n\n──────────────────\n⚔️ 공성 인원 기준\n──────────────────\n※ 아래는 주작 기준 예시이며, 현무·백호도 동일하게 적용됩니다.\n\n✔ 문파당 20명 기준\n예시)\n상대 10개 문파 / 아군 8개 문파\n➡️ 아군 : 8 × 20명 = 160명\n➡️ 상대 : 문파 수와 관계없이 160명 참여\n\n📌 즉, 문파 수와 관계없이 양측 공성 인원을 동일하게 맞추는 것을 원칙으로 합니다.\n\n──────────────────\n📣 앞으로 공성이 다시 활발하게 진행될 예정입니다.\n문원 여러분의 적극적인 관심과 공성 참여를 부탁드립니다.\n\n월하연가연희 운영진 일동 드림.","updated_at":""}}}

def normalize(d):
    d.setdefault("users", [])
    d.setdefault("posts", [])
    d.setdefault("global_chat", [])
    d.setdefault("settings", {}).setdefault("farm_items", ["해뼈","흑룡","묵룡","진룡"])
    d.setdefault("settings", {}).setdefault("admin_password", os.environ.get("ADMIN_PASSWORD", "1234"))
    d.setdefault("settings", {}).setdefault("notice", {"title":"공성 관련 협의 사항 안내","text":"📢 [공성 관련 협의 사항 안내]\n\n🔹 적용 대상 : 주작·현무·백호\n※ 청룡 공성은 제외됩니다.\n\n🔹 진행 방식\n모든 쪽문을 막은 상태로 진행\n\n──────────────────\n⚔️ 공성 인원 기준\n──────────────────\n※ 아래는 주작 기준 예시이며, 현무·백호도 동일하게 적용됩니다.\n\n✔ 문파당 20명 기준\n예시)\n상대 10개 문파 / 아군 8개 문파\n➡️ 아군 : 8 × 20명 = 160명\n➡️ 상대 : 문파 수와 관계없이 160명 참여\n\n📌 즉, 문파 수와 관계없이 양측 공성 인원을 동일하게 맞추는 것을 원칙으로 합니다.\n\n──────────────────\n📣 앞으로 공성이 다시 활발하게 진행될 예정입니다.\n문원 여러분의 적극적인 관심과 공성 참여를 부탁드립니다.\n\n월하연가연희 운영진 일동 드림.","updated_at":""})
    for u in d["users"]:
        u.setdefault("id", nid())
        u.setdefault("account", "")
        u.setdefault("status", "pending")
        u.setdefault("role", "일반")
        u.setdefault("pin_hash", "")
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
        p.setdefault("closed_at", "")
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


def v28_9_reopen_promotion_posts(d):
    try:
        for p in d.get("posts", []):
            if p.get("category") == "승급지원":
                p["closed"] = False
                p["status"] = "모집중"
    except Exception:
        pass
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
    changed_cleanup = cleanup_closed_posts(d)
    changed_alert = farm_alert_tick(d)
    if changed_cleanup or changed_alert:
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
    return same_job_family(slot_job, char_job)

def job_family(job):
    j = str(job or "")
    warrior = ["전사","검객","검제","검황","검성"]
    thief = ["도적","자객","진검","귀검","태성"]
    mage = ["주술사","술사","현사","현인","현자"]
    priest = ["도사","도인","명인","진인","진선"]
    for fam in [warrior, thief, mage, priest]:
        if j in fam:
            return fam[0]
    return j

def same_job_family(a, b):
    return job_family(a) == job_family(b)

def approved_chars(u):
    if not u:
        return []
    if u.get("status") == "approved":
        return u.get("chars", [])
    return [c for c in u.get("chars", []) if c.get("status") == "approved"]

def post_datetime(p):
    # 파밍은 종료시간을 젠시간으로 봅니다. 예: 08:00~09:00이면 09:00 젠
    base_time = p.get("end_time") if p.get("category") == "파밍" and p.get("end_time") else p.get("start_time")
    try:
        return datetime.fromisoformat(f"{p.get('date') or today()}T{base_time or '00:00'}").replace(tzinfo=KST)
    except Exception:
        return now()




def normalize_existing_approved_members(d):
    changed = False
    for u in d.get("users", []):
        if u.get("status") == "approved":
            for c in u.get("chars", []):
                if c.get("status") != "approved":
                    c["status"] = "approved"
                    changed = True
    return changed

def get_notice(d):
    n = d.get("settings", {}).get("notice", {})
    if isinstance(n, str):
        return {"title": "문파 공지사항", "text": n, "updated_at": ""}
    return {
        "title": n.get("title") or "문파 공지사항",
        "text": n.get("text") or "",
        "updated_at": n.get("updated_at") or "",
    }

def notice_preview_text(text, limit=7):
    rows = [x for x in str(text or "").splitlines() if x.strip()]
    return "\n".join(rows[:limit])

def notice_is_new(d):
    try:
        updated = get_notice(d).get("updated_at", "")
        if not updated:
            return False
        ts = datetime.fromisoformat(updated).timestamp()
        return now().timestamp() - ts < 86400
    except Exception:
        return False

def countdown_target(p):
    try:
        return post_datetime(p).isoformat()
    except Exception:
        return now().isoformat()

def remaining_text(p):
    dt = post_datetime(p)
    diff = dt - now()
    minutes = int(diff.total_seconds() // 60)
    prefix = "젠 " if p.get("category") == "파밍" else ""
    if minutes > 0:
        h = minutes // 60
        m = minutes % 60
        if h > 0:
            return f"{prefix}{h}시간 {m}분 남음"
        return f"{prefix}{m}분 남음"
    if minutes > -60:
        return "젠시간" if p.get("category") == "파밍" else "진행중"
    return "종료"











def safe_quote_toast(msg):
    try:
        import urllib.parse
        return urllib.parse.quote(str(msg), safe="")
    except Exception:
        return str(msg).replace(" ", "%20")


def toast_redirect(url, msg):
    if not msg:
        return redirect(url)
    sep = "&" if "?" in url else "?"
    return redirect(url + sep + "toast=" + safe_quote_toast(msg))


def action_msg(p, text):
    return f"🔔 [{post_title(p)}] {text}"

def system_notify(d, msg):
    # v28.7: 화면 토스트 중복 방지를 위해 /api/alerts는 비워두고,
    # 크롬 알림 전용 저장소 chrome_alerts에만 저장합니다.
    try:
        item = {
            "id": nid(),
            "uid": "system",
            "name": "알림",
            "text": msg,
            "time": now().isoformat(timespec="seconds")
        }
        d.setdefault("chrome_alerts", []).append(item)
        d["chrome_alerts"] = d.get("chrome_alerts", [])[-80:]
        return True
    except Exception:
        return False


def actor_label(u):
    if not u:
        return "관리자"
    c = selected_char(u)
    if c:
        return f"{c.get('name')}({c.get('job')})"
    return u.get("account", "관리자")

def post_title(p):
    return p.get("place") or p.get("category") or "모집글"

def reopen_on_edit_change(p):
    if p and p.get("closed") and p.get("category") in ["사냥", "600퀘", "승급지원"]:
        p["closed"] = False
        p["closed_at"] = ""
        return True
    return False

def reopen_if_not_full(p):
    try:
        if p and p.get("closed") and p.get("category") in ["사냥", "600퀘", "승급지원"]:
            if joined_count(p) < max_count(p):
                p["closed"] = False
                p["closed_at"] = ""
                return True
    except Exception:
        pass
    return False

def refresh_post_status_after_member_change(d, p):
    if p.get("category") == "승급지원":
        # 승급지원은 파밍처럼 정원 제한 없이 계속 모집중 유지
        p["closed"] = False
        p["status"] = "모집중"
        return
    changed = reopen_if_not_full(p)
    try:
        if p and p.get("category") in ["사냥", "600퀘", "승급지원"] and not p.get("closed"):
            if max_count(p) > 0 and joined_count(p) >= max_count(p):
                p["closed"] = True
                p["closed_at"] = now().isoformat(timespec="seconds")
                changed = True
    except Exception:
        pass
    return changed

def auto_close_full_posts(d):
    changed = False
    for p in d.get("posts", []):
        if p.get("category") == "승급지원":
            continue
        if p.get("closed"):
            continue
        if p.get("category") in ["사냥", "600퀘", "승급지원"]:
            try:
                if max_count(p) > 0 and joined_count(p) >= max_count(p):
                    p["closed"] = True
                    p["closed_at"] = now().isoformat(timespec="seconds")
                    changed = True
            except Exception:
                pass
    return changed

def cleanup_closed_posts(d):
    changed = False
    keep = []
    for p in d.get("posts", []):
        if p.get("closed") and p.get("category") in ["사냥", "600퀘", "승급지원"]:
            closed_at = p.get("closed_at", "")
            try:
                ts = datetime.fromisoformat(closed_at).timestamp()
            except Exception:
                ts = 0
            if ts and now().timestamp() - ts >= 3600:
                changed = True
                continue
        keep.append(p)
    if changed:
        d["posts"] = keep
    return changed

def delete_after_text(p):
    if not p.get("closed") or p.get("category") == "파밍":
        return ""
    closed_at = p.get("closed_at", "")
    try:
        ts = datetime.fromisoformat(closed_at).timestamp()
    except Exception:
        return ""
    remain = int(3600 - (now().timestamp() - ts))
    if remain <= 0:
        return "곧 삭제"
    m = max(1, remain // 60)
    return f"{m}분 후 자동삭제"

def share_text(p):
    cat = p.get("category", "")
    place = p.get("place", "")
    channel = p.get("channel", "")
    start = show_time(p.get("start_time", ""))
    end = show_time(p.get("end_time", ""))
    writer = p.get("owner_label", "")
    if cat == "사냥":
        lines = [f"[사냥] {place}"]
    elif cat == "파밍":
        lines = [f"[파밍] {place}"]
    elif cat == "600퀘":
        lines = [f"[600퀘] {place}"]
    elif cat == "승급지원":
        lines = [f"[승급지원] {place}"]
    else:
        lines = [f"[{cat}] {place}"]
    if channel:
        lines.append(f"채널 {channel}")
    lines.append(f"{start} ~ {end}")
    if writer:
        lines.append(f"작성자 {writer}")
    if cat == "사냥":
        for s in p.get("slots", []):
            job = s.get("job", "")
            who = s.get("label") or s.get("external") or "모집중"
            lines.append(f"{job} - {who}")
    else:
        if p.get("participants"):
            lines.append("참여자")
            for a in p.get("participants", []):
                lines.append(f"- {a.get('label','')}")
        else:
            lines.append("참여자 모집중")
    memo = p.get("memo", "").strip()
    if memo:
        lines.append(f"메모 {memo}")
    return "\n".join(lines)


def participant_for_user(p, u):
    if not p or not u:
        return None
    for a in p.get("participants", []):
        if a.get("uid") == u.get("id"):
            return a
    return None

def can_join_post(p):
    if not p or p.get("closed"):
        return False
    cat = p.get("category")
    if cat in ["파밍", "승급지원"]:
        return True
    if cat == "600퀘":
        return len(p.get("participants", [])) < int(p.get("capacity", 10) or 10)
    if cat == "사냥":
        return any(not s.get("uid") and not s.get("external") for s in p.get("slots", []))
    return True


def join_block_reason(p):
    if p.get("category") == "파밍" and not can_join_post(p):
        return "젠 15분 전부터는 참여할 수 없습니다."
    return ""



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
                msg = f"🔔 {p.get('place','파밍')} 젠 {target}분 전입니다. 채널 {p.get('channel','')} · {show_time(p.get('end_time') or p.get('start_time'))}"
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


def money_text(value):
    try:
        n = int(re.sub(r"[^0-9]", "", str(value or "0")))
    except Exception:
        n = 0
    if n <= 0:
        return "0전"
    if n >= 100000000:
        eok = n // 100000000
        rest = n % 100000000
        man = rest // 10000
        return f"{eok}억 {man}만전" if man else f"{eok}억전"
    if n >= 10000:
        return f"{n//10000}만전"
    return f"{n}전"

def farm_money_summary(p):
    dist = farm_distribution(p)
    early_n = len(p.get("early_ids", []))
    late_n = len(p.get("late_ids", []))
    return {
        "sale": money_text(dist.get("amount", 0)),
        "early_each": money_text(dist.get("early_each", 0)),
        "late_each": money_text(dist.get("late_each", 0)),
        "early_count": early_n,
        "late_count": late_n,
    }


def participant_group_label(p, part):
    key = part.get("char_id") or part.get("uid")
    if key in p.get("early_ids", []):
        return "선집합"
    if key in p.get("late_ids", []):
        return "후집합"
    return ""

def farm_alert_status(d):
    alerts = []
    for p in d.get("posts", []):
        if p.get("category") != "파밍" or p.get("closed"):
            continue
        left_text = remaining_text(p)
        dt = post_datetime(p)
        left = int((dt - now()).total_seconds() // 60)
        alerts.append({
            "id": p.get("id"),
            "place": p.get("place", "파밍"),
            "channel": p.get("channel", ""),
            "left": left,
            "text": left_text
        })
    return alerts



def can_manage_post(u, p):
    if not u or not p:
        return False
    if p.get("category") == "파밍":
        return is_admin(u)
    return p.get("owner_uid") == u.get("id") or is_admin(u)





def valid_pin(pin):
    return bool(re.fullmatch(r"\d{6}", str(pin or "")))

def pin_hash(pin):
    return hashlib.sha256(str(pin).encode("utf-8")).hexdigest()

def verify_pin(user, pin):
    return user.get("pin_hash") == pin_hash(pin)

def account_exists(d, account):
    target = str(account or "").strip()
    return any(str(u.get("account","")).strip() == target for u in d.get("users", []))

def char_name_exists(d, name, exclude_uid=""):
    target = str(name or "").strip()
    if not target:
        return False
    for u in d.get("users", []):
        if exclude_uid and u.get("id") == exclude_uid:
            continue
        for c in u.get("chars", []):
            if str(c.get("name","")).strip() == target:
                return True
    return False

def admin_password_ok(d, value):
    pw = str(d.get("settings", {}).get("admin_password", "1234"))
    return bool(value and str(value).strip() == pw)

def has_any_admin(d):
    return any(x.get("status") == "approved" and x.get("role") in ["관리자","부문파장","문파장","최고관리자"] for x in d.get("users", []))




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

BASE_HEAD = """<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{{ title }}</title><style>{{ css }}
/* v31.7 inline layout hard fix */
html, body{
  overflow-x:auto!important;
}

.quickbar.recruit-head{
  width:820px!important;
  max-width:820px!important;
  box-sizing:border-box!important;
}

.post-grid-v317 > .empty{
  grid-column:1 / -1!important;
  width:820px!important;
  max-width:820px!important;
}

/* 기존 모바일 전환 무력화 */
@media(max-width:980px){
  .wrap{
    max-width:1220px!important;
    width:1220px!important;
    min-width:1220px!important;
  }
  .app-shell{
    display:grid!important;
    grid-template-columns:820px 360px!important;
    width:1196px!important;
    min-width:1196px!important;
  }
  .left-stack{
    display:block!important;
    width:820px!important;
    min-width:820px!important;
  }
  .side-stack{
    grid-column:2!important;
    width:360px!important;
    min-width:360px!important;
    max-width:360px!important;
    position:sticky!important;
    top:12px!important;
  }
  .post-grid-v317{
    display:grid!important;
    grid-template-columns:403px 403px!important;
    width:820px!important;
    min-width:820px!important;
  }
  .post-grid-v317 > .card{
    width:403px!important;
    min-width:403px!important;
    max-width:403px!important;
  }
}

/* 카드 내부 compact */
.post-grid-v317 > .card{
  padding:14px!important;
  border-radius:18px!important;
}

.post-grid-v317 > .card h2{
  font-size:21px!important;
  margin:8px 0!important;
}

.post-grid-v317 > .card .meta{
  font-size:12px!important;
  line-height:1.45!important;
}

.post-grid-v317 > .card .slot{
  display:grid!important;
  grid-template-columns:minmax(0,1fr) auto!important;
  gap:8px!important;
  align-items:center!important;
  padding:10px 11px!important;
  margin:8px 0!important;
  width:100%!important;
  box-sizing:border-box!important;
}

.post-grid-v317 > .card .slot > div:first-child{
  min-width:0!important;
  overflow:hidden!important;
}

.post-grid-v317 > .card .slot .toolbar{
  display:flex!important;
  justify-content:flex-end!important;
  flex-wrap:nowrap!important;
  gap:6px!important;
  min-width:max-content!important;
}

.post-grid-v317 > .card .slot .btn,
.post-grid-v317 > .card .slot button{
  padding:8px 10px!important;
  font-size:13px!important;
  white-space:nowrap!important;
}

.post-grid-v317 > .card .actions{
  display:flex!important;
  gap:7px!important;
  flex-wrap:wrap!important;
  align-items:center!important;
  margin-top:10px!important;
}

.post-grid-v317 > .card .actions .btn{
  padding:9px 12px!important;
  font-size:13px!important;
}

.side-stack .chatbox{
  height:360px!important;
}

/* 승급지원 숨김 유지 */
.card[data-category="승급지원"] .settle-box,
.card[data-category="승급지원"] .settlement-box,
.card[data-category="승급지원"] .farming-settle,
.card[data-category="승급지원"] .farm-settle,
.card[data-category="승급지원"] .settle-panel,
.card[data-category="승급지원"] [data-section="settle"],
.card[data-category="승급지원"] .settle,
.card[data-category="승급지원"] .calc-box,
.card[data-category="승급지원"] .capacity-badge,
.card[data-category="승급지원"] .count-badge,
.card[data-category="승급지원"] .people-count,
.card[data-category="승급지원"] .member-count,
.card[data-category="승급지원"] .cap-badge{
  display:none!important;
}

</style></head><body><div class='wrap' style='max-width:1220px!important;width:1220px!important;min-width:1220px!important;margin:0 auto!important;padding:16px!important;box-sizing:border-box!important;'>"""
BASE_TAIL = """</div><script>
let slotN=0;
function qs(s){return document.querySelector(s)}
function fmt(v){v=(v||'').replace(/[^0-9]/g,'').slice(0,4);return v.length>=3?v.slice(0,v.length-2)+':'+v.slice(v.length-2):v}
function addSlot(){let j=(qs('#slotJob')||document.querySelector("select[name='slotJob']"))?.value,b=qs('#slots');if(!j||!b)return;let d=document.createElement('div');d.className='slot';d.innerHTML='<b>'+j+'</b><input type=hidden name=slot_job_'+slotN+' value=\"'+j+'\"><button type=button class=\"danger mini\" onclick=\"this.parentElement.remove()\">삭제</button>';b.appendChild(d);slotN++}
function mode(){let c=qs('#cat')?.value;document.querySelectorAll('.place').forEach(x=>x.style.display=x.dataset.cat==c?'':'none');let s=qs('#slotsBox');if(s)s.style.display=c=='사냥'?'':'none'}
document.addEventListener('DOMContentLoaded',()=>{let c=qs('#cat');if(c){c.onchange=mode;mode()}document.querySelectorAll('input[name=start_time],input[name=end_time]').forEach(i=>i.oninput=()=>i.value=fmt(i.value))});






async function copyPostText(btn){
  const pid = btn?.dataset?.pid || '';
  let text = btn?.dataset?.share || '';
  try{
    if(pid){
      const r = await fetch('/api/copy_text/' + encodeURIComponent(pid), {cache:'no-store'});
      text = await r.text();
    }
  }catch(e){}
  if(!text)return;
  try{
    await navigator.clipboard.writeText(text);
    showToast('글 내용을 복사했습니다. 카톡에 붙여넣기 하세요');
  }catch(e){
    const box=document.createElement('textarea');
    box.value=text;
    box.style.position='fixed';
    box.style.left='-9999px';
    document.body.appendChild(box);
    box.focus();
    box.select();
    try{
      document.execCommand('copy');
      showToast('글 내용을 복사했습니다. 카톡에 붙여넣기 하세요');
    }catch(err){
      alert(text);
    }
    document.body.removeChild(box);
  }
}

function formatBossRemain(totalSeconds){
  totalSeconds=Math.max(0, Math.floor(totalSeconds));
  const h=Math.floor(totalSeconds/3600);
  const m=Math.floor((totalSeconds%3600)/60);
  const s=totalSeconds%60;
  const pad=n=>String(n).padStart(2,'0');
  if(h>0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}`;
}












function showToast(msg){
  let wrap=document.getElementById('toastWrap');
  if(!wrap){
    wrap=document.createElement('div');
    wrap.id='toastWrap';
    document.body.appendChild(wrap);
  }
  const el=document.createElement('div');
  el.className='toast';
  el.textContent=msg;
  wrap.appendChild(el);
  setTimeout(()=>el.classList.add('show'),20);
  setTimeout(()=>{el.classList.remove('show');setTimeout(()=>el.remove(),300);},4500);
}
function getSeenAlertIds(){
  try{return new Set(JSON.parse(localStorage.getItem('seenAlertIds')||'[]'));}catch(e){return new Set();}
}
function saveSeenAlertIds(set){
  try{localStorage.setItem('seenAlertIds', JSON.stringify(Array.from(set).slice(-120)));}catch(e){}
}
function showUrlToast(){
  const params=new URLSearchParams(location.search);
  const msg=params.get('toast');
  if(msg){
    setTimeout(()=>showToast(msg),200);
    params.delete('toast');
    const qs=params.toString();
    history.replaceState(null,'',location.pathname+(qs?'?'+qs:''));
  }
}
async function pollSystemAlerts(){
  try{
    const r=await fetch('/api/alerts?_=' + Date.now(), {cache:'no-store'});
    const data=await r.json();
    const alerts=data.alerts||[];
    const seen=getSeenAlertIds();
    const nowMs=Date.now();
    alerts.forEach(a=>{
      const id=String(a.id||'');
      if(!id || seen.has(id)) return;
      seen.add(id);
      const t=Date.parse(a.time||'');
      const recent=Number.isNaN(t) ? true : (nowMs-t<18000);
      if(recent && a.text) showToast(a.text);
    });
    saveSeenAlertIds(seen);
  }catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{
  showUrlToast();
  pollSystemAlerts();
  setInterval(pollSystemAlerts,3000);
});

function toggleClanNotice(){
  const card=document.querySelector('.clan-notice-card');
  const btn=document.getElementById('clanNoticeBtn');
  if(!card)return;
  card.classList.toggle('expanded');
  if(btn)btn.textContent=card.classList.contains('expanded')?'접기':'더보기';
}

function updateBossTimers(){
  const nowMs=Date.now();
  document.querySelectorAll('.boss-timer').forEach(row=>{
    const target=row.dataset.target;
    const el=row.querySelector('.schedule-countdown');
    if(!target||!el)return;
    const targetMs=Date.parse(target);
    if(Number.isNaN(targetMs))return;
    const left=Math.floor((targetMs-nowMs)/1000);
    row.classList.remove('timer-yellow','timer-orange','timer-red','timer-done');
    el.classList.remove('timer-yellow','timer-orange','timer-red','timer-done');
    if(left<=0){
      el.textContent='젠시간';
      row.classList.add('timer-done');
      el.classList.add('timer-done');
    }else{
      el.textContent=formatBossRemain(left);
      if(left<=300){row.classList.add('timer-red');el.classList.add('timer-red');}
      else if(left<=900){row.classList.add('timer-orange');el.classList.add('timer-orange');}
      else if(left<=1800){row.classList.add('timer-yellow');el.classList.add('timer-yellow');}
    }
  });
}
document.addEventListener('DOMContentLoaded',()=>{updateBossTimers();setInterval(updateBossTimers,1000);});

function showToast(message){
  try{
    let t=document.getElementById('appToast');
    if(!t){t=document.createElement('div');t.id='appToast';t.className='toast';document.body.appendChild(t);}
    t.textContent=message;
    t.classList.add('show');
    setTimeout(()=>t.classList.remove('show'),1800);
  }catch(e){}
}
function bindActionToasts(){
  document.querySelectorAll("a[href*='join_slot'],a[href*='choose_participant'],a[href*='leave_'],a[href*='close/']").forEach(a=>{
    if(a.dataset.toastBound)return;
    a.dataset.toastBound='1';
    a.addEventListener('click',()=>{
      const txt=(a.textContent||'').trim();
      if(txt.includes('참여')) sessionStorage.setItem('toast','참여가 반영되었습니다');
      else if(txt.includes('취소')) sessionStorage.setItem('toast','참여가 취소되었습니다');
      else if(txt.includes('완료')) sessionStorage.setItem('toast','모집이 마감되었습니다');
    });
  });
  const msg=sessionStorage.getItem('toast');
  if(msg){sessionStorage.removeItem('toast');setTimeout(()=>showToast(msg),180);}
}
document.addEventListener('DOMContentLoaded', bindActionToasts);

function isUserEditing(){
  const a=document.activeElement;
  if(!a)return false;
  const tag=(a.tagName||'').toLowerCase();
  if(tag==='input'||tag==='textarea'||tag==='select')return true;
  if(a.isContentEditable)return true;
  const modal=document.querySelector('.modal-backdrop.show');
  if(modal)return true;
  return false;
}
function bindLivePageRefresh(){
  // v26.16: 전체 페이지 자동 새로고침 중지. 채팅/알림은 AJAX만 사용.
}
document.addEventListener('DOMContentLoaded', bindLivePageRefresh);


function keepChatScrollStable(box, renderFn){
  if(!box){ renderFn(); return; }
  const nearBottom = (box.scrollHeight - box.scrollTop - box.clientHeight) < 80;
  const oldTop = box.scrollTop;
  renderFn();
  if(nearBottom) box.scrollTop = box.scrollHeight;
  else box.scrollTop = oldTop;
}

function escapeHtml(s){
  return String(s||'').replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
function isChatNearBottom(box){
  return !box || (box.scrollHeight - box.scrollTop - box.clientHeight < 80);
}
async function loadGlobalChat(keepScroll=true){
  const box=document.getElementById('globalChatBox');
  if(!box)return;
  const nearBottom=isChatNearBottom(box);
  const oldTop=box.scrollTop;
  try{
    const r=await fetch('/api/global_chat');
    const j=await r.json();
    if(!j.ok)return;
    box.innerHTML=(j.messages||[]).map(m=>`<div class="chatmsg"><b>${escapeHtml(m.name)}</b><br>${escapeHtml(m.text)}<br><span class="meta">${escapeHtml(m.time)}</span></div>`).join('') || '<div class="empty">메시지 없음</div>';
    if(nearBottom) box.scrollTop=box.scrollHeight;
    else if(keepScroll) box.scrollTop=oldTop;
  }catch(e){}
}
function bindGlobalChat(){
  const form=document.getElementById('globalChatForm');
  const input=document.getElementById('globalChatInput');
  const box=document.getElementById('globalChatBox');
  if(box) box.scrollTop=box.scrollHeight;
  if(form && input){
    form.addEventListener('submit', async (e)=>{
      e.preventDefault();
      const text=input.value.trim();
      if(!text)return;
      const fd=new FormData();
      fd.append('text', text);
      input.value='';
      await fetch('/api/global_chat', {method:'POST', body:fd});
      await loadGlobalChat(false);
      if(box) box.scrollTop=box.scrollHeight;
    });
  }
  setInterval(()=>loadGlobalChat(true), 5000);
}
document.addEventListener('DOMContentLoaded', bindGlobalChat);

let __farmVoiceSent = {};

function openSettingsModal(){
  const m=document.getElementById('settingsModal');
  if(m){loadAlarmSettings();m.classList.add('show');}
}
function hideSettingsModal(){
  const m=document.getElementById('settingsModal');
  if(m)m.classList.remove('show');
}
function closeSettingsModal(e){
  if(e && e.target && e.target.id==='settingsModal') hideSettingsModal();
}

function getAlarmSettings(){
  return {
    voice: localStorage.getItem('farmVoiceEnabled') !== '0',
    volume: Math.max(0, Math.min(1, Number(localStorage.getItem('farmVoiceVolume') || '1')))
  };
}
function saveAlarmSettings(){
  const toggle=document.getElementById('alarmVoiceToggle');
  const volume=document.getElementById('alarmVolume');
  const text=document.getElementById('alarmVolumeText');
  if(toggle) localStorage.setItem('farmVoiceEnabled', toggle.checked ? '1':'0');
  if(volume){
    localStorage.setItem('farmVoiceVolume', String(Number(volume.value)/100));
    if(text) text.textContent=volume.value+'%';
  }
}
function loadAlarmSettings(){
  const s=getAlarmSettings();
  const toggle=document.getElementById('alarmVoiceToggle');
  const volume=document.getElementById('alarmVolume');
  const text=document.getElementById('alarmVolumeText');
  if(toggle) toggle.checked=s.voice;
  if(volume) volume.value=Math.round(s.volume*100);
  if(text) text.textContent=Math.round(s.volume*100)+'%';
  if(toggle) toggle.addEventListener('change', saveAlarmSettings);
  if(volume) volume.addEventListener('input', saveAlarmSettings);
}
function speakFarmAlarm(text){
  try{
    const s=getAlarmSettings();
    if(!s.voice) return;
    if(!('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang='ko-KR';
    u.rate=1;
    u.volume=s.volume;
    speechSynthesis.speak(u);
  }catch(e){}
}
function testFarmVoice(){
  speakFarmAlarm('해골왕 젠 30분 전입니다');
}
async function checkFarmAlarms(){
  try{
    const r = await fetch('/api/farm_alerts');
    const j = await r.json();
    (j.alerts||[]).forEach(a=>{
      [30,15,5].forEach(t=>{
        if(a.left<=t && a.left>=t-1){
          const key=a.id+'-'+t;
          const count=Number(__farmVoiceSent[key]||0);
          if(count<2){
            __farmVoiceSent[key]=count+1;
            speakFarmAlarm(a.place+' 젠 '+t+'분 전입니다');
            if(count===0){
              setTimeout(()=>{ 
                if(Number(__farmVoiceSent[key]||0)<2){
                  __farmVoiceSent[key]=2;
                  speakFarmAlarm(a.place+' 젠 '+t+'분 전입니다');
                }
              }, 2500);
            }
          }
        }
      });
    });
  }catch(e){}
}
setInterval(checkFarmAlarms, 60000);
document.addEventListener('DOMContentLoaded', ()=>{loadAlarmSettings();checkFarmAlarms();});


window.addEventListener('beforeunload',()=>{try{sessionStorage.setItem('liveScrollY',String(window.scrollY||0));}catch(e){}});
document.addEventListener('DOMContentLoaded',()=>{try{const y=sessionStorage.getItem('liveScrollY'); if(y){window.scrollTo(0,Number(y)); sessionStorage.removeItem('liveScrollY');}}catch(e){}});


/* v27.1 toast test + reliable popup */
window.BaramToast = function(msg){
  let wrap = document.getElementById('toastWrap');
  if(!wrap){
    wrap = document.createElement('div');
    wrap.id = 'toastWrap';
    document.body.appendChild(wrap);
  }
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg || '🔔 토스트 알림 테스트입니다.';
  wrap.appendChild(el);
  setTimeout(()=>el.classList.add('show'), 20);
  setTimeout(()=>{
    el.classList.remove('show');
    setTimeout(()=>el.remove(), 320);
  }, 4500);
};
window.showToast = window.BaramToast;

function showUrlToastV271(){
  try{
    const params = new URLSearchParams(location.search);
    const msg = params.get('toast');
    if(msg){
      setTimeout(()=>window.BaramToast(msg), 250);
      params.delete('toast');
      const qs = params.toString();
      history.replaceState(null,'',location.pathname + (qs ? '?' + qs : ''));
    }
  }catch(e){}
}
document.addEventListener('DOMContentLoaded', showUrlToastV271);

async function testToastFromSettings(){
  window.BaramToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  try{ await fetch('/api/test_toast?_=' + Date.now(), {cache:'no-store'}); }catch(e){}
}


/* v28.3 final settings choose notify */
(function(){
  function makeToast(msg){
    var wrap = document.getElementById('toastWrap');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = 'toastWrap';
      document.body.appendChild(wrap);
    }
    var el = document.createElement('div');
    el.className = 'toast v28-toast';
    el.textContent = msg || '🔔 토스트 알림입니다.';
    wrap.appendChild(el);
    setTimeout(function(){ el.classList.add('show'); }, 20);
    setTimeout(function(){
      el.classList.remove('show');
      setTimeout(function(){ if(el && el.parentNode) el.parentNode.removeChild(el); }, 320);
    }, 4500);
  }
  window.BaramToast = makeToast;
  window.showToast = makeToast;
  window.testToastFromSettings = function(){
    makeToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  };
  window.requestChromeNotifyPermission = async function(){
    if(!('Notification' in window)){
      makeToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    var result = await Notification.requestPermission();
    if(result === 'granted'){
      localStorage.setItem('chromeNotifyEnabled','1');
      new Notification('월하 · 연가 · 연희', {body:'크롬 알림이 켜졌습니다.'});
      makeToast('🔔 크롬 알림이 켜졌습니다.');
    }else{
      localStorage.setItem('chromeNotifyEnabled','0');
      makeToast('크롬 알림 권한이 허용되지 않았습니다.');
    }
  };
  window.sendChromeNotify = function(msg){
    try{
      if(!('Notification' in window)) return;
      if(localStorage.getItem('chromeNotifyEnabled') !== '1') return;
      if(Notification.permission !== 'granted') return;
      new Notification('월하 · 연가 · 연희', {body: msg || '새 알림이 있습니다.'});
    }catch(e){}
  };
  window.testChromeNotifyFromSettings = function(){
    if(!('Notification' in window)){
      makeToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    if(Notification.permission !== 'granted'){
      window.requestChromeNotifyPermission();
      return;
    }
    localStorage.setItem('chromeNotifyEnabled','1');
    new Notification('월하 · 연가 · 연희', {body:'크롬 알림 테스트입니다.'});
    makeToast('🔔 크롬 알림 테스트를 보냈습니다.');
  };
  function showUrlToast(){
    try{
      var params = new URLSearchParams(window.location.search);
      var msg = params.get('toast');
      if(msg){
        setTimeout(function(){
          makeToast(msg);
          window.sendChromeNotify(msg);
        }, 250);
        params.delete('toast');
        var qs = params.toString();
        history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
      }
    }catch(e){}
  }
  async function pollAlerts(){
    try{
      var r = await fetch('/api/alerts?_=' + Date.now(), {cache:'no-store'});
      var data = await r.json();
      var alerts = data.alerts || [];
      var seen = {};
      try{ seen = JSON.parse(localStorage.getItem('v283SeenAlerts') || '{}'); }catch(e){ seen = {}; }
      var now = Date.now();
      alerts.forEach(function(a){
        var id = String(a.id || '');
        if(!id || seen[id]) return;
        seen[id] = 1;
        var t = Date.parse(a.time || '');
        var recent = isNaN(t) ? true : (now - t < 20000);
        if(recent && a.text){
          makeToast(a.text);
          window.sendChromeNotify(a.text);
        }
      });
      var keys = Object.keys(seen).slice(-150);
      var slim = {};
      keys.forEach(function(k){ slim[k] = 1; });
      localStorage.setItem('v283SeenAlerts', JSON.stringify(slim));
    }catch(e){}
  }
  document.addEventListener('DOMContentLoaded', function(){
    showUrlToast();
    pollAlerts();
    setInterval(pollAlerts, 3000);
  });
})();


/* v28.4 toast duplicate guard - final override */
(function(){
  var lastToastMap = {};
  var activeTexts = {};

  function normalizeMsg(msg){
    return String(msg || '').replace(/\s+/g, ' ').trim();
  }

  function makeSingleToast(msg){
    msg = msg || '🔔 알림입니다.';
    var key = normalizeMsg(msg);
    var now = Date.now();

    if(lastToastMap[key] && now - lastToastMap[key] < 7000){
      return;
    }
    if(activeTexts[key]){
      return;
    }

    lastToastMap[key] = now;
    activeTexts[key] = 1;

    var wrap = document.getElementById('toastWrap');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = 'toastWrap';
      document.body.appendChild(wrap);
    }

    var el = document.createElement('div');
    el.className = 'toast v28-toast';
    el.textContent = msg;
    wrap.appendChild(el);

    setTimeout(function(){ el.classList.add('show'); }, 20);
    setTimeout(function(){
      el.classList.remove('show');
      setTimeout(function(){
        if(el && el.parentNode) el.parentNode.removeChild(el);
        delete activeTexts[key];
      }, 320);
    }, 4500);
  }

  window.BaramToast = makeSingleToast;
  window.showToast = makeSingleToast;

  window.testToastFromSettings = function(){
    makeSingleToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  };

  var oldSendChrome = window.sendChromeNotify;
  window.sendChromeNotify = function(msg){
    try{
      var key = 'chrome:' + normalizeMsg(msg);
      var now = Date.now();
      if(lastToastMap[key] && now - lastToastMap[key] < 7000) return;
      lastToastMap[key] = now;
      if(typeof oldSendChrome === 'function'){
        oldSendChrome(msg);
        return;
      }
      if(!('Notification' in window)) return;
      if(localStorage.getItem('chromeNotifyEnabled') !== '1') return;
      if(Notification.permission !== 'granted') return;
      new Notification('월하 · 연가 · 연희', {body: msg || '새 알림이 있습니다.'});
    }catch(e){}
  };

  function handleUrlToastOnce(){
    try{
      var params = new URLSearchParams(location.search);
      var msg = params.get('toast');
      if(msg){
        setTimeout(function(){
          makeSingleToast(msg);
          if(window.sendChromeNotify) window.sendChromeNotify(msg);
        }, 250);
        params.delete('toast');
        var qs = params.toString();
        history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
      }
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', handleUrlToastOnce);
})();


/* v28.5 single toast final guard */
(function(){
  var shown = {};
  function keyOf(msg){ return String(msg || '').replace(/\s+/g, ' ').trim(); }

  function makeOnlyOneToast(msg){
    msg = msg || '🔔 알림입니다.';
    var key = keyOf(msg);
    var now = Date.now();
    if(shown[key] && now - shown[key] < 10000) return;
    shown[key] = now;

    var wrap = document.getElementById('toastWrap');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = 'toastWrap';
      document.body.appendChild(wrap);
    }

    // 같은 문구가 이미 화면에 떠 있으면 추가하지 않음
    var nodes = wrap.querySelectorAll('.toast');
    for(var i=0;i<nodes.length;i++){
      if(keyOf(nodes[i].textContent) === key) return;
    }

    var el = document.createElement('div');
    el.className = 'toast v28-toast';
    el.textContent = msg;
    wrap.appendChild(el);

    setTimeout(function(){ el.classList.add('show'); }, 20);
    setTimeout(function(){
      el.classList.remove('show');
      setTimeout(function(){ if(el && el.parentNode) el.parentNode.removeChild(el); }, 320);
    }, 4500);
  }

  // 기존 함수 전부 마지막에 덮어쓰기
  window.BaramToast = makeOnlyOneToast;
  window.showToast = makeOnlyOneToast;

  window.testToastFromSettings = function(){
    makeOnlyOneToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  };

  window.sendChromeNotify = function(msg){
    try{
      if(!('Notification' in window)) return;
      if(localStorage.getItem('chromeNotifyEnabled') !== '1') return;
      if(Notification.permission !== 'granted') return;
      var key = 'chrome:' + keyOf(msg);
      var now = Date.now();
      if(shown[key] && now - shown[key] < 10000) return;
      shown[key] = now;
      new Notification('월하 · 연가 · 연희', {body: msg || '새 알림이 있습니다.'});
    }catch(e){}
  };

  window.requestChromeNotifyPermission = async function(){
    if(!('Notification' in window)){
      makeOnlyOneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    var result = await Notification.requestPermission();
    if(result === 'granted'){
      localStorage.setItem('chromeNotifyEnabled','1');
      new Notification('월하 · 연가 · 연희', {body:'크롬 알림이 켜졌습니다.'});
      makeOnlyOneToast('🔔 크롬 알림이 켜졌습니다.');
    }else{
      localStorage.setItem('chromeNotifyEnabled','0');
      makeOnlyOneToast('크롬 알림 권한이 허용되지 않았습니다.');
    }
  };

  window.testChromeNotifyFromSettings = function(){
    if(!('Notification' in window)){
      makeOnlyOneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    if(Notification.permission !== 'granted'){
      window.requestChromeNotifyPermission();
      return;
    }
    localStorage.setItem('chromeNotifyEnabled','1');
    window.sendChromeNotify('크롬 알림 테스트입니다.');
    makeOnlyOneToast('🔔 크롬 알림 테스트를 보냈습니다.');
  };

  function handleUrlToast(){
    try{
      var params = new URLSearchParams(location.search);
      var msg = params.get('toast');
      if(msg){
        setTimeout(function(){
          makeOnlyOneToast(msg);
          window.sendChromeNotify(msg);
        }, 250);
        params.delete('toast');
        var qs = params.toString();
        history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
      }
    }catch(e){}
  }

  // 다른 사람 알림용: 화면 토스트는 절대 띄우지 않고 크롬 알림만 보냄
  async function chromeOnlyPoll(){
    try{
      var r = await fetch('/api/alerts?_=' + Date.now(), {cache:'no-store'});
      var data = await r.json();
      var alerts = data.alerts || [];
      var seen = {};
      try{ seen = JSON.parse(localStorage.getItem('v285SeenAlerts') || '{}'); }catch(e){ seen = {}; }
      var now = Date.now();
      alerts.forEach(function(a){
        var id = String(a.id || '');
        if(!id || seen[id]) return;
        seen[id] = 1;
        var t = Date.parse(a.time || '');
        var recent = isNaN(t) ? true : (now - t < 20000);
        if(recent && a.text){
          window.sendChromeNotify(a.text);
        }
      });
      var keys = Object.keys(seen).slice(-150);
      var slim = {};
      keys.forEach(function(k){ slim[k] = 1; });
      localStorage.setItem('v285SeenAlerts', JSON.stringify(slim));
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', function(){
    handleUrlToast();
    chromeOnlyPoll();
    setInterval(chromeOnlyPoll, 3000);
  });
})();


/* v28.6 true single toast + clear old alert stores */
(function(){
  try{
    localStorage.removeItem('v28SeenAlerts');
    localStorage.removeItem('v281SeenAlerts');
    localStorage.removeItem('v283SeenAlerts');
    localStorage.removeItem('v285SeenAlerts');
    localStorage.removeItem('seenAlertIds');
    localStorage.removeItem('lastAlertId');
  }catch(e){}

  var shownMap = {};
  function keyOf(msg){ return String(msg || '').replace(/\s+/g, ' ').trim(); }

  function oneToast(msg){
    msg = msg || '🔔 알림입니다.';
    var key = keyOf(msg);
    var now = Date.now();
    if(shownMap[key] && now - shownMap[key] < 12000) return;
    shownMap[key] = now;

    var wrap = document.getElementById('toastWrap');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = 'toastWrap';
      document.body.appendChild(wrap);
    }
    var nodes = wrap.querySelectorAll('.toast');
    for(var i=0;i<nodes.length;i++){
      if(keyOf(nodes[i].textContent) === key) return;
    }

    var el = document.createElement('div');
    el.className = 'toast v28-toast';
    el.textContent = msg;
    wrap.appendChild(el);
    setTimeout(function(){ el.classList.add('show'); }, 20);
    setTimeout(function(){
      el.classList.remove('show');
      setTimeout(function(){ if(el && el.parentNode) el.parentNode.removeChild(el); }, 320);
    }, 4500);
  }

  window.BaramToast = oneToast;
  window.showToast = oneToast;

  window.testToastFromSettings = function(){
    oneToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  };

  window.sendChromeNotify = function(msg){
    try{
      if(!('Notification' in window)) return;
      if(localStorage.getItem('chromeNotifyEnabled') !== '1') return;
      if(Notification.permission !== 'granted') return;
      var key = 'chrome:' + keyOf(msg);
      var now = Date.now();
      if(shownMap[key] && now - shownMap[key] < 12000) return;
      shownMap[key] = now;
      new Notification('월하 · 연가 · 연희', {body: msg || '새 알림이 있습니다.'});
    }catch(e){}
  };

  window.requestChromeNotifyPermission = async function(){
    if(!('Notification' in window)){
      oneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    var result = await Notification.requestPermission();
    if(result === 'granted'){
      localStorage.setItem('chromeNotifyEnabled','1');
      new Notification('월하 · 연가 · 연희', {body:'크롬 알림이 켜졌습니다.'});
      oneToast('🔔 크롬 알림이 켜졌습니다.');
    }else{
      localStorage.setItem('chromeNotifyEnabled','0');
      oneToast('크롬 알림 권한이 허용되지 않았습니다.');
    }
  };

  window.testChromeNotifyFromSettings = function(){
    if(!('Notification' in window)){
      oneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    if(Notification.permission !== 'granted'){
      window.requestChromeNotifyPermission();
      return;
    }
    localStorage.setItem('chromeNotifyEnabled','1');
    window.sendChromeNotify('크롬 알림 테스트입니다.');
    oneToast('🔔 크롬 알림 테스트를 보냈습니다.');
  };

  function handleUrlToastOnly(){
    try{
      var params = new URLSearchParams(location.search);
      var msg = params.get('toast');
      if(msg){
        setTimeout(function(){
          oneToast(msg);
          window.sendChromeNotify(msg);
        }, 250);
        params.delete('toast');
        var qs = params.toString();
        history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
      }
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', handleUrlToastOnly);
})();


/* v28.7 split chrome alerts final */
(function(){
  try{
    localStorage.removeItem('v28SeenAlerts');
    localStorage.removeItem('v281SeenAlerts');
    localStorage.removeItem('v283SeenAlerts');
    localStorage.removeItem('v285SeenAlerts');
    localStorage.removeItem('seenAlertIds');
    localStorage.removeItem('lastAlertId');
  }catch(e){}

  var shown = {};
  function keyOf(msg){ return String(msg || '').replace(/\s+/g, ' ').trim(); }

  function oneToast(msg){
    msg = msg || '🔔 알림입니다.';
    var key = keyOf(msg);
    var now = Date.now();
    if(shown[key] && now - shown[key] < 12000) return;
    shown[key] = now;

    var wrap = document.getElementById('toastWrap');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.id = 'toastWrap';
      document.body.appendChild(wrap);
    }
    var nodes = wrap.querySelectorAll('.toast');
    for(var i=0;i<nodes.length;i++){
      if(keyOf(nodes[i].textContent) === key) return;
    }

    var el = document.createElement('div');
    el.className = 'toast v28-toast';
    el.textContent = msg;
    wrap.appendChild(el);
    setTimeout(function(){ el.classList.add('show'); }, 20);
    setTimeout(function(){
      el.classList.remove('show');
      setTimeout(function(){ if(el && el.parentNode) el.parentNode.removeChild(el); }, 320);
    }, 4500);
  }

  window.BaramToast = oneToast;
  window.showToast = oneToast;

  function canChromeNotify(){
    return ('Notification' in window) &&
           localStorage.getItem('chromeNotifyEnabled') === '1' &&
           Notification.permission === 'granted';
  }

  window.sendChromeNotify = function(msg){
    try{
      if(!canChromeNotify()) return false;
      var key = 'chrome:' + keyOf(msg);
      var now = Date.now();
      if(shown[key] && now - shown[key] < 12000) return false;
      shown[key] = now;
      new Notification('월하 · 연가 · 연희', {
        body: msg || '새 알림이 있습니다.',
        icon: '/favicon.ico'
      });
      return true;
    }catch(e){
      return false;
    }
  };

  window.requestChromeNotifyPermission = async function(){
    if(!('Notification' in window)){
      oneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    var result = await Notification.requestPermission();
    if(result === 'granted'){
      localStorage.setItem('chromeNotifyEnabled','1');
      try{
        new Notification('월하 · 연가 · 연희', { body:'크롬 알림이 켜졌습니다.' });
      }catch(e){}
      oneToast('🔔 크롬 알림이 켜졌습니다.');
    }else{
      localStorage.setItem('chromeNotifyEnabled','0');
      oneToast('크롬 알림 권한이 허용되지 않았습니다.');
    }
  };

  window.testToastFromSettings = function(){
    oneToast('🔔 토스트 알림 테스트입니다. 이 문구가 보이면 정상입니다.');
  };

  window.testChromeNotifyFromSettings = async function(){
    if(!('Notification' in window)){
      oneToast('이 브라우저는 크롬 알림을 지원하지 않습니다.');
      return;
    }
    if(Notification.permission !== 'granted'){
      await window.requestChromeNotifyPermission();
      return;
    }
    localStorage.setItem('chromeNotifyEnabled','1');
    var ok = window.sendChromeNotify('크롬 알림 테스트입니다.');
    if(ok) oneToast('🔔 크롬 알림 테스트를 보냈습니다.');
    else oneToast('크롬 알림이 차단되어 있습니다. 주소창 왼쪽 사이트 권한에서 알림 허용을 확인하세요.');
  };

  function handleUrlToast(){
    try{
      var params = new URLSearchParams(location.search);
      var msg = params.get('toast');
      if(msg){
        setTimeout(function(){
          oneToast(msg);
          window.sendChromeNotify(msg);
        }, 250);
        params.delete('toast');
        var qs = params.toString();
        history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
      }
    }catch(e){}
  }

  // 크롬 알림 전용 폴링: 화면 토스트는 띄우지 않음
  async function chromeAlertPoll(){
    try{
      var r = await fetch('/api/chrome_alerts?_=' + Date.now(), {cache:'no-store'});
      var data = await r.json();
      var alerts = data.alerts || [];
      var seen = {};
      try{ seen = JSON.parse(localStorage.getItem('v287ChromeSeen') || '{}'); }catch(e){ seen = {}; }
      var now = Date.now();
      alerts.forEach(function(a){
        var id = String(a.id || '');
        if(!id || seen[id]) return;
        seen[id] = 1;
        var t = Date.parse(a.time || '');
        var recent = isNaN(t) ? true : (now - t < 20000);
        if(recent && a.text){
          window.sendChromeNotify(a.text);
        }
      });
      var keys = Object.keys(seen).slice(-150);
      var slim = {};
      keys.forEach(function(k){ slim[k] = 1; });
      localStorage.setItem('v287ChromeSeen', JSON.stringify(slim));
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', function(){
    handleUrlToast();
    chromeAlertPoll();
    setInterval(chromeAlertPoll, 3000);
  });
})();


/* v28.8 farm alert toast + chrome notify */
(function(){
  function farmKey(a){
    return String(
      (a.id || '') + '|' +
      (a.post_id || '') + '|' +
      (a.title || a.name || '') + '|' +
      (a.minutes || a.left || a.remain || '') + '|' +
      (a.text || a.message || '')
    );
  }

  function farmMsg(a){
    if(a.text) return a.text;
    if(a.message) return a.message;

    var title = a.title || a.name || a.boss || a.place || '파밍';
    var left = a.minutes || a.left || a.remain || a.before || '';
    if(left){
      return '⏰ [' + title + '] 젠 ' + left + '분 전입니다.';
    }
    return '⏰ [' + title + '] 파밍 시간이 다가옵니다.';
  }

  async function pollFarmAlertsV288(){
    try{
      var r = await fetch('/api/farm_alerts?_=' + Date.now(), {cache:'no-store'});
      var data = await r.json();
      var arr = data.alerts || data.items || data || [];
      if(!Array.isArray(arr)) return;

      var seen = {};
      try{ seen = JSON.parse(localStorage.getItem('v288FarmSeen') || '{}'); }catch(e){ seen = {}; }

      arr.forEach(function(a){
        var k = farmKey(a);
        if(!k || seen[k]) return;
        seen[k] = Date.now();

        var msg = farmMsg(a);
        if(window.BaramToast) window.BaramToast(msg);
        if(window.sendChromeNotify) window.sendChromeNotify(msg);
      });

      var keys = Object.keys(seen).slice(-200);
      var slim = {};
      keys.forEach(function(k){ slim[k] = seen[k]; });
      localStorage.setItem('v288FarmSeen', JSON.stringify(slim));
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', function(){
    pollFarmAlertsV288();
    setInterval(pollFarmAlertsV288, 30000);
  });
})();

</script></body></html>"""

def render(page, **kw):
    kw.setdefault("title", APP_TITLE)
    kw.setdefault("css", CSS)
    kw.update(dict(app_version=APP_VERSION, jobs=JOBS, job_select=job_select, categories=CATEGORIES, places=PLACES, show_time=show_time, delete_after_text=delete_after_text, share_text=share_text, participant_for_user=participant_for_user, join_block_reason=join_block_reason, can_join_post=can_join_post, participant_group_label=participant_group_label, can_manage_post=can_manage_post, farm_money_summary=farm_money_summary, money_text=money_text, farm_distribution=farm_distribution, remaining_text=remaining_text, countdown_target=countdown_target, approved_chars=approved_chars, compatible_job=compatible_job, joined_count=joined_count, max_count=max_count, is_admin=is_admin, selected_char=selected_char, char_label=char_label, today=today))
    return render_template_string(BASE_HEAD + page + BASE_TAIL, **kw)



@app.route("/toast_test")
def toast_test_page():
    u = cur_user()
    if not approved(u):
        return redirect("/gate")
    return render("""
<section class='panel'>
  <a class='btn gray' href='/'>← 메인으로</a>
  <h1>🔔 토스트 알림 테스트</h1>
  <div class='notice'>버튼을 누르면 화면 우측 상단에 테스트 팝업이 떠야 합니다.</div>
  <div class="toast-test-box">
    <h3>토스트 테스트</h3>
    <p>이 버튼은 서버 저장 없이 브라우저에서 바로 토스트를 띄웁니다.</p>
    <button type="button" class="btn ok" onclick="testToastFromSettings()">토스트 테스트</button>
  </div>
</section>
""")

@app.route("/")
def index():
    d = load()
    changed_autoclose = auto_close_full_posts(d)
    changed_cleanup = cleanup_closed_posts(d)
    if changed_autoclose or changed_cleanup:
        save(d)
    u = cur_user(d)
    if not u:
        return redirect("/gate")
    if not approved(u):
        return redirect("/pending")
    cat = request.args.get("cat", "전체")
    posts = d["posts"]
    if cat != "전체":
        posts = [p for p in posts if p["category"] == cat]
    sched = [p for p in d["posts"] if p["category"] == "파밍" and not p.get("closed")]
    return render(T_INDEX, d=d, u=u, c=selected_char(u), cat=cat, posts=posts, sched=sched, online=online_users(d), notice=get_notice(d), notice_preview_text=notice_preview_text, notice_new=notice_is_new(d))

T_INDEX = """
<header class='header'>
  <div>
    <h1>⚔ 월하 · 연가 · 연희</h1>
    <div class='sub'>{{ app_version }} · {{ char_label(c) }}</div>
  </div>
  <div class='toolbar'>
    <a class='btn nav-btn gray' href='/chars'>캐릭터</a>
    <button type='button' class='btn nav-btn gray' onclick='openSettingsModal()'>⚙ 설정</button>
    {% if is_admin(u) %}<a class='btn nav-btn gray' href='/admin'>관리자</a>{% endif %}
    <a class='btn nav-btn gray' href='/logout'>로그아웃</a>
  </div>
</header>

<div class='summary-grid'>
  <div class='summary-card'><span>오늘 파밍</span><strong>{{ sched|length }}</strong></div>
  <div class='summary-card'><span>진행중 모집</span><strong>{{ posts|selectattr('closed','equalto',False)|list|length }}</strong></div>
  <div class='summary-card'><span>캐릭터</span><strong>{{ u.chars|selectattr('status','equalto','approved')|list|length }}</strong></div>
</div>


{% if notice.text %}
<section class='panel clan-notice-card'>
  <div class='clan-notice-head'>
    <h2>📢 {{ notice.title }}</h2>
    {% if notice_new %}<span class='tag ok'>NEW</span>{% endif %}
  </div>
  <div class='clan-notice-preview'>{{ notice_preview_text(notice.text) }}</div>
  <div class='clan-notice-full'>{{ notice.text }}</div>
  <button type='button' class='btn gray mini' onclick='toggleClanNotice()' id='clanNoticeBtn'>더보기</button>
</section>
{% endif %}

<div class='app-shell' data-live-root='1' style='display:grid!important;grid-template-columns:820px 360px!important;gap:16px!important;align-items:start!important;width:1196px!important;min-width:1196px!important;max-width:1196px!important;'>
  <main class='left-stack' style='display:block!important;width:820px!important;min-width:820px!important;max-width:820px!important;'>
    <div class='quickbar recruit-head'>
      <div class='recruit-title-row'>
        <h2>📌 모집글</h2>
        <a class='btn recruit-write-btn primary' href='/new'>＋ 모집</a>
      </div>
      <div class='category-bar'>
        {% for x in categories %}
          <a class='btn tab-chip {{ "ok" if x==cat else "gray" }} mini' href='/?cat={{x}}'>{{x}}</a>
        {% endfor %}
      </div>
    </div>

    <div class='post-grid-v317' style='display:grid!important;grid-template-columns:403px 403px!important;gap:14px!important;width:820px!important;min-width:820px!important;max-width:820px!important;align-items:start!important;'>
    {% for p in posts %}
    <section class='card {{ "closed" if p.closed else "" }}' data-category='{{p.category}}' style='width:403px!important;min-width:403px!important;max-width:403px!important;margin:0!important;box-sizing:border-box!important;overflow:hidden!important;'>
      <span class='tag {{ "closed-tag" if p.closed else "ok" }}'>{{ "모집 완료" if p.closed else "모집중" }}</span>{% if delete_after_text(p) %}<span class='tag auto-delete-tag'>{{ delete_after_text(p) }}</span>{% endif %}
      <span class='tag'>{{p.category}}</span>
      <span class='count'>{{joined_count(p)}} / {{max_count(p)}}명</span>
      <h2>{{p.place}}</h2>
      <div class='meta'>📍 {{p.channel}}채널 · ⏰ {{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}}{% if p.category=="파밍" %} · <b class='remain'>{{ remaining_text(p) }}</b>{% endif %}</div>
      <div class='meta'>👑 {{p.owner_label}} · {{p.created}}</div>
      {% if p.memo %}<div class='notice'>{{p.memo|autolink|safe}}</div>{% endif %}

      {% if p.category == "사냥" %}
        {% for s in p.slots %}
        <div class='slot'>
          <div>
            <b>{{s.job}}</b>
            <div class='meta'>{{s.label or s.external or "참여 대기"}}</div>
          </div>
          <div class='toolbar'>
            {% if not p.closed or can_manage_post(u,p) %}
              {% if s.uid==u.id %}
                <span class='tag ok'>내 자리</span>
                <a class='btn mini gray' href='/leave_slot/{{p.id}}/{{loop.index0}}'>취소</a>
              {% elif s.external %}
                <span class='tag'>외부</span>
                {% if is_admin(u) or p.owner_uid==u.id %}
                  <a class='btn mini danger' href='/remove_external_slot/{{p.id}}/{{loop.index0}}'>외부제거</a>
                {% endif %}
              {% elif not s.uid and not s.external %}
                <a class='btn mini ok' href='/choose_slot/{{p.id}}/{{loop.index0}}'>참여</a>
                {% if is_admin(u) or p.owner_uid==u.id %}<a class='btn mini gray' href='/external_slot/{{p.id}}/{{loop.index0}}?next=/'>+ 외부</a>{% endif %}
              {% endif %}
            {% endif %}
          </div>
        </div>
        {% endfor %}
      {% else %}
        <h3>참여자</h3>
        {% for a in p.participants %}
          <span class='pill'>{{a.label}}{% if a.uid==u.id %}<small class='group-badge'>내 참여</small>{% endif %}{% set g = participant_group_label(p,a) %}{% if g %}<small class='group-badge'>{{g}}</small>{% endif %}</span>
        {% else %}
          <p class='meta'>아직 참여자 없음</p>
        {% endfor %}
        {% set my_part = participant_for_user(p,u) %}
        {% if my_part and not p.closed %}
          <a class='btn gray full' href='/leave_participant/{{p.id}}'>참여취소</a>
        {% elif can_join_post(p) %}
          <a class='btn ok full' href='/choose_participant/{{p.id}}'>참여하기</a>
        {% elif join_block_reason(p) %}
          <div class='notice'>{{ join_block_reason(p) }}</div><button class='btn gray full' disabled>참여불가</button>
        {% endif %}

        {% if p.category in ["파밍","승급지원"] %}
          <div class='farm-box'>
            {% if p.category != '승급지원' %}<!-- v29_promotion_hide_settlement_start -->
<div class='farm-head'>
              <h3>파밍 정산</h3>
              <span class='tag'>{{ p.farm_result or "미등록" }}</span>
            </div>
            {% set fm = farm_money_summary(p) %}
            <div class='farm-summary'>
              <span>아이템 <b>{{ p.farm_item or "-" }}</b></span>
              <span>판매 <b>{{ fm.sale }}</b></span>
            </div>
            {% if fm.sale != "0전" %}
              <div class='farm-dist'>선집합 {{ fm.early_count }}명 · {{ fm.early_each }} / 후집합 {{ fm.late_count }}명 · {{ fm.late_each }}</div>
            {% endif %}
            {% if can_manage_post(u,p) %}
              <form class='farm-form' method='post' action='/farm_result/{{p.id}}'>
                <select name='farm_result'>
                  <option {% if p.farm_result=="노득" %}selected{% endif %}>노득</option>
                  <option {% if p.farm_result=="득템" %}selected{% endif %}>득템</option>
                </select>
                <input name='farm_item' value='{{p.farm_item}}' placeholder='아이템명'>
                <input name='sale_amount' value='{{p.sale_amount}}' placeholder='판매금액'>
                <input name='early_weight' value='{{p.early_weight or "1.0"}}' placeholder='선집합 기준'>
                <input name='late_weight' value='{{p.late_weight or "0.88"}}' placeholder='후집합 기준'>
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
        
<!-- v29_promotion_hide_settlement_end -->{% endif %}
<button type='button' class='btn gray copy-btn' onclick='copyPostText(this)' data-pid='{{p.id}}'>글복사</button>
        <a class='btn gray' href='/chat/{{p.id}}'>채팅 {{p.chat|length }}</a>
        {% if can_manage_post(u,p) and (not p.closed or is_admin(u)) %}
          {% if not p.closed %}<a class='btn ok' href='/close/{{p.id}}'>모집완료</a>{% endif %}
          {% if not p.closed or is_admin(u) %}<a class='btn gray' href='/edit/{{p.id}}'>수정</a>{% endif %}
          <a class='btn danger' href='/delete/{{p.id}}'>삭제</a>
        {% endif %}
      </div>
    </section>
    {% else %}
      <div class='empty'>모집글 없음</div>
    {% endfor %}
    </div>
  </main>

  <aside class='side-stack' style='grid-column:2!important;width:360px!important;min-width:360px!important;max-width:360px!important;position:sticky!important;top:12px!important;align-self:start!important;max-height:calc(100vh - 24px)!important;overflow-y:auto!important;'>
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
        <div class='schedule-row boss-timer' data-target='{{ countdown_target(p) }}'>
          <div>
            <b>{{p.place}}</b><br>
            <span class='meta'>{{p.date}} · {{show_time(p.end_time or p.start_time)}} 젠</span>
          </div>
          <strong class='schedule-countdown'>--:--</strong>
        </div>
      {% else %}
        <div class='empty'>등록된 파밍 일정 없음</div>
      {% endfor %}
    </section>

    <section class='panel' id='global-chat'>
      <h2>💬 통합채팅</h2>
      <div class='chatbox' id='globalChatBox'>
        {% for m in d.global_chat[-30:] %}
          <div class='chatmsg'><b>{{m.name}}</b><br>{{m.text}}<br><span class='meta'>{{m.time}}</span></div>
        {% else %}
          <div class='empty'>메시지 없음</div>
        {% endfor %}
      </div>
      <form class='toolbar' method='post' action='/global_chat' id='globalChatForm'>
        <input name='text' id='globalChatInput' placeholder='메시지'>
        <button>전송</button>
      </form>
    </section>
  </aside>
</div>

<div id='settingsModal' class='modal-backdrop' onclick='closeSettingsModal(event)'>
  <div class='settings-modal'>
    <div class='modal-head'>
      <h2>⚙ 설정</h2>
      <button type='button' class='btn gray mini' onclick='hideSettingsModal()'>닫기</button>
    </div>
    <div class='setting-card'>
      <div>
        <b>음성 알림</b>
        <div class='meta'>파밍 젠 30 · 15 · 5분 전 알림</div>
      </div>
      <label class='toggle'>
        <input type='checkbox' id='alarmVoiceToggle' checked>
        <span></span>
      </label>
    </div>
    <div class='setting-card vertical'>
      <label class='volume-label'>음량 <span id='alarmVolumeText'>100%</span></label>
      <input type='range' id='alarmVolume' min='0' max='100' value='100'>
      <button type='button' class='btn gray full' onclick='testFarmVoice()'>음성 테스트</button>
      <div class='meta'>같은 알림은 최대 2번만 알려줍니다.</div>
    </div>

    <div class='setting-card vertical toast-test-box'>
      <b>🔔 토스트 알림 테스트</b>
      <div class='meta'>사이트 안에서 우측 상단 팝업이 뜨는지 확인합니다.</div>
      <button type='button' class='btn ok full' onclick="testToastFromSettings()">토스트 테스트</button>
    </div>
    <div class='setting-card vertical toast-test-box'>
      <b>🔔 크롬 알림 설정</b>
      <div class='meta'>크롬 알림센터로 참석/취소/파밍 젠 알림을 받으려면 권한 허용이 필요합니다. 파밍 젠 알림도 토스트/크롬 알림으로 표시됩니다.</div>
      <div class='toolbar' style='margin-top:10px'>
        <button type='button' class='btn ok' onclick='requestChromeNotifyPermission()'>크롬 알림 켜기</button>
        <button type='button' class='btn gray' onclick='testChromeNotifyFromSettings()'>크롬 알림 테스트</button>
      </div>
    </div>
  </div>
</div>

"""



@app.route("/gate")
def gate():
    return render(GATE_HTML)

@app.route("/login", methods=["GET","POST"])
def login():
    d = load()
    if request.method == "POST":
        account = request.form.get("account","").strip()
        pin = request.form.get("pin","").strip()
        for u in d.get("users", []):
            if u.get("account") == account and verify_pin(u, pin):
                session["uid"] = u.get("id")
                if u.get("status") != "approved":
                    return redirect("/pending")
                cs = approved_chars(u) if "approved_chars" in globals() else [c for c in u.get("chars", []) if c.get("status") == "approved"]
                if cs and not u.get("selected_char_id"):
                    u["selected_char_id"] = cs[0].get("id")
                    save(d)
                return redirect("/")
        return render(LOGIN_HTML, error="계정명 또는 비밀번호가 맞지 않습니다.", form=request.form)
    return render(LOGIN_HTML, error="", form={})

@app.route("/register", methods=["GET","POST"])
def register():
    d = load()
    if request.method == "POST":
        acc = request.form.get("account","").strip()
        name = request.form.get("char_name","").strip()
        job = request.form.get("job","검성")
        pin = request.form.get("pin","").strip()
        pin_confirm = request.form.get("pin_confirm","").strip()
        admin_pw = request.form.get("admin_password","").strip()
        if not acc or not name:
            return render(REGISTER_HTML, error="계정명과 캐릭터명을 입력하세요.", form=request.form)
        if not valid_pin(pin):
            return render(REGISTER_HTML, error="비밀번호는 숫자 6자리로 입력하세요.", form=request.form)
        if pin != pin_confirm:
            return render(REGISTER_HTML, error="비밀번호 확인이 맞지 않습니다.", form=request.form)
        if account_exists(d, acc):
            return render(REGISTER_HTML, error="이미 등록된 계정명입니다.", form=request.form)
        if char_name_exists(d, name):
            return render(REGISTER_HTML, error="이미 등록된 캐릭터명입니다. 사칭 방지를 위해 다른 이름은 사용할 수 없습니다.", form=request.form)
        uid, cid = nid(), nid()
        first = len(d["users"]) == 0
        pw_ok = admin_password_ok(d, admin_pw)
        status = "approved" if (first or pw_ok) else "pending"
        role = "최고관리자" if first else ("관리자" if pw_ok else "일반")
        d["users"].append({"id":uid,"account":acc,"pin_hash":pin_hash(pin),"status":status,"role":role,"selected_char_id":cid,"chars":[{"id":cid,"name":name,"job":job,"status":status}]})
        save(d)
        session["uid"] = uid
        return redirect("/") if status == "approved" else redirect("/pending")
    return render(REGISTER_HTML, error="", form={})
@app.route("/pending")
def pending():
    return render(PENDING_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/gate")

@app.route("/new")
def new_post():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/pending")
    cats = ["사냥"] + (["파밍"] if is_admin(u) else []) + ["600퀘","승급지원"]
    return render(T_NEW, cats=cats)

T_NEW = """
<section class='panel'><a class='btn gray' href='/'>← 메인으로</a><h1>모집글 올리기</h1><form method='post' action='/create'><label>종류</label><select name='category' id='cat'>{% for c in cats %}<option>{{c}}</option>{% endfor %}</select>{% for cat, arr in places.items() %}<div class='place' data-cat='{{cat}}'><label>장소</label><select name='place_{{cat}}'>{% for p in arr %}<option>{{p}}</option>{% endfor %}</select></div>{% endfor %}<label>채널</label><input name='channel' maxlength='4'><label>날짜</label><input name='date' type='date' value='{{today()}}'><label>시작시간</label><div class='time-row'><select name='start_period'><option>오전</option><option>오후</option></select><input name='start_time' maxlength='5' placeholder='1107'></div><label>종료시간</label><div class='time-row'><select name='end_period'><option>오전</option><option>오후</option></select><input name='end_time' maxlength='5' placeholder='1120'></div><label>메모</label><textarea name='memo'></textarea><section class='panel' id='slotsBox'><h2>사냥 직업 자리 추가</h2><div class='toolbar'>{{ job_select('slotJob', '', 'slotJob')|safe }}<button type='button' class='ok' onclick='addSlot()'>추가</button></div><div id='slots'></div></section><button class='ok full'>등록</button></form></section>
"""

@app.route("/create", methods=["POST"])
def create():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/pending")
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
        msg = ""
        if chosen and not slot.get("uid") and not slot.get("external"):
            for s in p["slots"]:
                if s.get("uid")==u["id"]:
                    s.update({"uid":"","label":"","char_id":"","external":""})
            slot.update({"uid":u["id"],"label":char_label(chosen),"char_id":chosen.get("id",""),"external":""})
            refresh_post_status_after_member_change(d, p)
            msg = action_msg(p, f"{char_label(chosen)}님이 {slot.get('job','')} 자리에 참여했습니다.")
            system_notify(d, msg)
            auto_close_full_posts(d)
            save(d)
        return toast_redirect("/", msg) if msg else redirect("/")
    return render("""
<section class='panel'>
<a class='btn gray' href='/'>← 메인으로</a>
<h1>참여 캐릭터 선택</h1>
<div class='notice'>{{slot.job}} 자리에는 같은 계열 캐릭터만 참여할 수 있습니다.</div>
<form method='post'>
{% for c in options %}
<label class='choice-card'><input type='radio' name='char_id' value='{{c.id}}' required><span>{{c.name}}({{c.job}})</span></label>
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
    if not approved(u) or not p or p.get("category") not in ["600퀘","파밍","승급지원"] or not can_join_post(p):
        return redirect("/")
    options = approved_chars(u)
    if request.method == "POST":
        cid = request.form.get("char_id","")
        chosen = None
        for c in options:
            if c.get("id") == cid:
                chosen = c
        msg = ""
        if chosen:
            if p.get("category") in ["파밍", "승급지원"] or len(p.get("participants",[])) < int(p.get("capacity", 10) or 10):
                if not any(a.get("uid")==u["id"] and a.get("char_id")==chosen.get("id") for a in p["participants"]):
                    p["participants"].append({"uid":u["id"],"char_id":chosen.get("id"),"label":char_label(chosen)})
                    refresh_post_status_after_member_change(d, p)
                    msg = action_msg(p, f"{char_label(chosen)}님이 참여했습니다.")
                    system_notify(d, msg)
                    save(d)
        return toast_redirect("/", msg) if msg else redirect("/")
    return render("""
<section class='panel'>
<a class='btn gray' href='/'>← 메인으로</a>
<h1>참여 캐릭터 선택</h1>
<form method='post'>
{% for c in options %}
<label class='choice-card'><input type='radio' name='char_id' value='{{c.id}}' required><span>{{c.name}}({{c.job}})</span></label>
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
<a class='btn gray' href='/'>← 메인으로</a>
<h1>{{title}}</h1>
<form method='post'>
{% for m in members %}
<label class='choice-card'><input type='checkbox' name='member' value='{{m.char_id or m.uid}}' {% if (m.char_id or m.uid) in checked %}checked{% endif %}><span>{{m.label}}</span></label>
{% else %}
<div class='empty'>참여자가 없습니다.</div>
{% endfor %}
<button class='ok full'>저장</button>
</form>

{% if can_manage_post(u,p) and p.category == "사냥" %}
<section class='panel edit-member-panel'>
  <h2>👥 멤버 관리</h2>
  <div class='notice'>모집중/모집완료 상태에서도 관리자와 작성자는 멤버를 추가·제거할 수 있습니다. 모집완료 글에서 인원이 빠지면 자동으로 모집중으로 돌아갑니다.</div>
  <div class='edit-slots'>
    {% for s in p.slots %}
    <div class='edit-slot-row'>
      <div>
        <b>{{s.job}}</b>
        <div class='meta'>
          {% if s.label %}{{s.label}}
          {% elif s.external %}{{s.external}} <span class='tag'>외부</span>
          {% else %}빈 자리{% endif %}
        </div>
      </div>
      <div class='toolbar'>
        {% if s.uid or s.external %}
          <a class='btn mini danger' href='/manage_clear_slot/{{p.id}}/{{loop.index0}}'>제거</a>
        {% else %}
          <a class='btn mini ok' href='/manage_choose_slot/{{p.id}}/{{loop.index0}}'>참여자 추가</a>
          <a class='btn mini gray' href='/external_slot/{{p.id}}/{{loop.index0}}?next=/'>외부 추가</a>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
</section>
{% endif %}

</section>
""", title=title, members=members, checked=checked)

@app.route("/join_slot/<pid>/<int:i>")
def join_slot(pid,i):
    d=load(); u=cur_user(d); c=selected_char(u)
    p=find_post(d,pid)
    msg = ""
    if p and c and p["category"]=="사냥" and not p.get("closed") and 0<=i<len(p["slots"]):
        if not compatible_job(p["slots"][i].get("job",""), c.get("job","")):
            return redirect(f"/choose_slot/{pid}/{i}")
        for s in p["slots"]:
            if s.get("uid")==u["id"]:
                s.update({"uid":"","label":"","char_id":"","external":""})
        if not p["slots"][i].get("uid") and not p["slots"][i].get("external"):
            p["slots"][i].update({"uid":u["id"],"label":char_label(c),"char_id":c.get("id",""),"external":""})
            job = p["slots"][i].get("job","")
            msg = action_msg(p, f"{actor_label(u)}님이 {job} 자리에 참여했습니다.")
            system_notify(d, msg)
        auto_close_full_posts(d)
        save(d)
    return toast_redirect("/", msg) if msg else redirect("/")

@app.route("/leave_slot/<pid>/<int:i>")
def leave_slot(pid,i):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    msg = ""
    if p and 0<=i<len(p.get("slots", [])) and (p["slots"][i].get("uid")==u["id"] or can_manage_post(u,p)):
        job = p["slots"][i].get("job","")
        old = p["slots"][i].get("label") or actor_label(u)
        p["slots"][i].update({"uid":"","label":"","char_id":"","external":""})
        refresh_post_status_after_member_change(d, p)
        msg = action_msg(p, f"{job} 자리의 {old}님이 참여를 취소했습니다.")
        system_notify(d, msg)
        save(d)
    return toast_redirect("/", msg) if msg else redirect("/")

@app.route("/cancel_slot/<pid>/<int:i>")
def cancel_slot_alias(pid, i):
    return leave_slot(pid, i)

@app.route("/cancel/<pid>/<int:i>")
def cancel_alias(pid, i):
    return leave_slot(pid, i)

@app.route("/remove_slot/<pid>/<int:i>")
def remove_slot_alias(pid, i):
    return leave_slot(pid, i)

@app.route("/remove_external_slot/<pid>/<int:i>")
def remove_external_slot(pid, i):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    msg = ""
    if not p or not can_manage_post(u, p):
        return redirect("/")
    if 0 <= i < len(p.get("slots", [])):
        old = p["slots"][i].get("external") or p["slots"][i].get("label") or "외부인"
        job = p["slots"][i].get("job", "")
        p["slots"][i].update({"uid": "", "label": "", "char_id": "", "external": ""})
        refresh_post_status_after_member_change(d, p)
        msg = action_msg(p, f"{job} 자리의 {old}님이 제거되었습니다.")
        system_notify(d, msg)
        save(d)
    return toast_redirect("/", msg) if msg else redirect("/")


@app.route("/manage_clear_slot/<pid>/<int:i>")
def manage_clear_slot(pid, i):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or not can_manage_post(u, p):
        return redirect("/")
    if 0 <= i < len(p.get("slots", [])):
        old = p["slots"][i].get("label") or p["slots"][i].get("external") or "참여자"
        job = p["slots"][i].get("job","")
        p["slots"][i].update({"uid": "", "label": "", "char_id": "", "external": ""})
        system_notify(d, f"❌ {actor_label(u)}님이 [{post_title(p)}] {job} 자리의 {old}님을 제거했습니다.")
        refresh_post_status_after_member_change(d, p)
        save(d)
    return redirect(f"/edit/{pid}")


@app.route("/manage_choose_slot/<pid>/<int:i>", methods=["GET","POST"])
def manage_choose_slot(pid, i):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or not can_manage_post(u, p) or not (0 <= i < len(p.get("slots", []))):
        return redirect("/")
    slot = p["slots"][i]
    users = [x for x in d.get("users", []) if x.get("status") == "approved"]
    choices = []
    for user in users:
        for ch in user.get("chars", []):
            if ch.get("status") == "approved" and same_job_family(ch.get("job"), slot.get("job")):
                choices.append({
                    "uid": user.get("id"),
                    "char_id": ch.get("id"),
                    "label": f"{ch.get('name')}({ch.get('job')})"
                })
    if request.method == "POST":
        key = request.form.get("choice", "")
        for c in choices:
            if key == c["uid"] + "|" + c["char_id"]:
                slot.update({"uid": c["uid"], "char_id": c["char_id"], "label": c["label"], "external": ""})
                system_notify(d, f"✅ {actor_label(u)}님이 [{post_title(p)}] {slot.get('job','')} 자리에 {c['label']}님을 추가했습니다.")
                refresh_post_status_after_member_change(d, p)
                save(d)
                return redirect(f"/edit/{pid}")
    return render("""
<div class='card narrow'>
  <a class='btn gray' href='/edit/{{p.id}}'>← 수정으로</a>
  <h1>참여자 추가</h1>
  <div class='notice'>{{slot.job}} 자리에 추가할 캐릭터를 선택하세요.</div>
  {% if not choices %}
    <div class='empty'>추가 가능한 캐릭터가 없습니다.</div>
  {% else %}
  <form method='post'>
    {% for c in choices %}
      <label class='choice-line'>
        <input type='radio' name='choice' value='{{c.uid}}|{{c.char_id}}' required>
        {{c.label}}
      </label>
    {% endfor %}
    <button class='ok full'>추가</button>
  </form>
  {% endif %}
</div>
""", p=p, slot=slot, choices=choices)

@app.route("/external_slot/<pid>/<int:i>", methods=["GET","POST"])
def external_slot(pid, i):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    next_url = request.values.get("next") or request.referrer or "/"
    if not p or not can_manage_post(u, p) or not (0 <= i < len(p.get("slots", []))):
        return redirect(next_url or "/")
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            p["slots"][i].update({"uid": "", "label": name, "char_id": "", "external": name})
            job = p["slots"][i].get("job", "")
            refresh_post_status_after_member_change(d, p)
            msg = action_msg(p, f"{job} 자리에 외부인 {name}님이 추가되었습니다.")
            system_notify(d, msg)
            save(d)
            return toast_redirect(next_url or "/", msg)
        return redirect(next_url or "/")
    return render("""
<section class='panel'>
  <a class='btn gray' href='{{next_url}}'>← 돌아가기</a>
  <h1>외부인 추가</h1>
  <form method='post'>
    <input type='hidden' name='next' value='{{next_url}}'>
    <label>외부인 표시명</label>
    <input name='name' placeholder='예: 길드원/지인/격수' required>
    <button class='ok full'>저장</button>
  </form>
</section>
""", next_url=next_url)
@app.route("/participate/<pid>")
def participate(pid):
    d=load(); p=find_post(d,pid)
    if p and not can_join_post(p): return redirect("/")
    return redirect(f"/choose_participant/{pid}")

@app.route("/edit/<pid>", methods=["GET","POST"])
def edit(pid):
    d=load(); u=cur_user(d); p=find_post(d,pid)
    if not p or not can_manage_post(u, p): return redirect("/")
    if request.method=="POST":
        p["channel"]=digits(request.form.get("channel"),4); p["date"]=request.form.get("date") or today(); p["start_time"]=to24(request.form.get("start_period"),request.form.get("start_time")); p["end_time"]=to24(request.form.get("end_period"),request.form.get("end_time")); p["memo"]=request.form.get("memo",""); reopen_on_edit_change(p); save(d); return redirect("/")
    sp,st=split12(p.get("start_time")); ep,et=split12(p.get("end_time"))
    return render("""
<section class='panel'>
  <a class='btn gray' href='/'>← 메인으로</a>
  <h1>수정</h1>
  <div class='notice'>수정하거나 직업 자리를 추가·제거하면 모집완료 글도 자동으로 모집중으로 돌아갑니다.</div>
  <form method='post'>
    <label>채널</label>
    <input name='channel' value='{{p.channel}}'>
    <label>날짜</label>
    <input name='date' type='date' value='{{p.date}}'>
    <label>시작시간</label>
    <div class='time-row'>
      <select name='start_period'>
        <option {% if sp=='오전' %}selected{% endif %}>오전</option>
        <option {% if sp=='오후' %}selected{% endif %}>오후</option>
      </select>
      <input name='start_time' value='{{st}}'>
    </div>
    <label>종료시간</label>
    <div class='time-row'>
      <select name='end_period'>
        <option {% if ep=='오전' %}selected{% endif %}>오전</option>
        <option {% if ep=='오후' %}selected{% endif %}>오후</option>
      </select>
      <input name='end_time' value='{{et}}'>
    </div>
    <label>메모</label>
    <textarea name='memo'>{{p.memo|autolink|safe}}</textarea>
    <button class='ok full'>저장</button>
  </form>
</section>
<div class='toolbar edit-bottom-nav'><a class='btn gray' href='/'>수정 완료 후 메인으로 돌아가기</a></div>

{% if p.category == "사냥" %}
<section class='panel edit-job-panel'>
  <h2>⚔ 사냥 직업 자리 수정</h2>
  <div class='notice'>모집글의 직업 자리 자체를 추가하거나 제거합니다. 참여자가 있는 자리를 제거하면 해당 참여자도 함께 빠집니다.</div>

  <div class='edit-slots'>
    {% for s in p.slots %}
    <div class='edit-slot-row'>
      <div>
        <b>{{s.job}}</b>
        <div class='meta'>
          {% if s.label %}참여: {{s.label}}
          {% elif s.external %}외부: {{s.external}}
          {% else %}모집중{% endif %}
        </div>
      </div>
      <div class='toolbar'>
        <a class='btn mini danger' href='/edit_remove_job_slot/{{p.id}}/{{loop.index0}}' onclick="return confirm('이 자리를 제거할까요? 참여자가 있으면 함께 빠집니다.')">자리 제거</a>
      </div>
    </div>
    {% endfor %}
  </div>

  <form class='job-add-form' method='post' action='/edit_add_job_slot/{{p.id}}'>
    <label>직업 자리 추가</label>
    <div class='time-row'>
      <select name='job'>
        <optgroup label='전사 계열'>
          <option>전사</option><option>검객</option><option>검제</option><option>검황</option><option>검성</option>
        </optgroup>
        <optgroup label='도적 계열'>
          <option>도적</option><option>자객</option><option>진검</option><option>귀검</option><option>태성</option>
        </optgroup>
        <optgroup label='주술사 계열'>
          <option>주술사</option><option>술사</option><option>현사</option><option>현인</option><option>현자</option>
        </optgroup>
        <optgroup label='도사 계열'>
          <option>도사</option><option>도인</option><option>명인</option><option>진인</option><option>진선</option>
        </optgroup>
      </select>
      <button class='ok'>자리 추가</button>
    </div>
  </form>
</section>
{% endif %}
""", p=p,sp=sp,st=st,ep=ep,et=et)


@app.route("/edit_add_job_slot/<pid>", methods=["POST"])
def edit_add_job_slot(pid):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or not can_manage_post(u, p) or p.get("category") != "사냥":
        return redirect("/")
    job = request.form.get("job", "").strip()
    msg = ""
    if job:
        p.setdefault("slots", []).append({"job": job, "uid": "", "label": "", "char_id": "", "external": ""})
        reopen_on_edit_change(p)
        refresh_post_status_after_member_change(d, p)
        msg = action_msg(p, f"{job} 자리가 추가되었습니다.")
        system_notify(d, msg)
        save(d)
    return toast_redirect(f"/edit/{pid}", msg) if msg else redirect(f"/edit/{pid}")


@app.route("/edit_remove_job_slot/<pid>/<int:i>")
def edit_remove_job_slot(pid, i):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or not can_manage_post(u, p) or p.get("category") != "사냥":
        return redirect("/")
    msg = ""
    if 0 <= i < len(p.get("slots", [])):
        removed_job = p["slots"][i].get("job","")
        p["slots"].pop(i)
        reopen_on_edit_change(p)
        refresh_post_status_after_member_change(d, p)
        msg = action_msg(p, f"{removed_job} 자리가 제거되었습니다.")
        system_notify(d, msg)
        save(d)
    return toast_redirect(f"/edit/{pid}", msg) if msg else redirect(f"/edit/{pid}")


@app.route("/close/<pid>")
def close(pid):
    d = load()
    if normalize_existing_approved_members(d):
        save(d)
    u = cur_user(d)
    p = find_post(d, pid)
    if p and can_manage_post(u, p):
        p["closed"] = True
        if not p.get("closed_at"):
            p["closed_at"] = now().isoformat(timespec="seconds")
        save(d)
    return redirect("/")

@app.route("/delete/<pid>")
def delete(pid):
    d=load(); u=cur_user(d)
    d["posts"]=[p for p in d["posts"] if not (p["id"]==pid and can_manage_post(u, p))]
    save(d); return redirect("/")



@app.route("/farm_result/<pid>", methods=["POST"])
def farm_result(pid):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not p or p.get("category") != "파밍":
        return redirect("/")
    if not can_manage_post(u, p):
        return redirect("/")
    p["farm_result"] = request.form.get("farm_result", "").strip()
    p["farm_item"] = request.form.get("farm_item", "").strip()
    p["sale_amount"] = digits(request.form.get("sale_amount", ""), 20)
    p["early_weight"] = request.form.get("early_weight", p.get("early_weight","1.0")).strip() or "1.0"
    p["late_weight"] = request.form.get("late_weight", p.get("late_weight","0.88")).strip() or "0.88"
    p.setdefault("early_ids", [])
    p.setdefault("late_ids", [])
    p.setdefault("early_weight", "1.0")
    p.setdefault("late_weight", "0.88")
    save(d)
    return redirect("/")





@app.route("/api/copy_text/<pid>")
def api_copy_text(pid):
    d = load()
    p = find_post(d, pid)
    if not p:
        return "", 404, {"Content-Type": "text/plain; charset=utf-8"}
    return share_text(p), 200, {"Content-Type": "text/plain; charset=utf-8"}





@app.route("/api/test_toast")
def api_test_toast():
    d = load()
    msg = "🔔 서버 크롬 알림 테스트입니다."
    system_notify(d, msg)
    save(d)
    return {"ok": True, "message": msg}


    return {"ok": False}


@app.route("/api/chrome_alerts")
def api_chrome_alerts():
    d = load()
    return {"alerts": d.get("chrome_alerts", [])[-30:]}

@app.route("/api/alerts")
def api_alerts():
    return {"alerts": []}





@app.route("/api/global_chat", methods=["GET","POST"])
def api_global_chat():
    d = load()
    u = cur_user(d)
    c = selected_char(u) if u else None
    if request.method == "POST":
        if not approved(u) or not c:
            return {"ok": False, "error": "login_required"}, 403
        text = request.form.get("text","").strip()
        if text:
            d.setdefault("global_chat", []).append({"name":char_label(c),"text":text,"time":now_text()})
            d["global_chat"] = d["global_chat"][-100:]
            save(d)
        return {"ok": True}
    return {"ok": True, "messages": d.get("global_chat", [])[-50:]}

@app.route("/global_chat", methods=["POST"])
def global_chat():
    d=load(); u=cur_user(d); c=selected_char(u); txt=request.form.get("text","").strip()
    if txt and c:
        d["global_chat"].append({"name":char_label(c),"text":txt,"time":now_text()}); d["global_chat"]=d["global_chat"][-100:]; save(d)
    return redirect("/#global-chat")

@app.route("/chat/<pid>", methods=["GET","POST"])
def chat(pid):
    d=load(); u=cur_user(d); c=selected_char(u); p=find_post(d,pid)
    if not p: return redirect("/")
    if request.method=="POST":
        txt=request.form.get("text","").strip()
        if txt and c: p["chat"].append({"name":char_label(c),"text":txt,"time":now_text()}); save(d)
        return redirect(f"/chat/{pid}")
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인으로</a><h1>채팅</h1><div class='chatbox'>{% for m in p.chat %}<div class='chatmsg'><b>{{m.name}}</b><br>{{m.text}}</div>{% else %}<div class='empty'>메시지 없음</div>{% endfor %}</div><form method='post' class='toolbar'><input name='text'><button>전송</button></form></section>", p=p)

@app.route("/chars", methods=["GET","POST"])
def chars():
    d=load(); u=cur_user(d)
    if not approved(u): return redirect("/pending")
    if request.method=="POST":
        name=request.form.get("name","").strip(); job=request.form.get("job","검성")
        if name and not char_name_exists(d, name, exclude_uid=u.get("id","")): u["chars"].append({"id":nid(),"name":name,"job":job,"status":"approved" if u.get("status")=="approved" else "pending"}); save(d)
        return redirect("/chars")
    return render("<section class='panel'><a class='btn gray' href='/'>← 메인으로</a><h1>캐릭터</h1>{% for c in u.chars %}<div class='slot'><div><b>{{c.name}}({{c.job}})</b><br>{{ '승인됨' if c.status=='approved' else '승인대기' }}</div>{% if c.status=='approved' %}<a class='btn mini ok' href='/select_char/{{c.id}}'>선택</a>{% endif %}</div>{% endfor %}<form method='post'><h2>추가</h2><input name='name'>{{ job_select('job')|safe }}<button class='ok'>추가</button></form></section>", u=u)

@app.route("/select_char/<cid>")
def select_char(cid):
    d=load(); u=cur_user(d)
    if u: u["selected_char_id"]=cid; save(d)
    return redirect("/chars")

@app.route("/admin")
def admin():
    d=load(); u=cur_user(d)
    if u and u.get("status") == "approved" and not has_any_admin(d):
        u["role"] = "최고관리자"
        save(d)
    if not is_admin(u): return redirect("/")
    pending=[x for x in d["users"] if x["status"]=="pending"]
    pending_chars=[]
    for x in d["users"]:
        for ch in x.get("chars", []):
            if ch.get("status") == "pending":
                pending_chars.append({"user": x, "char": ch})
    return render("""
<section class='panel admin-console'>
  <a class='btn gray' href='/'>← 메인으로</a>
  <h1>관리자 콘솔</h1>
  <div class='admin-grid'>
    <div class='admin-card'><span>가입대기</span><strong>{{pending|length}}</strong></div>
    <div class='admin-card'><span>캐릭터대기</span><strong>{{pending_chars|length}}</strong></div>
    <div class='admin-card'><span>모집글</span><strong>{{posts|length}}</strong></div>
    <div class='admin-card'><span>채팅</span><strong>{{chat_count}}</strong></div>
  </div>

  <div class='notice'>기존 문파원은 data.json을 유지하면 다시 가입/승인할 필요가 없습니다. 승인된 계정의 추가 캐릭터는 자동 승인됩니다.</div>
  <h2>가입 승인</h2>
  {% for x in pending %}
    <div class='slot'><div><b>{{x.account}}</b><br><span class='meta'>{{x.chars[0].name if x.chars else ""}} / {{x.chars[0].job if x.chars else ""}}</span></div><a class='btn mini ok' href='/admin/approve/{{x.id}}'>승인</a></div>
  {% else %}<div class='empty'>가입 승인 대기 없음</div>{% endfor %}

  <h2>캐릭터 승인</h2>
  {% for item in pending_chars %}
    <div class='slot'><div><b>{{item.char.name}}({{item.char.job}})</b><br><span class='meta'>{{item.user.account}}</span></div><a class='btn mini ok' href='/admin/approve_char/{{item.user.id}}/{{item.char.id}}'>승인</a></div>
  {% else %}<div class='empty'>캐릭터 승인 대기 없음</div>{% endfor %}

  <h2>권한 관리</h2>
  {% for x in users %}
    <div class='slot'>
      <div><b>{{x.account}}</b><br><span class='meta'>{{x.status}} / {{x.role}}</span>{% for ch in x.chars %}<br><span class='meta'>- {{ch.name}}({{ch.job}}) · {{ch.status}}</span>{% endfor %}</div>
      <div class='toolbar'>
        <a class='btn mini gray' href='/admin/role/{{x.id}}/일반'>일반</a>
        <a class='btn mini gray' href='/admin/role/{{x.id}}/관리자'>관리자</a>
        <a class='btn mini gray' href='/admin/role/{{x.id}}/최고관리자'>최고</a>
        {% if x.id != me.id %}<a class='btn mini danger' href='/admin/delete_user/{{x.id}}' onclick="return confirm('유저를 삭제할까요?')">삭제</a>{% endif %}
      </div>
    </div>
  {% endfor %}


  <section class='panel admin-notice-box'>
    <h2>📢 문파 공지사항</h2>
    <form method='post' action='/admin/notice' class='notice-edit-form'>
      <label>공지 제목</label>
      <input name='notice_title' value='{{notice.title}}' placeholder='예: 공성 관련 협의 사항 안내'>
      <label>공지 내용</label>
      <textarea name='notice_text' rows='14' placeholder='공지 내용을 입력하세요'>{{notice.text}}</textarea>
      <button class='ok full'>공지 저장</button>
    </form>
    <div class='notice'>저장하면 메인 상단 공지사항 카드에 표시됩니다.</div>
  </section>

  <h2>관리자 비밀번호</h2>
  <form class='admin-form' method='post' action='/admin/password'>
    <input name='admin_password' type='password' placeholder='새 관리자 비밀번호'>
    <button class='ok'>변경</button>
  </form>
  <div class='notice'>관리자 비밀번호를 아는 사람은 가입 시 바로 관리자 승인됩니다. 현재 기본값을 쓰고 있다면 꼭 변경하세요.</div>


  <h2>모집글 관리</h2>
  <div class='admin-post-tabs'>
    <a class='btn tab-chip gray mini' href='#admin-farm'>파밍글</a>
    <a class='btn tab-chip gray mini' href='#admin-hunt'>사냥글</a>
    <a class='btn tab-chip gray mini' href='#admin-quest'>600퀘</a>
    <a class='btn tab-chip gray mini' href='#admin-support'>승급지원</a>
  </div>

  <div id='admin-farm' class='admin-post-section'>
    <h3>파밍글</h3>
    {% for p in posts if p.category in ["파밍","승급지원"] %}
      <div class='admin-post-row'>
        <div>
          <b>{{p.place}}</b>
          <div class='meta'>{{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}} · {{p.owner_label}} · {{ "모집 완료" if p.closed else "모집중" }}</div>
        </div>
        <div class='toolbar'>
          <a class='btn mini gray' href='/edit/{{p.id}}'>수정</a>
          <a class='btn mini danger' href='/admin/delete_post/{{p.id}}' onclick="return confirm('이 파밍글을 삭제할까요?')">삭제</a>
        </div>
      </div>
    {% else %}<div class='empty'>파밍글 없음</div>{% endfor %}
  </div>

  <div id='admin-hunt' class='admin-post-section'>
    <h3>사냥글</h3>
    {% for p in posts if p.category == "사냥" %}
      <div class='admin-post-row'>
        <div>
          <b>{{p.place}}</b>
          <div class='meta'>{{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}} · {{p.owner_label}} · {{ "모집 완료" if p.closed else "모집중" }}</div>
        </div>
        <div class='toolbar'>
          <a class='btn mini gray' href='/edit/{{p.id}}'>수정</a>
          <a class='btn mini danger' href='/admin/delete_post/{{p.id}}' onclick="return confirm('이 사냥글을 삭제할까요?')">삭제</a>
        </div>
      </div>
    {% else %}<div class='empty'>사냥글 없음</div>{% endfor %}
  </div>

  <div id='admin-quest' class='admin-post-section'>
    <h3>600퀘</h3>
    {% for p in posts if p.category == "600퀘" %}
      <div class='admin-post-row'>
        <div>
          <b>{{p.place}}</b>
          <div class='meta'>{{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}} · {{p.owner_label}} · {{ "모집 완료" if p.closed else "모집중" }}</div>
        </div>
        <div class='toolbar'>
          <a class='btn mini gray' href='/edit/{{p.id}}'>수정</a>
          <a class='btn mini danger' href='/admin/delete_post/{{p.id}}' onclick="return confirm('이 600퀘 글을 삭제할까요?')">삭제</a>
        </div>
      </div>
    {% else %}<div class='empty'>600퀘 글 없음</div>{% endfor %}
  </div>


  <div id='admin-support' class='admin-post-section'>
    <h3>승급지원</h3>
    {% for p in posts if p.category == "승급지원" %}
      <div class='admin-post-row'>
        <div>
          <b>{{p.place}}</b>
          <div class='meta'>{{p.date}} · {{show_time(p.start_time)}} ~ {{show_time(p.end_time)}} · {{p.owner_label}} · {{ "모집 완료" if p.closed else "모집중" }}</div>
        </div>
        <div class='toolbar'>
          <a class='btn mini gray' href='/edit/{{p.id}}'>수정</a>
          <a class='btn mini danger' href='/admin/delete_post/{{p.id}}' onclick="return confirm('이 승급지원 글을 삭제할까요?')">삭제</a>
        </div>
      </div>
    {% else %}<div class='empty'>승급지원 글 없음</div>{% endfor %}
  </div>

  <h2>데이터 관리</h2>
  <div class='danger-zone'>
    <div class='admin-action-title'>종류별 삭제</div>
    <div class='toolbar'>
      <a class='btn danger' href='/admin/clear_posts/파밍' onclick="return confirm('파밍글을 전부 삭제할까요?')">파밍글 삭제</a>
      <a class='btn danger' href='/admin/clear_posts/사냥' onclick="return confirm('사냥글을 전부 삭제할까요?')">사냥글 삭제</a>
      <a class='btn danger' href='/admin/clear_posts/600퀘' onclick="return confirm('600퀘 글을 전부 삭제할까요?')">600퀘 삭제</a>
      <a class='btn danger' href='/admin/clear_posts/승급지원' onclick="return confirm('승급지원 글을 전부 삭제할까요?')">승급지원 삭제</a>
      <a class='btn danger' href='/admin/clear_chat' onclick="return confirm('통합채팅과 글 채팅을 전부 삭제할까요?')">채팅 삭제</a>
    </div>
    <div class='admin-action-title'>전체 초기화</div>
    <div class='toolbar'>
      <a class='btn danger' href='/admin/clear_posts' onclick="return confirm('모집글을 전부 삭제할까요?')">모집글 전체 삭제</a>
    </div>
  </div>
</section>
""", users=d["users"], pending=pending, pending_chars=pending_chars, posts=d["posts"], chat_count=len(d.get("global_chat", [])), me=u, notice=get_notice(d))


@app.route("/admin/approve_char/<uid>/<cid>")
def approve_char(uid, cid):
    d=load(); u=cur_user(d)
    if is_admin(u):
        for x in d["users"]:
            if x["id"]==uid:
                x["status"]="approved"
                for ch in x.get("chars", []):
                    if ch.get("id")==cid:
                        ch["status"]="approved"
                if not x.get("selected_char_id") and x.get("chars"):
                    x["selected_char_id"]=x["chars"][0]["id"]
        save(d)
    return redirect("/admin")

@app.route("/admin/delete_user/<uid>")
def admin_delete_user(uid):
    d=load(); u=cur_user(d)
    if is_admin(u) and uid != u.get("id"):
        d["users"]=[x for x in d["users"] if x.get("id") != uid]
        # 모집글/참여자에서 삭제 유저 정리
        for p in d.get("posts", []):
            p["participants"]=[a for a in p.get("participants", []) if a.get("uid") != uid]
            for s in p.get("slots", []):
                if s.get("uid") == uid:
                    s.update({"uid":"","label":"","char_id":""})
        save(d)
    return redirect("/admin")

@app.route("/admin/clear_chat")
def admin_clear_chat():
    d=load(); u=cur_user(d)
    if is_admin(u):
        d["global_chat"]=[]
        for p in d.get("posts", []):
            p["chat"]=[]
        save(d)
    return redirect("/admin")





@app.route("/admin/delete_post/<pid>")
def admin_delete_post(pid):
    d=load(); u=cur_user(d)
    if is_admin(u):
        d["posts"]=[p for p in d.get("posts", []) if p.get("id") != pid]
        save(d)
    return redirect("/admin")

@app.route("/admin/clear_posts/<category>")
def admin_clear_posts_category(category):
    d=load(); u=cur_user(d)
    if is_admin(u) and category in ["사냥","파밍","600퀘","승급지원"]:
        d["posts"]=[p for p in d.get("posts", []) if p.get("category") != category]
        save(d)
    return redirect("/admin")

@app.route("/admin/clear_posts")
def admin_clear_posts():
    d=load(); u=cur_user(d)
    if is_admin(u):
        d["posts"]=[]
        save(d)
    return redirect("/admin")


@app.route("/admin/notice", methods=["POST"])
def admin_notice_save():
    d = load()
    u = cur_user(d)
    if is_admin(u):
        d.setdefault("settings", {})["notice"] = {
            "title": request.form.get("notice_title", "").strip() or "문파 공지사항",
            "text": request.form.get("notice_text", "").strip(),
            "updated_at": now().isoformat(timespec="seconds")
        }
        save(d)
    return redirect("/admin")

@app.route("/admin/password", methods=["POST"])
def admin_password():
    d=load(); u=cur_user(d)
    if is_admin(u):
        pw=request.form.get("admin_password","").strip()
        if pw:
            d.setdefault("settings", {})["admin_password"]=pw
            save(d)
    return redirect("/admin")

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
        admin_count = sum(1 for x in d["users"] if x.get("status")=="approved" and x.get("role") in ["관리자","부문파장","문파장","최고관리자"])
        for x in d["users"]:
            if x["id"]==uid:
                # 마지막 관리자 또는 본인을 일반으로 내리면 관리자 페이지를 잃을 수 있어서 차단
                if role == "일반" and (admin_count <= 1 or uid == u.get("id")):
                    break
                x["role"]=role
        save(d)
    return redirect("/admin")



@app.route("/api/farm_alerts")
def api_farm_alerts():
    d = load()
    # 호출 시점에도 채팅 알림 기록 처리
    if farm_alert_tick(d):
        save(d)
    return {"ok": True, "alerts": farm_alert_status(d)}

@app.route("/health")
def health():
    return {"ok": True, "version": APP_VERSION}

if __name__ == "__main__":
    port = int(os.environ.get("PORT","7777"))
    app.run(host="0.0.0.0", port=port)

@app.route("/leave_participant/<pid>")
def leave_participant(pid):
    d = load()
    u = cur_user(d)
    p = find_post(d, pid)
    if not approved(u) or not p or p.get("closed"):
        return redirect("/")
    p["participants"] = [a for a in p.get("participants", []) if a.get("uid") != u.get("id")]
    # 파밍 정산 체크에서도 제거
    ids_to_remove = []
    for c in u.get("chars", []):
        ids_to_remove.append(c.get("id"))
    ids_to_remove.append(u.get("id"))
    p["early_ids"] = [x for x in p.get("early_ids", []) if x not in ids_to_remove]
    p["late_ids"] = [x for x in p.get("late_ids", []) if x not in ids_to_remove]
    refresh_post_status_after_member_change(d, p)
    save(d)
    return redirect("/")

