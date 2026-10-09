import hmac
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

from db import add_entry, delete_entries, load, using_local_file

# ---------- Config ----------
IST = ZoneInfo("Asia/Kolkata")
MEMBERS = ["Sripada", "Vyasa"]
THEME = {
    "Sripada": "linear-gradient(120deg,#6c5ce7,#f06595,#ff922b,#6c5ce7)",
    "Vyasa": "linear-gradient(120deg,#ff922b,#fcc419,#51cf66,#ff922b)",
}
SPEND_CATS = {
    "Food": ("🍔", "#ff8a3d"), "Fuel": ("⛽", "#e8590c"), "Travel": ("🚌", "#4dabf7"),
    "Shopping": ("🛍️", "#f06595"), "Bills": ("💡", "#f5b800"), "Rent": ("🏠", "#20c997"),
    "Fun": ("🎮", "#9775fa"), "Other": ("✨", "#ff5d73"),
}
EARN_CATS = {
    "Salary": ("💼", "#12b886"), "Freelance": ("💻", "#0ca678"),
    "Mutt": ("🛕", "#7048e8"),
    "Gift": ("🎁", "#ff6b9d"), "Other": ("✨", "#51cf66"),
}
ICON = {**{k: v[0] for k, v in EARN_CATS.items()}, **{k: v[0] for k, v in SPEND_CATS.items()}}
COLOR = {**{k: v[1] for k, v in EARN_CATS.items()}, **{k: v[1] for k, v in SPEND_CATS.items()}}

st.set_page_config(page_title="Family Money Tracker", page_icon="💰", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
@keyframes drift{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
@keyframes pop{from{transform:scale(.88) translateY(10px);opacity:0}to{transform:none;opacity:1}}
@keyframes grow{from{width:0}}
@keyframes pulse{0%,100%{box-shadow:0 8px 18px rgba(108,92,231,.25)}50%{box-shadow:0 0 0 8px rgba(240,101,149,.25),0 8px 22px rgba(108,92,231,.4)}}
@keyframes floaty{0%,100%{transform:translateY(0) rotate(-6deg)}50%{transform:translateY(-12px) rotate(8deg)}}
@keyframes shine{0%{transform:translateX(-120%)}100%{transform:translateX(220%)}}

.stApp{background:linear-gradient(135deg,#fff7ec,#ffe8f1,#e8e4ff,#e3f9ee,#fff7ec);background-size:400% 400%;animation:drift 22s ease infinite}
/* FIX: push content below Streamlit's top bar and hide Share/star/edit/GitHub buttons */
.block-container{max-width:1200px;width:100%;padding-top:4.2rem;padding-bottom:3rem}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer{display:none !important}
/* Try to hide the "Created by / Hosted with Streamlit" badge (may not work on Community Cloud) */
[class*="viewerBadge"],[data-testid="stAppViewerBadge"],a[href*="streamlit.io/cloud"],
._container_gzau3_1,._viewerBadge_nim44_23{display:none !important}
header[data-testid="stHeader"]{background:transparent}
.hero{position:relative;overflow:hidden;border-radius:26px;padding:20px 22px;color:#fff;margin-bottom:14px;
  background-size:300% 300%;animation:drift 9s ease infinite;box-shadow:0 10px 24px rgba(108,92,231,.28)}
.hero h1{margin:0;font-size:clamp(1.35rem,4.5vw,2.2rem);font-weight:800;color:#fff;position:relative;overflow-wrap:anywhere}
.hero p{margin:2px 0 0;font-weight:700;position:relative}
.fl{position:absolute;font-size:1.8rem;animation:floaty 4s ease-in-out infinite;opacity:.85}
.f1{right:6%;top:12%}.f2{right:18%;bottom:8%;animation-delay:1s}.f3{right:30%;top:20%;animation-delay:2s}
.tile{position:relative;overflow:hidden;border-radius:22px;padding:16px 18px;color:#fff;margin-bottom:10px;
  box-shadow:0 8px 18px rgba(0,0,0,.12);animation:pop .6s ease both}
.tile::after{content:"";position:absolute;top:0;left:0;width:40%;height:100%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.35),transparent);animation:shine 4.5s ease-in-out infinite}
.tile .l{font-weight:700;opacity:.95}
.tile .v{font-size:clamp(1.5rem,3.2vw,2rem);font-weight:800;line-height:1.15;word-break:break-word}
.tile .m{font-weight:700;font-size:.9rem;opacity:.95;margin-top:2px}
.earn{background:linear-gradient(135deg,#12b886,#63e6be)}
.spend{background:linear-gradient(135deg,#ff5d73,#ffa94d);animation-delay:.1s}
.net{background:linear-gradient(90deg,#6c5ce7,#f06595);animation:pop .6s ease .2s both,pulse 3s ease-in-out 1s infinite}
.netneg{background:linear-gradient(90deg,#e03131,#862e9c);animation:pop .6s ease .2s both}
.bar{height:18px;border-radius:99px;overflow:hidden;display:flex;background:linear-gradient(90deg,#ff5d73,#ffa94d);margin:4px 0 2px;box-shadow:inset 0 2px 4px rgba(0,0,0,.15)}
.bar i{display:block;height:100%;background:linear-gradient(90deg,#12b886,#63e6be);animation:grow 1.2s ease-out}
.barl{display:flex;justify-content:space-between;font-weight:700;font-size:.85rem;margin-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}
.chip{border-radius:16px;padding:8px 14px;color:#fff;font-weight:800;box-shadow:0 4px 10px rgba(0,0,0,.12);animation:pop .5s ease both;transition:transform .2s}
.chip:hover{transform:translateY(-4px) scale(1.06)}
.chip small{display:block;font-weight:600;opacity:.95}
.top{background:linear-gradient(90deg,#ffd43b,#ff922b);border-radius:16px;padding:10px 14px;font-weight:800;color:#2a1b3d;margin-bottom:10px;animation:pop .5s ease both}
h2,h3{color:#5f3dc4 !important}
button[data-baseweb="tab"]{background:#fff;border-radius:99px;margin-right:6px;padding:6px 14px;font-weight:800;box-shadow:0 3px 8px rgba(0,0,0,.08);transition:transform .2s}
button[data-baseweb="tab"]:hover{transform:translateY(-2px)}
button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,#6c5ce7,#f06595);color:#fff}
button[data-baseweb="tab"][aria-selected="true"] p{color:#fff}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none}
.stButton>button,[data-testid="stFormSubmitButton"]>button,.stDownloadButton>button{
  background:linear-gradient(90deg,#ffc43d,#ff922b);color:#2a1b3d;font-weight:800;border:0;border-radius:14px;min-height:46px;transition:transform .15s}
.stButton>button:active,[data-testid="stFormSubmitButton"]>button:active{transform:scale(.96)}
div[role="radiogroup"]{gap:8px}
div[role="radiogroup"] label{background:#fff;border-radius:99px;padding:6px 16px;box-shadow:0 3px 8px rgba(0,0,0,.08)}

/* ===== FORCE READABLE COLOURS (works even when phone/browser is in dark mode) ===== */
:root{color-scheme:light}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{color:#2a1b3d}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,
[data-testid="stWidgetLabel"] p,[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] *,
div[role="radiogroup"] label p,div[role="radiogroup"] label div{color:#2a1b3d !important;font-weight:700}
h1,h2,h3,h4{color:#5f3dc4 !important}
.hero h1,.hero p,.hero span{color:#fff !important}
.tile,.tile *,.chip,.chip *{color:#fff !important}
.top,.top *{color:#2a1b3d !important}
button[data-baseweb="tab"] p{color:#5f3dc4 !important;font-weight:800}
button[data-baseweb="tab"][aria-selected="true"] p{color:#fff !important}
.stButton>button p,[data-testid="stFormSubmitButton"]>button p,.stDownloadButton>button p{color:#2a1b3d !important;font-weight:800}
input,textarea,div[data-baseweb="select"]>div,div[data-baseweb="input"],div[data-baseweb="base-input"]{
  background:#fff !important;color:#2a1b3d !important;border-radius:12px}
div[data-baseweb="select"] *{color:#2a1b3d !important}
[data-baseweb="popover"],[data-baseweb="popover"] ul,[data-baseweb="popover"] li{background:#fff !important;color:#2a1b3d !important}
[data-testid="stForm"]{background:rgba(255,255,255,.75);border:2px solid #e5dbff;border-radius:20px;padding:14px}
[data-testid="stExpander"]{background:rgba(255,255,255,.8);border-radius:18px;border:2px solid #ffe3e3}
[data-testid="stExpander"] summary p{color:#e0364f !important;font-weight:800}
[data-testid="stDataFrame"],[data-testid="stDataEditor"]{background:#fff;border-radius:16px;box-shadow:0 4px 12px rgba(0,0,0,.08);padding:4px}

/* colourful alerts */
[data-testid="stAlert"]{border-radius:18px;border:0;box-shadow:0 6px 16px rgba(255,146,43,.25);
  background:linear-gradient(90deg,#fff3bf,#ffd8a8,#ffc9e0);background-size:200% 200%;animation:drift 8s ease infinite}
[data-testid="stAlert"] *{color:#5a2d00 !important;font-weight:700}

/* member selector: chosen person lights up */
div[role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,#6c5ce7,#f06595,#ff922b);
  background-size:200% 200%;animation:drift 5s ease infinite;box-shadow:0 6px 16px rgba(108,92,231,.4);transform:translateY(-2px)}
div[role="radiogroup"] label:has(input:checked) p,div[role="radiogroup"] label:has(input:checked) div{color:#fff !important}
div[role="radiogroup"] label{transition:transform .2s,box-shadow .2s;cursor:pointer}
div[role="radiogroup"] label:hover{transform:translateY(-2px) scale(1.04)}

/* extra life: rainbow strip under the hero, lifting tiles, wiggling emojis */
@keyframes rainbow{0%{background-position:0% 50%}100%{background-position:200% 50%}}
@keyframes wiggle{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(8deg)}}
.hero::after{content:"";position:absolute;left:0;right:0;bottom:0;height:6px;
  background:linear-gradient(90deg,#ff5d73,#ffa94d,#ffd43b,#51cf66,#4dabf7,#9775fa,#ff5d73);background-size:200% 100%;animation:rainbow 3s linear infinite}
.tile{transition:transform .25s,box-shadow .25s}
.tile:hover{transform:translateY(-6px) scale(1.02);box-shadow:0 14px 28px rgba(0,0,0,.2)}
.hero h1{animation:pop .7s ease both}
.chip small{font-size:1.05rem}

/* ===== RESPONSIVE: base (all screens) ===== */
html,body,.stApp{overflow-x:hidden}
div[data-baseweb="tab-list"]{overflow-x:auto;flex-wrap:nowrap;gap:4px;padding:4px 2px 8px;scrollbar-width:none}
div[data-baseweb="tab-list"]::-webkit-scrollbar{display:none}
button[data-baseweb="tab"]{flex:0 0 auto;white-space:nowrap}
div[role="radiogroup"]{flex-wrap:wrap}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"],[data-testid="stDataEditor"]{max-width:100%}
input,select,textarea{font-size:16px !important}
.stButton>button,[data-testid="stFormSubmitButton"]>button,.stDownloadButton>button{min-height:46px}

/* ===== TABLET (and small laptops): columns wrap 2 per row ===== */
@media (max-width:1024px){
  .block-container{padding-left:1.2rem;padding-right:1.2rem}
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;gap:.75rem}
  [data-testid="stColumn"]{min-width:calc(50% - .75rem) !important;flex:1 1 calc(50% - .75rem) !important}
}

/* ===== MOBILE: everything stacks, compact sizes ===== */
@media (max-width:640px){
  .block-container{padding-left:.8rem;padding-right:.8rem;padding-top:3.6rem;padding-bottom:max(2.5rem,env(safe-area-inset-bottom))}
  [data-testid="stColumn"]{min-width:100% !important;flex:1 1 100% !important}
  .hero{padding:16px;border-radius:20px}
  .hero p{font-size:.85rem}
  .fl{font-size:1.2rem}.f3{display:none}
  .tile{padding:12px 14px;border-radius:18px}
  .chip{padding:6px 10px;font-size:.85rem}
  .top{font-size:.9rem}
  div[role="radiogroup"] label{padding:5px 12px}
  h2,h3{font-size:1.2rem !important}
  button[data-baseweb="tab"]{padding:5px 12px;font-size:.85rem}
  .stButton>button,.stDownloadButton>button{width:100%}
}

/* ===== LAPTOP / LARGE DESKTOP: use more width ===== */
@media (min-width:1400px){
  .block-container{max-width:1320px}
}
@media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- PIN lock ----------
def get_pin():
    pin = os.getenv("APP_PIN")
    if not pin:
        try:
            pin = st.secrets.get("APP_PIN")
        except Exception:
            pin = None
    return str(pin) if pin else None


def pin_gate():
    pin = get_pin()
    if pin is None:
        st.warning("⚠️ No APP_PIN is set, so anyone with the link can open this app. "
                   "Add APP_PIN in Streamlit secrets.")
        return
    if st.session_state.get("authed"):
        return
    st.markdown('<div class="hero" style="background:linear-gradient(120deg,#6c5ce7,#f06595,#ff922b)">'
                '<h1>🔒 Family Money Tracker</h1><p>Enter your PIN to continue</p></div>',
                unsafe_allow_html=True)
    with st.form("pin_form"):
        typed = st.text_input("PIN", type="password", label_visibility="collapsed", placeholder="Enter PIN")
        if st.form_submit_button("Unlock", use_container_width=True):
            if hmac.compare_digest(typed.encode(), pin.encode()):
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Wrong PIN. Try again.")
    st.stop()


pin_gate()


# ---------- Helpers ----------
def inr(x):
    return f"₹{x:,.2f}".replace(".00", "")


def mood(e, s):
    if e == 0 and s == 0:
        return "Add your first entry ✍️"
    if e == 0:
        return "No earnings logged yet 👀"
    r = (e - s) / e
    if r >= 0.5:
        return "Super saver! 🌟"
    if r >= 0.2:
        return "Nice and steady 👍"
    if r >= 0:
        return "Close to the limit 😅"
    return "Over budget, slow down! 🚨"


def tiles(df, label):
    e = df.loc[df.type == "earn", "amount"].sum()
    s = df.loc[df.type == "spend", "amount"].sum()
    n = e - s
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="tile earn"><div class="l">💰 Earned {label}</div><div class="v">{inr(e)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="tile spend"><div class="l">🛍️ Spent {label}</div><div class="v">{inr(s)}</div></div>', unsafe_allow_html=True)
    cls, word, ico = ("net", "Left over", "🎉") if n >= 0 else ("netneg", "Spent more than earned", "⚠️")
    c3.markdown(f'<div class="tile {cls}"><div class="l">{ico} {word}</div><div class="v">{inr(abs(n))}</div><div class="m">{mood(e, s)}</div></div>', unsafe_allow_html=True)
    pct = 50 if e + s == 0 else e / (e + s) * 100
    st.markdown(f'<div class="bar"><i style="width:{pct}%"></i></div><div class="barl"><span style="color:#0a8f6b">Earned {pct:.0f}%</span><span style="color:#e0364f">Spent {100 - pct:.0f}%</span></div>', unsafe_allow_html=True)


def category_section(df, key):
    sp = df[df.type == "spend"].groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if sp.empty:
        st.info("No spending in this period yet.")
        return
    top = sp.iloc[0]
    a, b = st.columns([1, 1])
    with a:
        st.markdown(f'<div class="top">🏆 Biggest spend: {ICON.get(top.category, "")} {top.category} · {inr(top.amount)}</div>', unsafe_allow_html=True)
        chips = "".join(
            f'<div class="chip" style="background:{COLOR.get(r.category, "#888")};animation-delay:{i * 0.07}s">{ICON.get(r.category, "")} {r.category}<small>{inr(r.amount)}</small></div>'
            for i, r in enumerate(sp.itertuples())
        )
        st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
    with b:
        fig = px.pie(sp, names="category", values="amount", hole=0.5, color="category", color_discrete_map=COLOR)
        fig.update_traces(textinfo="percent", textposition="inside", marker=dict(line=dict(color="#fff", width=2)))
        fig.update_layout(height=360, margin=dict(t=10, b=10, l=10, r=10), showlegend=True,
                          legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"),
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, key=key)


def type_color(col):
    return ["background-color:#d3f9d8;color:#0a8f6b;font-weight:700" if v == "earn"
            else "background-color:#ffe3e3;color:#e0364f;font-weight:700" for v in col]


def entries_table(df):
    if df.empty:
        st.caption("Nothing here yet.")
        return
    show = df.assign(
        date=df.date.dt.strftime("%d %b %Y"),
        category=df.category.map(lambda c: f"{ICON.get(c, '')} {c}"),
    )[["date", "type", "category", "amount", "note"]]
    sty = show.style.apply(type_color, subset=["type"]).format({"amount": "₹{:,.0f}"})
    st.dataframe(sty, use_container_width=True, hide_index=True)


def chart_style(fig, legend_below=True):
    fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10), legend_title_text="", xaxis_title=None,
                      legend=dict(orientation="h", y=-0.25) if legend_below else {},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,.6)")
    return fig


# ---------- Header + member ----------
now = datetime.now(IST)
member = st.radio("Who?", MEMBERS, horizontal=True, label_visibility="collapsed")
h = now.hour
greet = "Good morning 🌅" if h < 12 else "Good afternoon 🌞" if h < 17 else "Good evening 🌆" if h < 21 else "Good night 🌙"
st.markdown(
    f'<div class="hero" style="background:{THEME[member]}">'
    f'<span class="fl f1">💸</span><span class="fl f2">🪙</span><span class="fl f3">💰</span>'
    f'<h1>{greet}, {member}!</h1><p>{now.strftime("%A, %d %B %Y · %I:%M %p")}</p></div>',
    unsafe_allow_html=True,
)
if using_local_file():
    st.warning("⚠️ Not connected to a database yet, so data is temporary. Add DATABASE_URL in "
               "Streamlit secrets so entries are saved and the emails can see them.")

df = load(member)
today = now.date()

flash = st.session_state.pop("flash", None)
if flash == "earn":
    st.balloons()
    st.toast("💰 Earning added. Nice!", icon="🎉")
elif flash == "spend":
    st.toast("🛍️ Spending added.", icon="✅")

today_spend = df[(df.date.dt.date == today) & (df.type == "spend")]
if now.hour >= 22 and today_spend.empty:
    st.warning(f"🔔 It's past 10 PM. Add today's spending for {member}!")

# ---------- Tabs ----------
t_today, t_add, t_month, t_year = st.tabs(["🌞 Today", "➕ Add", "📅 Month", "🗓️ 1 Year"])

with t_today:
    day = df[df.date.dt.date == today]
    tiles(day, "today")
    st.subheader("Where today's money went")
    category_section(day, "cat_today")
    st.subheader("Today's entries")
    entries_table(day)

with t_add:
    st.subheader(f"Add entry for {member}")
    typ = st.radio("Type", ["spend", "earn"], format_func=lambda t: "🛍️ Spent" if t == "spend" else "💰 Earned", horizontal=True)
    cats = list(SPEND_CATS if typ == "spend" else EARN_CATS)
    with st.form("add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        amount = c1.number_input("Amount (₹)", min_value=0.0, step=10.0)
        cat = c2.selectbox("Category", cats, format_func=lambda c: f"{ICON[c]} {c}")
        c3, c4 = st.columns(2)
        d = c3.date_input("Date", value=today, max_value=today)
        note = c4.text_input("Note (optional)")
        if st.form_submit_button("Add entry", use_container_width=True):
            if amount > 0:
                add_entry(member, typ, cat, amount, note.strip(), d)
                st.session_state["flash"] = typ
                st.rerun()
            else:
                st.error("Enter an amount greater than 0.")

with t_month:
    months = [str(p) for p in pd.period_range(end=pd.Period(today, "M"), periods=12, freq="M")][::-1]
    pick = st.selectbox("Month", months)
    mdf = df[df.date.dt.strftime("%Y-%m") == pick]
    tiles(mdf, pick)
    st.subheader("Full expenditure by category")
    category_section(mdf, "cat_month")
    sp = mdf[mdf.type == "spend"]
    if not sp.empty:
        st.subheader("Daily spending")
        daily = sp.groupby([sp.date.dt.day.rename("day"), "category"], as_index=False)["amount"].sum()
        fig = chart_style(px.bar(daily, x="day", y="amount", color="category", color_discrete_map=COLOR))
        st.plotly_chart(fig, use_container_width=True, key="daily")
    st.subheader("All entries this month")
    entries_table(mdf)

with t_year:
    start = pd.Period(today, "M") - 11
    ydf = df[df.date.dt.to_period("M") >= start].copy()
    tiles(ydf, "in 12 months")
    idx = pd.period_range(start, pd.Period(today, "M"), freq="M")
    ydf["month"] = ydf.date.dt.to_period("M")
    piv = ydf.pivot_table(index="month", columns="type", values="amount", aggfunc="sum").reindex(idx).fillna(0)
    for col in ("earn", "spend"):
        if col not in piv:
            piv[col] = 0.0
    piv["left"] = piv["earn"] - piv["spend"]
    piv.index = piv.index.strftime("%b %Y")

    st.subheader("Month by month")
    long = piv.reset_index().rename(columns={"index": "month"}).melt(
        id_vars="month", value_vars=["earn", "spend"], var_name="type", value_name="amount")
    fig = px.bar(long, x="month", y="amount", color="type", barmode="group",
                 color_discrete_map={"earn": "#12b886", "spend": "#ff5d73"})
    fig.add_scatter(x=piv.index, y=piv["left"], mode="lines+markers", name="left",
                    line=dict(color="#6c5ce7", width=4), marker=dict(size=9))
    fig.update_xaxes(tickangle=-45, automargin=True)
    st.plotly_chart(chart_style(fig), use_container_width=True, key="year_bar")

    table = piv[["earn", "spend", "left"]].rename(columns={"earn": "Earned", "spend": "Spent", "left": "Left"})
    table.loc["TOTAL"] = table.sum()
    sty = (table.style.format("₹{:,.0f}")
           .set_properties(subset=["Earned"], **{"background-color": "#d3f9d8", "color": "#0a8f6b", "font-weight": "700"})
           .set_properties(subset=["Spent"], **{"background-color": "#ffe3e3", "color": "#e0364f", "font-weight": "700"})
           .set_properties(subset=["Left"], **{"background-color": "#e5dbff", "color": "#5f3dc4", "font-weight": "700"}))
    st.dataframe(sty, use_container_width=True)

    st.subheader("Full expenditure by category")
    category_section(ydf, "cat_year")
    st.download_button("⬇️ Download all entries (CSV)", df.to_csv(index=False).encode(),
                       file_name=f"{member.replace(' ', '_').lower()}_money.csv", mime="text/csv")

with st.expander("🗑️ Delete wrong entries"):
    if df.empty:
        st.caption("No entries yet.")
    else:
        edit = df.head(50).assign(delete=False)
        edit["date"] = edit.date.dt.strftime("%d %b %Y")
        res = st.data_editor(
            edit, hide_index=True, use_container_width=True, key="editor",
            disabled=["id", "type", "category", "amount", "note", "date"],
            column_config={"id": None},
        )
        if st.button("Delete selected"):
            ids = res.loc[res["delete"], "id"].tolist()
            if ids:
                delete_entries(ids)
                st.rerun()

if get_pin() and st.button("🔒 Lock app"):
    st.session_state["authed"] = False
    st.rerun()
