"""Helpers shared by every screen: login state, role guards, formatting."""
from functools import wraps

from flask import g, redirect, request, session, url_for

import db

LABELS = {
    "remote": "Remote", "hybrid": "Hybrid", "in_person": "In person",
    "full_time": "Full time", "part_time": "Part time", "any": "Any",
}


def current_user():
    """The logged-in user row (cached per request) or None."""
    if "user" not in g:
        uid = session.get("user_id")
        g.user = db.fetch_one("SELECT id, email, role FROM users WHERE id = %s", (uid,)) if uid else None
    return g.user


def login_required(role):
    """Decorator: the page needs a logged-in user with this role."""
    def wrap(view):
        @wraps(view)
        def inner(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("auth.login", next=request.path))
            if user["role"] != role:
                return redirect(url_for("home"))
            return view(*args, **kwargs)
        return inner
    return wrap


def wants_json():
    return request.headers.get("X-Requested-With") == "fetch"


def like_param(q):
    """Escape a search string for SQL LIKE."""
    q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{q}%"


def fmt_pay(job):
    lo, hi, period = job["pay_min"], job["pay_max"], job["pay_period"]
    if period == "hour":
        return f"${lo:,}–${hi:,} / hr" if lo != hi else f"${lo:,} / hr"
    short = lambda n: f"${n / 1000:,.0f}k" if n >= 1000 else f"${n:,}"
    return f"{short(lo)}–{short(hi)} / yr" if lo != hi else f"{short(lo)} / yr"


def label(value):
    return LABELS.get(value, value or "")


def to_int(value, low=0, high=10_000_000):
    """Parse an optional whole number from a form; None when blank or invalid."""
    try:
        n = int(str(value).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None
    return n if low <= n <= high else None
