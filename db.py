"""Shared storage for the app and the notifier. First one that is configured wins:
  1. DATABASE_URL                       any Postgres (Supabase, Neon, Aiven, CockroachDB...)
  2. SHEET_ID + GOOGLE_SERVICE_ACCOUNT_JSON   a Google Sheet
  3. nothing set                        local CSV file (testing only; wiped on Streamlit Cloud)
Each value can be an environment variable or a Streamlit secret.
"""
import csv
import json
import os
import threading
import time

import pandas as pd

HEADERS = ["id", "member", "type", "category", "amount", "note", "date"]
CSV_PATH = "money_local.csv"
_TTL = 10  # seconds: keeps us far below Google's read limit
_lock = threading.Lock()
_cache = {"t": 0.0, "vals": None}
_store = None


# ---------- secrets ----------
def _secret(name):
    v = os.getenv(name)
    if v:
        return v
    try:
        import streamlit as st
        v = st.secrets.get(name)
    except Exception:
        v = None
    return v


def _creds():
    sid, raw = _secret("SHEET_ID"), _secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sid or not raw:
        return None
    sid = str(sid).strip()
    if "/d/" in sid:  # allow pasting the whole sheet link
        sid = sid.split("/d/")[1].split("/")[0]
    if not isinstance(raw, str):  # secret written as a TOML table
        raw = json.dumps(dict(raw))
    return sid, json.loads(raw)


def _sql_url():
    url = _secret("DATABASE_URL")
    if not url:
        return None
    url = str(url).strip()
    if "=" in url.split("://")[0]:  # pasted 'DATABASE_URL = "postgresql://..."'
        url = url.split("=", 1)[1].strip()
    url = url.strip("'\"").strip()  # remove quote marks
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _with_driver(url):
    """Newer SQLAlchemy defaults to the 'psycopg' driver; use whichever one is installed."""
    if not url.startswith("postgresql://"):
        return url
    try:
        import psycopg2  # noqa: F401
        drv = "postgresql+psycopg2://"
    except ImportError:
        drv = "postgresql+psycopg://"
    return drv + url[len("postgresql://"):]


def _check_url(url):
    """Give a clear message (never printing the password) when the link is wrong."""
    scheme = url.split("://")[0] if "://" in url else ""
    if scheme not in ("postgresql", "postgresql+psycopg2", "sqlite"):
        raise ValueError("DATABASE_URL must start with postgresql:// (copy the Session pooler "
                         "connection string from Supabase -> Connect). The value you set does not.")
    if "[" in url or "]" in url:
        raise ValueError("DATABASE_URL still has [ ] brackets. Replace [YOUR-PASSWORD], including "
                         "the brackets, with your real password.")


def using_local_file():
    return _sql_url() is None and _creds() is None


# ---------- stores ----------
class SheetsStore:
    def __init__(self, sheet_id, info):
        import gspread
        self.sh = gspread.service_account_from_dict(info).open_by_key(sheet_id)
        self.ws = self.sh.sheet1

    def values(self):
        return self.ws.get_all_values()

    def append(self, row):
        self.ws.append_row(row, value_input_option="RAW")  # RAW: text stays text, no formulas run

    def delete_rows(self, nums):  # 1-based sheet row numbers, one API call
        reqs = [{"deleteDimension": {"range": {"sheetId": self.ws.id, "dimension": "ROWS",
                                               "startIndex": n - 1, "endIndex": n}}}
                for n in sorted(nums, reverse=True)]
        if reqs:
            self.sh.batch_update({"requests": reqs})


class CsvStore:
    def values(self):
        if not os.path.exists(CSV_PATH):
            return []
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            return list(csv.reader(f))

    def append(self, row):
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def delete_rows(self, nums):
        drop = set(nums)
        rows = [r for i, r in enumerate(self.values(), start=1) if i not in drop]
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)


def _get_store():
    global _store
    if _store is None:
        c = _creds()
        _store = SheetsStore(*c) if c else CsvStore()
    return _store


def _values():
    with _lock:
        if _cache["vals"] is not None and time.time() - _cache["t"] < _TTL:
            return _cache["vals"]
        vals = _get_store().values()
        if not vals:  # brand-new empty sheet: write the header row
            _get_store().append(HEADERS)
            vals = [HEADERS]
        _cache.update(t=time.time(), vals=vals)
        return vals


def _invalidate():
    _cache.update(t=0.0, vals=None)


def _to_id(x):
    try:
        return int(float(str(x).strip()))
    except ValueError:
        return None


# ---------- public API (same as before) ----------
def _list_add_entry(member, typ, cat, amount, note, d):
    vals = _values()
    used = [i for i in (_to_id(r[0]) for r in vals[1:] if r) if i is not None]
    row = [max(used, default=0) + 1, member, typ, cat, float(amount), note, d.isoformat()]
    with _lock:
        _get_store().append(row)
    _invalidate()


def _list_delete_entries(ids):
    want = {int(i) for i in ids}
    vals = _values()
    nums = [n for n, r in enumerate(vals, start=1) if n > 1 and r and _to_id(r[0]) in want]
    with _lock:
        _get_store().delete_rows(nums)
    _invalidate()


def _list_load(member) -> pd.DataFrame:
    vals = _values()
    cols = ["id", "type", "category", "amount", "note", "date"]
    rows = [(r + [""] * len(HEADERS))[:len(HEADERS)] for r in vals[1:] if r]
    df = pd.DataFrame(rows, columns=HEADERS)
    df = df[df["member"] == member].copy()
    df["id"] = df["id"].map(_to_id)
    df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(",", ""), errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["id", "amount", "date"])
    df["id"] = df["id"].astype(int)
    df = df.sort_values(["date", "id"], ascending=False)[cols].reset_index(drop=True)
    return df


# ---------- SQL backend (Postgres / SQLite via DATABASE_URL) ----------
_engine = None
_table = None


def _sql():
    global _engine, _table
    if _engine is None:
        from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine
        meta = MetaData()
        _table = Table(
            "entries", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("member", String), Column("type", String), Column("category", String),
            Column("amount", Float), Column("note", String), Column("date", String),
        )
        _check_url(_sql_url())
        try:
            _engine = create_engine(_with_driver(_sql_url()), pool_pre_ping=True)
        except Exception:
            raise ValueError("DATABASE_URL could not be read. Use only letters and numbers in the "
                             "database password, and paste only the link (no quotes, no name=).") from None
        meta.create_all(_engine)
    return _engine, _table


def _sql_add_entry(member, typ, cat, amount, note, d):
    from sqlalchemy import insert
    eng, t = _sql()
    with eng.begin() as c:
        c.execute(insert(t).values(member=member, type=typ, category=cat,
                                   amount=float(amount), note=note, date=d.isoformat()))


def _sql_delete_entries(ids):
    from sqlalchemy import delete
    eng, t = _sql()
    with eng.begin() as c:
        c.execute(delete(t).where(t.c.id.in_([int(i) for i in ids])))


def _sql_load(member):
    from sqlalchemy import select
    eng, t = _sql()
    q = (select(t.c.id, t.c.type, t.c.category, t.c.amount, t.c.note, t.c.date)
         .where(t.c.member == member).order_by(t.c.date.desc(), t.c.id.desc()))
    with eng.connect() as c:
        df = pd.read_sql_query(q, c)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------- public API (the app and notifier only use these) ----------
def add_entry(member, typ, cat, amount, note, d):
    return (_sql_add_entry if _sql_url() else _list_add_entry)(member, typ, cat, amount, note, d)


def delete_entries(ids):
    return (_sql_delete_entries if _sql_url() else _list_delete_entries)(ids)


def load(member) -> pd.DataFrame:
    return (_sql_load if _sql_url() else _list_load)(member)
