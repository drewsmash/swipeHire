"""SwipeHire web application.

Docker:  docker compose up --build -d   then open http://localhost:8300
Local:   python main.py (needs a MySQL server and a .env, see AGENTS.md)
"""
import functools
import hashlib
import os
import secrets

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

import db
from views import admin, auth, employer, files, guests, seeker
from views.common import current_user, fmt_pay, label, timeago

app = Flask(__name__)
# Behind Cloudflare: trust X-Forwarded-Proto/Host so external URLs come out as https://<public host>.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")


def public_url(path=""):
    """Absolute URL for link previews. Uses PUBLIC_URL from .env when set
    (e.g. https://swipehire.whalenet.net), otherwise the address the request came in on."""
    base = PUBLIC_URL or request.url_root.rstrip("/")
    return base + (path if path.startswith("/") else "/" + path)


app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB uploads (resume / photo)

app.register_blueprint(auth.bp)
app.register_blueprint(seeker.bp)
app.register_blueprint(employer.bp)
app.register_blueprint(files.bp)
app.register_blueprint(admin.bp)

app.add_template_filter(fmt_pay, "pay")
app.add_template_filter(label, "label")
app.add_template_filter(timeago, "ago")


@functools.lru_cache(maxsize=64)
def static_version(filename):
    """Short content hash of a static file. Changes whenever the file changes."""
    try:
        with open(os.path.join(app.static_folder, filename), "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:10]
    except OSError:
        return None


@app.url_defaults
def bust_static_cache(endpoint, values):
    """Add ?v=<hash> to every static URL. Cloudflare and browsers cache style.css/app.js
    for hours; a new hash after each change means they always fetch the new file."""
    if endpoint == "static" and "filename" in values and "v" not in values:
        version = static_version(values["filename"])
        if version:
            values["v"] = version


@app.before_request
def check_csrf_token():
    """Every POST must carry the per-session token (form field or X-CSRF-Token header)."""
    if request.method == "POST":
        token = session.get("csrf_token")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or sent != token:
            abort(400, "Form expired. Reload the page and try again.")


@app.context_processor
def page_globals():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    me = current_user()
    return {"csrf_token": session["csrf_token"], "me": me, "is_guest": guests.is_guest(me),
            "public_url": public_url}


@app.get("/")
def home():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if user["role"] == "employer":
        return redirect(url_for("employer.applicants"))
    if user["role"] == "admin":
        return redirect(url_for("admin.stats"))
    return redirect(url_for("seeker.home"))


@app.get("/try")
@app.get("/try/<role>")
def try_it(role="seeker"):
    """Shareable link: splash page that drops the visitor straight into a NEW guest account.
    GET only shows the page (safe for link-preview bots); its script then POSTs /guest."""
    role = "employer" if role == "employer" else "seeker"
    me = current_user()
    continuing = bool(me) and guests.is_guest(me) and me["role"] == role
    return render_template("try.html", role=role, continuing=continuing)


@app.get("/health")
def health():
    ok = db.check_connection()
    return {"database": "connected" if ok else "disconnected"}, (200 if ok else 503)


@app.errorhandler(413)
def too_large(_):
    return "File too large (8 MB max). Go back and pick a smaller file.", 413


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), debug=True)
