"""DataAnalyst AI - Streamlit UI for the car company's Text-to-SQL agent.

Run:  streamlit run app.py
"""

import html
import numbers
import os
import re
import uuid
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

import streamlit as st  # noqa: E402
from langgraph.types import Command  # noqa: E402

from agent.graph import build_graph  # noqa: E402
from agent.nodes import profile_dataframe  # noqa: E402
from agent.state import initial_state  # noqa: E402
from charts import CHART_TITLES_HE, build_chart, overview_trend  # noqa: E402
from database.executor import MAX_ROWS, QUERY_TIMEOUT_SEC, run_query  # noqa: E402

st.set_page_config(page_title="DataAnalyst AI · חברת הרכבים", page_icon="◆", layout="wide",
                   initial_sidebar_state="expanded")

# (category, question)
EXAMPLE_QUESTIONS = [
    ("עובדים", "מי העובד שמכר הכי הרבה רכבים ב-2024?"),
    ("סניפים", "איזה סניף הכניס הכי הרבה כסף השנה?"),
    ("מוצרים", "מה הרכב הנמכר ביותר לפי קטגוריה?"),
    ("גיאוגרפיה", "השווה מכירות בין המדינות"),
    ("מגמות", "מה המגמה החודשית של המכירות ב-3 שנים האחרונות?"),
]

PIPELINE = ["הבנת השאלה", "בניית שאילתה", "בדיקת בטיחות", "אישור מנהל", "הרצה וניתוח"]

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
MONTHS_HE_FULL = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר",
                  "נובמבר", "דצמבר"]

# Lucide-style line icons (24x24, stroke = currentColor)
_ICON_PATHS = {
    "logo": '<path d="M4 20V12"/><path d="M9.3 20V8"/><path d="M14.6 20v-5"/><path d="M20 20V4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "arrow": '<path d="M19 12H5"/><path d="m12 19-7-7 7-7"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "rows": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/>',
    "hand": '<path d="M18 11V6a2 2 0 0 0-4 0v5M14 10V4a2 2 0 0 0-4 0v6M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>',
    "db": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
}


def icon(name: str, size: int = 16, sw: float = 1.7) -> str:
    return (f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{_ICON_PATHS[name]}</svg>')


# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------

_CATEGORY_CSS = "\n".join(
    f'.st-key-sug_{i} button::after {{ content: "{cat}"; }}' for i, (cat, _) in enumerate(EXAMPLE_QUESTIONS)
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Hebrew:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --bg: #09090B;
  --panel: #111114;
  --panel-2: #16161A;
  --hover: #1B1B20;
  --line: #222228;
  --line-2: #2C2C33;
  --tx: #EDEDF0;
  --tx-2: #A0A0AB;
  --tx-3: #686873;
  --acc: #7B93FF;
  --acc-soft: rgba(123,147,255,.12);
  --amber: #E8B65A;
  --amber-soft: rgba(232,182,90,.12);
  --green: #3DD68C;
  --green-soft: rgba(61,214,140,.12);
  --red: #FF6369;
  --red-soft: rgba(255,99,105,.10);
  --r-sm: 8px; --r: 12px; --r-lg: 16px;
  --font: 'IBM Plex Sans Hebrew', 'Heebo', system-ui, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, monospace;
}

/* ============ Base ============ */
html, body, .stApp, .stMarkdown, p, li, label, h1, h2, h3, h4, input, textarea, button,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] div, [data-testid="stMarkdownContainer"] {
  font-family: var(--font) !important;
}
[data-testid="stIconMaterial"] { font-family: "Material Symbols Rounded" !important; }
.stApp { background: var(--bg); color: var(--tx); -webkit-font-smoothing: antialiased; }
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
[data-testid="stMain"] .block-container, [data-testid="stMainBlockContainer"] {
  padding: 0 40px 72px !important; max-width: 1180px; direction: rtl; text-align: right;
}
[data-testid="stVerticalBlock"] { gap: 0.75rem; }
::selection { background: rgba(123,147,255,.3); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #26262C; border-radius: 10px; border: 3px solid var(--bg); }
[data-testid="stMarkdownContainer"] { direction: rtl; text-align: right; }
.ic { flex-shrink: 0; display: inline-block; vertical-align: middle; }
.num { font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
.mono { font-family: var(--mono) !important; }

/* ============ App shell: sidebar on the right ============ */
[data-testid="stAppViewContainer"] { flex-direction: row-reverse; }
section[data-testid="stSidebar"] {
  background: #0C0C0E !important; border-left: 1px solid var(--line) !important; border-right: none !important;
  width: 284px !important; min-width: 284px !important;
}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarHeader"], [data-testid="stExpandSidebarButton"] { display: none !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { direction: rtl; text-align: right; padding: 18px 14px 18px; }
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 2px; }

.sb-brand { display:flex; align-items:center; gap:11px; padding: 4px 6px 18px; }
.sb-mark { width:34px; height:34px; border-radius:9px; display:grid; place-items:center; color: var(--bg);
  background: linear-gradient(160deg, #F4F4F6, #BDBDC6); box-shadow: 0 1px 0 rgba(255,255,255,.4) inset, 0 4px 14px rgba(0,0,0,.5); }
.sb-name { font-weight:600; font-size:.95rem; color: var(--tx); letter-spacing:-.1px; line-height:1.2; }
.sb-ws { font-size:.76rem; color: var(--tx-3); }
.sb-label { font-size:.72rem; font-weight:500; color: var(--tx-3); padding: 18px 8px 6px; display:flex; justify-content:space-between; }
.sb-label .mono { font-size:.68rem; }
.sb-empty { font-size:.82rem; color: var(--tx-3); padding: 6px 8px; line-height:1.6; }

section[data-testid="stSidebar"] .stMarkdown { margin-bottom: 0 !important; }
section[data-testid="stSidebar"] .stButton, section[data-testid="stSidebar"] [data-testid="stElementContainer"] { width: 100% !important; }
section[data-testid="stSidebar"] .stButton button {
  width: 100%; min-height: 34px; padding: 6px 10px; justify-content: flex-start; text-align: right;
  background: transparent !important; border: 1px solid transparent !important; border-radius: var(--r-sm); color: var(--tx-2) !important; box-shadow:none;
}
section[data-testid="stSidebar"] .stButton button > div { justify-content: flex-start; width: 100%; }
section[data-testid="stSidebar"] .stButton button p {
  font-size: .85rem !important; font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 232px;
}
section[data-testid="stSidebar"] .stButton button:hover { background: var(--hover) !important; color: var(--tx) !important; }
section[data-testid="stSidebar"] .stButton button:focus:not(:active) { border-color: transparent; color: var(--tx); }
[class*="st-key-hist_"] button p::before { content:""; display:inline-block; width:6px; height:6px; border-radius:50%;
  margin-left: 9px; vertical-align: middle; background: var(--tx-3); }
[class*="st-key-hist_ok"] button p::before { background: var(--green); }
[class*="st-key-hist_wait"] button p::before { background: var(--amber); }
[class*="st-key-hist_err"] button p::before { background: var(--red); }
section[data-testid="stSidebar"] .st-key-new_side button {
  background: var(--panel-2) !important; border: 1px solid var(--line-2) !important; color: var(--tx) !important; justify-content: center; min-height: 38px; margin-bottom: 6px;
}
section[data-testid="stSidebar"] .st-key-new_side button:hover { background: var(--hover) !important; border-color: #3A3A42 !important; }
section[data-testid="stSidebar"] .st-key-new_side button > div { justify-content: center; }
section[data-testid="stSidebar"] .st-key-new_side button p { font-weight: 500 !important; }
section[data-testid="stSidebar"] .st-key-clear_hist button p { color: var(--tx-3); font-size: .78rem !important; }

.sb-sys { margin-top: 18px; border: 1px solid var(--line); border-radius: var(--r); background: var(--panel); padding: 4px 12px; }
.sb-sys .r { display:flex; align-items:center; justify-content:space-between; gap:8px; padding: 9px 0; font-size:.78rem; color: var(--tx-3); }
.sb-sys .r + .r { border-top: 1px solid var(--line); }
.sb-sys .r span { display:flex; align-items:center; gap:7px; }
.sb-sys .r b { font-weight:500; color: var(--tx-2); }
.sb-sys .mono { font-size:.72rem; color: var(--tx-2); }

/* ============ Top bar ============ */
.tb { display:flex; align-items:center; justify-content:space-between; height: 60px; margin: 0 0 8px;
  border-bottom: 1px solid var(--line); }
.tb-crumb { display:flex; align-items:center; gap:8px; font-size:.86rem; color: var(--tx-3); }
.tb-crumb b { color: var(--tx); font-weight:500; }
.tb-crumb .sep { color: #3A3A42; }
.tb-right { display:flex; align-items:center; gap:8px; }
.badge { display:inline-flex; align-items:center; gap:6px; height: 26px; padding: 0 10px; border-radius: 999px; font-size:.76rem;
  font-weight:500; color: var(--tx-2); border: 1px solid var(--line-2); background: var(--panel); white-space: nowrap; }
.badge .dot { width:6px; height:6px; border-radius:50%; background: var(--green); box-shadow: 0 0 0 3px var(--green-soft); }
.badge.off .dot { background: var(--red); box-shadow: 0 0 0 3px var(--red-soft); }
.badge.acc { color: #C3CEFF; border-color: rgba(123,147,255,.3); background: var(--acc-soft); }
.badge.amb { color: #F3D9A4; border-color: rgba(232,182,90,.3); background: var(--amber-soft); }
.badge.grn { color: #A6F0CB; border-color: rgba(61,214,140,.28); background: var(--green-soft); }

/* ============ Hero ============ */
.hero { padding: 56px 0 26px; }
.hero-date { font-size: .84rem; color: var(--tx-3); margin-bottom: 10px; }
.hero .h1 { font-size: 2.35rem; font-weight: 600; letter-spacing: -.8px; color: var(--tx); margin: 0; line-height: 1.2; padding: 0; }
.hero p { font-size: 1.02rem; color: var(--tx-2); margin: 10px 0 0; max-width: 620px; line-height: 1.65; }

/* ============ Composer ============ */
.st-key-composer { background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--r-lg); padding: 6px 6px 10px;
  box-shadow: 0 1px 0 rgba(255,255,255,.03) inset, 0 24px 48px -24px rgba(0,0,0,.8); transition: border-color .2s, box-shadow .2s; }
.st-key-composer:focus-within { border-color: #44444E; box-shadow: 0 0 0 4px rgba(123,147,255,.10), 0 24px 48px -24px rgba(0,0,0,.8); }
.st-key-composer [data-testid="stForm"] { border: none; padding: 0; }
.st-key-composer [data-baseweb="textarea"], .st-key-composer [data-baseweb="base-input"] { background: transparent !important; border: none !important; }
.st-key-composer [data-testid="stTextArea"] > div, .st-key-composer [data-testid="stTextArea"] div[data-baseweb] { border: none !important; box-shadow: none !important; }
.st-key-composer textarea { direction: rtl; background: transparent !important; color: var(--tx) !important; font-size: 1.06rem !important;
  line-height: 1.65 !important; padding: 12px 14px 4px !important; resize: none; caret-color: var(--acc); }
.st-key-composer textarea::placeholder { color: #55555F !important; }
.st-key-composer [data-testid="InputInstructions"] { display: none; }
.cmp-meta { display:flex; align-items:center; gap:16px; padding: 0 12px; font-size:.78rem; color: var(--tx-3); flex-wrap: wrap; }
.cmp-meta span { display:inline-flex; align-items:center; gap:6px; }
.kbd { font-family: var(--mono) !important; font-size:.68rem; color: var(--tx-2); padding: 1px 6px; border-radius: 5px;
  border: 1px solid var(--line-2); border-bottom-width: 2px; background: var(--panel-2); }
.st-key-composer [data-testid="stFormSubmitButton"] { display:flex; justify-content:flex-start; padding-left: 4px; }

/* ============ Buttons ============ */
.stButton button, [data-testid="stFormSubmitButton"] button, .stDownloadButton button {
  border-radius: 10px; min-height: 38px; font-weight: 500; transition: background .15s, border-color .15s, color .15s, transform .15s; box-shadow: none;
}
.stButton button p, [data-testid="stFormSubmitButton"] button p, .stDownloadButton button p { font-size: .88rem; font-weight: 500; }
button[kind^="primary"] { background: #EDEDF0 !important; color: #09090B !important; border: 1px solid #EDEDF0 !important; }
button[kind^="primary"] p, button[kind^="primary"] span { color: #09090B !important; }
button[kind^="primary"]:hover { background: #FFFFFF !important; border-color: #FFFFFF !important; transform: translateY(-1px); }
button[kind^="primary"]:active { transform: none; }
button[kind^="secondary"] { background: var(--panel) !important; border: 1px solid var(--line-2) !important; color: var(--tx) !important; }
button[kind^="secondary"]:hover { background: var(--hover) !important; border-color: #3A3A42 !important; color: var(--tx) !important; }

/* ============ Section head ============ */
.sh { display:flex; align-items:flex-end; justify-content:space-between; gap: 12px; margin: 40px 0 4px; }
.sh .t { font-size: .95rem; font-weight: 600; color: var(--tx); }
.sh .s { font-size: .8rem; color: var(--tx-3); margin-top: 2px; }

/* ============ Suggestions list ============ */
.st-key-suggest { border: 1px solid var(--line); border-radius: var(--r-lg); background: var(--panel); overflow: hidden; gap: 0 !important; }
.st-key-suggest [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-key-suggest .stButton + .stButton, .st-key-suggest [data-testid="stElementContainer"] + [data-testid="stElementContainer"] { border-top: 1px solid var(--line); }
.st-key-suggest .stButton button { width: 100%; min-height: 52px; border: none !important; border-radius: 0 !important; background: transparent !important;
  justify-content: flex-start; padding: 0 18px; position: relative; color: var(--tx-2) !important; }
.st-key-suggest .stButton button p { font-size: .93rem; font-weight: 400; color: var(--tx); }
.st-key-suggest .stButton button::before { content: "←"; position: absolute; left: 18px; color: var(--tx-3); transition: transform .2s, color .2s; font-size: .95rem; }
.st-key-suggest .stButton button::after { position: absolute; left: 50px; font-size: .72rem; color: var(--tx-3); border: 1px solid var(--line-2);
  border-radius: 999px; padding: 1px 9px; }
.st-key-suggest .stButton button > div { width: 100%; justify-content: flex-start; }
.st-key-suggest .stButton button p { text-align: right; }
.st-key-suggest .stButton button:hover { background: var(--hover) !important; }
.st-key-suggest .stButton button:hover::before { color: var(--tx); transform: translateX(-4px); }
__CATEGORY_CSS__

/* ============ Cards ============ */
.card { background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); }
.card-h { display:flex; align-items:center; justify-content:space-between; padding: 16px 20px 0; }
.card-h .t { font-size: .88rem; font-weight: 600; color: var(--tx); }
.card-h .s { font-size: .76rem; color: var(--tx-3); }

/* KPI strip */
.kpis { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); overflow: hidden; }
.kpi { padding: 18px 20px 18px; min-width: 0; }
.kpi + .kpi { border-right: 1px solid var(--line); }
.kpi .l { font-size: .78rem; color: var(--tx-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi .v { font-size: 1.65rem; font-weight: 600; letter-spacing: -.6px; color: var(--tx); margin-top: 6px; line-height: 1.15;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }
.kpi .v small { font-size: .95rem; color: var(--tx-3); font-weight: 500; margin-right: 1px; }
.kpi .d { display:flex; align-items:center; gap:6px; margin-top: 8px; font-size: .76rem; color: var(--tx-3); white-space: nowrap; overflow:hidden; text-overflow: ellipsis; }
.delta { display:inline-flex; align-items:center; gap:3px; padding: 1px 7px; border-radius: 6px; font-weight: 600; font-size: .72rem; font-variant-numeric: tabular-nums; direction: ltr; }
.delta.up { color: var(--green); background: var(--green-soft); }
.delta.down { color: var(--red); background: var(--red-soft); }

/* Ranked list */
.rank { padding: 10px 20px 14px; }
.rank .row { display:grid; grid-template-columns: 18px 1fr auto; align-items:center; gap: 12px; padding: 9px 0; }
.rank .row + .row { border-top: 1px solid var(--line); }
.rank .n { font-size: .74rem; color: var(--tx-3); font-family: var(--mono) !important; }
.rank .nm { font-size: .88rem; color: var(--tx); }
.rank .nm span { color: var(--tx-3); font-size: .76rem; }
.rank .bar { height: 4px; border-radius: 4px; background: var(--line); margin-top: 7px; overflow: hidden; }
.rank .bar i { display:block; height:100%; border-radius: 4px; background: var(--acc); }
.rank .row:first-child .bar i { background: var(--amber); }
.rank .val { font-size: .86rem; color: var(--tx-2); font-variant-numeric: tabular-nums; }

/* Chart cards (st.container keys) */
.st-key-trend, [class*="st-key-cc_"] { background: var(--panel); border: 1px solid var(--line); border-radius: var(--r-lg); padding: 0 6px 6px; gap: 0 !important; }
[data-testid="stPlotlyChart"] { background: transparent; border: none; }
.cc-h { padding: 16px 14px 4px; }
.cc-h .t { font-size: .88rem; font-weight: 600; color: var(--tx); }
.cc-h .s { font-size: .76rem; color: var(--tx-3); margin-top: 2px; }

/* ============ Progress track ============ */
.track { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 6px; margin: 22px 0 6px; }
.track .seg .bar { height: 3px; border-radius: 3px; background: var(--line-2); overflow: hidden; position: relative; }
.track .seg.done .bar { background: var(--acc); }
.track .seg.active .bar { background: var(--line-2); }
.track .seg.active .bar::after { content:""; position:absolute; inset:0; width: 40%; background: var(--amber); border-radius: 3px; animation: slide 1.6s ease-in-out infinite; }
.track .seg.fail .bar { background: var(--red); }
.track .lb { display:flex; align-items:center; gap:6px; margin-top: 9px; font-size: .76rem; color: var(--tx-3); white-space: nowrap; overflow:hidden; text-overflow: ellipsis; }
.track .seg.done .lb { color: var(--tx-2); }
.track .seg.active .lb { color: var(--amber); }
.track .seg.fail .lb { color: var(--red); }
.track .lb .mono { font-size: .68rem; opacity: .7; }

/* ============ Approval ============ */
.plan { margin-top: 26px; background: var(--panel); border: 1px solid var(--line-2); border-radius: var(--r-lg); overflow: hidden; animation: rise .35s cubic-bezier(.2,.8,.2,1); }
.plan-h { display:flex; align-items:center; justify-content:space-between; gap: 12px; padding: 16px 22px; border-bottom: 1px solid var(--line); background: var(--panel-2); }
.plan-h .l { display:flex; align-items:center; gap: 12px; }
.plan-ic { width: 34px; height: 34px; border-radius: 9px; display:grid; place-items:center; color: var(--amber); background: var(--amber-soft); border: 1px solid rgba(232,182,90,.25); }
.plan-h .t { font-size: .95rem; font-weight: 600; color: var(--tx); }
.plan-h .s { font-size: .78rem; color: var(--tx-3); }
.plan-b { display:grid; grid-template-columns: minmax(0, 1fr) 270px; }
.plan-main { padding: 24px 26px 26px; }
.plan-q { font-size: .8rem; color: var(--tx-3); margin-bottom: 8px; }
.plan-q b { color: var(--tx-2); font-weight: 500; }
.plan-x { font-size: 1.28rem; line-height: 1.75; color: var(--tx); font-weight: 400; letter-spacing: -.1px; }
.plan-side { border-right: 1px solid var(--line); padding: 20px 20px; background: rgba(255,255,255,.012); }
.plan-side .hd { font-size: .74rem; color: var(--tx-3); margin-bottom: 10px; }
.chk { display:flex; align-items:center; gap: 10px; padding: 7px 0; font-size: .84rem; color: var(--tx-2); }
.chk .ok { width: 20px; height: 20px; border-radius: 6px; display:grid; place-items:center; color: var(--green); background: var(--green-soft); }

/* ============ Report ============ */
.rep-h { padding: 34px 0 6px; animation: rise .35s cubic-bezier(.2,.8,.2,1); }
.rep-eb { display:flex; align-items:center; gap: 8px; font-size: .8rem; color: var(--tx-3); margin-bottom: 10px; }
.rep-h .h1 { font-size: 1.9rem; font-weight: 600; letter-spacing: -.6px; color: var(--tx); margin: 0; padding: 0; line-height: 1.3; }
.rep-meta { display:flex; gap: 6px; flex-wrap: wrap; margin-top: 14px; }
.summary { position: relative; margin-top: 18px; padding: 22px 26px; border-radius: var(--r-lg); background: var(--panel); border: 1px solid var(--line); }
.summary::before { content:""; position:absolute; right: 0; top: 20px; bottom: 20px; width: 2px; border-radius: 2px; background: var(--amber); }
.summary .lbl { display:flex; align-items:center; gap: 7px; font-size: .76rem; font-weight: 500; color: var(--amber); margin-bottom: 8px; }
.summary .body { font-size: 1.04rem; line-height: 1.9; color: #D9D9DE; white-space: pre-line; }
.bignum { padding: 44px 20px; text-align: center; }
.bignum .l { font-size: .84rem; color: var(--tx-3); }
.bignum .v { font-size: 4.2rem; font-weight: 600; letter-spacing: -2px; color: var(--tx); line-height: 1.1; margin-top: 8px; font-variant-numeric: tabular-nums; }

.callout { display:flex; gap: 14px; align-items:flex-start; padding: 18px 20px; border-radius: var(--r-lg); border: 1px solid var(--line-2); background: var(--panel); margin-top: 26px; }
.callout .ci { width: 32px; height: 32px; border-radius: 9px; display:grid; place-items:center; flex-shrink: 0; }
.callout .t { font-weight: 600; font-size: .93rem; color: var(--tx); }
.callout .s { font-size: .86rem; color: var(--tx-2); margin-top: 3px; line-height: 1.6; }
.callout.err { border-color: rgba(255,99,105,.28); } .callout.err .ci { color: var(--red); background: var(--red-soft); }
.callout.info .ci { color: var(--tx-2); background: var(--hover); }

/* ============ Streamlit widgets ============ */
.stTabs [data-baseweb="tab-list"] { gap: 22px; border-bottom: 1px solid var(--line); background: transparent; }
.stTabs [data-baseweb="tab"] { height: 42px; padding: 0 2px; background: transparent; color: var(--tx-3); }
.stTabs [data-baseweb="tab"] p { font-size: .88rem; font-weight: 500; }
.stTabs [aria-selected="true"] { color: var(--tx) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--tx) !important; height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 18px; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: var(--r); overflow: hidden; }
[data-testid="stExpander"] details { background: var(--panel); border: 1px solid var(--line) !important; border-radius: var(--r) !important; }
[data-testid="stExpander"] summary { padding: 12px 16px; }
[data-testid="stExpander"] summary p { font-size: .86rem; color: var(--tx-2); font-weight: 500; }
[data-testid="stExpander"] summary:hover p { color: var(--tx); }
[data-testid="stCode"] pre { background: #0C0C0F !important; border: 1px solid var(--line); border-radius: var(--r); padding: 16px 18px !important; }
[data-testid="stCode"] code { font-family: var(--mono) !important; font-size: .84rem; line-height: 1.7; direction: ltr; text-align: left; }
[data-testid="stCaptionContainer"] p { color: var(--tx-3); font-size: .78rem; }
[data-testid="stSpinner"] { margin-top: 20px; padding: 14px 18px; border: 1px solid var(--line-2); border-radius: var(--r); background: var(--panel);
  display: flex; color: var(--tx-2); }
[data-testid="stSpinner"] p { font-size: .88rem; color: var(--tx-2); }
[data-testid="stSpinner"] i { border-color: var(--line-2) !important; border-top-color: var(--amber) !important; }
[data-testid="stToast"] { background: var(--panel-2); border: 1px solid var(--line-2); }

@keyframes rise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes slide { 0% { right: -40%; } 100% { right: 100%; } }
.rise { animation: rise .4s cubic-bezier(.2,.8,.2,1) both; }

@media (max-width: 1000px) {
  [data-testid="stMain"] .block-container, [data-testid="stMainBlockContainer"] { padding: 0 18px 60px !important; }
  .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .kpi:nth-child(3) { border-right: none; }
  .kpi:nth-child(n+3) { border-top: 1px solid var(--line); }
  .plan-b { grid-template-columns: 1fr; }
  .plan-side { border-right: none; border-top: 1px solid var(--line); }
  .hero .h1 { font-size: 1.8rem; }
  .tb-right .badge.hide-sm { display: none; }
}
</style>
""".replace("__CATEGORY_CSS__", _CATEGORY_CSS),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Graph + session state
# ---------------------------------------------------------------------------

@st.cache_resource
def get_graph():
    """One compiled graph (and one MemorySaver) shared across reruns."""
    return build_graph()


graph = get_graph()

ss = st.session_state
ss.setdefault("stage", "idle")          # idle | awaiting_approval | done
ss.setdefault("thread_id", None)
ss.setdefault("pending", None)          # interrupt payload
ss.setdefault("final", None)            # final graph state
ss.setdefault("history", [])            # [{question, time, status}]
ss.setdefault("question_input", "")
ss.setdefault("asked_at", None)


def _config() -> dict:
    return {"configurable": {"thread_id": ss.thread_id}}


def _record_history(question: str, status: str) -> None:
    ss.history = [h for h in ss.history if h["question"] != question]
    ss.history.insert(0, {"question": question, "time": datetime.now().strftime("%H:%M"), "status": status})
    ss.history = ss.history[:12]


def _after_run(question: str) -> None:
    """Inspect the checkpoint: paused at the interrupt, or finished."""
    snapshot = graph.get_state(_config())
    interrupts = [i for t in snapshot.tasks for i in (t.interrupts or [])]
    if snapshot.next and interrupts:
        ss.stage, ss.pending, ss.final = "awaiting_approval", interrupts[0].value, None
        _record_history(question, "ממתין לאישור")
    else:
        ss.stage, ss.pending, ss.final = "done", None, snapshot.values
        status = (snapshot.values.get("final_response") or {}).get("status") or ("error" if snapshot.values.get("error") else "success")
        _record_history(question, {"success": "✓", "cancelled": "בוטל", "failed": "נכשל"}.get(status, "שגיאה"))


def ask(question: str) -> None:
    question = question.strip()
    if not question:
        st.toast("נא להקליד שאלה", icon=":material/info:")
        return
    ss.thread_id = str(uuid.uuid4())
    ss.asked_at = datetime.now()
    with st.spinner("הסוכן מנתח את השאלה ובונה שאילתה…"):
        try:
            graph.invoke(initial_state(question), _config())
        except Exception as exc:
            ss.stage, ss.final = "done", {"question": question, "error": f"שגיאה בהפעלת הסוכן: {exc}"}
            _record_history(question, "שגיאה")
            return
    _after_run(question)


def resume(approved: bool) -> None:
    question = (ss.pending or {}).get("question", "")
    msg = "מריץ את השאילתה, בוחר ויזואליזציות ומפיק תובנות…" if approved else "מבטל…"
    with st.spinner(msg):
        try:
            graph.invoke(Command(resume=approved), _config())
        except Exception as exc:
            ss.stage, ss.final = "done", {"question": question, "error": f"שגיאה בהרצה: {exc}"}
            return
    _after_run(question)


def set_question(q: str) -> None:
    ss.question_input = q
    ss.auto_ask = q


def reset() -> None:
    ss.stage, ss.pending, ss.final, ss.question_input = "idle", None, None, ""


# ---------------------------------------------------------------------------
# Formatting + render helpers
# ---------------------------------------------------------------------------

def esc(x) -> str:
    return html.escape(str(x))


def pretty(col) -> str:
    return str(col).replace("_", " ").title()


def is_money(col) -> bool:
    return bool(re.search(r"price|revenue|amount|total|income|sales_value|salary|value", str(col), re.I))


def compact(v, money: bool = False) -> str:
    if not isinstance(v, numbers.Number):
        return esc(v)
    a, sign = abs(float(v)), "-" if v < 0 else ""
    pre = '<small>$</small>' if money else ""
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div * (1 if div >= 1e6 else 10):
            n = f"{a / div:.2f}".rstrip("0").rstrip(".")
            return f"{sign}{pre}{n}<small>{suf}</small>"
    n = f"{a:,.0f}" if float(a).is_integer() or a >= 100 else f"{a:,.2f}"
    return f"{sign}{pre}{n}"


def plain(v, money: bool = False) -> str:
    return re.sub(r"<[^>]+>", "", compact(v, money))


def delta(cur: float, prev: float) -> str:
    if not prev:
        return ""
    pct = (cur - prev) / prev * 100
    cls, arrow = ("up", "↑") if pct >= 0 else ("down", "↓")
    return f'<span class="delta {cls}">{arrow} {abs(pct):.1f}%</span>'


def kpi_strip(tiles: list[tuple[str, str, str]]) -> str:
    cells = "".join(f'<div class="kpi"><div class="l">{l}</div><div class="v">{v}</div><div class="d">{d}</div></div>'
                    for l, v, d in tiles[:4])
    return f'<div class="kpis rise">{cells}</div>'


def section(title: str, sub: str = "", right: str = "") -> None:
    st.markdown(f'<div class="sh"><div><div class="t">{esc(title)}</div>'
                f'{f"<div class=s>{esc(sub)}</div>" if sub else ""}</div><div>{right}</div></div>',
                unsafe_allow_html=True)


def track(stage: str, final: dict | None) -> str:
    """Five-segment pipeline progress."""
    f = final or {}
    fr = f.get("final_response") or {}
    states = ["todo"] * 5
    if stage == "awaiting_approval":
        states = ["done", "done", "done", "active", "todo"]
    elif stage == "done":
        if fr.get("status") == "cancelled":
            states = ["done", "done", "done", "fail", "todo"]
        elif f.get("results") is not None:
            states = ["done"] * 5
        elif f.get("sql_query"):
            states = ["done", "done", "done", "done", "fail"]
        else:
            states = ["done", "fail", "todo", "todo", "todo"]
    segs = []
    for i, (name, cls) in enumerate(zip(PIPELINE, states), 1):
        mark = {"done": icon("check", 12, 2.4), "fail": icon("x", 12, 2.4)}.get(cls, f'<span class="mono">0{i}</span>')
        segs.append(f'<div class="seg {cls}"><div class="bar"></div><div class="lb">{mark}{name}</div></div>')
    return f'<div class="track">{"".join(segs)}</div>'


def result_kpis(df, final: dict) -> str:
    p = profile_dataframe(df)
    nums, cats = p["numeric_cols"], p["cat_cols"] or p["date_cols"]
    tiles = [("שורות", f'<span class="num">{len(df):,}</span>', f"{len(df.columns)} עמודות")]
    if nums and len(df) == 1:
        row = df.iloc[0]
        if cats:
            tiles.append((esc(pretty(cats[0])), esc(row[cats[0]]), "התוצאה שנמצאה"))
        for col in nums[:3]:
            tiles.append((esc(pretty(col)), compact(row[col], is_money(col)), f"{row[col]:,.2f}".rstrip("0").rstrip(".")))
    elif nums:
        col = nums[0]
        s, money = df[col].dropna(), is_money(col)
        tiles.append((f"סה״כ · {esc(pretty(col))}", compact(s.sum(), money), "סכום כל השורות"))
        tiles.append((f"ממוצע · {esc(pretty(col))}", compact(s.mean(), money),
                      f"טווח {plain(s.min(), money)} – {plain(s.max(), money)}"))
        if cats and len(s):
            top = df.loc[df[col].idxmax()]
            tiles.append(("המוביל", esc(top[cats[0]]), f"{esc(pretty(col))}: {plain(top[col], money)}"))
    elif cats:
        tiles.append((f"ערכים ייחודיים · {esc(pretty(cats[0]))}", f"{df[cats[0]].nunique():,}", ""))
    if len(tiles) < 4:
        tiles.append(("תיקון עצמי", str(final.get("retry_count") or 0), "ניסיונות תיקון SQL"))
    return kpi_strip(tiles)


@st.cache_data(ttl=600, show_spinner=False)
def load_overview():
    """Live snapshot of the business for the home screen (read-only queries)."""
    yearly = run_query("SELECT CAST(strftime('%Y', sale_date) AS INT) y, COUNT(*) n, SUM(final_price) rev "
                       "FROM sales GROUP BY y ORDER BY y")
    year = int(yearly["y"].max())
    monthly = run_query("SELECT CAST(strftime('%Y', sale_date) AS INT) y, CAST(strftime('%m', sale_date) AS INT) m, "
                        f"SUM(final_price) rev FROM sales WHERE strftime('%Y', sale_date) IN ('{year}', '{year - 1}') "
                        "GROUP BY y, m")
    branches = run_query("SELECT b.city, b.country, SUM(s.final_price) rev FROM sales s JOIN branches b "
                         f"ON b.id = s.branch_id WHERE strftime('%Y', s.sale_date) = '{year}' "
                         "GROUP BY b.id ORDER BY rev DESC LIMIT 5")
    counts = run_query("SELECT (SELECT COUNT(*) FROM customers) customers, (SELECT COUNT(*) FROM branches) branches, "
                       "(SELECT COUNT(DISTINCT country) FROM branches) countries")
    return year, yearly, monthly, branches, counts.iloc[0]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(f'<div class="sb-brand"><div class="sb-mark">{icon("logo", 18, 2.6)}</div>'
                '<div><div class="sb-name">DataAnalyst AI</div><div class="sb-ws">חברת הרכבים · סביבת ניהול</div></div></div>',
                unsafe_allow_html=True)
    st.button("ניתוח חדש", key="new_side", on_click=reset, icon=":material/add:", width="stretch")

    st.markdown(f'<div class="sb-label"><span>אחרונים</span><span class="mono">{len(ss.history) or ""}</span></div>',
                unsafe_allow_html=True)
    if not ss.history:
        st.markdown('<div class="sb-empty">השאלות שתשאל יופיעו כאן.</div>', unsafe_allow_html=True)
    for i, h in enumerate(ss.history):
        code = {"✓": "ok", "ממתין לאישור": "wait", "בוטל": "cancel"}.get(h["status"], "err")
        st.button(h["question"], key=f"hist_{code}_{i}", help=f"{h['time']} · {h['status']} · לחץ כדי לשאול שוב",
                  on_click=set_question, args=(h["question"],))
    if ss.history and st.button("נקה היסטוריה", key="clear_hist"):
        ss.history = []
        st.rerun()

    prompt_version = os.getenv("PROMPT_VERSION", "improved")
    tracing = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.getenv("LANGSMITH_API_KEY")
    st.markdown(
        f"""<div class="sb-sys">
  <div class="r"><span>{icon("cpu", 14)}מודל</span><b class="mono">gpt-4o-mini</b></div>
  <div class="r"><span>{icon("spark", 14)}פרומפט</span><b class="mono">{esc(prompt_version)}</b></div>
  <div class="r"><span>{icon("db", 14)}מקור נתונים</span><b class="mono">car_company.db</b></div>
  <div class="r"><span>{icon("lock", 14)}הרשאות</span><b>קריאה בלבד</b></div>
  <div class="r"><span>{icon("clock", 14)}LangSmith</span><b>{"פעיל" if tracing else "כבוי"}</b></div>
</div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------

has_key = bool(os.getenv("OPENAI_API_KEY"))
crumb = {"idle": "ניתוח חדש", "awaiting_approval": "ממתין לאישור", "done": "דוח ניתוח"}[ss.stage]
st.markdown(
    f"""<div class="tb">
  <div class="tb-crumb">חברת הרכבים <span class="sep">/</span> ניתוחים <span class="sep">/</span> <b>{crumb}</b></div>
  <div class="tb-right">
    <span class="badge hide-sm">{icon("lock", 12, 2)}קריאה בלבד</span>
    <span class="badge{'' if has_key else ' off'}"><span class="dot"></span>{'הסוכן מחובר' if has_key else 'חסר מפתח API'}</span>
  </div>
</div>""",
    unsafe_allow_html=True,
)

if not has_key:
    st.markdown(f'<div class="callout err">{"<div class=ci>" + icon("alert", 16) + "</div>"}<div><div class="t">לא הוגדר OPENAI_API_KEY</div>'
                '<div class="s">העתק את ‎.env.example‎ לקובץ ‎.env‎ והוסף את המפתח, ואז הפעל מחדש.</div></div></div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero + composer
# ---------------------------------------------------------------------------

if ss.stage == "idle":
    now = datetime.now()
    st.markdown(
        f"""<div class="hero rise">
  <div class="hero-date">יום {DAYS_HE[now.weekday()]}, {now.day} ב{MONTHS_HE_FULL[now.month - 1]} {now.year}</div>
  <div class="h1">על מה נרצה לקבל תשובה היום?</div>
  <p>שאל בעברית חופשית על מכירות, סניפים, עובדים ומלאי. הסוכן יבנה שאילתה, יבקש את אישורך, ויחזיר דוח עם גרפים ותובנות.</p>
</div>""",
        unsafe_allow_html=True,
    )
else:
    st.write("")

with st.container(key="composer"):
    with st.form("ask_form", clear_on_submit=False, border=False):
        question = st.text_area("השאלה שלך", key="question_input", height=88 if ss.stage == "idle" else 68,
                                label_visibility="collapsed", placeholder="לדוגמה: איזה סניף הכניס הכי הרבה כסף ב-2024?")
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f'<div class="cmp-meta"><span>{icon("shield", 13)}SELECT בלבד</span>'
                    f'<span>{icon("hand", 13)}שום דבר לא רץ בלי אישורך</span>'
                    '<span><span class="kbd">Ctrl</span><span class="kbd">Enter</span></span></div>',
                    unsafe_allow_html=True)
        submitted = c2.form_submit_button("נתח", type="primary", width="stretch", icon=":material/arrow_back:")

if ss.stage != "idle":
    st.markdown(track(ss.stage, ss.final), unsafe_allow_html=True)

if submitted or ss.get("auto_ask"):
    ask(ss.pop("auto_ask", None) or question)
    st.rerun()


# ---------------------------------------------------------------------------
# Home: suggestions + live business snapshot
# ---------------------------------------------------------------------------

if ss.stage == "idle":
    section("שאלות מוצעות", "לחיצה מריצה את הניתוח מיד")
    with st.container(key="suggest"):
        for i, (_, q) in enumerate(EXAMPLE_QUESTIONS):
            st.button(q, key=f"sug_{i}", on_click=set_question, args=(q,), width="stretch")

    try:
        year, yearly, monthly, branches, counts = load_overview()
    except Exception:
        year = None
    if year:
        cur, prev = yearly[yearly["y"] == year].iloc[0], yearly[yearly["y"] == year - 1]
        prev = prev.iloc[0] if len(prev) else None
        avg_cur = cur["rev"] / cur["n"]
        avg_prev = prev["rev"] / prev["n"] if prev is not None else 0
        section(f"תמונת מצב · {year}", "נתונים חיים ממסד הנתונים, בהשוואה לשנה הקודמת",
                f'<span class="badge grn"><span class="dot"></span>מעודכן</span>')
        st.markdown(kpi_strip([
            ("הכנסות", compact(cur["rev"], True), f'{delta(cur["rev"], prev["rev"] if prev is not None else 0)} מול {year - 1}'),
            ("רכבים שנמכרו", f'<span class="num">{int(cur["n"]):,}</span>', f'{delta(cur["n"], prev["n"] if prev is not None else 0)} מול {year - 1}'),
            ("עסקה ממוצעת", compact(avg_cur, True), f"{delta(avg_cur, avg_prev)} מול {year - 1}"),
            ("רשת", f'<span class="num">{int(counts["branches"])}</span> <small>סניפים</small>',
             f'{int(counts["countries"])} מדינות · {int(counts["customers"]):,} לקוחות'),
        ]), unsafe_allow_html=True)

        st.write("")
        c_trend, c_rank = st.columns([1.75, 1], gap="small")
        with c_trend:
            with st.container(key="trend"):
                st.markdown(f'<div class="cc-h"><div class="t">הכנסות חודשיות</div>'
                            f'<div class="s">{year} מול {year - 1}, בדולרים</div></div>', unsafe_allow_html=True)
                st.plotly_chart(overview_trend(monthly, year), width="stretch",
                                config={"displayModeBar": False}, key="ov_trend")
        with c_rank:
            top = branches["rev"].max()
            rows = "".join(
                f'<div class="row"><div class="n">{i:02d}</div><div><div class="nm">{esc(r.city)} <span>· {esc(r.country)}</span></div>'
                f'<div class="bar"><i style="width:{r.rev / top * 100:.0f}%"></i></div></div>'
                f'<div class="val">{plain(r.rev, True)}</div></div>'
                for i, r in enumerate(branches.itertuples(), 1)
            )
            st.markdown(f'<div class="card rise" style="height:100%"><div class="card-h"><div class="t">סניפים מובילים</div>'
                        f'<div class="s">לפי הכנסות {year}</div></div><div class="rank">{rows}</div></div>',
                        unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Approval (human_approval interrupt)
# ---------------------------------------------------------------------------

if ss.stage == "awaiting_approval" and ss.pending:
    p = ss.pending
    st.markdown(
        f"""<div class="plan">
  <div class="plan-h">
    <div class="l"><div class="plan-ic">{icon("shield", 17)}</div>
      <div><div class="t">תוכנית הביצוע מוכנה לאישורך</div><div class="s">שלב 4 מתוך 5 · השאילתה לא תורץ עד שתאשר</div></div></div>
    <span class="badge amb">ממתין לאישור</span>
  </div>
  <div class="plan-b">
    <div class="plan-main">
      <div class="plan-q">השאלה: <b>{esc(p.get('question', ''))}</b></div>
      <div class="plan-x">{esc(p.get('sql_explanation', ''))}</div>
    </div>
    <div class="plan-side">
      <div class="hd">בדיקות שעברו</div>
      <div class="chk"><span class="ok">{icon("check", 12, 2.6)}</span>שאילתת SELECT בלבד</div>
      <div class="chk"><span class="ok">{icon("check", 12, 2.6)}</span>חיבור למסד במצב קריאה</div>
      <div class="chk"><span class="ok">{icon("check", 12, 2.6)}</span>עד {MAX_ROWS:,} שורות</div>
      <div class="chk"><span class="ok">{icon("check", 12, 2.6)}</span>מגבלת זמן {QUERY_TIMEOUT_SEC} שניות</div>
    </div>
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    with st.expander("הצג את שאילתת ה-SQL", icon=":material/code:"):
        st.code(p.get("sql_query", ""), language="sql")
    b1, b2, _ = st.columns([1.1, 0.8, 4])
    if b1.button("אשר והרץ", type="primary", width="stretch", key="approve", icon=":material/check:"):
        resume(True)
        st.rerun()
    if b2.button("בטל", width="stretch", key="cancel"):
        resume(False)
        st.rerun()


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

if ss.stage == "done" and ss.final:
    final = ss.final
    fr = final.get("final_response") or {}
    df = final.get("results")

    if fr.get("status") == "cancelled":
        st.markdown(f'<div class="callout info"><div class="ci">{icon("hand", 16)}</div><div><div class="t">הניתוח בוטל</div>'
                    '<div class="s">השאילתה לא הורצה. אפשר לנסח את השאלה מחדש ולנסות שוב.</div></div></div>',
                    unsafe_allow_html=True)
    elif final.get("error") and fr.get("status") != "success":
        st.markdown(f'<div class="callout err"><div class="ci">{icon("alert", 16)}</div><div><div class="t">הניתוח לא הושלם</div>'
                    f'<div class="s">{esc(final["error"])}</div></div></div>', unsafe_allow_html=True)
        if final.get("sql_query"):
            with st.expander("השאילתה האחרונה שנוסתה", icon=":material/code:"):
                st.code(final["sql_query"], language="sql")
    elif df is not None:
        when = (ss.asked_at or datetime.now()).strftime("%H:%M")
        meta = (f'<span class="badge">{icon("rows", 12)}<span class="num">{len(df):,}</span> שורות</span>'
                f'<span class="badge">{len(df.columns)} עמודות</span>'
                f'<span class="badge grn">{icon("check", 12, 2.4)}אושר והורץ</span>')
        if final.get("retry_count"):
            meta += f'<span class="badge amb">תוקן אוטומטית ×{final["retry_count"]}</span>'
        st.markdown(f'<div class="rep-h"><div class="rep-eb">{icon("spark", 13)}דוח ניתוח · היום, {when}</div>'
                    f'<div class="h1">{esc(final.get("question", ""))}</div><div class="rep-meta">{meta}</div></div>',
                    unsafe_allow_html=True)

        if final.get("insights"):
            st.markdown(f'<div class="summary rise"><div class="lbl">{icon("spark", 13)}תקציר מנהלים</div>'
                        f'<div class="body">{esc(final["insights"])}</div></div>', unsafe_allow_html=True)

        if df.shape == (1, 1):
            value = df.iloc[0, 0]
            shown = compact(value, is_money(df.columns[0])) if isinstance(value, numbers.Number) else esc(value)
            st.markdown(f'<div class="card bignum rise" style="margin-top:16px"><div class="l">{esc(pretty(df.columns[0]))}</div>'
                        f'<div class="v">{shown}</div></div>', unsafe_allow_html=True)
            with st.expander("השאילתה שהורצה", icon=":material/code:"):
                st.caption(final.get("sql_explanation", ""))
                st.code(final.get("sql_query", ""), language="sql")
        else:
            if not df.empty:
                st.write("")
                st.markdown(result_kpis(df, final), unsafe_allow_html=True)
            st.write("")
            chart_types = final.get("chart_types") or []
            tabs = st.tabs((["ויזואליזציה"] if chart_types else []) + ["נתונים", "שאילתה"])
            t = iter(tabs)

            def chart_card(ctype: str, idx: int, height: int) -> None:
                fig = build_chart(df, ctype)
                raw = re.sub(r"<[^>]+>", "", str(fig.layout.title.text or ""))
                metric = raw.split(":", 1)[1].strip() if ":" in raw else ""
                fig.update_layout(title=None, height=height, margin={"l": 8, "r": 8, "t": 8, "b": 8})
                with st.container(key=f"cc_{idx}"):
                    st.markdown(f'<div class="cc-h"><div class="t">{esc(CHART_TITLES_HE.get(ctype, ctype))}</div>'
                                f'<div class="s">{esc(metric)}</div></div>', unsafe_allow_html=True)
                    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key=f"chart_{ctype}_{idx}")

            if chart_types:
                with next(t):
                    first, *rest = chart_types
                    chart_card(first, 0, 360)
                    if rest:
                        for j, (col, ctype) in enumerate(zip(st.columns(len(rest), gap="small"), rest), 1):
                            with col:
                                chart_card(ctype, j, 290)
                    st.caption("הוויזואליזציות נבחרו אוטומטית לפי מבנה הנתונים")
            with next(t):
                st.dataframe(df, width="stretch", hide_index=True, height=min(520, 40 + 35 * len(df)))
                st.download_button("הורד CSV", df.to_csv(index=False).encode("utf-8-sig"), file_name="results.csv",
                                   mime="text/csv", icon=":material/download:")
            with next(t):
                st.markdown(f'<div class="card" style="padding:16px 20px;margin-bottom:4px;color:var(--tx-2);font-size:.92rem;line-height:1.7">'
                            f'{esc(final.get("sql_explanation", ""))}</div>', unsafe_allow_html=True)
                st.code(final.get("sql_query", ""), language="sql")

    st.write("")
    st.button("ניתוח חדש", on_click=reset, key="new_q", icon=":material/add:")
