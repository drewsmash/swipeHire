"""Log in, sign up (as a job seeker or an employer) and log out."""
import mysql.connector
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import db

bp = Blueprint("auth", __name__)


def start_session(user_id):
    token = session.get("csrf_token")
    session.clear()
    session["user_id"] = user_id
    if token:
        session["csrf_token"] = token


def safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = db.fetch_one("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            start_session(user["id"])
            return redirect(safe_next(request.args.get("next")) or url_for("home"))
        flash("Wrong email or password.")
    return render_template("login.html")


# One-click guest login into the seeded demo accounts (see init_db.py).
GUEST_ACCOUNTS = {"seeker": "seeker@swipehire.test", "employer": "google@swipehire.test"}


@bp.post("/guest")
def guest():
    email = GUEST_ACCOUNTS.get(request.form.get("role"))
    user = db.fetch_one("SELECT id FROM users WHERE email = %s", (email,)) if email else None
    if not user:
        flash("Guest accounts are not set up. Run: docker compose down -v && docker compose up -d")
        return redirect(url_for("auth.login"))
    start_session(user["id"])
    flash("You're browsing as a guest using a shared test account.")
    return redirect(url_for("home"))


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    role = request.values.get("role", "seeker")
    if role not in ("seeker", "employer"):
        role = "seeker"
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        if "@" not in email or len(password) < 8 or not name:
            flash("Enter a name, a valid email and a password of at least 8 characters.")
            return render_template("signup.html", role=role)
        pw = generate_password_hash(password)
        try:
            conn = db.get_connection()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (email, password_hash, role) VALUES (%s,%s,%s)", (email, pw, role))
                uid = cur.lastrowid
                if role == "seeker":
                    cur.execute("INSERT INTO seeker_profiles (user_id, full_name, contact_email) VALUES (%s,%s,%s)",
                                (uid, name, email))
                else:
                    cur.execute("INSERT INTO companies (user_id, name, contact_email) VALUES (%s,%s,%s)",
                                (uid, name, email))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except mysql.connector.IntegrityError:
            flash("An account with that email already exists.")
            return render_template("signup.html", role=role)
        start_session(uid)
        flash("Welcome to SwipeHire! Fill in your profile to get better matches." if role == "seeker"
              else "Welcome! Post your first job so seekers can swipe on it.")
        return redirect(url_for("seeker.profile") if role == "seeker" else url_for("employer.job_new"))
    return render_template("signup.html", role=role)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
