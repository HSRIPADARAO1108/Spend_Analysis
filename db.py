"""Shared storage for the app and the notifier: a Google Sheet.

Needs two secrets (environment variable or Streamlit secret):
  SHEET_ID                      the long id in the sheet's web address
  GOOGLE_SERVICE_ACCOUNT_JSON   the full contents of the service-account key file
Without them it falls back to a local CSV file (for testing only; it is wiped on Streamlit Cloud).
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


def using_local_file():
    return _creds() is None


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
def add_entry(member, typ, cat, amount, note, d):
    vals = _values()
    used = [i for i in (_to_id(r[0]) for r in vals[1:] if r) if i is not None]
    row = [max(used, default=0) + 1, member, typ, cat, float(amount), note, d.isoformat()]
    with _lock:
        _get_store().append(row)
    _invalidate()


def delete_entries(ids):
    want = {int(i) for i in ids}
    vals = _values()
    nums = [n for n, r in enumerate(vals, start=1) if n > 1 and r and _to_id(r[0]) in want]
    with _lock:
        _get_store().delete_rows(nums)
    _invalidate()


def load(member) -> pd.DataFrame:
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
