"""Scheduled Gmail jobs.
  python notifier.py daily              -> 10 PM check-in email
  python notifier.py monthly [YYYY-MM]  -> monthly analysis email (default: last month)
  python notifier.py preview            -> save both emails as HTML files (nothing is sent)
"""
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import pandas as pd

from db import load, using_local_file

IST = ZoneInfo("Asia/Kolkata")
MEMBERS = ["Sripada", "My Brother"]
HEAD = {"Sripada": "linear-gradient(120deg,#6c5ce7,#f06595)", "My Brother": "linear-gradient(120deg,#ff922b,#fcc419)"}
COLOR = {"Food": "#ff8a3d", "Travel": "#4dabf7", "Shopping": "#f06595", "Bills": "#f5b800",
         "Rent": "#20c997", "Fun": "#9775fa", "Other": "#ff5d73"}
ICON = {"Food": "🍔", "Travel": "🚌", "Shopping": "🛍️", "Bills": "💡", "Rent": "🏠", "Fun": "🎮", "Other": "✨"}


def inr(x):
    return f"₹{x:,.0f}"


def totals(df):
    return (df.loc[df.type == "earn", "amount"].sum(), df.loc[df.type == "spend", "amount"].sum())


# ---------- shared HTML pieces ----------
def tiles_html(e, s):
    def td(label, val, bg, fg):
        return (f'<td style="background:{bg};border-radius:12px;padding:10px"><div style="color:{fg}">{label}</div>'
                f'<b style="font-size:20px;color:{fg}">{val}</b></td>')
    return ('<table style="width:100%;text-align:center;border-collapse:separate;border-spacing:6px 0"><tr>'
            + td("💰 Earned", inr(e), "#d3f9d8", "#0a8f6b") + td("🛍️ Spent", inr(s), "#ffe3e3", "#e0364f")
            + td("🎉 Left", inr(e - s), "#e5dbff", "#5f3dc4") + "</tr></table>")


def card(title, inner):
    return (f'<div style="border-radius:18px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.12);margin:16px 0;background:#fff">'
            f'<div style="background:{HEAD[title]};color:#fff;padding:14px 18px;font-size:20px;font-weight:800">{title}</div>'
            f'<div style="padding:16px 18px">{inner}</div></div>')


def wrap(title, sub, summary, blocks):
    btn = ""
    if os.getenv("APP_URL"):
        btn = (f'<p style="text-align:center"><a href="{os.environ["APP_URL"]}" style="display:inline-block;'
               'background:linear-gradient(90deg,#ffc43d,#ff922b);color:#2a1b3d;font-weight:800;text-decoration:none;'
               'padding:12px 26px;border-radius:14px">Open Money Tracker</a></p>')
    return f"""<div style="font-family:Arial,sans-serif;max-width:620px;margin:auto;background:#fff7ec;padding:16px">
 <div style="background:linear-gradient(120deg,#6c5ce7,#f06595,#ff922b);color:#fff;border-radius:18px;padding:20px">
  <div style="font-size:24px;font-weight:800">{title}</div><div>{sub}</div>
  <div style="margin-top:8px;font-size:16px">{summary}</div></div>
 {''.join(blocks)}{btn}
 <p style="color:#888;font-size:12px;text-align:center">Sent automatically by your Family Money Tracker</p></div>"""


# ---------- 10 PM daily email ----------
def build_daily(today):
    blocks, texts, missing, E, S = [], [], [], 0, 0
    for m in MEMBERS:
        d = load(m)
        d = d[d.date.dt.date == today]
        e, s = totals(d)
        E, S = E + e, S + s
        ok = not d[d.type == "spend"].empty
        if not ok:
            missing.append(m)
        status = ('<p style="color:#0a8f6b;font-weight:700">✅ Spending added today</p>' if ok else
                  '<p style="color:#e0364f;font-weight:700">⚠️ No spending added yet. Please update!</p>')
        blocks.append(card(m, tiles_html(e, s) + status))
        texts.append(f"{m}: earned {inr(e)}, spent {inr(s)}, left {inr(e - s)}" + ("" if ok else " (no spending added)"))
    subject = "🔔 10 PM: update today's spending" if missing else "✅ 10 PM check-in: all updated"
    html = wrap("🔔 10 PM check-in", today.strftime("%A, %d %B %Y"),
                f"Together today: earned {inr(E)} · spent {inr(S)} · left {inr(E - S)}", blocks)
    return subject, html, "\n".join(texts)


# ---------- Monthly email ----------
def member_block(m, period):
    df = load(m)
    cur = df[df.date.dt.to_period("M") == period]
    prev = df[df.date.dt.to_period("M") == period - 1]
    e, s = totals(cur)
    ps = totals(prev)[1]
    cats = cur[cur.type == "spend"].groupby("category").amount.sum().sort_values(ascending=False)
    change = "" if ps == 0 else f" ({'↑' if s > ps else '↓'} {abs(s - ps) / ps * 100:.0f}% vs last month)"
    rows = "".join(
        f'<tr><td style="padding:4px 0">{ICON.get(c, "")} {c}</td>'
        f'<td style="width:45%"><div style="background:#eee;border-radius:9px"><div style="height:12px;border-radius:9px;'
        f'width:{v / cats.iloc[0] * 100:.0f}%;background:{COLOR.get(c, "#888")}"></div></div></td>'
        f'<td style="text-align:right;font-weight:700">{inr(v)}</td></tr>' for c, v in cats.items()
    ) or '<tr><td style="color:#888">No spending recorded</td></tr>'
    inner = f'{tiles_html(e, s)}<p style="color:#555">Spending{change}</p><table style="width:100%">{rows}</table>'
    return card(m, inner), f"{m}: earned {inr(e)}, spent {inr(s)}, left {inr(e - s)}{change}", e, s


def build_email(period):
    label = period.strftime("%B %Y")
    blocks, texts, E, S = [], [], 0, 0
    for m in MEMBERS:
        h, t, e, s = member_block(m, period)
        blocks.append(h); texts.append(t); E += e; S += s
    html = wrap("💰 Family money report", label, f"Together: earned {inr(E)} · spent {inr(S)} · left {inr(E - S)}", blocks)
    return f"Family money report · {label}", html, "\n".join(texts)


# ---------- sending ----------
def send_email(subject, html, text):
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ["SMTP_USER"], os.environ["EMAIL_TO"]
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "465"))) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.sendmail(msg["From"], [x.strip() for x in os.environ["EMAIL_TO"].split(",")], msg.as_string())


def require_online_setup():
    """Stop with a clear error instead of sending an empty (all ₹0) email."""
    missing = [k for k in ("SMTP_USER", "SMTP_PASS", "EMAIL_TO") if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing secrets: {', '.join(missing)}. Add them in GitHub -> Settings -> Secrets -> Actions.")
    if using_local_file():
        sys.exit("SHEET_ID / GOOGLE_SERVICE_ACCOUNT_JSON are missing, so there is no data to report. "
                 "Add them in GitHub -> Settings -> Secrets -> Actions.")


def last_month():
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    return pd.Period(arg, "M") if arg else pd.Period(datetime.now(IST).date(), "M") - 1


def daily():
    require_online_setup()
    send_email(*build_daily(datetime.now(IST).date()))
    print("Daily email sent.")


def monthly():
    require_online_setup()
    send_email(*build_email(last_month()))
    print("Monthly email sent.")


def preview():
    for name, (_, html, _) in {"daily": build_daily(datetime.now(IST).date()), "monthly": build_email(last_month())}.items():
        with open(f"preview_{name}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"saved preview_{name}.html")


if __name__ == "__main__":
    {"daily": daily, "monthly": monthly, "preview": preview}[sys.argv[1] if len(sys.argv) > 1 else ""]()
