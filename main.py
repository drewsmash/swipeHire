"""SwipeHire web application.

Docker:  docker compose up --build -d   then open http://localhost:8095
Local:   python main.py (needs a MySQL server and a .env, see AGENTS.md)
"""
import os
import secrets

from flask import Flask, abort, redirect, request, session, url_for

import db
from views import auth, employer, files, seeker
from views.common import current_user, fmt_pay, label

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB uploads (resume / photo)

app.register_blueprint(auth.bp)
app.register_blueprint(seeker.bp)
app.register_blueprint(employer.bp)
app.register_blueprint(files.bp)

app.add_template_filter(fmt_pay, "pay")
app.add_template_filter(label, "label")


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
    return {"csrf_token": session["csrf_token"], "me": current_user()}


@app.get("/")
def home():
    user = current_user()
    if not user:
        return redirect(url_for("auth.login"))
    if user["role"] == "employer":
        return redirect(url_for("employer.applicants"))
    return redirect(url_for("seeker.home"))


@app.get("/health")
def health():
    ok = db.check_connection()
    return {"database": "connected" if ok else "disconnected"}, (200 if ok else 503)


@app.errorhandler(413)
def too_large(_):
    return "File too large (8 MB max). Go back and pick a smaller file.", 413


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")), debug=True)
